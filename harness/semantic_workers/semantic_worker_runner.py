#!/usr/bin/env python3
"""Direct semantic-worker execution boundary.

Validated jobs may run through an explicitly configured Quillframe Model API,
a fresh local Codex/Claude process, the retained OpenAI Responses compatibility
adapter, or higher-level Control Plane/GitHub/chat/human transports. Transport
choice never changes the frozen semantic job or its authority.
"""
from __future__ import annotations

import argparse, json, os, shlex, shutil, subprocess, sys
from pathlib import Path
from typing import Any

from peer_chat_relay import validate_packet, validate_peer_result
from semantic_worker_router import load_json, validate_dispatchable_job, validate_result, worker_job_view


def dump(v: Any, path: Path | None = None) -> None:
    s = json.dumps(v, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(s, encoding="utf-8")
    else:
        print(s, end="")


def model_api_command() -> tuple[str | None, str | None]:
    endpoint = os.getenv("QUILLFRAME_MODEL_API_ENDPOINT", "").strip()
    if not endpoint:
        return None, None
    adapter = Path(__file__).resolve().parent / "adapters" / "model_runtime_adapter.py"
    if not adapter.exists():
        return None, None
    return shlex.join([sys.executable, str(adapter)]), "model_api"


def local_command(*, packet_only: bool = False) -> tuple[str | None, str | None]:
    if os.getenv("QUILLFRAME_DISABLE_LOCAL_AGENT_AUTO", "").lower() in {"1", "true", "yes"}:
        return None, None
    requested = os.getenv("QUILLFRAME_LOCAL_AGENT_PROVIDER", "auto").strip().lower() or "auto"
    if requested not in {"auto", "codex", "claude"}:
        return None, None
    selected = None
    if requested == "codex" and shutil.which("codex"):
        selected = "codex"
    elif requested == "claude" and shutil.which("claude"):
        selected = "claude"
    elif requested == "auto":
        selected = "codex" if shutil.which("codex") else ("claude" if shutil.which("claude") else None)
    if not selected:
        return None, None
    adapter = Path(__file__).resolve().parent / "adapters" / "local_agent_adapter.py"
    if not adapter.exists():
        return None, None
    args = [sys.executable, str(adapter), "--provider", selected]
    if packet_only:
        args.append("--packet-only")
    return shlex.join(args), (f"local_{selected}_native_subagent" if packet_only else f"local_{selected}_cli")


def legacy_openai_command() -> str | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    adapter = Path(__file__).resolve().parent / "adapters" / "openai_responses_adapter.py"
    return shlex.join([sys.executable, str(adapter)]) if adapter.exists() else None


def resolve(explicit: str | None, *, packet_only: bool = False) -> tuple[str | None, str | None]:
    if explicit:
        return explicit, "cli"
    if os.getenv("QUILLFRAME_SEMANTIC_WORKER_CMD"):
        return os.environ["QUILLFRAME_SEMANTIC_WORKER_CMD"], "environment"
    if packet_only:
        return local_command(packet_only=True)
    cmd, src = model_api_command()
    if cmd:
        return cmd, src
    cmd, src = local_command()
    if cmd:
        return cmd, src
    cmd = legacy_openai_command()
    if cmd:
        return cmd, "legacy_openai_env"
    return None, None


def capabilities(cmd: str | None, src: str | None) -> dict[str, Any]:
    return {
        "semantic_execution_runtime": "0.5",
        "router_available": True,
        "command_adapter_supported": True,
        "adapter_configured": bool(cmd),
        "adapter_source": src,
        "model_api_configured": bool(os.getenv("QUILLFRAME_MODEL_API_ENDPOINT", "").strip()),
        "local_codex_detected": shutil.which("codex") is not None,
        "local_claude_detected": shutil.which("claude") is not None,
        "legacy_openai_adapter_available": bool(os.getenv("OPENAI_API_KEY")),
        "independent_worker_available": bool(cmd),
        "fallback_without_adapter": "semantic_pending_at_direct_layer",
        "higher_level_transports": ["control_plane_mcp", "github_bridge", "peer_chat_relay", "human"],
        "provider_identity_required": False,
    }


def invoke(job: dict[str, Any], cmd: str, timeout: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    argv = shlex.split(cmd)
    if not argv:
        return None, {"state": "worker_failed", "error": "empty adapter command"}
    try:
        proc = subprocess.run(
            argv,
            input=json.dumps(worker_job_view(job), ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, {"state": "worker_failed", "error": f"adapter timeout after {timeout}s"}
    except OSError as exc:
        return None, {"state": "worker_failed", "error": f"adapter launch failed: {exc}"}
    if proc.returncode != 0:
        return None, {
            "state": "worker_failed",
            "error": f"adapter exited {proc.returncode}" + (f": {proc.stderr.strip()[:2000]}" if proc.stderr.strip() else ""),
        }
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return None, {"state": "semantic_invalid", "error": f"adapter stdout invalid JSON: {exc}"}
    if not isinstance(result, dict):
        return None, {"state": "semantic_invalid", "error": "adapter result must be object"}
    errors = validate_result(job, result)
    if errors:
        return None, {"state": "semantic_invalid", "error": "; ".join(errors)}
    if result.get("status") == "unsupported":
        return result, {"state": "unsupported"}
    if result.get("status") == "failed":
        return result, {"state": "worker_failed", "error": "; ".join(result.get("errors", [])) or None}
    judgment = result.get("judgment", {})
    rejected = judgment.get("verdict") == "reject" or judgment.get("result") == "fail"
    return result, {"state": "semantic_reject" if rejected else "completed"}


def invoke_frozen_packet(packet_bytes: bytes | str, cmd: str, timeout: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Run a packet-only adapter without rebuilding or reserializing the packet."""
    raw = packet_bytes.encode("utf-8") if isinstance(packet_bytes, str) else packet_bytes
    if not isinstance(raw, bytes) or not raw:
        return None, {"state": "infrastructure_failed", "error": "frozen packet bytes are required"}
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, {"state": "infrastructure_failed", "error": f"frozen packet invalid: {exc}"}
    if not isinstance(packet, dict):
        return None, {"state": "infrastructure_failed", "error": "frozen packet must be an object"}
    packet_errors = validate_packet(packet)
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if packet_errors or raw != canonical:
        return None, {"state": "infrastructure_failed", "error": "; ".join(packet_errors or ["frozen packet bytes are not canonical"])}
    argv = shlex.split(cmd)
    if not argv:
        return None, {"state": "infrastructure_failed", "error": "empty packet adapter command"}
    try:
        proc = subprocess.run(argv, input=raw, text=False, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, {"state": "infrastructure_failed", "error": f"packet adapter timeout after {timeout}s"}
    except OSError as exc:
        return None, {"state": "infrastructure_failed", "error": f"packet adapter launch failed: {exc}"}
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip() if isinstance(proc.stderr, bytes) else str(proc.stderr or "").strip()
        return None, {"state": "infrastructure_failed", "error": f"packet adapter exited {proc.returncode}" + (f": {detail[:2000]}" if detail else "")}
    try:
        result = json.loads(proc.stdout.decode("utf-8") if isinstance(proc.stdout, bytes) else proc.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, {"state": "infrastructure_failed", "error": f"packet result invalid JSON: {exc}"}
    if not isinstance(result, dict):
        return None, {"state": "infrastructure_failed", "error": "packet result must be an object"}
    provider = next((argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "--provider"), None)
    if provider not in {"codex", "claude"}:
        return None, {"state": "infrastructure_failed", "error": "packet adapter provider is missing or unsupported"}
    # The thin local adapter returns only the judgment.  The runner binds that
    # judgment to the Core-owned job and nonce; it does not accept a new
    # reviewer/session/authority identity from the adapter.
    if not {"job_id", "subject_id", "kind", "input_fingerprint", "status", "worker", "judgment", "proposals", "errors"}.issubset(result):
        result = {
            "job_id": packet["job"]["job_id"],
            "subject_id": packet["job"]["subject_id"],
            "kind": packet["job"]["kind"],
            "input_fingerprint": packet["job"]["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": f"{provider}_native_subagent",
                "model_or_reviewer": provider,
                "run_reference": packet["relay_nonce"],
            },
            "judgment": result,
            "proposals": [],
            "errors": [],
            "execution": {"run_reference": packet["relay_nonce"]},
        }
    result_errors = validate_peer_result(packet, result)
    if result_errors:
        return None, {"state": "infrastructure_failed", "error": "; ".join(result_errors)}
    rejected = (result.get("judgment") or {}).get("verdict") == "reject" or (result.get("judgment") or {}).get("result") == "fail"
    return result, {"state": "semantic_reject" if rejected else "completed", "run_reference": packet["relay_nonce"]}


def run_jobs(payload: dict[str, Any], cmd: str | None, src: str | None, timeout: int) -> dict[str, Any]:
    jobs = payload.get("jobs", [])
    executions: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    if not cmd:
        for job in jobs:
            errors = validate_dispatchable_job(job)
            executions.append({
                "job_id": job.get("job_id"), "subject_id": job.get("subject_id"),
                "input_fingerprint": job.get("input_fingerprint"),
                "state": "semantic_invalid" if errors else "semantic_pending",
                "error": "; ".join(errors) if errors else None,
            })
        overall = "semantic_invalid" if any(x["state"] == "semantic_invalid" for x in executions) else "semantic_pending"
        return {
            "semantic_execution_version": "5", "status": overall, "adapter": None,
            "direct_layer_only": True,
            "higher_level_transports": ["control_plane_mcp", "github_bridge", "peer_chat_relay", "human"],
            "results": [], "executions": executions,
        }
    for job in jobs:
        errors = validate_dispatchable_job(job)
        if errors:
            executions.append({
                "job_id": job.get("job_id"), "subject_id": job.get("subject_id"),
                "input_fingerprint": job.get("input_fingerprint"), "state": "semantic_invalid",
                "error": "; ".join(errors),
            })
            continue
        result, execution = invoke(job, cmd, timeout)
        execution.update({
            "job_id": job["job_id"], "subject_id": job["subject_id"],
            "input_fingerprint": job["input_fingerprint"],
        })
        executions.append(execution)
        if result is not None:
            results.append(result)
    states = {x["state"] for x in executions}
    overall = (
        "semantic_invalid" if "semantic_invalid" in states else
        "worker_failed" if "worker_failed" in states else
        "unsupported" if "unsupported" in states else
        "semantic_reject" if "semantic_reject" in states else "completed"
    )
    return {
        "semantic_execution_version": "5", "status": overall,
        "adapter": {"type": "command", "source": src, "command": cmd},
        "direct_layer_only": True, "results": results, "executions": executions,
    }


def main() -> int:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capabilities"); c.add_argument("--adapter-command")
    r = sub.add_parser("run"); r.add_argument("--jobs", required=True); r.add_argument("--output"); r.add_argument("--adapter-command"); r.add_argument("--timeout", type=int, default=180); r.add_argument("--require-complete", action="store_true")
    f = sub.add_parser("run-frozen-packet"); f.add_argument("--packet"); f.add_argument("--output"); f.add_argument("--adapter-command"); f.add_argument("--timeout", type=int, default=180)
    args = p.parse_args(); packet_only = args.cmd == "run-frozen-packet"; cmd, src = resolve(getattr(args, "adapter_command", None), packet_only=packet_only)
    if args.cmd == "capabilities":
        dump(capabilities(cmd, src)); return 0
    if packet_only:
        raw = Path(args.packet).read_bytes() if args.packet else sys.stdin.buffer.read()
        result, execution = invoke_frozen_packet(raw, cmd or "", args.timeout)
        report = {
            "semantic_execution_version": "5",
            "status": execution["state"],
            "adapter": {"type": "frozen-packet-command", "source": src, "command": cmd},
            "result": result,
            "execution": execution,
        }
        dump(report, Path(args.output) if args.output else None)
        return 0 if execution["state"] in {"completed", "semantic_reject"} else 2
    report = run_jobs(load_json(Path(args.jobs)), cmd, src, args.timeout)
    dump(report, Path(args.output) if args.output else None)
    if args.require_complete and report["status"] not in {"completed", "semantic_reject"}:
        return 2
    return 1 if report["status"] in {"semantic_invalid", "worker_failed"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
