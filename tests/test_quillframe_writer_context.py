from __future__ import annotations

import json
import unittest

from harness.context_runtime import fingerprint
from persistence.quillframe_sqlite import fingerprint_text
from production_runtime.contracts import ProductionRunError
from production_runtime.repair import writer_context
from production_runtime.writer_context import (
    INVENTORY_SCHEMA,
    materialize_writer_pack,
)
from quality.author_objective_gate import validate_objective_assessments


def objectives() -> dict:
    value = {
        "schema": "quillframe_current_author_objectives_v1",
        "items": [{
            "objective_id": "OBJ-1",
            "statement": "Use natural Chinese and enact the character's choice.",
            "source_refs": ["author:current"],
            "hard": True,
        }],
        "source_fingerprint": fingerprint("author-current"),
        "priority": "current_explicit_author_direction",
        "authority": False,
    }
    value["objectives_fingerprint"] = fingerprint(value)
    return value


def inventory() -> dict:
    value = {
        "schema": INVENTORY_SCHEMA,
        "present_character_ids": ["A"],
        "required_context_ids": [],
        "items": [
            {
                "context_id": "character:A",
                "category": "present_character",
                "source_fingerprint": fingerprint("character:A"),
                "selection_view": {"character_id": "A", "name": "A"},
                "writer_value": {"character_id": "A", "name": "A"},
            },
            {
                "context_id": "lore:unselected",
                "category": "world_fact",
                "source_fingerprint": fingerprint("lore:unselected"),
                "selection_view": {"fact": "UNSELECTED-LORE-SENTINEL"},
                "writer_value": {"fact": "UNSELECTED-LORE-SENTINEL"},
            },
        ],
        "forbidden_classes": [
            "rejected_prose", "reviewer_analysis", "repair_explanation",
            "private_character_deliberation", "unrelated_plan_or_lore",
            "future_pov_unknown", "scripted_quality_diagnostic",
        ],
        "authority": False,
    }
    value["inventory_fingerprint"] = fingerprint(value)
    return value


class WriterContextBoundaryTests(unittest.TestCase):
    def source(self) -> dict:
        return {
            "source_request": {"rule_material": [{
                "id": "RULE-1",
                "authority": "framework",
                "statement": "Mechanically bound authority statement.",
            }]},
            "candidate_fingerprint": fingerprint_text("REJECTED-PROSE-SENTINEL"),
            "candidate_text": "REJECTED-PROSE-SENTINEL",
            "reader_binding": {"result": {"judgment": {
                "reviewer_analysis": "REVIEWER-EXPLANATION-SENTINEL",
            }}},
        }

    @staticmethod
    def repair(mode: str) -> dict:
        target = {
            "target_id": "TARGET-1",
            "scene_ref": "SCENE-1",
            "route": "local_edit",
            "evidence_quote": "TARGET-WINDOW",
            "edit_window_quote": "TARGET-WINDOW",
        }
        return {
            "policy": {
                "repair_owner": "surface",
                "revision_route": "fresh_realization" if mode == "fresh_realization" else "local_edit",
                "generation_mode": mode,
                "targets": [target],
                "excluded_writer_context_classes": [
                    "rejected_prose", "reviewer_analysis", "repair_explanation",
                ],
            },
            "objective_envelope": {"fingerprint": fingerprint("objective-envelope")},
            "editor_binding_fingerprint": fingerprint("editor-binding"),
        }

    def test_fresh_realization_never_projects_rejected_prose_or_review_explanation(self) -> None:
        context = writer_context(
            self.source(),
            self.repair("fresh_realization"),
            {
                "context_bundle_fingerprint": fingerprint("bundle"),
                "freeze_fingerprint": fingerprint("freeze"),
            },
        )
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertNotIn("REJECTED-PROSE-SENTINEL", serialized)
        self.assertNotIn("REVIEWER-EXPLANATION-SENTINEL", serialized)
        self.assertNotIn("TARGET-WINDOW", serialized)
        self.assertNotIn("bounded_repair_evidence", context)

    def test_local_repair_projects_only_exact_edit_windows_not_full_candidate(self) -> None:
        source = self.source()
        source["candidate_text"] = "OUTSIDE-BEFORE TARGET-WINDOW OUTSIDE-AFTER"
        source["candidate_fingerprint"] = fingerprint_text(source["candidate_text"])
        context = writer_context(source, self.repair("local_or_bounded_repair"), {})
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertIn("TARGET-WINDOW", serialized)
        self.assertNotIn("OUTSIDE-BEFORE", serialized)
        self.assertNotIn("OUTSIDE-AFTER", serialized)
        self.assertFalse(context["bounded_repair_evidence"]["full_candidate_visible"])

    def test_writer_pack_contains_only_model_selected_context_and_rejects_private_keys(self) -> None:
        pack = materialize_writer_pack(
            inventory(),
            selected_context_ids=["character:A"],
            scene_contract={"ending_constraint": "A choice closes."},
            director_note="Let the choice carry the pressure.",
            author_objectives=objectives(),
            source_binding_fingerprint=fingerprint("source-binding"),
        )
        serialized = json.dumps(pack, ensure_ascii=False)
        self.assertNotIn("UNSELECTED-LORE-SENTINEL", serialized)
        self.assertEqual(["character:A"], pack["selection"]["selected_context_ids"])
        with self.assertRaises(ProductionRunError) as caught:
            materialize_writer_pack(
                inventory(),
                selected_context_ids=["character:A"],
                scene_contract={"ending_constraint": "A choice closes."},
                director_note="Let the choice carry the pressure.",
                author_objectives=objectives(),
                source_binding_fingerprint=fingerprint("source-binding"),
                craft_guidance={"reviewer_analysis": "must never reach Writer"},
            )
        self.assertEqual("writer_context_boundary_violation", caught.exception.code)


class AuthorObjectiveGateTests(unittest.TestCase):
    @staticmethod
    def judgment(status: str, route: str, result: str) -> dict:
        return {
            "result": result,
            "objective_assessments": [{
                "objective_id": "OBJ-1",
                "status": status,
                "evidence_refs": ["candidate:exact-span"],
                "impact_scope": "whole_candidate",
                "repair_route": route,
                "report": "Bound synthetic evidence.",
            }],
        }

    def test_hard_not_met_and_uncertain_cannot_be_averaged_into_pass(self) -> None:
        failed = validate_objective_assessments(
            objectives(), self.judgment("not_met", "fresh_realization", "fail")
        )
        self.assertEqual("fail", failed["status"])
        pending = validate_objective_assessments(
            objectives(), self.judgment("uncertain", "scene_realization", "insufficient_evidence")
        )
        self.assertEqual("pending", pending["status"])
        for status in ("not_met", "uncertain"):
            with self.assertRaisesRegex(ValueError, "requires a repair route"):
                validate_objective_assessments(
                    objectives(), self.judgment(status, "no_change", "fail")
                )


if __name__ == "__main__":
    unittest.main()
