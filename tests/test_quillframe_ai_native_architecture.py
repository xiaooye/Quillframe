"""Mechanical guards for the AI-native fiction-source boundary.

These tests verify code paths and schemas only.  They do not score prose or
claim that any generated manuscript is natural, humorous, or author-approved.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CURRENT_CONTRACTS = (
    ROOT / "harness" / "semantic_workers" / "contracts" / "production-loop.json",
    ROOT / "harness" / "semantic_workers" / "contracts" / "quality.json",
)
PRODUCTION_DECISION_MODULES = (
    ROOT / "production_runtime" / "runtime.py",
    ROOT / "production_runtime" / "semantic.py",
    ROOT / "production_runtime" / "workflow.py",
    ROOT / "production_runtime" / "repair.py",
    ROOT / "production_runtime" / "writer_context.py",
    ROOT / "quality" / "candidate_qualification.py",
    ROOT / "quality" / "production_readiness.py",
    ROOT / "quality" / "repair_policy.py",
)


def schema_property_names(value):
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            yield from properties
        for child in value.values():
            yield from schema_property_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from schema_property_names(child)


class AiNativeArchitectureTests(unittest.TestCase):
    def test_current_contracts_expose_no_script_or_mechanical_literary_gate_fields(self):
        forbidden_fields = {
            "quality_script", "script_path", "program_source", "shell_command",
            "english_count", "english_word_count", "banned_words", "ai_word_count",
            "sentence_length", "paragraph_length", "dialogue_ratio", "aigc_score",
            "humanizer_score", "human_likeness_score", "literary_average_score",
        }
        observed = set()
        for path in CURRENT_CONTRACTS:
            registry = json.loads(path.read_text(encoding="utf-8"))
            observed.update(name.lower() for name in schema_property_names(registry["contracts"]))
        self.assertTrue(forbidden_fields.isdisjoint(observed), sorted(forbidden_fields & observed))

    def test_draft_and_revise_decision_modules_do_not_generate_or_execute_quality_programs(self):
        blocked_imports = {"subprocess", "tempfile"}
        blocked_calls = {"compile", "eval", "exec"}
        for path in PRODUCTION_DECISION_MODULES:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                imports = {
                    alias.name.split(".", 1)[0]
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.Import, ast.ImportFrom))
                    for alias in node.names
                }
                calls = {
                    node.func.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                self.assertTrue(blocked_imports.isdisjoint(imports), sorted(blocked_imports & imports))
                self.assertTrue(blocked_calls.isdisjoint(calls), sorted(blocked_calls & calls))

    def test_optional_prose_telemetry_is_outside_production_decisions(self):
        for path in PRODUCTION_DECISION_MODULES:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("prose_telemetry", source)
                self.assertNotIn("quality.prose_telemetry", source)

    def test_consumer_failure_identity_did_not_enter_general_framework(self):
        forbidden = (
            "CHINABOY-LOCAL-20260828",
            "run_29af7d066b1547c89e8719835f02fb67",
            "cand_7bdba0de9333453a87f4e283eaa35c1c",
            "/home/quillframe/projects/quillframe-chinaboy-local",
        )
        framework_paths = (*PRODUCTION_DECISION_MODULES, *CURRENT_CONTRACTS)
        for path in framework_paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                source = path.read_text(encoding="utf-8")
                for value in forbidden:
                    self.assertNotIn(value, source)


if __name__ == "__main__":
    unittest.main()
