#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "HARNESS_MANIFEST.yaml"
WORKFLOW = ROOT / ".github/workflows/novelforge-progress-stall.yml"
EXPECTED_HARNESS_BLOB = "6c894b0c24a1fc2d41e3d04a1b819f18fddd4c49"
EXPECTED_WORKFLOW_BLOB = "bbf8a710bc019747fd155279d4beab6e0406c03a"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = b"blob " + str(len(data)).encode() + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one insertion point, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    if git_blob_sha(HARNESS) != EXPECTED_HARNESS_BLOB:
        raise SystemExit("HARNESS before-blob mismatch; refusing progress/stall integration")
    if git_blob_sha(WORKFLOW) != EXPECTED_WORKFLOW_BLOB:
        raise SystemExit("progress/stall workflow before-blob mismatch; refusing integration")

    text = HARNESS.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "  author_steering: harness/control_plane/author_steering.py\n"
        "  author_steering_schema: harness/control_plane/author_steering.schema.json\n",
        "  author_steering: harness/control_plane/author_steering.py\n"
        "  author_steering_schema: harness/control_plane/author_steering.schema.json\n"
        "  progress_stall: harness/control_plane/progress_stall.py\n"
        "  progress_stall_schema: harness/control_plane/progress_stall.schema.json\n",
        "harness discovery",
    )
    text = replace_once(
        text,
        "  author_steering_followup_auto_execute: false\n"
        "  author_steering_model_execution: false\n",
        "  author_steering_followup_auto_execute: false\n"
        "  author_steering_model_execution: false\n"
        "  progress_observation_transport_event: feedback.observed\n"
        "  progress_observation_schema: novelforge_progress_observation_v1\n"
        "  progress_state_schema: novelforge_progress_state_v1\n"
        "  progress_replan_request_schema: novelforge_progress_replan_request_v1\n"
        "  progress_observation_source_kind: deterministic_runtime\n"
        "  progress_requires_durable_session_binding: true\n"
        "  progress_requires_current_run_binding: true\n"
        "  progress_predecessor_chain: linear\n"
        "  progress_waiting_counts_as_stall: false\n"
        "  progress_transport_retry_counts_as_stall: false\n"
        "  progress_replan_followup_auto_execute: false\n"
        "  progress_completion_authority: false\n"
        "  progress_production_readiness_authority: false\n"
        "  progress_model_execution: false\n",
        "session runtime contract",
    )
    text = replace_once(
        text,
        "  author_steering_consumption: exactly-once-session-scoped\n",
        "  author_steering_consumption: exactly-once-session-scoped\n"
        "  progress_observation_transport_event: feedback.observed\n"
        "  progress_observation_typed_payload_required: true\n"
        "  progress_observation_source_kind: deterministic_runtime\n"
        "  progress_observation_requires_session_version_hash: true\n"
        "  progress_observation_requires_current_session_run: true\n"
        "  progress_observation_idempotency: required\n"
        "  progress_replan_request_auto_execute: false\n",
        "control plane contract",
    )
    text = replace_once(
        text,
        "  author_steering: .github/workflows/novelforge-author-steering.yml\n",
        "  author_steering: .github/workflows/novelforge-author-steering.yml\n"
        "  progress_stall: .github/workflows/novelforge-progress-stall.yml\n",
        "workflow discovery",
    )
    text = replace_once(
        text,
        "state-integrity-cross-contract-self-test, author-steering-self-test, settlement-runtime-self-test",
        "state-integrity-cross-contract-self-test, author-steering-self-test, progress-stall-self-test, settlement-runtime-self-test",
        "normal CI requirement",
    )
    text = replace_once(
        text,
        "  author_steering_consequential_write_interruptible: false\n",
        "  author_steering_consequential_write_interruptible: false\n"
        "  progress_observation_grants_canon_authority: false\n"
        "  progress_state_grants_project_write_authority: false\n"
        "  progress_state_grants_framework_write_authority: false\n"
        "  progress_state_grants_settlement_authority: false\n"
        "  progress_state_grants_production_readiness_authority: false\n"
        "  progress_state_grants_acceptance_authority: false\n"
        "  progress_state_grants_completion_authority: false\n"
        "  progress_replan_request_can_auto_mutate_plan: false\n"
        "  progress_followup_ops_auto_execute: false\n",
        "write boundary",
    )
    HARNESS.write_text(text, encoding="utf-8")

    workflow = WORKFLOW.read_text(encoding="utf-8")
    workflow = replace_once(
        workflow,
        "on:\n  pull_request:\n    branches: [main]\n",
        "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n",
        "main push trigger",
    )
    WORKFLOW.write_text(workflow, encoding="utf-8")

    commands = [
        ["python", "-m", "py_compile", "harness/control_plane/progress_stall.py"],
        ["python", "-m", "json.tool", "harness/control_plane/progress_stall.schema.json"],
        ["python", "harness/control_plane/progress_stall.py", "self-test", "--path", "/tmp/novelforge-progress-stall-integrate.db"],
        ["python", "harness/control_plane/author_steering.py", "self-test", "--path", "/tmp/novelforge-author-steering-progress-integration.db"],
        ["python", "scripts/version_identity.py"],
        ["python", "scripts/docs_quality.py"],
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=ROOT, check=True)

    print("HARNESS_AFTER_BLOB=" + git_blob_sha(HARNESS))
    print("WORKFLOW_AFTER_BLOB=" + git_blob_sha(WORKFLOW))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
