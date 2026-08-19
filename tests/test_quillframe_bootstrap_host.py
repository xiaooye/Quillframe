from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from pathlib import Path

import project_sdk
from harness.integrations import host_bootstrap


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
        commands = [
            hook["command"]
            for groups in settings["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertTrue(commands)
        for command in commands:
            self.assertNotIn("python -m quillframe.cli", command)
            self.assertIn("framework_root.txt", command)
            self.assertIn("quillframe.toml", command)

    def test_root_codex_hook_commands_do_not_follow_ambient_git_toplevel(self):
        hooks = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for groups in hooks["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertTrue(commands)
        for command in commands:
            self.assertNotIn("git rev-parse --show-toplevel", command)
            self.assertIn("framework_root.txt", command)
            self.assertIn("quillframe.toml", command)

    def test_console_entrypoint_is_declared(self):
        with (ROOT / "pyproject.toml").open("rb") as fh:
            pyproject = tomllib.load(fh)
        self.assertEqual(pyproject["project"]["scripts"]["quillframe"], "quillframe.cli:main")

    def test_framework_bundle_covers_public_runtime_entry(self):
        from release.build_framework_bundle import content_manifest

        paths = {row["path"] for row in content_manifest(ROOT)["files"]}
        self.assertIn("quillframe/cli.py", paths)
        self.assertIn("quillframe/api.py", paths)
        self.assertIn("core_operations.py", paths)
        self.assertIn("pyproject.toml", paths)
        self.assertIn("VERSION", paths)
        self.assertIn("studio/host_bridge.py", paths)
        self.assertIn("studio/host_bridge_contract.json", paths)

    def test_unpacked_framework_bundle_runs_project_sdk_self_test(self):
        from release.build_framework_bundle import build

        with tempfile.TemporaryDirectory(prefix="qf-unpacked-bundle-test-") as td:
            root = Path(td)
            bundle = root / "framework.tar"
            build(ROOT, bundle)
            unpacked = root / "unpacked"
            unpacked.mkdir()
            with tarfile.open(bundle, "r") as archive:
                archive.extractall(unpacked)
            proc = subprocess.run(
                [sys.executable, "project_sdk.py", "self-test", "--tmp", str(root / "project-sdk-self-test")],
                cwd=unpacked,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertEqual(json.loads(proc.stdout)["project_sdk_contract"], "PASS")
            cli_self_test = subprocess.run(
                [sys.executable, "quillframe.py", "self-test"],
                cwd=unpacked,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cli_self_test.returncode, 0, cli_self_test.stderr or cli_self_test.stdout)
            self.assertEqual(json.loads(cli_self_test.stdout)["quillframe_cli_contract"], "PASS")

    def test_framework_checkout_identity_refreshes_index_before_status_check(self):
        import release.build_framework_bundle as bundle_builder

        calls: list[object] = []

        def fake_refresh(root: Path) -> None:
            calls.append(("refresh", root))

        def fake_git(root: Path, *args: str) -> str:
            calls.append(args)
            if args == ("status", "--porcelain", "--untracked-files=normal"):
                return ""
            if args == ("rev-parse", "HEAD"):
                return "a" * 40
            raise AssertionError(args)

        with (
            patch.object(project_sdk, "_framework_root", return_value=ROOT),
            patch.object(project_sdk, "_refresh_git_index", side_effect=fake_refresh),
            patch.object(project_sdk, "_git", side_effect=fake_git),
            patch.object(
                bundle_builder,
                "build",
                return_value={
                    "bundle_fingerprint": "sha256:" + "b" * 64,
                    "content_index_fingerprint": "sha256:" + "c" * 64,
                },
            ),
        ):
            identity = project_sdk.framework_checkout_identity(ROOT)

        self.assertEqual(calls[0], ("refresh", ROOT))
        self.assertIn(("status", "--porcelain", "--untracked-files=normal"), calls)
        self.assertEqual(identity["commit"], "a" * 40)
        self.assertEqual(identity["bundle_fingerprint"], "sha256:" + "b" * 64)

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

    def test_validate_project_accepts_mapped_project_without_standard_tree(self):
        with tempfile.TemporaryDirectory(prefix="qf-mapped-validate-") as td:
            project = Path(td)
            for rel in (
                "project/book",
                "project/state",
                "project/volumes/VOL-001",
                "project/characters",
                "project/profiles",
                "manuscripts/draft",
                "manuscripts/review",
                "manuscripts/accepted",
            ):
                (project / rel).mkdir(parents=True, exist_ok=True)
            (project / "project" / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
            (project / "project" / "START_HERE.md").write_text("# Start\n", encoding="utf-8")
            (project / "project" / "CONTEXT_PROTOCOL.md").write_text("# Context\n", encoding="utf-8")
            (project / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            (project / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
            (project / "quillframe.toml").write_text(
                "\n".join(
                    [
                        '[quillframe]',
                        'schema = "quillframe_project_v1"',
                        'project_schema_version = "1"',
                        'minimum_framework_version = "0.9.1"',
                        '',
                        '[project]',
                        'id = "PROJECT-MAPPED-VALIDATE"',
                        'title = "Mapped Validate"',
                        'language = "zh-CN"',
                        'version = "0.1.0"',
                        'status = "active"',
                        '',
                        '[adapter]',
                        'layout = "mapped"',
                        '',
                        '[paths]',
                        'project_entry = "project/PROJECT.md"',
                        'start_here = "project/START_HERE.md"',
                        'context_protocol = "project/CONTEXT_PROTOCOL.md"',
                        'story_bible = "project/book"',
                        'current_state = "project/state"',
                        'active_plans = "project/volumes/VOL-001"',
                        'manuscripts = "manuscripts"',
                        'profiles = "project/profiles"',
                        '',
                        '[authority]',
                        'durable_story_authority = "project_files"',
                        'runtime_projection_authority = false',
                        'review_draft_is_canon = false',
                        'acceptance_required_for_canon = true',
                        'settlement_required_for_canon = true',
                        '',
                        '[quality]',
                        'framework_surface_fundamentals = true',
                        'framework_reader_engagement = true',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            framework = {
                "name": "Quillframe",
                "version": "0.9.1",
                "commit": "a" * 40,
                "bundle_fingerprint": "sha256:" + "b" * 64,
            }
            (project / "quillframe.lock.json").write_text(
                json.dumps(
                    {
                        "schema": project_sdk.LOCK_SCHEMA,
                        "framework": framework,
                        "project_schema_version": "1",
                    }
                ),
                encoding="utf-8",
            )
            (project / "framework.attestation.json").write_text(
                json.dumps(
                    {
                        "schema": project_sdk.ATTESTATION_SCHEMA,
                        "framework": framework,
                    }
                ),
                encoding="utf-8",
            )
            validation = project_sdk.validate_project(project)
            self.assertTrue(validation["valid"], validation)
            self.assertTrue(validation["authority_ready"], validation)
            self.assertFalse(any("missing required directory: specs" in item for item in validation["errors"]), validation)
            self.assertFalse(any("README.en.md" in item for item in validation["errors"]), validation)

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

    def test_host_bootstrap_accepts_mapped_project_contract(self):
        with tempfile.TemporaryDirectory(prefix="qf-hook-mapped-") as td:
            project = Path(td)
            for rel in (
                "project/book",
                "project/state",
                "project/volumes/VOL-001",
                "project/characters",
                "project/profiles",
                "manuscripts/draft",
                "manuscripts/review",
                "manuscripts/accepted",
            ):
                (project / rel).mkdir(parents=True, exist_ok=True)
            (project / "project" / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
            (project / "project" / "START_HERE.md").write_text("# Start\n", encoding="utf-8")
            (project / "project" / "CONTEXT_PROTOCOL.md").write_text("# Context\n", encoding="utf-8")
            (project / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            (project / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
            (project / "quillframe.toml").write_text(
                "\n".join(
                    [
                        '[quillframe]',
                        'schema = "quillframe_project_v1"',
                        'project_schema_version = "1"',
                        f'minimum_framework_version = "{project_sdk.DEFAULT_FRAMEWORK_VERSION}"',
                        '',
                        '[project]',
                        'id = "PROJECT-MAPPED-HOOK"',
                        'title = "Mapped Hook"',
                        'language = "zh-CN"',
                        'version = "0.1.0"',
                        'status = "active"',
                        '',
                        '[adapter]',
                        'layout = "mapped"',
                        '',
                        '[paths]',
                        'project_entry = "project/PROJECT.md"',
                        'start_here = "project/START_HERE.md"',
                        'context_protocol = "project/CONTEXT_PROTOCOL.md"',
                        'story_bible = "project/book"',
                        'current_state = "project/state"',
                        'active_plans = "project/volumes/VOL-001"',
                        'manuscripts = "manuscripts"',
                        'profiles = "project/profiles"',
                        '',
                        '[authority]',
                        'durable_story_authority = "project_files"',
                        'runtime_projection_authority = false',
                        'review_draft_is_canon = false',
                        'acceptance_required_for_canon = true',
                        'settlement_required_for_canon = true',
                        '',
                        '[quality]',
                        'framework_surface_fundamentals = true',
                        'framework_reader_engagement = true',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            framework = {
                "name": "Quillframe",
                "version": project_sdk.DEFAULT_FRAMEWORK_VERSION,
                "commit": "a" * 40,
                "bundle_fingerprint": "sha256:" + "b" * 64,
            }
            (project / "quillframe.lock.json").write_text(
                json.dumps(
                    {
                        "schema": project_sdk.LOCK_SCHEMA,
                        "framework": framework,
                        "project_schema_version": "1",
                    }
                ),
                encoding="utf-8",
            )
            (project / "framework.attestation.json").write_text(
                json.dumps(
                    {
                        "schema": project_sdk.ATTESTATION_SCHEMA,
                        "framework": framework,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(project_sdk, "framework_checkout_identity", return_value=framework), patch.object(host_bootstrap, "project_sdk", return_value=project_sdk):
                snapshot = host_bootstrap.build_snapshot(
                    "claude_code",
                    "mapped-hook-session",
                    project,
                    full_authority_refresh=True,
                )
            context = host_bootstrap.bootstrap_context(snapshot)
            self.assertEqual(snapshot["project_id"], "PROJECT-MAPPED-HOOK")
            self.assertNotIn("BLOCKED:", context)

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
