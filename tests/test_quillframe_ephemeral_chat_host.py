from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

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

    def test_github_models_is_a_truthful_independent_peer_provider(self):
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
                "provider": "github_models",
                "model_or_reviewer": "openai/gpt-4.1",
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


if __name__ == "__main__":
    unittest.main()
