"""Deterministic host-lifecycle receipt for native independent review.

The receipt attests a host-created separate context bound to durable lifecycle
events. It is deliberately not a cryptographic signature or OS sandbox proof.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from peer_chat_relay import validate_peer_result  # noqa: E402

SCHEMA = "quillframe_independent_invocation_receipt_v1"
ASSURANCE_CLASS = "host_native_separate_context"
PROVIDERS = {
    "codex": {"transport": "codex_native", "worker_provider": "codex_native"},
    "claude": {"transport": "claude_code_native", "worker_provider": "claude_code_native"},
}
PERMISSIONS = {
    "canon_write": False,
    "framework_write": False,
    "durable_user_taste_write": False,
    "project_read": False,
    "filesystem": False,
    "shell": False,
    "network": False,
    "memory": False,
    "write": False,
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def build_receipt(
    packet: dict[str, Any],
    result: dict[str, Any],
    *,
    lease_id: str,
    project_id: str,
    run_id: str,
    provider: str,
    parent_session_id: str,
    reviewer_session_id: str,
    host_agent_id: str,
    host_invocation_id: str,
    lifecycle_events: list[dict[str, Any]],
) -> dict[str, Any]:
    errors = validate_peer_result(packet, result)
    if errors:
        raise ValueError("native peer result invalid: " + "; ".join(errors))
    if provider not in PROVIDERS:
        raise ValueError("provider must be codex|claude")
    expected = PROVIDERS[provider]
    if (result.get("worker") or {}).get("provider") != expected["worker_provider"]:
        raise ValueError("native result worker.provider does not match lease provider")
    if parent_session_id == reviewer_session_id:
        raise ValueError("reviewer session must differ from parent session")
    if [event.get("event_kind") for event in lifecycle_events] != ["prepared", "claimed", "completed"]:
        raise ValueError("native lifecycle must be prepared, claimed, completed")
    if any(
        not isinstance(event.get("event_id"), str)
        or not isinstance(event.get("event_fingerprint"), str)
        for event in lifecycle_events
    ):
        raise ValueError("native lifecycle events require IDs and fingerprints")
    job = packet.get("job") or {}
    payload = ((job.get("input") or {}).get("payload") or {})
    receipt = {
        "schema": SCHEMA,
        "lease_id": _nonempty(lease_id, "lease_id"),
        "project_id": _nonempty(project_id, "project_id"),
        "run_id": _nonempty(run_id, "run_id"),
        "job_id": _nonempty(job.get("job_id"), "job_id"),
        "candidate_fingerprint": _nonempty(payload.get("candidate_fingerprint"), "candidate_fingerprint"),
        "input_fingerprint": _nonempty(job.get("input_fingerprint"), "input_fingerprint"),
        "packet_fingerprint": fingerprint(packet),
        "result_fingerprint": fingerprint(result),
        "relay_nonce": _nonempty(packet.get("relay_nonce"), "relay_nonce"),
        "provider": provider,
        "transport": expected["transport"],
        "parent_session_id": _nonempty(parent_session_id, "parent_session_id"),
        "reviewer_session_id": _nonempty(reviewer_session_id, "reviewer_session_id"),
        "host_agent_id": _nonempty(host_agent_id, "host_agent_id"),
        "host_invocation_id": _nonempty(host_invocation_id, "host_invocation_id"),
        "lifecycle_events": lifecycle_events,
        "assurance_class": ASSURANCE_CLASS,
        "host_lifecycle_attestation": True,
        "cryptographic_signature": False,
        "os_isolation_attested": False,
        "model_execution": True,
        "authority": False,
        "permissions": PERMISSIONS,
    }
    receipt["receipt_fingerprint"] = fingerprint(receipt)
    return receipt


def validate_receipt(receipt: Any, packet: dict[str, Any], result: dict[str, Any]) -> list[str]:
    if not isinstance(receipt, dict):
        return ["independent invocation receipt must be object"]
    errors: list[str] = []
    if receipt.get("schema") != SCHEMA:
        errors.append("independent invocation receipt schema mismatch")
        return errors
    expected_self = fingerprint({key: value for key, value in receipt.items() if key != "receipt_fingerprint"})
    if receipt.get("receipt_fingerprint") != expected_self:
        errors.append("independent invocation receipt self-fingerprint mismatch")
    for key in (
        "lease_id",
        "project_id",
        "run_id",
        "parent_session_id",
        "reviewer_session_id",
        "host_agent_id",
        "host_invocation_id",
    ):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            errors.append(f"independent invocation receipt {key} invalid")
    peer_errors = validate_peer_result(packet, result)
    errors.extend("native peer result: " + error for error in peer_errors)
    job = packet.get("job") if isinstance(packet, dict) else None
    job = job if isinstance(job, dict) else {}
    payload = ((job.get("input") or {}).get("payload") or {})
    expected = {
        "job_id": job.get("job_id"),
        "candidate_fingerprint": payload.get("candidate_fingerprint"),
        "input_fingerprint": job.get("input_fingerprint"),
        "packet_fingerprint": fingerprint(packet),
        "result_fingerprint": fingerprint(result),
        "relay_nonce": packet.get("relay_nonce"),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"independent invocation receipt mismatch: {key}")
    provider = receipt.get("provider")
    provider_contract = PROVIDERS.get(provider)
    if provider_contract is None:
        errors.append("independent invocation receipt provider invalid")
    else:
        if receipt.get("transport") != provider_contract["transport"]:
            errors.append("independent invocation receipt transport mismatch")
        if (result.get("worker") or {}).get("provider") != provider_contract["worker_provider"]:
            errors.append("independent invocation receipt worker provider mismatch")
    if receipt.get("parent_session_id") == receipt.get("reviewer_session_id"):
        errors.append("independent invocation receipt sessions must differ")
    events = receipt.get("lifecycle_events")
    if (
        not isinstance(events, list)
        or len(events) != 3
        or not all(isinstance(event, dict) for event in events)
        or [event.get("event_kind") for event in events] != ["prepared", "claimed", "completed"]
        or any(
            not isinstance(event.get(key), str) or not event[key].strip()
            for event in events
            for key in ("event_id", "event_fingerprint")
        )
    ):
        errors.append("independent invocation receipt lifecycle invalid")
    if receipt.get("assurance_class") != ASSURANCE_CLASS:
        errors.append("independent invocation receipt assurance class invalid")
    if receipt.get("permissions") != PERMISSIONS:
        errors.append("independent invocation receipt permissions invalid")
    if receipt.get("authority") is not False or receipt.get("model_execution") is not True:
        errors.append("independent invocation receipt authority/execution invalid")
    if (
        receipt.get("host_lifecycle_attestation") is not True
        or receipt.get("cryptographic_signature") is not False
        or receipt.get("os_isolation_attested") is not False
    ):
        errors.append("independent invocation receipt assurance attestation invalid")
    return errors
