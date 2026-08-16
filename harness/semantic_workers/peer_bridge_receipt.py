#!/usr/bin/env python3
"""Machine receipt for Project-owned peer semantic validation.

The peer-chat relay proves job/result/nonce binding. The Project-hosted bridge
adds consuming-Project and exact-Framework provenance plus an auditable GitHub
runtime trace. This receipt is deterministic evidence bound to the exact result;
it is not a cryptographic signature, literary judgment, or Canon authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from peer_chat_relay import validate_peer_result
from registered_contract_binding import validate_registered_job

SCHEMA = "novelforge_project_peer_validation_receipt_v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def scalar_fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be positive integer")
    return value


def _runtime_trace(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("runtime_trace object required")
    run_id = _positive_int(value.get("github_run_id"), "runtime_trace.github_run_id")
    run_attempt = _positive_int(value.get("github_run_attempt"), "runtime_trace.github_run_attempt")
    result_comment_id = _positive_int(value.get("result_comment_id"), "runtime_trace.result_comment_id")
    event_name = value.get("github_event_name")
    if event_name != "issue_comment":
        raise ValueError("runtime_trace.github_event_name must be issue_comment")
    action_ref = value.get("framework_action_ref")
    if not isinstance(action_ref, str) or len(action_ref) != 40:
        raise ValueError("runtime_trace.framework_action_ref must be exact 40-character commit")
    workflow = value.get("workflow_name")
    if not isinstance(workflow, str) or not workflow.strip():
        raise ValueError("runtime_trace.workflow_name required")
    return {
        "source": "project_owned_github_actions_bridge",
        "github_run_id": run_id,
        "github_run_attempt": run_attempt,
        "github_event_name": event_name,
        "result_comment_id": result_comment_id,
        "workflow_name": workflow,
        "framework_action_ref": action_ref,
        "cryptographic_signature": False,
    }


def build_receipt(
    packet: dict[str, Any],
    result: dict[str, Any],
    *,
    project_id: str,
    project_repo: str,
    framework_repo: str,
    framework_commit: str,
    issue_number: int,
    runtime_trace: dict[str, Any],
) -> dict[str, Any]:
    relay_errors = validate_peer_result(packet, result)
    if relay_errors:
        raise ValueError("peer relay validation failed: " + "; ".join(relay_errors))
    job = packet.get("job")
    if not isinstance(job, dict):
        raise ValueError("peer packet job required")
    contract_errors = validate_registered_job(job)
    if contract_errors:
        raise ValueError("registered contract binding failed: " + "; ".join(contract_errors))
    provenance = job.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("job provenance required")
    expected = {
        "project_id": project_id,
        "project_repo": project_repo.lower(),
        "framework_repo": framework_repo.lower(),
        "framework_commit": framework_commit,
    }
    for key, value in expected.items():
        actual = provenance.get(key)
        if key.endswith("_repo") and isinstance(actual, str):
            actual = actual.lower()
        if actual != value:
            raise ValueError(f"job/bridge provenance mismatch: {key}")
    _positive_int(issue_number, "issue_number")
    nonce = packet.get("relay_nonce")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("relay nonce required")
    trace = _runtime_trace(runtime_trace)
    if trace["framework_action_ref"] != framework_commit:
        raise ValueError("runtime trace framework_action_ref must equal framework_commit")
    return {
        "schema": SCHEMA,
        "mode": "validate-result",
        "project_id": project_id,
        "project_repo": project_repo.lower(),
        "framework_repo": framework_repo.lower(),
        "framework_commit": framework_commit,
        "issue_number": issue_number,
        "job_id": job.get("job_id"),
        "subject_id": job.get("subject_id"),
        "model_contract_id": (job.get("input") or {}).get("model_contract_id"),
        "input_fingerprint": job.get("input_fingerprint"),
        "result_fingerprint": fingerprint(result),
        "relay_nonce_fingerprint": scalar_fingerprint(nonce),
        "worker_provider": (result.get("worker") or {}).get("provider"),
        "runtime_trace": trace,
        "registered_contract_validated": True,
        "peer_relay_validated": True,
        "project_hosted": True,
        "authority": False,
        "model_execution": False,
    }


def validate_receipt(receipt: dict[str, Any], packet: dict[str, Any], result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        return ["invalid peer validation receipt schema"]
    if receipt.get("mode") != "validate-result":
        errors.append("peer validation receipt mode mismatch")
    if receipt.get("project_hosted") is not True:
        errors.append("peer validation receipt must be project_hosted")
    if receipt.get("registered_contract_validated") is not True:
        errors.append("peer validation receipt missing registered contract proof")
    if receipt.get("peer_relay_validated") is not True:
        errors.append("peer validation receipt missing relay proof")
    if receipt.get("authority") is not False:
        errors.append("peer validation receipt authority must be false")

    job = packet.get("job") if isinstance(packet, dict) else None
    if not isinstance(job, dict):
        errors.append("peer packet job required")
        return errors
    errors += ["peer relay: " + item for item in validate_peer_result(packet, result)]
    errors += ["registered contract: " + item for item in validate_registered_job(job)]

    expected = {
        "job_id": job.get("job_id"),
        "subject_id": job.get("subject_id"),
        "model_contract_id": (job.get("input") or {}).get("model_contract_id"),
        "input_fingerprint": job.get("input_fingerprint"),
        "result_fingerprint": fingerprint(result),
        "relay_nonce_fingerprint": scalar_fingerprint(str(packet.get("relay_nonce") or "")),
        "worker_provider": (result.get("worker") or {}).get("provider"),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"peer validation receipt mismatch: {key}")

    provenance = job.get("provenance") or {}
    provenance_expected = {
        "project_id": receipt.get("project_id"),
        "project_repo": receipt.get("project_repo"),
        "framework_repo": receipt.get("framework_repo"),
        "framework_commit": receipt.get("framework_commit"),
    }
    for key, value in provenance_expected.items():
        actual = provenance.get(key)
        if key.endswith("_repo") and isinstance(actual, str):
            actual = actual.lower()
        if actual != value:
            errors.append(f"peer validation receipt provenance mismatch: {key}")
    try:
        _positive_int(receipt.get("issue_number"), "issue_number")
        trace = _runtime_trace(receipt.get("runtime_trace"))
        if trace["framework_action_ref"] != receipt.get("framework_commit"):
            errors.append("peer validation receipt runtime framework ref mismatch")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def self_test() -> dict[str, Any]:
    from peer_chat_relay import build as build_packet
    from semantic_worker_router import make_contract_job

    fp = "sha256:" + "a" * 64
    job = make_contract_job(
        "quality.production_review",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "fixture", "reader_grip": "very_high"},
        source_session_id="SES-MANAGER",
    )
    job["provenance"].update({
        "project_id": "PROJECT-SELF",
        "project_repo": "owner/project",
        "framework_repo": "owner/framework",
        "framework_commit": "f" * 40,
    })
    packet = build_packet(job)
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "chatgpt_peer_chat", "model_or_reviewer": "fixture", "run_reference": packet["relay_nonce"]},
        "judgment": {"confidence": 0.9, "result": "pass", "report": "fixture", "evidence_refs": ["fixture"]},
        "proposals": [],
        "errors": [],
    }
    trace = {
        "github_run_id": 123,
        "github_run_attempt": 1,
        "github_event_name": "issue_comment",
        "result_comment_id": 456,
        "workflow_name": "Project peer bridge",
        "framework_action_ref": "f" * 40,
    }
    receipt = build_receipt(
        packet,
        result,
        project_id="PROJECT-SELF",
        project_repo="owner/project",
        framework_repo="owner/framework",
        framework_commit="f" * 40,
        issue_number=7,
        runtime_trace=trace,
    )
    tampered = json.loads(json.dumps(receipt))
    tampered["result_fingerprint"] = "sha256:" + "0" * 64
    fake_ref = json.loads(json.dumps(receipt))
    fake_ref["runtime_trace"]["framework_action_ref"] = "e" * 40
    checks = {
        "valid_receipt_passes": not validate_receipt(receipt, packet, result),
        "result_tamper_rejected": any("result_fingerprint" in x for x in validate_receipt(tampered, packet, result)),
        "runtime_ref_tamper_rejected": any("framework ref mismatch" in x for x in validate_receipt(fake_ref, packet, result)),
        "registered_contract_proof_present": receipt["registered_contract_validated"] is True,
        "peer_relay_proof_present": receipt["peer_relay_validated"] is True,
        "project_framework_bound": receipt["project_id"] == "PROJECT-SELF" and receipt["framework_commit"] == "f" * 40,
        "runtime_trace_auditable": receipt["runtime_trace"]["source"] == "project_owned_github_actions_bridge" and receipt["runtime_trace"]["cryptographic_signature"] is False,
    }
    return {
        "peer_bridge_receipt_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/validate a Project-owned peer semantic validation receipt")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    build = sub.add_parser("build")
    build.add_argument("--packet", required=True)
    build.add_argument("--result", required=True)
    build.add_argument("--project-id", required=True)
    build.add_argument("--project-repo", required=True)
    build.add_argument("--framework-repo", required=True)
    build.add_argument("--framework-commit", required=True)
    build.add_argument("--issue-number", required=True, type=int)
    build.add_argument("--github-run-id", required=True, type=int)
    build.add_argument("--github-run-attempt", required=True, type=int)
    build.add_argument("--result-comment-id", required=True, type=int)
    build.add_argument("--github-event-name", required=True)
    build.add_argument("--workflow-name", required=True)
    build.add_argument("--framework-action-ref", required=True)
    build.add_argument("--output")
    args = parser.parse_args()
    if args.command == "self-test":
        value = self_test()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0 if value["peer_bridge_receipt_contract"] == "PASS" else 1
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    receipt = build_receipt(
        packet,
        result,
        project_id=args.project_id,
        project_repo=args.project_repo,
        framework_repo=args.framework_repo,
        framework_commit=args.framework_commit,
        issue_number=args.issue_number,
        runtime_trace={
            "github_run_id": args.github_run_id,
            "github_run_attempt": args.github_run_attempt,
            "github_event_name": args.github_event_name,
            "result_comment_id": args.result_comment_id,
            "workflow_name": args.workflow_name,
            "framework_action_ref": args.framework_action_ref,
        },
    )
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())