#!/usr/bin/env python3
"""Unified deterministic host bootstrap for Claude Code and Codex.

This module verifies execution authority, persists the existing typed Quillframe
manager-session contract, exposes task-mode/run bootstrap state, and gates
consequential host tools. It performs no model calls and grants no Canon,
Project-settlement, or Framework-promotion authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CP_DIR = ROOT / "harness" / "control_plane"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CP_DIR) not in sys.path:
    sys.path.insert(0, str(CP_DIR))
from control_plane import ControlPlane  # noqa: E402

SCHEMA = "quillframe_host_bootstrap_v2"
HOSTS = {"claude_code", "codex"}
TASK_MODES = {
    "DESIGN-BOOK",
    "DESIGN-VOLUME",
    "PLAN-UNIT",
    "PLAN-CHAPTER",
    "DRAFT",
    "REVISE",
    "RESEARCH",
    "SETTLE",
    "AUDIT",
    "CORPUS-INGEST",
    "LEARN",
    "SYSTEM-IMPROVE",
}
FRAMEWORK_TASK_MODES = {"SYSTEM-IMPROVE", "AUDIT", "RESEARCH"}
CONSEQUENTIAL_TOOLS = {"Bash", "Edit", "Write", "apply_patch"}
SHELL_META = set(";&|><\n\r`$")
NATIVE_REVIEWER_AGENT_TYPE = "quillframe-independent-reviewer"
NATIVE_REVIEWER_PROVIDER = {
    "codex": "codex_native_subagent",
    "claude_code": "claude_native_subagent",
}


def _load_source_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_sdk() -> ModuleType:
    return _load_source_module("quillframe_project_sdk_host", ROOT / "project_sdk.py")


def session_runtime() -> ModuleType:
    return _load_source_module(
        "quillframe_session_runtime_host",
        ROOT / "harness" / "session_runtime" / "session_runtime.py",
    )


def sha_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def find_project_root(cwd: Path) -> Path | None:
    current = cwd.expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "quillframe.toml").is_file():
            return candidate
    return None


def runtime_root(project_root: Path | None) -> Path:
    return project_root.resolve() if project_root else ROOT


def control_plane_path(project_root: Path | None) -> Path:
    return runtime_root(project_root) / ".quillframe" / "runtime.db"


def control_plane(project_root: Path | None) -> ControlPlane:
    cp = ControlPlane(os.getenv("QUILLFRAME_DB", str(control_plane_path(project_root))))
    cp.init()
    return cp


def host_session_id(host: str, native_session_id: str) -> str:
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    payload = f"{host}\0{native_session_id}".encode("utf-8")
    prefix = "CLAUDE" if host == "claude_code" else "CODEX"
    return f"SES-{prefix}-" + hashlib.sha256(payload).hexdigest()[:24]


def _git_snapshot() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    commit: str | None = None
    branch: str | None = None
    dirty: bool | None = None
    try:
        commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "-C", str(ROOT), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip() or None
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
        errors.append(f"Framework git inspection failed: {type(exc).__name__}")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else None
    return {
        "name": "Quillframe",
        "version": version,
        "commit": commit,
        "branch": branch,
        "dirty": dirty,
    }, errors


def authority_snapshot(project_root: Path | None) -> dict[str, Any]:
    if project_root is None:
        framework, errors = _git_snapshot()
        return {
            "scope": "framework",
            "project_id": None,
            "project_root": None,
            "framework_root": str(ROOT),
            "framework": framework,
            "authority_ready": not errors,
            "materialized_authority_verified": False,
            "errors": errors,
            "guard": {"framework_commit": framework.get("commit")},
        }

    sdk = project_sdk()
    validation = sdk.validate_project(project_root)
    materialized = sdk.verify_materialized_framework(project_root, ROOT)
    errors = list(validation.get("errors", []))
    errors.extend(x for x in materialized.get("errors", []) if x not in errors)
    manifest = sdk.load_manifest(project_root)
    project = manifest.get("project", {}) if isinstance(manifest, dict) else {}
    verified = bool(validation.get("valid")) and bool(materialized.get("materialized_authority_verified"))
    return {
        "scope": "project",
        "project_id": project.get("id"),
        "project_root": str(project_root.resolve()),
        "framework_root": str(ROOT),
        "framework": materialized.get("framework_lock") or validation.get("framework_lock"),
        "authority_ready": bool(validation.get("authority_ready")),
        "materialized_authority_verified": verified,
        "errors": errors,
        "guard": {
            "lock_sha256": sha_file(project_root / "quillframe.lock.json"),
            "attestation_sha256": sha_file(project_root / "framework.attestation.json"),
        },
    }


def authority_cache_path(project_root: Path | None, host: str, session_id: str) -> Path:
    return runtime_root(project_root) / ".quillframe" / "hosts" / host / f"{session_id}.authority.json"


def save_authority_cache(project_root: Path | None, host: str, session_id: str, authority: dict[str, Any]) -> None:
    path = authority_cache_path(project_root, host, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(authority, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_authority_cache(project_root: Path | None, host: str, session_id: str) -> dict[str, Any] | None:
    path = authority_cache_path(project_root, host, session_id)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def lightweight_authority_fresh(authority: dict[str, Any]) -> tuple[bool, str | None]:
    stale_reason = authority.get("stale_reason")
    if isinstance(stale_reason, str) and stale_reason:
        return False, stale_reason
    if authority.get("scope") == "framework":
        try:
            commit = subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        except Exception as exc:
            return False, f"Framework git inspection failed: {type(exc).__name__}"
        expected = authority.get("guard", {}).get("framework_commit")
        if expected and commit != expected:
            return False, "Framework HEAD changed after bootstrap"
        return True, None

    project_root_raw = authority.get("project_root")
    guard = authority.get("guard")
    framework = authority.get("framework")
    if not isinstance(project_root_raw, str) or not isinstance(guard, dict) or not isinstance(framework, dict):
        return False, "authority cache is incomplete"
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
        return False, "Pinned Framework checkout became dirty after bootstrap"
    if commit != framework.get("commit"):
        return False, "Pinned Framework HEAD changed after bootstrap"
    return True, None


def _usage_class(host: str) -> str:
    return "claude_plan" if host == "claude_code" else "codex_agentic"


def authority_binding(authority: dict[str, Any]) -> dict[str, Any]:
    framework = authority.get("framework") if isinstance(authority.get("framework"), dict) else {}
    return {
        "scope": authority.get("scope"),
        "project_id": authority.get("project_id"),
        "framework_version": framework.get("version"),
        "framework_commit": framework.get("commit"),
        "bundle_fingerprint": framework.get("bundle_fingerprint"),
        "lock_sha256": authority.get("guard", {}).get("lock_sha256"),
        "attestation_sha256": authority.get("guard", {}).get("attestation_sha256"),
    }


def ensure_manager_session(
    host: str,
    native_session_id: str,
    project_root: Path | None,
    authority: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    runtime = session_runtime()
    sid = host_session_id(host, native_session_id)
    cp = control_plane(project_root)
    existing = cp.get_session(sid)
    if existing:
        session = existing["session"]
        errors = runtime.validate(session) if isinstance(session, dict) else ["session payload must be object"]
        if errors:
            raise ValueError("persisted host manager session is invalid: " + "; ".join(errors))
        if session.get("backend") != host:
            raise ValueError("persisted host manager session backend mismatch")
        if session.get("project_id") != authority.get("project_id"):
            raise ValueError("persisted host manager session Project mismatch")
        return session, int(existing["version"])

    resource_id = authority.get("project_id") or "FRAMEWORK-QUILLFRAME"
    session = runtime.new_session(
        resource_id,
        "manager",
        "local_agent_cli",
        host,
        project_id=authority.get("project_id"),
        usage_class=_usage_class(host),
        memory_policy="bounded",
        resume_policy="checkpoint_revalidate",
        provider_session_id=native_session_id,
    )
    session["session_id"] = sid
    session["context_policy"]["authority_snapshot"] = authority_binding(authority)
    errors = runtime.validate(session)
    if errors:
        raise ValueError("new host manager session is invalid: " + "; ".join(errors))
    cp.put_session(session, expected_version=0)
    return session, 1


def active_runs(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        run for run in session.get("runs", [])
        if isinstance(run, dict) and run.get("status") == "running" and run.get("ended_at") is None
    ]


def derived_state(authority: dict[str, Any], session: dict[str, Any]) -> tuple[str, list[str]]:
    runtime = session_runtime()
    errors = runtime.validate(session)
    if errors:
        return "blocked", errors
    stale_reason = authority.get("stale_reason")
    if isinstance(stale_reason, str) and stale_reason:
        return "blocked", [stale_reason]
    if authority.get("scope") == "project" and not authority.get("materialized_authority_verified"):
        return "blocked", list(authority.get("errors", [])) or ["exact Project Framework authority is not verified"]
    if authority.get("scope") == "framework" and not authority.get("authority_ready"):
        return "blocked", list(authority.get("errors", [])) or ["Framework checkout identity is unavailable"]

    mode = session.get("task_mode")
    runs = active_runs(session)
    if len(runs) > 1:
        return "blocked", ["manager session contains multiple active runs"]
    if mode and runs:
        stored_binding = session.get("context_policy", {}).get("authority_snapshot")
        if stored_binding != authority_binding(authority):
            return "blocked", ["authority changed after active run start; begin a fresh manager session/run"]
    if not mode or not runs:
        return "awaiting_task_mode", []
    if mode not in TASK_MODES:
        return "blocked", [f"invalid task_mode in persisted session: {mode}"]
    if authority.get("scope") == "framework" and mode not in FRAMEWORK_TASK_MODES:
        return "blocked", [f"task_mode {mode} cannot own Generic Framework writes"]
    return "running", []


def build_snapshot(
    host: str,
    native_session_id: str,
    project_root: Path | None,
    *,
    full_authority_refresh: bool,
    refresh_stale: bool = True,
) -> dict[str, Any]:
    sid = host_session_id(host, native_session_id)
    authority = None if full_authority_refresh else load_authority_cache(project_root, host, sid)
    if authority is not None:
        fresh, stale_reason = lightweight_authority_fresh(authority)
        if not fresh:
            if refresh_stale:
                authority = None
            else:
                authority = deepcopy(authority)
                authority["stale_reason"] = stale_reason or "authority changed after bootstrap"
    if authority is None:
        authority = authority_snapshot(project_root)
        save_authority_cache(project_root, host, sid, authority)
    session, version = ensure_manager_session(host, native_session_id, project_root, authority)
    state, state_errors = derived_state(authority, session)
    errors = list(authority.get("errors", []))
    stale_reason = authority.get("stale_reason")
    if isinstance(stale_reason, str) and stale_reason and stale_reason not in errors:
        errors.append(stale_reason)
    errors.extend(x for x in state_errors if x not in errors)
    runs = active_runs(session)
    return {
        "schema": SCHEMA,
        "host": host,
        "scope": authority.get("scope"),
        "state": state,
        "authority": authority,
        "project_id": authority.get("project_id"),
        "project_root": authority.get("project_root"),
        "framework_root": str(ROOT),
        "session_id": session["session_id"],
        "session_version": version,
        "primary_task_mode": session.get("task_mode") or "UNRESOLVED",
        "active_run_id": runs[0].get("run_id") if len(runs) == 1 else None,
        "errors": errors,
    }


def _mode_command(snapshot: dict[str, Any]) -> str:
    project_arg = f' --project "{snapshot["project_root"]}"' if snapshot.get("project_root") else ""
    prefix = "quillframe" if snapshot.get("scope") == "project" else "python -m quillframe.cli"
    return (
        f'{prefix} host-run begin --session-id {snapshot["session_id"]} '
        f'--mode <ONE_TASK_MODE>{project_arg}'
    )


def bootstrap_context(snapshot: dict[str, Any]) -> str:
    authority = snapshot.get("authority") or {}
    framework = authority.get("framework") or {}
    scope_token = "GENERIC_FRAMEWORK" if snapshot.get("scope") == "framework" else "PROJECT"
    base = (
        f"Quillframe host bootstrap v2: host={snapshot.get('host')} scope={scope_token} "
        f"state={snapshot.get('state')} QF_SESSION_ID={snapshot.get('session_id')}. "
    )
    if snapshot.get("scope") == "framework":
        base += (
            f"This is the Generic Framework, not a fiction Project. Framework version={framework.get('version')} "
            f"commit={framework.get('commit')}. Never write concrete novel characters/plot/Canon/private user taste here. "
            "For fiction intent, create a separate consumer Project outside this checkout with the strict `python -m quillframe.cli init <path> --id <ID> --title <TITLE> [--language zh-CN]` command, then restart the host from that Project. "
        )
    else:
        verified = "VERIFIED" if authority.get("materialized_authority_verified") else "UNVERIFIED"
        base += (
            f"Authority={verified}; Project={snapshot.get('project_id')}; Framework={framework.get('version')} "
            f"commit={framework.get('commit')} bundle={framework.get('bundle_fingerprint')}. "
            "Project owns story facts/Canon/plans/manuscripts; Framework owns generic mechanisms. "
        )
    if snapshot.get("state") == "blocked":
        errors = "; ".join(str(x) for x in snapshot.get("errors", [])) or "bootstrap precondition failed"
        return base + f"BLOCKED: {errors}. Read-only diagnosis only; do not repin or mutate Canon automatically."
    if snapshot.get("state") == "awaiting_task_mode":
        return base + (
            "Primary task_mode is UNRESOLVED. For work that belongs to this scope, semantically determine exactly one Quillframe mode before consequential work, then run: "
            + _mode_command(snapshot)
            + ". Do not guess multiple modes or use generic agent workflows as authority."
        )
    return base + (
        f"RUNNING: primary_task_mode={snapshot.get('primary_task_mode')} active_run_id={snapshot.get('active_run_id')}. "
        "Continue only inside that mode/run. Plan != Canon; Review != Accepted; Accepted != Settled."
    )


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


def _native_reviewer_identity(host: str, event: dict[str, Any]) -> dict[str, str]:
    """Extract lifecycle identity only from trusted host event fields."""
    if host == "claude_code":
        parent_native = event.get("session_id")
        agent_id = event.get("agent_id")
        agent_type = event.get("agent_type")
        invocation_id = event.get("invocation_id") or agent_id
    elif host == "codex":
        parent_native = event.get("parent_session_id")
        agent_id = event.get("subagent_id")
        agent_type = event.get("subagent_type")
        invocation_id = event.get("invocation_id") or agent_id
    else:
        raise ValueError(f"unsupported host: {host}")
    if not all(isinstance(value, str) and value.strip() for value in (parent_native, agent_id, agent_type, invocation_id)):
        raise ValueError("native reviewer lifecycle identity is incomplete")
    if agent_type != NATIVE_REVIEWER_AGENT_TYPE:
        raise ValueError("native reviewer agent type is not trusted")
    return {
        "parent_session_id": host_session_id(host, parent_native.strip()),
        "host_agent_id": agent_id.strip(),
        "host_invocation_id": invocation_id.strip(),
        "agent_type": agent_type,
    }


def _native_reviewer_state_path(state_root: Path, identity: dict[str, str]) -> Path:
    safe = hashlib.sha256(
        (identity["parent_session_id"] + "\0" + identity["host_agent_id"] + "\0" + identity["host_invocation_id"]).encode("utf-8")
    ).hexdigest()
    return state_root / ".quillframe" / "native-reviewers" / f"{safe}.json"


def _native_reviewer_packet_from_bytes(packet_bytes: Any) -> dict[str, Any]:
    if not isinstance(packet_bytes, str) or not packet_bytes:
        raise ValueError("native claim did not contain exact frozen packet bytes")
    try:
        packet = json.loads(packet_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError("native frozen packet is not valid JSON") from exc
    if not isinstance(packet, dict):
        raise ValueError("native frozen packet must be a JSON object")
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if packet_bytes != canonical:
        raise ValueError("native frozen packet bytes are not canonical")
    relay = _load_source_module(
        "quillframe_native_peer_chat_relay",
        ROOT / "harness" / "semantic_workers" / "peer_chat_relay.py",
    )
    errors = relay.validate_packet(packet)
    binding = packet.get("return_binding")
    if isinstance(binding, dict) and binding.get("run_reference") != packet.get("relay_nonce"):
        errors.append("packet return_binding/run_reference mismatch")
    if not isinstance(binding, dict):
        errors.append("packet return_binding is required")
    if errors:
        raise ValueError("native frozen packet invalid: " + "; ".join(errors))
    return packet


def _native_reviewer_packet_context(claim: dict[str, Any]) -> str:
    packet_bytes = claim.get("packet_bytes")
    packet = _native_reviewer_packet_from_bytes(packet_bytes)
    return json.dumps(
        {
            "schema": "quillframe_native_reviewer_context_v1",
            "instruction": "Judge only this exact frozen packet and return one JSON judgment object.",
            "frozen_packet": packet,
            "permissions": {
                "project": False,
                "filesystem": False,
                "shell": False,
                "network": False,
                "memory": False,
                "write": False,
            },
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_native_reviewer_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state_path.parent, 0o700)
    temp = state_path.with_suffix(".tmp")
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, state_path)
        os.chmod(state_path, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _remove_native_reviewer_state(state_path: Path) -> None:
    try:
        state_path.unlink()
    except FileNotFoundError:
        pass
    try:
        state_path.parent.rmdir()
    except (FileNotFoundError, OSError):
        pass


def _native_reviewer_judgment(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("last_assistant_message") if isinstance(event.get("last_assistant_message"), str) else event.get("response")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("native_reviewer_output_missing")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("native_reviewer_output_invalid_json") from exc
    if not isinstance(value, dict):
        raise ValueError("native_reviewer_output_not_object")
    return value


def _native_reviewer_runtime(runtime: Any | None) -> Any:
    if runtime is not None:
        return runtime
    from studio.host_bridge import production_runtime
    return production_runtime()


def native_reviewer_hook(
    host: str,
    event: dict[str, Any],
    *,
    project_id: str,
    state_root: Path,
    runtime: Any | None = None,
) -> dict[str, Any]:
    """Run native reviewer lifecycle; host attestation is not OS isolation."""
    identity = _native_reviewer_identity(host, event)
    runtime = _native_reviewer_runtime(runtime)
    event_name = str(event.get("hook_event_name") or "")
    state_path = _native_reviewer_state_path(state_root, identity)
    if event_name == "SubagentStart":
        claim = runtime.claim_independent_dispatch(
            project_id,
            provider=NATIVE_REVIEWER_PROVIDER[host],
            parent_session_id=identity["parent_session_id"],
            agent_type=identity["agent_type"],
            host_agent_id=identity["host_agent_id"],
            host_invocation_id=identity["host_invocation_id"],
        )
        reviewer_session_id = claim.get("reviewer_session_id")
        if not isinstance(reviewer_session_id, str) or not reviewer_session_id:
            raise ValueError("native claim did not create a reviewer session")
        if reviewer_session_id == identity["parent_session_id"]:
            raise ValueError("native reviewer session must differ from parent session")
        context = _native_reviewer_packet_context(claim)
        state = {
            "schema": "quillframe_native_reviewer_hook_state_v3",
            "lease_id": claim.get("lease_id"),
            "provider": claim.get("provider"),
            "reviewer_session_id": reviewer_session_id,
        }
        _write_native_reviewer_state(state_path, state)
        return hook_json(event_name, context=context)
    if event_name == "PreToolUse":
        return hook_json(
            event_name,
            decision="deny",
            reason="Quillframe native reviewer is JSON-only and has no tool, filesystem, network, memory, or write access.",
        )
    if event_name == "SubagentStop":
        if not state_path.is_file():
            raise ValueError("native_reviewer_state_missing")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        try:
            judgment = _native_reviewer_judgment(event)
        except ValueError as exc:
            runtime.fail_independent_dispatch(
                project_id,
                lease_id=state["lease_id"],
                reviewer_session_id=state["reviewer_session_id"],
                host_agent_id=identity["host_agent_id"],
                host_invocation_id=identity["host_invocation_id"],
                error={"code": str(exc), "kind": "infrastructure"},
            )
            _remove_native_reviewer_state(state_path)
            return hook_json(event_name)
        runtime.complete_independent_judgment(
            project_id,
            lease_id=state["lease_id"],
            reviewer_session_id=state["reviewer_session_id"],
            host_agent_id=identity["host_agent_id"],
            host_invocation_id=identity["host_invocation_id"],
            judgment=judgment,
        )
        _remove_native_reviewer_state(state_path)
        return hook_json(event_name)
    return hook_json(event_name)


def normalize_tool(host: str, tool_name: str) -> str:
    if host == "codex" and tool_name == "apply_patch":
        return "apply_patch"
    return tool_name


def _command_tokens(command: str) -> list[str] | None:
    if not command or any(char in command for char in SHELL_META):
        return None
    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return None


def _split_quillframe_command(tokens: list[str], subcommand: str) -> list[str] | None:
    if tokens[:2] == ["quillframe", subcommand]:
        return tokens[2:]
    if tokens[:4] in (
        ["python", "-m", "quillframe.cli", subcommand],
        ["python3", "-m", "quillframe.cli", subcommand],
    ):
        return tokens[4:]
    return None


def is_bootstrap_command(command: str, expected_session_id: str) -> bool:
    tokens = _command_tokens(command)
    if not tokens:
        return False
    rest = _split_quillframe_command(tokens, "host-run")
    if rest is None or not rest or rest[0] not in {"status", "begin"}:
        return False
    action = rest[0]
    args = rest[1:]
    allowed_flags = {"--session-id", "--project"} | ({"--mode"} if action == "begin" else set())
    parsed: dict[str, str] = {}
    index = 0
    while index < len(args):
        flag = args[index]
        if flag not in allowed_flags or flag in parsed or index + 1 >= len(args):
            return False
        parsed[flag] = args[index + 1]
        index += 2
    if parsed.get("--session-id") != expected_session_id:
        return False
    if action == "begin":
        return parsed.get("--mode") in TASK_MODES
    return "--mode" not in parsed


def is_project_init_command(command: str, cwd: Path) -> bool:
    """Allow only the narrow consumer-project creation escape from Framework scope.

    This does not approve the shell operation; returning True only lets the host's
    normal permission layer consider it. `project_sdk.init_project` still enforces
    clean exact Framework pinning and that the target lives outside the Framework.
    """
    tokens = _command_tokens(command)
    if not tokens:
        return False
    rest = _split_quillframe_command(tokens, "init")
    if rest is None or not rest or rest[0].startswith("-"):
        return False
    target_raw = rest[0]
    args = rest[1:]
    allowed_flags = {"--id", "--title", "--language", "--framework-version"}
    parsed: dict[str, str] = {}
    index = 0
    while index < len(args):
        flag = args[index]
        if flag not in allowed_flags or flag in parsed or index + 1 >= len(args):
            return False
        parsed[flag] = args[index + 1]
        index += 2
    if not parsed.get("--id") or not parsed.get("--title"):
        return False
    target = Path(target_raw).expanduser()
    if not target.is_absolute():
        target = cwd / target
    target = target.resolve()
    framework = ROOT.resolve()
    return target != framework and framework not in target.parents


def _tool_command(event: dict[str, Any]) -> str:
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    value = tool_input.get("command")
    return value if isinstance(value, str) else ""


def pretool_decision(snapshot: dict[str, Any], event: dict[str, Any]) -> tuple[str | None, str | None]:
    tool = normalize_tool(snapshot["host"], str(event.get("tool_name") or ""))
    if tool == "Skill":
        return "deny", "External host Skill routing is not Quillframe workflow authority."
    if tool not in CONSEQUENTIAL_TOOLS:
        return None, None

    authority = snapshot.get("authority") or {}
    fresh, stale_reason = lightweight_authority_fresh(authority)
    if not fresh:
        return "deny", stale_reason or "Quillframe authority changed after bootstrap"
    if snapshot.get("state") == "blocked":
        return "deny", "; ".join(snapshot.get("errors", [])) or "Quillframe bootstrap is blocked"
    if snapshot.get("state") != "running":
        if tool == "Bash":
            command = _tool_command(event)
            if is_bootstrap_command(command, snapshot["session_id"]):
                return None, None
            if snapshot.get("scope") == "framework":
                cwd = Path(str(event.get("cwd") or ROOT))
                if is_project_init_command(command, cwd):
                    return None, None
        return "deny", (
            "Quillframe primary task_mode/run is not active. Determine exactly one task mode and execute the injected host-run begin command first; fiction intent from the Generic Framework may only use the strict consumer-project init command."
        )
    return None, None


def begin_run(project_root: Path | None, session_id: str, mode: str) -> dict[str, Any]:
    if mode not in TASK_MODES:
        raise ValueError(f"unsupported Quillframe task_mode: {mode}")
    authority = authority_snapshot(project_root)
    if project_root is not None and not authority.get("materialized_authority_verified"):
        raise ValueError("exact Project Framework authority is not verified: " + "; ".join(authority.get("errors", [])))
    if project_root is None and not authority.get("authority_ready"):
        raise ValueError("Framework checkout authority is unavailable")
    if project_root is None and mode not in FRAMEWORK_TASK_MODES:
        raise ValueError(f"task_mode {mode} cannot own Generic Framework writes")

    runtime = session_runtime()
    cp = control_plane(project_root)
    existing = cp.get_session(session_id)
    if not existing:
        raise ValueError("unknown Quillframe host session; start the host and allow SessionStart bootstrap first")
    session = existing["session"]
    errors = runtime.validate(session) if isinstance(session, dict) else ["session payload must be object"]
    if errors:
        raise ValueError("invalid persisted manager session: " + "; ".join(errors))
    if session.get("project_id") != authority.get("project_id"):
        raise ValueError("session Project does not match current bootstrap target")

    active = active_runs(session)
    if active:
        if len(active) == 1 and session.get("task_mode") == mode:
            return {
                "schema": "quillframe_host_run_result_v1",
                "state": "running",
                "duplicate": True,
                "session_id": session_id,
                "task_mode": mode,
                "run_id": active[0]["run_id"],
            }
        raise ValueError("manager session already has an active run/task_mode; explicit completion/termination is required before switching")
    if session.get("task_mode") not in (None, mode):
        raise ValueError("manager session already resolved a different task_mode")

    updated = deepcopy(session)
    updated["task_mode"] = mode
    updated["context_policy"]["authority_snapshot"] = authority_binding(authority)
    run_id = "RUN-HOST-" + uuid.uuid4().hex
    inputs = [
        value for value in (
            authority.get("guard", {}).get("lock_sha256"),
            authority.get("guard", {}).get("attestation_sha256"),
            (authority.get("framework") or {}).get("bundle_fingerprint"),
        ) if isinstance(value, str)
    ]
    updated = runtime.start_run(updated, run_id, list(dict.fromkeys(inputs)))
    validation = runtime.validate(updated)
    if validation:
        raise ValueError("manager session invalid after run start: " + "; ".join(validation))
    cp.put_session(updated, expected_version=int(existing["version"]))
    return {
        "schema": "quillframe_host_run_result_v1",
        "state": "running",
        "duplicate": False,
        "session_id": session_id,
        "task_mode": mode,
        "run_id": run_id,
        "authority": authority_binding(authority),
    }


def run_status(project_root: Path | None, session_id: str) -> dict[str, Any]:
    cp = control_plane(project_root)
    existing = cp.get_session(session_id)
    if not existing:
        raise ValueError("unknown Quillframe host session")
    session = existing["session"]
    authority = authority_snapshot(project_root)
    state, errors = derived_state(authority, session)
    active = active_runs(session)
    return {
        "schema": "quillframe_host_run_status_v1",
        "state": state,
        "session_id": session_id,
        "task_mode": session.get("task_mode") or "UNRESOLVED",
        "active_run_id": active[0].get("run_id") if len(active) == 1 else None,
        "authority_ready": bool(authority.get("materialized_authority_verified")) if project_root else bool(authority.get("authority_ready")),
        "errors": errors or authority.get("errors", []),
    }


def main_for_host(host: str) -> int:
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    event: dict[str, Any] = {}
    project_root: Path | None = None
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("hook input must be object")
        cwd = Path(str(event.get("cwd") or os.getcwd()))
        project_root = find_project_root(cwd)
        name = str(event.get("hook_event_name") or "")
        reviewer_type = event.get("agent_type") if host == "claude_code" else event.get("subagent_type")
        native = str(
            (event.get("session_id") if host == "claude_code" else event.get("parent_session_id"))
            or event.get("session_id")
            or ""
        )
        if not native and reviewer_type != NATIVE_REVIEWER_AGENT_TYPE:
            return 0
        if reviewer_type == NATIVE_REVIEWER_AGENT_TYPE:
            if project_root is None:
                raise ValueError("native reviewer requires a mapped Project root")
            manifest = project_sdk().load_manifest(project_root)
            project_id = str((manifest.get("project") or {}).get("id") or event.get("project_id") or "")
            if not project_id:
                raise ValueError("native reviewer Project identity is missing")
            output = native_reviewer_hook(
                host,
                event,
                project_id=project_id,
                state_root=project_root,
            )
            print(json.dumps(output, ensure_ascii=False))
            return 0
        snapshot = build_snapshot(
            host,
            native,
            project_root,
            full_authority_refresh=name == "SessionStart",
            refresh_stale=name != "PreToolUse",
        )
        if name == "SessionEnd":
            return 0
        context = bootstrap_context(snapshot)
        if name in {"SessionStart", "UserPromptSubmit", "PostToolUse"}:
            print(json.dumps(hook_json(name, context=context), ensure_ascii=False))
            return 0
        if name == "PreToolUse":
            decision, reason = pretool_decision(snapshot, event)
            print(json.dumps(hook_json("PreToolUse", context=context, decision=decision, reason=reason), ensure_ascii=False))
            return 0
        return 0
    except Exception as exc:
        message = f"Quillframe {host} host bootstrap error: {type(exc).__name__}: {exc}"
        name = str(event.get("hook_event_name") or "")
        tool = str(event.get("tool_name") or "")
        normalized = normalize_tool(host, tool)
        if name == "PreToolUse" and (normalized in CONSEQUENTIAL_TOOLS or normalized == "Skill"):
            print(json.dumps(hook_json("PreToolUse", decision="deny", reason=message), ensure_ascii=False))
            return 0
        if name in {"SessionStart", "UserPromptSubmit", "PostToolUse"}:
            print(json.dumps(hook_json(name, context=message), ensure_ascii=False))
            return 0
        print(message, file=sys.stderr)
        return 0
