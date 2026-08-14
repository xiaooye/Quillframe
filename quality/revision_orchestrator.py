#!/usr/bin/env python3
"""Multi-pass revision planning and finding aggregation for NovelForge 7.2.

Inspired by specialist-pass revision systems, but adapted to NovelForge's owning-
mechanism rules. This module does not perform literary judgment. It plans bounded
passes, tolerates unavailable passes, normalizes findings, deduplicates them, and
routes failures to the mechanism that owns the repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from quality.findings import validate_finding  # noqa:E402

SCHEMA = "novelforge_revision_orchestrator_v1"
PASSES: dict[str, dict[str, Any]] = {
    "continuity": {"requires": ["state_before", "state_after"], "execution": "deterministic", "tool": "quality/state_graph.py"},
    "character": {"requires": ["scene_excerpt", "character_snapshots"], "execution": "semantic_packaging", "tool": "quality/character_integrity.py"},
    "reader": {"requires": ["candidate_text"], "execution": "semantic_packaging", "tool": "quality/reader_panel.py"},
    "surface": {"requires": ["candidate_text"], "execution": "semantic_or_deterministic_adapter", "tool": None},
    "research_fact": {"requires": ["candidate_text", "research_context"], "execution": "optional_semantic", "tool": None},
}
SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}
REPAIR_ACTIONS = {
    "story": "return_to_story_or_plan",
    "plan": "return_to_plan",
    "scene": "rerun_scene_simulation",
    "character": "rerun_character_simulation",
    "reader": "rerun_reader_pressure_and_scene_simulation",
    "surface": "local_rewrite_or_scene_regeneration",
    "continuity": "repair_continuity_or_state_transition",
    "context": "rebuild_sparse_context",
    "memory": "invalidate_or_rebuild_derived_memory",
    "research": "research_or_fact_resolution",
    "runtime": "repair_runtime_transport_or_capability",
    "human": "request_human_editorial_decision",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _missing_value(value: Any) -> bool:
    """Treat only absent/empty prerequisites as missing; mappings like {} are valid state snapshots."""
    return value is None or value == "" or value == []


def plan_passes(available: dict[str, Any], requested: list[str] | None = None) -> dict[str, Any]:
    wanted = requested or list(PASSES)
    unknown = sorted(set(wanted) - set(PASSES))
    if unknown:
        raise ValueError("unknown passes: " + ", ".join(unknown))
    planned = []; skipped = []
    for name in wanted:
        spec = PASSES[name]
        missing = [key for key in spec["requires"] if _missing_value(available.get(key))]
        if missing:
            skipped.append({"pass": name, "reason": "missing_prerequisite", "missing": missing})
        else:
            planned.append({"pass": name, **spec})
    return {
        "schema": SCHEMA,
        "planned": planned,
        "skipped": skipped,
        "failure_isolation": True,
        "model_execution": False,
    }


def _finding_key(f: dict[str, Any]) -> str:
    payload = {
        "category": f.get("category"), "subject_id": f.get("subject_id"),
        "description": " ".join(str(f.get("description", "")).lower().split()),
        "repair_owner": f.get("repair_owner"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _merge_evidence(target: dict[str, Any], other: dict[str, Any]) -> None:
    for key in ("candidate_evidence", "authority_evidence"):
        seen = {(x.get("source_ref"), x.get("summary")) for x in target.get(key, []) if isinstance(x, dict)}
        for item in other.get(key, []):
            marker = (item.get("source_ref"), item.get("summary")) if isinstance(item, dict) else None
            if marker and marker not in seen:
                target.setdefault(key, []).append(item); seen.add(marker)
    refs = list(dict.fromkeys([*target.get("source_refs", []), *other.get("source_refs", [])]))
    target["source_refs"] = refs
    target["confidence"] = max(float(target.get("confidence", 0)), float(other.get("confidence", 0)))
    if SEVERITY_RANK.get(other.get("severity"), 9) < SEVERITY_RANK.get(target.get("severity"), 9):
        target["severity"] = other["severity"]


def _repair_queue(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        groups[finding["repair_owner"]].append(finding)
    queue = []
    for owner, items in groups.items():
        categories = Counter(x["category"] for x in items)
        action = REPAIR_ACTIONS[owner]
        # Surface clusters belong to scene regeneration rather than endless local patches.
        if owner == "surface" and len(items) >= 3:
            action = "regenerate_scene_surface_realization"
        # Reader flatness is explicitly not a line-edit problem.
        if owner == "reader" and any(x["category"] in {"safe_but_flat", "reader_grip", "forward_pull"} for x in items):
            action = "rerun_reader_pressure_and_scene_simulation"
        queue.append({
            "repair_owner": owner,
            "action": action,
            "finding_count": len(items),
            "categories": dict(categories),
            "highest_severity": min((x["severity"] for x in items), key=lambda s: SEVERITY_RANK.get(s, 9)),
            "finding_ids": [x["finding_id"] for x in items],
        })
    queue.sort(key=lambda x: (SEVERITY_RANK.get(x["highest_severity"], 9), -x["finding_count"], x["repair_owner"]))
    return queue


def aggregate(pass_reports: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pass_reports, dict):
        raise ValueError("pass_reports must be an object")
    findings_by_key: dict[str, dict[str, Any]] = {}
    passes_run = []; passes_skipped = []; diagnostics = {}
    invalid: list[str] = []
    for pass_name, report in pass_reports.items():
        if pass_name not in PASSES:
            invalid.append(f"unknown pass report: {pass_name}"); continue
        if report is None or (isinstance(report, dict) and report.get("status") in {"unsupported", "failed", "skipped"}):
            passes_skipped.append({"pass": pass_name, "reason": (report or {}).get("status", "missing") if isinstance(report, dict) else "missing"}); continue
        if not isinstance(report, dict):
            invalid.append(f"{pass_name}: report must be object"); continue
        passes_run.append(pass_name)
        diagnostics[pass_name] = {k: v for k, v in report.items() if k not in {"findings", "comparisons", "readers"}}
        raw_findings = report.get("findings", [])
        if not isinstance(raw_findings, list):
            invalid.append(f"{pass_name}: findings must be list"); continue
        for finding in raw_findings:
            if not isinstance(finding, dict):
                invalid.append(f"{pass_name}: finding must be object"); continue
            errors = validate_finding(finding)
            if errors:
                invalid.extend(f"{pass_name}/{finding.get('finding_id')}: {e}" for e in errors); continue
            key = _finding_key(finding)
            if key in findings_by_key:
                _merge_evidence(findings_by_key[key], finding)
            else:
                findings_by_key[key] = json.loads(json.dumps(finding, ensure_ascii=False))
    findings = list(findings_by_key.values())
    findings.sort(key=lambda f: (SEVERITY_RANK.get(f["severity"], 9), f["repair_owner"], f["category"], f["finding_id"]))
    return {
        "schema": "novelforge_revision_report_v1",
        "passes_run": passes_run,
        "passes_skipped": passes_skipped,
        "invalid_inputs": invalid,
        "total_findings": len(findings),
        "findings_by_severity": dict(Counter(f["severity"] for f in findings)),
        "findings_by_repair_owner": dict(Counter(f["repair_owner"] for f in findings)),
        "findings": findings,
        "diagnostics": diagnostics,
        "repair_queue": _repair_queue(findings),
        "authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    from quality.findings import make_finding
    base = make_finding(
        finding_id="F1", category="surface_fragmentation", severity="warning", repair_owner="surface", subject_id="SCN-1",
        description="Fragmented prose cluster.", candidate_evidence=[{"source_ref": "cand:1", "summary": "fragment"}], source_refs=["cand:1"], confidence=0.8,
    )
    duplicate = json.loads(json.dumps(base)); duplicate["finding_id"] = "F1B"; duplicate["candidate_evidence"].append({"source_ref": "cand:2", "summary": "same pattern"})
    # Recompute fingerprint after fixture mutation.
    from quality.findings import fingerprint_for
    duplicate["finding_fingerprint"] = fingerprint_for(duplicate)
    s2 = make_finding(finding_id="F2", category="over_explain", severity="warning", repair_owner="surface", subject_id="SCN-1", description="Narrator repeats shown meaning.", candidate_evidence=[{"source_ref": "cand:3", "summary": "repeat"}], source_refs=["cand:3"], confidence=0.9)
    s3 = make_finding(finding_id="F3", category="process_broadcast", severity="info", repair_owner="surface", subject_id="SCN-1", description="Procedure dominates scene.", candidate_evidence=[{"source_ref": "cand:4", "summary": "procedure"}], source_refs=["cand:4"], confidence=0.7)
    c1 = make_finding(finding_id="C1", category="knowledge_boundary", severity="error", repair_owner="character", subject_id="CHAR-1", description="Character knows unavailable fact.", candidate_evidence=[{"source_ref": "cand:5", "summary": "knows"}], authority_evidence=[{"source_ref": "canon:1", "summary": "not shared"}], source_refs=["cand:5", "canon:1"], confidence=0.95)
    plan = plan_passes({"candidate_text": "x", "state_before": {}, "state_after": {}, "scene_excerpt": "x", "character_snapshots": [{}]})
    report = aggregate({"surface": {"findings": [base, duplicate, s2, s3]}, "character": {"findings": [c1]}, "reader": {"status": "unsupported"}})
    surface = next(x for x in report["repair_queue"] if x["repair_owner"] == "surface")
    ok = (
        len(plan["planned"]) == 4 and any(x["pass"] == "research_fact" for x in plan["skipped"])
        and report["total_findings"] == 4 and surface["action"] == "regenerate_scene_surface_realization"
        and report["passes_skipped"][0]["pass"] == "reader" and report["invalid_inputs"] == []
    )
    dump({
        "revision_orchestrator_contract": "PASS" if ok else "FAIL", "narrow_pass_planning": True,
        "failure_isolation": True, "dedupe": report["total_findings"] == 4,
        "surface_cluster_regeneration": surface["action"] == "regenerate_scene_surface_realization",
        "authority": False, "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge multi-pass revision orchestrator")
    sub = p.add_subparsers(dest="command", required=True)
    pl = sub.add_parser("plan"); pl.add_argument("--available", required=True); pl.add_argument("--pass", action="append", dest="passes"); pl.add_argument("--output")
    ag = sub.add_parser("aggregate"); ag.add_argument("--reports", required=True); ag.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test": return self_test()
    if args.command == "plan": value = plan_passes(load_json(Path(args.available)), args.passes)
    else: value = aggregate(load_json(Path(args.reports)))
    dump(value, Path(args.output) if args.output else None); return 0 if not value.get("invalid_inputs") else 1


if __name__ == "__main__": raise SystemExit(main())
