#!/usr/bin/env python3
"""Deterministic QA observability for known-regression escapes.

This module never decides whether prose is bad. It records already-interpreted
mechanism identity plus expected/actual detection stage so NovelForge can tell a
new discovery from a known failure that escaped the manager quality loop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_known_regression_escape_v1"
DETECTION_STAGES = {
    "manager_self_audit",
    "reader_engagement",
    "continuity",
    "independent_review",
    "user",
    "post_delivery_audit",
    "unknown",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _refs(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{name} must be string array")
    return [x.strip() for x in value]


def record(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("escape payload must be object")
    candidate = _sha(payload.get("candidate_fingerprint"), "candidate_fingerprint")
    mechanism = _text(payload.get("failure_mechanism"), "failure_mechanism")
    expected = payload.get("where_it_should_have_been_caught")
    actual = payload.get("where_it_was_actually_detected")
    if expected not in DETECTION_STAGES:
        raise ValueError("where_it_should_have_been_caught invalid")
    if actual not in DETECTION_STAGES:
        raise ValueError("where_it_was_actually_detected invalid")
    previously_known = payload.get("previously_known")
    user_detected = payload.get("user_detected")
    if not isinstance(previously_known, bool) or not isinstance(user_detected, bool):
        raise ValueError("previously_known/user_detected must be boolean")
    known_refs = _refs(payload.get("known_evidence_refs", []), "known_evidence_refs")
    detection_refs = _refs(payload.get("detection_evidence_refs", []), "detection_evidence_refs")
    if previously_known and not known_refs:
        raise ValueError("previously_known=true requires known_evidence_refs")
    if user_detected and actual != "user":
        raise ValueError("user_detected=true requires actual detection stage=user")

    quality_loop_escape = bool(previously_known and actual != expected)
    user_regression_detector_escape = bool(previously_known and user_detected and expected != "user")
    body = {
        "schema": SCHEMA,
        "candidate_fingerprint": candidate,
        "failure_mechanism": mechanism,
        "where_it_should_have_been_caught": expected,
        "where_it_was_actually_detected": actual,
        "user_detected": user_detected,
        "previously_known": previously_known,
        "known_evidence_refs": known_refs,
        "detection_evidence_refs": detection_refs,
        "quality_loop_escape": quality_loop_escape,
        "user_regression_detector_escape": user_regression_detector_escape,
        "literary_verdict_created_by_runtime": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }
    body["receipt_fingerprint"] = _fp(body)
    return body


def validate(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return ["escape receipt must be object"]
    errors: list[str] = []
    if receipt.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    try:
        _sha(receipt.get("candidate_fingerprint"), "candidate_fingerprint")
        _text(receipt.get("failure_mechanism"), "failure_mechanism")
    except ValueError as exc:
        errors.append(str(exc))
    if receipt.get("where_it_should_have_been_caught") not in DETECTION_STAGES:
        errors.append("expected detection stage invalid")
    if receipt.get("where_it_was_actually_detected") not in DETECTION_STAGES:
        errors.append("actual detection stage invalid")
    if receipt.get("literary_verdict_created_by_runtime") is not False:
        errors.append("runtime must not create literary verdict")
    if receipt.get("authority") is not False:
        errors.append("receipt must be non-authoritative")
    perms = receipt.get("permissions", {})
    if not isinstance(perms, dict) or any(perms.get(k) is not False for k in ("canon_write", "framework_write", "durable_user_taste_write")):
        errors.append("write permissions must be false")
    body = {k: v for k, v in receipt.items() if k != "receipt_fingerprint"}
    if receipt.get("receipt_fingerprint") != _fp(body):
        errors.append("receipt_fingerprint mismatch")
    return errors


def self_test() -> dict[str, Any]:
    fp = "sha256:" + "a" * 64
    escape = record({
        "candidate_fingerprint": fp,
        "failure_mechanism": "synthetic_punchline_stacking",
        "where_it_should_have_been_caught": "manager_self_audit",
        "where_it_was_actually_detected": "user",
        "user_detected": True,
        "previously_known": True,
        "known_evidence_refs": ["regression:SYN-BANTER"],
        "detection_evidence_refs": ["feedback:round-2"],
    })
    discovery = record({
        "candidate_fingerprint": fp,
        "failure_mechanism": "new_unmodeled_mechanism",
        "where_it_should_have_been_caught": "unknown",
        "where_it_was_actually_detected": "user",
        "user_detected": True,
        "previously_known": False,
        "known_evidence_refs": [],
        "detection_evidence_refs": ["feedback:discovery"],
    })
    caught = record({
        "candidate_fingerprint": fp,
        "failure_mechanism": "synthetic_punchline_stacking",
        "where_it_should_have_been_caught": "manager_self_audit",
        "where_it_was_actually_detected": "manager_self_audit",
        "user_detected": False,
        "previously_known": True,
        "known_evidence_refs": ["regression:SYN-BANTER"],
        "detection_evidence_refs": ["self-audit:round-2"],
    })
    checks = {
        "known_user_detection_is_escape": escape["quality_loop_escape"] and escape["user_regression_detector_escape"],
        "new_discovery_not_mislabeled_escape": not discovery["quality_loop_escape"],
        "manager_catch_not_escape": not caught["quality_loop_escape"],
        "receipt_valid": not validate(escape),
        "runtime_does_not_judge_literature": escape["literary_verdict_created_by_runtime"] is False,
        "model_execution": escape["model_execution"] is False,
    }
    return {
        "schema": SCHEMA,
        "known_regression_escape_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge known-regression escape observability")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record")
    r.add_argument("--input", required=True)
    r.add_argument("--output")
    v = sub.add_parser("validate")
    v.add_argument("--input", required=True)
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        out = self_test()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["known_regression_escape_contract"] == "PASS" else 1
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.command == "record":
        out = record(raw)
        text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    errors = validate(raw)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
