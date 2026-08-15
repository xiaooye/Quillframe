#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "HARNESS_MANIFEST.yaml"
WORKFLOW = ROOT / ".github/workflows/novelforge-author-steering.yml"
EXPECTED_HARNESS_BLOB = "e36c536ab35fdf142c235ba14929cfb57c6f3929"
EXPECTED_WORKFLOW_BLOB = "005491d501588c274c09a96bee8fde9e29ca51dd"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = b"blob " + str(len(data)).encode() + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def replace_once(text: str, old: str, new: str, name: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one insertion point, found {text.count(old)}")
    return text.replace(old, new, 1)


def main() -> int:
    if git_blob_sha(HARNESS) != EXPECTED_HARNESS_BLOB:
        raise SystemExit("HARNESS before-blob mismatch; refusing migration")
    if git_blob_sha(WORKFLOW) != EXPECTED_WORKFLOW_BLOB:
        raise SystemExit("author-steering workflow before-blob mismatch; refusing migration")

    text = HARNESS.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "  propagation_debt: harness/propagation_debt.py\n  propagation_debt_schema: harness/propagation_debt.schema.json\n",
        "  propagation_debt: harness/propagation_debt.py\n  propagation_debt_schema: harness/propagation_debt.schema.json\n"
        "  author_steering: harness/control_plane/author_steering.py\n"
        "  author_steering_schema: harness/control_plane/author_steering.schema.json\n",
        "harness discovery",
    )
    text = replace_once(
        text,
        "  resume_revalidates_project_authority: true\n  resume_reresolves_required_capabilities: true\n",
        "  resume_revalidates_project_authority: true\n  resume_reresolves_required_capabilities: true\n"
        "  author_steering_transport_event: feedback.observed\n"
        "  author_steering_payload_schema: novelforge_author_steering_request_v1\n"
        "  author_steering_safe_point_schema: novelforge_author_steering_safe_point_v1\n"
        "  author_steering_decision_schema: novelforge_author_steering_decision_v1\n"
        "  author_steering_receipt_schema: novelforge_author_steering_receipt_v1\n"
        "  author_steering_source_kinds: [user, authorized_human]\n"
        "  author_steering_requires_safe_point: true\n"
        "  author_steering_consume_once: true\n"
        "  author_steering_resume_lineage_revalidation: true\n"
        "  author_steering_consequential_write_interruptible: false\n"
        "  author_steering_followup_auto_execute: false\n"
        "  author_steering_model_execution: false\n",
        "session runtime contract",
    )
    text = replace_once(
        text,
        "  runtime_command_before_state_compare_and_swap: required\n",
        "  runtime_command_before_state_compare_and_swap: required\n"
        "  author_steering_transport_event: feedback.observed\n"
        "  author_steering_typed_payload_required: true\n"
        "  author_steering_generic_feedback_auto_routes: false\n"
        "  author_steering_consumption: exactly-once-session-scoped\n",
        "control plane contract",
    )
    text = replace_once(
        text,
        "  state_integrity_p0: .github/workflows/novelforge-state-integrity-p0.yml\n",
        "  state_integrity_p0: .github/workflows/novelforge-state-integrity-p0.yml\n"
        "  author_steering: .github/workflows/novelforge-author-steering.yml\n",
        "workflow discovery",
    )
    text = replace_once(
        text,
        "state-integrity-cross-contract-self-test, settlement-runtime-self-test",
        "state-integrity-cross-contract-self-test, author-steering-self-test, settlement-runtime-self-test",
        "normal CI requirement",
    )
    text = replace_once(
        text,
        "  propagation_debt_requires_explicit_dependency_evidence: true\n",
        "  propagation_debt_requires_explicit_dependency_evidence: true\n"
        "  author_steering_request_grants_canon_authority: false\n"
        "  author_steering_decision_grants_canon_authority: false\n"
        "  author_steering_grants_project_write_authority: false\n"
        "  author_steering_grants_framework_write_authority: false\n"
        "  author_steering_grants_settlement_authority: false\n"
        "  author_steering_followup_ops_auto_execute: false\n"
        "  author_steering_consequential_write_interruptible: false\n",
        "write boundary",
    )
    HARNESS.write_text(text, encoding="utf-8")

    wf = WORKFLOW.read_text(encoding="utf-8")
    wf = replace_once(
        wf,
        "on:\n  pull_request:\n    branches: [main]\n",
        "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n",
        "main push trigger",
    )
    WORKFLOW.write_text(wf, encoding="utf-8")

    checks = [
        ["python", "-m", "py_compile", "harness/control_plane/author_steering.py"],
        ["python", "-m", "json.tool", "harness/control_plane/author_steering.schema.json"],
        ["python", "harness/control_plane/author_steering.py", "self-test", "--path", "/tmp/novelforge-author-steering-migrate.db"],
        ["python", "scripts/version_identity.py"],
        ["python", "scripts/docs_quality.py"],
    ]
    for cmd in checks:
        subprocess.run(cmd, cwd=ROOT, check=True)

    print("HARNESS_AFTER_BLOB=" + git_blob_sha(HARNESS))
    print("WORKFLOW_AFTER_BLOB=" + git_blob_sha(WORKFLOW))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
