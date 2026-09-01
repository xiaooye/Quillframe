from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from evals.native_style_runner import NativeStyleRunner, NativeStyleRunnerError


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "evals" / "native_style_runner.py"
VISIBLE_TEXT = "released candidate"
VISIBLE_FP = "sha256:" + hashlib.sha256(VISIBLE_TEXT.encode("utf-8")).hexdigest()


class FakeExecutor:
    def __init__(self, *, result=None, final_status="completed") -> None:
        self.result = result or {"status": final_status, "candidate": {"candidate_id": "C", "candidate_fingerprint": VISIBLE_FP}}
        self.final_status = final_status
        self.executed = False
        self.resumed = False

    def status(self, project_id, run_id):
        status = self.final_status if self.executed or self.resumed else "created"
        return {"status": status, "candidate": {"candidate_id": "C", "candidate_fingerprint": VISIBLE_FP} if status == "completed" else None}

    def execute(self, project_id, run_id, **execution):
        self.executed = True
        return self.result

    def resume_execution(self, project_id, run_id):
        self.resumed = True
        return self.result


class FakeOperations:
    def __init__(self) -> None:
        self.visible_calls = []

    def candidate_visible_get(self, project_id, *, candidate_id):
        self.visible_calls.append((project_id, candidate_id))
        return {"candidate_id": candidate_id, "candidate_fingerprint": VISIBLE_FP,
                "content": VISIBLE_TEXT, "content_access": "production_release_only",
                "accepted": False, "settled": False}


class NativeStyleRunnerTests(unittest.TestCase):
    def test_ast_uses_only_public_production_executor_and_has_no_transport_or_write_path(self):
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        production_imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("production_runtime")]
        self.assertEqual(len(production_imports), 1)
        self.assertEqual(production_imports[0].module, "production_runtime")
        self.assertEqual([alias.name for alias in production_imports[0].names], ["ProductionRunExecutor"])
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue(imported.isdisjoint({"agent_runtime", "model_runtime", "subprocess"}))
        source = RUNNER.read_text(encoding="utf-8").lower()
        for forbidden in ("agentjob", "adapter", "codex"):
            self.assertNotIn(forbidden, source)
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(called.isdisjoint({"accept_candidate", "settle", "publish"}))

    def test_completed_candidate_is_read_only_through_core_visibility(self):
        executor = FakeExecutor()
        operations = FakeOperations()
        result = NativeStyleRunner(executor, operations).execute("P", "R", instruction="frozen request")
        self.assertEqual(result["candidate"]["content"], VISIBLE_TEXT)
        self.assertEqual(operations.visible_calls, [("P", "C")])
        self.assertFalse(result["authority"])

    def test_bare_runtime_prose_fails_closed(self):
        executor = FakeExecutor(result={"status": "completed", "content": "bare prose"})
        operations = FakeOperations()
        with self.assertRaises(NativeStyleRunnerError) as blocked:
            NativeStyleRunner(executor, operations).execute("P", "R")
        self.assertEqual(blocked.exception.code, "native_runtime_prose_forbidden")
        self.assertEqual(operations.visible_calls, [])

    def test_nested_or_string_runtime_prose_fails_closed(self):
        cases = (
            ({"status": "completed", "debug": {"text": "hidden draft"}}, "native_runtime_result_invalid"),
            ({"status": "completed", "candidate": "hidden draft"}, "native_runtime_prose_forbidden"),
            ({"status": "completed", "rows": [{"manuscript": "hidden draft"}]}, "native_runtime_result_invalid"),
        )
        for payload, code in cases:
            with self.subTest(payload=payload):
                executor = FakeExecutor(result=payload)
                with self.assertRaises(NativeStyleRunnerError) as blocked:
                    NativeStyleRunner(executor, FakeOperations()).execute("P", "R")
                self.assertEqual(blocked.exception.code, code)

    def test_visible_candidate_identity_or_lifecycle_mismatch_fails_closed(self):
        class BadOperations(FakeOperations):
            def candidate_visible_get(self, project_id, *, candidate_id):
                value = super().candidate_visible_get(project_id, candidate_id=candidate_id)
                value["candidate_id"] = "OTHER"
                return value
        with self.assertRaises(NativeStyleRunnerError) as blocked:
            NativeStyleRunner(FakeExecutor(), BadOperations()).execute("P", "R")
        self.assertEqual(blocked.exception.code, "native_candidate_not_visible")

    def test_unfinished_run_returns_text_free_status_and_visible_read_fails_closed(self):
        executor = FakeExecutor(
            final_status="awaiting_external",
            result={"status": "awaiting_external", "peer_packet": {"candidate_text": "hidden draft"}},
        )
        operations = FakeOperations()
        runner = NativeStyleRunner(executor, operations)
        result = runner.execute("P", "R")
        self.assertEqual("awaiting_external", result["status"])
        self.assertNotIn("peer_packet", result)
        self.assertNotIn("hidden draft", str(result))
        self.assertEqual(operations.visible_calls, [])
        with self.assertRaises(NativeStyleRunnerError) as blocked:
            runner.visible_candidate("P", "R")
        self.assertEqual(blocked.exception.code, "native_run_not_completed")
        self.assertEqual(operations.visible_calls, [])

    def test_durable_pending_status_preserves_only_safe_polling_metadata(self):
        pending = {
            "status": "semantic_pending", "awaiting": "same_model_request",
            "same_request_poll_only": True, "candidate_visible": False,
            "raw_draft_visible": False, "automatic_model_retry": False,
            "execution_journal": {
                "active_executor": False, "dispatched_call_count": 1,
                "confirmed_call_count": 0, "unconfirmed_call_ids": ["pcall_1"],
                "hard_unconfirmed_call_ids": [], "pending_call_ids": ["pcall_1"],
                "safe_to_poll_pending": True, "request_fingerprint": "sha256:" + "a" * 64,
                "private_prompt": "must not escape",
            },
        }
        executor = FakeExecutor(result=pending, final_status="semantic_pending")
        result = NativeStyleRunner(executor, FakeOperations()).execute("P", "R")
        self.assertEqual("same_model_request", result["awaiting"])
        self.assertTrue(result["same_request_poll_only"])
        self.assertEqual(["pcall_1"], result["execution_journal"]["pending_call_ids"])
        self.assertNotIn("private_prompt", result["execution_journal"])


if __name__ == "__main__":
    unittest.main()
