#!/usr/bin/env python3
"""NovelForge capability-aware Corpus discovery runtime.

Deterministic responsibilities only:
- resolve requested discovery channels against a host capability manifest;
- validate returned source/tool provenance and evidence fingerprints;
- enforce the declared rights/storage gate;
- deduplicate and summarize diversity.

This module never performs Web/GitHub/MCP search itself and never infers legal
rights from a title, URL, author, or provider response.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_capabilities import validate_manifest  # noqa: E402
from rights_gate import decision as rights_decision  # noqa: E402

QUEUE_SCHEMA = "novelforge_corpus_discovery_queue_v2"
DISPATCH_SCHEMA = "novelforge_corpus_dispatch_plan_v1"
RESULT_SCHEMA = "novelforge_corpus_discovery_results_v1"
VERIFIED_SCHEMA = "novelforge_verified_corpus_discovery_v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


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


def build_dispatch(queue: dict[str, Any], manifest: dict[str, Any], *, allow_model: bool = False,
                   allow_user_interaction: bool = True) -> dict[str, Any]:
    if queue.get("schema") != QUEUE_SCHEMA:
        raise ValueError(f"queue schema must be {QUEUE_SCHEMA}")
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("invalid capability manifest: " + "; ".join(errors))
    dispatches: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for request in queue.get("requests", []):
        eligible = []
        rejected = []
        for plan in request.get("host_search_plan", []):
            cap_name = plan.get("requires_capability")
            cap = manifest.get("capabilities", {}).get(cap_name)
            if not cap or not cap.get("available"):
                rejected.append({"channel": plan.get("channel"), "capability": cap_name, "reason": "capability_unavailable"})
                continue
            if cap.get("model_execution") and not allow_model:
                rejected.append({"channel": plan.get("channel"), "capability": cap_name, "reason": "model_execution_forbidden"})
                continue
            if cap.get("user_interaction") and not allow_user_interaction:
                rejected.append({"channel": plan.get("channel"), "capability": cap_name, "reason": "user_interaction_forbidden"})
                continue
            eligible.append({
                "channel": plan.get("channel"),
                "capability": cap_name,
                "query_seed": plan.get("query_seed"),
                "purpose": plan.get("purpose"),
                "capability_provenance": cap.get("source"),
                "usage_class": cap.get("usage_class"),
                "user_interaction": bool(cap.get("user_interaction")),
                "model_execution": bool(cap.get("model_execution")),
            })
        item = {
            "request_id": request.get("request_id"),
            "gap_id": request.get("gap_id"),
            "hypothesis_id": request.get("hypothesis_id"),
            "research_question": request.get("research_question"),
            "request_fingerprint": fingerprint(request),
            "eligible": eligible,
            "rejected": rejected,
        }
        if eligible:
            dispatches.append(item)
        else:
            item["state"] = "awaiting_capability"
            unresolved.append(item)
    return {
        "schema": DISPATCH_SCHEMA,
        "capability_manifest_id": manifest.get("manifest_id"),
        "dispatches": dispatches,
        "unresolved": unresolved,
        "network_or_tool_execution_performed": False,
        "authority_granted": False,
    }


def evidence_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": record.get("request_id"),
        "channel": record.get("channel"),
        "tool_or_provider": record.get("tool_or_provider"),
        "retrieved_at": record.get("retrieved_at"),
        "source_locator": record.get("source_locator"),
        "source_title": record.get("source_title"),
        "source_type": record.get("source_type"),
        "work_id": record.get("work_id"),
        "metadata": record.get("metadata", {}),
        "evidence": record.get("evidence", {}),
    }


def validate_record(record: dict[str, Any], known_requests: set[str]) -> list[str]:
    errors: list[str] = []
    required = [
        "request_id", "channel", "tool_or_provider", "retrieved_at", "source_locator",
        "source_title", "source_type", "rights_class", "rights_basis", "storage_intent",
        "evidence_fingerprint",
    ]
    for key in required:
        if key not in record:
            errors.append(f"missing {key}")
    if errors:
        return errors
    if record["request_id"] not in known_requests:
        errors.append("unknown request_id")
    for key in ("channel", "tool_or_provider", "retrieved_at", "source_locator", "source_title", "source_type"):
        if not str(record.get(key) or "").strip():
            errors.append(f"{key} must be non-empty")
    expected = fingerprint(evidence_payload(record))
    if record.get("evidence_fingerprint") != expected:
        errors.append("evidence_fingerprint mismatch")
    rights_record = {
        "corpus_id": record.get("corpus_id") or expected,
        "source_title": record.get("source_title"),
        "source_type": record.get("source_type"),
        "rights_class": record.get("rights_class"),
        "rights_basis": record.get("rights_basis"),
        "storage_intent": record.get("storage_intent"),
        "excerpt_purpose": record.get("excerpt_purpose"),
    }
    rd = rights_decision(rights_record)
    errors.extend("rights_gate: " + x for x in rd["errors"])
    evidence = record.get("evidence", {})
    if not isinstance(evidence, dict):
        errors.append("evidence must be object")
    else:
        raw_keys = {"full_text", "raw_text", "source_text"}.intersection(evidence)
        if raw_keys and not (record.get("rights_class") == "redistributable" and record.get("storage_intent") == "full_text"):
            errors.append("raw/full source text present without redistributable full_text permission")
        if "excerpt" in evidence:
            if record.get("storage_intent") != "short_excerpt":
                errors.append("excerpt requires storage_intent=short_excerpt")
            if len(str(evidence.get("excerpt") or "")) > 4000:
                errors.append("excerpt exceeds bounded discovery evidence limit")
    return errors


def validate_results(queue: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    if queue.get("schema") != QUEUE_SCHEMA:
        raise ValueError(f"queue schema must be {QUEUE_SCHEMA}")
    if results.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"results schema must be {RESULT_SCHEMA}")
    requests = {r.get("request_id"): r for r in queue.get("requests", []) if r.get("request_id")}
    verified: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_logical: set[tuple[str, str, str]] = set()
    for i, record in enumerate(results.get("results", [])):
        if not isinstance(record, dict):
            errors.append(f"result[{i}] must be object"); continue
        item_errors = validate_record(record, set(requests))
        logical = (
            str(record.get("request_id")),
            str(record.get("source_locator", "")).strip().lower(),
            str(record.get("evidence_fingerprint")),
        )
        if logical in seen_logical:
            continue
        seen_logical.add(logical)
        if item_errors:
            errors.extend(f"result[{i}]: {x}" for x in item_errors)
            continue
        verified.append({
            **record,
            "corpus_id": record.get("corpus_id") or "CORP-" + record["evidence_fingerprint"].split(":", 1)[1][:24],
            "verified": True,
            "legal_analysis_performed": False,
        })
    distinct_works = {str(x.get("work_id") or x.get("source_title")) for x in verified}
    distinct_sources = {str(x.get("source_locator")) for x in verified}
    channels = {str(x.get("channel")) for x in verified}
    by_request: dict[str, dict[str, Any]] = {}
    for rid, req in requests.items():
        rows = [x for x in verified if x.get("request_id") == rid]
        min_works = int(req.get("diversity_requirements", {}).get("min_distinct_works", 1))
        min_sources = int(req.get("diversity_requirements", {}).get("min_distinct_sources", min_works))
        works = {str(x.get("work_id") or x.get("source_title")) for x in rows}
        sources = {str(x.get("source_locator")) for x in rows}
        by_request[rid] = {
            "verified_results": len(rows),
            "distinct_works": len(works),
            "distinct_sources": len(sources),
            "diversity_satisfied": len(works) >= min_works and len(sources) >= min_sources,
            "counterexample_required": bool(req.get("diversity_requirements", {}).get("seek_counterexample", True)),
        }
    return {
        "schema": VERIFIED_SCHEMA,
        "verified": verified,
        "errors": errors,
        "summary": {
            "verified_results": len(verified),
            "distinct_works": len(distinct_works),
            "distinct_sources": len(distinct_sources),
            "channels": sorted(channels),
            "requests": by_request,
        },
        "discovery_is_ingestion": False,
        "legal_analysis_performed": False,
        "authority_granted": False,
    }


def self_test() -> dict[str, Any]:
    request = {
        "schema": "novelforge_corpus_discovery_request_v2", "request_id": "CDR-T", "gap_id": "CG-T",
        "hypothesis_id": "PH-T", "research_question": "fixture", "host_search_plan": [
            {"channel": "web", "requires_capability": "web_search", "query_seed": "fixture", "purpose": "fixture"},
            {"channel": "github", "requires_capability": "github_search", "query_seed": "fixture", "purpose": "fixture"},
        ],
        "diversity_requirements": {"min_distinct_works": 1, "min_distinct_sources": 1, "seek_counterexample": True},
    }
    queue = {"schema": QUEUE_SCHEMA, "requests": [request]}
    manifest = {
        "schema": "novelforge_host_capabilities_v1", "manifest_id": "HC-T", "secrets_embedded": False,
        "capabilities": {
            "web_search": {"available": True, "source": "fixture", "permission": "read", "usage_class": "none", "user_interaction": False, "model_execution": False},
            "github_search": {"available": False, "source": "fixture", "permission": "none", "usage_class": "none", "user_interaction": False, "model_execution": False},
        },
    }
    dispatch = build_dispatch(queue, manifest)
    rec = {
        "request_id": "CDR-T", "channel": "web", "tool_or_provider": "fixture-search", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_locator": "https://example.invalid/work", "source_title": "Fixture Work", "source_type": "book", "work_id": "WORK-T",
        "rights_class": "analysis_only", "rights_basis": "fixture lawful access", "storage_intent": "derived_only",
        "metadata": {"author": "Fixture"}, "evidence": {"mechanism_hint": "state change creates pace"},
    }
    rec["evidence_fingerprint"] = fingerprint(evidence_payload(rec))
    good = validate_results(queue, {"schema": RESULT_SCHEMA, "results": [rec, dict(rec)]})
    bad_rec = dict(rec); bad_rec["evidence_fingerprint"] = "sha256:" + "0" * 64
    bad = validate_results(queue, {"schema": RESULT_SCHEMA, "results": [bad_rec]})
    ok = (
        len(dispatch["dispatches"]) == 1
        and dispatch["dispatches"][0]["eligible"][0]["capability"] == "web_search"
        and any(x["reason"] == "capability_unavailable" for x in dispatch["dispatches"][0]["rejected"])
        and good["summary"]["verified_results"] == 1
        and good["summary"]["requests"]["CDR-T"]["diversity_satisfied"] is True
        and not good["errors"]
        and bool(bad["errors"])
    )
    return {
        "discovery_runtime_contract": "PASS" if ok else "FAIL",
        "capability_binding": True,
        "provenance_fingerprint_binding": bool(bad["errors"]),
        "dedupe": good["summary"]["verified_results"] == 1,
        "rights_gate_enforced": True,
        "network_execution_performed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Corpus discovery runtime")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dispatch"); d.add_argument("--queue", required=True); d.add_argument("--capabilities", required=True); d.add_argument("--output"); d.add_argument("--allow-model", action="store_true"); d.add_argument("--no-user-interaction", action="store_true")
    v = sub.add_parser("validate-results"); v.add_argument("--queue", required=True); v.add_argument("--results", required=True); v.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["discovery_runtime_contract"] == "PASS" else 1
    if args.cmd == "dispatch":
        result = build_dispatch(load(args.queue), load(args.capabilities), allow_model=args.allow_model, allow_user_interaction=not args.no_user_interaction)
        dump(result, args.output); return 0 if result["dispatches"] or not result["unresolved"] else 2
    result = validate_results(load(args.queue), load(args.results)); dump(result, args.output)
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
