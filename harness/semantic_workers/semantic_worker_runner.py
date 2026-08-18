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


def local_command() -> tuple[str | None, str | None]:
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
    return shlex.join([sys.executable, str(adapter), "--provider", selected]), f"local_{selected}_cli"


def legacy_openai_command() -> str | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    adapter = Path(__file__).resolve().parent / "adapters" / "openai_responses_adapter.py"
    return shlex.join([sys.executable, str(adapter)]) if adapter.exists() else None


def resolve(explicit: str | None) -> tuple[str | None, str | None]:
    if explicit:
        return explicit, "cli"
    if os.getenv("QUILLFRAME_SEMANTIC_WORKER_CMD"):
        return os.environ["QUILLFRAME_SEMANTIC_WORKER_CMD"], "environment"
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
    args = p.parse_args(); cmd, src = resolve(getattr(args, "adapter_command", None))
    if args.cmd == "capabilities":
        dump(capabilities(cmd, src)); return 0
    report = run_jobs(load_json(Path(args.jobs)), cmd, src, args.timeout)
    dump(report, Path(args.output) if args.output else None)
    if args.require_complete and report["status"] not in {"completed", "semantic_reject"}:
        return 2
    return 1 if report["status"] in {"semantic_invalid", "worker_failed"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
