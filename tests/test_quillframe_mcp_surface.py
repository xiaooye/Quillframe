from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.control_plane import mcp_stdio
from harness.control_plane.mcp_stdio import MCPServer, TOOLS


class McpSurfaceTests(unittest.TestCase):
    def test_tools_are_split_between_novelist_and_internal_ops(self):
        by_name = {tool["name"]: tool for tool in TOOLS}
        self.assertEqual(by_name["quillframe_candidate_visible_get"]["_meta"]["surface_class"], "novelist_facing")
        self.assertEqual(by_name["quillframe_session_put"]["_meta"]["surface_class"], "internal_ops")
        self.assertEqual(by_name["quillframe_handoff_claim"]["_meta"]["surface_class"], "internal_ops")
        self.assertNotIn("quillframe_candidate_accept", by_name)
        self.assertNotIn("quillframe_settlement_apply", by_name)

    def test_capabilities_manifest_keeps_authority_privileged(self):
        with tempfile.TemporaryDirectory(prefix="qf-mcp-surface-") as td:
            server = MCPServer(str(Path(td) / "runtime.db"))
            server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2026-07-28"}})
            server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
            response = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "quillframe_capabilities", "arguments": {}}})
            manifest = response["result"]["structuredContent"]
            self.assertEqual(manifest["product_boundary"], "host_runs_agent_quillframe_governs_novel")
            self.assertIn("candidate.visible.get", manifest["surface_classes"]["novelist_facing"])
            self.assertIn("candidate.accept", manifest["surface_classes"]["privileged_author"])
            self.assertIn("settlement.apply", manifest["surface_classes"]["privileged_author"])
            self.assertFalse(manifest["authority"])
            self.assertFalse(manifest["canon_authority"])
            self.assertFalse(manifest["settlement_authority"])

    def test_uninitialized_server_does_not_expose_tools_or_call(self):
        with tempfile.TemporaryDirectory(prefix="qf-mcp-surface-") as td:
            server = MCPServer(str(Path(td) / "runtime.db"))
            response = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            self.assertEqual(response["error"]["code"], -32002)

    def test_agent_mcp_review_projection_never_returns_manuscript_or_reconstructable_diff(self):
        raw_review = {
            "schema": "quillframe_candidate_review_projection_v1",
            "candidate": {"candidate_id": "C", "candidate_fingerprint": "sha256:" + "a" * 64},
            "candidate_revision": {
                "revision_id": "REV-C",
                "content": "private candidate manuscript",
                "content_fingerprint": "sha256:" + "a" * 64,
                "authority_class": "review",
            },
            "incumbent_revision": {
                "revision_id": "REV-I",
                "content": "private incumbent manuscript",
                "content_fingerprint": "sha256:" + "b" * 64,
                "authority_class": "accepted",
            },
            "diff": {"diff": ["-private incumbent manuscript", "+private candidate manuscript"]},
            "future_candidate_content": "future top-level manuscript leak",
            "evidence": {"independent": {"result": "pass"}},
            "private_reasoning_exposed": False,
            "authority": False,
            "canon_authority": False,
            "settlement_authority": False,
        }
        with tempfile.TemporaryDirectory(prefix="qf-mcp-review-visibility-") as td, patch.object(
            mcp_stdio.CoreOperations,
            "candidate_review_get",
            return_value=raw_review,
        ):
            server = MCPServer(str(Path(td) / "runtime.db"))
            result = server.call_tool(
                "quillframe_candidate_review_get",
                {"project_id": "P", "candidate_id": "C"},
            )

        serialized = str(result)
        self.assertNotIn("private candidate manuscript", serialized)
        self.assertNotIn("private incumbent manuscript", serialized)
        self.assertNotIn("future top-level manuscript leak", serialized)
        self.assertNotIn("future_candidate_content", result)
        self.assertNotIn("content", result["candidate_revision"])
        self.assertNotIn("content", result["incumbent_revision"])
        self.assertNotIn("diff", result)
        self.assertEqual(result["manuscript_access"], "candidate.visible.get_only")

    def test_agent_mcp_reject_and_revision_require_explicit_user_authorization(self):
        by_name = {tool["name"]: tool for tool in TOOLS}
        for name in ("quillframe_candidate_reject", "quillframe_candidate_revision_request"):
            schema = by_name[name]["inputSchema"]
            self.assertIn("user_authorized", schema["required"])
            self.assertEqual(schema["properties"]["user_authorized"], {"const": True})

        with tempfile.TemporaryDirectory(prefix="qf-mcp-authority-") as td, patch.object(
            mcp_stdio.CoreOperations,
            "reject_candidate",
        ) as reject, patch.object(
            mcp_stdio.CoreOperations,
            "request_candidate_revision",
        ) as revision:
            server = MCPServer(str(Path(td) / "runtime.db"))
            common = {
                "project_id": "P",
                "candidate_id": "C",
                "candidate_fingerprint": "sha256:" + "a" * 64,
                "authorized_by": "agent",
                "authorization": {"source": "agent self-assertion"},
                "idempotency_key": "IDEMPOTENT",
            }
            for name, args in (
                ("quillframe_candidate_reject", common),
                ("quillframe_candidate_reject", {**common, "user_authorized": False}),
                (
                    "quillframe_candidate_revision_request",
                    {**common, "revision_request": {"instruction": "change it"}},
                ),
                (
                    "quillframe_candidate_revision_request",
                    {**common, "revision_request": {"instruction": "change it"}, "user_authorized": False},
                ),
            ):
                with self.subTest(name=name, explicit=args.get("user_authorized")):
                    with self.assertRaisesRegex(ValueError, "explicit user action"):
                        server.call_tool(name, args)
            reject.assert_not_called()
            revision.assert_not_called()


if __name__ == "__main__":
    unittest.main()
