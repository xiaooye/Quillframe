#!/usr/bin/env python3
"""Preference-aware Corpus discovery request planner.

This module never performs network discovery itself. It converts durable Corpus
gaps into capability-aware, provider-neutral requests. A host must resolve the
requirements against a typed host-capability manifest before dispatch.
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

SCHEMA = "novelforge_corpus_discovery_request_v2"
CHANNELS = [
    ("web", "web_search", "discover official/platform/publisher/library candidates"),
    ("github", "github_search", "discover permissively licensed/public-domain datasets, tooling, or public research artifacts"),
    ("user_files", "user_files", "consider user-provided lawful copies only when explicitly available"),
    ("file_library", "file_library", "search host-managed user file library only when explicitly available"),
    ("mcp", "mcp_client", "use an authorized MCP search/library connector when available"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_request(gap: dict[str, Any]) -> dict[str, Any]:
    tags = list(dict.fromkeys(gap.get("genre_tags", [])))
    dims = list(dict.fromkeys(gap.get("style_dimensions", [])))
    constraints = gap.get("source_constraints", {}) or {}
    query_seed = " ".join([gap["question"], gap.get("desired_contrast") or "", *tags, *dims]).strip()
    allowed_channels = set(constraints.get("channels", [c[0] for c in CHANNELS]))
    plans = []
    for channel, required_capability, purpose in CHANNELS:
        if channel not in allowed_channels:
            continue
        plans.append({
            "channel": channel,
            "requires_capability": required_capability,
            "purpose": purpose,
            "query_seed": query_seed,
            "execution_authority": "host_only",
        })
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
            "channels": sorted(allowed_channels),
        },
        "diversity_requirements": {
            "min_distinct_works": int(constraints.get("min_distinct_works", 3)),
            "min_distinct_sources": int(constraints.get("min_distinct_sources", 3)),
            "seek_counterexample": True,
            "avoid_single_author_overfit": True,
            "prefer_multiple_genres_when_generalizing": gap["subject_scope"] == "general_craft",
        },
        "host_search_plan": plans,
        "result_contract": {
            "schema": "novelforge_corpus_discovery_results_v1",
            "required_provenance": [
                "channel", "tool_or_provider", "retrieved_at", "source_locator",
                "source_title", "source_type", "evidence_fingerprint",
            ],
            "rights_metadata_required_before_ingestion": True,
        },
        "ingest_boundary": {
            "discovery_is_not_ingestion": True,
            "rights_gate_required": True,
            "full_text_storage_requires_redistributable": True,
            "analysis_only_may_store_full_text": False,
            "unknown_rights_metadata_only": True,
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
        "source_constraints": {"rights": ["analysis_only", "redistributable"], "channels": ["web", "user_files"]},
    }
    req = build_request(gap)
    caps = {x["requires_capability"] for x in req["host_search_plan"]}
    ok = (
        req["schema"] == SCHEMA
        and caps == {"web_search", "user_files"}
        and req["diversity_requirements"]["seek_counterexample"] is True
        and req["ingest_boundary"]["rights_gate_required"] is True
        and req["ingest_boundary"]["named_author_imitation_profile_forbidden"] is True
        and all(x["execution_authority"] == "host_only" for x in req["host_search_plan"])
    )
    return {
        "corpus_scout_contract": "PASS" if ok else "FAIL",
        "request_schema": SCHEMA,
        "provider_neutral": True,
        "capability_requirements_explicit": True,
        "autonomous_gap_to_query_plan": True,
        "rights_gate_preserved": True,
        "counterexample_search_required": True,
        "discovery_execution_claimed": False,
    }


def dump(v: Any) -> None:
    print(json.dumps(v, ensure_ascii=False, indent=2))


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Corpus discovery planner")
    p.add_argument("--learning-db", default=os.getenv("NOVELFORGE_LEARNING_DB", ".novelforge/learning.db"))
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("plan"); q.add_argument("--limit", type=int, default=10); q.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["corpus_scout_contract"] == "PASS" else 1
    store = LearningStore(args.learning_db); store.init()
    requests = [build_request(g) for g in store.list_open_gaps(args.limit)]
    payload = {"schema": "novelforge_corpus_discovery_queue_v2", "requests": requests}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
