#!/usr/bin/env python3
"""Deterministic Claude Code host adapter for Quillframe.

The hook records lifecycle metadata, injects verified bootstrap state, and
fails closed for consequential consumer-Project tools when exact Framework
authority is unavailable. It performs no model calls and grants no Canon or
Framework write authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CP_DIR = ROOT / "harness" / "control_plane"
if str(CP_DIR) not in sys.path:
    sys.path.insert(0, str(CP_DIR))
from control_plane import ControlPlane  # noqa: E402

SCHEMA = "quillframe_claude_bootstrap_v1"
CONSEQUENTIAL_TOOLS = {"Write", "Edit", "Bash"}


def os_session_id(native: str) -> str:
    return "SES-CLAUDE-" + hashlib.sha256(native.encode("utf-8")).hexdigest()[:24]


def sha_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_source_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_sdk() -> ModuleType:
    return _load_source_module("quillframe_project_sdk_hook", ROOT / "project_sdk.py")


def find_project_root(cwd: Path) -> Path | None:
    current = cwd.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "quillframe.toml").is_file():
            return candidate
    return None


def framework_mode_snapshot(event: dict[str, Any], sid: str) -> dict[str, Any]:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else None
    commit = None
    clean = None
    errors: list[str] = []
    try:
        commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        clean = not bool(
            subprocess.run(
                ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=normal"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        )
    except Exception as exc:
        errors.append(f"Framework git inspection failed: {type(exc).__name__}")
    return {
        "schema": SCHEMA,
        "host": "claude_code",
        "scope": "framework",
        "status": "framework_only" if not errors else "blocked",
        "authority_ready": False,
        "materialized_authority_verified": False,
        "project_id": None,
        "project_root": None,
        "framework_root": str(ROOT),
        "framework": {"name": "Quillframe", "version": version, "commit": commit, "clean": clean},
        "primary_task_mode": "UNRESOLVED",
        "session_id": sid,
        "errors": errors,
        "event": event.get("hook_event_name"),
    }


def project_mode_snapshot(project_root: Path, event: dict[str, Any], sid: str) -> dict[str, Any]:
    sdk = project_sdk()
    validation = sdk.validate_project(project_root)
    materialized = sdk.verify_materialized_framework(project_root, ROOT)
    errors = list(validation.get("errors", []))
    errors.extend(x for x in materialized.get("errors", []) if x not in errors)
    manifest = sdk.load_manifest(project_root)
    project = manifest.get("project", {}) if isinstance(manifest, dict) else {}
    lock_path = project_root / "quillframe.lock.json"
    attestation_path = project_root / "framework.attestation.json"
    verified = bool(validation.get("valid")) and bool(materialized.get("materialized_authority_verified"))
    return {
        "schema": SCHEMA,
        "host": "claude_code",
        "scope": "project",
        "status": "verified" if verified else "blocked",
        "authority_ready": bool(validation.get("authority_ready")),
        "materialized_authority_verified": verified,
        "project_id": project.get("id"),
        "project_root": str(project_root),
        "framework_root": str(ROOT),
        "framework": materialized.get("framework_lock") or validation.get("framework_lock"),
        "primary_task_mode": "UNRESOLVED",
        "session_id": sid,
        "errors": errors,
        "event": event.get("hook_event_name"),
        "guard": {
            "lock_sha256": sha_file(lock_path),
            "attestation_sha256": sha_file(attestation_path),
        },
    }


def cache_path(snapshot: dict[str, Any]) -> Path:
    root = Path(snapshot.get("project_root") or ROOT)
    return root / ".quillframe" / "claude" / f"{snapshot['session_id']}.json"


def save_snapshot(snapshot: dict[str, Any]) -> None:
    path = cache_path(snapshot)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_snapshot(project_root: Path | None, sid: str) -> dict[str, Any] | None:
    root = project_root or ROOT
    path = root / ".quillframe" / "claude" / f"{sid}.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) and value.get("schema") == SCHEMA else None
    except (OSError, json.JSONDecodeError):
        return None


def lightweight_snapshot_fresh(snapshot: dict[str, Any]) -> tuple[bool, str | None]:
    if snapshot.get("scope") != "project":
        return True, None
    project_root_raw = snapshot.get("project_root")
    framework = snapshot.get("framework")
    guard = snapshot.get("guard")
    if not isinstance(project_root_raw, str) or not isinstance(framework, dict) or not isinstance(guard, dict):
        return False, "bootstrap cache is incomplete"
    project_root = Path(project_root_raw)
    if sha_file(project_root / "quillframe.lock.json") != guard.get("lock_sha256"):
        return False, "Project lock changed after bootstrap"
    if sha_file(project_root / "framework.attestation.json") != guard.get("attestation_sha256"):
        return False, "Framework attestation changed after bootstrap"
    try:
        commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=normal"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        )
    except Exception as exc:
        return False, f"Framework git inspection failed: {type(exc).__name__}"
    if dirty:
        return False, "Framework checkout became dirty after bootstrap"
    if commit != framework.get("commit"):
        return False, "Framework HEAD changed after bootstrap"
    return True, None


def bootstrap_context(snapshot: dict[str, Any]) -> str:
    if snapshot.get("scope") == "framework":
        return (
            "Quillframe host bootstrap: scope=GENERIC_FRAMEWORK; this repository is not a fiction Project. "
            f"Framework version={snapshot.get('framework', {}).get('version')} commit={snapshot.get('framework', {}).get('commit')}. "
            "Do not store novel characters, plot, plans, manuscripts, Canon, or private user taste in this Framework repo. "
            "For Quillframe work, read HARNESS_MANIFEST.yaml plus the applicable SKILL/HARNESS contracts, then resolve exactly one primary task_mode. "
            "For a new story, create a separate consumer Project with the Project SDK/`quillframe init`; never substitute generic Claude skills for Quillframe fiction workflow authority."
        )
    if snapshot.get("scope") == "project":
        framework = snapshot.get("framework") or {}
        if snapshot.get("materialized_authority_verified"):
            return (
                f"Quillframe host bootstrap VERIFIED: project={snapshot.get('project_id')}; "
                f"Framework={framework.get('version')} commit={framework.get('commit')} bundle={framework.get('bundle_fingerprint')}. "
                f"Pinned Framework root: {snapshot.get('framework_root')}. "
                "This Project owns story facts/Canon/plans/manuscripts; Quillframe owns generic mechanisms. "
                "Primary task_mode is still UNRESOLVED: determine exactly one Quillframe mode before task execution, then create/resume the manager run and build sparse Context. "
                "Plan != Canon; Review != Accepted; Accepted != Settled. External Claude skills are not Quillframe workflow authority."
            )
        errors = "; ".join(str(x) for x in snapshot.get("errors", [])) or "exact authority verification failed"
        return (
            f"Quillframe host bootstrap BLOCKED for project={snapshot.get('project_id')}: {errors}. "
            "Read-only diagnosis is allowed, but consequential host tools are denied until the Project lock/attestation and materialized Framework agree. "
            "Do not repin automatically during ordinary production; use an explicit authorized pin/migration operation."
        )
    return "Quillframe host bootstrap could not identify a Framework or consumer Project; do not assume story or write authority."


def hook_json(
    event_name: str,
    *,
    context: str | None = None,
    decision: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    specific: dict[str, Any] = {"hookEventName": event_name}
    if context:
        specific["additionalContext"] = context
    if event_name == "PreToolUse" and decision:
        specific["permissionDecision"] = decision
        if reason:
            specific["permissionDecisionReason"] = reason
    return {"hookSpecificOutput": specific}


def put_session(event: dict[str, Any], snapshot: dict[str, Any], sid: str) -> None:
    cp = ControlPlane(os.getenv("QUILLFRAME_DB", str(ROOT / ".quillframe" / "runtime.db")))
    cp.init()
    existing = cp.get_session(sid)
    payload = dict(existing["session"]) if existing else {
        "session_id": sid,
        "resource_id": snapshot.get("project_id") or "RUNTIME-LOCAL",
        "project_id": snapshot.get("project_id"),
        "role": "manager",
        "status": "running",
        "transport": "local_agent_cli",
        "backend": "claude_code",
        "provider_session_id": str(event.get("session_id") or ""),
    }
    name = event.get("hook_event_name")
    payload["status"] = "idle" if name == "SessionEnd" else "running"
    payload["project_id"] = snapshot.get("project_id")
    payload["quillframe_bootstrap"] = {
        "scope": snapshot.get("scope"),
        "status": snapshot.get("status"),
        "authority_ready": snapshot.get("authority_ready"),
        "materialized_authority_verified": snapshot.get("materialized_authority_verified"),
        "primary_task_mode": snapshot.get("primary_task_mode"),
    }
    payload["hook_last_event"] = {
        "name": name,
        "cwd": event.get("cwd"),
        "source": event.get("source"),
        "tool_name": event.get("tool_name"),
        "tool_use_id": event.get("tool_use_id"),
    }
    cp.put_session(payload, expected_version=existing["version"] if existing else 0)


def main() -> int:
    event: dict[str, Any] = {}
    project_root: Path | None = None
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("hook input must be object")
        native = str(event.get("session_id") or "")
        if not native:
            return 0
        sid = os_session_id(native)
        cwd = Path(str(event.get("cwd") or os.getcwd()))
        project_root = find_project_root(cwd)
        name = str(event.get("hook_event_name") or "")

        snapshot = load_snapshot(project_root, sid)
        needs_full_refresh = name == "SessionStart" or snapshot is None
        if snapshot is not None and snapshot.get("scope") == "project":
            fresh, _ = lightweight_snapshot_fresh(snapshot)
            if not fresh and name in {"UserPromptSubmit", "PostToolUse"}:
                needs_full_refresh = True

        if needs_full_refresh:
            snapshot = project_mode_snapshot(project_root, event, sid) if project_root else framework_mode_snapshot(event, sid)
            save_snapshot(snapshot)

        assert snapshot is not None
        try:
            put_session(event, snapshot, sid)
        except Exception as exc:
            snapshot.setdefault("telemetry_warnings", []).append(f"ControlPlane: {type(exc).__name__}: {exc}")

        context = bootstrap_context(snapshot)
        if name == "SessionStart":
            print(json.dumps(hook_json("SessionStart", context=context), ensure_ascii=False))
            return 0
        if name == "UserPromptSubmit":
            print(json.dumps(hook_json("UserPromptSubmit", context=context), ensure_ascii=False))
            return 0
        if name == "PreToolUse":
            tool = str(event.get("tool_name") or "")
            if snapshot.get("scope") == "project":
                fresh, stale_reason = lightweight_snapshot_fresh(snapshot)
                verified = bool(snapshot.get("materialized_authority_verified")) and fresh
                if tool in CONSEQUENTIAL_TOOLS and not verified:
                    reason = stale_reason or "Quillframe Project exact Framework authority is not verified"
                    print(
                        json.dumps(
                            hook_json("PreToolUse", context=context, decision="deny", reason=reason),
                            ensure_ascii=False,
                        )
                    )
                    return 0
                if tool == "Skill":
                    print(
                        json.dumps(
                            hook_json(
                                "PreToolUse",
                                context=context,
                                decision="ask",
                                reason="External Claude Skill is not Quillframe workflow authority; explicit approval is required in a Quillframe Project.",
                            ),
                            ensure_ascii=False,
                        )
                    )
                    return 0
            print(json.dumps(hook_json("PreToolUse", context=context), ensure_ascii=False))
            return 0
        if name == "PostToolUse":
            if snapshot.get("scope") == "project":
                fresh, _ = lightweight_snapshot_fresh(snapshot)
                if not fresh and project_root:
                    snapshot = project_mode_snapshot(project_root, event, sid)
                    save_snapshot(snapshot)
                    context = bootstrap_context(snapshot)
            print(json.dumps(hook_json("PostToolUse", context=context), ensure_ascii=False))
            return 0
        return 0
    except Exception as exc:
        message = f"Quillframe Claude host guard error: {type(exc).__name__}: {exc}"
        name = str(event.get("hook_event_name") or "")
        tool = str(event.get("tool_name") or "")
        if name == "PreToolUse" and project_root is not None and tool in CONSEQUENTIAL_TOOLS:
            print(json.dumps(hook_json("PreToolUse", decision="deny", reason=message), ensure_ascii=False))
            return 0
        if name in {"SessionStart", "UserPromptSubmit", "PostToolUse"}:
            print(json.dumps(hook_json(name, context=message), ensure_ascii=False))
            return 0
        print(message, file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
