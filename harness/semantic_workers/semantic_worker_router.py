#!/usr/bin/env python3
"""Provider-neutral semantic job/result packaging and validation.

Deterministic only: this module never performs literary judgment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORBIDDEN_BLIND_KEYS = {"expected","expected_verdict","expected_codes","blocks_release","gold","gold_label","prior_result"}
ALLOWED_KINDS = {"eval_judge","corpus_analyze","benchmark_synthesize","external_review","preference_distill","artifact_audit"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f: return json.load(f)


def dump_json(obj: Any, path: Path | None = None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")
    else: print(text, end="")


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def semantic_payload(job: dict[str, Any]) -> dict[str, Any]:
    # Execution/session lineage intentionally does not alter semantic fingerprint.
    return {"kind": job["kind"], "subject_id": job["subject_id"], "input": job.get("input", {}),
            "rubric": job.get("rubric", []), "output_contract": job.get("output_contract", {})}


def fingerprint_for(job: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(semantic_payload(job))).hexdigest()


def find_forbidden_keys(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_BLIND_KEYS: hits.append(f"{path}.{key}")
            hits.extend(find_forbidden_keys(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj): hits.extend(find_forbidden_keys(value, f"{path}[{i}]"))
    return hits


def make_eval_jobs(queue: dict[str, Any], *, source_session_id: str | None = None, handoff_id: str | None = None) -> dict[str, Any]:
    if queue.get("blind") is not True: raise ValueError("eval queue must declare blind=true")
    leakage = find_forbidden_keys(queue)
    if leakage: raise ValueError("blind queue contains forbidden answer-key fields: " + ", ".join(leakage))
    created_at = datetime.now(timezone.utc).isoformat(); jobs = []
    for case in queue.get("cases", []):
        subject_id = case["id"]
        job = {
            "job_id": f"SEM-EVAL-{subject_id}", "kind": "eval_judge", "subject_id": subject_id,
            "created_at": created_at, "input_fingerprint": "",
            "input": {"type": case.get("type"), "domain": case.get("domain"), "fixture": case.get("fixture", {})},
            "rubric": case.get("rubric", []), "output_contract": case.get("judgment_contract", {}),
            "permissions": {"canon_write": False, "os_behavior_write": False, "durable_user_taste_write": False, "allowed_result_scope": "observation"},
            "provenance": {"source": "blind_eval_queue", "suite_version": queue.get("suite_version")},
            "execution": {"source_session_id": source_session_id, "worker_session_id": None, "handoff_id": handoff_id, "attempt_id": None},
        }
        job["input_fingerprint"] = fingerprint_for(job); jobs.append(job)
    return {"semantic_worker_queue_version": "2", "source_suite_version": queue.get("suite_version"), "blind": True, "jobs": jobs}


def validate_job(job: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance"}
    missing = sorted(required - set(job))
    if missing: return ["missing fields: " + ", ".join(missing)]
    if job["kind"] not in ALLOWED_KINDS: errors.append(f"unsupported kind: {job['kind']}")
    leakage = find_forbidden_keys({"input": job.get("input"), "rubric": job.get("rubric"), "output_contract": job.get("output_contract")})
    if job["kind"] == "eval_judge" and leakage: errors.append("answer-key leakage: " + ", ".join(leakage))
    perms = job.get("permissions", {})
    for key in ("canon_write","os_behavior_write","durable_user_taste_write"):
        if perms.get(key) is not False: errors.append(f"permission {key} must be false")
    if job.get("input_fingerprint") != fingerprint_for(job): errors.append("input_fingerprint mismatch")
    execution = job.get("execution")
    if execution is not None:
        if not isinstance(execution, dict): errors.append("execution must be object")
        elif set(execution) - {"source_session_id","worker_session_id","handoff_id","attempt_id"}: errors.append("execution contains unknown lineage fields")
    return errors


def validate_result(job: dict[str, Any], result: dict[str, Any]) -> list[str]:
    errors = validate_job(job)
    required = {"job_id","subject_id","kind","input_fingerprint","status","worker","judgment","proposals","errors"}
    missing = sorted(required - set(result))
    if missing: return errors + ["result missing fields: " + ", ".join(missing)]
    for key in ("job_id","subject_id","kind","input_fingerprint"):
        if result.get(key) != job.get(key): errors.append(f"result/job mismatch: {key}")
    if result.get("status") not in {"completed","unsupported","failed"}: errors.append("invalid result status")
    worker = result.get("worker", {})
    if not isinstance(worker, dict) or not worker.get("provider") or not worker.get("model_or_reviewer"): errors.append("worker.provider/model_or_reviewer required")
    judgment = result.get("judgment", {})
    confidence = judgment.get("confidence") if isinstance(judgment, dict) else None
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1: errors.append("judgment.confidence must be 0..1")
    if result.get("status") == "completed" and job["kind"] == "eval_judge":
        if judgment.get("verdict") not in {"accept","reject",None}: errors.append("eval verdict must be accept|reject|null")
        if judgment.get("result") not in {"pass","fail",None}: errors.append("eval result must be pass|fail|null")
        if judgment.get("verdict") is None and judgment.get("result") is None: errors.append("completed eval requires verdict or result")
        if not isinstance(judgment.get("codes", []), list): errors.append("judgment.codes must be list")
        if not isinstance(judgment.get("evidence", []), list): errors.append("judgment.evidence must be list")
    forbidden_actions = {"settle_canon","promote_generic_hard_rule","overwrite_durable_user_taste","grant_permissions"}
    for proposal in result.get("proposals", []):
        if isinstance(proposal, dict) and proposal.get("action") in forbidden_actions: errors.append(f"forbidden direct proposal action: {proposal.get('action')}")
    # If a job declares a target reviewer session/handoff, a result may not contradict it.
    lineage = job.get("execution") or {}; result_lineage = result.get("execution") or {}
    for key in ("source_session_id","handoff_id"):
        if lineage.get(key) and result_lineage.get(key) not in {None, lineage.get(key)}: errors.append(f"execution lineage mismatch: {key}")
    return errors


def load_jobs(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for job in payload.get("jobs", []):
        if job["job_id"] in out: raise ValueError(f"duplicate job_id: {job['job_id']}")
        out[job["job_id"]] = job
    return out


def validate_results(jobs_payload: dict[str, Any], results_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    jobs = load_jobs(jobs_payload); validated = []; errors: list[str] = []; seen: set[str] = set()
    for result in results_payload.get("results", []):
        job_id = result.get("job_id")
        if job_id in seen: errors.append(f"duplicate result job_id: {job_id}"); continue
        seen.add(job_id); job = jobs.get(job_id)
        if not job: errors.append(f"result references unknown job_id: {job_id}"); continue
        item_errors = validate_result(job, result)
        if item_errors: errors.extend(f"{job_id}: {msg}" for msg in item_errors)
        else: validated.append(result)
    return validated, errors


def eval_judgments(validated_results: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for result in validated_results:
        if result["kind"] != "eval_judge" or result["status"] != "completed": continue
        j = result["judgment"]; payload = {"codes": j.get("codes", []), "evidence": j.get("evidence", []), "confidence": j.get("confidence"), "worker": result.get("worker"), "input_fingerprint": result.get("input_fingerprint"), "execution": result.get("execution")}
        if j.get("verdict") is not None: payload["verdict"] = j["verdict"]
        if j.get("result") is not None: payload["result"] = j["result"]
        out[result["subject_id"]] = payload
    return out


def self_test() -> int:
    queue = {"blind": True, "suite_version": "self", "cases": [{"id": "CASE-1", "type": "regression", "domain": "reader", "fixture": {"text": "x"}, "rubric": ["judge"], "judgment_contract": {}}]}
    jobs = make_eval_jobs(queue, source_session_id="SES-A", handoff_id="HO-A"); job = jobs["jobs"][0]
    result = {"job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"], "input_fingerprint": job["input_fingerprint"], "status": "completed", "worker": {"provider": "self_test", "model_or_reviewer": "fixture"}, "judgment": {"verdict": "accept", "result": None, "codes": [], "evidence": ["fixture"], "confidence": 1.0}, "proposals": [], "errors": [], "execution": {"source_session_id": "SES-A", "worker_session_id": "SES-B", "handoff_id": "HO-A", "attempt_id": "ATT-1"}}
    preserved = fingerprint_for({**job, "execution": {"source_session_id": "DIFFERENT"}}) == job["input_fingerprint"]
    ok = not validate_job(job) and not validate_result(job, result) and preserved
    dump_json({"semantic_router_contract": "PASS" if ok else "FAIL", "fingerprint_excludes_runtime_lineage": preserved})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Novel OS Semantic Worker Router")
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare-evals"); prep.add_argument("--queue", required=True); prep.add_argument("--output"); prep.add_argument("--source-session-id"); prep.add_argument("--handoff-id")
    vj = sub.add_parser("validate-jobs"); vj.add_argument("--jobs", required=True)
    vr = sub.add_parser("validate-results"); vr.add_argument("--jobs", required=True); vr.add_argument("--results", required=True); vr.add_argument("--judgments-output")
    sub.add_parser("self-test"); args = p.parse_args()
    if args.command == "self-test": return self_test()
    if args.command == "prepare-evals": dump_json(make_eval_jobs(load_json(Path(args.queue)), source_session_id=args.source_session_id, handoff_id=args.handoff_id), Path(args.output) if args.output else None); return 0
    if args.command == "validate-jobs":
        payload = load_json(Path(args.jobs)); errors = [f"{j.get('job_id')}: {e}" for j in payload.get("jobs", []) for e in validate_job(j)]
        if errors:
            for e in errors: print(e, file=sys.stderr)
            return 1
        print(f"validated semantic jobs: {len(payload.get('jobs', []))}"); return 0
    validated, errors = validate_results(load_json(Path(args.jobs)), load_json(Path(args.results)))
    if errors:
        for e in errors: print(e, file=sys.stderr)
        return 1
    judgments = eval_judgments(validated)
    if args.judgments_output: dump_json(judgments, Path(args.judgments_output))
    print(f"validated semantic results: {len(validated)}; eval judgments: {len(judgments)}"); return 0


if __name__ == "__main__": raise SystemExit(main())
