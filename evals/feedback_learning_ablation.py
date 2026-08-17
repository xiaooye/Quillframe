#!/usr/bin/env python3
"""Prepare fingerprint-bound independent semantic jobs for feedback-learning ablations.

This deterministic tool never judges the winner. It packages anonymous A/B
condition summaries for the registered independent `quality.ablation_compare`
contract. Without real independent results the truthful state is PENDING_MODEL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals" / "feedback_learning_ablation_manifest.json"
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))

from semantic_worker_router import make_contract_job, validate_result  # noqa: E402

SCHEMA = "novelforge_feedback_learning_ablation_queue_v1"
CONTRACT = "quality.ablation_compare"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def _condition(condition_id: str, value: dict[str, Any]) -> dict[str, Any]:
    judgment = {"trace": value}
    return {
        "condition_id": condition_id,
        "input_fingerprint": fp({"condition_input": value}),
        "result_fingerprint": fp({"condition_result": judgment}),
        "judgment": judgment,
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "novelforge_feedback_learning_ablation_manifest_v1":
        errors.append("manifest schema mismatch")
    if manifest.get("pair_review_contract") != CONTRACT:
        errors.append("pair review contract mismatch")
    if manifest.get("model_execution_required_for_semantic_outcomes") is not True:
        errors.append("semantic outcomes must require model execution")
    if manifest.get("manager_self_judgment_allowed") is not False:
        errors.append("manager self judgment must be forbidden")
    if manifest.get("missing_model_state") != "PENDING_MODEL":
        errors.append("missing model state must be PENDING_MODEL")
    authority = manifest.get("authority")
    if not isinstance(authority, dict) or any(authority.get(k) is not False for k in ("canon_write", "project_profile_write", "durable_user_taste_write", "framework_behavior_write")):
        errors.append("all authority fields must be false")
    controls = manifest.get("controls")
    if not isinstance(controls, list) or len(controls) < 6:
        errors.append("at least six feedback-learning controls required")
        return errors
    seen: set[str] = set()
    for row in controls:
        if not isinstance(row, dict):
            errors.append("control must be object"); continue
        cid = row.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append("control id required"); continue
        if cid in seen:
            errors.append(f"duplicate control id: {cid}")
        seen.add(cid)
        if not isinstance(row.get("candidate_ref"), str) or not row["candidate_ref"]:
            errors.append(f"{cid}: candidate_ref required")
        if not isinstance(row.get("observation_criteria"), list) or not row["observation_criteria"]:
            errors.append(f"{cid}: observation criteria required")
        if not isinstance(row.get("condition_a"), dict) or not isinstance(row.get("condition_b"), dict):
            errors.append(f"{cid}: two conditions required")
    return errors


def build_queue(manifest: dict[str, Any]) -> dict[str, Any]:
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("; ".join(errors))
    jobs = []
    for row in manifest["controls"]:
        candidate_fp = fp({"candidate_ref": row["candidate_ref"]})
        payload = {
            "comparison_id": "FBK-ABL-" + row["id"],
            "candidate_fingerprint": candidate_fp,
            "condition_a": _condition("A", row["condition_a"]),
            "condition_b": _condition("B", row["condition_b"]),
            "observation_criteria": list(row["observation_criteria"]),
        }
        job = make_contract_job(CONTRACT, "FBK-ABL-" + row["id"], payload, source_session_id="SES-FEEDBACK-ABLATION")
        if job.get("provenance", {}).get("independent_gate") is not True:
            raise ValueError(f"{row['id']}: registered contract must require independent gate")
        jobs.append({"control_id": row["id"], "job": job})
    return {
        "schema": SCHEMA,
        "manifest_fingerprint": fp(manifest),
        "contract": CONTRACT,
        "semantic_status": "PENDING_MODEL",
        "reason": "independent semantic comparison results not supplied",
        "jobs": jobs,
        "manager_self_judgment_allowed": False,
        "authority": False,
        "model_execution": False,
    }


def consume_results(queue: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    by_subject = {r.get("subject_id"): r for r in results if isinstance(r, dict)}
    observations = []
    pending = []
    for item in queue.get("jobs", []):
        job = item["job"]
        result = by_subject.get(job.get("subject_id"))
        if result is None:
            pending.append(item["control_id"]); continue
        errors = validate_result(job, result)
        if errors:
            raise ValueError(f"{item['control_id']}: " + "; ".join(errors))
        if result.get("status") != "completed":
            pending.append(item["control_id"]); continue
        execution = result.get("execution") if isinstance(result.get("execution"), dict) else {}
        worker = result.get("worker") if isinstance(result.get("worker"), dict) else {}
        invocation = execution.get("worker_session_id") or execution.get("attempt_id") or worker.get("run_reference")
        if not invocation:
            raise ValueError(f"{item['control_id']}: independent invocation lineage required")
        observations.append({
            "control_id": item["control_id"],
            "job_fingerprint": job["input_fingerprint"],
            "result_fingerprint": fp(result),
            "invocation": str(invocation),
            "judgment": result["judgment"],
        })
    status = "PENDING_MODEL" if pending else "SEMANTIC_EVIDENCE_READY"
    return {
        "schema": "novelforge_feedback_learning_ablation_evidence_v1",
        "semantic_status": status,
        "pending_controls": pending,
        "observations": observations,
        "authority": False,
        "framework_promotion_authority": False,
        "model_execution": False,
    }


def self_test() -> dict[str, Any]:
    manifest = load(MANIFEST)
    queue = build_queue(manifest)
    unique = len({item["job"]["input_fingerprint"] for item in queue["jobs"]}) == len(queue["jobs"])
    no_gold = all(
        not any(k in canonical(item["job"]).decode("utf-8") for k in ("expected_verdict", "gold_label", "simpler_arm"))
        for item in queue["jobs"]
    )
    pending = consume_results(queue, [])
    ok = all([
        queue["semantic_status"] == "PENDING_MODEL",
        unique,
        no_gold,
        pending["semantic_status"] == "PENDING_MODEL",
        len(pending["pending_controls"]) == len(queue["jobs"]),
        queue["manager_self_judgment_allowed"] is False,
    ])
    return {
        "schema": SCHEMA,
        "feedback_learning_ablation_contract": "PASS" if ok else "FAIL",
        "independent_contract_bound": all(item["job"].get("provenance", {}).get("independent_gate") is True for item in queue["jobs"]),
        "unique_fingerprint_bound_jobs": unique,
        "hidden_expected_not_in_jobs": no_gold,
        "no_model_state": pending["semantic_status"],
        "manager_self_judgment_allowed": False,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge feedback learning ablation packager")
    p.add_argument("--manifest", default=str(MANIFEST))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    consume = sub.add_parser("consume"); consume.add_argument("--results", required=True)
    sub.add_parser("self-test")
    a = p.parse_args()
    if a.cmd == "self-test":
        out = self_test()
    else:
        queue = build_queue(load(Path(a.manifest)))
        if a.cmd == "build":
            out = queue
        else:
            results = json.loads(Path(a.results).read_text(encoding="utf-8"))
            if not isinstance(results, list):
                raise ValueError("results must be JSON array")
            out = consume_results(queue, results)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("feedback_learning_ablation_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
