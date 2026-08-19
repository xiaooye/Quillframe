#!/usr/bin/env python3
"""Deterministic, side-effect-free resume preflight for Quillframe sessions.

This module answers one question only: does the currently durable session and
checkpoint have enough still-valid evidence to be eligible for a future resume
command? It never resumes a session, creates a run, consumes a result, invokes a
model, or grants Project/Framework/Canon authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "quillframe_session_resume_preflight_v1"
AUTHORITY_EVIDENCE_SCHEMA = "quillframe_resume_authority_evidence_v1"
CAPABILITY_SCHEMA = "quillframe_host_capabilities_v1"
RESUMABLE_STATUSES = {"idle", "awaiting_user", "awaiting_external", "failed"}
FRAMEWORK_KEYS = ("version", "commit", "bundle_fingerprint")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fingerprint(value: Any) -> str:
    return sha_bytes(canonical(value).encode("utf-8"))


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def safe_project_file(project_root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        raise ValueError("artifact path must be a non-empty project-relative path")
    root = project_root.resolve()
    path = (root / rel).resolve()
    if path != root and root not in path.parents:
        raise ValueError("artifact path escapes project root")
    return path


def read_session_row(db_path: Path, session_id: str) -> dict[str, Any] | None:
    if not db_path.exists() or not db_path.is_file():
        return None
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT payload_json,payload_hash,version,updated_at FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    payload = json.loads(row["payload_json"])
    if not isinstance(payload, dict):
        raise ValueError("durable session payload must be an object")
    return {
        "session": payload,
        "payload_hash": row["payload_hash"],
        "version": int(row["version"]),
        "updated_at": row["updated_at"],
    }


def current_project_identity(project_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    manifest_path = project_root / "quillframe.toml"
    lock_path = project_root / "quillframe.lock.json"
    attestation_path = project_root / "framework.attestation.json"

    if not manifest_path.exists():
        return None, ["project_manifest_missing"]
    try:
        with manifest_path.open("rb") as handle:
            manifest = tomllib.load(handle)
    except Exception:
        return None, ["project_manifest_invalid"]
    project = manifest.get("project") if isinstance(manifest.get("project"), dict) else {}
    project_id = project.get("id")
    if not isinstance(project_id, str) or not project_id:
        return None, ["project_identity_invalid"]
    authority = manifest.get("authority") if isinstance(manifest.get("authority"), dict) else {}

    if not lock_path.exists():
        return None, ["project_lock_missing"]
    try:
        lock = load_object(lock_path)
    except Exception:
        return None, ["project_lock_invalid"]
    if lock.get("schema") != "quillframe_lock_v1":
        blockers.append("project_lock_schema_invalid")
    framework = lock.get("framework")
    if (
        not isinstance(framework, dict)
        or framework.get("name") != "Quillframe"
        or any(not isinstance(framework.get(k), str) or not framework.get(k) for k in FRAMEWORK_KEYS)
    ):
        return None, [*blockers, "project_framework_identity_invalid"]
    current_framework = {k: framework[k] for k in FRAMEWORK_KEYS}

    if not attestation_path.exists():
        blockers.append("framework_attestation_missing")
    else:
        try:
            attestation = load_object(attestation_path)
            attested_framework = attestation.get("framework") if isinstance(attestation.get("framework"), dict) else attestation
            if any(attested_framework.get(k) != current_framework[k] for k in FRAMEWORK_KEYS):
                blockers.append("framework_attestation_mismatch")
        except Exception:
            blockers.append("framework_attestation_invalid")

    return {
        "project_id": project_id,
        "project_authority_fingerprint": fingerprint(authority),
        "framework": current_framework,
    }, blockers


def probe_local_capabilities(project_root: Path) -> dict[str, Any] | None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "quillframe.py"), "capabilities", "probe-local"],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or value.get("schema") != CAPABILITY_SCHEMA or not isinstance(value.get("capabilities"), dict):
        return None
    return value


def inspect(
    *,
    db_path: Path,
    project_root: Path,
    session_id: str,
    checkpoint_id: str,
    expected_session_version: int,
    authority_evidence_path: Path,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    blockers: list[str] = []
    unresolved: list[str] = []

    project_root = project_root.resolve()
    before_db_stat = db_path.stat() if db_path.exists() else None
    row = read_session_row(db_path, session_id)
    checks["runtime_store_present"] = row is not None
    if row is None:
        blockers.append("session_not_found")
        return _result(checks, blockers, unresolved, None, None, expected_session_version)

    session = row["session"]
    current_version = row["version"]
    checks["session_payload_hash_valid"] = row.get("payload_hash") == fingerprint(session)
    if not checks["session_payload_hash_valid"]:
        blockers.append("session_payload_hash_mismatch")

    checks["session_version_matches"] = current_version == expected_session_version
    if not checks["session_version_matches"]:
        blockers.append("session_version_mismatch")

    checks["session_id_matches"] = session.get("session_id") == session_id
    if not checks["session_id_matches"]:
        blockers.append("session_identity_mismatch")

    status = session.get("status")
    checks["session_status_resumable"] = status in RESUMABLE_STATUSES
    if not checks["session_status_resumable"]:
        blockers.append("session_status_not_resumable")

    policy = session.get("resume_policy")
    checks["resume_policy_allows_resume"] = policy in {"same_session", "same_fingerprint", "checkpoint_revalidate"}
    if not checks["resume_policy_allows_resume"]:
        blockers.append("resume_policy_forbidden")

    if policy == "same_session":
        provider_bound = bool(session.get("provider_session_id") or session.get("external_session_ref"))
        checks["same_session_binding_present"] = provider_bound
        if not provider_bound:
            blockers.append("same_session_binding_missing")

    checkpoints = session.get("checkpoints") if isinstance(session.get("checkpoints"), list) else []
    checkpoint = next((item for item in checkpoints if isinstance(item, dict) and item.get("checkpoint_id") == checkpoint_id), None)
    checks["checkpoint_found"] = checkpoint is not None
    if checkpoint is None:
        blockers.append("checkpoint_not_found")
        return _result(checks, blockers, unresolved, row, None, expected_session_version)

    latest_checkpoint = next((item for item in reversed(checkpoints) if isinstance(item, dict) and item.get("checkpoint_id")), None)
    checks["checkpoint_is_latest"] = bool(latest_checkpoint and latest_checkpoint.get("checkpoint_id") == checkpoint_id)
    if not checks["checkpoint_is_latest"]:
        blockers.append("checkpoint_not_latest_use_replay_contract")

    checks["checkpoint_policy_matches"] = checkpoint.get("resume_policy") == policy
    if not checks["checkpoint_policy_matches"]:
        blockers.append("checkpoint_resume_policy_mismatch")

    run_id = checkpoint.get("run_id")
    runs = session.get("runs") if isinstance(session.get("runs"), list) else []
    checks["checkpoint_run_exists"] = isinstance(run_id, str) and any(
        isinstance(item, dict) and item.get("run_id") == run_id for item in runs
    )
    if not checks["checkpoint_run_exists"]:
        blockers.append("checkpoint_run_missing")

    pending_gate = checkpoint.get("pending_gate")
    pending_handoff = checkpoint.get("pending_handoff")
    checks["no_pending_gate"] = not bool(pending_gate)
    checks["no_pending_handoff"] = not bool(pending_handoff)
    if pending_gate:
        blockers.append("pending_gate_requires_fresh_validation")
    if pending_handoff:
        blockers.append("pending_handoff_requires_binding")

    try:
        evidence = load_object(authority_evidence_path)
    except Exception:
        evidence = {}
        blockers.append("authority_evidence_invalid")
    checks["authority_evidence_schema"] = evidence.get("schema") == AUTHORITY_EVIDENCE_SCHEMA
    if not checks["authority_evidence_schema"]:
        blockers.append("authority_evidence_schema_invalid")

    current_identity, identity_blockers = current_project_identity(project_root)
    blockers.extend(identity_blockers)
    checks["current_project_identity_available"] = current_identity is not None

    current_framework = current_identity.get("framework") if current_identity else None
    expected_framework = evidence.get("framework") if isinstance(evidence.get("framework"), dict) else None
    checks["framework_identity_matches"] = bool(
        current_framework
        and expected_framework
        and all(expected_framework.get(k) == current_framework.get(k) for k in FRAMEWORK_KEYS)
    )
    if not checks["framework_identity_matches"]:
        blockers.append("framework_identity_changed_or_unproven")

    expected_project_id = evidence.get("project_id")
    current_project_id = current_identity.get("project_id") if current_identity else None
    checks["project_identity_matches"] = bool(
        isinstance(expected_project_id, str)
        and expected_project_id
        and expected_project_id == session.get("project_id")
        and expected_project_id == current_project_id
    )
    if not checks["project_identity_matches"]:
        blockers.append("project_identity_mismatch")

    expected_authority_fp = evidence.get("project_authority_fingerprint")
    current_authority_fp = current_identity.get("project_authority_fingerprint") if current_identity else None
    checks["project_authority_matches"] = bool(
        isinstance(expected_authority_fp, str)
        and expected_authority_fp.startswith("sha256:")
        and expected_authority_fp == current_authority_fp
    )
    if not checks["project_authority_matches"]:
        blockers.append("project_authority_changed_or_unproven")

    expected_fingerprints = checkpoint.get("artifact_fingerprints") if isinstance(checkpoint.get("artifact_fingerprints"), list) else []
    bindings = evidence.get("artifact_bindings") if isinstance(evidence.get("artifact_bindings"), list) else []
    verified_fingerprints: set[str] = set()
    artifact_binding_errors = False
    for binding in bindings:
        if not isinstance(binding, dict) or not isinstance(binding.get("path"), str) or not isinstance(binding.get("fingerprint"), str):
            artifact_binding_errors = True
            continue
        try:
            path = safe_project_file(project_root, binding["path"])
        except ValueError:
            artifact_binding_errors = True
            continue
        if not path.exists() or not path.is_file():
            artifact_binding_errors = True
            continue
        actual = sha_bytes(path.read_bytes())
        if actual != binding["fingerprint"]:
            artifact_binding_errors = True
            continue
        verified_fingerprints.add(actual)
    checks["artifact_bindings_valid"] = not artifact_binding_errors
    checks["checkpoint_artifacts_verified"] = all(isinstance(fp, str) and fp in verified_fingerprints for fp in expected_fingerprints)
    if artifact_binding_errors:
        blockers.append("artifact_binding_invalid")
    if not checks["checkpoint_artifacts_verified"]:
        blockers.append("checkpoint_artifact_fingerprint_unverified")

    raw_required = evidence.get("required_capabilities", [])
    required_capabilities = raw_required if isinstance(raw_required, list) else []
    checks["required_capability_identifiers_valid"] = isinstance(raw_required, list) and all(
        isinstance(item, str) and item for item in required_capabilities
    )
    if not checks["required_capability_identifiers_valid"]:
        blockers.append("required_capability_evidence_invalid")
    if required_capabilities and checks["required_capability_identifiers_valid"]:
        capability_manifest = probe_local_capabilities(project_root)
        checks["local_capability_probe_available"] = capability_manifest is not None
        if capability_manifest is None:
            blockers.append("local_capability_probe_failed")
        else:
            capabilities = capability_manifest["capabilities"]
            missing_capabilities = [
                name for name in required_capabilities
                if not isinstance(capabilities.get(name), dict) or capabilities[name].get("available") is not True
            ]
            checks["required_capabilities_available"] = not missing_capabilities
            if missing_capabilities:
                blockers.append("required_capability_unavailable")
                unresolved.extend(f"capability:{name}" for name in missing_capabilities)
    else:
        checks["required_capabilities_available"] = not required_capabilities

    approval_refs = evidence.get("approval_refs") if isinstance(evidence.get("approval_refs"), list) else []
    checks["approval_evidence_well_formed"] = all(isinstance(item, str) and item for item in approval_refs)
    if not checks["approval_evidence_well_formed"]:
        blockers.append("approval_evidence_invalid")

    after_db_stat = db_path.stat() if db_path.exists() else None
    checks["read_did_not_modify_runtime_store"] = bool(
        before_db_stat
        and after_db_stat
        and before_db_stat.st_mtime_ns == after_db_stat.st_mtime_ns
        and before_db_stat.st_size == after_db_stat.st_size
    )
    if not checks["read_did_not_modify_runtime_store"]:
        blockers.append("runtime_store_changed_during_preflight")

    return _result(checks, blockers, unresolved, row, checkpoint, expected_session_version)


def _result(
    checks: dict[str, bool],
    blockers: list[str],
    unresolved: list[str],
    row: dict[str, Any] | None,
    checkpoint: dict[str, Any] | None,
    expected_session_version: int,
) -> dict[str, Any]:
    blockers = list(dict.fromkeys(blockers))
    unresolved = list(dict.fromkeys(unresolved))
    ready = not blockers and not unresolved and all(checks.values())
    return {
        "schema": SCHEMA,
        "status": "READY" if ready else "BLOCKED",
        "ready": ready,
        "checks": checks,
        "blockers": blockers,
        "unresolved": unresolved,
        "session": {
            "session_id": row["session"].get("session_id") if row else None,
            "status": row["session"].get("status") if row else None,
            "resume_policy": row["session"].get("resume_policy") if row else None,
            "expected_version": expected_session_version,
            "current_version": row.get("version") if row else None,
            "payload_hash": row.get("payload_hash") if row else None,
        },
        "checkpoint": {
            "checkpoint_id": checkpoint.get("checkpoint_id") if checkpoint else None,
            "run_id": checkpoint.get("run_id") if checkpoint else None,
            "workflow_step": checkpoint.get("workflow_step") if checkpoint else None,
        },
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }


def self_test() -> int:
    sys.path.insert(0, str(ROOT / "harness" / "control_plane"))
    from control_plane import ControlPlane  # type: ignore

    with tempfile.TemporaryDirectory(prefix="quillframe-resume-preflight-") as tmp:
        root = Path(tmp)
        (root / ".quillframe").mkdir()
        artifact = root / "draft.txt"
        artifact.write_text("frozen candidate\n", encoding="utf-8")
        artifact_fp = sha_bytes(artifact.read_bytes())
        authority = {"canon_write": "settlement_only", "framework_write": "forbidden"}
        authority_fp = fingerprint(authority)
        framework = {
            "name": "Quillframe",
            "version": "0.9.1",
            "commit": "fixture-commit",
            "bundle_fingerprint": "sha256:" + "a" * 64,
        }
        (root / "quillframe.toml").write_text(
            '[quillframe]\nschema="quillframe_project_v1"\n[project]\nid="BOOK-SELFTEST"\ntitle="Self Test"\nlanguage="en"\nversion="0.1.0"\nstatus="active"\n[authority]\ncanon_write="settlement_only"\nframework_write="forbidden"\n',
            encoding="utf-8",
        )
        (root / "quillframe.lock.json").write_text(json.dumps({"schema": "quillframe_lock_v1", "framework": framework}), encoding="utf-8")
        (root / "framework.attestation.json").write_text(json.dumps({"framework": framework}), encoding="utf-8")
        evidence_path = root / "resume-authority.json"
        evidence_path.write_text(json.dumps({
            "schema": AUTHORITY_EVIDENCE_SCHEMA,
            "project_id": "BOOK-SELFTEST",
            "project_authority_fingerprint": authority_fp,
            "framework": {k: framework[k] for k in FRAMEWORK_KEYS},
            "artifact_bindings": [{"path": "draft.txt", "fingerprint": artifact_fp}],
            "required_capabilities": [],
            "approval_refs": [],
        }), encoding="utf-8")

        db = root / ".quillframe" / "runtime.db"
        cp = ControlPlane(db)
        cp.init()
        session = {
            "schema": "quillframe_agent_session_v1",
            "resource_id": "BOOK-SELFTEST",
            "project_id": "BOOK-SELFTEST",
            "session_id": "SES-PREFLIGHT",
            "provider_session_id": None,
            "external_session_ref": None,
            "parent_session_id": None,
            "role": "manager",
            "task_mode": "DRAFT",
            "transport": "chat_session",
            "backend": "self_test",
            "usage_class": "ordinary_chat",
            "status": "idle",
            "memory_policy": "session",
            "context_policy": {"authority_snapshot": None, "context_manifest_ref": None, "allowed_artifact_refs": [], "allowed_paths": [], "forbidden_context_classes": [], "hidden_gold": "forbidden"},
            "resume_policy": "checkpoint_revalidate",
            "runs": [{"run_id": "RUN-PREFLIGHT", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None, "status": "running", "input_artifact_fingerprints": [artifact_fp], "output_artifact_fingerprints": [], "usage_class": "ordinary_chat"}],
            "checkpoints": [{"checkpoint_id": "CP-PREFLIGHT", "run_id": "RUN-PREFLIGHT", "workflow_step": "context-frozen", "artifact_fingerprints": [artifact_fp], "pending_gate": None, "pending_handoff": None, "resume_policy": "checkpoint_revalidate", "created_at": "2026-01-01T00:00:00+00:00"}],
            "events": [],
            "provenance": {"runtime": "self_test", "version": "1", "durable_store": "control_plane"},
        }
        put = cp.put_session(session, expected_version=0)
        good = inspect(db_path=db, project_root=root, session_id="SES-PREFLIGHT", checkpoint_id="CP-PREFLIGHT", expected_session_version=put["version"], authority_evidence_path=evidence_path)
        stale_version = inspect(db_path=db, project_root=root, session_id="SES-PREFLIGHT", checkpoint_id="CP-PREFLIGHT", expected_session_version=999, authority_evidence_path=evidence_path)
        artifact.write_text("changed\n", encoding="utf-8")
        stale_artifact = inspect(db_path=db, project_root=root, session_id="SES-PREFLIGHT", checkpoint_id="CP-PREFLIGHT", expected_session_version=put["version"], authority_evidence_path=evidence_path)
        artifact.write_text("frozen candidate\n", encoding="utf-8")
        changed_manifest = root / "quillframe.toml"
        changed_manifest.write_text(changed_manifest.read_text(encoding="utf-8").replace('id="BOOK-SELFTEST"', 'id="BOOK-OTHER"'), encoding="utf-8")
        wrong_project = inspect(db_path=db, project_root=root, session_id="SES-PREFLIGHT", checkpoint_id="CP-PREFLIGHT", expected_session_version=put["version"], authority_evidence_path=evidence_path)
        changed_manifest.write_text(changed_manifest.read_text(encoding="utf-8").replace('id="BOOK-OTHER"', 'id="BOOK-SELFTEST"'), encoding="utf-8")

        local_capability_evidence = load_object(evidence_path)
        local_capability_evidence["required_capabilities"] = ["subprocess"]
        local_capability_path = root / "resume-local-capability.json"
        local_capability_path.write_text(json.dumps(local_capability_evidence), encoding="utf-8")
        local_capability_ready = inspect(db_path=db, project_root=root, session_id="SES-PREFLIGHT", checkpoint_id="CP-PREFLIGHT", expected_session_version=put["version"], authority_evidence_path=local_capability_path)

        unavailable_capability_evidence = load_object(evidence_path)
        unavailable_capability_evidence["required_capabilities"] = ["semantic_model"]
        unavailable_capability_path = root / "resume-unavailable-capability.json"
        unavailable_capability_path.write_text(json.dumps(unavailable_capability_evidence), encoding="utf-8")
        unavailable_capability_blocked = inspect(db_path=db, project_root=root, session_id="SES-PREFLIGHT", checkpoint_id="CP-PREFLIGHT", expected_session_version=put["version"], authority_evidence_path=unavailable_capability_path)

        missing_db = root / "missing" / "runtime.db"
        missing = inspect(db_path=missing_db, project_root=root, session_id="SES-X", checkpoint_id="CP-X", expected_session_version=1, authority_evidence_path=evidence_path)
        ok = (
            good["ready"] is True
            and stale_version["ready"] is False and "session_version_mismatch" in stale_version["blockers"]
            and stale_artifact["ready"] is False and "checkpoint_artifact_fingerprint_unverified" in stale_artifact["blockers"]
            and wrong_project["ready"] is False and "project_identity_mismatch" in wrong_project["blockers"]
            and local_capability_ready["ready"] is True
            and unavailable_capability_blocked["ready"] is False and "required_capability_unavailable" in unavailable_capability_blocked["blockers"]
            and missing["ready"] is False and not missing_db.exists() and not missing_db.parent.exists()
            and good["mutation_performed"] is False and good["authority"] is False
        )
        dump({
            "resume_preflight_contract": "PASS" if ok else "FAIL",
            "ready_case": good["ready"],
            "stale_version_blocked": not stale_version["ready"],
            "stale_artifact_blocked": not stale_artifact["ready"],
            "wrong_project_blocked": not wrong_project["ready"],
            "locally_provable_capability_ready": local_capability_ready["ready"],
            "unavailable_capability_blocked": not unavailable_capability_blocked["ready"],
            "missing_store_side_effect_free": not missing_db.exists() and not missing_db.parent.exists(),
            "mutation_performed": False,
            "authority": False,
            "model_execution": False,
        })
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe deterministic session resume preflight")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("--db", required=True)
    inspect_p.add_argument("--project-root", required=True)
    inspect_p.add_argument("--session-id", required=True)
    inspect_p.add_argument("--checkpoint-id", required=True)
    inspect_p.add_argument("--expected-session-version", type=int, required=True)
    inspect_p.add_argument("--authority-evidence", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    result = inspect(
        db_path=Path(args.db),
        project_root=Path(args.project_root),
        session_id=args.session_id,
        checkpoint_id=args.checkpoint_id,
        expected_session_version=args.expected_session_version,
        authority_evidence_path=Path(args.authority_evidence),
    )
    dump(result)
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
