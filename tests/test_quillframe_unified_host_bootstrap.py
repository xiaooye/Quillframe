from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import project_sdk
from harness.integrations import host_bootstrap, host_scaffold
from harness.session_runtime import session_runtime


ROOT = Path(__file__).resolve().parents[1]


def native_packet() -> dict:
    from harness.semantic_workers.semantic_worker_router import fingerprint_for

    job = {
        "job_id": "SEM-NATIVE-HOOK",
        "subject_id": "DOC-NATIVE",
        "kind": "external_review",
        "created_at": "fixture",
        "input_fingerprint": "",
        "input": {"candidate": "secret frozen candidate"},
        "rubric": ["judge the frozen candidate"],
        "output_contract": {"type": "object"},
        "permissions": {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False},
        "provenance": {"source": "fixture"},
    }
    job["input_fingerprint"] = fingerprint_for(job)
    return {
        "schema": "quillframe_peer_review_packet_v1",
        "relay_nonce": "native-frozen-nonce",
        "input_fingerprint": job["input_fingerprint"],
        "job": job,
        "reviewer_instruction": "Judge only this frozen packet.",
        "return_binding": {
            "run_reference": "native-frozen-nonce",
            "fresh_conversation_required": True,
            "same_project_writer_chat_forbidden": True,
        },
    }


class FakeNativeRuntime:
    def __init__(self) -> None:
        self.claim_calls: list[dict] = []
        self.complete_calls: list[dict] = []
        self.fail_calls: list[dict] = []

    def claim_independent_dispatch(self, project_id: str, **kwargs):
        self.claim_calls.append({"project_id": project_id, **kwargs})
        if len(self.claim_calls) != 1:
            raise RuntimeError("pending lease already claimed")
        return {
            "lease_id": "lease-native-hook",
            "project_id": project_id,
            "run_id": "RUN-NATIVE-HOOK",
            "provider": kwargs["provider"],
            "parent_session_id": kwargs["parent_session_id"],
            "reviewer_session_id": "ses-review-native-hook",
            "host_agent_id": kwargs["host_agent_id"],
            "host_invocation_id": kwargs["host_invocation_id"],
            "peer_packet": native_packet(),
            "packet_bytes": json.dumps(native_packet(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        }

    def complete_independent_dispatch(self, project_id: str, **kwargs):
        self.complete_calls.append({"project_id": project_id, **kwargs})
        return {"status": "completed", "candidate": {"content": "must not reach parent hook output"}}

    def fail_independent_dispatch(self, project_id: str, **kwargs):
        self.fail_calls.append({"project_id": project_id, **kwargs})
        return {"status": "infrastructure_failed"}


class UnifiedHostBootstrapTests(unittest.TestCase):
    def _hook_commands(self, config_path: Path) -> list[str]:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        return [
            hook["command"]
            for groups in config["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]

    def test_framework_hooks_are_safe_from_an_unrelated_git_cwd(self):
        codex_commands = self._hook_commands(ROOT / ".codex/hooks.json")
        claude_commands = self._hook_commands(ROOT / ".claude/settings.json")
        self.assertTrue(codex_commands)
        self.assertTrue(claude_commands)
        event = json.dumps(
            {
                "session_id": "unrelated-cwd-session",
                "cwd": str(ROOT),
                "hook_event_name": "SessionStart",
                "source": "startup",
            }
        )
        with tempfile.TemporaryDirectory(prefix="qf-unrelated-hook-cwd-") as td:
            subprocess.run(["git", "init", "--quiet", td], check=True)
            for command in (codex_commands[0], claude_commands[0]):
                proc = subprocess.run(
                    command,
                    shell=True,
                    cwd=td,
                    input=event,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                payload = json.loads(proc.stdout)
                self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
                self.assertIn("authority", payload["hookSpecificOutput"]["additionalContext"].lower())

    def test_project_init_hooks_run_without_installed_quillframe_command(self):
        identity = {
            "name": "Quillframe",
            "version": project_sdk.DEFAULT_FRAMEWORK_VERSION,
            "commit": "a" * 40,
            "bundle_fingerprint": "sha256:" + "b" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="qf-project-hook-run-") as td, patch.object(
            project_sdk, "framework_checkout_identity", return_value=identity
        ):
            project = Path(td) / "project"
            project_sdk.init_project(
                project,
                "PROJECT-HOOK-RUN",
                "Hook Run",
                "en",
                project_sdk.DEFAULT_FRAMEWORK_VERSION,
                False,
                ROOT,
            )
            settings = json.loads((project / ".claude/settings.json").read_text(encoding="utf-8"))
            command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            self.assertIn("framework_root.txt", command)
            self.assertIn("quillframe.toml", command)
            event = json.dumps(
                {
                    "session_id": "project-hook-session",
                    "cwd": str(project),
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                }
            )
            proc = subprocess.run(
                command,
                shell=True,
                cwd=project,
                input=event,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("PROJECT-HOOK-RUN", payload["hookSpecificOutput"]["additionalContext"])

    def test_framework_claude_hooks_do_not_depend_on_project_dir_environment(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for groups in settings["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertTrue(commands)
        self.assertEqual(len(set(commands)), 1)
        command = commands[0]
        self.assertNotIn("python -m quillframe.cli", command)
        self.assertIn("framework_root.txt", command)
        self.assertIn("quillframe.toml", command)
        self.assertIn("SubagentStart", settings["hooks"])
        self.assertIn("SubagentStop", settings["hooks"])
        self.assertIn(".*", [group["matcher"] for group in settings["hooks"]["PreToolUse"]])

    def test_native_reviewer_hooks_use_trusted_host_variants_and_hide_stop_result(self):
        self.assertTrue(hasattr(host_bootstrap, "native_reviewer_hook"))
        cases = (
            (
                "claude_code",
                {
                    "session_id": "claude-parent-native",
                    "agent_id": "claude-agent-native",
                    "agent_type": "quillframe-independent-reviewer",
                    "prompt": "lease_id=forged-from-prompt",
                },
                {"last_assistant_message": json.dumps({"confidence": 1.0, "result": "pass"})},
                "claude-agent-native",
                "claude-agent-native",
            ),
            (
                "codex",
                {
                    "parent_session_id": "codex-parent-native",
                    "subagent_id": "codex-agent-native",
                    "subagent_type": "quillframe-independent-reviewer",
                    "invocation_id": "codex-invocation-native",
                    "prompt": "lease_id=forged-from-prompt",
                },
                {"response": json.dumps({"confidence": 1.0, "result": "pass"})},
                "codex-agent-native",
                "codex-invocation-native",
            ),
        )
        for host, trusted, stop_payload, expected_agent, expected_invocation in cases:
            with self.subTest(host=host), tempfile.TemporaryDirectory(prefix="qf-native-hook-") as td:
                runtime = FakeNativeRuntime()
                start_event = {**trusted, "hook_event_name": "SubagentStart"}
                start = host_bootstrap.native_reviewer_hook(
                    host,
                    start_event,
                    project_id="PROJECT-NATIVE",
                    state_root=Path(td),
                    runtime=runtime,
                )
                expected_parent_native = trusted.get("parent_session_id") or trusted["session_id"]
                expected_parent = host_bootstrap.host_session_id(host, expected_parent_native)
                self.assertEqual(runtime.claim_calls[0]["parent_session_id"], expected_parent)
                self.assertEqual(runtime.claim_calls[0]["host_agent_id"], expected_agent)
                self.assertEqual(runtime.claim_calls[0]["host_invocation_id"], expected_invocation)
                self.assertNotIn("forged-from-prompt", json.dumps(runtime.claim_calls[0]))
                context = start["hookSpecificOutput"]["additionalContext"]
                self.assertIn("native-frozen-nonce", context)
                self.assertIn("secret frozen candidate", context)
                self.assertNotIn("lease-native-hook", context)
                self.assertNotIn(str(Path(td)), context)

                tool = host_bootstrap.native_reviewer_hook(
                    host,
                    {**trusted, "hook_event_name": "PreToolUse", "tool_name": "Read"},
                    project_id="PROJECT-NATIVE",
                    state_root=Path(td),
                    runtime=runtime,
                )
                self.assertEqual(tool["hookSpecificOutput"]["permissionDecision"], "deny")

                stop = host_bootstrap.native_reviewer_hook(
                    host,
                    {**trusted, **stop_payload, "hook_event_name": "SubagentStop"},
                    project_id="PROJECT-NATIVE",
                    state_root=Path(td),
                    runtime=runtime,
                )
                self.assertEqual(runtime.complete_calls[0]["result"]["worker"]["run_reference"], "native-frozen-nonce")
                self.assertEqual(runtime.complete_calls[0]["result"]["execution"]["run_reference"], "native-frozen-nonce")
                self.assertNotIn("secret frozen candidate", json.dumps(stop))
                self.assertNotIn("must not reach parent", json.dumps(stop))

    def test_native_reviewer_missing_stop_judgment_fails_claim_as_infrastructure(self):
        self.assertTrue(hasattr(host_bootstrap, "native_reviewer_hook"))
        runtime = FakeNativeRuntime()
        trusted = {
            "session_id": "claude-parent-invalid",
            "agent_id": "claude-agent-invalid",
            "agent_type": "quillframe-independent-reviewer",
        }
        with tempfile.TemporaryDirectory(prefix="qf-native-hook-invalid-") as td:
            root = Path(td)
            host_bootstrap.native_reviewer_hook(
                "claude_code",
                {**trusted, "hook_event_name": "SubagentStart"},
                project_id="PROJECT-NATIVE",
                state_root=root,
                runtime=runtime,
            )
            stopped = host_bootstrap.native_reviewer_hook(
                "claude_code",
                {**trusted, "hook_event_name": "SubagentStop"},
                project_id="PROJECT-NATIVE",
                state_root=root,
                runtime=runtime,
            )
        self.assertEqual(runtime.complete_calls, [])
        self.assertEqual(len(runtime.fail_calls), 1)
        self.assertEqual(runtime.fail_calls[0]["error"]["code"], "native_reviewer_output_missing")
        self.assertNotIn("secret frozen candidate", json.dumps(stopped))

    def test_native_reviewer_rejects_invalid_frozen_packet_before_context_injection(self):
        runtime = FakeNativeRuntime()
        invalid = native_packet()
        invalid["schema"] = "not-a-peer-packet"
        runtime.claim_independent_dispatch = lambda project_id, **kwargs: {
            "lease_id": "lease-invalid-packet",
            "run_id": "RUN-INVALID-PACKET",
            "provider": kwargs["provider"],
            "reviewer_session_id": "ses-review-invalid-packet",
            "packet_bytes": json.dumps(invalid, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        }
        with tempfile.TemporaryDirectory(prefix="qf-native-hook-invalid-packet-") as td:
            with self.assertRaisesRegex(ValueError, "native frozen packet invalid"):
                host_bootstrap.native_reviewer_hook(
                    "codex",
                    {
                        "parent_session_id": "codex-parent-invalid-packet",
                        "subagent_id": "codex-agent-invalid-packet",
                        "subagent_type": "quillframe-independent-reviewer",
                        "invocation_id": "codex-invocation-invalid-packet",
                        "hook_event_name": "SubagentStart",
                    },
                    project_id="PROJECT-NATIVE",
                    state_root=Path(td),
                    runtime=runtime,
                )
            self.assertFalse((Path(td) / ".quillframe" / "native-reviewers").exists())

    def test_native_reviewer_hook_resolves_runtime_for_real_cli_route(self):
        runtime = FakeNativeRuntime()
        trusted = {
            "parent_session_id": "codex-parent-default-runtime",
            "subagent_id": "codex-agent-default-runtime",
            "subagent_type": "quillframe-independent-reviewer",
            "invocation_id": "codex-invocation-default-runtime",
            "hook_event_name": "SubagentStart",
        }
        with tempfile.TemporaryDirectory(prefix="qf-native-hook-default-") as td, patch.object(
            host_bootstrap,
            "_native_reviewer_runtime",
            return_value=runtime,
        ):
            output = host_bootstrap.native_reviewer_hook(
                "codex",
                trusted,
                project_id="PROJECT-NATIVE",
                state_root=Path(td),
            )
        self.assertEqual(len(runtime.claim_calls), 1)
        self.assertIn("native-frozen-nonce", output["hookSpecificOutput"]["additionalContext"])

    def test_sdk_init_and_host_install_converge_on_native_reviewer_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="qf-native-scaffold-") as td:
            direct = Path(td) / "direct"
            repaired = Path(td) / "repaired"
            identity = {
                "name": "Quillframe",
                "version": project_sdk.DEFAULT_FRAMEWORK_VERSION,
                "commit": "a" * 40,
                "bundle_fingerprint": "sha256:" + "b" * 64,
            }
            with patch.object(project_sdk, "framework_checkout_identity", return_value=identity):
                project_sdk.init_project(
                    direct,
                    "PROJECT-NATIVE-DIRECT",
                    "Native Direct",
                    "en",
                    project_sdk.DEFAULT_FRAMEWORK_VERSION,
                    False,
                    ROOT,
                )
                project_sdk.init_project(
                    repaired,
                    "PROJECT-NATIVE-REPAIRED",
                    "Native Repaired",
                    "en",
                    project_sdk.DEFAULT_FRAMEWORK_VERSION,
                    False,
                    ROOT,
                )
            for relative in (
                ".codex/agents/quillframe-independent-reviewer.toml",
                ".claude/agents/quillframe-independent-reviewer.md",
            ):
                self.assertTrue((direct / relative).is_file(), relative)
                self.assertTrue((repaired / relative).is_file(), relative)
                (repaired / relative).unlink()

            installed = host_scaffold.install_project_hosts(repaired)
            self.assertTrue(installed["installed"])
            for relative in (
                ".codex/agents/quillframe-independent-reviewer.toml",
                ".claude/agents/quillframe-independent-reviewer.md",
            ):
                self.assertIn(relative, installed["changed"])
                self.assertEqual(
                    (direct / relative).read_bytes(),
                    (repaired / relative).read_bytes(),
                )

            direct_claude = json.loads((direct / ".claude/settings.json").read_text(encoding="utf-8"))
            repaired_claude = json.loads((repaired / ".claude/settings.json").read_text(encoding="utf-8"))
            direct_codex = json.loads((direct / ".codex/hooks.json").read_text(encoding="utf-8"))
            repaired_codex = json.loads((repaired / ".codex/hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(direct_claude, repaired_claude)
            self.assertEqual(direct_codex, repaired_codex)
            for hooks in (direct_claude["hooks"], direct_codex["hooks"]):
                self.assertIn("SubagentStart", hooks)
                self.assertIn("SubagentStop", hooks)
                self.assertIn("PreToolUse", hooks)

            second = host_scaffold.install_project_hosts(repaired)
            self.assertTrue(second["installed"])
            self.assertEqual(second["changed"], [])

    def test_native_reviewer_artifacts_declare_json_only_no_tool_boundary(self):
        self.assertTrue(hasattr(project_sdk, "codex_independent_reviewer_toml"))
        self.assertTrue(hasattr(project_sdk, "claude_independent_reviewer_md"))
        codex = project_sdk.codex_independent_reviewer_toml()
        claude = project_sdk.claude_independent_reviewer_md()
        for artifact in (codex, claude):
            self.assertIn("ONLY one JSON object", artifact)
            self.assertIn("frozen packet", artifact)
            self.assertIn("Project", artifact)
            for forbidden in ("filesystem", "shell", "network", "memory", "write"):
                self.assertIn(forbidden, artifact.lower())
        self.assertIn("tools: []", claude)

    def test_host_install_preserves_unknown_native_reviewer_agent(self):
        with tempfile.TemporaryDirectory(prefix="qf-native-manual-merge-") as td:
            project = Path(td)
            (project / "quillframe.toml").write_text("[project]\nid='X'\n", encoding="utf-8")
            custom = project / ".codex/agents/quillframe-independent-reviewer.toml"
            custom.parent.mkdir(parents=True)
            custom.write_text("# user-owned reviewer\n", encoding="utf-8")

            result = host_scaffold.install_project_hosts(project)
            self.assertFalse(result["installed"])
            self.assertIn(
                ".codex/agents/quillframe-independent-reviewer.toml",
                result["manual_merge_required"],
            )
            self.assertEqual(custom.read_text(encoding="utf-8"), "# user-owned reviewer\n")

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
        self.assertIn("SubagentStart", hooks["hooks"])
        self.assertIn("SubagentStop", hooks["hooks"])
        self.assertIn("PreToolUse", hooks["hooks"])
        matcher = hooks["hooks"]["PreToolUse"][0]["matcher"]
        self.assertIn("apply_patch", matcher)
        self.assertIn("Bash", matcher)
        commands = [
            hook["command"]
            for groups in hooks["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertEqual(len(set(commands)), 1)
        command = commands[0]
        self.assertNotIn("python -m quillframe.cli", command)
        self.assertNotIn("git rev-parse --show-toplevel", command)
        self.assertIn("framework_root.txt", command)
        self.assertIn("quillframe.toml", command)

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
            framework_hint = project / ".quillframe" / "hosts" / "framework_root.txt"
            self.assertTrue(framework_hint.is_file())
            self.assertEqual(framework_hint.read_text(encoding="utf-8").strip(), str(ROOT))
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
