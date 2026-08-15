#!/usr/bin/env python3
"""Validate a reviewed semantic-eval baseline without fabricating model output."""
from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
DEFAULT_BASELINE = EVALS / "baselines" / "semantic-8.0-dev.1.json"
ROUTER = ROOT / "harness" / "semantic_workers" / "semantic_worker_router.py"
SCHEMA = "novelforge_semantic_acceptance_baseline_v1"
FP_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_BASELINE_KEYS = {
    "expected", "expected_verdict", "expected_codes", "gold", "gold_label",
    "judgment", "evidence", "codes", "verdict", "raw_output", "reviewer_output",
    "chain_of_thought", "prompt", "prior_result",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def framework_version() -> str:
    text = (ROOT / "HARNESS_MANIFEST.yaml").read_text(encoding="utf-8")
    m = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", text)
    if not m:
        raise ValueError("HARNESS_MANIFEST.yaml missing version")
    return m.group(1)


def leaked_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_BASELINE_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(leaked_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            hits.extend(leaked_keys(child, f"{path}[{i}]"))
    return hits


def current_semantic_jobs() -> tuple[str, dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="novelforge-semantic-baseline-") as td:
        tmp = Path(td)
        queue = tmp / "queue.json"
        jobs = tmp / "jobs.json"
        subprocess.run(
            [sys.executable, str(EVALS / "build_judge_queue.py"), "--output", str(queue)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        subprocess.run(
            [sys.executable, str(ROUTER), "prepare-evals", "--queue", str(queue), "--output", str(jobs),
             "--source-session-id", "SES-BASELINE-VALIDATOR", "--handoff-id", "HO-BASELINE-VALIDATOR"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        subprocess.run(
            [sys.executable, str(ROUTER), "validate-jobs", "--jobs", str(jobs)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        q = load(queue)
        j = load(jobs)
    if q.get("blind") is not True or j.get("blind") is not True:
        raise ValueError("semantic baseline validator requires blind queue/jobs")
    mapping = {item["subject_id"]: item["input_fingerprint"] for item in j["jobs"]}
    if len(mapping) != len(j["jobs"]):
        raise ValueError("duplicate semantic subject_id in live jobs")
    return str(q.get("suite_version")), mapping


def validate_baseline(baseline: dict[str, Any], suite_version: str, current: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(baseline, dict):
        return ["baseline must be object"]
    if baseline.get("schema") != SCHEMA:
        errors.append("baseline schema mismatch")
    if baseline.get("framework_version") != framework_version():
        errors.append("framework version mismatch")
    if baseline.get("suite_version") != suite_version:
        errors.append("suite version mismatch")
    if baseline.get("status") != "semantic_accept":
        errors.append("baseline status must be semantic_accept")
    if baseline.get("blind") is not True or baseline.get("fingerprint_bound") is not True:
        errors.append("baseline must be blind and fingerprint-bound")
    if not isinstance(baseline.get("acceptance_subject_commit"), str) or not SHA_RE.fullmatch(baseline["acceptance_subject_commit"]):
        errors.append("acceptance_subject_commit must be 40 lowercase hex")
    if baseline.get("authority") is not False or baseline.get("model_execution") is not False:
        errors.append("baseline is non-authoritative and validator performs no model execution")
    permissions = baseline.get("permissions")
    expected_permissions = {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False}
    if permissions != expected_permissions:
        errors.append("baseline permissions must all be false and exact")

    leaks = leaked_keys(baseline)
    if leaks:
        errors.append("baseline stores forbidden reviewer/gold fields: " + ", ".join(leaks))

    raw_sources = baseline.get("review_sources")
    sources: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append("review_sources must be non-empty list")
    else:
        for src in raw_sources:
            if not isinstance(src, dict):
                errors.append("review source must be object")
                continue
            sid = src.get("source_id")
            if not isinstance(sid, str) or not sid or sid in sources:
                errors.append(f"invalid or duplicate review source id: {sid!r}")
                continue
            sources[sid] = src
            if not isinstance(src.get("github_run_id"), int) or src["github_run_id"] <= 0:
                errors.append(f"{sid}: github_run_id must be positive integer")
            if not isinstance(src.get("artifact_name"), str) or not src["artifact_name"]:
                errors.append(f"{sid}: artifact_name required")
            if not isinstance(src.get("artifact_digest"), str) or not FP_RE.fullmatch(src["artifact_digest"]):
                errors.append(f"{sid}: artifact_digest must be sha256 fingerprint")
            if not isinstance(src.get("transport"), str) or not src["transport"]:
                errors.append(f"{sid}: transport required")
            if src.get("independent_invocation") is not True or src.get("fresh_per_fingerprint") is not True:
                errors.append(f"{sid}: independent/fresh review proof required")

    raw_cases = baseline.get("cases")
    records: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_cases, list):
        errors.append("cases must be list")
        raw_cases = []
    for record in raw_cases:
        if not isinstance(record, dict):
            errors.append("case record must be object")
            continue
        cid = record.get("case_id")
        if not isinstance(cid, str) or not cid or cid in records:
            errors.append(f"invalid or duplicate case_id: {cid!r}")
            continue
        records[cid] = record
        fp = record.get("input_fingerprint")
        if not isinstance(fp, str) or not FP_RE.fullmatch(fp):
            errors.append(f"{cid}: invalid input_fingerprint")
        if record.get("result") != "PASS":
            errors.append(f"{cid}: only reviewed PASS may enter semantic acceptance baseline")
        if record.get("source_id") not in sources:
            errors.append(f"{cid}: unknown review source")
        supersedes = record.get("supersedes")
        if supersedes is not None:
            if not isinstance(supersedes, dict):
                errors.append(f"{cid}: supersedes must be object")
            else:
                old = supersedes.get("input_fingerprint")
                if not isinstance(old, str) or not FP_RE.fullmatch(old) or old == fp:
                    errors.append(f"{cid}: superseded fingerprint must be valid and different")
                if supersedes.get("reason") != "material_rubric_fingerprint_change":
                    errors.append(f"{cid}: unsupported supersession reason")

    missing = sorted(set(current) - set(records))
    extra = sorted(set(records) - set(current))
    if missing:
        errors.append("missing current semantic cases: " + ", ".join(missing))
    if extra:
        errors.append("baseline contains non-current semantic cases: " + ", ".join(extra))
    for cid in sorted(set(current) & set(records)):
        if records[cid].get("input_fingerprint") != current[cid]:
            errors.append(f"{cid}: current fingerprint differs from accepted fingerprint")
    if len({r.get("input_fingerprint") for r in records.values()}) != len(records):
        errors.append("accepted input fingerprints must be unique")
    used_sources = {r.get("source_id") for r in records.values()}
    unused = sorted(set(sources) - used_sources)
    if unused:
        errors.append("unused review sources: " + ", ".join(unused))
    return errors


def evaluate(path: Path) -> dict[str, Any]:
    suite_version, current = current_semantic_jobs()
    baseline = load(path)
    errors = validate_baseline(baseline, suite_version, current)
    return {
        "schema": "novelforge_semantic_acceptance_validation_v1",
        "baseline": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "suite_version": suite_version,
        "semantic_case_count": len(current),
        "accepted_case_count": len(baseline.get("cases", [])) if isinstance(baseline, dict) else 0,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "baseline_is_model_output": False,
        "model_execution": False,
        "authority": False,
    }


def self_test() -> int:
    suite_version, current = current_semantic_jobs()
    baseline = load(DEFAULT_BASELINE)
    errors = validate_baseline(baseline, suite_version, current)
    tampered = copy.deepcopy(baseline)
    tampered["cases"][0]["input_fingerprint"] = "sha256:" + "0" * 64
    tamper_detected = bool(validate_baseline(tampered, suite_version, current))
    missing = copy.deepcopy(baseline)
    missing["cases"] = missing["cases"][:-1]
    missing_detected = bool(validate_baseline(missing, suite_version, current))
    authority = copy.deepcopy(baseline)
    authority["authority"] = True
    authority_detected = bool(validate_baseline(authority, suite_version, current))
    ok = not errors and tamper_detected and missing_detected and authority_detected
    print(json.dumps({
        "semantic_acceptance_baseline_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "suite_version": suite_version,
        "semantic_case_count": len(current),
        "baseline_errors": errors,
        "fingerprint_drift_detected": tamper_detected,
        "missing_case_detected": missing_detected,
        "authority_escalation_detected": authority_detected,
        "baseline_is_model_output": False,
        "model_execution": False,
        "authority": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge reviewed semantic acceptance baseline validator")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    v = sub.add_parser("validate")
    v.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    report = evaluate(Path(args.baseline).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
