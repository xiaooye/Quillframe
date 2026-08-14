#!/usr/bin/env python3
"""NovelForge semantic work packaging for adaptive learning.

Creates bounded, fingerprint-bound jobs for Corpus mechanism analysis and
learning evals. It never executes a model and never embeds answer keys.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))
from semantic_worker_router import fingerprint_for, find_forbidden_keys, validate_job  # noqa: E402

ANALYSIS_QUEUE_SCHEMA = "novelforge_learning_analysis_jobs_v1"
EVAL_QUEUE_SCHEMA = "novelforge_learning_eval_jobs_v1"
FORBIDDEN_RAW = {"full_text", "raw_text", "source_text"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("JSON root must be object")
    return value


def dump(value: Any, path: str | Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path: Path(path).write_text(text, encoding="utf-8")
    else: print(text, end="")


def permissions() -> dict[str, Any]:
    return {
        "canon_write": False,
        "os_behavior_write": False,
        "durable_user_taste_write": False,
        "allowed_result_scope": "observation",
    }


def bounded_evidence(record: dict[str, Any]) -> dict[str, Any]:
    evidence = record.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    clean = {k: v for k, v in evidence.items() if k not in FORBIDDEN_RAW}
    excerpt = clean.get("excerpt")
    if excerpt is not None:
        clean["excerpt"] = str(excerpt)[:4000]
    return clean


def make_job(kind: str, subject_id: str, input_payload: dict[str, Any], rubric: list[str], output_contract: dict[str, Any], *, provenance: dict[str, Any], source_session_id: str | None = None) -> dict[str, Any]:
    job = {
        "job_id": "SEM-LEARN-" + uuid.uuid4().hex,
        "kind": kind,
        "subject_id": subject_id,
        "created_at": now_iso(),
        "input_fingerprint": "",
        "input": input_payload,
        "rubric": rubric,
        "output_contract": output_contract,
        "permissions": permissions(),
        "provenance": provenance,
        "execution": {"source_session_id": source_session_id, "worker_session_id": None, "handoff_id": None, "attempt_id": None},
    }
    leakage = find_forbidden_keys({"input": input_payload, "rubric": rubric, "output_contract": output_contract})
    if leakage:
        raise ValueError("semantic packet contains forbidden answer-key fields: " + ", ".join(leakage))
    job["input_fingerprint"] = fingerprint_for(job)
    errors = validate_job(job)
    if errors: raise ValueError("invalid semantic job: " + "; ".join(errors))
    return job


def build_analysis_jobs(verified: dict[str, Any], *, research_question: str, hypothesis_id: str | None = None, source_session_id: str | None = None) -> dict[str, Any]:
    if verified.get("schema") != "novelforge_verified_corpus_discovery_v1":
        raise ValueError("verified discovery schema required")
    jobs = []
    for record in verified.get("verified", []):
        if not record.get("verified"):
            continue
        subject = str(record.get("corpus_id") or record.get("evidence_fingerprint"))
        input_payload = {
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
        rubric = [
            "Answer only the research question using the supplied bounded evidence.",
            "Separate observed mechanism from speculation.",
            "Actively look for counterevidence or a boundary where the mechanism should not generalize.",
            "Do not imitate a named author and do not infer project Canon or user biography.",
            "Every claim must cite supplied evidence refs/fields; uncertainty must lower confidence.",
        ]
        output_contract = {
            "schema": "novelforge_corpus_mechanism_analysis_v1",
            "required": ["mechanisms", "counterexamples", "applicability_boundaries", "evidence_refs", "confidence"],
            "notes": "Typed observation only; no direct preference promotion or Framework write authority.",
        }
        jobs.append(make_job(
            "corpus_analyze", subject, input_payload, rubric, output_contract,
            provenance={"source": "verified_corpus_discovery", "evidence_fingerprint": record.get("evidence_fingerprint")},
            source_session_id=source_session_id,
        ))
    return {"schema": ANALYSIS_QUEUE_SCHEMA, "blind": True, "research_question": research_question, "hypothesis_id": hypothesis_id, "jobs": jobs}


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
        input_payload = {
            "learning_scope": request.get("scope"),
            "hypothesis_id": request.get("hypothesis_id"),
            "mechanism": request.get("mechanism"),
            "profile_boundary": request.get("profile_boundary", {}),
            "fixture": case.get("fixture", {}),
            "evaluation_purpose": case.get("purpose"),
        }
        rubric = list(case.get("rubric", []))
        if not rubric: raise ValueError(f"eval case {case['id']} requires rubric")
        output_contract = case.get("output_contract") or {
            "schema": "novelforge_learning_eval_judgment_v1",
            "required": ["result", "codes", "evidence", "confidence"],
        }
        jobs.append(make_job(
            "eval_judge", str(case["id"]), input_payload, rubric, output_contract,
            provenance={"source": "learning_eval_request", "hypothesis_id": request.get("hypothesis_id")},
            source_session_id=source_session_id,
        ))
    return {"schema": EVAL_QUEUE_SCHEMA, "blind": True, "scope": request.get("scope"), "hypothesis_id": request.get("hypothesis_id"), "jobs": jobs}


def self_test() -> dict[str, Any]:
    verified = {
        "schema": "novelforge_verified_corpus_discovery_v1",
        "verified": [{
            "verified": True, "corpus_id": "CORP-T", "source_title": "Fixture", "source_type": "book",
            "source_locator": "fixture://work", "work_id": "WORK-T", "channel": "user_files", "tool_or_provider": "fixture",
            "rights_class": "analysis_only", "storage_intent": "derived_only", "evidence_fingerprint": "sha256:" + "1" * 64,
            "metadata": {}, "evidence": {"mechanism_hint": "pressure changes options", "raw_text": "must not pass"},
        }],
    }
    aq = build_analysis_jobs(verified, research_question="What creates pace?", hypothesis_id="PH-T")
    analysis_job = aq["jobs"][0]
    raw_absent = "raw_text" not in json.dumps(analysis_job, ensure_ascii=False)
    fingerprint_valid = analysis_job["input_fingerprint"] == fingerprint_for(analysis_job) and not validate_job(analysis_job)
    eval_request = {
        "schema": "novelforge_learning_eval_request_v1", "scope": "user_taste", "hypothesis_id": "PH-T",
        "mechanism": "pace comes from state change", "profile_boundary": {"exceptions": ["deliberate shock fragment"]},
        "cases": [{"id": "LE-1", "purpose": "distinguish functional pace from fragmentation", "fixture": {"text": "fixture"}, "rubric": ["judge functional pacing mechanism"]}],
    }
    eq = build_eval_jobs(eval_request)
    leak_guard = False
    try:
        bad = dict(eval_request); bad["expected"] = {"result": "pass"}; build_eval_jobs(bad)
    except ValueError:
        leak_guard = True
    ok = bool(aq["jobs"]) and bool(eq["jobs"]) and raw_absent and fingerprint_valid and leak_guard
    return {
        "learning_eval_contract": "PASS" if ok else "FAIL",
        "analysis_jobs_fingerprint_bound": fingerprint_valid,
        "raw_source_text_excluded": raw_absent,
        "answer_key_leakage_guard": leak_guard,
        "model_execution": False,
        "write_authority": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge semantic learning work packager")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analysis-jobs"); a.add_argument("--verified", required=True); a.add_argument("--research-question", required=True); a.add_argument("--hypothesis-id"); a.add_argument("--source-session-id"); a.add_argument("--output")
    e = sub.add_parser("eval-jobs"); e.add_argument("--request", required=True); e.add_argument("--source-session-id"); e.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["learning_eval_contract"] == "PASS" else 1
    if args.cmd == "analysis-jobs":
        result = build_analysis_jobs(load(args.verified), research_question=args.research_question, hypothesis_id=args.hypothesis_id, source_session_id=args.source_session_id)
    else:
        result = build_eval_jobs(load(args.request), source_session_id=args.source_session_id)
    dump(result, args.output); return 0


if __name__ == "__main__":
    raise SystemExit(main())
