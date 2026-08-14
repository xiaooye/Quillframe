#!/usr/bin/env python3
"""AI-native Corpus discovery planning boundary for NovelForge.

The model owns query/contrast/counterexample strategy through the
`corpus.discovery_plan` contract. This module only exposes bounded learning gaps,
validates fingerprint-bound semantic results, constrains plans to declared
channels, maps channels to host capabilities, and emits the deterministic
Discovery Runtime queue. It never searches the network or performs literary
analysis itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEARNING_DIR = ROOT / "learning"
SEM = ROOT / "harness" / "semantic_workers"
if str(LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(LEARNING_DIR))
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))
from learning_store import LearningStore  # noqa: E402
from semantic_worker_router import make_contract_job, validate_results  # noqa: E402

PLANNING_QUEUE_SCHEMA = "novelforge_corpus_planning_jobs_v1"
DISCOVERY_QUEUE_SCHEMA = "novelforge_corpus_discovery_queue_v2"
REQUEST_SCHEMA = "novelforge_corpus_discovery_request_v2"
REGISTRY = SEM / "contracts" / "context-research.json"
CHANNEL_CAPABILITIES = {
    "web": "web_search",
    "github": "github_search",
    "user_files": "user_files",
    "file_library": "file_library",
    "mcp": "mcp_client",
}


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def dump(value: Any, path: str | Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _constraints(gap: dict[str, Any]) -> dict[str, Any]:
    raw = gap.get("source_constraints", {}) or {}
    if not isinstance(raw, dict):
        raise ValueError("source_constraints must be object")
    channels = raw.get("channels", list(CHANNEL_CAPABILITIES))
    if not isinstance(channels, list) or not channels or not all(isinstance(x, str) for x in channels):
        raise ValueError("source_constraints.channels must be non-empty string list")
    unknown = sorted(set(channels) - set(CHANNEL_CAPABILITIES))
    if unknown:
        raise ValueError("unknown source channels: " + ", ".join(unknown))
    return {
        "rights": raw.get("rights", ["redistributable", "analysis_only", "unknown"]),
        "prefer_primary_official": bool(raw.get("prefer_primary_official", True)),
        "languages": list(raw.get("languages", [])),
        "platforms": list(raw.get("platforms", [])),
        "exclude_sources": list(raw.get("exclude_sources", [])),
        "channels": list(dict.fromkeys(channels)),
        "min_distinct_works": int(raw.get("min_distinct_works", 3)),
        "min_distinct_sources": int(raw.get("min_distinct_sources", 3)),
    }


def planning_payload(gap: dict[str, Any]) -> dict[str, Any]:
    required = ("gap_id", "subject_scope", "question")
    missing = [key for key in required if not gap.get(key)]
    if missing:
        raise ValueError("corpus gap missing: " + ", ".join(missing))
    constraints = _constraints(gap)
    return {
        "gap": {
            "gap_id": gap["gap_id"],
            "subject_scope": gap["subject_scope"],
            "hypothesis_id": gap.get("hypothesis_id"),
            "research_question": gap["question"],
            "desired_contrast": gap.get("desired_contrast"),
            "genre_tags": list(gap.get("genre_tags", [])),
            "style_dimensions": list(gap.get("style_dimensions", [])),
        },
        "source_constraints": constraints,
        "allowed_channels": constraints["channels"],
        "channel_vocabulary": [
            {"channel": channel, "requires_capability": CHANNEL_CAPABILITIES[channel]}
            for channel in constraints["channels"]
        ],
        "runtime_boundaries": {
            "channel_availability_is_unknown_to_model": True,
            "discovery_is_not_ingestion": True,
            "rights_gate_required": True,
            "named_author_imitation_profile_forbidden": True,
        },
    }


def prepare_jobs(gaps: list[dict[str, Any]], *, source_session_id: str | None = None) -> dict[str, Any]:
    jobs = []
    for gap in gaps:
        payload = planning_payload(gap)
        jobs.append(make_contract_job(
            "corpus.discovery_plan",
            str(gap["gap_id"]),
            payload,
            registry_path=REGISTRY,
            source_session_id=source_session_id,
        ))
    return {
        "schema": PLANNING_QUEUE_SCHEMA,
        "jobs": jobs,
        "semantic_strategy_owner": "model",
        "network_or_tool_execution_performed": False,
    }


def _request_id(job: dict[str, Any]) -> str:
    raw = f"{job['subject_id']}:{job['input_fingerprint']}".encode("utf-8")
    return "CDR-" + hashlib.sha256(raw).hexdigest()[:24]


def _request_from_result(job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    payload = job.get("input", {}).get("payload", {})
    gap = payload.get("gap", {})
    constraints = payload.get("source_constraints", {})
    allowed = set(payload.get("allowed_channels", []))
    judgment = result.get("judgment", {})
    searches = judgment.get("searches", [])
    if not isinstance(searches, list) or not searches:
        raise ValueError(f"{job['subject_id']}: model returned no searches")
    plans = []
    seen: set[tuple[str, str]] = set()
    for search in searches:
        if not isinstance(search, dict):
            raise ValueError(f"{job['subject_id']}: search plan must be object")
        channel = search.get("channel")
        query = str(search.get("query") or "").strip()
        if channel not in allowed:
            raise ValueError(f"{job['subject_id']}: model selected disallowed channel {channel!r}")
        if channel not in CHANNEL_CAPABILITIES:
            raise ValueError(f"{job['subject_id']}: unknown channel {channel!r}")
        if not query:
            raise ValueError(f"{job['subject_id']}: empty search query")
        logical = (str(channel), query)
        if logical in seen:
            continue
        seen.add(logical)
        plans.append({
            "channel": channel,
            "requires_capability": CHANNEL_CAPABILITIES[channel],
            "purpose": str(search.get("purpose") or "").strip(),
            "query_seed": query,
            "contrast_role": search.get("contrast_role"),
            "execution_authority": "host_only",
        })
    if not plans:
        raise ValueError(f"{job['subject_id']}: no usable search plans")
    scope = gap.get("subject_scope")
    return {
        "schema": REQUEST_SCHEMA,
        "request_id": _request_id(job),
        "gap_id": gap.get("gap_id"),
        "hypothesis_id": gap.get("hypothesis_id"),
        "subject_scope": scope,
        "research_question": gap.get("research_question"),
        "desired_contrast": gap.get("desired_contrast"),
        "genre_tags": gap.get("genre_tags", []),
        "style_dimensions": gap.get("style_dimensions", []),
        "source_constraints": {
            "rights": constraints.get("rights", []),
            "prefer_primary_official": constraints.get("prefer_primary_official", True),
            "languages": constraints.get("languages", []),
            "platforms": constraints.get("platforms", []),
            "exclude_sources": constraints.get("exclude_sources", []),
            "channels": constraints.get("channels", []),
        },
        "diversity_requirements": {
            "min_distinct_works": constraints.get("min_distinct_works", 3),
            "min_distinct_sources": constraints.get("min_distinct_sources", 3),
            "seek_counterexample": True,
            "avoid_single_author_overfit": True,
            "prefer_multiple_genres_when_generalizing": scope == "general_craft",
            "model_strategy": judgment.get("diversity_strategy"),
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
        "planning_fingerprint": job.get("input_fingerprint"),
        "planning_worker": result.get("worker"),
        "created_at": job.get("created_at"),
    }


def consume_results(jobs_payload: dict[str, Any], results_payload: dict[str, Any]) -> dict[str, Any]:
    if jobs_payload.get("schema") != PLANNING_QUEUE_SCHEMA:
        raise ValueError(f"jobs schema must be {PLANNING_QUEUE_SCHEMA}")
    validated, errors = validate_results(jobs_payload, results_payload)
    if errors:
        raise ValueError("invalid corpus planning results: " + "; ".join(errors))
    by_job = {job["job_id"]: job for job in jobs_payload.get("jobs", [])}
    requests = []
    for result in validated:
        if result.get("status") != "completed":
            continue
        job = by_job[result["job_id"]]
        if job.get("input", {}).get("model_contract_id") != "corpus.discovery_plan":
            raise ValueError("corpus planning job used wrong model contract")
        requests.append(_request_from_result(job, result))
    return {
        "schema": DISCOVERY_QUEUE_SCHEMA,
        "requests": requests,
        "semantic_strategy_owner": "model",
        "capability_authorization_owner": "host_runtime",
        "rights_authorization_owner": "rights_gate",
        "network_or_tool_execution_performed": False,
        "authority_granted": False,
    }


def self_test() -> dict[str, Any]:
    gap = {
        "gap_id": "CG-TEST",
        "subject_scope": "general_craft",
        "hypothesis_id": "PH-TEST",
        "question": "What mechanisms create fast pacing without fragmenting coherent action?",
        "desired_contrast": "state-change pacing versus cosmetic sentence chopping",
        "genre_tags": ["commercial_fiction"],
        "style_dimensions": ["pace", "paragraph_rhythm"],
        "source_constraints": {
            "rights": ["analysis_only", "redistributable"],
            "channels": ["web", "user_files"],
            "min_distinct_works": 2,
            "min_distinct_sources": 2,
        },
    }
    jobs = prepare_jobs([gap])
    job = jobs["jobs"][0]
    result = {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
        "judgment": {
            "confidence": 0.9,
            "searches": [
                {"channel": "web", "query": "narrative pacing state change paragraph coherence study", "purpose": "find mechanism evidence", "contrast_role": "support"},
                {"channel": "user_files", "query": "fast scene intact paragraph counterexample", "purpose": "find contrasting examples", "contrast_role": "counterexample"},
            ],
            "diversity_strategy": "Compare mechanism evidence across distinct works and include a counterexample.",
        },
        "proposals": [], "errors": [],
    }
    queue = consume_results(jobs, {"results": [result]})
    request = queue["requests"][0]
    queries = [x["query_seed"] for x in request["host_search_plan"]]
    model_query_preserved = queries[0] == "narrative pacing state change paragraph coherence study"
    capability_map = {x["requires_capability"] for x in request["host_search_plan"]} == {"web_search", "user_files"}
    rights_preserved = request["ingest_boundary"]["rights_gate_required"] is True and request["ingest_boundary"]["named_author_imitation_profile_forbidden"] is True
    disallowed_guard = False
    bad = json.loads(json.dumps(result)); bad["judgment"]["searches"][0]["channel"] = "github"
    try:
        consume_results(jobs, {"results": [bad]})
    except ValueError:
        disallowed_guard = True
    ok = (
        job["input"].get("model_contract_id") == "corpus.discovery_plan"
        and model_query_preserved and capability_map and rights_preserved and disallowed_guard
    )
    return {
        "corpus_scout_contract": "PASS" if ok else "FAIL",
        "semantic_search_strategy_owner": "model",
        "model_query_preserved": model_query_preserved,
        "capability_mapping_deterministic": capability_map,
        "disallowed_channel_guard": disallowed_guard,
        "rights_gate_preserved": rights_preserved,
        "network_execution_performed": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge AI-native Corpus discovery planner boundary")
    p.add_argument("--learning-db", default=os.getenv("NOVELFORGE_LEARNING_DB", ".novelforge/learning.db"))
    sub = p.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--limit", type=int, default=10); prep.add_argument("--source-session-id"); prep.add_argument("--output")
    consume = sub.add_parser("consume")
    consume.add_argument("--jobs", required=True); consume.add_argument("--results", required=True); consume.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["corpus_scout_contract"] == "PASS" else 1
    if args.cmd == "prepare":
        store = LearningStore(args.learning_db); store.init()
        value = prepare_jobs(store.list_open_gaps(args.limit), source_session_id=args.source_session_id)
    else:
        value = consume_results(load(args.jobs), load(args.results))
    dump(value, getattr(args, "output", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
