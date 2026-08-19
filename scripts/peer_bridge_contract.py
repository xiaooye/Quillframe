#!/usr/bin/env python3
"""Deterministic ownership contract for the project-hosted peer semantic bridge."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/quillframe-chat-semantic-bridge.yml"
ACTION = ROOT / ".github/actions/project-peer-semantic/action.yml"
BRIDGE = ROOT / ".github/actions/project-peer-semantic/bridge.py"


def main() -> int:
    errors: list[str] = []
    for path in (WORKFLOW, ACTION, BRIDGE):
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
    if errors:
        print(json.dumps({"peer_bridge_contract": "FAIL", "errors": errors}, indent=2))
        return 1

    workflow = WORKFLOW.read_text(encoding="utf-8")
    action = ACTION.read_text(encoding="utf-8")
    bridge = BRIDGE.read_text(encoding="utf-8")

    if "workflow_call:" not in workflow:
        errors.append("peer bridge workflow must be reusable via workflow_call")
    if "types: [opened]" in workflow or "issues:\n" in workflow or "issue_comment:\n" in workflow:
        errors.append("Framework peer bridge must not listen to Framework issue events")
    if "@${{ inputs.framework-ref }}" in workflow:
        errors.append("reusable workflow may not use an expression in a step uses ref")
    required_exact_checkout = [
        "repository: ${{ github.repository }}",
        "ref: ${{ github.sha }}",
        "path: .quillframe-project",
        "persist-credentials: false",
        "uses: actions/download-artifact@v4",
        "name: ${{ inputs.frozen-packet-artifact }}",
        "path: .quillframe-frozen-packet",
        "repository: xiaooye/Quillframe",
        "ref: ${{ inputs.framework-ref }}",
        "path: .quillframe-framework",
        "EXPECTED_FRAMEWORK_COMMIT: ${{ inputs.framework-ref }}",
        "QUILLFRAME_ACTION_REF: ${{ steps.framework.outputs.commit }}",
        "QUILLFRAME_ACTION_REPOSITORY: xiaooye/Quillframe",
        "QUILLFRAME_PROJECT_CHECKOUT: ${{ github.workspace }}/.quillframe-project",
        "QUILLFRAME_FROZEN_PACKET_CHECKOUT: ${{ github.workspace }}/.quillframe-frozen-packet",
        "QUILLFRAME_PROJECT_ROOT: ${{ inputs.project-root }}",
        "QUILLFRAME_FROZEN_PACKET: ${{ inputs.frozen-packet }}",
        "QUILLFRAME_FROZEN_PACKET_SHA256: ${{ inputs.frozen-packet-sha256 }}",
        ".quillframe-framework/.github/actions/project-peer-semantic/bridge.py",
        ".quillframe-framework/.github/actions/project-peer-semantic/auto_review.py",
    ]
    for needle in required_exact_checkout:
        if needle not in workflow:
            errors.append(f"reusable workflow exact-checkout guard missing: {needle}")
    if "github.action_ref" not in action or "github.action_repository" not in action:
        errors.append("composite action must expose actual action ref/repository to deterministic binding")

    required_bridge_guards = [
        "caller_repo == action_repo",
        "locked_commit != action_ref",
        '"project_repo": binding["caller_repo"]',
        '"framework_repo": binding["framework_repo"]',
        '"framework_commit": binding["framework_commit"]',
        "only repository owner may trigger the default peer bridge",
    ]
    for needle in required_bridge_guards:
        if needle not in bridge:
            errors.append(f"bridge guard missing: {needle}")

    result = {
        "peer_bridge_contract": "PASS" if not errors else "FAIL",
        "project_hosted_runtime": not errors,
        "framework_issue_listener": False,
        "exact_lock_binding": not errors,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
