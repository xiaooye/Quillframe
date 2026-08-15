#!/usr/bin/env python3
"""Explain one NovelForge context build without inventing relevance scores.

The trace combines deterministic Inspector eligibility, optional model-owned
`context.select` evidence, and deterministic memory-tier packing into one
non-authoritative explanation of what was loaded and why.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_context_trace_v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _ids(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            out.append(item["id"])
    return out


def build_trace(
    inspector: dict[str, Any],
    memory_tiers: dict[str, Any] | None = None,
    semantic_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(inspector, dict) or inspector.get("schema") != "novelforge_context_inspector_v2":
        raise ValueError("context inspector v2 snapshot required")
    items_raw = inspector.get("items", [])
    if not isinstance(items_raw, list):
        raise ValueError("inspector.items must be list")

    semantic_fp = None
    semantic_tiers: dict[str, str] = {}
    semantic_reasons: dict[str, Any] = {}
    if semantic_result is not None:
        if not isinstance(semantic_result, dict):
            raise ValueError("semantic_result must be object")
        semantic_fp = semantic_result.get("input_fingerprint")
        judgment = semantic_result.get("judgment", {}) if isinstance(semantic_result.get("judgment", {}), dict) else {}
        for tier, key in (("hot", "hot_ids"), ("working", "working_ids"), ("archive", "archive_ids")):
            values = judgment.get(key, [])
            if isinstance(values, list):
                for item_id in values:
                    if isinstance(item_id, str):
                        semantic_tiers[item_id] = tier
        reasons = judgment.get("reasons", [])
        if isinstance(reasons, list):
            for row in reasons:
                if isinstance(row, dict) and isinstance(row.get("block_id"), str):
                    semantic_reasons[row["block_id"]] = row.get("reason")

    loaded_hot: list[str] = []
    loaded_working: list[str] = []
    archive: list[str] = []
    visibility_excluded: list[str] = []
    temporal_excluded: list[str] = []
    invalidated: list[str] = []
    skipped: dict[str, str] = {}
    budgets = None
    used = None

    if memory_tiers is not None:
        if memory_tiers.get("schema") != "novelforge_memory_tiers_v4":
            raise ValueError("memory tiers v4 report required")
        selection_fp = memory_tiers.get("selection_fingerprint")
        if semantic_fp is not None and selection_fp is not None and semantic_fp != selection_fp:
            raise ValueError("semantic result / memory tier selection fingerprint mismatch")
        selected = memory_tiers.get("selected", {}) if isinstance(memory_tiers.get("selected", {}), dict) else {}
        loaded_hot = _ids(selected.get("hot", []))
        loaded_working = _ids(selected.get("working", []))
        archive = [item for item in memory_tiers.get("archive", []) if isinstance(item, str)]
        visibility_excluded = [item for item in memory_tiers.get("visibility_excluded", []) if isinstance(item, str)]
        temporal_excluded = [item for item in memory_tiers.get("temporal_excluded", []) if isinstance(item, str)]
        invalidated = [item for item in memory_tiers.get("invalidated", []) if isinstance(item, str)]
        skipped_root = memory_tiers.get("skipped", {}) if isinstance(memory_tiers.get("skipped", {}), dict) else {}
        for tier in ("hot", "working"):
            rows = skipped_root.get(tier, [])
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and isinstance(row.get("id"), str):
                        skipped[row["id"]] = row.get("reason") or "budget_skip"
        budgets = memory_tiers.get("budgets")
        used = memory_tiers.get("used")

    loaded = set(loaded_hot + loaded_working)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in items_raw:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
            raise ValueError("inspector item id required")
        item_id = raw["id"]
        if item_id in seen:
            raise ValueError("duplicate inspector item id")
        seen.add(item_id)
        exclusions: list[str] = []
        if not raw.get("eligible", False):
            exclusions.append("inspector_ineligible")
        if raw.get("hidden"):
            exclusions.append("author_hidden")
        if raw.get("invalidated") or item_id in invalidated:
            exclusions.append("invalidated")
        if item_id in visibility_excluded:
            exclusions.append("perspective_visibility")
        if item_id in temporal_excluded:
            exclusions.append("future_story_order")
        if item_id in skipped:
            exclusions.append(skipped[item_id])
        loaded_tier = "hot" if item_id in loaded_hot else ("working" if item_id in loaded_working else None)
        rows.append({
            "id": item_id,
            "class": raw.get("class"),
            "source": raw.get("source"),
            "source_fingerprint": raw.get("source_fingerprint"),
            "authority": raw.get("authority"),
            "inclusion_reason": raw.get("inclusion_reason"),
            "stages": raw.get("stages", []),
            "priority": raw.get("priority", 0),
            "pinned": bool(raw.get("pinned", False)),
            "derived": bool(raw.get("derived", False)),
            "hidden": bool(raw.get("hidden", False)),
            "invalidated": bool(raw.get("invalidated", False)),
            "eligible": bool(raw.get("eligible", False)),
            "semantic_tier": semantic_tiers.get(item_id),
            "semantic_reason": semantic_reasons.get(item_id),
            "loaded": item_id in loaded,
            "loaded_tier": loaded_tier,
            "archived": item_id in archive,
            "exclusion_reasons": exclusions,
        })

    payload = {
        "manifest_id": inspector.get("manifest_id"),
        "stage": inspector.get("stage"),
        "items": rows,
        "semantic_selection_fingerprint": semantic_fp or (memory_tiers or {}).get("selection_fingerprint"),
        "budgets": budgets,
        "used": used,
    }
    return {
        "schema": SCHEMA,
        "trace_fingerprint": fingerprint(payload),
        **payload,
        "selection_owner": "model",
        "eligibility_owner": "deterministic_runtime",
        "budget_owner": "deterministic_runtime",
        "semantic_relevance_numeric_score": False,
        "authority": False,
        "canon_write": False,
        "model_execution": False,
    }


def self_test() -> int:
    inspector = {
        "schema": "novelforge_context_inspector_v2",
        "manifest_id": "M1",
        "stage": "writer_pre_draft",
        "items": [
            {"id": "A", "class": "character", "source": "canon:A", "source_fingerprint": "sha256:" + "a" * 64, "authority": "accepted", "inclusion_reason": "scene participant", "stages": ["writer_pre_draft"], "priority": 5, "pinned": False, "derived": False, "hidden": False, "invalidated": False, "eligible": True},
            {"id": "B", "class": "memory", "source": "memory:B", "source_fingerprint": "sha256:" + "b" * 64, "authority": False, "inclusion_reason": "derived memory", "stages": ["writer_pre_draft"], "priority": 0, "pinned": False, "derived": True, "hidden": False, "invalidated": False, "eligible": True},
            {"id": "C", "class": "future", "source": "plan:C", "source_fingerprint": "sha256:" + "c" * 64, "authority": "active_plan", "inclusion_reason": "future", "stages": ["writer_pre_draft"], "priority": 0, "pinned": False, "derived": False, "hidden": False, "invalidated": False, "eligible": False},
        ],
    }
    selection_fingerprint = "sha256:" + "d" * 64
    semantic = {
        "input_fingerprint": selection_fingerprint,
        "judgment": {
            "hot_ids": ["A"],
            "working_ids": ["B"],
            "archive_ids": [],
            "reasons": [
                {"block_id": "A", "reason": "immediate participant"},
                {"block_id": "B", "reason": "supports relationship context"},
            ],
        },
    }
    memory = {
        "schema": "novelforge_memory_tiers_v4",
        "selection_fingerprint": selection_fingerprint,
        "budgets": {"hot": 10, "working": 10},
        "used": {"hot": 3, "working": 4},
        "selected": {"hot": [{"id": "A"}], "working": []},
        "archive": ["B"],
        "visibility_excluded": [],
        "temporal_excluded": ["C"],
        "skipped": {"hot": [], "working": [{"id": "B", "reason": "whole_item_exceeds_remaining_budget"}]},
        "invalidated": [],
    }
    report = build_trace(inspector, memory, semantic)
    truthful = (
        report["items"][0]["loaded"]
        and report["items"][1]["loaded"] is False
        and "whole_item_exceeds_remaining_budget" in report["items"][1]["exclusion_reasons"]
        and "future_story_order" in report["items"][2]["exclusion_reasons"]
    )
    ownership = (
        report["selection_owner"] == "model"
        and report["budget_owner"] == "deterministic_runtime"
        and report["semantic_relevance_numeric_score"] is False
    )
    mismatch = False
    bad = json.loads(json.dumps(memory))
    bad["selection_fingerprint"] = "sha256:" + "e" * 64
    try:
        build_trace(inspector, bad, semantic)
    except ValueError:
        mismatch = True
    ok = truthful and ownership and mismatch and report["authority"] is False
    print(json.dumps({
        "context_trace_contract": "PASS" if ok else "FAIL",
        "loaded_vs_skipped_truthful": truthful,
        "ownership_preserved": ownership,
        "fingerprint_guard": mismatch,
        "authority": report["authority"],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge Context Trace builder")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--inspector", required=True)
    build_parser.add_argument("--memory-tiers")
    build_parser.add_argument("--semantic-result")
    build_parser.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()

    def load(path: str | None) -> dict[str, Any] | None:
        return json.loads(Path(path).read_text(encoding="utf-8")) if path else None

    report = build_trace(load(args.inspector), load(args.memory_tiers), load(args.semantic_result))  # type: ignore[arg-type]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
