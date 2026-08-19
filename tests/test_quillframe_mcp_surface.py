from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.control_plane.mcp_stdio import MCPServer, TOOLS


class McpSurfaceTests(unittest.TestCase):
    def test_tools_are_split_between_novelist_and_internal_ops(self):
        by_name = {tool["name"]: tool for tool in TOOLS}
        self.assertEqual(by_name["quillframe_project_projection_preview"]["_meta"]["surface_class"], "novelist_facing")
        self.assertEqual(by_name["quillframe_candidate_visible_get"]["_meta"]["surface_class"], "novelist_facing")
        self.assertEqual(by_name["quillframe_session_put"]["_meta"]["surface_class"], "internal_ops")
        self.assertEqual(by_name["quillframe_handoff_claim"]["_meta"]["surface_class"], "internal_ops")
        self.assertNotIn("quillframe_candidate_accept", by_name)
        self.assertNotIn("quillframe_settlement_apply", by_name)

    def test_capabilities_manifest_keeps_authority_privileged(self):
        with tempfile.TemporaryDirectory(prefix="qf-mcp-surface-") as td:
            server = MCPServer(str(Path(td) / "runtime.db"))
            server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
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


if __name__ == "__main__":
    unittest.main()
