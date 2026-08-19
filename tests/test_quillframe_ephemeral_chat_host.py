from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC = ROOT / "harness" / "semantic_workers"
EVALS = ROOT / "evals"
for path in (ROOT, SEMANTIC, EVALS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from harness.integrations import chat_host_relay
from peer_bridge_receipt import self_test as receipt_self_test
from peer_chat_relay import build as build_packet, validate_peer_result
from qualification_test_fixtures import make_qualified_receipt
from semantic_worker_router import make_contract_job


def _load_auto_review():
    path = ROOT / ".github" / "actions" / "project-peer-semantic" / "auto_review.py"
    spec = importlib.util.spec_from_file_location("quillframe_auto_review_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class EphemeralChatHostTests(unittest.TestCase):
    def test_loopback_relay_is_manager_only_and_atomic(self):
        report = chat_host_relay.self_test()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["loopback_default"])
        self.assertTrue(report["checks"]["response_atomic"])
        self.assertTrue(report["checks"]["manager_transport_only"])
        self.assertFalse(report["authority"])

    def test_github_copilot_actions_is_the_truthful_github_independent_provider(self):
        fp = "sha256:" + "a" * 64
        job = make_contract_job(
            "quality.production_review",
            "CH-TEST",
            {"candidate_fingerprint": fp, "candidate_text": "bounded candidate", "reader_grip": "very_high"},
            source_session_id="SES-MANAGER",
            qualification_receipt=make_qualified_receipt(fp, "CH-TEST"),
        )
        packet = build_packet(job)
        result = {
            "job_id": job["job_id"],
            "subject_id": job["subject_id"],
            "kind": job["kind"],
            "input_fingerprint": job["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": "github_copilot_actions",
                "model_or_reviewer": "copilot",
                "run_reference": packet["relay_nonce"],
            },
            "judgment": {
                "confidence": 0.8,
                "result": "pass",
                "report": "No material defect in the bounded fixture.",
                "evidence_refs": ["candidate:fixture"],
            },
            "proposals": [],
            "errors": [],
        }
        self.assertEqual(validate_peer_result(packet, result), [])
        unsupported = json.loads(json.dumps(result))
        unsupported["worker"]["provider"] = "github_models"
        self.assertTrue(any("declared" in item for item in validate_peer_result(packet, unsupported)))
        tampered = json.loads(json.dumps(result))
        tampered["worker"]["run_reference"] = "wrong"
        self.assertTrue(any("relay nonce" in item for item in validate_peer_result(packet, tampered)))

    def test_project_peer_receipt_self_test_covers_executable_build_contract(self):
        report = receipt_self_test()
        self.assertEqual(report["peer_bridge_receipt_contract"], "PASS")
        self.assertTrue(report["checks"]["valid_receipt_passes"])
        self.assertTrue(report["checks"]["runtime_ref_tamper_rejected"])

    def test_auto_review_parser_accepts_only_json_object_shape(self):
        module = _load_auto_review()
        self.assertEqual(module._parse_json_object('```json\n{"result":"pass"}\n```'), {"result": "pass"})
        with self.assertRaises(ValueError):
            module._parse_json_object("not-json")

    def test_project_peer_action_exposes_review_mode_without_live_model_call(self):
        text = (ROOT / ".github" / "actions" / "project-peer-semantic" / "action.yml").read_text(encoding="utf-8")
        self.assertIn("prepare, review, or validate-result", text)
        self.assertIn("QUILLFRAME_REVIEW_MODEL", text)
        self.assertIn("auto_review.py", text)
        self.assertIn("validation-receipt", text)
        self.assertIn("peer-result", text)

    def test_github_paths_consume_frozen_packet_without_rebuild_or_models_claim(self):
        action = (ROOT / ".github/actions/project-peer-semantic/action.yml").read_text(encoding="utf-8")
        bridge = (ROOT / ".github/actions/project-peer-semantic/bridge.py").read_text(encoding="utf-8")
        auto = (ROOT / ".github/actions/project-peer-semantic/auto_review.py").read_text(encoding="utf-8")
        self.assertIn("frozen-packet", action)
        self.assertIn("QUILLFRAME_FROZEN_PACKET", action)
        self.assertNotIn("build_packet(job)", bridge)
        self.assertNotIn("build_packet(job)", auto)
        self.assertNotIn("github_models", bridge + auto + action)

    def test_reusable_github_bridge_checks_out_and_executes_exact_commit(self):
        workflow = (ROOT / ".github/workflows/quillframe-chat-semantic-bridge.yml").read_text(encoding="utf-8")
        self.assertNotIn("@${{ inputs.framework-ref }}", workflow)
        self.assertIn("repository: ${{ github.repository }}", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn("path: .quillframe-project", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("QUILLFRAME_PROJECT_CHECKOUT: ${{ github.workspace }}/.quillframe-project", workflow)
        self.assertIn("repository: xiaooye/Quillframe", workflow)
        self.assertIn("ref: ${{ inputs.framework-ref }}", workflow)
        self.assertIn("EXPECTED_FRAMEWORK_COMMIT: ${{ inputs.framework-ref }}", workflow)
        self.assertIn("QUILLFRAME_ACTION_REF: ${{ steps.framework.outputs.commit }}", workflow)
        self.assertIn(".quillframe-framework/.github/actions/project-peer-semantic/bridge.py", workflow)
        self.assertIn(".quillframe-framework/.github/actions/project-peer-semantic/auto_review.py", workflow)

    def test_project_bridge_binds_to_caller_checkout_and_rejects_escape(self):
        module_path = ROOT / ".github" / "actions" / "project-peer-semantic" / "bridge.py"
        spec = importlib.util.spec_from_file_location("quillframe_bridge_checkout_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(module_path.parent))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)

        with tempfile.TemporaryDirectory(prefix="qf-peer-caller-") as td:
            workspace = Path(td)
            checkout = workspace / ".quillframe-project"
            checkout.mkdir()
            (checkout / "project").mkdir()
            (checkout / "project" / "quillframe.toml").write_text(
                '[project]\nid = "PROJECT-TEMP"\n', encoding="utf-8"
            )
            (checkout / "project" / "quillframe.lock.json").write_text(
                json.dumps({"framework": {"source_repo": "xiaooye/Quillframe", "commit": "a" * 40}}),
                encoding="utf-8",
            )
            packet_path = checkout / "project" / "packet.json"
            packet_path.write_bytes(
                json.dumps(
                    build_packet(
                        make_contract_job(
                            "context.profile_derive",
                            "CH-TEMP",
                            {
                                "source": {
                                    "object_id": "CH-TEMP",
                                    "object_type": "Chapter",
                                    "source_fingerprint": "sha256:" + "b" * 64,
                                    "model_view": {"bounded": True},
                                    "stage_hints": ["draft"],
                                },
                                "manual_override_present": False,
                            },
                            source_session_id="SES-TEMP",
                        )
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            env = {
                "GITHUB_WORKSPACE": str(workspace),
                "QUILLFRAME_PROJECT_CHECKOUT": str(checkout),
                "QUILLFRAME_PROJECT_ROOT": "project",
                "QUILLFRAME_FROZEN_PACKET": "project/packet.json",
                "QUILLFRAME_PROJECT_ID": "PROJECT-TEMP",
                "QUILLFRAME_ACTION_REPOSITORY": "xiaooye/Quillframe",
                "QUILLFRAME_ACTION_REF": "a" * 40,
                "GITHUB_REPOSITORY": "example/consumer",
                "QUILLFRAME_ACTION_PATH": str(ROOT / ".github" / "actions" / "project-peer-semantic"),
            }
            with patch.dict(os.environ, env, clear=False):
                binding = module.load_project_binding()
                self.assertEqual(binding["project_root"], checkout / "project")
                packet, raw = module.load_frozen_packet()
                self.assertEqual(raw, packet_path.read_bytes())
                with patch.dict(os.environ, {"QUILLFRAME_PROJECT_ROOT": "../escape"}, clear=False):
                    with self.assertRaises(SystemExit):
                        module.load_project_binding()
                with patch.dict(os.environ, {"QUILLFRAME_FROZEN_PACKET": "../escape.json"}, clear=False):
                    with self.assertRaises(SystemExit):
                        module.load_frozen_packet()


if __name__ == "__main__":
    unittest.main()
