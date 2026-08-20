from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SECRET = "P1_REDACTION_SENTINEL"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_runner():
    semantic = ROOT / "harness" / "semantic_workers"
    sys.path.insert(0, str(semantic))
    return load_module("qf_p1_runner", semantic / "semantic_worker_runner.py")


def load_local():
    semantic = ROOT / "harness" / "semantic_workers"
    sys.path.insert(0, str(semantic))
    return load_module("qf_p1_local", semantic / "adapters" / "local_agent_adapter.py")


def load_bridge():
    sys.path.insert(0, str(ROOT))
    return load_module(
        "qf_p1_bridge",
        ROOT / ".github" / "actions" / "project-peer-semantic" / "bridge.py",
    )


def load_review(bridge):
    sys.modules["bridge"] = bridge
    return load_module(
        "qf_p1_auto_review",
        ROOT / ".github" / "actions" / "project-peer-semantic" / "auto_review.py",
    )


def load_tauri_sidecar():
    return load_module("qf_p1_tauri_sidecar", ROOT / "studio" / "tauri_core_sidecar.py")


class RedactionBoundaryTests(unittest.TestCase):
    def test_tauri_sidecar_failure_is_typed_and_never_echoes_raw_exception(self):
        sidecar = load_tauri_sidecar()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = sidecar.main([f"unknown-{SECRET}"])
        report = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(report["code"], "sidecar_command_invalid")
        self.assertNotIn("message", report)
        self.assertNotIn(SECRET, stdout.getvalue())

        stdout = io.StringIO()
        with (
            patch.object(sidecar, "_read_stdin_json", return_value={}),
            patch.object(sidecar, "_invoke", side_effect=OSError(f"{SECRET} /var/private/sentinel")),
            contextlib.redirect_stdout(stdout),
        ):
            status = sidecar.main(["invoke"])
        report = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertEqual(report["code"], "sidecar_internal_error")
        self.assertNotIn(SECRET, stdout.getvalue())

    def test_runner_cli_file_and_json_failures_are_typed_and_redacted(self):
        runner = load_runner()
        sentinel_path = f"/tmp/{SECRET}/jobs.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = runner.main(["run", "--jobs", sentinel_path])
        report = json.loads(stdout.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(report["status"], "semantic_invalid")
        self.assertEqual(report["executions"][0]["error_code"], "semantic_input_unavailable")
        self.assertNotIn(SECRET, stdout.getvalue())
        self.assertNotIn(sentinel_path, stdout.getvalue())

        with patch.object(runner, "load_json", side_effect=json.JSONDecodeError(SECRET, "", 0)):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = runner.main(["run", "--jobs", "safe.json"])
        report = json.loads(stdout.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(report["executions"][0]["error_code"], "semantic_input_invalid_json")
        self.assertNotIn(SECRET, stdout.getvalue())

        with (
            patch.object(runner, "load_json", return_value={"jobs": []}),
            patch.object(runner, "dump", side_effect=[OSError(SECRET), None]) as dump_mock,
        ):
            status = runner.main(["run", "--jobs", "safe.json", "--output", sentinel_path])
            fallback_report = dump_mock.call_args_list[-1].args[0]
        self.assertEqual(status, 2)
        self.assertEqual(fallback_report["executions"][0]["error_code"], "semantic_output_unavailable")
        self.assertNotIn(SECRET, json.dumps(fallback_report))

    def test_runner_report_omits_command_and_typed_failure_omits_stderr(self):
        runner = load_runner()
        report = runner.run_jobs({"jobs": []}, f"echo {SECRET}", "environment", 7)
        self.assertNotIn(SECRET, json.dumps(report))
        self.assertNotIn("command", report["adapter"])
        self.assertTrue(report["adapter"]["configured"])

        proc = SimpleNamespace(returncode=23, stdout=b"", stderr=f"stderr {SECRET}".encode())
        with patch.object(runner.subprocess, "run", return_value=proc):
            _result, execution = runner.invoke({}, "echo safe", 7)
        self.assertNotIn(SECRET, json.dumps(execution))
        self.assertEqual(execution["error_code"], "adapter_exit")
        self.assertEqual(execution["exit_code"], 23)
        self.assertEqual(execution["timeout_seconds"], 7)

    def test_runner_oserror_and_json_parser_are_typed_and_redacted(self):
        runner = load_runner()
        with patch.object(runner.subprocess, "run", side_effect=OSError(SECRET)):
            _result, execution = runner.invoke({}, "echo safe", 9)
        self.assertNotIn(SECRET, json.dumps(execution))
        self.assertEqual(execution["error_code"], "adapter_launch_failed")

        proc = SimpleNamespace(returncode=0, stdout=b"not-json", stderr=b"")
        parser_error = json.JSONDecodeError(SECRET, "", 0)
        with (
            patch.object(runner.subprocess, "run", return_value=proc),
            patch.object(runner.json, "loads", side_effect=parser_error),
        ):
            _result, execution = runner.invoke({}, "echo safe", 9, source="cli")
        self.assertNotIn(SECRET, json.dumps(execution))
        self.assertEqual(execution["error_code"], "adapter_result_invalid_json")

    def test_local_adapter_oserror_and_parser_errors_are_typed_and_redacted(self):
        adapter = load_local()
        packet = {"job": {"output_contract": {"type": "object"}}, "relay_nonce": "RUN-P1"}
        with (
            patch.object(adapter, "_frozen_packet", return_value=(b"{}", packet)),
            patch.object(adapter, "exe", return_value="codex"),
            patch.object(adapter.subprocess, "run", side_effect=OSError(SECRET)),
        ):
            with self.assertRaises(adapter.FrozenPacketError) as caught:
                adapter.execute_frozen_packet(b"{}", "codex", timeout=3)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(caught.exception.code, "provider_launch_failed")

        def fake_success(argv, **_kwargs):
            output_path = Path(argv[argv.index("--output-last-message") + 1])
            output_path.write_text("{}", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

        with (
            patch.object(adapter, "_frozen_packet", return_value=(b"{}", packet)),
            patch.object(adapter, "exe", return_value="codex"),
            patch.object(adapter.subprocess, "run", side_effect=fake_success),
            patch.object(adapter, "parse_json_text", side_effect=ValueError(SECRET)),
        ):
            with self.assertRaises(adapter.FrozenPacketError) as caught:
                adapter.execute_frozen_packet(b"{}", "codex", timeout=3)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(caught.exception.code, "provider_result_invalid")

    def test_bridge_command_failure_and_json_failure_do_not_escape_raw_details(self):
        bridge = load_bridge()
        proc = SimpleNamespace(returncode=2, stdout=SECRET, stderr=f"stderr {SECRET}")
        with patch.object(bridge.subprocess, "run", return_value=proc):
            with self.assertRaises(SystemExit) as caught:
                bridge.run(["gh", "api", SECRET], capture=True)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertIn("command_failed", str(caught.exception))

        with patch.object(bridge.Path, "read_text", side_effect=OSError(SECRET)):
            with self.assertRaises(SystemExit) as caught:
                bridge.read_json(Path("/private/secret.json"))
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertIn("json_read_failed", str(caught.exception))

    def test_copilot_failure_and_parser_failure_are_typed_and_redacted(self):
        bridge = load_bridge()
        review = load_review(bridge)
        env = {"COPILOT_GITHUB_TOKEN": "token-for-test", "PATH": "/usr/bin"}
        proc = SimpleNamespace(
            returncode=17,
            stdout=f"stdout {SECRET}".encode(),
            stderr=f"stderr {SECRET}".encode(),
        )
        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(review.subprocess, "run", return_value=proc),
        ):
            with self.assertRaises(Exception) as caught:
                review._copilot_judgment(b"{}", "model")
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(getattr(caught.exception, "code", None), "copilot_exit")
        self.assertEqual(getattr(caught.exception, "exit_code", None), 17)

        with (
            patch.object(review, "_parse_json_object", side_effect=ValueError(SECRET)),
            patch.object(
                review.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout=b"{}", stderr=b""),
            ),
            patch.dict(os.environ, env, clear=False),
        ):
            with self.assertRaises(Exception) as caught:
                review._copilot_judgment(b"{}", "model")
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(getattr(caught.exception, "code", None), "copilot_result_invalid")


if __name__ == "__main__":
    unittest.main()
