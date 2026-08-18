from __future__ import annotations

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import project_sdk
from harness.integrations import host_bootstrap, host_scaffold
from harness.session_runtime import session_runtime


ROOT = Path(__file__).resolve().parents[1]


class UnifiedHostBootstrapTests(unittest.TestCase):
    def test_root_agents_is_direct_codex_safe_bootstrap(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Generic Quillframe Framework", text)
        self.assertIn("QF_SESSION_ID", text)
        self.assertIn("host-run begin", text)
        self.assertIn("SYSTEM-IMPROVE", text)
        self.assertNotIn("AGENTS Bootstrap Router", text)

    def test_framework_codex_hook_file_covers_lifecycle_and_edits(self):
        hooks = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("SessionStart", hooks["hooks"])
        self.assertIn("UserPromptSubmit", hooks["hooks"])
        self.assertIn("PreToolUse", hooks["hooks"])
        matcher = hooks["hooks"]["PreToolUse"][0]["matcher"]
        self.assertIn("apply_patch", matcher)
        self.assertIn("Bash", matcher)

    def test_framework_host_uses_typed_session_and_requires_mode_run(self):
        native = "test-codex-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="qf-host-db-") as td, patch.dict(
            os.environ, {"QUILLFRAME_DB": str(Path(td) / "runtime.db")}
        ):
            snapshot = host_bootstrap.build_snapshot("codex", native, None, full_authority_refresh=True)
            self.assertEqual(snapshot["state"], "awaiting_task_mode")
            self.assertEqual(snapshot["primary_task_mode"], "UNRESOLVED")
            cp = host_bootstrap.control_plane(None)
            stored = cp.get_session(snapshot["session_id"])
            self.assertIsNotNone(stored)
            self.assertEqual(session_runtime.validate(stored["session"]), [])
            self.assertEqual(stored["session"]["schema"], session_runtime.SCHEMA)

            denied, _ = host_bootstrap.pretool_decision(
                snapshot,
                {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch"}},
            )
            self.assertEqual(denied, "deny")

            begin_command = (
                "python -m quillframe.cli host-run begin "
                f"--session-id {snapshot['session_id']} --mode SYSTEM-IMPROVE"
            )
            decision, reason = host_bootstrap.pretool_decision(
                snapshot,
                {"tool_name": "Bash", "tool_input": {"command": begin_command}, "cwd": str(ROOT)},
            )
            self.assertIsNone(decision, reason)
            lookalike, _ = host_bootstrap.pretool_decision(
                snapshot,
                {"tool_name": "Bash", "tool_input": {"command": begin_command + "; rm -rf /tmp/nope"}, "cwd": str(ROOT)},
            )
            self.assertEqual(lookalike, "deny")

            started = host_bootstrap.begin_run(None, snapshot["session_id"], "SYSTEM-IMPROVE")
            self.assertEqual(started["state"], "running")
            running = host_bootstrap.build_snapshot("codex", native, None, full_authority_refresh=False)
            self.assertEqual(running["state"], "running")
            self.assertEqual(running["primary_task_mode"], "SYSTEM-IMPROVE")
            self.assertEqual(running["active_run_id"], started["run_id"])
            decision, reason = host_bootstrap.pretool_decision(
                running,
                {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch"}},
            )
            self.assertIsNone(decision, reason)

            with self.assertRaisesRegex(ValueError, "active run/task_mode"):
                host_bootstrap.begin_run(None, snapshot["session_id"], "AUDIT")

    def test_framework_fiction_intent_can_only_escape_through_strict_project_init(self):
        native = "test-framework-init-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="qf-host-db-") as td, patch.dict(
            os.environ, {"QUILLFRAME_DB": str(Path(td) / "runtime.db")}
        ):
            snapshot = host_bootstrap.build_snapshot("claude_code", native, None, full_authority_refresh=True)
            init_command = (
                "python -m quillframe.cli init ../riverside-high "
                "--id RIVERSIDE-HIGH --title 'Riverside High' --language zh-CN"
            )
            decision, reason = host_bootstrap.pretool_decision(
                snapshot,
                {"tool_name": "Bash", "tool_input": {"command": init_command}, "cwd": str(ROOT)},
            )
            self.assertIsNone(decision, reason)
            self.assertTrue(host_bootstrap.is_project_init_command(init_command, ROOT))

            inside = "python -m quillframe.cli init fiction --id BAD --title Bad"
            self.assertFalse(host_bootstrap.is_project_init_command(inside, ROOT))
            denied_inside, _ = host_bootstrap.pretool_decision(
                snapshot,
                {"tool_name": "Bash", "tool_input": {"command": inside}, "cwd": str(ROOT)},
            )
            self.assertEqual(denied_inside, "deny")

            force = init_command + " --force"
            self.assertFalse(host_bootstrap.is_project_init_command(force, ROOT))
            denied_force, _ = host_bootstrap.pretool_decision(
                snapshot,
                {"tool_name": "Bash", "tool_input": {"command": force}, "cwd": str(ROOT)},
            )
            self.assertEqual(denied_force, "deny")

            chained = init_command + "; echo unsafe"
            self.assertFalse(host_bootstrap.is_project_init_command(chained, ROOT))

    def test_project_scaffold_adds_codex_and_preserves_unknown_agents(self):
        with tempfile.TemporaryDirectory(prefix="qf-host-scaffold-") as td:
            project = Path(td)
            (project / "quillframe.toml").write_text("[project]\nid='X'\n", encoding="utf-8")
            (project / "AGENTS.md").write_text(project_sdk.agents_md(), encoding="utf-8")
            (project / "CLAUDE.md").write_text(project_sdk.claude_md(), encoding="utf-8")
            (project / ".claude").mkdir()
            (project / ".claude" / "settings.json").write_text(project_sdk.claude_settings_json(), encoding="utf-8")

            first = host_scaffold.install_project_hosts(project)
            self.assertTrue(first["installed"])
            self.assertIn(".codex/hooks.json", first["changed"])
            agents_text = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("QF_SESSION_ID", agents_text)
            self.assertIn("never synthesize a Quillframe manuscript", agents_text)
            self.assertIn("candidate.visible.get", agents_text)
            codex = json.loads((project / ".codex" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(codex["hooks"]["PreToolUse"][0]["matcher"], "Bash|apply_patch|Edit|Write")

            second = host_scaffold.install_project_hosts(project)
            self.assertTrue(second["installed"])
            self.assertEqual(second["changed"], [])

            (project / "AGENTS.md").write_text("# Custom instructions\n", encoding="utf-8")
            third = host_scaffold.install_project_hosts(project)
            self.assertFalse(third["installed"])
            self.assertEqual(third["manual_merge_required"], ["AGENTS.md"])
            self.assertEqual((project / "AGENTS.md").read_text(encoding="utf-8"), "# Custom instructions\n")

    def test_exact_project_authority_then_mode_run_then_stale_lock_block(self):
        with tempfile.TemporaryDirectory(prefix="qf-host-project-") as td, patch.dict(
            os.environ, {"QUILLFRAME_DB": str(Path(td) / "runtime.db")}
        ):
            project = Path(td) / "novel"
            project_sdk.init_project(
                project,
                "PROJECT-HOST-V2",
                "Host V2",
                "en",
                project_sdk.DEFAULT_FRAMEWORK_VERSION,
                False,
                ROOT,
            )
            host_scaffold.install_project_hosts(project)
            native = "test-claude-" + uuid.uuid4().hex
            snapshot = host_bootstrap.build_snapshot("claude_code", native, project, full_authority_refresh=True)
            self.assertEqual(snapshot["state"], "awaiting_task_mode")
            self.assertTrue(snapshot["authority"]["materialized_authority_verified"])

            started = host_bootstrap.begin_run(project, snapshot["session_id"], "DESIGN-BOOK")
            self.assertEqual(started["task_mode"], "DESIGN-BOOK")
            running = host_bootstrap.build_snapshot("claude_code", native, project, full_authority_refresh=False)
            self.assertEqual(running["state"], "running")

            lock_path = project / "quillframe.lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["framework"]["commit"] = "0" * 40
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            blocked = host_bootstrap.build_snapshot("claude_code", native, project, full_authority_refresh=False)
            self.assertEqual(blocked["state"], "blocked")
            decision, _ = host_bootstrap.pretool_decision(
                blocked,
                {"tool_name": "Write", "tool_input": {"file_path": str(project / "plans" / "x.md")}},
            )
            self.assertEqual(decision, "deny")

    def test_invalid_framework_fiction_mode_is_rejected(self):
        native = "test-framework-mode-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="qf-host-db-") as td, patch.dict(
            os.environ, {"QUILLFRAME_DB": str(Path(td) / "runtime.db")}
        ):
            snapshot = host_bootstrap.build_snapshot("claude_code", native, None, full_authority_refresh=True)
            with self.assertRaisesRegex(ValueError, "cannot own Generic Framework writes"):
                host_bootstrap.begin_run(None, snapshot["session_id"], "DRAFT")


if __name__ == "__main__":
    unittest.main()
