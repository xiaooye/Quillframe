#!/usr/bin/env python3
"""Generic Quillframe Model Runtime adapter for bounded semantic jobs.

The user configures only an API endpoint and access token. Quillframe discovers
models/protocols and executes the semantic request through ModelRuntime. This
adapter never grants Canon, Framework-write, or durable-taste authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
WORKER_DIR = HERE.parent.parent
for path in (ROOT, WORKER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from model_runtime import MemorySecretStore, ModelRuntime, ModelRuntimeError  # noqa: E402
from semantic_worker_router import ALLOWED_KINDS, validate_job, validate_result  # noqa: E402


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def bounded_prompt(job: dict[str, Any]) -> str:
    payload = {
        key: job.get(key)
        for key in (
            "kind", "subject_id", "input_fingerprint", "input", "rubric",
            "output_contract", "permissions", "provenance",
        )
    }
    independent = bool((job.get("provenance") or {}).get("independent_gate", False))
    return (
        "You are a bounded semantic worker inside Quillframe. Use only the supplied packet. "
        "Return exactly one JSON object matching output_contract; do not wrap it in Markdown. "
        "Do not provide private chain-of-thought. Do not settle Canon, promote Framework behavior, "
        "overwrite durable taste, grant permissions, or perform unrelated tool actions. "
        f"independent_gate={str(independent).lower()}; do not claim stronger independence than this fresh invocation proves.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def parse_judgment(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    obj = json.loads(value)
    if not isinstance(obj, dict):
        raise ValueError("semantic judgment must be one JSON object")
    return obj


def typed(
    job: dict[str, Any],
    status: str,
    *,
    judgment: dict[str, Any] | None = None,
    model_id: str | None = None,
    protocol: str | None = None,
    response_id: str | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    lineage = dict(job.get("execution") or {})
    lineage["worker_session_id"] = lineage.get("worker_session_id") or "SES-MODELAPI-" + uuid.uuid4().hex
    lineage["attempt_id"] = lineage.get("attempt_id") or "ATT-" + uuid.uuid4().hex
    return {
        "job_id": job.get("job_id", "unknown"),
        "subject_id": job.get("subject_id", "unknown"),
        "kind": job.get("kind", "artifact_audit"),
        "input_fingerprint": job.get("input_fingerprint", "sha256:" + "0" * 64),
        "status": status,
        "worker": {
            "provider": "model_api",
            "model_or_reviewer": model_id or "auto-discovered",
            "run_reference": response_id,
            "transport": "quillframe_model_runtime",
            "protocol": protocol,
        },
        "judgment": judgment or {"confidence": 0.0},
        "proposals": [],
        "errors": errors or [],
        "execution": lineage,
    }


def execute(job: dict[str, Any], *, endpoint: str, token: str, model_preference: str | None = None) -> dict[str, Any]:
    errors = validate_job(job)
    if errors:
        return typed(job, "failed", errors=["invalid semantic job: " + "; ".join(errors)])
    if job.get("kind") not in ALLOWED_KINDS:
        return typed(job, "unsupported", errors=[f"unsupported kind={job.get('kind')}"])
    if not endpoint.strip():
        return typed(job, "failed", errors=["QUILLFRAME_MODEL_API_ENDPOINT is not configured"])
    runtime = ModelRuntime(MemorySecretStore())
    try:
        snapshot = runtime.connect(endpoint, token)
        model = runtime.select_model(snapshot.service_id, {"text"}, preference=model_preference, allow_probe=True)
        turn = runtime.invoke(
            snapshot.service_id,
            model.model_id,
            [
                {"role": "system", "content": "Return only the requested typed JSON object. No Markdown and no private chain-of-thought."},
                {"role": "user", "content": bounded_prompt(job)},
            ],
            [],
            max_output_tokens=int(os.getenv("QUILLFRAME_MODEL_SEMANTIC_MAX_OUTPUT_TOKENS", "4096")),
        )
        judgment = parse_judgment(turn.text)
        result = typed(
            job,
            "completed",
            judgment=judgment,
            model_id=model.model_id,
            protocol=turn.protocol,
            response_id=turn.response_id,
        )
        binding = validate_result(job, result)
        return result if not binding else typed(
            job,
            "failed",
            model_id=model.model_id,
            protocol=turn.protocol,
            response_id=turn.response_id,
            errors=["self-validation: " + "; ".join(binding)],
        )
    except (ModelRuntimeError, ValueError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        return typed(job, "failed", errors=[f"Model Runtime semantic execution failed ({code}): {exc}"])


def self_test() -> int:
    sample = {
        "kind": "external_review",
        "subject_id": "SUBJECT",
        "input_fingerprint": "sha256:" + "a" * 64,
        "input": {"candidate": "x"},
        "rubric": ["judge"],
        "output_contract": {"type": "object", "required": ["confidence"], "properties": {"confidence": {"type": "number"}}},
        "permissions": {"canon_write": False},
        "provenance": {"independent_gate": True},
    }
    prompt = bounded_prompt(sample)
    parsed = parse_judgment('{"confidence":0.8}')
    result = typed(sample, "completed", judgment=parsed, model_id="fixture", protocol="openai_responses")
    encoded = json.dumps(result, ensure_ascii=False)
    ok = (
        "output_contract" in prompt
        and "independent_gate=true" in prompt
        and parsed == {"confidence": 0.8}
        and "access_token" not in encoded.lower()
        and "authorization" not in encoded.lower()
        and result["worker"]["provider"] == "model_api"
    )
    dump({"model_runtime_semantic_adapter_contract": "PASS" if ok else "FAIL", "model_execution": False, "secret_serialized": False})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--capabilities", action="store_true")
    args = p.parse_args()
    if args.self_test:
        return self_test()
    endpoint = os.getenv("QUILLFRAME_MODEL_API_ENDPOINT", "").strip()
    if args.capabilities:
        dump({
            "adapter": "quillframe-model-runtime",
            "adapter_version": "0.1",
            "available": bool(endpoint),
            "endpoint_configured": bool(endpoint),
            "token_present": bool(os.getenv("QUILLFRAME_MODEL_API_TOKEN", "")),
            "model_preference_configured": bool(os.getenv("QUILLFRAME_MODEL_PREFERENCE", "")),
            "secret_serialized": False,
        })
        return 0
    try:
        job = json.load(sys.stdin)
    except Exception as exc:
        dump({"status": "failed", "errors": [f"stdin job invalid: {exc}"]})
        return 1
    result = execute(
        job,
        endpoint=endpoint,
        token=os.getenv("QUILLFRAME_MODEL_API_TOKEN", ""),
        model_preference=os.getenv("QUILLFRAME_MODEL_PREFERENCE") or None,
    )
    dump(result)
    return 0 if result.get("status") in {"completed", "unsupported"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
