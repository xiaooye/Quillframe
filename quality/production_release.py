#!/usr/bin/env python3
"""Final structural release aggregation for NovelForge production candidates.

`quality.production_readiness` remains the owner of semantic/surface/continuity
quality gates. This wrapper prevents a valid semantic PASS from becoming release
permission when a production policy also requires structural receipts such as a
context-assembly or closed-loop execution binding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from candidate_qualification import validate_qualification_receipt

SCHEMA = "novelforge_production_release_v1"
READINESS_SCHEMA = "novelforge_production_readiness_v1"
STATUSES = {"pass", "fail", "pending"}


def _fp_value(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256 fingerprint")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256 fingerprint") from exc
    return value


def aggregate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("release payload must be object")
    readiness = payload.get("production_readiness")
    if not isinstance(readiness, dict) or readiness.get("schema") != READINESS_SCHEMA:
        raise ValueError("validated production_readiness result required")
    candidate = _sha(readiness.get("candidate_fingerprint"), "candidate_fingerprint")
    base_ready = readiness.get("ready_for_user_visible_review")
    if not isinstance(base_ready, bool):
        raise ValueError("production_readiness ready flag required")
    readiness_policy = readiness.get("policy", {}) if isinstance(readiness.get("policy"), dict) else {}
    require_independent = readiness_policy.get("require_independent_semantic") is True
    qualification = payload.get("pre_independent_qualification")
    qualification_fp = None
    if require_independent:
        errors = validate_qualification_receipt(qualification, candidate_fingerprint=candidate, require_qualified=True)
        if errors:
            raise ValueError("pre_independent_qualification invalid at release: " + "; ".join(errors))
        qualification_fp = qualification.get("receipt_fingerprint")

    policy = payload.get("structural_policy", {})
    if not isinstance(policy, dict):
        raise ValueError("structural_policy must be object")
    required = policy.get("required_receipts", [])
    if not isinstance(required, list) or any(not isinstance(x, str) or not x for x in required):
        raise ValueError("required_receipts must be string array")
    if len(required) != len(set(required)):
        raise ValueError("required_receipts must be unique")

    raw_receipts = payload.get("structural_receipts", [])
    if not isinstance(raw_receipts, list):
        raise ValueError("structural_receipts must be array")
    receipts: dict[str, dict[str, Any]] = {}
    for raw in raw_receipts:
        if not isinstance(raw, dict):
            raise ValueError("structural receipt must be object")
        kind = raw.get("kind")
        if not isinstance(kind, str) or not kind:
            raise ValueError("structural receipt kind required")
        if kind in receipts:
            raise ValueError(f"duplicate structural receipt: {kind}")
        status = raw.get("status")
        if status not in STATUSES:
            raise ValueError(f"invalid structural receipt status: {kind}")
        receipt_candidate = _sha(raw.get("candidate_fingerprint"), f"{kind}.candidate_fingerprint")
        if receipt_candidate != candidate:
            raise ValueError(f"structural receipt candidate mismatch: {kind}")
        receipt_fp = _sha(raw.get("receipt_fingerprint"), f"{kind}.receipt_fingerprint")
        refs = raw.get("evidence_refs", [])
        if not isinstance(refs, list) or any(not isinstance(x, str) or not x for x in refs):
            raise ValueError(f"{kind}.evidence_refs must be string array")
        receipts[kind] = {
            "kind": kind,
            "status": status,
            "candidate_fingerprint": candidate,
            "receipt_fingerprint": receipt_fp,
            "evidence_refs": refs,
        }

    missing = [x for x in required if x not in receipts]
    blocking = [x for x in required if x in receipts and receipts[x]["status"] == "fail"]
    pending = missing + [x for x in required if x in receipts and receipts[x]["status"] == "pending"]
    structural_ready = not blocking and not pending and all(receipts[x]["status"] == "pass" for x in required)
    final_ready = base_ready and structural_ready

    body = {
        "schema": SCHEMA,
        "candidate_fingerprint": candidate,
        "production_readiness_fingerprint": _fp_value(readiness),
        "base_production_readiness": base_ready,
        "pre_independent_qualification_required": require_independent,
        "pre_independent_qualification_fingerprint": qualification_fp,
        "independent_pass_can_override_qualification_failure": False,
        "required_structural_receipts": required,
        "structural_receipts": [receipts[k] for k in sorted(receipts)],
        "missing_structural_receipts": missing,
        "blocking_structural_receipts": blocking,
        "pending_structural_receipts": pending,
        "structural_ready": structural_ready,
        "ready_for_user_visible_review": final_ready,
        "semantic_pass_can_override_missing_structural_receipt": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False},
        "model_execution": False,
    }
    body["release_fingerprint"] = _fp_value(body)
    return body


def self_test() -> dict[str, Any]:
    fp = "sha256:" + "a" * 64
    receipt_fp = "sha256:" + "b" * 64
    readiness = {"schema": READINESS_SCHEMA, "candidate_fingerprint": fp, "ready_for_user_visible_review": True}
    missing = aggregate({"production_readiness": readiness, "structural_policy": {"required_receipts": ["context_assembly"]}, "structural_receipts": []})
    present = aggregate({"production_readiness": readiness, "structural_policy": {"required_receipts": ["context_assembly"]}, "structural_receipts": [{"kind": "context_assembly", "status": "pass", "candidate_fingerprint": fp, "receipt_fingerprint": receipt_fp, "evidence_refs": ["CTX-R1"]}]})
    base_fail = aggregate({"production_readiness": {**readiness, "ready_for_user_visible_review": False}, "structural_policy": {"required_receipts": ["context_assembly"]}, "structural_receipts": [{"kind": "context_assembly", "status": "pass", "candidate_fingerprint": fp, "receipt_fingerprint": receipt_fp, "evidence_refs": ["CTX-R1"]}]})
    ok = all([
        not missing["ready_for_user_visible_review"] and "context_assembly" in missing["missing_structural_receipts"],
        present["ready_for_user_visible_review"],
        not base_fail["ready_for_user_visible_review"],
        present["semantic_pass_can_override_missing_structural_receipt"] is False,
    ])
    return {
        "schema": SCHEMA,
        "production_release_contract": "PASS" if ok else "FAIL",
        "reviewer_pass_missing_structural_receipt_blocks": not missing["ready_for_user_visible_review"],
        "all_required_receipts_pass": present["ready_for_user_visible_review"],
        "base_quality_failure_still_blocks": not base_fail["ready_for_user_visible_review"],
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge final production release aggregator")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("aggregate"); a.add_argument("--input", required=True)
    sub.add_parser("self-test")
    ns = p.parse_args()
    out = self_test() if ns.cmd == "self-test" else aggregate(json.loads(Path(ns.input).read_text(encoding="utf-8")))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("production_release_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
