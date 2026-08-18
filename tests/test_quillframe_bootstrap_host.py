from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import project_sdk


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "harness" / "integrations" / "claude_hook.py"


class BootstrapHostTests(unittest.TestCase):
    def test_root_claude_imports_real_quillframe_contracts(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.en.md", text)
        self.assertIn("@SKILL.md", text)
        self.assertIn("@CLAUDE.en.md", text)
        self.assertIn("@harness/HARNESS_AGENT.en.md", text)
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Skill", settings["permissions"]["deny"])

    def test_console_entrypoint_is_declared(self):
        with (ROOT / "pyproject.toml").open("rb") as fh:
            pyproject = tomllib.load(fh)
        self.assertEqual(pyproject["project"]["scripts"]["quillframe"], "quillframe.cli:main")

    def test_framework_bundle_covers_public_runtime_entry(self):
        from release.build_framework_bundle import content_manifest

        paths = {row["path"] for row in content_manifest(ROOT)["files"]}
        self.assertIn("quillframe/cli.py", paths)
        self.assertIn("quillframe/api.py", paths)
        self.assertIn("pyproject.toml", paths)
        self.assertIn("VERSION", paths)

    def test_init_rejects_project_inside_framework_checkout(self):
        with self.assertRaisesRegex(ValueError, "outside the generic Quillframe Framework checkout"):
            project_sdk.init_project(
                ROOT / "fiction-project-must-not-live-here",
                "PROJECT-BAD-LOCATION",
                "Bad Location",
                "en",
                project_sdk.DEFAULT_FRAMEWORK_VERSION,
                False,
                ROOT,
            )

    def test_init_writes_exact_lock_attestation_and_claude_host(self):
        with tempfile.TemporaryDirectory(prefix="qf-bootstrap-test-") as td:
            project = Path(td) / "novel"
            result = project_sdk.init_project(
                project,
                "PROJECT-BOOTSTRAP-TEST",
                "Bootstrap Test",
                "zh-CN",
                project_sdk.DEFAULT_FRAMEWORK_VERSION,
                False,
                ROOT,
            )
            self.assertTrue(result["authority_ready"])
            lock_path = project / "quillframe.lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            attestation = json.loads((project / "framework.attestation.json").read_text(encoding="utf-8"))
            framework = lock["framework"]
            self.assertRegex(framework["commit"], r"^[0-9a-f]{40,64}$")
            self.assertRegex(framework["bundle_fingerprint"], r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(attestation["framework"], framework)
            settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertIn("SessionStart", settings["hooks"])
            self.assertIn("PreToolUse", settings["hooks"])
            self.assertIn("Skill", settings["permissions"]["ask"])
            self.assertTrue(project_sdk.validate_project(project)["authority_ready"])

            lock["framework"]["commit"] = None
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            legacy = project_sdk.validate_project(project)
            self.assertTrue(legacy["valid"])
            self.assertFalse(legacy["authority_ready"])
            with self.assertRaisesRegex(ValueError, "exact Framework authority is not ready"):
                project_sdk.build_project(project)

    def test_attestation_mismatch_is_not_authority_ready(self):
        with tempfile.TemporaryDirectory(prefix="qf-attestation-test-") as td:
            project = Path(td)
            for rel in project_sdk.REQUIRED_DIRS:
                (project / rel).mkdir(parents=True, exist_ok=True)
            (project / "quillframe.toml").write_text(
                project_sdk.framework_toml("PROJECT-X", "X", "en", "0.9.0"), encoding="utf-8"
            )
            framework = {
                "name": "Quillframe",
                "version": "0.9.0",
                "commit": "a" * 40,
                "bundle_fingerprint": "sha256:" + "b" * 64,
            }
            lock = {
                "schema": project_sdk.LOCK_SCHEMA,
                "framework": framework,
                "project_schema_version": "1",
            }
            (project / "quillframe.lock.json").write_text(json.dumps(lock), encoding="utf-8")
            bad = dict(framework)
            bad["commit"] = "c" * 40
            (project / "framework.attestation.json").write_text(
                json.dumps({"schema": project_sdk.ATTESTATION_SCHEMA, "framework": bad}), encoding="utf-8"
            )
            status = project_sdk.project_authority_status(project)
            self.assertFalse(status["authority_ready"])
            self.assertTrue(any("mismatch: commit" in item for item in status["errors"]))

    def test_malformed_explicit_fingerprint_is_structural_error(self):
        with tempfile.TemporaryDirectory(prefix="qf-malformed-lock-test-") as td:
            project = Path(td)
            for rel in project_sdk.REQUIRED_DIRS:
                (project / rel).mkdir(parents=True, exist_ok=True)
            (project / "quillframe.toml").write_text(
                project_sdk.framework_toml("PROJECT-X", "X", "en", "0.9.0"), encoding="utf-8"
            )
            lock = {
                "schema": project_sdk.LOCK_SCHEMA,
                "framework": {
                    "name": "Quillframe",
                    "version": "0.9.0",
                    "commit": "a" * 40,
                    "bundle_fingerprint": "not-a-fingerprint",
                },
                "project_schema_version": "1",
            }
            (project / "quillframe.lock.json").write_text(json.dumps(lock), encoding="utf-8")
            validation = project_sdk.validate_project(project)
            self.assertFalse(validation["valid"])
            self.assertTrue(any("bundle_fingerprint" in item for item in validation["errors"]))

    def _run_hook(self, event: dict) -> dict:
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def test_framework_session_start_identifies_generic_framework_before_first_prompt(self):
        session = "framework-bootstrap-host-test-session"
        start = self._run_hook({
            "session_id": session,
            "cwd": str(ROOT),
            "hook_event_name": "SessionStart",
            "source": "startup",
            "model": "test-model",
        })
        context = start["hookSpecificOutput"]["additionalContext"]
        self.assertIn("scope=GENERIC_FRAMEWORK", context)
        self.assertIn("not a fiction Project", context)
        self.assertIn("create a separate consumer Project", context)

        skill = self._run_hook({
            "session_id": session,
            "cwd": str(ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_use_id": "framework-skill",
            "tool_input": {"skill": "superpowers:brainstorming"},
            "permission_mode": "bypassPermissions",
        })
        self.assertEqual(skill["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_claude_project_bootstrap_and_stale_authority_guard(self):
        with tempfile.TemporaryDirectory(prefix="qf-hook-test-") as td:
            project = Path(td) / "novel"
            project_sdk.init_project(
                project,
                "PROJECT-HOOK-TEST",
                "Hook Test",
                "en",
                project_sdk.DEFAULT_FRAMEWORK_VERSION,
                False,
                ROOT,
            )
            session = "bootstrap-host-test-session"
            start = self._run_hook({
                "session_id": session,
                "cwd": str(project),
                "hook_event_name": "SessionStart",
                "source": "startup",
                "model": "test-model",
            })
            context = start["hookSpecificOutput"]["additionalContext"]
            self.assertIn("VERIFIED", context)
            self.assertIn("PROJECT-HOOK-TEST", context)

            skill = self._run_hook({
                "session_id": session,
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": "Skill",
                "tool_use_id": "tool-skill",
                "tool_input": {"skill": "superpowers:brainstorming"},
                "permission_mode": "bypassPermissions",
            })
            self.assertEqual(skill["hookSpecificOutput"]["permissionDecision"], "deny")

            lock_path = project / "quillframe.lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["framework"]["commit"] = "0" * 40
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            denied = self._run_hook({
                "session_id": session,
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_use_id": "tool-write",
                "tool_input": {"file_path": str(project / "plans" / "book" / "x.md")},
                "permission_mode": "bypassPermissions",
            })
            self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertIn("lock changed", denied["hookSpecificOutput"]["permissionDecisionReason"].lower())


if __name__ == "__main__":
    unittest.main()
