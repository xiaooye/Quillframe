#!/usr/bin/env python3
"""Validate typed Quillframe session-resume command candidates.

This validator binds a proposed resume intent to one READY preflight, one exact
durable before-state, and one authority-evidence fingerprint. Validation itself
performs no runtime mutation and grants no authority; the separately exposed
runtime command executor must revalidate the candidate again at execute time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

COMMAND_SCHEMA = "quillframe_session_resume_command_v1"
VALIDATION_SCHEMA = "quillframe_session_resume_command_validation_v1"
PREFLIGHT_SCHEMA = "quillframe_session_resume_preflight_v1"
AUTHORITY_EVIDENCE_SCHEMA = "quillframe_resume_authority_evidence_v1"
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

TOP_FIELDS = {
    "schema",
    "command_id",
    "action",
    "mode",
    "session_id",
    "expected_before_state",
    "preflight",
    "idempotency_key",
    "authority",
}
BEFORE_FIELDS = {"session_version", "session_payload_hash", "checkpoint_id"}
PREFLIGHT_FIELDS = {"result_fingerprint", "authority_evidence_ref", "authority_evidence_fingerprint"}
REQUIRED_PREFLIGHT_CHECKS = {
    "runtime_store_present",
    "session_payload_hash_valid",
    "session_version_matches",
    "session_id_matches",
    "session_status_resumable",
    "resume_policy_allows_resume",
    "checkpoint_found",
    "checkpoint_is_latest",
    "checkpoint_policy_matches",
    "checkpoint_run_exists",
    "no_pending_gate",
    "no_pending_handoff",
    "authority_evidence_schema",
    "current_project_identity_available",
    "framework_identity_matches",
    "project_identity_matches",
    "project_authority_matches",
    "artifact_bindings_valid",
    "checkpoint_artifacts_verified",
    "required_capability_identifiers_valid",
    "required_capabilities_available",
    "approval_evidence_well_formed",
    "read_did_not_modify_runtime_store",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))


def project_file(project_root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        return None
    root = project_root.resolve()
    candidate = (root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def intent_payload(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": command.get("action"),
        "mode": command.get("mode"),
        "session_id": command.get("session_id"),
        "expected_before_state": command.get("expected_before_state"),
        "preflight": command.get("preflight"),
        "authority": command.get("authority"),
    }


def shape_errors(command: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    extra = sorted(set(command) - TOP_FIELDS)
    missing = sorted(TOP_FIELDS - set(command))
    if extra:
        errors.append("unexpected_top_fields:" + ",".join(extra))
    if missing:
        errors.append("missing_top_fields:" + ",".join(missing))
    if command.get("schema") != COMMAND_SCHEMA:
        errors.append("command_schema_invalid")
    if not isinstance(command.get("command_id"), str) or not command.get("command_id") or len(command["command_id"]) > 160:
        errors.append("command_id_invalid")
    if command.get("action") != "session.resume":
        errors.append("action_invalid")
    if command.get("mode") != "resume_latest_checkpoint":
        errors.append("mode_invalid")
    if not isinstance(command.get("session_id"), str) or not command.get("session_id") or len(command["session_id"]) > 240:
        errors.append("session_id_invalid")
    if command.get("authority") is not False:
        errors.append("command_authority_must_be_false")

    before = command.get("expected_before_state")
    if not isinstance(before, dict):
        errors.append("expected_before_state_invalid")
    else:
        if set(before) != BEFORE_FIELDS:
            errors.append("expected_before_state_fields_invalid")
        version = before.get("session_version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            errors.append("session_version_invalid")
        if not is_sha(before.get("session_payload_hash")):
            errors.append("session_payload_hash_invalid")
        if not isinstance(before.get("checkpoint_id"), str) or not before.get("checkpoint_id") or len(before["checkpoint_id"]) > 240:
            errors.append("checkpoint_id_invalid")

    preflight = command.get("preflight")
    if not isinstance(preflight, dict):
        errors.append("preflight_binding_invalid")
    else:
        if set(preflight) != PREFLIGHT_FIELDS:
            errors.append("preflight_binding_fields_invalid")
        if not is_sha(preflight.get("result_fingerprint")):
            errors.append("preflight_result_fingerprint_invalid")
        if not isinstance(preflight.get("authority_evidence_ref"), str) or not preflight.get("authority_evidence_ref") or len(preflight["authority_evidence_ref"]) > 512:
            errors.append("authority_evidence_ref_invalid")
        if not is_sha(preflight.get("authority_evidence_fingerprint")):
            errors.append("authority_evidence_fingerprint_invalid")

    if not is_sha(command.get("idempotency_key")):
        errors.append("idempotency_key_invalid")
    return errors


def validate(command: dict[str, Any], preflight: dict[str, Any], project_root: Path) -> dict[str, Any]:
    errors = shape_errors(command)
    checks: dict[str, bool] = {}

    checks["preflight_schema"] = preflight.get("schema") == PREFLIGHT_SCHEMA
    checks["preflight_ready"] = preflight.get("status") == "READY" and preflight.get("ready") is True
    checks["preflight_side_effect_free"] = preflight.get("mutation_performed") is False
    checks["preflight_authority_false"] = (
        preflight.get("authority") is False
        and preflight.get("canon_authority") is False
        and preflight.get("framework_write_authority") is False
        and preflight.get("settlement_authority") is False
    )
    if not checks["preflight_schema"]:
        errors.append("preflight_schema_invalid")
    if not checks["preflight_ready"]:
        errors.append("preflight_not_ready")
    if not checks["preflight_side_effect_free"]:
        errors.append("preflight_mutation_state_invalid")
    if not checks["preflight_authority_false"]:
        errors.append("preflight_authority_invalid")

    preflight_checks = preflight.get("checks") if isinstance(preflight.get("checks"), dict) else {}
    missing_checks = sorted(name for name in REQUIRED_PREFLIGHT_CHECKS if preflight_checks.get(name) is not True)
    checks["required_preflight_checks_true"] = not missing_checks
    if missing_checks:
        errors.append("preflight_required_checks_missing_or_false:" + ",".join(missing_checks))

    command_preflight = command.get("preflight") if isinstance(command.get("preflight"), dict) else {}
    actual_preflight_fp = fingerprint(preflight)
    checks["preflight_fingerprint_matches"] = command_preflight.get("result_fingerprint") == actual_preflight_fp
    if not checks["preflight_fingerprint_matches"]:
        errors.append("preflight_fingerprint_mismatch")

    session = preflight.get("session") if isinstance(preflight.get("session"), dict) else {}
    checkpoint = preflight.get("checkpoint") if isinstance(preflight.get("checkpoint"), dict) else {}
    before = command.get("expected_before_state") if isinstance(command.get("expected_before_state"), dict) else {}
    checks["session_identity_matches"] = command.get("session_id") == session.get("session_id")
    checks["session_version_matches"] = (
        before.get("session_version") == session.get("current_version")
        and before.get("session_version") == session.get("expected_version")
    )
    checks["session_payload_hash_matches"] = before.get("session_payload_hash") == session.get("payload_hash")
    checks["checkpoint_identity_matches"] = before.get("checkpoint_id") == checkpoint.get("checkpoint_id")
    if not checks["session_identity_matches"]:
        errors.append("session_identity_mismatch")
    if not checks["session_version_matches"]:
        errors.append("session_version_before_state_mismatch")
    if not checks["session_payload_hash_matches"]:
        errors.append("session_payload_hash_before_state_mismatch")
    if not checks["checkpoint_identity_matches"]:
        errors.append("checkpoint_identity_mismatch")

    evidence_path = project_file(project_root, command_preflight.get("authority_evidence_ref"))
    checks["authority_evidence_scoped"] = evidence_path is not None
    evidence: dict[str, Any] | None = None
    if evidence_path is None:
        errors.append("authority_evidence_scope_invalid")
    else:
        try:
            evidence = load_object(evidence_path)
        except Exception:
            errors.append("authority_evidence_invalid_json")
    checks["authority_evidence_schema"] = bool(evidence and evidence.get("schema") == AUTHORITY_EVIDENCE_SCHEMA)
    if not checks["authority_evidence_schema"]:
        errors.append("authority_evidence_schema_invalid")
    actual_evidence_fp = fingerprint(evidence) if evidence else None
    checks["authority_evidence_fingerprint_matches"] = command_preflight.get("authority_evidence_fingerprint") == actual_evidence_fp
    if not checks["authority_evidence_fingerprint_matches"]:
        errors.append("authority_evidence_fingerprint_mismatch")

    expected_intent_fp = fingerprint(intent_payload(command))
    checks["idempotency_key_matches_intent"] = command.get("idempotency_key") == expected_intent_fp
    if not checks["idempotency_key_matches_intent"]:
        errors.append("idempotency_key_mismatch")

    errors = list(dict.fromkeys(errors))
    valid = not errors and all(checks.values())
    return {
        "schema": VALIDATION_SCHEMA,
        "valid": valid,
        "errors": errors,
        "checks": checks,
        "command_fingerprint": fingerprint(command),
        "intent_fingerprint": expected_intent_fp,
        "preflight_fingerprint": actual_preflight_fp,
        "authority_evidence_fingerprint": actual_evidence_fp,
        "execution_authorized": False,
        "execution_performed": False,
        "runtime_mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "preflight_revalidation_required_at_execute": True,
        "resume_command_executor_exposed": True,
        "replay_or_fork": False,
    }


def make_command(*, session_id: str, version: int, payload_hash: str, checkpoint_id: str, preflight: dict[str, Any], evidence_ref: str, evidence: dict[str, Any], command_id: str) -> dict[str, Any]:
    command = {
        "schema": COMMAND_SCHEMA,
        "command_id": command_id,
        "action": "session.resume",
        "mode": "resume_latest_checkpoint",
        "session_id": session_id,
        "expected_before_state": {
            "session_version": version,
            "session_payload_hash": payload_hash,
            "checkpoint_id": checkpoint_id,
        },
        "preflight": {
            "result_fingerprint": fingerprint(preflight),
            "authority_evidence_ref": evidence_ref,
            "authority_evidence_fingerprint": fingerprint(evidence),
        },
        "idempotency_key": "",
        "authority": False,
    }
    command["idempotency_key"] = fingerprint(intent_payload(command))
    return command


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="quillframe-resume-command-") as tmp:
        root = Path(tmp)
        evidence = {
            "schema": AUTHORITY_EVIDENCE_SCHEMA,
            "project_id": "BOOK-CMD",
            "project_authority_fingerprint": "sha256:" + "a" * 64,
            "framework": {"version": "0.9.0", "commit": "fixture", "bundle_fingerprint": "sha256:" + "b" * 64},
            "artifact_bindings": [],
            "required_capabilities": [],
            "approval_refs": [],
        }
        evidence_ref = "resume-authority.json"
        (root / evidence_ref).write_text(json.dumps(evidence), encoding="utf-8")
        payload_hash = "sha256:" + "c" * 64
        checks = {name: True for name in REQUIRED_PREFLIGHT_CHECKS}
        preflight = {
            "schema": PREFLIGHT_SCHEMA,
            "status": "READY",
            "ready": True,
            "checks": checks,
            "blockers": [],
            "unresolved": [],
            "session": {"session_id": "SES-CMD", "status": "idle", "resume_policy": "checkpoint_revalidate", "expected_version": 4, "current_version": 4, "payload_hash": payload_hash},
            "checkpoint": {"checkpoint_id": "CP-CMD", "run_id": "RUN-CMD", "workflow_step": "context-frozen"},
            "mutation_performed": False,
            "model_execution": False,
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
            "settlement_authority": False,
        }
        command = make_command(
            session_id="SES-CMD",
            version=4,
            payload_hash=payload_hash,
            checkpoint_id="CP-CMD",
            preflight=preflight,
            evidence_ref=evidence_ref,
            evidence=evidence,
            command_id="CMD-RESUME-1",
        )
        valid = validate(command, preflight, root)

        stale = json.loads(json.dumps(command))
        stale["expected_before_state"]["session_version"] = 3
        stale["idempotency_key"] = fingerprint(intent_payload(stale))
        stale_result = validate(stale, preflight, root)

        blocked_preflight = json.loads(json.dumps(preflight))
        blocked_preflight["status"] = "BLOCKED"
        blocked_preflight["ready"] = False
        blocked_preflight["blockers"] = ["session_version_mismatch"]
        blocked = json.loads(json.dumps(command))
        blocked["preflight"]["result_fingerprint"] = fingerprint(blocked_preflight)
        blocked["idempotency_key"] = fingerprint(intent_payload(blocked))
        blocked_result = validate(blocked, blocked_preflight, root)

        tampered_evidence = dict(evidence)
        tampered_evidence["project_id"] = "BOOK-OTHER"
        (root / evidence_ref).write_text(json.dumps(tampered_evidence), encoding="utf-8")
        tampered_evidence_result = validate(command, preflight, root)
        (root / evidence_ref).write_text(json.dumps(evidence), encoding="utf-8")

        bad_idempotency = json.loads(json.dumps(command))
        bad_idempotency["idempotency_key"] = "sha256:" + "d" * 64
        bad_idempotency_result = validate(bad_idempotency, preflight, root)

        schema = load_object(Path(__file__).with_name("resume_command_schema.json"))
        ok = (
            schema.get("$id") == COMMAND_SCHEMA
            and valid["valid"] is True
            and stale_result["valid"] is False and "session_version_before_state_mismatch" in stale_result["errors"]
            and blocked_result["valid"] is False and "preflight_not_ready" in blocked_result["errors"]
            and tampered_evidence_result["valid"] is False and "authority_evidence_fingerprint_mismatch" in tampered_evidence_result["errors"]
            and bad_idempotency_result["valid"] is False and "idempotency_key_mismatch" in bad_idempotency_result["errors"]
            and valid["execution_authorized"] is False and valid["runtime_mutation_performed"] is False
            and valid["preflight_revalidation_required_at_execute"] is True
            and valid["resume_command_executor_exposed"] is True
        )
        dump({
            "resume_command_candidate_contract": "PASS" if ok else "FAIL",
            "valid_candidate": valid["valid"],
            "stale_before_state_rejected": not stale_result["valid"],
            "blocked_preflight_rejected": not blocked_result["valid"],
            "tampered_authority_evidence_rejected": not tampered_evidence_result["valid"],
            "idempotency_mismatch_rejected": not bad_idempotency_result["valid"],
            "execution_authorized": False,
            "runtime_mutation_performed": False,
            "resume_command_executor_exposed": True,
            "model_execution": False,
            "authority": False,
        })
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe typed session-resume command candidate validator")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_p = sub.add_parser("validate")
    validate_p.add_argument("--command", required=True)
    validate_p.add_argument("--preflight", required=True)
    validate_p.add_argument("--project-root", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    result = validate(load_object(Path(args.command)), load_object(Path(args.preflight)), Path(args.project_root))
    dump(result)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
