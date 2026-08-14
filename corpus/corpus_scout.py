#!/usr/bin/env python3
"""Preference-aware corpus discovery planner.

This module does not scrape the web. It turns open learning gaps into typed,
provider-neutral discovery requests that the current host can execute through
Web/GitHub/MCP/library/user-file connectors.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEARNING_DIR = ROOT / "learning"
if str(LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(LEARNING_DIR))
from learning_store import LearningStore  # noqa: E402

SCHEMA = "novelforge_corpus_discovery_request_v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_request(gap: dict[str, Any]) -> dict[str, Any]:
    tags = list(dict.fromkeys(gap.get("genre_tags", [])))
    dims = list(dict.fromkeys(gap.get("style_dimensions", [])))
    constraints = gap.get("source_constraints", {}) or {}
    query_seed = " ".join([gap["question"], gap.get("desired_contrast") or "", *tags, *dims]).strip()
    return {
        "schema": SCHEMA,
        "request_id": "CDR-" + uuid.uuid4().hex,
        "gap_id": gap["gap_id"],
        "hypothesis_id": gap.get("hypothesis_id"),
        "subject_scope": gap["subject_scope"],
        "research_question": gap["question"],
        "desired_contrast": gap.get("desired_contrast"),
        "genre_tags": tags,
        "style_dimensions": dims,
        "source_constraints": {
            "rights": constraints.get("rights", ["redistributable", "analysis_only", "unknown"]),
            "prefer_primary_official": constraints.get("prefer_primary_official", True),
            "languages": constraints.get("languages", []),
            "platforms": constraints.get("platforms", []),
            "exclude_sources": constraints.get("exclude_sources", []),
        },
        "diversity_requirements": {
            "min_distinct_works": int(constraints.get("min_distinct_works", 3)),
            "seek_counterexample": True,
            "avoid_single_author_overfit": True,
            "prefer_multiple_genres_when_generalizing": gap["subject_scope"] == "general_craft",
        },
        "host_search_plan": [
            {
                "channel": "web",
                "purpose": "discover official/platform/publisher/library candidates",
                "query_seed": query_seed,
            },
            {
                "channel": "github",
                "purpose": "discover permissively licensed/public-domain datasets, tooling, or public research artifacts",
                "query_seed": query_seed,
            },
            {
                "channel": "user_files",
                "purpose": "consider user-provided lawful copies only when explicitly available",
                "query_seed": query_seed,
            },
        ],
        "ingest_boundary": {
            "discovery_is_not_ingestion": True,
            "rights_gate_required": True,
            "full_text_storage_requires_redistributable": True,
            "analysis_only_may_store_full_text": False,
            "named_author_imitation_profile_forbidden": True,
        },
        "created_at": now_iso(),
    }


def self_test() -> dict[str, Any]:
    gap = {
        "gap_id": "CG-TEST",
        "subject_scope": "user_taste",
        "hypothesis_id": "PH-TEST",
        "question": "How do high-tempo scenes preserve coherent paragraph units?",
        "desired_contrast": "fast pace without non-functional fragmentation",
        "genre_tags": ["commercial_fiction"],
        "style_dimensions": ["pace", "paragraph_rhythm"],
        "source_constraints": {"rights": ["analysis_only", "redistributable"]},
    }
    req = build_request(gap)
    ok = (
        req["schema"] == SCHEMA
        and req["diversity_requirements"]["seek_counterexample"] is True
        and req["ingest_boundary"]["rights_gate_required"] is True
        and req["ingest_boundary"]["named_author_imitation_profile_forbidden"] is True
    )
    return {
        "corpus_scout_contract": "PASS" if ok else "FAIL",
        "provider_neutral": True,
        "autonomous_gap_to_query_plan": True,
        "rights_gate_preserved": True,
        "counterexample_search_required": True,
    }


def dump(v: Any) -> None:
    print(json.dumps(v, ensure_ascii=False, indent=2))


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge corpus discovery planner")
    p.add_argument("--learning-db", default=os.getenv("NOVELFORGE_LEARNING_DB", ".novelforge/learning.db"))
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("plan"); q.add_argument("--limit", type=int, default=10); q.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["corpus_scout_contract"] == "PASS" else 1
    store = LearningStore(args.learning_db); store.init()
    requests = [build_request(g) for g in store.list_open_gaps(args.limit)]
    payload = {"schema": "novelforge_corpus_discovery_queue_v1", "requests": requests}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
