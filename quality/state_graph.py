#!/usr/bin/env python3
"""Derived scene/world state graph diffing for NovelForge 7.2.

The graph is a verification view, never a second Canon authority. Deterministic
logic reports stable-field contradictions and unexplained changes; narrative
plausibility remains semantic work.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from quality.findings import make_finding, validate_finding  # noqa:E402

SCHEMA = "novelforge_state_graph_v1"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot_id = snapshot.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ValueError("snapshot_id required")
    nodes_raw = snapshot.get("nodes", [])
    edges_raw = snapshot.get("edges", [])
    transitions_raw = snapshot.get("transitions", [])
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list) or not isinstance(transitions_raw, list):
        raise ValueError("nodes/edges/transitions must be lists")
    nodes: dict[str, dict[str, Any]] = {}
    for raw in nodes_raw:
        if not isinstance(raw, dict):
            raise ValueError("node must be object")
        node_id = raw.get("id")
        if not isinstance(node_id, str) or not node_id.strip() or node_id in nodes:
            raise ValueError("node ids must be unique non-empty strings")
        attrs = raw.get("attributes", {})
        stable = raw.get("stable_fields", [])
        if not isinstance(attrs, dict) or not isinstance(stable, list) or not all(isinstance(x, str) for x in stable):
            raise ValueError(f"invalid node attributes/stable_fields: {node_id}")
        nodes[node_id] = {
            "id": node_id,
            "type": raw.get("type", "entity"),
            "attributes": attrs,
            "stable_fields": stable,
            "source_ref": raw.get("source_ref") or f"snapshot:{snapshot_id}:{node_id}",
        }
    edges: list[dict[str, Any]] = []
    for raw in edges_raw:
        if not isinstance(raw, dict):
            raise ValueError("edge must be object")
        source = raw.get("source"); target = raw.get("target"); relation = raw.get("relation")
        if not all(isinstance(x, str) and x.strip() for x in (source, target, relation)):
            raise ValueError("edge source/target/relation required")
        edges.append({"source": source, "target": target, "relation": relation, "attributes": raw.get("attributes", {}), "source_ref": raw.get("source_ref") or f"snapshot:{snapshot_id}:edge:{source}:{relation}:{target}"})
    transitions: list[dict[str, Any]] = []
    for raw in transitions_raw:
        if not isinstance(raw, dict):
            raise ValueError("transition must be object")
        node_id = raw.get("node_id"); field = raw.get("field"); evidence_ref = raw.get("evidence_ref")
        if not all(isinstance(x, str) and x.strip() for x in (node_id, field, evidence_ref)):
            raise ValueError("transition node_id/field/evidence_ref required")
        transitions.append({
            "node_id": node_id, "field": field,
            "from": raw.get("from"), "to": raw.get("to"),
            "evidence_ref": evidence_ref,
        })
    return {
        "schema": SCHEMA,
        "snapshot_id": snapshot_id,
        "nodes": nodes,
        "edges": edges,
        "transitions": transitions,
        "derived": True,
        "authority": False,
    }


def _transition_for(after: dict[str, Any], node_id: str, field: str, before_value: Any, after_value: Any) -> dict[str, Any] | None:
    for tr in after["transitions"]:
        if tr["node_id"] == node_id and tr["field"] == field and tr.get("from") == before_value and tr.get("to") == after_value:
            return tr
    return None


def diff(before_snapshot: dict[str, Any], after_snapshot: dict[str, Any]) -> dict[str, Any]:
    before = normalize_snapshot(before_snapshot)
    after = normalize_snapshot(after_snapshot)
    findings = []
    explained = []
    idx = 0
    for node_id in sorted(set(before["nodes"]).intersection(after["nodes"])):
        b = before["nodes"][node_id]
        a = after["nodes"][node_id]
        fields = sorted(set(b["attributes"]).union(a["attributes"]))
        stable = set(b["stable_fields"]).union(a["stable_fields"])
        for field in fields:
            old = b["attributes"].get(field)
            new = a["attributes"].get(field)
            if old == new:
                continue
            transition = _transition_for(after, node_id, field, old, new)
            if transition:
                explained.append({"node_id": node_id, "field": field, "from": old, "to": new, "evidence_ref": transition["evidence_ref"]})
                continue
            idx += 1
            is_stable = field in stable
            category = "stable_state_contradiction" if is_stable else "unexplained_state_change"
            severity = "error" if is_stable else "warning"
            repair_owner = "continuity"
            finding = make_finding(
                finding_id=f"STATE-{idx}",
                category=category,
                severity=severity,
                repair_owner=repair_owner,
                subject_id=node_id,
                description=(
                    f"Stable field {field!r} changed without transition evidence."
                    if is_stable else f"State field {field!r} changed without transition evidence."
                ),
                candidate_evidence=[{"source_ref": a["source_ref"], "summary": f"after {field}={new!r}"}],
                authority_evidence=[{"source_ref": b["source_ref"], "summary": f"before {field}={old!r}"}],
                source_refs=[b["source_ref"], a["source_ref"]],
                confidence=1.0,
                proposal={"required_transition_evidence": True, "direct_mutation": False},
            )
            findings.append(finding)
    return {
        "schema": "novelforge_state_graph_diff_v1",
        "before_snapshot_id": before["snapshot_id"],
        "after_snapshot_id": after["snapshot_id"],
        "findings": findings,
        "explained_transitions": explained,
        "derived": True,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    before = {
        "snapshot_id": "S1",
        "nodes": [{"id": "CHAR-1", "type": "character", "attributes": {"eye_color": "brown", "location": "hall", "trust": 1}, "stable_fields": ["eye_color"], "source_ref": "canon:CHAR-1@S1"}],
        "edges": [], "transitions": [],
    }
    after = {
        "snapshot_id": "S2",
        "nodes": [{"id": "CHAR-1", "type": "character", "attributes": {"eye_color": "blue", "location": "yard", "trust": 2}, "stable_fields": ["eye_color"], "source_ref": "candidate:CHAR-1@S2"}],
        "edges": [],
        "transitions": [
            {"node_id": "CHAR-1", "field": "location", "from": "hall", "to": "yard", "evidence_ref": "event:walk-out"},
            {"node_id": "CHAR-1", "field": "trust", "from": 1, "to": 2, "evidence_ref": "event:confession"},
        ],
    }
    report = diff(before, after)
    categories = [x["category"] for x in report["findings"]]
    stable_detected = categories == ["stable_state_contradiction"]
    transitions_explained = {x["field"] for x in report["explained_transitions"]} == {"location", "trust"}
    findings_valid = all(not validate_finding(x) for x in report["findings"])
    ok = stable_detected and transitions_explained and findings_valid and report["authority"] is False
    dump({
        "state_graph_contract": "PASS" if ok else "FAIL",
        "stable_contradiction_detected": stable_detected,
        "evidence_backed_transition_exempted": transitions_explained,
        "evidence_chained_findings": findings_valid,
        "derived_authority": False,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge derived state graph audit")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("diff"); d.add_argument("--before", required=True); d.add_argument("--after", required=True); d.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    report = diff(load_json(Path(args.before)), load_json(Path(args.after)))
    dump(report, Path(args.output) if args.output else None)
    return 0 if not report["findings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
