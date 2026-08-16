#!/usr/bin/env python3
"""Deterministic write-intent/action preflight guard.

This module does not execute writes and does not grant authority. It proves that
a consequential action a runtime is about to invoke matches the resource class,
operation class, exact target, before-state binding, and idempotency identity of
the already-authorized write intent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_write_intent_guard_v1"
BLOCK_RESOURCE_ACTION_MISMATCH = "BLOCK_RESOURCE_ACTION_MISMATCH"
BLOCK_WRITE_BEFORE_STATE_MISMATCH = "BLOCK_WRITE_BEFORE_STATE_MISMATCH"
BLOCK_WRITE_AUTHORITY_MISSING = "BLOCK_WRITE_AUTHORITY_MISSING"


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _fp(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _normalize_intent(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("write_intent must be object")
    authority = raw.get("authorized", False)
    if not isinstance(authority, bool):
        raise ValueError("write_intent.authorized must be boolean")
    return {
        "intent_id": _nonempty(raw.get("intent_id"), "intent_id"),
        "resource_class": _nonempty(raw.get("resource_class"), "resource_class"),
        "operation_class": _nonempty(raw.get("operation_class"), "operation_class"),
        "exact_target": _nonempty(raw.get("exact_target"), "exact_target"),
        "before_state_fingerprint": _nonempty(raw.get("before_state_fingerprint"), "before_state_fingerprint"),
        "idempotency_key": _nonempty(raw.get("idempotency_key"), "idempotency_key"),
        "authorized": authority,
    }


def _normalize_action(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("actual_action must be object")
    return {
        "resource_class": _nonempty(raw.get("resource_class"), "resource_class"),
        "operation_class": _nonempty(raw.get("operation_class"), "operation_class"),
        "exact_target": _nonempty(raw.get("exact_target"), "exact_target"),
        "observed_before_state_fingerprint": _nonempty(raw.get("observed_before_state_fingerprint"), "observed_before_state_fingerprint"),
        "idempotency_key": _nonempty(raw.get("idempotency_key"), "idempotency_key"),
    }


def check(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("guard payload must be object")
    if payload.get("schema") not in {None, SCHEMA}:
        raise ValueError("invalid guard schema")
    intent = _normalize_intent(payload.get("write_intent"))
    action = _normalize_action(payload.get("actual_action"))
    codes: list[str] = []
    mismatches: list[str] = []

    if not intent["authorized"]:
        codes.append(BLOCK_WRITE_AUTHORITY_MISSING)
    for field in ("resource_class", "operation_class", "exact_target", "idempotency_key"):
        if intent[field] != action[field]:
            mismatches.append(field)
    if mismatches:
        codes.append(BLOCK_RESOURCE_ACTION_MISMATCH)
    if intent["before_state_fingerprint"] != action["observed_before_state_fingerprint"]:
        codes.append(BLOCK_WRITE_BEFORE_STATE_MISMATCH)

    body = {
        "schema": SCHEMA,
        "intent_id": intent["intent_id"],
        "allowed": not codes,
        "codes": codes,
        "mismatch_fields": mismatches,
        "write_executed": False,
        "authority_granted": False,
        "canon_write_granted": False,
        "framework_write_granted": False,
        "model_execution": False,
    }
    body["guard_fingerprint"] = _fp({"intent": intent, "action": action, "result": body})
    return body


def self_test() -> dict[str, Any]:
    fp = "sha256:" + "a" * 64
    intent = {
        "intent_id": "WI-1", "resource_class": "github_issue", "operation_class": "create",
        "exact_target": "xiaooye/repo#new", "before_state_fingerprint": fp,
        "idempotency_key": "issue:create:abc", "authorized": True,
    }
    exact = check({"schema": SCHEMA, "write_intent": intent, "actual_action": {
        "resource_class": "github_issue", "operation_class": "create", "exact_target": "xiaooye/repo#new",
        "observed_before_state_fingerprint": fp, "idempotency_key": "issue:create:abc"}})
    resource_mismatch = check({"schema": SCHEMA, "write_intent": intent, "actual_action": {
        "resource_class": "repository_content", "operation_class": "create_file", "exact_target": "xiaooye/repo/notes.md",
        "observed_before_state_fingerprint": fp, "idempotency_key": "issue:create:abc"}})
    stale = check({"schema": SCHEMA, "write_intent": intent, "actual_action": {
        "resource_class": "github_issue", "operation_class": "create", "exact_target": "xiaooye/repo#new",
        "observed_before_state_fingerprint": "sha256:" + "b" * 64, "idempotency_key": "issue:create:abc"}})
    noauth = check({"schema": SCHEMA, "write_intent": {**intent, "authorized": False}, "actual_action": {
        "resource_class": "github_issue", "operation_class": "create", "exact_target": "xiaooye/repo#new",
        "observed_before_state_fingerprint": fp, "idempotency_key": "issue:create:abc"}})
    ok = all([
        exact["allowed"],
        not resource_mismatch["allowed"] and BLOCK_RESOURCE_ACTION_MISMATCH in resource_mismatch["codes"],
        not stale["allowed"] and BLOCK_WRITE_BEFORE_STATE_MISMATCH in stale["codes"],
        not noauth["allowed"] and BLOCK_WRITE_AUTHORITY_MISSING in noauth["codes"],
        exact["write_executed"] is False and exact["authority_granted"] is False,
    ])
    return {
        "schema": SCHEMA,
        "write_intent_guard_contract": "PASS" if ok else "FAIL",
        "exact_match_allowed": exact["allowed"],
        "resource_action_mismatch_blocked": not resource_mismatch["allowed"],
        "stale_before_state_blocked": not stale["allowed"],
        "missing_authority_blocked": not noauth["allowed"],
        "write_executed": False,
        "authority_granted": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge write intent guard")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--input", required=True)
    sub.add_parser("self-test")
    ns = p.parse_args()
    out = self_test() if ns.cmd == "self-test" else check(json.loads(Path(ns.input).read_text(encoding="utf-8")))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("write_intent_guard_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
