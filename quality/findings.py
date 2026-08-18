#!/usr/bin/env python3
"""Normalized evidence-chained quality findings for Quillframe 7.2.

Deterministic only. Findings are observations/proposals and never grant Canon,
Framework-behavior, or durable user-taste write authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

SCHEMA = "quillframe_quality_finding_v1"
SEVERITIES = {"error", "warning", "info"}
REPAIR_OWNERS = {
    "story", "plan", "scene", "character", "reader", "surface",
    "continuity", "context", "memory", "research", "runtime", "human",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint_payload(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "finding_id": finding.get("finding_id"),
        "category": finding.get("category"),
        "severity": finding.get("severity"),
        "repair_owner": finding.get("repair_owner"),
        "subject_id": finding.get("subject_id"),
        "description": finding.get("description"),
        "candidate_evidence": finding.get("candidate_evidence", []),
        "authority_evidence": finding.get("authority_evidence", []),
        "source_refs": finding.get("source_refs", []),
    }


def fingerprint_for(finding: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(fingerprint_payload(finding))).hexdigest()


def _normalize_evidence(items: Any) -> list[dict[str, Any]]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError("evidence must be a list")
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("evidence item must be an object")
        ref = item.get("source_ref")
        summary = item.get("summary")
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("evidence.source_ref is required")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("evidence.summary is required")
        normalized: dict[str, Any] = {"source_ref": ref.strip(), "summary": summary.strip()}
        fp = item.get("fingerprint")
        if fp is not None:
            if not isinstance(fp, str) or not fp.startswith("sha256:"):
                raise ValueError("evidence.fingerprint must be sha256:* when present")
            normalized["fingerprint"] = fp
        out.append(normalized)
    return out


def make_finding(
    *, finding_id: str, category: str, severity: str, repair_owner: str,
    subject_id: str, description: str,
    candidate_evidence: list[dict[str, Any]] | None = None,
    authority_evidence: list[dict[str, Any]] | None = None,
    source_refs: list[str] | None = None, confidence: float = 1.0,
    proposal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    if repair_owner not in REPAIR_OWNERS:
        raise ValueError(f"invalid repair_owner: {repair_owner}")
    if not all(isinstance(x, str) and x.strip() for x in (finding_id, category, subject_id, description)):
        raise ValueError("finding_id/category/subject_id/description must be non-empty strings")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise ValueError("confidence must be 0..1")
    refs = source_refs or []
    if not isinstance(refs, list) or not all(isinstance(x, str) and x.strip() for x in refs):
        raise ValueError("source_refs must contain non-empty strings")
    finding: dict[str, Any] = {
        "schema": SCHEMA,
        "finding_id": finding_id.strip(),
        "category": category.strip(),
        "severity": severity,
        "repair_owner": repair_owner,
        "subject_id": subject_id.strip(),
        "description": description.strip(),
        "candidate_evidence": _normalize_evidence(candidate_evidence),
        "authority_evidence": _normalize_evidence(authority_evidence),
        "source_refs": [x.strip() for x in refs],
        "confidence": float(confidence),
        "authority": False,
        "proposal_only": True,
        "permissions": {
            "canon_write": False,
            "framework_write": False,
            "durable_user_taste_write": False,
        },
    }
    if proposal is not None:
        if not isinstance(proposal, dict):
            raise ValueError("proposal must be an object")
        finding["proposal"] = proposal
    finding["finding_fingerprint"] = fingerprint_for(finding)
    return finding


def validate_finding(finding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if finding.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    if finding.get("severity") not in SEVERITIES:
        errors.append("invalid severity")
    if finding.get("repair_owner") not in REPAIR_OWNERS:
        errors.append("invalid repair_owner")
    for key in ("finding_id", "category", "subject_id", "description"):
        if not isinstance(finding.get(key), str) or not finding[key].strip():
            errors.append(f"{key} required")
    confidence = finding.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        errors.append("confidence must be 0..1")
    if finding.get("authority") is not False or finding.get("proposal_only") is not True:
        errors.append("finding must be non-authoritative proposal evidence")
    perms = finding.get("permissions", {})
    if any(perms.get(k) is not False for k in ("canon_write", "framework_write", "durable_user_taste_write")):
        errors.append("finding permissions must all be false")
    try:
        _normalize_evidence(finding.get("candidate_evidence", []))
        _normalize_evidence(finding.get("authority_evidence", []))
    except ValueError as exc:
        errors.append(str(exc))
    if finding.get("finding_fingerprint") != fingerprint_for(finding):
        errors.append("finding_fingerprint mismatch")
    return errors


def self_test() -> int:
    item = make_finding(
        finding_id="F-1", category="knowledge_boundary", severity="error",
        repair_owner="character", subject_id="CHAR-1",
        description="Character uses information not established as known.",
        candidate_evidence=[{"source_ref": "candidate:1", "summary": "Uses the secret."}],
        authority_evidence=[{"source_ref": "canon:INFO-1", "summary": "Secret belongs to CHAR-2 only."}],
        source_refs=["candidate:1", "canon:INFO-1"], confidence=0.95,
    )
    tampered = dict(item); tampered["description"] = "changed"
    ok = not validate_finding(item) and "finding_fingerprint mismatch" in validate_finding(tampered)
    print(json.dumps({
        "quality_finding_contract": "PASS" if ok else "FAIL",
        "fingerprint_bound": True,
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe normalized quality findings")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
