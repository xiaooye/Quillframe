#!/usr/bin/env python3
"""Public-repository synthetic integration probe for NovelForge peer primitives.

This is test infrastructure only. It intentionally does not create a real
Project-owned independent-review receipt and never treats the Framework repo as
a consuming Project. The probe validates registered-contract, relay, receipt
primitives with a synthetic consumer identity and separately asserts that the
real Project-hosted bridge rejects self-hosting by the Framework repository.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))

from peer_bridge_receipt import build_receipt, validate_receipt  # noqa: E402
from peer_chat_relay import build as build_packet, validate_peer_result  # noqa: E402
from registered_contract_binding import validate_registered_job  # noqa: E402
from semantic_worker_router import make_contract_job  # noqa: E402

FRAMEWORK_REPO = "xiaooye/cn_webnovel_agent"
SYNTHETIC_PROJECT_ID = "PROJECT-PUBLIC-TEST"
SYNTHETIC_PROJECT_REPO = "xiaooye/novelforge-public-test-consumer"


def assert_self_host_guard(*, issue_number: int, framework_commit: str, job: dict) -> bool:
    bridge = ROOT / ".github" / "actions" / "project-peer-semantic" / "bridge.py"
    with tempfile.TemporaryDirectory(prefix="novelforge-public-peer-probe-") as tmp:
        workspace = Path(tmp)
        project = workspace / "project"
        project.mkdir()
        (project / "novelforge.toml").write_text(
            "\n".join([
                "[novelforge]",
                'schema="novelforge_project_v1"',
                'project_schema_version="1"',
                "[project]",
                f'id="{SYNTHETIC_PROJECT_ID}"',
                'title="Public integration fixture"',
                'language="en"',
                'version="0.0.0-test"',
                'status="active"',
                "[adapter]",
                'layout="mapped"',
            ]) + "\n",
            encoding="utf-8",
        )
        (project / "novelforge.lock.json").write_text(
            json.dumps({
                "schema": "novelforge_lock_v1",
                "project_schema_version": "1",
                "framework": {
                    "name": "NovelForge",
                    "source_repo": FRAMEWORK_REPO,
                    "commit": framework_commit,
                    "bundle_fingerprint": "sha256:" + "b" * 64,
                },
            }),
            encoding="utf-8",
        )
        event = workspace / "event.json"
        event.write_text(json.dumps({
            "issue": {
                "number": issue_number,
                "title": f"[novelforge-peer][{SYNTHETIC_PROJECT_ID}] {job['job_id']}",
                "body": json.dumps(job),
            }
        }), encoding="utf-8")
        env = os.environ.copy()
        env.update({
            "GITHUB_WORKSPACE": str(workspace),
            "GITHUB_EVENT_PATH": str(event),
            "GITHUB_REPOSITORY": FRAMEWORK_REPO,
            "GITHUB_REPOSITORY_OWNER": "xiaooye",
            "GITHUB_ACTOR": "xiaooye",
            "NOVELFORGE_PROJECT_ROOT": "project",
            "NOVELFORGE_PROJECT_ID": SYNTHETIC_PROJECT_ID,
            "NOVELFORGE_ACTION_REPOSITORY": FRAMEWORK_REPO,
            "NOVELFORGE_ACTION_REF": framework_commit,
            "NOVELFORGE_BRIDGE_MODE": "prepare",
        })
        proc = subprocess.run(
            [sys.executable, str(bridge)],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return proc.returncode != 0 and "consumer peer bridge may not run with Framework repository as caller" in output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--framework-commit", required=True)
    args = parser.parse_args()
    if args.issue <= 0:
        raise SystemExit("issue must be positive")
    if not re.fullmatch(r"[0-9a-f]{40}", args.framework_commit):
        raise SystemExit("framework commit must be exact 40-char lowercase SHA")

    candidate_fp = "sha256:" + "a" * 64
    job = make_contract_job(
        "quality.production_review",
        "PUBLIC-ISSUE-57",
        {
            "candidate_fingerprint": candidate_fp,
            "candidate_text": "Synthetic public Actions integration fixture; not novel content.",
            "reader_grip": "very_high",
        },
        source_session_id="SES-PUBLIC-PROBE-MANAGER",
    )
    job["provenance"].update({
        "project_id": SYNTHETIC_PROJECT_ID,
        "project_repo": SYNTHETIC_PROJECT_REPO,
        "framework_repo": FRAMEWORK_REPO,
        "framework_commit": args.framework_commit,
    })
    contract_errors = validate_registered_job(job)

    packet = build_packet(job)
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "chatgpt_peer_chat",
            "model_or_reviewer": "synthetic-fixture",
            "run_reference": packet["relay_nonce"],
        },
        "judgment": {
            "confidence": 0.99,
            "result": "pass",
            "codes": [],
            "evidence": ["synthetic structural fixture"],
            "summary": "Synthetic structural validation only.",
            "flatness_risk": "low",
        },
        "proposals": [],
        "errors": [],
    }
    relay_errors = validate_peer_result(packet, result)

    run_id = int(os.environ.get("GITHUB_RUN_ID", "1"))
    run_attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    synthetic_comment_id = args.issue * 1000 + 1
    receipt = build_receipt(
        packet,
        result,
        project_id=SYNTHETIC_PROJECT_ID,
        project_repo=SYNTHETIC_PROJECT_REPO,
        framework_repo=FRAMEWORK_REPO,
        framework_commit=args.framework_commit,
        issue_number=args.issue,
        runtime_trace={
            "github_run_id": run_id,
            "github_run_attempt": run_attempt,
            "github_event_name": "issue_comment",
            "result_comment_id": synthetic_comment_id,
            "workflow_name": "NovelForge public synthetic peer probe",
            "framework_action_ref": args.framework_commit,
        },
    )
    receipt_errors = validate_receipt(receipt, packet, result)

    tampered = json.loads(json.dumps(receipt))
    tampered["result_fingerprint"] = "sha256:" + "0" * 64
    tamper_rejected = any(
        "result_fingerprint" in item for item in validate_receipt(tampered, packet, result)
    )
    self_host_blocked = assert_self_host_guard(
        issue_number=args.issue,
        framework_commit=args.framework_commit,
        job=job,
    )

    checks = {
        "registered_contract_valid": not contract_errors,
        "peer_packet_result_binding_valid": not relay_errors,
        "synthetic_receipt_primitive_valid": not receipt_errors,
        "receipt_tamper_rejected": tamper_rejected,
        "framework_self_host_guard_blocked": self_host_blocked,
        "receipt_authority_false": receipt.get("authority") is False,
        "receipt_model_execution_false": receipt.get("model_execution") is False,
    }
    output = {
        "schema": "novelforge_public_peer_issue_probe_v1",
        "issue_number": args.issue,
        "framework_commit": args.framework_commit,
        "synthetic_consumer_only": True,
        "production_project_receipt": False,
        "literary_judgment": False,
        "authority": False,
        "checks": checks,
        "errors": {
            "registered_contract": contract_errors,
            "relay": relay_errors,
            "receipt": receipt_errors,
        },
        "result": "PASS" if all(checks.values()) else "FAIL",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
