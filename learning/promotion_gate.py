#!/usr/bin/env python3
"""NovelForge deterministic learning promotion prerequisite gate.

The gate evaluates evidence completeness. It NEVER edits Framework behavior,
Project Canon, or durable private user taste. A `promotable` result is a typed
proposal for an authorized manager/human workflow, not write authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_learning_promotion_candidate_v1"
SCOPES = {"one_off", "project", "user_taste", "general_craft"}
PASS_STATES = {"pass", "passed", "success", "green"}


def passed(value: Any) -> bool:
    if isinstance(value, bool): return value
    if isinstance(value, str): return value.lower() in PASS_STATES
    if isinstance(value, dict):
        for key in ("status", "result", "conclusion"):
            if key in value: return passed(value[key])
    return False


def nonempty_refs(value: Any) -> list[str]:
    if not isinstance(value, list): return []
    return list(dict.fromkeys(str(x) for x in value if str(x).strip()))


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if candidate.get("schema") != SCHEMA:
        blockers.append(f"schema must be {SCHEMA}")
    scope = candidate.get("scope")
    if scope not in SCOPES:
        blockers.append("invalid scope")
    mechanism = str(candidate.get("mechanism") or "").strip()
    if not mechanism:
        blockers.append("mechanism required")
    evidence = candidate.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}; blockers.append("evidence must be object")
    contradictions = int(evidence.get("open_contradictions", 0) or 0)
    if contradictions > 0:
        blockers.append("open contradictions must be resolved or scope narrowed")

    status = "blocked"
    if scope == "one_off":
        blockers.append("one_off scope is intentionally non-durable")
    elif scope == "project":
        if not evidence.get("explicit_project_authority", False):
            blockers.append("project activation requires explicit project authority")
        if not nonempty_refs(evidence.get("evidence_refs")):
            blockers.append("project activation requires traceable evidence_refs")
        if not blockers:
            status = "ready_for_activation"
    elif scope == "user_taste":
        explicit = int(evidence.get("explicit_user_evidence", 0) or 0)
        repeated = int(evidence.get("independent_consistent_corrections", 0) or 0)
        if explicit < 1 and repeated < 2:
            blockers.append("user_taste requires explicit evidence or at least two independent consistent corrections")
        if not passed(evidence.get("personalized_eval")):
            blockers.append("user_taste requires personalized eval evidence")
        if not nonempty_refs(evidence.get("evidence_refs")):
            blockers.append("user_taste requires traceable evidence_refs")
        if not evidence.get("applicability_boundary"):
            warnings.append("user_taste applicability boundary is empty; narrow scope when evidence supports it")
        if not blockers:
            status = "ready_for_activation"
    elif scope == "general_craft":
        cross_work = nonempty_refs(evidence.get("cross_work_refs"))
        counter = nonempty_refs(evidence.get("counterexample_refs"))
        if len(cross_work) < 3:
            blockers.append("general_craft requires at least three distinct cross-work evidence refs")
        if len(counter) < 1:
            blockers.append("general_craft requires at least one counterexample/contrast ref")
        if not evidence.get("profile_boundary"):
            blockers.append("general_craft requires explicit profile/applicability boundary")
        if not passed(evidence.get("capability_eval")):
            blockers.append("general_craft requires passing capability eval")
        if not passed(evidence.get("regression_eval")):
            blockers.append("general_craft requires passing regression eval")
        if not str(evidence.get("version_target") or "").strip():
            blockers.append("general_craft requires version_target")
        if not str(evidence.get("rollback_ref") or "").strip():
            blockers.append("general_craft requires rollback_ref")
        ci = evidence.get("framework_ci")
        if not passed(ci):
            blockers.append("general_craft requires green framework CI evidence")
        if isinstance(ci, dict) and not str(ci.get("commit") or "").strip():
            blockers.append("framework CI evidence must bind an exact commit")
        if not nonempty_refs(evidence.get("provenance_refs")):
            blockers.append("general_craft requires provenance_refs")
        if not blockers:
            status = "promotable"

    return {
        "schema": "novelforge_learning_promotion_gate_v1",
        "candidate_id": candidate.get("candidate_id"),
        "scope": scope,
        "mechanism": mechanism or None,
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "behavior_write_authority": False,
        "canon_write_authority": False,
        "durable_user_taste_write_authority": False,
        "next_action": (
            "authorized_manager_or_human_review" if status in {"promotable", "ready_for_activation"}
            else "repair_evidence_or_narrow_scope"
        ),
    }


def self_test() -> dict[str, Any]:
    incomplete = {
        "schema": SCHEMA, "candidate_id": "LCAND-BAD", "scope": "general_craft", "mechanism": "fixture",
        "evidence": {"cross_work_refs": ["A"], "framework_ci": {"conclusion": "success", "commit": "abc"}},
    }
    complete = {
        "schema": SCHEMA, "candidate_id": "LCAND-GOOD", "scope": "general_craft", "mechanism": "state change creates functional pace",
        "evidence": {
            "cross_work_refs": ["WORK-A", "WORK-B", "WORK-C"], "counterexample_refs": ["WORK-D"],
            "profile_boundary": {"exceptions": ["deliberate shock fragment"]},
            "capability_eval": {"result": "pass", "ref": "EVAL-CAP"},
            "regression_eval": {"result": "pass", "ref": "EVAL-REG"},
            "version_target": "7.1.0", "rollback_ref": "git:baseline", "open_contradictions": 0,
            "framework_ci": {"conclusion": "success", "commit": "0123456789abcdef0123456789abcdef01234567"},
            "provenance_refs": ["SRC-1", "SRC-2"],
        },
    }
    bad = evaluate(incomplete); good = evaluate(complete)
    user_bad = evaluate({
        "schema": SCHEMA, "candidate_id": "UT-BAD", "scope": "user_taste", "mechanism": "fixture",
        "evidence": {"explicit_user_evidence": 0, "independent_consistent_corrections": 1, "personalized_eval": "pass", "evidence_refs": ["E"]},
    })
    ok = (
        bad["status"] == "blocked" and len(bad["blockers"]) >= 5
        and good["status"] == "promotable" and not good["blockers"]
        and user_bad["status"] == "blocked"
        and good["behavior_write_authority"] is False and good["canon_write_authority"] is False
    )
    return {
        "promotion_gate_contract": "PASS" if ok else "FAIL",
        "general_craft_prerequisites_enforced": bad["status"] == "blocked" and good["status"] == "promotable",
        "user_taste_evidence_threshold_enforced": user_bad["status"] == "blocked",
        "auto_behavior_write": False,
        "auto_canon_write": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge learning promotion prerequisite gate")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate"); e.add_argument("--candidate", required=True); e.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["promotion_gate_contract"] == "PASS" else 1
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8")); result = evaluate(candidate)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output: Path(args.output).write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
