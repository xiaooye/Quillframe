#!/usr/bin/env python3
"""Optional OpenAI Responses API adapter for NovelForge semantic contracts.

This path is separately metered API usage and is never required for local/peer
chat operation. stdin is one validated semantic job; stdout is one typed result.
The job's model contract defines the requested semantic output shape.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
WORKER_DIR = HERE.parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
from semantic_worker_router import ALLOWED_KINDS, validate_job, validate_result  # noqa: E402

API_URL = "https://api.openai.com/v1/responses"
LEGACY_EVAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "result", "codes", "evidence", "confidence"],
    "properties": {
        "verdict": {"type": ["string", "null"], "enum": ["accept", "reject", None]},
        "result": {"type": ["string", "null"], "enum": ["pass", "fail", None]},
        "codes": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def output_schema(job: dict[str, Any]) -> dict[str, Any]:
    declared = job.get("output_contract")
    if isinstance(declared, dict) and declared.get("type"):
        return declared
    if job.get("kind") == "eval_judge":
        return LEGACY_EVAL_SCHEMA
    return {"type": "object", "required": ["confidence"], "properties": {"confidence": {"type": "number", "minimum": 0, "maximum": 1}}}


def empty() -> dict[str, Any]:
    return {"confidence": 0.0}


def bounded_prompt(job: dict[str, Any]) -> str:
    payload = {k: job.get(k) for k in ("kind", "subject_id", "input_fingerprint", "input", "rubric", "output_contract", "permissions", "provenance")}
    independent = bool((job.get("provenance") or {}).get("independent_gate", False))
    return (
        "You are a bounded semantic worker in the NovelForge fiction-production harness. "
        "Perform only the semantic task described by the supplied packet using only its evidence. "
        "Do not provide private chain-of-thought. Return only one JSON object matching output_contract. "
        "Never settle Canon, promote framework behavior, overwrite durable taste, grant permissions, or perform story-direction writes. "
        f"The packet declares independent_gate={str(independent).lower()}; do not claim stronger independence than the runtime provides.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def request_body(job: dict[str, Any]) -> dict[str, Any]:
    model = os.getenv("NOVELFORGE_OPENAI_MODEL", "gpt-5.1")
    effort = os.getenv("NOVELFORGE_OPENAI_REASONING_EFFORT", "medium")
    return {
        "model": model,
        "store": False,
        "reasoning": {"effort": effort},
        "input": [{"role": "user", "content": [{"type": "input_text", "text": bounded_prompt(job)}]}],
        "text": {"format": {"type": "json_schema", "name": "novelforge_semantic_judgment", "strict": False, "schema": output_schema(job)}},
    }


def typed(job: dict[str, Any], status: str, judgment: dict[str, Any] | None = None,
          run_ref: str | None = None, errors: list[str] | None = None) -> dict[str, Any]:
    lineage = dict(job.get("execution") or {})
    lineage["worker_session_id"] = lineage.get("worker_session_id") or "SES-OPENAI-" + uuid.uuid4().hex
    lineage["attempt_id"] = lineage.get("attempt_id") or "ATT-" + uuid.uuid4().hex
    return {
        "job_id": job.get("job_id", "unknown"), "subject_id": job.get("subject_id", "unknown"),
        "kind": job.get("kind", "artifact_audit"), "input_fingerprint": job.get("input_fingerprint", "sha256:" + "0" * 64),
        "status": status,
        "worker": {"provider": "openai", "model_or_reviewer": os.getenv("NOVELFORGE_OPENAI_MODEL", "gpt-5.1"), "run_reference": run_ref},
        "judgment": judgment or empty(), "proposals": [], "errors": errors or [], "execution": lineage,
    }


def extract_output(response: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response.get("output_text"), str):
        obj = json.loads(response["output_text"])
        if not isinstance(obj, dict): raise ValueError("output_text not object")
        return obj
    texts = []
    for item in response.get("output", []):
        if not isinstance(item, dict): continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str): texts.append(content["text"])
    if not texts: raise ValueError("Responses payload contained no output text")
    obj = json.loads(texts[-1])
    if not isinstance(obj, dict): raise ValueError("judgment not object")
    return obj


def execute(job: dict[str, Any], timeout: int) -> dict[str, Any]:
    errors = validate_job(job)
    if errors: return typed(job, "failed", errors=["invalid semantic job: " + "; ".join(errors)])
    if job["kind"] not in ALLOWED_KINDS: return typed(job, "unsupported", errors=[f"unsupported kind={job['kind']}"])
    key = os.getenv("OPENAI_API_KEY")
    if not key: return typed(job, "failed", errors=["OPENAI_API_KEY is not configured"])
    body = json.dumps(request_body(job), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response_handle:
            response = json.loads(response_handle.read().decode("utf-8"))
        judgment = extract_output(response)
        result = typed(job, "completed", judgment=judgment, run_ref=response.get("id"))
        binding = validate_result(job, result)
        return result if not binding else typed(job, "failed", run_ref=response.get("id"), errors=["self-validation: " + "; ".join(binding)])
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return typed(job, "failed", errors=[f"OpenAI Responses execution failed: {exc}"])


def self_test() -> int:
    from semantic_worker_router import fingerprint_for
    job = {"job_id": "SEM-T", "kind": "external_review", "subject_id": "CH-T", "created_at": "fixture", "input_fingerprint": "", "input": {"candidate": "x"}, "rubric": ["judge reader experience"], "output_contract": {"type": "object", "required": ["confidence", "would_continue"], "properties": {"confidence": {"type": "number", "minimum": 0, "maximum": 1}, "would_continue": {"type": "boolean"}}}, "permissions": {"canon_write": False, "os_behavior_write": False, "durable_user_taste_write": False}, "provenance": {"independent_gate": False}, "execution": {}}
    job["input_fingerprint"] = fingerprint_for(job)
    body = request_body(job); fmt = body["text"]["format"]
    ok = not validate_job(job) and job["kind"] in ALLOWED_KINDS and fmt["schema"] == job["output_contract"] and fmt["strict"] is False and body["store"] is False
    dump({"openai_adapter_contract": "PASS" if ok else "FAIL", "contract_native_output_schema": fmt["schema"] == job["output_contract"], "all_semantic_kinds_supported": job["kind"] in ALLOWED_KINDS, "store": False, "structured_output_strict": False, "model_execution": False})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--capabilities", action="store_true"); p.add_argument("--dry-run", action="store_true"); p.add_argument("--self-test", action="store_true"); p.add_argument("--timeout", type=int, default=180); args = p.parse_args()
    if args.self_test: return self_test()
    if args.capabilities:
        dump({"provider": "openai", "adapter_version": "0.3", "available": bool(os.getenv("OPENAI_API_KEY")), "supported_kinds": sorted(ALLOWED_KINDS), "output_shape": "job.output_contract", "store": False, "api_url": API_URL}); return 0
    try: job = json.load(sys.stdin)
    except Exception as exc:
        dump({"valid": False, "error": str(exc)}); return 1
    if args.dry_run:
        errors = validate_job(job); dump({"valid": not errors, "errors": errors, "request": request_body(job), "authorization_header_included": False}); return 0 if not errors else 1
    result = execute(job, args.timeout); dump(result); return 0 if result.get("status") in {"completed", "unsupported"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
