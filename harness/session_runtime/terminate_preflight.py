#!/usr/bin/env python3
"""Side-effect-free preflight for a guarded NovelForge session termination.

Termination is an operational runtime-state command only. This preflight binds
one exact durable Session before-state and its current active/latest Run, checks
that the Session belongs to the current Project, and never mutates the runtime,
runs a model, or grants Project/Canon/Framework/Settlement authority.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import resume_preflight
import session_runtime
from harness.control_plane.control_plane import ControlPlane

SCHEMA = "novelforge_session_terminate_preflight_v1"
TERMINABLE_STATUSES = {
    status for status, targets in session_runtime.ALLOWED_TRANSITIONS.items()
    if "terminated" in targets
}


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _result(
    checks: dict[str, bool],
    blockers: list[str],
    row: dict[str, Any] | None,
    run: dict[str, Any] | None,
    expected_session_version: int,
) -> dict[str, Any]:
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers and all(checks.values())
    out = {
        "schema": SCHEMA,
        "status": "READY" if ready else "BLOCKED",
        "ready": ready,
        "checks": checks,
        "blockers": blockers,
        "unresolved": [],
        "session": {
            "session_id": row["session"].get("session_id") if row else None,
            "project_id": row["session"].get("project_id") if row else None,
            "status": row["session"].get("status") if row else None,
            "expected_version": expected_session_version,
            "current_version": row.get("version") if row else None,
            "payload_hash": row.get("payload_hash") if row else None,
        } if row else None,
        "run": {
            "run_id": run.get("run_id"),
            "status": run.get("status"),
            "started_at": run.get("started_at"),
            "ended_at": run.get("ended_at"),
        } if run else None,
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    out["result_fingerprint"] = resume_preflight.fingerprint(out)
    return out


def inspect(
    *,
    db_path: Path,
    project_root: Path,
    session_id: str,
    expected_session_version: int,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    blockers: list[str] = []
    project_root = project_root.resolve()
    db_path = db_path.resolve()
    before_db_stat = db_path.stat() if db_path.exists() else None

    row = resume_preflight.read_session_row(db_path, session_id)
    checks["runtime_store_present"] = row is not None
    if row is None:
        blockers.append("session_not_found")
        return _result(checks, blockers, None, None, expected_session_version)

    session = row["session"]
    checks["session_payload_hash_valid"] = row.get("payload_hash") == resume_preflight.fingerprint(session)
    if not checks["session_payload_hash_valid"]:
        blockers.append("session_payload_hash_mismatch")

    checks["session_version_matches"] = row.get("version") == expected_session_version
    if not checks["session_version_matches"]:
        blockers.append("session_version_mismatch")

    checks["session_id_matches"] = session.get("session_id") == session_id
    if not checks["session_id_matches"]:
        blockers.append("session_identity_mismatch")

    status = session.get("status")
    checks["session_status_terminable"] = status in TERMINABLE_STATUSES
    if not checks["session_status_terminable"]:
        blockers.append("session_status_not_terminable")

    identity, identity_blockers = resume_preflight.current_project_identity(project_root)
    blockers.extend(identity_blockers)
    checks["current_project_identity_available"] = identity is not None
    current_project_id = identity.get("project_id") if identity else None
    durable_project_id = session.get("project_id")
    checks["project_identity_matches"] = bool(
        isinstance(durable_project_id, str)
        and durable_project_id
        and durable_project_id == current_project_id
    )
    if not checks["project_identity_matches"]:
        blockers.append("project_identity_mismatch")

    runs = session.get("runs") if isinstance(session.get("runs"), list) else []
    latest_run = next((item for item in reversed(runs) if isinstance(item, dict) and item.get("run_id")), None)
    active_runs = [item for item in runs if isinstance(item, dict) and item.get("status") == "running"]
    checks["at_most_one_active_run"] = len(active_runs) <= 1
    if not checks["at_most_one_active_run"]:
        blockers.append("multiple_active_runs_require_repair")

    bound_run = active_runs[0] if active_runs else latest_run
    checks["active_run_is_latest"] = not active_runs or bool(latest_run and bound_run and latest_run.get("run_id") == bound_run.get("run_id"))
    if not checks["active_run_is_latest"]:
        blockers.append("active_run_not_latest")

    if bound_run is not None:
        run_status = bound_run.get("status")
        checks["run_state_well_formed"] = (
            isinstance(bound_run.get("run_id"), str)
            and bool(bound_run.get("run_id"))
            and isinstance(run_status, str)
            and bool(run_status)
            and (run_status != "running" or bound_run.get("ended_at") is None)
        )
        if not checks["run_state_well_formed"]:
            blockers.append("run_state_invalid")
    else:
        checks["run_state_well_formed"] = True

    after_db_stat = db_path.stat() if db_path.exists() else None
    checks["read_did_not_modify_runtime_store"] = bool(
        before_db_stat
        and after_db_stat
        and before_db_stat.st_mtime_ns == after_db_stat.st_mtime_ns
        and before_db_stat.st_size == after_db_stat.st_size
    )
    if not checks["read_did_not_modify_runtime_store"]:
        blockers.append("runtime_store_changed_during_preflight")

    return _result(checks, blockers, row, bound_run, expected_session_version)


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="novelforge-terminate-preflight-") as tmp:
        root = Path(tmp)
        (root / ".novelforge").mkdir()
        framework = {
            "name": "NovelForge",
            "version": "0.8.0",
            "commit": "fixture-terminate",
            "bundle_fingerprint": "sha256:" + "a" * 64,
        }
        (root / "novelforge.toml").write_text(
            '[novelforge]\nschema="novelforge_project_v1"\n[project]\nid="BOOK-TERMINATE"\ntitle="Terminate"\nlanguage="en"\nversion="0.1.0"\nstatus="active"\n[authority]\ncanon_write="settlement_only"\nframework_write="forbidden"\n',
            encoding="utf-8",
        )
        (root / "novelforge.lock.json").write_text(json.dumps({"schema": "novelforge_lock_v1", "framework": framework}), encoding="utf-8")
        (root / "framework.attestation.json").write_text(json.dumps({"framework": framework}), encoding="utf-8")

        db = root / ".novelforge" / "runtime.db"
        cp = ControlPlane(db)
        cp.init()
        session = {
            "schema": "novelforge_agent_session_v1",
            "resource_id": "BOOK-TERMINATE",
            "project_id": "BOOK-TERMINATE",
            "session_id": "SES-TERMINATE",
            "provider_session_id": None,
            "external_session_ref": None,
            "parent_session_id": None,
            "role": "manager",
            "task_mode": "DRAFT",
            "transport": "chat_session",
            "backend": "self_test",
            "usage_class": "ordinary_chat",
            "status": "running",
            "memory_policy": "session",
            "context_policy": {"authority_snapshot": None, "context_manifest_ref": None, "allowed_artifact_refs": [], "allowed_paths": [], "forbidden_context_classes": [], "hidden_gold": "forbidden"},
            "resume_policy": "checkpoint_revalidate",
            "runs": [{"run_id": "RUN-TERMINATE", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None, "status": "running", "input_artifact_fingerprints": [], "output_artifact_fingerprints": [], "usage_class": "ordinary_chat"}],
            "checkpoints": [],
            "events": [],
            "provenance": {"runtime": "self_test", "version": "1", "durable_store": "control_plane"},
        }
        put = cp.put_session(session, expected_version=0)
        ready = inspect(db_path=db, project_root=root, session_id="SES-TERMINATE", expected_session_version=put["version"])
        stale = inspect(db_path=db, project_root=root, session_id="SES-TERMINATE", expected_session_version=put["version"] + 1)

        ended = session_runtime.terminate_run(session, "RUN-TERMINATE", detail="preflight-fixture")
        ended["session_id"] = "SES-ENDED"
        ended["project_id"] = "BOOK-TERMINATE"
        cp.put_session(ended, expected_version=0)
        terminal = inspect(db_path=db, project_root=root, session_id="SES-ENDED", expected_session_version=1)

        ok = (
            ready["ready"] is True
            and ready["run"]["run_id"] == "RUN-TERMINATE"
            and stale["ready"] is False and "session_version_mismatch" in stale["blockers"]
            and terminal["ready"] is False and "session_status_not_terminable" in terminal["blockers"]
            and ready["mutation_performed"] is False and ready["authority"] is False
        )
        dump({
            "session_terminate_preflight_contract": "PASS" if ok else "FAIL",
            "ready_case": ready["ready"],
            "stale_version_blocked": not stale["ready"],
            "terminal_session_blocked": not terminal["ready"],
            "mutation_performed": False,
            "model_execution": False,
            "authority": False,
        })
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge session terminate preflight")
    parser.add_argument("--db", default=".novelforge/runtime.db")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("--project-root", required=True)
    inspect_p.add_argument("--session-id", required=True)
    inspect_p.add_argument("--expected-session-version", required=True, type=int)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    value = inspect(
        db_path=Path(args.db),
        project_root=Path(args.project_root),
        session_id=args.session_id,
        expected_session_version=args.expected_session_version,
    )
    dump(value)
    return 0 if value["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
