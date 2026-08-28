#!/usr/bin/env python3
"""Validate authorization for a typed Quillframe runtime command.

V1 authorizes only `session.resume`. Authorization is operational permission to
attempt a runtime-state transition after a fresh preflight. It never grants
Canon, Framework-write, Settlement, Project-write, or model-execution authority.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import resume_command  # noqa: E402

AUTH_SCHEMA = "quillframe_runtime_command_authorization_v1"
VALIDATION_SCHEMA = "quillframe_runtime_command_authorization_validation_v1"
MANAGER_POLICY_REF = "policy:runtime.resume.non_consequential.v1"
SOURCE_KINDS = {"user", "authorized_human", "manager_runtime_policy"}
MANAGER_ALLOWED_STATUSES = {"idle", "awaiting_external"}
TOP_FIELDS = {
    "schema",
    "authorization_id",
    "operation",
    "command_fingerprint",
    "intent_fingerprint",
    "decision",
    "source",
    "scope",
    "issued_at",
    "authority",
}
SOURCE_FIELDS = {"kind", "evidence_ref"}
SCOPE_FIELDS = {
    "runtime_state_mutation",
    "model_execution",
    "project_write",
    "canon_write",
    "framework_write",
    "settlement",
}
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ABS_WIN_RE = re.compile(r"^[A-Za-z]:[\\/]")


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))


def timestamp_valid(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def evidence_ref_safe(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 512:
        return False
    return not value.startswith("/") and not bool(ABS_WIN_RE.match(value))


def shape_errors(authorization: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    extra = sorted(set(authorization) - TOP_FIELDS)
    missing = sorted(TOP_FIELDS - set(authorization))
    if extra:
        errors.append("unexpected_top_fields:" + ",".join(extra))
    if missing:
        errors.append("missing_top_fields:" + ",".join(missing))
    if authorization.get("schema") != AUTH_SCHEMA:
        errors.append("authorization_schema_invalid")
    authorization_id = authorization.get("authorization_id")
    if not isinstance(authorization_id, str) or not authorization_id or len(authorization_id) > 160:
        errors.append("authorization_id_invalid")
    if authorization.get("operation") != "session.resume":
        errors.append("operation_invalid")
    if not is_sha(authorization.get("command_fingerprint")):
        errors.append("command_fingerprint_invalid")
    if not is_sha(authorization.get("intent_fingerprint")):
        errors.append("intent_fingerprint_invalid")
    if authorization.get("decision") not in {"allow", "deny"}:
        errors.append("decision_invalid")
    if authorization.get("authority") is not False:
        errors.append("authorization_authority_must_be_false")
    if not timestamp_valid(authorization.get("issued_at")):
        errors.append("issued_at_invalid")

    source = authorization.get("source")
    if not isinstance(source, dict):
        errors.append("source_invalid")
    else:
        if set(source) != SOURCE_FIELDS:
            errors.append("source_fields_invalid")
        if source.get("kind") not in SOURCE_KINDS:
            errors.append("source_kind_invalid")
        if not evidence_ref_safe(source.get("evidence_ref")):
            errors.append("source_evidence_ref_invalid")

    scope = authorization.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope_invalid")
    else:
        if set(scope) != SCOPE_FIELDS:
            errors.append("scope_fields_invalid")
        expected = {
            "runtime_state_mutation": True,
            "model_execution": False,
            "project_write": False,
            "canon_write": False,
            "framework_write": False,
            "settlement": False,
        }
        if any(scope.get(key) is not value for key, value in expected.items()):
            errors.append("scope_escalation_forbidden")
    return errors


def validate(
    authorization: dict[str, Any],
    command: dict[str, Any],
    preflight: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    errors = shape_errors(authorization)
    checks: dict[str, bool] = {}

    command_validation = resume_command.validate(command, preflight, project_root)
    checks["resume_command_valid"] = command_validation.get("valid") is True
    if not checks["resume_command_valid"]:
        errors.append("resume_command_candidate_invalid")

    checks["operation_matches_command"] = authorization.get("operation") == command.get("action") == "session.resume"
    if not checks["operation_matches_command"]:
        errors.append("authorization_operation_mismatch")

    checks["command_fingerprint_matches"] = authorization.get("command_fingerprint") == command_validation.get("command_fingerprint")
    if not checks["command_fingerprint_matches"]:
        errors.append("authorization_command_fingerprint_mismatch")

    checks["intent_fingerprint_matches"] = authorization.get("intent_fingerprint") == command_validation.get("intent_fingerprint")
    if not checks["intent_fingerprint_matches"]:
        errors.append("authorization_intent_fingerprint_mismatch")

    checks["command_still_requires_fresh_preflight"] = command_validation.get("preflight_revalidation_required_at_execute") is True
    if not checks["command_still_requires_fresh_preflight"]:
        errors.append("fresh_preflight_requirement_missing")

    source = authorization.get("source") if isinstance(authorization.get("source"), dict) else {}
    source_kind = source.get("kind")
    source_ref = source.get("evidence_ref")
    session = preflight.get("session") if isinstance(preflight.get("session"), dict) else {}
    session_status = session.get("status")

    checks["manager_policy_ref_exact"] = source_kind != "manager_runtime_policy" or source_ref == MANAGER_POLICY_REF
    if not checks["manager_policy_ref_exact"]:
        errors.append("manager_runtime_policy_ref_invalid")

    checks["manager_policy_status_allowed"] = source_kind != "manager_runtime_policy" or session_status in MANAGER_ALLOWED_STATUSES
    if not checks["manager_policy_status_allowed"]:
        errors.append("manager_runtime_policy_cannot_authorize_session_status")

    checks["human_required_for_interactive_or_failed"] = (
        session_status not in {"awaiting_user", "failed"}
        or source_kind in {"user", "authorized_human"}
        or authorization.get("decision") == "deny"
    )
    if not checks["human_required_for_interactive_or_failed"]:
        errors.append("interactive_or_failed_resume_requires_human_authorization")

    decision = authorization.get("decision")
    errors = list(dict.fromkeys(errors))
    valid = not errors and all(checks.values())
    granted = valid and decision == "allow"

    return {
        "schema": VALIDATION_SCHEMA,
        "valid": valid,
        "authorization_granted": granted,
        "decision": decision,
        "source_kind": source_kind,
        "session_status": session_status,
        "errors": errors,
        "checks": checks,
        "authorization_fingerprint": resume_command.fingerprint(authorization),
        "command_fingerprint": command_validation.get("command_fingerprint"),
        "intent_fingerprint": command_validation.get("intent_fingerprint"),
        "executor_may_attempt_revalidation": granted,
        "preflight_revalidation_required_at_execute": True,
        "execution_performed": False,
        "runtime_mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "project_write_authority": False,
    }


def fixture(
    *,
    root: Path,
    status: str = "idle",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    evidence = {
        "schema": resume_command.AUTHORITY_EVIDENCE_SCHEMA,
        "project_id": "BOOK-AUTH",
        "project_manifest_fingerprint": "sha256:" + "a" * 64,
        "scope": "novel",
        "data_root": str(root / ".quillframe" / "data"),
        "artifact_bindings": [],
        "required_capabilities": [],
        "approval_refs": [],
    }
    evidence_ref = "resume-authority.json"
    (root / evidence_ref).write_text(json.dumps(evidence), encoding="utf-8")
    payload_hash = "sha256:" + "c" * 64
    preflight_checks = {name: True for name in resume_command.REQUIRED_PREFLIGHT_CHECKS}
    preflight = {
        "schema": resume_command.PREFLIGHT_SCHEMA,
        "status": "READY",
        "ready": True,
        "checks": preflight_checks,
        "blockers": [],
        "unresolved": [],
        "session": {
            "session_id": "SES-AUTH",
            "status": status,
            "resume_policy": "checkpoint_revalidate",
            "expected_version": 7,
            "current_version": 7,
            "payload_hash": payload_hash,
        },
        "checkpoint": {
            "checkpoint_id": "CP-AUTH",
            "run_id": "RUN-AUTH",
            "workflow_step": "context-frozen",
        },
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    command = resume_command.make_command(
        session_id="SES-AUTH",
        version=7,
        payload_hash=payload_hash,
        checkpoint_id="CP-AUTH",
        preflight=preflight,
        evidence_ref=evidence_ref,
        evidence=evidence,
        command_id="CMD-AUTH-1",
    )
    return evidence, preflight, command


def make_authorization(
    *,
    command: dict[str, Any],
    preflight: dict[str, Any],
    project_root: Path,
    decision: str,
    source_kind: str,
    evidence_ref: str,
    authorization_id: str,
) -> dict[str, Any]:
    command_validation = resume_command.validate(command, preflight, project_root)
    return {
        "schema": AUTH_SCHEMA,
        "authorization_id": authorization_id,
        "operation": "session.resume",
        "command_fingerprint": command_validation["command_fingerprint"],
        "intent_fingerprint": command_validation["intent_fingerprint"],
        "decision": decision,
        "source": {"kind": source_kind, "evidence_ref": evidence_ref},
        "scope": {
            "runtime_state_mutation": True,
            "model_execution": False,
            "project_write": False,
            "canon_write": False,
            "framework_write": False,
            "settlement": False,
        },
        "issued_at": "2026-01-01T00:00:00+00:00",
        "authority": False,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="quillframe-resume-authorization-") as tmp:
        root = Path(tmp)
        _, idle_preflight, idle_command = fixture(root=root, status="idle")
        manager = make_authorization(
            command=idle_command,
            preflight=idle_preflight,
            project_root=root,
            decision="allow",
            source_kind="manager_runtime_policy",
            evidence_ref=MANAGER_POLICY_REF,
            authorization_id="AUTH-MANAGER",
        )
        manager_result = validate(manager, idle_command, idle_preflight, root)

        _, wait_preflight, wait_command = fixture(root=root, status="awaiting_user")
        manager_wait = make_authorization(
            command=wait_command,
            preflight=wait_preflight,
            project_root=root,
            decision="allow",
            source_kind="manager_runtime_policy",
            evidence_ref=MANAGER_POLICY_REF,
            authorization_id="AUTH-MANAGER-WAIT",
        )
        manager_wait_result = validate(manager_wait, wait_command, wait_preflight, root)

        human_wait = make_authorization(
            command=wait_command,
            preflight=wait_preflight,
            project_root=root,
            decision="allow",
            source_kind="user",
            evidence_ref="urn:quillframe:user-action:resume-self-test",
            authorization_id="AUTH-USER-WAIT",
        )
        human_wait_result = validate(human_wait, wait_command, wait_preflight, root)

        deny = make_authorization(
            command=idle_command,
            preflight=idle_preflight,
            project_root=root,
            decision="deny",
            source_kind="manager_runtime_policy",
            evidence_ref=MANAGER_POLICY_REF,
            authorization_id="AUTH-DENY",
        )
        deny_result = validate(deny, idle_command, idle_preflight, root)

        tampered = json.loads(json.dumps(manager))
        tampered["command_fingerprint"] = "sha256:" + "d" * 64
        tampered_result = validate(tampered, idle_command, idle_preflight, root)

        elevated = json.loads(json.dumps(manager))
        elevated["scope"]["canon_write"] = True
        elevated_result = validate(elevated, idle_command, idle_preflight, root)

        absolute_ref = json.loads(json.dumps(human_wait))
        absolute_ref["source"]["evidence_ref"] = "/tmp/private-authorization.json"
        absolute_ref_result = validate(absolute_ref, wait_command, wait_preflight, root)

        schema = load_object(Path(__file__).with_name("runtime_command_authorization_schema.json"))
        ok = (
            schema.get("$id") == AUTH_SCHEMA
            and manager_result["valid"] is True and manager_result["authorization_granted"] is True
            and manager_wait_result["valid"] is False and manager_wait_result["authorization_granted"] is False
            and "manager_runtime_policy_cannot_authorize_session_status" in manager_wait_result["errors"]
            and human_wait_result["valid"] is True and human_wait_result["authorization_granted"] is True
            and deny_result["valid"] is True and deny_result["authorization_granted"] is False
            and tampered_result["valid"] is False
            and elevated_result["valid"] is False and "scope_escalation_forbidden" in elevated_result["errors"]
            and absolute_ref_result["valid"] is False
            and manager_result["runtime_mutation_performed"] is False
            and manager_result["model_execution"] is False
            and manager_result["authority"] is False
            and manager_result["preflight_revalidation_required_at_execute"] is True
        )
        dump({
            "runtime_command_authorization_contract": "PASS" if ok else "FAIL",
            "manager_idle_authorized": manager_result["authorization_granted"],
            "manager_awaiting_user_rejected": not manager_wait_result["valid"],
            "user_awaiting_user_authorized": human_wait_result["authorization_granted"],
            "deny_valid_but_not_granted": deny_result["valid"] and not deny_result["authorization_granted"],
            "tampered_command_binding_rejected": not tampered_result["valid"],
            "scope_escalation_rejected": not elevated_result["valid"],
            "absolute_evidence_ref_rejected": not absolute_ref_result["valid"],
            "preflight_revalidation_required_at_execute": True,
            "runtime_mutation_performed": False,
            "model_execution": False,
            "authority": False,
        })
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe runtime command authorization validator")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_p = sub.add_parser("validate")
    validate_p.add_argument("--authorization", required=True)
    validate_p.add_argument("--resume-command", required=True)
    validate_p.add_argument("--preflight", required=True)
    validate_p.add_argument("--project-root", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    result = validate(
        load_object(Path(args.authorization)),
        load_object(Path(args.resume_command)),
        load_object(Path(args.preflight)),
        Path(args.project_root),
    )
    dump(result)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
