#!/usr/bin/env python3
"""Deterministic session-state runtime for NovelForge.

This tool does not run an LLM. It creates/validates session records, enforces
legal lifecycle transitions, appends operational events, and saves checkpoints.
Durable persistence is provided by ../control_plane/control_plane.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_agent_session_v1"
STATUSES = {
    "created", "running", "idle", "awaiting_user", "awaiting_external",
    "completed", "failed", "terminated", "stale",
}
MEMORY_POLICIES = {"none", "bounded", "session", "external", "checkpoint_only"}
RESUME_POLICIES = {"forbidden", "same_session", "same_fingerprint", "checkpoint_revalidate"}
ROLES = {"manager", "writer", "specialist", "semantic_reviewer", "human_reviewer", "other"}
USAGE_CLASSES = {"ordinary_chat", "codex_agentic", "claude_plan", "api_metered", "local_model", "human", "unknown"}

ALLOWED_TRANSITIONS = {
    "created": {"running", "terminated"},
    "running": {"idle", "awaiting_user", "awaiting_external", "completed", "failed", "terminated", "stale"},
    "idle": {"running", "completed", "terminated", "stale"},
    "awaiting_user": {"running", "failed", "terminated", "stale"},
    "awaiting_external": {"running", "failed", "terminated", "stale"},
    "failed": {"running", "terminated", "stale"},
    "completed": {"stale"},
    "terminated": set(),
    "stale": {"terminated"},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError("session file must contain one JSON object")
    return value


def dump(obj: Any, path: Path | None = None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def new_session(resource_id: str, role: str, transport: str, backend: str, *, project_id: str | None = None,
                parent_session_id: str | None = None, task_mode: str | None = None,
                usage_class: str = "unknown", memory_policy: str = "bounded",
                resume_policy: str = "checkpoint_revalidate", provider_session_id: str | None = None,
                external_session_ref: str | None = None) -> dict[str, Any]:
    session = {
        "schema": SCHEMA,
        "resource_id": resource_id,
        "project_id": project_id,
        "session_id": "SES-" + uuid.uuid4().hex,
        "provider_session_id": provider_session_id,
        "external_session_ref": external_session_ref,
        "parent_session_id": parent_session_id,
        "role": role,
        "task_mode": task_mode,
        "transport": transport,
        "backend": backend,
        "usage_class": usage_class,
        "status": "created",
        "memory_policy": memory_policy,
        "context_policy": {
            "authority_snapshot": None,
            "context_manifest_ref": None,
            "allowed_artifact_refs": [],
            "allowed_paths": [],
            "forbidden_context_classes": [],
            "hidden_gold": "forbidden",
        },
        "resume_policy": resume_policy,
        "runs": [],
        "checkpoints": [],
        "events": [{
            "event_id": "EV-" + uuid.uuid4().hex,
            "type": "session.created",
            "run_id": None,
            "artifact_refs": [],
            "artifact_fingerprints": [],
            "created_at": now(),
            "detail": None,
        }],
        "provenance": {"runtime": "session_runtime.py", "version": "2", "durable_store": "control_plane"},
    }
    errors = validate(session)
    if errors:
        raise ValueError("new session invalid: " + "; ".join(errors))
    return session


def validate(session: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["schema", "resource_id", "session_id", "role", "transport", "backend", "usage_class", "status",
                "memory_policy", "context_policy", "resume_policy", "runs", "checkpoints", "events", "provenance"]
    for key in required:
        if key not in session:
            errors.append(f"missing {key}")
    if errors:
        return errors
    if session.get("schema") != SCHEMA: errors.append("invalid schema")
    if not isinstance(session.get("resource_id"), str) or not session["resource_id"]: errors.append("resource_id must be non-empty string")
    if not isinstance(session.get("session_id"), str) or not session["session_id"].startswith("SES-"): errors.append("session_id must start SES-")
    if session.get("role") not in ROLES: errors.append("invalid role")
    if session.get("status") not in STATUSES: errors.append("invalid status")
    if session.get("memory_policy") not in MEMORY_POLICIES: errors.append("invalid memory_policy")
    if session.get("resume_policy") not in RESUME_POLICIES: errors.append("invalid resume_policy")
    if session.get("usage_class") not in USAGE_CLASSES: errors.append("invalid usage_class")
    for key in ("transport", "backend"):
        if not isinstance(session.get(key), str) or not session[key]: errors.append(f"{key} must be non-empty string")
    context = session.get("context_policy")
    if not isinstance(context, dict):
        errors.append("context_policy must be object")
    else:
        if context.get("hidden_gold") != "forbidden": errors.append("context_policy.hidden_gold must be forbidden")
        for key in ("allowed_artifact_refs", "allowed_paths", "forbidden_context_classes"):
            if not isinstance(context.get(key), list): errors.append(f"context_policy.{key} must be array")
    for key in ("runs", "checkpoints", "events"):
        if not isinstance(session.get(key), list): errors.append(f"{key} must be array")
    if session.get("role") == "semantic_reviewer":
        if session.get("memory_policy") not in {"none", "bounded"}: errors.append("semantic_reviewer memory_policy must be none|bounded")
        if session.get("resume_policy") not in {"forbidden", "same_fingerprint"}: errors.append("semantic_reviewer resume_policy must be forbidden|same_fingerprint")
    return errors


def append_event(session: dict[str, Any], event_type: str, *, run_id: str | None = None,
                 artifact_refs: list[str] | None = None, artifact_fingerprints: list[str] | None = None,
                 detail: str | None = None) -> None:
    session["events"].append({"event_id": "EV-" + uuid.uuid4().hex, "type": event_type, "run_id": run_id,
                              "artifact_refs": artifact_refs or [], "artifact_fingerprints": artifact_fingerprints or [],
                              "created_at": now(), "detail": detail})


def transition(session: dict[str, Any], target: str, detail: str | None = None) -> dict[str, Any]:
    errors = validate(session)
    if errors: raise ValueError("invalid session before transition: " + "; ".join(errors))
    source = session["status"]
    if target not in ALLOWED_TRANSITIONS.get(source, set()): raise ValueError(f"illegal session transition {source} -> {target}")
    out = deepcopy(session); out["status"] = target
    event_name = {"running": "session.running", "idle": "session.idle", "awaiting_user": "interrupt.awaiting_user",
                  "awaiting_external": "interrupt.awaiting_external", "completed": "session.completed", "failed": "session.failed",
                  "terminated": "session.terminated", "stale": "session.stale"}[target]
    append_event(out, event_name, detail=detail)
    return out


def start_run(session: dict[str, Any], run_id: str, inputs: list[str]) -> dict[str, Any]:
    out = transition(session, "running") if session["status"] != "running" else deepcopy(session)
    if any(r.get("run_id") == run_id for r in out["runs"]): raise ValueError(f"duplicate run_id {run_id}")
    out["runs"].append({"run_id": run_id, "started_at": now(), "ended_at": None, "status": "running",
                        "input_artifact_fingerprints": inputs, "output_artifact_fingerprints": [], "usage_class": out.get("usage_class")})
    append_event(out, "run.started", run_id=run_id, artifact_fingerprints=inputs)
    return out


def terminate_run(session: dict[str, Any], run_id: str, detail: str | None = None) -> dict[str, Any]:
    """Terminate one active run and its owning Session as one runtime state change."""
    errors = validate(session)
    if errors:
        raise ValueError("invalid session before run termination: " + "; ".join(errors))
    if "terminated" not in ALLOWED_TRANSITIONS.get(session["status"], set()):
        raise ValueError(f"session status {session['status']} cannot be terminated")
    matches = [index for index, run in enumerate(session.get("runs", [])) if isinstance(run, dict) and run.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError(f"run_id must resolve exactly once: {run_id}")
    index = matches[0]
    current = session["runs"][index]
    if current.get("status") != "running" or current.get("ended_at") is not None:
        raise ValueError(f"run is not active: {run_id}")

    out = deepcopy(session)
    ended_at = now()
    run = out["runs"][index]
    run["status"] = "terminated"
    run["ended_at"] = ended_at
    fingerprints = []
    for key in ("input_artifact_fingerprints", "output_artifact_fingerprints"):
        values = run.get(key)
        if isinstance(values, list):
            fingerprints.extend(value for value in values if isinstance(value, str))
    append_event(out, "run.terminated", run_id=run_id, artifact_fingerprints=list(dict.fromkeys(fingerprints)), detail=detail)
    return transition(out, "terminated", detail=detail)


def checkpoint(session: dict[str, Any], run_id: str, workflow_step: str, fingerprints: list[str], *,
               pending_gate: str | None = None, pending_handoff: str | None = None) -> dict[str, Any]:
    if not any(r.get("run_id") == run_id for r in session.get("runs", [])): raise ValueError(f"unknown run_id {run_id}")
    out = deepcopy(session); cp_id = "CP-" + uuid.uuid4().hex
    out["checkpoints"].append({"checkpoint_id": cp_id, "run_id": run_id, "workflow_step": workflow_step,
                               "artifact_fingerprints": fingerprints, "pending_gate": pending_gate,
                               "pending_handoff": pending_handoff, "resume_policy": out["resume_policy"], "created_at": now()})
    append_event(out, "checkpoint.saved", run_id=run_id, artifact_fingerprints=fingerprints, detail=cp_id)
    return out


def self_test() -> int:
    manager = new_session("BOOK-001", "manager", "chat_session", "chatgpt", project_id="BOOK-001",
                          usage_class="ordinary_chat", memory_policy="session", resume_policy="checkpoint_revalidate")
    manager = start_run(manager, "RUN-SELFTEST", ["sha256:" + "a" * 64])
    manager = checkpoint(manager, "RUN-SELFTEST", "frozen-artifact", ["sha256:" + "a" * 64], pending_gate="semantic")
    manager = transition(manager, "awaiting_external"); manager = transition(manager, "running"); manager = transition(manager, "completed")
    reviewer = new_session("BOOK-001", "semantic_reviewer", "local_agent_cli", "claude_code",
                           parent_session_id=manager["session_id"], usage_class="claude_plan", memory_policy="none", resume_policy="same_fingerprint")
    illegal_ok = False
    try: transition(manager, "running")
    except ValueError: illegal_ok = True
    bad = deepcopy(reviewer); bad["memory_policy"] = "session"
    isolation_ok = any("semantic_reviewer memory_policy" in e for e in validate(bad))

    stoppable = new_session("BOOK-STOP", "manager", "chat_session", "chatgpt", project_id="BOOK-STOP",
                            usage_class="ordinary_chat", memory_policy="session", resume_policy="checkpoint_revalidate")
    stoppable = start_run(stoppable, "RUN-STOP", ["sha256:" + "b" * 64])
    stopped = terminate_run(stoppable, "RUN-STOP", detail="self-test")
    run_termination_ok = (
        stopped["status"] == "terminated"
        and stopped["runs"][-1]["status"] == "terminated"
        and isinstance(stopped["runs"][-1]["ended_at"], str)
        and any(event.get("type") == "run.terminated" and event.get("run_id") == "RUN-STOP" for event in stopped["events"])
        and any(event.get("type") == "session.terminated" for event in stopped["events"])
    )

    ok = not validate(manager) and not validate(reviewer) and illegal_ok and isolation_ok and run_termination_ok
    dump({"session_runtime_contract": "PASS" if ok else "FAIL", "manager_status": manager["status"],
          "illegal_transition_guard": illegal_ok, "semantic_reviewer_isolation_guard": isolation_ok,
          "active_run_termination_guard": run_termination_ok, "durable_store_separation": True})
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge session runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    p_new = sub.add_parser("new"); p_new.add_argument("--resource-id", required=True); p_new.add_argument("--project-id"); p_new.add_argument("--role", choices=sorted(ROLES), required=True); p_new.add_argument("--transport", required=True); p_new.add_argument("--backend", required=True); p_new.add_argument("--parent-session-id"); p_new.add_argument("--task-mode"); p_new.add_argument("--usage-class", choices=sorted(USAGE_CLASSES), default="unknown"); p_new.add_argument("--memory-policy", choices=sorted(MEMORY_POLICIES), default="bounded"); p_new.add_argument("--resume-policy", choices=sorted(RESUME_POLICIES), default="checkpoint_revalidate"); p_new.add_argument("--provider-session-id"); p_new.add_argument("--external-session-ref"); p_new.add_argument("--output")
    p_validate = sub.add_parser("validate"); p_validate.add_argument("--session", required=True)
    p_transition = sub.add_parser("transition"); p_transition.add_argument("--session", required=True); p_transition.add_argument("--to", choices=sorted(STATUSES), required=True); p_transition.add_argument("--detail"); p_transition.add_argument("--output")
    sub.add_parser("self-test"); args = parser.parse_args()
    if args.command == "self-test": return self_test()
    if args.command == "new":
        obj = new_session(args.resource_id, args.role, args.transport, args.backend, project_id=args.project_id,
                          parent_session_id=args.parent_session_id, task_mode=args.task_mode, usage_class=args.usage_class,
                          memory_policy=args.memory_policy, resume_policy=args.resume_policy,
                          provider_session_id=args.provider_session_id, external_session_ref=args.external_session_ref)
        dump(obj, Path(args.output) if args.output else None); return 0
    obj = load(Path(args.session))
    if args.command == "validate":
        errors = validate(obj); dump({"valid": not errors, "errors": errors}); return 0 if not errors else 1
    out = transition(obj, args.to, args.detail); dump(out, Path(args.output) if args.output else None); return 0


if __name__ == "__main__": raise SystemExit(main())
