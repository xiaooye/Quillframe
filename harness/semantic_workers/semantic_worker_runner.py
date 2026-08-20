#!/usr/bin/env python3
"""Direct semantic-worker execution boundary.

Validated jobs may run through an explicitly configured Quillframe Model API,
a fresh local Codex/Claude process, or higher-level Control Plane/GitHub/chat/
human transports. Transport choice never changes the frozen semantic job or
its authority.
"""
from __future__ import annotations

import argparse, json, os, re, shlex, shutil, subprocess, sys
from pathlib import Path
from typing import Any

from peer_chat_relay import validate_packet, validate_peer_result
from semantic_worker_router import load_json, validate_dispatchable_job, validate_result, worker_job_view


_SAFE_REFERENCE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")


def _safe_reference(value: Any) -> str | None:
    return value if isinstance(value, str) and _SAFE_REFERENCE_RE.fullmatch(value) else None


def _failure(
    state: str,
    code: str,
    *,
    source: str | None = None,
    exit_code: int | None = None,
    timeout: int | None = None,
    run_reference: Any = None,
) -> dict[str, Any]:
    return {
        "state": state,
        "error_code": code,
        "error": code,
        "adapter_source": _safe_reference(source),
        "adapter_configured": source is not None,
        "exit_code": exit_code,
        "timeout_seconds": timeout,
        "run_reference": _safe_reference(run_reference),
    }


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
    return shlex.join(args), f"local_{selected}_cli"


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
        "independent_worker_available": bool(cmd),
        "fallback_without_adapter": "semantic_pending_at_direct_layer",
        "higher_level_transports": ["control_plane_mcp", "github_bridge", "peer_chat_relay", "human"],
        "provider_identity_required": False,
    }


def invoke(job: dict[str, Any], cmd: str, timeout: int, *, source: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    execution = job.get("execution") if isinstance(job, dict) else None
    run_reference = execution.get("attempt_id") if isinstance(execution, dict) else None
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return None, _failure("worker_failed", "adapter_command_invalid", source=source, timeout=timeout, run_reference=run_reference)
    if not argv:
        return None, _failure("worker_failed", "adapter_command_empty", source=source, timeout=timeout, run_reference=run_reference)
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
        return None, _failure("worker_failed", "adapter_timeout", source=source, timeout=timeout, run_reference=run_reference)
    except OSError:
        return None, _failure("worker_failed", "adapter_launch_failed", source=source, timeout=timeout, run_reference=run_reference)
    if proc.returncode != 0:
        return None, _failure("worker_failed", "adapter_exit", source=source, exit_code=proc.returncode, timeout=timeout, run_reference=run_reference)
    try:
        result = json.loads(proc.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None, _failure("semantic_invalid", "adapter_result_invalid_json", source=source, timeout=timeout, run_reference=run_reference)
    if not isinstance(result, dict):
        return None, _failure("semantic_invalid", "adapter_result_not_object", source=source, timeout=timeout, run_reference=run_reference)
    errors = validate_result(job, result)
    if errors:
        return None, _failure("semantic_invalid", "adapter_result_contract_invalid", source=source, timeout=timeout, run_reference=run_reference)
    if result.get("status") == "unsupported":
        return result, {"state": "unsupported"}
    if result.get("status") == "failed":
        return None, _failure("worker_failed", "adapter_reported_failure", source=source, timeout=timeout, run_reference=run_reference)
    judgment = result.get("judgment", {})
    rejected = judgment.get("verdict") == "reject" or judgment.get("result") == "fail"
    return result, {"state": "semantic_reject" if rejected else "completed"}


def invoke_frozen_packet(packet_bytes: bytes | str, cmd: str, timeout: int, *, source: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Run a packet-only adapter without rebuilding or reserializing the packet."""
    raw = packet_bytes.encode("utf-8") if isinstance(packet_bytes, str) else packet_bytes
    if not isinstance(raw, bytes) or not raw:
        return None, _failure("infrastructure_failed", "frozen_packet_bytes_required", source=source, timeout=timeout)
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None, _failure("infrastructure_failed", "frozen_packet_invalid", source=source, timeout=timeout)
    if not isinstance(packet, dict):
        return None, _failure("infrastructure_failed", "frozen_packet_not_object", source=source, timeout=timeout)
    packet_errors = validate_packet(packet)
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if packet_errors or raw != canonical:
        return None, _failure("infrastructure_failed", "frozen_packet_contract_invalid", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return None, _failure("infrastructure_failed", "packet_adapter_command_invalid", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    if not argv:
        return None, _failure("infrastructure_failed", "packet_adapter_command_empty", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    try:
        proc = subprocess.run(argv, input=raw, text=False, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, _failure("infrastructure_failed", "packet_adapter_timeout", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    except OSError:
        return None, _failure("infrastructure_failed", "packet_adapter_launch_failed", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    if proc.returncode != 0:
        return None, _failure("infrastructure_failed", "packet_adapter_exit", source=source, exit_code=proc.returncode, timeout=timeout, run_reference=packet.get("relay_nonce"))
    try:
        result = json.loads(proc.stdout.decode("utf-8") if isinstance(proc.stdout, bytes) else proc.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None, _failure("infrastructure_failed", "packet_result_invalid_json", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    if not isinstance(result, dict):
        return None, _failure("infrastructure_failed", "packet_result_not_object", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    provider = next((argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "--provider"), None)
    if provider not in {"codex", "claude"}:
        return None, _failure("infrastructure_failed", "packet_adapter_provider_invalid", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    # The thin local adapter returns only the judgment.  The runner binds that
    # judgment to the Core-owned job and nonce; it does not accept a new
    # reviewer/session/authority identity from the adapter.
    typed_fields = {
        "job_id", "subject_id", "kind", "input_fingerprint", "status",
        "worker", "judgment", "proposals", "errors",
    }
    if typed_fields.issubset(result):
        return None, _failure("infrastructure_failed", "packet_adapter_identity_forbidden", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    result = {
        "job_id": packet["job"]["job_id"],
        "subject_id": packet["job"]["subject_id"],
        "kind": packet["job"]["kind"],
        "input_fingerprint": packet["job"]["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": f"{provider}_cli",
            "model_or_reviewer": provider,
            "run_reference": packet["relay_nonce"],
        },
        "judgment": result,
        "proposals": [],
        "errors": [],
        "execution": {
            "run_reference": packet["relay_nonce"],
            "transport": "local_cli",
            "assurance_class": "local_process_bounded_context",
            "local_process": {
                "provider": provider,
                "binary": provider,
                "temporary_workspace": True,
                "project_mount": False,
                "os_isolation_attested": False,
            },
        },
    }
    result_errors = validate_peer_result(packet, result)
    if result_errors:
        return None, _failure("infrastructure_failed", "packet_result_contract_invalid", source=source, timeout=timeout, run_reference=packet.get("relay_nonce"))
    rejected = (result.get("judgment") or {}).get("verdict") == "reject" or (result.get("judgment") or {}).get("result") == "fail"
    return result, {"state": "semantic_reject" if rejected else "completed", "run_reference": packet["relay_nonce"]}


def run_jobs(payload: dict[str, Any], cmd: str | None, src: str | None, timeout: int) -> dict[str, Any]:
    jobs = payload.get("jobs", [])
    executions: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    if not cmd:
        for job in jobs:
            errors = validate_dispatchable_job(job)
            failure = _failure(
                "semantic_invalid" if errors else "semantic_pending",
                "semantic_job_invalid" if errors else "semantic_execution_pending",
                source=src,
            )
            executions.append({
                "job_id": job.get("job_id"), "subject_id": job.get("subject_id"),
                "input_fingerprint": job.get("input_fingerprint"),
                **failure,
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
                "input_fingerprint": job.get("input_fingerprint"),
                **_failure("semantic_invalid", "semantic_job_invalid", source=src),
            })
            continue
        result, execution = invoke(job, cmd, timeout, source=src)
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
        "adapter": {"type": "command", "source": _safe_reference(src), "configured": bool(cmd)},
        "direct_layer_only": True, "results": results, "executions": executions,
    }


def _cli_failure_report(*, packet_only: bool, source: str | None, configured: bool, code: str) -> dict[str, Any]:
    execution = _failure("semantic_invalid", code, source=source)
    if packet_only:
        return {
            "semantic_execution_version": "5",
            "status": "semantic_invalid",
            "adapter": {"type": "frozen-packet-command", "source": _safe_reference(source), "configured": configured},
            "result": None,
            "execution": execution,
        }
    return {
        "semantic_execution_version": "5",
        "status": "semantic_invalid",
        "adapter": {"type": "command", "source": _safe_reference(source), "configured": configured},
        "direct_layer_only": True,
        "results": [],
        "executions": [execution],
    }


def _emit_cli_failure(*, packet_only: bool, source: str | None, configured: bool, code: str) -> int:
    report = _cli_failure_report(packet_only=packet_only, source=source, configured=configured, code=code)
    try:
        dump(report)
    except OSError:
        # A broken stdout has no safe secondary transport. The typed exit status
        # remains the only observable signal and raw exception text is discarded.
        pass
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capabilities"); c.add_argument("--adapter-command")
    r = sub.add_parser("run"); r.add_argument("--jobs", required=True); r.add_argument("--output"); r.add_argument("--adapter-command"); r.add_argument("--timeout", type=int, default=180); r.add_argument("--require-complete", action="store_true")
    f = sub.add_parser("run-frozen-packet"); f.add_argument("--packet"); f.add_argument("--output"); f.add_argument("--adapter-command"); f.add_argument("--timeout", type=int, default=180)
    args = p.parse_args(argv); packet_only = args.cmd == "run-frozen-packet"; cmd, src = resolve(getattr(args, "adapter_command", None), packet_only=packet_only)
    if args.cmd == "capabilities":
        dump(capabilities(cmd, src)); return 0
    if packet_only:
        try:
            raw = Path(args.packet).read_bytes() if args.packet else sys.stdin.buffer.read()
        except OSError:
            return _emit_cli_failure(packet_only=True, source=src, configured=bool(cmd), code="semantic_input_unavailable")
        result, execution = invoke_frozen_packet(raw, cmd or "", args.timeout, source=src)
        report = {
            "semantic_execution_version": "5",
            "status": execution["state"],
            "adapter": {"type": "frozen-packet-command", "source": _safe_reference(src), "configured": bool(cmd)},
            "result": result,
            "execution": execution,
        }
        try:
            dump(report, Path(args.output) if args.output else None)
        except OSError:
            return _emit_cli_failure(packet_only=True, source=src, configured=bool(cmd), code="semantic_output_unavailable")
        return 0 if execution["state"] in {"completed", "semantic_reject"} else 2
    try:
        payload = load_json(Path(args.jobs))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _emit_cli_failure(packet_only=False, source=src, configured=bool(cmd), code="semantic_input_invalid_json")
    except OSError:
        return _emit_cli_failure(packet_only=False, source=src, configured=bool(cmd), code="semantic_input_unavailable")
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs", []), list):
        return _emit_cli_failure(packet_only=False, source=src, configured=bool(cmd), code="semantic_input_contract_invalid")
    report = run_jobs(payload, cmd, src, args.timeout)
    try:
        dump(report, Path(args.output) if args.output else None)
    except OSError:
        return _emit_cli_failure(packet_only=False, source=src, configured=bool(cmd), code="semantic_output_unavailable")
    if args.require_complete and report["status"] not in {"completed", "semantic_reject"}:
        return 2
    return 1 if report["status"] in {"semantic_invalid", "worker_failed"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
