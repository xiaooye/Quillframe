from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "harness" / "semantic_workers" / "adapters" / "local_agent_adapter.py"
if str(ROOT / "harness" / "semantic_workers") not in sys.path:
    sys.path.insert(0, str(ROOT / "harness" / "semantic_workers"))

from peer_chat_relay import build as build_packet
from peer_chat_relay import validate_peer_result
from semantic_worker_router import make_contract_job


def frozen_bytes() -> bytes:
    job = make_contract_job(
        "context.profile_derive",
        "CH-NATIVE-LOCAL",
        {
            "source": {
                "object_id": "CH-NATIVE-LOCAL",
                "object_type": "Chapter",
                "source_fingerprint": "sha256:" + "a" * 64,
                "model_view": {"bounded": True},
                "stage_hints": ["draft"],
            },
            "manual_override_present": False,
        },
        source_session_id="SES-MANAGER",
    )
    packet = build_packet(job)
    return json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class NativeLocalPacketTests(unittest.TestCase):
    def test_packet_execute_passes_exact_bytes_and_project_free_cwd(self):
        import harness.semantic_workers.adapters.local_agent_adapter as adapter

        packet = frozen_bytes()
        calls: list[dict] = []

        def fake_run(argv, *, input, text, capture_output, cwd, timeout, check):
            calls.append({"argv": argv, "input": input, "text": text, "cwd": cwd, "timeout": timeout, "check": check})
            output = Path(argv[argv.index("--output-last-message") + 1])
            output.write_text('{"result":"pass","confidence":0.9}', encoding="utf-8")
            return type("Proc", (), {"returncode": 0, "stderr": "", "stdout": ""})()

        with patch.object(adapter, "exe", return_value="codex"), patch.object(adapter.subprocess, "run", side_effect=fake_run):
            judgment = adapter.execute_frozen_packet(packet, "codex", timeout=3)

        self.assertEqual(judgment, {"result": "pass", "confidence": 0.9})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["input"], packet)
        self.assertFalse((Path(calls[0]["cwd"]) / "quillframe.toml").exists())
        self.assertIn("--ephemeral", calls[0]["argv"])
        self.assertIn("--sandbox", calls[0]["argv"])
        self.assertEqual(adapter.frozen_packet_run_reference(packet), json.loads(packet)["relay_nonce"])

    def test_packet_result_binds_both_worker_and_execution_to_frozen_nonce(self):
        import harness.semantic_workers.adapters.local_agent_adapter as adapter

        packet = frozen_bytes()
        nonce = json.loads(packet)["relay_nonce"]
        with patch.object(
            adapter,
            "execute_frozen_packet",
            return_value={"result": "pass", "confidence": 0.9},
        ):
            result = adapter.execute_frozen_packet_result(packet, "codex", timeout=3)
        self.assertEqual(result["worker"]["provider"], "codex_cli")
        self.assertEqual(result["worker"]["run_reference"], nonce)
        self.assertEqual(result["execution"]["run_reference"], nonce)
        self.assertEqual(result["execution"]["transport"], "local_cli")
        self.assertEqual(result["execution"]["assurance_class"], "local_process_bounded_context")
        self.assertEqual(result["execution"]["local_process"]["provider"], "codex")
        self.assertEqual(result["job_id"], json.loads(packet)["job"]["job_id"])

    def test_local_packet_result_is_accepted_but_not_native_receipt_eligible(self):
        import harness.semantic_workers.adapters.local_agent_adapter as adapter
        from independent_invocation_receipt import build_receipt
        from semantic_worker_router import fingerprint_for

        job = {
            "job_id": "SEM-LOCAL-PEER",
            "kind": "external_review",
            "subject_id": "CH-LOCAL-PEER",
            "created_at": "fixture",
            "input_fingerprint": "",
            "input": {"candidate": "bounded"},
            "rubric": ["judge"],
            "output_contract": {
                "type": "object",
                "required": ["confidence", "result"],
                "properties": {
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "result": {"enum": ["pass", "fail"]},
                },
                "additionalProperties": False,
            },
            "permissions": {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False},
            "provenance": {"source": "fixture"},
        }
        job["input_fingerprint"] = fingerprint_for(job)
        packet = json.dumps(build_packet(job), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        with patch.object(adapter, "execute_frozen_packet", return_value={"result": "pass", "confidence": 0.9}):
            result = adapter.execute_frozen_packet_result(packet, "codex", timeout=3)
        self.assertEqual(validate_peer_result(json.loads(packet), result), [])
        with self.assertRaises(ValueError):
            build_receipt(
                json.loads(packet), result,
                lease_id="LEASE", project_id="PROJECT", run_id="RUN",
                provider="codex_cli", parent_session_id="PARENT",
                reviewer_session_id="CHILD", host_agent_id="AGENT",
                host_invocation_id="INV", lifecycle_events=[
                    {"event_kind": "prepared", "event_id": "E1", "event_fingerprint": "F1"},
                    {"event_kind": "claimed", "event_id": "E2", "event_fingerprint": "F2"},
                    {"event_kind": "completed", "event_id": "E3", "event_fingerprint": "F3"},
                ],
            )

    def test_local_packet_result_requires_both_nonce_bindings(self):
        import harness.semantic_workers.adapters.local_agent_adapter as adapter
        from semantic_worker_router import fingerprint_for

        job = {
            "job_id": "SEM-LOCAL-NONCE",
            "kind": "external_review",
            "subject_id": "CH-LOCAL-NONCE",
            "created_at": "fixture",
            "input_fingerprint": "",
            "input": {"candidate": "bounded"},
            "rubric": ["judge"],
            "output_contract": {
                "type": "object",
                "required": ["confidence", "result"],
                "properties": {
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "result": {"enum": ["pass", "fail"]},
                },
                "additionalProperties": False,
            },
            "permissions": {
                "canon_write": False,
                "framework_behavior_write": False,
                "durable_user_taste_write": False,
            },
            "provenance": {"source": "fixture"},
        }
        job["input_fingerprint"] = fingerprint_for(job)
        packet = json.dumps(
            build_packet(job), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        packet_value = json.loads(packet)
        with patch.object(
            adapter,
            "execute_frozen_packet",
            return_value={"result": "pass", "confidence": 0.9},
        ):
            valid = adapter.execute_frozen_packet_result(packet, "codex", timeout=3)

        wrong_worker = json.loads(json.dumps(valid))
        wrong_worker["worker"]["run_reference"] = "wrong"
        worker_errors = validate_peer_result(packet_value, wrong_worker)
        self.assertTrue(any("worker run reference" in error for error in worker_errors))

        wrong_execution = json.loads(json.dumps(valid))
        wrong_execution["execution"]["run_reference"] = "wrong"
        execution_errors = validate_peer_result(packet_value, wrong_execution)
        self.assertTrue(any("execution run reference" in error for error in execution_errors))

    def test_runner_rejects_tampered_packet_result_as_infrastructure_failure(self):
        from harness.semantic_workers import semantic_worker_runner as runner

        packet = frozen_bytes()
        packet_value = json.loads(packet)
        tampered = {
            "job_id": packet_value["job"]["job_id"],
            "subject_id": packet_value["job"]["subject_id"],
            "kind": packet_value["job"]["kind"],
            "input_fingerprint": packet_value["job"]["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": "claude_native_subagent",
                "model_or_reviewer": "wrong-provider",
                "run_reference": "wrong-nonce",
            },
            "judgment": {
                "description": "bounded",
                "trigger_when": "draft",
                "estimated_tokens": 8,
                "semantic_tags": ["chapter"],
                "stage_affinities": ["draft"],
            },
            "proposals": [],
            "errors": [],
            "execution": {"run_reference": "wrong-nonce"},
        }
        proc = type("Proc", (), {
            "returncode": 0,
            "stdout": json.dumps(tampered).encode("utf-8"),
            "stderr": b"",
        })()
        with patch.object(runner.subprocess, "run", return_value=proc):
            result, execution = runner.invoke_frozen_packet(packet, "adapter --packet-only", 3)
        self.assertIsNone(result)
        self.assertEqual(execution["state"], "infrastructure_failed")

    def test_runner_wraps_judgment_without_rebuilding_packet(self):
        from harness.semantic_workers import semantic_worker_runner as runner
        from semantic_worker_router import fingerprint_for

        job = {
            "job_id": "SEM-NATIVE-WRAP",
            "kind": "external_review",
            "subject_id": "CH-NATIVE-WRAP",
            "created_at": "fixture",
            "input_fingerprint": "",
            "input": {"candidate": "bounded"},
            "rubric": ["judge"],
            "output_contract": {
                "type": "object",
                "required": ["confidence", "result"],
                "properties": {
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "result": {"enum": ["pass", "fail"]},
                },
                "additionalProperties": False,
            },
            "permissions": {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False},
            "provenance": {"source": "fixture"},
        }
        job["input_fingerprint"] = fingerprint_for(job)
        packet = json.dumps(build_packet(job), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        calls: list[bytes] = []
        proc = type("Proc", (), {
            "returncode": 0,
            "stdout": json.dumps({"result": "pass", "confidence": 0.9}).encode("utf-8"),
            "stderr": b"",
        })()

        def fake_run(argv, *, input, text, capture_output, timeout, check):
            calls.append(input)
            self.assertEqual(argv[-1], "--packet-only")
            self.assertEqual(argv[argv.index("--provider") + 1], "codex")
            return proc

        with patch.object(runner.subprocess, "run", side_effect=fake_run):
            result, execution = runner.invoke_frozen_packet(packet, "adapter --provider codex --packet-only", 3)

        self.assertEqual(calls, [packet])
        self.assertIsNotNone(result)
        self.assertEqual(result["worker"]["provider"], "codex_cli")
        self.assertEqual(result["worker"]["run_reference"], json.loads(packet)["relay_nonce"])
        self.assertEqual(result["execution"]["transport"], "local_cli")
        self.assertEqual(result["execution"]["assurance_class"], "local_process_bounded_context")
        self.assertEqual(execution["state"], "completed")

    def test_runner_rejects_adapter_minted_typed_identity(self):
        from harness.semantic_workers import semantic_worker_runner as runner
        from semantic_worker_router import fingerprint_for

        job = {
            "job_id": "SEM-LOCAL-IDENTITY",
            "kind": "external_review",
            "subject_id": "CH-LOCAL-IDENTITY",
            "created_at": "fixture",
            "input_fingerprint": "",
            "input": {"candidate": "bounded"},
            "rubric": ["judge"],
            "output_contract": {
                "type": "object",
                "required": ["confidence", "result"],
                "properties": {
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "result": {"enum": ["pass", "fail"]},
                },
                "additionalProperties": False,
            },
            "permissions": {
                "canon_write": False,
                "framework_behavior_write": False,
                "durable_user_taste_write": False,
            },
            "provenance": {"source": "fixture"},
        }
        job["input_fingerprint"] = fingerprint_for(job)
        packet = json.dumps(
            build_packet(job),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        frozen = json.loads(packet)
        forged = {
            "job_id": frozen["job"]["job_id"],
            "subject_id": frozen["job"]["subject_id"],
            "kind": frozen["job"]["kind"],
            "input_fingerprint": frozen["job"]["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": "human",
                "model_or_reviewer": "forged-authority",
                "run_reference": frozen["relay_nonce"],
            },
            "judgment": {"result": "pass", "confidence": 0.9},
            "proposals": [],
            "errors": [],
            "execution": {"run_reference": frozen["relay_nonce"]},
        }
        proc = type("Proc", (), {
            "returncode": 0,
            "stdout": json.dumps(forged).encode("utf-8"),
            "stderr": b"",
        })()

        with patch.object(runner.subprocess, "run", return_value=proc):
            result, execution = runner.invoke_frozen_packet(
                packet,
                "adapter --provider codex --packet-only",
                3,
            )

        self.assertIsNone(result)
        self.assertEqual(execution["state"], "infrastructure_failed")
        self.assertEqual(execution["error_code"], "packet_adapter_identity_forbidden")
        self.assertEqual(execution["error"], "packet_adapter_identity_forbidden")

    def test_packet_route_source_identifies_local_cli_not_native_subagent(self):
        from harness.semantic_workers import semantic_worker_runner as runner

        with patch.object(runner.shutil, "which", side_effect=lambda name: "/usr/bin/codex" if name == "codex" else None):
            command, source = runner.local_command(packet_only=True)
        self.assertIsNotNone(command)
        self.assertEqual(source, "local_codex_cli")
        self.assertNotIn("native_subagent", source)

    def test_tampered_or_malformed_packet_is_infrastructure_failure_without_invocation(self):
        import harness.semantic_workers.adapters.local_agent_adapter as adapter

        packet = json.loads(frozen_bytes())
        packet["relay_nonce"] = "tampered"
        with patch.object(adapter.subprocess, "run") as run:
            with self.assertRaises(adapter.FrozenPacketError):
                adapter.execute_frozen_packet(json.dumps(packet).encode("utf-8"), "codex", timeout=3)
            run.assert_not_called()
        with self.assertRaises(adapter.FrozenPacketError):
            adapter.execute_frozen_packet(b"not-json", "codex", timeout=3)

    def test_malformed_judgment_is_infrastructure_failure(self):
        import harness.semantic_workers.adapters.local_agent_adapter as adapter

        def fake_run(argv, **kwargs):
            output = Path(argv[argv.index("--output-last-message") + 1])
            output.write_text("not-json", encoding="utf-8")
            return type("Proc", (), {"returncode": 0, "stderr": "", "stdout": ""})()

        with patch.object(adapter, "exe", return_value="codex"), patch.object(adapter.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(adapter.FrozenPacketError):
                adapter.execute_frozen_packet(frozen_bytes(), "codex", timeout=3)


if __name__ == "__main__":
    unittest.main()
