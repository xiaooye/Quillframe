#!/usr/bin/env python3
"""Combine deterministic and semantic narrative verification evidence.

Deterministic state-graph findings and model-owned narrative findings share the
NovelForge finding contract but retain distinct provenance/repair ownership.
A semantic issues-found judgment is valid evidence, not a transport failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.findings import make_finding, validate_finding  # noqa: E402

SCHEMA = "novelforge_narrative_verification_v1"
CONTRACT = "narrative.verify"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} required")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    value = _text(value, name)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} invalid hex") from exc
    return value


def _semantic_findings(result: dict[str, Any], candidate_fingerprint: str) -> tuple[str, list[dict[str, Any]]]:
    if result.get("candidate_fingerprint") != candidate_fingerprint:
        raise ValueError("semantic candidate fingerprint mismatch")
    verdict = result.get("verdict")
    if verdict not in {"clear", "issues_found"}:
        raise ValueError("semantic verdict must be clear|issues_found")
    rows = result.get("findings", [])
    if not isinstance(rows, list):
        raise ValueError("semantic findings must be list")
    if verdict == "clear" and rows:
        raise ValueError("clear verdict cannot contain findings")
    if verdict == "issues_found" and not rows:
        raise ValueError("issues_found verdict requires findings")

    findings: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError("semantic finding must be object")
        finding = make_finding(
            finding_id=f"NARR-{index}",
            category=_text(row.get("category"), f"finding[{index}].category"),
            severity=row.get("severity"),
            repair_owner=row.get("repair_owner"),
            subject_id=_text(row.get("subject_id"), f"finding[{index}].subject_id"),
            description=_text(row.get("description"), f"finding[{index}].description"),
            candidate_evidence=row.get("candidate_evidence", []),
            authority_evidence=row.get("authority_evidence", []),
            source_refs=row.get("source_refs", []),
            confidence=row.get("confidence", 1.0),
            proposal={"semantic_owner": "model", "direct_mutation": False},
        )
        errors = validate_finding(finding)
        if errors:
            raise ValueError("invalid normalized finding: " + "; ".join(errors))
        findings.append(finding)
    return verdict, findings


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    candidate_fingerprint = _sha(payload.get("candidate_fingerprint"), "candidate_fingerprint")

    delta = payload.get("candidate_state_delta")
    if not isinstance(delta, dict) or delta.get("schema") != "novelforge_candidate_state_delta_v1":
        raise ValueError("candidate_state_delta v1 required")
    if delta.get("candidate_fingerprint") != candidate_fingerprint:
        raise ValueError("candidate state delta fingerprint mismatch")

    deterministic = payload.get("deterministic_report")
    if not isinstance(deterministic, dict) or deterministic.get("schema") != "novelforge_state_graph_diff_v1":
        raise ValueError("state graph diff report required")
    deterministic_findings = deterministic.get("findings", [])
    if not isinstance(deterministic_findings, list):
        raise ValueError("deterministic findings must be list")
    for finding in deterministic_findings:
        errors = validate_finding(finding)
        if errors:
            raise ValueError("invalid deterministic finding: " + "; ".join(errors))

    semantic = payload.get("semantic_result")
    if not isinstance(semantic, dict):
        raise ValueError("semantic_result required")
    if semantic.get("contract_id") != CONTRACT:
        raise ValueError(f"semantic contract must be {CONTRACT}")
    if semantic.get("status") != "completed":
        raise ValueError("semantic result must be completed")
    semantic_input_fingerprint = _sha(semantic.get("input_fingerprint"), "semantic_result.input_fingerprint")
    expected = payload.get("expected_semantic_input_fingerprint")
    if expected is not None and semantic_input_fingerprint != _sha(expected, "expected_semantic_input_fingerprint"):
        raise ValueError("semantic input fingerprint mismatch")
    semantic_result = semantic.get("result")
    if not isinstance(semantic_result, dict):
        raise ValueError("semantic_result.result required")
    semantic_verdict, semantic_findings = _semantic_findings(semantic_result, candidate_fingerprint)

    findings = deterministic_findings + semantic_findings
    core = {
        "candidate_fingerprint": candidate_fingerprint,
        "candidate_delta_fingerprint": delta.get("delta_fingerprint"),
        "deterministic_report_ref": {
            "before_snapshot_id": deterministic.get("before_snapshot_id"),
            "after_snapshot_id": deterministic.get("after_snapshot_id"),
        },
        "semantic_input_fingerprint": semantic_input_fingerprint,
        "semantic_result_fingerprint": fingerprint(semantic_result),
        "semantic_verdict": semantic_verdict,
        "deterministic_findings": deterministic_findings,
        "semantic_findings": semantic_findings,
        "findings": findings,
    }
    return {
        "schema": SCHEMA,
        **core,
        "verification_fingerprint": fingerprint(core),
        "status": "issues_found" if findings else "clear",
        "deterministic_finding_count": len(deterministic_findings),
        "semantic_finding_count": len(semantic_findings),
        "semantic_reject_is_transport_failure": False,
        "authority": False,
        "canon_write": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    candidate = "sha256:" + "a" * 64
    deterministic_finding = make_finding(
        finding_id="STATE-1",
        category="unexplained_state_change",
        severity="warning",
        repair_owner="continuity",
        subject_id="CHAR-A",
        description="Location changed without transition.",
        candidate_evidence=[{"source_ref": "candidate:A", "summary": "street"}],
        authority_evidence=[{"source_ref": "canon:A", "summary": "hall"}],
        source_refs=["candidate:A", "canon:A"],
    )
    payload = {
        "candidate_fingerprint": candidate,
        "candidate_state_delta": {
            "schema": "novelforge_candidate_state_delta_v1",
            "candidate_fingerprint": candidate,
            "delta_fingerprint": "sha256:" + "b" * 64,
        },
        "deterministic_report": {
            "schema": "novelforge_state_graph_diff_v1",
            "before_snapshot_id": "S1",
            "after_snapshot_id": "S2",
            "findings": [deterministic_finding],
        },
        "expected_semantic_input_fingerprint": "sha256:" + "c" * 64,
        "semantic_result": {
            "contract_id": CONTRACT,
            "status": "completed",
            "input_fingerprint": "sha256:" + "c" * 64,
            "result": {
                "candidate_fingerprint": candidate,
                "verdict": "issues_found",
                "findings": [{
                    "category": "knowledge_boundary",
                    "severity": "error",
                    "repair_owner": "character",
                    "subject_id": "CHAR-B",
                    "description": "Character uses unavailable evidence.",
                    "candidate_evidence": [{"source_ref": "candidate:p2", "summary": "Uses secret"}],
                    "authority_evidence": [{"source_ref": "canon:INFO", "summary": "Not yet known"}],
                    "source_refs": ["candidate:p2", "canon:INFO"],
                    "confidence": 0.95,
                }],
            },
        },
    }
    report = build_report(payload)
    combined = len(report["findings"]) == 2 and report["status"] == "issues_found"
    reject_semantics = report["semantic_reject_is_transport_failure"] is False
    mismatch = False
    bad = json.loads(json.dumps(payload))
    bad["semantic_result"]["result"]["candidate_fingerprint"] = "sha256:" + "d" * 64
    try:
        build_report(bad)
    except ValueError:
        mismatch = True
    ok = combined and reject_semantics and mismatch and report["authority"] is False
    print(json.dumps({
        "narrative_verification_contract": "PASS" if ok else "FAIL",
        "combined_findings": combined,
        "semantic_reject_is_transport_failure": report["semantic_reject_is_transport_failure"],
        "candidate_fingerprint_guard": mismatch,
        "non_authoritative": report["authority"] is False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge layered narrative verification")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--input", required=True)
    build_parser.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    report = build_report(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
