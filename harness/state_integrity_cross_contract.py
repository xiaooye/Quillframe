#!/usr/bin/env python3
"""Cross-contract regression for Runtime authorization vs Project property authority.

A valid operational Runtime authorization can permit a runtime-session mutation,
but it never becomes Project/story-property write authority. Property ownership
continues to be resolved by the Project property-write policy and Settlement.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION_RUNTIME = ROOT / "harness" / "session_runtime"
for path in (ROOT, ROOT / "harness", SESSION_RUNTIME):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import property_write_policy as property_policy  # noqa: E402
import runtime_command_authorization as runtime_authorization  # noqa: E402


def main() -> int:
    policy = property_policy.normalize_policy({
        "schema": property_policy.POLICY_SCHEMA,
        "default": {"mutation_class": "proposal_only"},
        "object_types": {
            "CHAR": {
                "default": {"mutation_class": "settlement_only"},
                "properties": {
                    "display_name": {"mutation_class": "user_declared"},
                },
            }
        },
    })

    with tempfile.TemporaryDirectory(prefix="quillframe-property-runtime-cross-") as tmp:
        root = Path(tmp)
        _, preflight, command = runtime_authorization.fixture(root=root, status="idle")
        authorization = runtime_authorization.make_authorization(
            command=command,
            preflight=preflight,
            project_root=root,
            decision="allow",
            source_kind="user",
            evidence_ref="urn:quillframe:self-test:runtime-authorization",
            authorization_id="AUTH-PROPERTY-CROSS",
        )
        authorization_result = runtime_authorization.validate(authorization, command, preflight, root)

        runtime_story_write = property_policy.evaluate(policy, "CHAR", "current_location", "runtime")
        semantic_story_write = property_policy.evaluate(policy, "CHAR", "current_location", "semantic_worker")
        user_story_write = property_policy.evaluate(policy, "CHAR", "current_location", "user")
        settlement_story_write = property_policy.evaluate(policy, "CHAR", "current_location", "settlement")

        checks = {
            "runtime_authorization_is_valid_and_granted": (
                authorization_result["valid"] is True
                and authorization_result["authorization_granted"] is True
            ),
            "runtime_authorization_scope_excludes_project_write": (
                authorization["scope"]["runtime_state_mutation"] is True
                and authorization["scope"]["project_write"] is False
                and authorization["scope"]["canon_write"] is False
                and authorization["scope"]["settlement"] is False
                and authorization_result["project_write_authority"] is False
                and authorization_result["canon_authority"] is False
                and authorization_result["settlement_authority"] is False
            ),
            "runtime_writer_cannot_bypass_settlement_only_property": (
                runtime_story_write["decision"] == "deny"
                and runtime_story_write["direct_write_allowed"] is False
                and "settlement_writer_required" in runtime_story_write["requirements"]
            ),
            "semantic_worker_still_routes_to_proposal": (
                semantic_story_write["decision"] == "proposal_required"
                and semantic_story_write["direct_write_allowed"] is False
            ),
            "explicit_user_instruction_still_requires_settlement_route": (
                user_story_write["decision"] == "settlement_required"
                and user_story_write["direct_write_allowed"] is False
            ),
            "only_settlement_writer_gets_guarded_direct_route": (
                settlement_story_write["decision"] == "allow_direct"
                and settlement_story_write["direct_write_allowed"] is True
                and {"accepted_evidence", "expected_before", "settlement_receipt"}.issubset(
                    set(settlement_story_write["requirements"])
                )
            ),
        }
        ok = all(checks.values())
        print(json.dumps({
            "schema": "quillframe_state_integrity_cross_contract_v1",
            "contract": "PASS" if ok else "FAIL",
            "checks": checks,
            "runtime_authorization_authority": False,
            "property_write_route_authority_is_separate": True,
            "canon_authority": False,
            "framework_write_authority": False,
            "model_execution": False,
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
