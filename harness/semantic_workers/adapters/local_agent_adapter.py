#!/usr/bin/env python3
"""Local Codex/Claude adapter for Quillframe semantic model contracts.

stdin: one validated semantic job JSON
stdout: one semantic result JSON

A fresh subprocess and temporary workspace are used for each job. The adapter
never decides literary semantics itself: the job's model-readable rubric and
`output_contract` define the requested judgment shape.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
WORKER_DIR = HERE.parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
from semantic_worker_router import ALLOWED_KINDS, validate_job, validate_result  # noqa: E402
from peer_chat_relay import validate_packet  # noqa: E402

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


class FrozenPacketError(ValueError):
    """Infrastructure failure while validating or executing a frozen packet."""


def _frozen_packet(packet_bytes: bytes | str) -> tuple[bytes, dict[str, Any]]:
    raw = packet_bytes.encode("utf-8") if isinstance(packet_bytes, str) else packet_bytes
    if not isinstance(raw, bytes) or not raw:
        raise FrozenPacketError("frozen packet bytes are required")
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrozenPacketError("frozen packet is not valid UTF-8 JSON") from exc
    if not isinstance(packet, dict):
        raise FrozenPacketError("frozen packet must be a JSON object")
    errors = validate_packet(packet)
    if errors:
        raise FrozenPacketError("frozen packet invalid: " + "; ".join(errors))
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if raw != canonical:
        raise FrozenPacketError("frozen packet bytes are not canonical; rebuilding is forbidden")
    nonce = packet.get("relay_nonce")
    binding = packet.get("return_binding") or {}
    if not isinstance(nonce, str) or not nonce or binding.get("run_reference") != nonce:
        raise FrozenPacketError("frozen packet nonce binding is invalid")
    return raw, packet


def frozen_packet_run_reference(packet_bytes: bytes | str) -> str:
    return str(_frozen_packet(packet_bytes)[1]["relay_nonce"])


def execute_frozen_packet(packet_bytes: bytes | str, requested: str, timeout: int = 180) -> dict[str, Any]:
    """Execute one exact packet in a Project-free temporary cwd.

    The return value is the provider's judgment object only.  Reviewer/session/
    authority identity remains the native host/Core lifecycle's responsibility.
    """
    raw, packet = _frozen_packet(packet_bytes)
    provider = requested if requested in {"codex", "claude"} else None
    if provider is None:
        raise FrozenPacketError(f"unsupported native provider: {requested}")
    if not exe(provider):
        raise FrozenPacketError(f"local agent unavailable: {provider}")
    output_contract = packet.get("job", {}).get("output_contract")
    if not isinstance(output_contract, dict):
        raise FrozenPacketError("frozen packet output contract is missing")
    with tempfile.TemporaryDirectory(prefix="quillframe-native-packet-") as td:
        cwd = Path(td)
        try:
            if provider == "codex":
                schema_path = cwd / "judgment.schema.json"
                output_path = cwd / "judgment.json"
                schema_path.write_text(json.dumps(output_contract, ensure_ascii=False, sort_keys=True), encoding="utf-8")
                proc = subprocess.run(
                    codex_command(schema_path, output_path),
                    input=raw,
                    text=False,
                    capture_output=True,
                    cwd=cwd,
                    timeout=timeout,
                    check=False,
                )
                if proc.returncode != 0:
                    raise FrozenPacketError(f"{provider} exited {proc.returncode}")
                if not output_path.is_file():
                    raise FrozenPacketError(f"{provider} produced no judgment")
                raw_result = output_path.read_bytes()
            else:
                proc = subprocess.run(
                    claude_command(),
                    input=raw,
                    text=False,
                    capture_output=True,
                    cwd=cwd,
                    timeout=timeout,
                    check=False,
                )
                if proc.returncode != 0:
                    raise FrozenPacketError(f"{provider} exited {proc.returncode}")
                raw_result = proc.stdout
            if not isinstance(raw_result, bytes):
                raw_result = str(raw_result).encode("utf-8")
            text_result = raw_result.decode("utf-8")
            judgment = extract_claude(text_result) if provider == "claude" else parse_json_text(text_result)
        except subprocess.TimeoutExpired as exc:
            raise FrozenPacketError(f"{provider} timeout after {timeout}s") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, FrozenPacketError):
                raise
            raise FrozenPacketError(f"{provider} judgment invalid: {exc}") from exc
    if not isinstance(judgment, dict):
        raise FrozenPacketError("native judgment must be a JSON object")
    return judgment


def execute_frozen_packet_result(packet_bytes: bytes | str, requested: str, timeout: int = 180) -> dict[str, Any]:
    """Wrap packet-only judgment as the exact peer-result contract.

    The packet owns the job identity and relay nonce.  This adapter may add
    execution metadata, but it must never mint a new run reference or alter the
    frozen packet.
    """
    raw, packet = _frozen_packet(packet_bytes)
    provider = requested if requested in {"codex", "claude"} else None
    if provider is None:
        raise FrozenPacketError(f"unsupported native provider: {requested}")
    nonce = str(packet["relay_nonce"])
    judgment = execute_frozen_packet(raw, provider, timeout)
    return {
        "job_id": packet["job"]["job_id"],
        "subject_id": packet["job"]["subject_id"],
        "kind": packet["job"]["kind"],
        "input_fingerprint": packet["job"]["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": f"{provider}_native_subagent",
            "model_or_reviewer": provider,
            "run_reference": nonce,
        },
        "judgment": judgment,
        "proposals": [],
        "errors": [],
        "execution": {"run_reference": nonce},
    }


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def exe(name: str) -> str | None:
    return shutil.which(name)


def select(requested: str) -> str | None:
    if requested == "codex":
        return "codex" if exe("codex") else None
    if requested == "claude":
        return "claude" if exe("claude") else None
    return "codex" if exe("codex") else ("claude" if exe("claude") else None)


def output_schema(job: dict[str, Any]) -> dict[str, Any]:
    declared = job.get("output_contract")
    if isinstance(declared, dict) and declared.get("type"):
        return declared
    if job.get("kind") == "eval_judge":
        return LEGACY_EVAL_SCHEMA
    return {
        "type": "object",
        "required": ["confidence"],
        "properties": {"confidence": {"type": "number", "minimum": 0, "maximum": 1}},
    }


def empty_judgment() -> dict[str, Any]:
    return {"confidence": 0.0}


def typed(job: dict[str, Any], provider: str, status: str, *, judgment: dict[str, Any] | None = None,
          run_ref: str | None = None, errors: list[str] | None = None) -> dict[str, Any]:
    lineage = dict(job.get("execution") or {})
    lineage["worker_session_id"] = lineage.get("worker_session_id") or f"SES-LOCAL-{uuid.uuid4().hex}"
    lineage["attempt_id"] = lineage.get("attempt_id") or f"ATT-{uuid.uuid4().hex}"
    return {
        "job_id": job.get("job_id", "unknown"),
        "subject_id": job.get("subject_id", "unknown"),
        "kind": job.get("kind", "artifact_audit"),
        "input_fingerprint": job.get("input_fingerprint", "sha256:" + "0" * 64),
        "status": status,
        "worker": {
            "provider": f"{provider}_cli",
            "model_or_reviewer": os.getenv(f"QUILLFRAME_{provider.upper()}_MODEL", f"{provider} configured model"),
            "run_reference": run_ref,
        },
        "judgment": judgment or empty_judgment(),
        "proposals": [],
        "errors": errors or [],
        "execution": lineage,
    }


def prompt(job: dict[str, Any]) -> str:
    bounded = {k: job.get(k) for k in (
        "kind", "subject_id", "input_fingerprint", "input", "rubric",
        "output_contract", "permissions", "provenance",
    )}
    independent = bool((job.get("provenance") or {}).get("independent_gate", False))
    return (
        "You are a bounded semantic worker in the Quillframe fiction-production harness. "
        "Perform the semantic task described by the supplied purpose/rubric using ONLY the packet below. "
        "Do not inspect repository/project files, search for hidden expected labels, or provide private chain-of-thought. "
        "Return ONLY one JSON object matching the packet's output_contract. "
        "Do not settle Canon, promote framework behavior, overwrite durable user taste, grant permissions, or perform story-direction writes. "
        f"This job declares independent_gate={str(independent).lower()}; do not claim stronger independence than the runtime provides.\n\n"
        + json.dumps(bounded, ensure_ascii=False, indent=2)
    )


def parse_json_text(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    obj = json.loads(value)
    if not isinstance(obj, dict):
        raise ValueError("judgment must be object")
    return obj


def codex_command(schema: Path, output: Path) -> list[str]:
    cmd = [
        exe("codex") or "codex", "exec", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "read-only", "--output-schema", str(schema),
        "--output-last-message", str(output),
    ]
    model = os.getenv("QUILLFRAME_CODEX_MODEL", "").strip()
    if model:
        cmd += ["--model", model]
    return cmd + ["-"]


def claude_command() -> list[str]:
    cmd = [
        exe("claude") or "claude", "-p",
        "Execute the bounded Quillframe semantic packet supplied on stdin and return only the requested JSON object.",
        "--output-format", "json", "--max-turns", "1", "--permission-mode", "plan",
    ]
    model = os.getenv("QUILLFRAME_CLAUDE_MODEL", "").strip()
    if model:
        cmd += ["--model", model]
    return cmd


def extract_claude(stdout: str) -> dict[str, Any]:
    outer = json.loads(stdout)
    if isinstance(outer, dict):
        if isinstance(outer.get("structured_output"), dict):
            return outer["structured_output"]
        if isinstance(outer.get("result"), dict):
            return outer["result"]
        if isinstance(outer.get("result"), str):
            return parse_json_text(outer["result"])
        if "confidence" in outer:
            return outer
    raise ValueError("Claude JSON has no parseable semantic judgment")


def execute(job: dict[str, Any], requested: str, timeout: int) -> dict[str, Any]:
    errors = validate_job(job)
    provider = select(requested)
    label = provider or (requested if requested in {"codex", "claude"} else "codex")
    if errors:
        return typed(job, label, "failed", errors=["invalid semantic job: " + "; ".join(errors)])
    if job["kind"] not in ALLOWED_KINDS:
        return typed(job, label, "unsupported", errors=[f"unsupported kind={job['kind']}"])
    if provider is None:
        return typed(job, label, "failed", errors=[f"local agent unavailable: {requested}"])

    run_ref = f"local-{provider}:{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="quillframe-semantic-") as td:
        wd = Path(td)
        try:
            if provider == "codex":
                schema_path = wd / "judgment.schema.json"
                output_path = wd / "judgment.json"
                schema_path.write_text(json.dumps(output_schema(job), ensure_ascii=False), encoding="utf-8")
                proc = subprocess.run(
                    codex_command(schema_path, output_path), input=prompt(job), text=True,
                    capture_output=True, cwd=wd, timeout=timeout, check=False,
                )
                if proc.returncode != 0:
                    return typed(job, provider, "failed", run_ref=run_ref,
                                 errors=[f"Codex exited {proc.returncode}: {proc.stderr.strip()[:2000]}"])
                if not output_path.exists():
                    return typed(job, provider, "failed", run_ref=run_ref, errors=["Codex produced no output file"])
                judgment = parse_json_text(output_path.read_text(encoding="utf-8"))
            else:
                proc = subprocess.run(
                    claude_command(), input=prompt(job), text=True, capture_output=True,
                    cwd=wd, timeout=timeout, check=False,
                )
                if proc.returncode != 0:
                    return typed(job, provider, "failed", run_ref=run_ref,
                                 errors=[f"Claude exited {proc.returncode}: {proc.stderr.strip()[:2000]}"])
                judgment = extract_claude(proc.stdout)
        except subprocess.TimeoutExpired:
            return typed(job, provider, "failed", run_ref=run_ref, errors=[f"{provider} timeout after {timeout}s"])
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return typed(job, provider, "failed", run_ref=run_ref, errors=[f"{provider} execution invalid: {exc}"])

    result = typed(job, provider, "completed", judgment=judgment, run_ref=run_ref)
    binding = validate_result(job, result)
    return result if not binding else typed(job, provider, "failed", run_ref=run_ref, errors=["self-validation: " + "; ".join(binding)])


def self_test() -> int:
    reader_job = {
        "job_id": "SEM-T", "kind": "external_review", "subject_id": "CH-T",
        "created_at": "fixture", "input_fingerprint": "", "input": {"candidate": "x"},
        "rubric": ["judge reader experience"],
        "output_contract": {"type": "object", "required": ["confidence", "would_continue"], "properties": {"confidence": {"type": "number", "minimum": 0, "maximum": 1}, "would_continue": {"type": "boolean"}}},
        "permissions": {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False},
        "provenance": {"independent_gate": False}, "execution": {},
    }
    from semantic_worker_router import fingerprint_for
    reader_job["input_fingerprint"] = fingerprint_for(reader_job)
    schema = output_schema(reader_job); packet = prompt(reader_job); cmd = codex_command(Path("/tmp/schema.json"), Path("/tmp/out.json"))
    ok = not validate_job(reader_job) and reader_job["kind"] in ALLOWED_KINDS and schema == reader_job["output_contract"] and "would_continue" in json.dumps(schema) and "independent_gate=false" in packet and "exec" in cmd and "--ephemeral" in cmd and "--output-schema" in cmd and "--sandbox" in cmd
    dump({"local_agent_adapter_contract": "PASS" if ok else "FAIL", "contract_native_output_schema": schema == reader_job["output_contract"], "all_semantic_kinds_supported": reader_job["kind"] in ALLOWED_KINDS, "isolated_temp_workspace": True, "codex_binary_detected": bool(exe("codex")), "claude_binary_detected": bool(exe("claude"))})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--provider", choices=["auto", "codex", "claude"], default=os.getenv("QUILLFRAME_LOCAL_AGENT_PROVIDER", "auto"))
    p.add_argument("--packet-only", action="store_true", help="consume one canonical frozen peer packet and print only its judgment")
    p.add_argument("--timeout", type=int, default=180); p.add_argument("--capabilities", action="store_true"); p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test: return self_test()
    if args.capabilities:
        selected = select(args.provider)
        dump({"adapter": "local-agent-cli", "adapter_version": "0.3", "requested_provider": args.provider, "selected_provider": selected, "codex_binary_available": bool(exe("codex")), "claude_binary_available": bool(exe("claude")), "available": selected is not None, "supported_kinds": sorted(ALLOWED_KINDS), "output_shape": "job.output_contract", "independence_boundary": "separate_local_agent_process", "api_key_required_by_harness": False})
        return 0
    if args.packet_only:
        try:
            raw_packet = sys.stdin.buffer.read()
            provider = select(args.provider)
            if provider is None:
                raise FrozenPacketError(f"local agent unavailable: {args.provider}")
            dump(execute_frozen_packet(raw_packet, provider, args.timeout))
            return 0
        except FrozenPacketError as exc:
            dump({"status": "infrastructure_failed", "error": str(exc)})
            return 2
    try: job = json.load(sys.stdin)
    except Exception as exc:
        dump({"status": "failed", "errors": [f"stdin job invalid: {exc}"]}); return 1
    result = execute(job, args.provider, args.timeout); dump(result)
    return 0 if result.get("status") in {"completed", "unsupported"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
