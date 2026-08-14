#!/usr/bin/env python3
"""Deterministic learning-input boundary for NovelForge semantic contracts.

Semantic learning intelligence lives in `model_contracts.json`. This thin layer
only converts existing learning/corpus artifacts into bounded inputs, removes
raw source fields, protects blind eval packets, and delegates semantic job
construction/fingerprinting to the generic semantic router. It executes no model.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))
from semantic_worker_router import find_forbidden_keys, make_contract_job, validate_job  # noqa: E402

ANALYSIS_QUEUE_SCHEMA = "novelforge_learning_analysis_jobs_v1"
EVAL_QUEUE_SCHEMA = "novelforge_learning_eval_jobs_v1"
FORBIDDEN_RAW = {"full_text", "raw_text", "source_text"}


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


def bounded_evidence(record: dict[str, Any]) -> dict[str, Any]:
    evidence = record.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    clean = {key: value for key, value in evidence.items() if key not in FORBIDDEN_RAW}
    excerpt = clean.get("excerpt")
    if excerpt is not None:
        clean["excerpt"] = str(excerpt)[:4000]
    return clean


def build_analysis_jobs(verified: dict[str, Any], *, research_question: str,
                        hypothesis_id: str | None = None,
                        source_session_id: str | None = None) -> dict[str, Any]:
    if verified.get("schema") != "novelforge_verified_corpus_discovery_v1":
        raise ValueError("verified discovery schema required")
    jobs = []
    for record in verified.get("verified", []):
        if not isinstance(record, dict) or not record.get("verified"):
            continue
        subject = str(record.get("corpus_id") or record.get("evidence_fingerprint"))
        payload = {
            "research_question": research_question,
            "hypothesis_id": hypothesis_id,
            "source": {
                "corpus_id": record.get("corpus_id"),
                "source_title": record.get("source_title"),
                "source_type": record.get("source_type"),
                "source_locator": record.get("source_locator"),
                "work_id": record.get("work_id"),
                "channel": record.get("channel"),
                "tool_or_provider": record.get("tool_or_provider"),
                "rights_class": record.get("rights_class"),
                "storage_intent": record.get("storage_intent"),
                "evidence_fingerprint": record.get("evidence_fingerprint"),
                "metadata": record.get("metadata", {}),
                "bounded_evidence": bounded_evidence(record),
            },
        }
        job = make_contract_job(
            "learning.mechanism_analyze", subject, payload,
            source_session_id=source_session_id,
        )
        job["provenance"]["evidence_fingerprint"] = record.get("evidence_fingerprint")
        # Provenance is execution metadata and intentionally outside semantic identity.
        jobs.append(job)
    return {
        "schema": ANALYSIS_QUEUE_SCHEMA,
        "blind": True,
        "research_question": research_question,
        "hypothesis_id": hypothesis_id,
        "jobs": jobs,
    }


def build_eval_jobs(request: dict[str, Any], *, source_session_id: str | None = None) -> dict[str, Any]:
    if request.get("schema") != "novelforge_learning_eval_request_v1":
        raise ValueError("learning eval request schema required")
    leakage = find_forbidden_keys(request)
    if leakage:
        raise ValueError("learning eval request leaks answer-key fields: " + ", ".join(leakage))
    jobs = []
    for case in request.get("cases", []):
        if not isinstance(case, dict) or not case.get("id"):
            raise ValueError("eval case requires id")
        criteria = case.get("rubric", [])
        if not isinstance(criteria, list) or not criteria or not all(isinstance(x, str) and x.strip() for x in criteria):
            raise ValueError(f"eval case {case['id']} requires evaluation criteria")
        payload = {
            "learning_scope": request.get("scope"),
            "hypothesis_id": request.get("hypothesis_id"),
            "mechanism": request.get("mechanism"),
            "profile_boundary": request.get("profile_boundary", {}),
            "fixture": case.get("fixture", {}),
            "evaluation_purpose": case.get("purpose"),
            "evaluation_criteria": criteria,
        }
        job = make_contract_job(
            "learning.evaluate", str(case["id"]), payload,
            source_session_id=source_session_id,
        )
        job["provenance"]["hypothesis_id"] = request.get("hypothesis_id")
        jobs.append(job)
    return {
        "schema": EVAL_QUEUE_SCHEMA,
        "blind": True,
        "scope": request.get("scope"),
        "hypothesis_id": request.get("hypothesis_id"),
        "jobs": jobs,
    }


def self_test() -> dict[str, Any]:
    verified = {
        "schema": "novelforge_verified_corpus_discovery_v1",
        "verified": [{
            "verified": True,
            "corpus_id": "CORP-T",
            "source_title": "Fixture",
            "source_type": "book",
            "source_locator": "fixture://work",
            "work_id": "WORK-T",
            "channel": "user_files",
            "tool_or_provider": "fixture",
            "rights_class": "analysis_only",
            "storage_intent": "derived_only",
            "evidence_fingerprint": "sha256:" + "1" * 64,
            "metadata": {},
            "evidence": {"mechanism_hint": "pressure changes options", "raw_text": "must not pass"},
        }],
    }
    analysis = build_analysis_jobs(verified, research_question="What creates pace?", hypothesis_id="PH-T")
    analysis_job = analysis["jobs"][0]
    raw_absent = "raw_text" not in json.dumps(analysis_job, ensure_ascii=False)
    analysis_contract = analysis_job["input"].get("model_contract_id") == "learning.mechanism_analyze"
    fingerprint_valid = not validate_job(analysis_job)

    eval_request = {
        "schema": "novelforge_learning_eval_request_v1",
        "scope": "user_taste",
        "hypothesis_id": "PH-T",
        "mechanism": "pace comes from state change",
        "profile_boundary": {"exceptions": ["deliberate shock fragment"]},
        "cases": [{
            "id": "LE-1",
            "purpose": "distinguish functional pace from fragmentation",
            "fixture": {"text": "fixture"},
            "rubric": ["judge functional pacing mechanism"],
        }],
    }
    evaluation = build_eval_jobs(eval_request)
    eval_job = evaluation["jobs"][0]
    eval_contract = eval_job["input"].get("model_contract_id") == "learning.evaluate"
    leak_guard = False
    try:
        bad = dict(eval_request)
        bad["expected"] = {"result": "pass"}
        build_eval_jobs(bad)
    except ValueError:
        leak_guard = True

    ok = raw_absent and analysis_contract and eval_contract and fingerprint_valid and leak_guard
    return {
        "learning_eval_contract": "PASS" if ok else "FAIL",
        "semantic_intelligence_in_model_contracts": analysis_contract and eval_contract,
        "analysis_jobs_fingerprint_bound": fingerprint_valid,
        "raw_source_text_excluded": raw_absent,
        "answer_key_leakage_guard": leak_guard,
        "model_execution": False,
        "write_authority": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge deterministic learning semantic-input boundary")
    sub = p.add_subparsers(dest="cmd", required=True)
    analysis = sub.add_parser("analysis-jobs")
    analysis.add_argument("--verified", required=True)
    analysis.add_argument("--research-question", required=True)
    analysis.add_argument("--hypothesis-id")
    analysis.add_argument("--source-session-id")
    analysis.add_argument("--output")
    evaluation = sub.add_parser("eval-jobs")
    evaluation.add_argument("--request", required=True)
    evaluation.add_argument("--source-session-id")
    evaluation.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test()
        dump(result)
        return 0 if result["learning_eval_contract"] == "PASS" else 1
    if args.cmd == "analysis-jobs":
        result = build_analysis_jobs(
            load(args.verified), research_question=args.research_question,
            hypothesis_id=args.hypothesis_id, source_session_id=args.source_session_id,
        )
    else:
        result = build_eval_jobs(load(args.request), source_session_id=args.source_session_id)
    dump(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
