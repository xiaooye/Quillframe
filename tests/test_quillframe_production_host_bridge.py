from __future__ import annotations

import unittest

from studio import host_bridge


class ProductionHostBridgeTests(unittest.TestCase):
    def test_v11_contract_exposes_native_dispatch_without_compatibility_aliases(self):
        contract = host_bridge.contract()
        self.assertEqual(contract["version"], "11")
        for operation in (
            "author.run.execute",
            "author.run.status",
            "author.run.resume",
            "author.run.cancel",
            "author.run.events",
            "author.run.context.refresh",
            "author.run.independent.submit",
            "author.run.independent.dispatch.prepare",
            "model.service.add",
            "model.service.discover",
            "model.service.test",
            "model.capabilities",
            "model.route.preview",
            "document.open",
            "document.revisions.list",
            "project.restore",
            "project.list",
            "document.list",
            "candidate.review.get",
            "candidate.visible.get",
            "candidate.reject",
            "candidate.revision.request",
            "settlement.preflight",
        ):
            self.assertIn(operation, contract["operations"])
        self.assertEqual(
            contract["operations"]["author.run.execute"]["required_args"],
            [
                "project_id",
                "run_id",
                "service_id",
                "instruction",
                "reader_grip",
                "rule_material",
                "independent_provenance",
            ],
        )
        self.assertFalse(contract["invariants"]["independent_review_project_peer_receipt_required"])
        self.assertTrue(contract["invariants"]["independent_review_receipt_required"])
        self.assertIs(
            contract["invariants"].get("independent_review_eligible_invocation_receipt_required"),
            True,
        )
        self.assertTrue(contract["invariants"]["independent_review_native_lifecycle_receipt_supported"])
        self.assertEqual(
            contract.get("native_independent_review", {}).get("provider_ids"),
            ["codex_native_subagent", "claude_native_subagent"],
        )
        self.assertEqual(
            contract.get("native_independent_review", {}).get("transports"),
            ["codex_native", "claude_code_native"],
        )
        self.assertFalse(contract["invariants"]["independent_review_same_runtime_substitution"])
        self.assertEqual(
            contract["operations"]["author.run.independent.submit"]["required_args"],
            ["project_id", "run_id", "peer_packet", "result", "independence_receipt"],
        )
        self.assertEqual(contract["deferred_operations"]["project.delete"]["status"], "unsupported")
        self.assertFalse(contract["secret_boundary"]["cloudflare_required"])
        self.assertTrue(contract["invariants"]["manuscript_visibility_requires_production_release"])
        self.assertFalse(contract["invariants"]["host_self_generated_manuscript_is_releaseable"])
        self.assertTrue(contract["invariants"]["ephemeral_runtime_exact_git_identity_required"])

    def test_access_token_is_redacted_from_fingerprint_but_business_authorization_is_bound(self):
        secret_a = "QF-SECRET-SENTINEL-111"
        secret_b = "QF-SECRET-SENTINEL-222"
        token_a = {
            "schema": host_bridge.REQUEST_SCHEMA,
            "bridge_version": host_bridge.BRIDGE_VERSION,
            "request_id": "same",
            "operation": "model.service.add",
            "surface": "local_app",
            "args": {"endpoint": "https://example.invalid/v1", "access_token": secret_a},
            "authority": False,
        }
        token_b = {**token_a, "args": {"endpoint": "https://example.invalid/v1", "access_token": secret_b}}
        result_a = host_bridge.invoke(token_a)
        result_b = host_bridge.invoke(token_b)
        self.assertEqual(result_a["request_fingerprint"], result_b["request_fingerprint"])
        self.assertNotIn(secret_a, str(result_a))
        self.assertNotIn(secret_b, str(result_b))
        self.assertFalse(result_a["secret_values_persisted"])

        auth_a = {
            "schema": host_bridge.REQUEST_SCHEMA,
            "bridge_version": host_bridge.BRIDGE_VERSION,
            "request_id": "auth",
            "operation": "candidate.accept",
            "surface": "local_app",
            "args": {
                "project_id": "MISSING",
                "candidate_id": "C",
                "candidate_fingerprint": "sha256:x",
                "authorized_by": "user",
                "authorization": {"source": "studio", "explicit_action": "accept", "reason": "approve-a"},
                "idempotency_key": "k",
                "user_authorized": True,
            },
            "authority": False,
        }
        auth_b = {**auth_a, "args": {**auth_a["args"], "authorization": {"source": "studio", "explicit_action": "accept", "reason": "approve-b"}}}
        accepted_a = host_bridge.invoke(auth_a)
        accepted_b = host_bridge.invoke(auth_b)
        self.assertNotEqual(accepted_a["request_fingerprint"], accepted_b["request_fingerprint"])

    def test_core_q1_invalid_authorization_secret_is_not_echoed_by_bridge(self):
        secret = "Bearer Q1-BRIDGE-AUTH-SENTINEL"
        request = {
            "schema": host_bridge.REQUEST_SCHEMA,
            "bridge_version": host_bridge.BRIDGE_VERSION,
            "request_id": "q1-bridge-invalid-auth",
            "operation": "candidate.reject",
            "surface": "local_app",
            "args": {
                "project_id": "MISSING",
                "candidate_id": "C",
                "candidate_fingerprint": "sha256:x",
                "authorized_by": "user",
                "authorization": {"intent": "reject", "reason": secret},
                "idempotency_key": "q1-bridge-invalid-auth",
                "user_authorized": True,
            },
            "authority": False,
        }
        result = host_bridge.invoke(request)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "invalid_authorization")
        self.assertNotIn(secret, str(result))
        self.assertFalse(result["secret_values_persisted"])

    def test_secret_value_is_scrubbed_from_nested_data_and_exception_text(self):
        secret = "QF-SECRET-EXCEPTION-SENTINEL"
        req = {
            "schema": host_bridge.REQUEST_SCHEMA,
            "bridge_version": host_bridge.BRIDGE_VERSION,
            "request_id": "secret-error",
            "operation": "model.service.add",
            "surface": "local_app",
            "args": {"endpoint": "https://example.invalid/v1", "access_token": secret},
            "authority": False,
        }
        out = host_bridge.result(
            req,
            "failed",
            data={"diagnostic": f"provider echoed {secret}"},
            error={"code": "fixture", "message": f"request rejected credential {secret}"},
        )
        serialized = str(out)
        self.assertNotIn(secret, serialized)
        self.assertIn("<redacted>", serialized)
        self.assertEqual(out["operation"], "model.service.add")
        self.assertFalse(out["secret_values_persisted"])

    def test_production_and_secret_operations_are_not_agent_package_operations(self):
        cases = (
            ("model.service.add", {"endpoint": "https://example.invalid/v1", "access_token": "secret"}),
            ("model.service.token.replace", {"service_id": "s", "access_token": "secret"}),
            (
                "author.run.execute",
                {
                    "project_id": "p",
                    "run_id": "r",
                    "service_id": "s",
                    "instruction": "x",
                    "reader_grip": "very_high",
                    "rule_material": [{"id": "R", "authority": "framework", "statement": "x"}],
                    "independent_provenance": {
                        "project_id": "p",
                        "project_repo": "owner/project",
                        "framework_repo": "owner/framework",
                        "framework_commit": "f" * 40,
                    },
                },
            ),
            (
                "author.run.independent.submit",
                {"project_id": "p", "run_id": "r", "peer_packet": {}, "result": {}, "independence_receipt": {}},
            ),
        )
        for operation, args in cases:
            out = host_bridge.invoke(
                {
                    "schema": host_bridge.REQUEST_SCHEMA,
                    "bridge_version": host_bridge.BRIDGE_VERSION,
                    "request_id": operation,
                    "operation": operation,
                    "surface": "agent_package",
                    "args": args,
                    "authority": False,
                }
            )
            self.assertEqual(out["status"], "invalid")
            self.assertIn("not authorized", " ".join(out["error"]["messages"]))


    def test_host_cannot_fabricate_production_runtime_provenance(self):
        out = host_bridge.invoke({
            "schema": host_bridge.REQUEST_SCHEMA,
            "bridge_version": host_bridge.BRIDGE_VERSION,
            "request_id": "reserved-production-source",
            "operation": "document.revision.save",
            "surface": "local_app",
            "args": {
                "project_id": "missing",
                "document_id": "missing",
                "content": "host-authored substitute",
                "source": "production_runtime",
            },
            "authority": False,
        })
        self.assertEqual(out["status"], "failed")
        self.assertEqual(out["error"]["code"], "reserved_provenance")

    def test_self_test_passes_without_live_network(self):
        report = host_bridge.self_test()
        self.assertEqual(report["quillframe_host_bridge_contract"], "PASS")
        self.assertEqual(report["contract_version"], "11")
        self.assertTrue(report["secret_value_fingerprint_independent"])


if __name__ == "__main__":
    unittest.main()
