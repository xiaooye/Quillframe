#!/usr/bin/env python3
"""Validate typed Quillframe session-terminate command candidates.

The candidate binds one explicit stop intent to one READY terminate preflight and
one exact durable Session/Run before-state. Validation is side-effect-free and
does not itself authorize or execute the command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import terminate_preflight

COMMAND_SCHEMA = "quillframe_session_terminate_command_v1"
VALIDATION_SCHEMA = "quillframe_session_terminate_command_validation_v1"
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TOP_FIELDS = {
    "schema", "command_id", "action", "mode", "session_id",
    "expected_before_state", "preflight", "idempotency_key", "authority",
}
BEFORE_FIELDS = {"session_version", "session_payload_hash", "session_status", "run_id", "run_status"}
PREFLIGHT_FIELDS = {"result_fingerprint"}
REQUIRED_PREFLIGHT_CHECKS = {
    "runtime_store_present",
    "session_payload_hash_valid",
    "session_version_matches",
    "session_id_matches",
    "session_status_terminable",
    "current_project_identity_available",
    "project_identity_matches",
    "at_most_one_active_run",
    "active_run_is_latest",
    "run_state_well_formed",
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
    if command.get("action") != "session.terminate":
        errors.append("action_invalid")
    if command.get("mode") != "terminate_session_and_active_run":
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
        if not isinstance(before.get("session_status"), str) or not before.get("session_status"):
            errors.append("session_status_invalid")
        for field in ("run_id", "run_status"):
            value = before.get(field)
            if value is not None and (not isinstance(value, str) or not value):
                errors.append(f"{field}_invalid")
        if (before.get("run_id") is None) != (before.get("run_status") is None):
            errors.append("run_binding_incomplete")

    preflight = command.get("preflight")
    if not isinstance(preflight, dict):
        errors.append("preflight_binding_invalid")
    else:
        if set(preflight) != PREFLIGHT_FIELDS:
            errors.append("preflight_binding_fields_invalid")
        if not is_sha(preflight.get("result_fingerprint")):
            errors.append("preflight_result_fingerprint_invalid")
    if not is_sha(command.get("idempotency_key")):
        errors.append("idempotency_key_invalid")
    return errors


def validate(command: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    errors = shape_errors(command)
    checks: dict[str, bool] = {}
    checks["preflight_schema"] = preflight.get("schema") == terminate_preflight.SCHEMA
    checks["preflight_ready"] = preflight.get("status") == "READY" and preflight.get("ready") is True
    checks["preflight_side_effect_free"] = preflight.get("mutation_performed") is False
    checks["preflight_authority_false"] = (
        preflight.get("authority") is False
        and preflight.get("project_write_authority") is False
        and preflight.get("canon_authority") is False
        and preflight.get("framework_write_authority") is False
        and preflight.get("settlement_authority") is False
    )
    if not checks["preflight_schema"]: errors.append("preflight_schema_invalid")
    if not checks["preflight_ready"]: errors.append("preflight_not_ready")
    if not checks["preflight_side_effect_free"]: errors.append("preflight_mutation_state_invalid")
    if not checks["preflight_authority_false"]: errors.append("preflight_authority_invalid")

    raw_checks = preflight.get("checks") if isinstance(preflight.get("checks"), dict) else {}
    missing_checks = sorted(name for name in REQUIRED_PREFLIGHT_CHECKS if raw_checks.get(name) is not True)
    checks["required_preflight_checks_true"] = not missing_checks
    if missing_checks:
        errors.append("preflight_required_checks_missing_or_false:" + ",".join(missing_checks))

    binding = command.get("preflight") if isinstance(command.get("preflight"), dict) else {}
    actual_preflight_fp = fingerprint({key: value for key, value in preflight.items() if key != "result_fingerprint"})
    checks["preflight_fingerprint_matches"] = binding.get("result_fingerprint") == preflight.get("result_fingerprint") == actual_preflight_fp
    if not checks["preflight_fingerprint_matches"]:
        errors.append("preflight_fingerprint_mismatch")

    session = preflight.get("session") if isinstance(preflight.get("session"), dict) else {}
    run = preflight.get("run") if isinstance(preflight.get("run"), dict) else None
    before = command.get("expected_before_state") if isinstance(command.get("expected_before_state"), dict) else {}
    checks["session_identity_matches"] = command.get("session_id") == session.get("session_id")
    checks["session_version_matches"] = before.get("session_version") == session.get("current_version") == session.get("expected_version")
    checks["session_payload_hash_matches"] = before.get("session_payload_hash") == session.get("payload_hash")
    checks["session_status_matches"] = before.get("session_status") == session.get("status")
    checks["run_binding_matches"] = (
        (run is None and before.get("run_id") is None and before.get("run_status") is None)
        or (
            run is not None
            and before.get("run_id") == run.get("run_id")
            and before.get("run_status") == run.get("status")
        )
    )
    for name, message in (
        ("session_identity_matches", "session_identity_mismatch"),
        ("session_version_matches", "session_version_before_state_mismatch"),
        ("session_payload_hash_matches", "session_payload_hash_before_state_mismatch"),
        ("session_status_matches", "session_status_before_state_mismatch"),
        ("run_binding_matches", "run_before_state_mismatch"),
    ):
        if not checks[name]: errors.append(message)

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
        "preflight_fingerprint": preflight.get("result_fingerprint"),
        "execution_authorized": False,
        "execution_performed": False,
        "runtime_mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "preflight_revalidation_required_at_execute": True,
    }


def make_command(*, preflight: dict[str, Any], command_id: str) -> dict[str, Any]:
    session = preflight.get("session") if isinstance(preflight.get("session"), dict) else {}
    run = preflight.get("run") if isinstance(preflight.get("run"), dict) else None
    command = {
        "schema": COMMAND_SCHEMA,
        "command_id": command_id,
        "action": "session.terminate",
        "mode": "terminate_session_and_active_run",
        "session_id": session.get("session_id"),
        "expected_before_state": {
            "session_version": session.get("current_version"),
            "session_payload_hash": session.get("payload_hash"),
            "session_status": session.get("status"),
            "run_id": run.get("run_id") if run else None,
            "run_status": run.get("status") if run else None,
        },
        "preflight": {"result_fingerprint": preflight.get("result_fingerprint")},
        "idempotency_key": "",
        "authority": False,
    }
    command["idempotency_key"] = fingerprint(intent_payload(command))
    return command


def self_test() -> int:
    checks = {name: True for name in REQUIRED_PREFLIGHT_CHECKS}
    base = {
        "schema": terminate_preflight.SCHEMA,
        "status": "READY",
        "ready": True,
        "checks": checks,
        "blockers": [],
        "unresolved": [],
        "session": {"session_id": "SES-STOP", "project_id": "BOOK-STOP", "status": "running", "expected_version": 4, "current_version": 4, "payload_hash": "sha256:" + "a" * 64},
        "run": {"run_id": "RUN-STOP", "status": "running", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None},
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    base["result_fingerprint"] = fingerprint(base)
    command = make_command(preflight=base, command_id="CMD-STOP-1")
    valid = validate(command, base)

    stale = json.loads(json.dumps(command))
    stale["expected_before_state"]["session_version"] = 3
    stale["idempotency_key"] = fingerprint(intent_payload(stale))
    stale_result = validate(stale, base)

    wrong_run = json.loads(json.dumps(command))
    wrong_run["expected_before_state"]["run_id"] = "RUN-OTHER"
    wrong_run["idempotency_key"] = fingerprint(intent_payload(wrong_run))
    wrong_run_result = validate(wrong_run, base)

    blocked = json.loads(json.dumps(base))
    blocked.pop("result_fingerprint")
    blocked["status"] = "BLOCKED"
    blocked["ready"] = False
    blocked["blockers"] = ["session_status_not_terminable"]
    blocked["checks"]["session_status_terminable"] = False
    blocked["result_fingerprint"] = fingerprint(blocked)
    blocked_command = make_command(preflight=blocked, command_id="CMD-STOP-BLOCKED")
    blocked_result = validate(blocked_command, blocked)

    schema = load_object(Path(__file__).with_name("terminate_command_schema.json"))
    ok = (
        schema.get("$id") == COMMAND_SCHEMA
        and valid["valid"] is True
        and stale_result["valid"] is False and "session_version_before_state_mismatch" in stale_result["errors"]
        and wrong_run_result["valid"] is False and "run_before_state_mismatch" in wrong_run_result["errors"]
        and blocked_result["valid"] is False and "preflight_not_ready" in blocked_result["errors"]
        and valid["execution_authorized"] is False and valid["runtime_mutation_performed"] is False
    )
    dump({
        "session_terminate_command_contract": "PASS" if ok else "FAIL",
        "valid_candidate": valid["valid"],
        "stale_before_state_rejected": not stale_result["valid"],
        "wrong_run_rejected": not wrong_run_result["valid"],
        "blocked_preflight_rejected": not blocked_result["valid"],
        "execution_authorized": False,
        "runtime_mutation_performed": False,
        "model_execution": False,
        "authority": False,
    })
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe typed session terminate command validator")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_p = sub.add_parser("validate")
    validate_p.add_argument("--command", required=True)
    validate_p.add_argument("--preflight", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    value = validate(load_object(Path(args.command)), load_object(Path(args.preflight)))
    dump(value)
    return 0 if value["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
