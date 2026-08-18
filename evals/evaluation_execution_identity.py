#!/usr/bin/env python3
"""Create and validate content-addressed execution identities for semantic eval evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_evaluation_execution_identity_v1"
FP_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def framework_version(root: Path) -> str:
    text = (root / "HARNESS_MANIFEST.yaml").read_text(encoding="utf-8")
    m = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", text)
    if not m:
        raise ValueError("HARNESS_MANIFEST.yaml missing version")
    return m.group(1)


def identity_payload(identity: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in identity.items() if k != "identity_fingerprint"}


def optional_positive_int(env: dict[str, str], key: str) -> int | None:
    raw = env.get(key)
    if raw in {None, ""}:
        return None
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def validate_identity(identity: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if identity.get("schema") != SCHEMA:
        errors.append("execution identity schema mismatch")
    candidate = identity.get("candidate", {})
    if not isinstance(candidate.get("commit"), str) or not SHA_RE.fullmatch(candidate["commit"]):
        errors.append("candidate.commit must be 40 lowercase hex")
    if not isinstance(candidate.get("framework_version"), str) or not candidate["framework_version"]:
        errors.append("candidate.framework_version required")
    reviewer = identity.get("reviewer", {})
    for key in ("provider", "model_id", "model_revision_binding"):
        if not isinstance(reviewer.get(key), str) or not reviewer[key]:
            errors.append(f"reviewer.{key} required")
    evaluation = identity.get("evaluation", {})
    if evaluation.get("blind") is not True:
        errors.append("evaluation must be blind")
    for key in ("queue_fingerprint", "jobs_fingerprint", "capabilities_fingerprint", "harness_fingerprint"):
        value = evaluation.get(key)
        if not isinstance(value, str) or not FP_RE.fullmatch(value):
            errors.append(f"evaluation.{key} must be sha256 fingerprint")
    environment = identity.get("environment", {})
    for key in ("runner_os", "runner_arch", "python_version"):
        if not isinstance(environment.get(key), str) or not environment[key]:
            errors.append(f"environment.{key} required")
    budget = identity.get("resource_budget", {})
    for key in ("max_semantic_calls", "job_timeout_minutes"):
        value = budget.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            errors.append(f"resource_budget.{key} must be a positive integer or null")
    provenance = identity.get("provenance", {})
    if not isinstance(provenance.get("github_run_id"), str) or not provenance["github_run_id"]:
        errors.append("provenance.github_run_id required")
    actual = identity.get("identity_fingerprint")
    expected = fingerprint(identity_payload(identity))
    if actual != expected:
        errors.append("identity_fingerprint mismatch")
    return errors


def build_identity(*, root: Path, queue: Path, jobs: Path, capabilities: Path, candidate_commit: str,
                   model_id: str, reasoning_effort: str, domain: str, env: dict[str, str]) -> dict[str, Any]:
    if not SHA_RE.fullmatch(candidate_commit):
        raise ValueError("candidate commit must be 40 lowercase hex")
    queue_data = load_json(queue)
    harness_files = [
        "HARNESS_MANIFEST.yaml",
        "evals/build_judge_queue.py",
        "evals/run_evals.py",
        "harness/semantic_workers/semantic_worker_router.py",
        "harness/semantic_workers/semantic_worker_runner.py",
        "harness/semantic_workers/model_contract_catalog.json",
    ]
    harness_parts = {rel: file_fingerprint(root / rel) for rel in harness_files}
    max_calls = optional_positive_int(env, "QUILLFRAME_MAX_SEMANTIC_CALLS")
    job_timeout = optional_positive_int(env, "QUILLFRAME_JOB_TIMEOUT_MINUTES")
    budget_binding = env.get("QUILLFRAME_RESOURCE_BUDGET_BINDING")
    if not budget_binding:
        budget_binding = "workflow_has_no_explicit_token_or_job-timeout_budget" if max_calls is None and job_timeout is None else "explicit_workflow_resource_budget"
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "candidate": {
            "commit": candidate_commit,
            "framework_version": framework_version(root),
        },
        "reviewer": {
            "provider": "openai",
            "model_id": model_id,
            "model_revision_binding": "provider_managed_unpinned",
            "reasoning_effort": reasoning_effort,
            "sampling": {"temperature": None, "seed": None, "binding": "provider_defaults_unpinned"},
        },
        "evaluation": {
            "suite_version": queue_data.get("suite_version"),
            "domain": domain,
            "blind": True,
            "queue_fingerprint": file_fingerprint(queue),
            "jobs_fingerprint": file_fingerprint(jobs),
            "capabilities_fingerprint": file_fingerprint(capabilities),
            "harness_fingerprint": fingerprint(harness_parts),
            "harness_components": harness_parts,
        },
        "environment": {
            "runner_os": env.get("RUNNER_OS") or platform.system(),
            "runner_arch": env.get("RUNNER_ARCH") or platform.machine(),
            "runner_image_os": env.get("ImageOS"),
            "runner_image_version": env.get("ImageVersion"),
            "python_version": platform.python_version(),
        },
        "resource_budget": {
            "require_complete": True,
            "max_semantic_calls": max_calls,
            "job_timeout_minutes": job_timeout,
            "token_budget": None,
            "binding": budget_binding,
        },
        "provenance": {
            "github_run_id": env.get("GITHUB_RUN_ID") or "local-self-test",
            "github_run_attempt": env.get("GITHUB_RUN_ATTEMPT"),
            "github_workflow": env.get("GITHUB_WORKFLOW"),
            "github_ref": env.get("GITHUB_REF"),
        },
    }
    payload["identity_fingerprint"] = fingerprint(payload)
    return payload


def self_test() -> int:
    base = {
        "schema": SCHEMA,
        "candidate": {"commit": "a" * 40, "framework_version": "9.9.9"},
        "reviewer": {"provider": "openai", "model_id": "test-model", "model_revision_binding": "provider_managed_unpinned"},
        "evaluation": {"blind": True, **{k: "sha256:" + c * 64 for k, c in [
            ("queue_fingerprint", "1"), ("jobs_fingerprint", "2"), ("capabilities_fingerprint", "3"), ("harness_fingerprint", "4")]}},
        "environment": {"runner_os": "test", "runner_arch": "test", "python_version": "3.11"},
        "resource_budget": {"require_complete": True, "max_semantic_calls": 12, "job_timeout_minutes": 45},
        "provenance": {"github_run_id": "1"},
    }
    base["identity_fingerprint"] = fingerprint(base)
    pristine = not validate_identity(base)
    tampered = json.loads(json.dumps(base))
    tampered["reviewer"]["model_id"] = "other-model"
    tamper_detected = "identity_fingerprint mismatch" in validate_identity(tampered)
    rebound = json.loads(json.dumps(tampered))
    rebound["identity_fingerprint"] = fingerprint(identity_payload(rebound))
    rebound_valid = not validate_identity(rebound)
    bad_budget = json.loads(json.dumps(base))
    bad_budget["resource_budget"]["max_semantic_calls"] = 0
    budget_guard = "resource_budget.max_semantic_calls must be a positive integer or null" in validate_identity(bad_budget)
    ok = pristine and tamper_detected and rebound_valid and budget_guard and base["identity_fingerprint"] != rebound["identity_fingerprint"]
    print(json.dumps({"execution_identity_contract": "PASS" if ok else "FAIL", "tamper_detected": tamper_detected,
                      "model_change_changes_identity": base["identity_fingerprint"] != rebound["identity_fingerprint"],
                      "resource_budget_guard": budget_guard}, indent=2))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    v = sub.add_parser("validate")
    v.add_argument("path")
    c = sub.add_parser("capture")
    c.add_argument("--queue", required=True)
    c.add_argument("--jobs", required=True)
    c.add_argument("--capabilities", required=True)
    c.add_argument("--candidate-commit", required=True)
    c.add_argument("--model", required=True)
    c.add_argument("--reasoning-effort", required=True)
    c.add_argument("--domain", required=True)
    c.add_argument("--output", required=True)
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "validate":
        errors = validate_identity(load_json(Path(args.path)))
        print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
        return 0 if not errors else 1
    root = Path(__file__).resolve().parents[1]
    ident = build_identity(root=root, queue=Path(args.queue), jobs=Path(args.jobs), capabilities=Path(args.capabilities),
                           candidate_commit=args.candidate_commit, model_id=args.model, reasoning_effort=args.reasoning_effort,
                           domain=args.domain, env=dict(os.environ))
    errors = validate_identity(ident)
    if errors:
        raise SystemExit("; ".join(errors))
    Path(args.output).write_text(json.dumps(ident, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(ident["identity_fingerprint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
