"""Deterministic contract coverage, not a literary-quality or retention eval.

Synthetic reports below exercise schema and dispatch boundaries only. No model
is called, and accepting their shape does not validate their literary judgment.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "harness" / "semantic_workers", ROOT / "evals"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from qualification_test_fixtures import make_qualified_receipt
from registered_contract_binding import validate_registered_job
from semantic_worker_router import (
    fingerprint_for,
    load_contract_registry,
    make_contract_job,
    resolve_contract_registry,
    validate_contract_input,
    validate_typed_value,
    worker_job_view,
)


SUBJECT = "CH-CONTRACT-FIXTURE"
CANDIDATE_TEXT = "Synthetic deterministic CI candidate."
CANDIDATE_FP = "sha256:" + hashlib.sha256(CANDIDATE_TEXT.encode("utf-8")).hexdigest()
REVIEW_CONTRACTS = ("reader.engagement_audit", "quality.production_review")
READING_POSITION = {
    "genre_profile": "Quiet contemporary fiction.",
    "platform_profile": "Serialized prose with room for everyday relationships.",
    "chapter_position": "An opening chapter.",
    "reader_grip": "low",
}


def contract_for(contract_id):
    path, _ = resolve_contract_registry(contract_id)
    registry = load_contract_registry(path)
    return registry, registry["contracts"][contract_id]


def review_payload():
    return {
        "candidate_fingerprint": CANDIDATE_FP,
        "candidate_text": CANDIDATE_TEXT,
        "reader_visible_context": [{
            "source_ref": "fixture:prior-public-paragraph",
            "text": "Synthetic previously disclosed context.",
        }],
        **READING_POSITION,
    }


def pressure_payload():
    return {
        "chapter_id": SUBJECT,
        "current_reading_order": 1,
        "author_request": "Prepare a bounded proposal for this synthetic fixture.",
        "sources": [{"source_ref": "fixture:brief", "text": "Synthetic brief."}],
    }


def realization_payload():
    return {
        "scene_id": "SCENE-CONTRACT-FIXTURE",
        "resolved_trajectory": {"events": [{
            "event_ref": "fixture:choice",
            "observable_action": "A participant leaves an invitation unanswered.",
        }]},
        "character_action_evidence": [{
            "character_id": "CHAR-CONTRACT-FIXTURE",
            "private_goal": "Synthetic private evidence for projection only.",
        }],
        "pov_boundary": {"visible_event_refs": ["fixture:choice"]},
    }


class ProseQualityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualification = make_qualified_receipt(CANDIDATE_FP, SUBJECT)

    def review_job(self, contract_id, payload=None):
        return make_contract_job(
            contract_id,
            SUBJECT,
            review_payload() if payload is None else payload,
            source_session_id="SES-CONTRACT-FIXTURE",
            qualification_receipt=self.qualification,
        )

    def test_registered_reviews_disclose_positive_value_and_evidence_requirements(self):
        for contract_id in REVIEW_CONTRACTS:
            with self.subTest(contract_id=contract_id):
                registry, contract = contract_for(contract_id)
                job = self.review_job(contract_id)
                self.assertEqual([], validate_registered_job(job))
                self.assertEqual("8", registry["version"])
                self.assertEqual(registry["version"], job["input"]["model_contract_version"])
                self.assertEqual(contract["purpose"], job["input"]["purpose"])
                self.assertEqual(contract["rubric"], job["rubric"])
                rubric = " ".join(job["rubric"]).lower()
                for requirement in (
                    "whole", "positive reading value", "safe-but-flat",
                    "locatable", "evidence_refs", "interchangeable speaking strategies",
                    "reader pressure", "prior judgments", "not measured reader retention",
                ):
                    self.assertIn(requirement, rubric)
                self.assertEqual(CANDIDATE_TEXT, job["input"]["payload"]["candidate_text"])

    def test_review_counterexamples_are_disclosed_without_mechanical_quotas(self):
        for contract_id in REVIEW_CONTRACTS:
            with self.subTest(contract_id=contract_id):
                rubric = " ".join(self.review_job(contract_id)["rubric"]).lower()
                for boundary in (
                    "quiet daily life", "specialized procedure", "restrained narration",
                    "can pass", "quotas of events", "dialogue", "emotion",
                    "body reactions", "cliffhangers", "stylistic preference"
                    if contract_id == "quality.production_review" else "stylistic dislike",
                ):
                    self.assertIn(boundary, rubric)

    def test_existing_review_inputs_remain_valid_without_optional_positioning(self):
        payload = {"candidate_fingerprint": CANDIDATE_FP, "candidate_text": CANDIDATE_TEXT}
        for contract_id in REVIEW_CONTRACTS:
            with self.subTest(contract_id=contract_id):
                _, contract = contract_for(contract_id)
                self.assertEqual({"candidate_fingerprint", "candidate_text"},
                                 set(contract["input_contract"]["required"]))
                self.assertEqual([], validate_registered_job(self.review_job(contract_id, payload)))

    def test_review_result_shape_does_not_encode_a_predetermined_verdict(self):
        for contract_id in REVIEW_CONTRACTS:
            _, contract = contract_for(contract_id)
            schema = contract["output_contract"]
            self.assertEqual({"confidence", "result", "report", "evidence_refs"}, set(schema["required"]))
            self.assertEqual(["pass", "fail"], schema["properties"]["result"]["enum"])
            for verdict in ("pass", "fail"):
                with self.subTest(contract_id=contract_id, verdict=verdict):
                    report = {
                        "confidence": 0.5,
                        "result": verdict,
                        "report": "Synthetic structural result; no model judgment executed.",
                        "evidence_refs": ["fixture:paragraph-1"],
                    }
                    self.assertEqual([], validate_typed_value(report, schema))
                    report["literary_score"] = 100
                    self.assertTrue(validate_typed_value(report, schema))

    def test_review_roles_and_write_boundaries_are_unchanged(self):
        for contract_id, role, independent in (
            ("reader.engagement_audit", "reader_engagement", False),
            ("quality.production_review", "semantic_independent", True),
        ):
            with self.subTest(contract_id=contract_id):
                _, contract = contract_for(contract_id)
                self.assertEqual([role], contract["release_roles"])
                self.assertIs(independent, contract["independent_gate"])
                for key in ("canon_write", "framework_behavior_write", "durable_user_taste_write"):
                    self.assertIs(False, contract["permissions"][key])

    def test_nested_creator_state_predictions_and_prior_judgments_are_rejected(self):
        blocked_keys = (
            "outline", "future_plan", "author_intent", "writer_reasoning",
            "private_character_state", "character_action_evidence",
            "prior_review", "prior_judgment", "prior_judgments", "judgment",
            "reader_assessment", "semantic_rule_assessment", "reader_pressure",
            "pressure_points", "expected_reward", "expected_rewards",
            "proposed_net_change", "next_chapter_pull", "qualification_receipt",
            "self_audit", "blocking_findings", "expected", "expected_verdict",
            "expected_codes", "gold", "gold_label", "prior_result",
        )
        for contract_id in REVIEW_CONTRACTS:
            for key in blocked_keys:
                with self.subTest(contract_id=contract_id, key=key):
                    payload = review_payload()
                    payload["reader_visible_context"][0]["metadata"] = {
                        "nested": [{key: "Synthetic forbidden stage evidence."}],
                    }
                    with self.assertRaisesRegex(ValueError, "forbidden fields"):
                        self.review_job(contract_id, payload)

    def test_forbidden_field_names_are_not_banned_words_in_manuscript_text(self):
        payload = review_payload()
        payload["candidate_text"] = "A fictional speaker mentions a prior judgment and an expected reward."
        payload["candidate_fingerprint"] = "sha256:" + hashlib.sha256(
            payload["candidate_text"].encode("utf-8")
        ).hexdigest()
        for contract_id in REVIEW_CONTRACTS:
            with self.subTest(contract_id=contract_id):
                _, contract = contract_for(contract_id)
                self.assertEqual([], validate_contract_input(contract_id, contract, payload))

    def test_independent_worker_does_not_receive_qualification_judgments(self):
        job = self.review_job("quality.production_review")
        self.assertIn("dispatch_proof", job)
        visible = worker_job_view(job)
        self.assertNotIn("dispatch_proof", visible)
        self.assertEqual(review_payload(), visible["input"]["payload"])
        self.assertNotIn("qualification_receipt", visible["input"]["payload"])

    def test_registered_rubric_tampering_and_version_relabeling_are_not_new_jobs(self):
        jobs = [self.review_job(contract_id) for contract_id in REVIEW_CONTRACTS]
        jobs.extend([
            make_contract_job("reader.pressure", SUBJECT, pressure_payload()),
            make_contract_job("scene.realization_project", SUBJECT, realization_payload()),
        ])
        for original in jobs:
            for change in ("rubric", "version"):
                with self.subTest(contract_id=original["input"]["model_contract_id"], change=change):
                    job = deepcopy(original)
                    if change == "rubric":
                        job["rubric"] = ["Synthetic substituted instruction."]
                    else:
                        job["input"]["model_contract_version"] = str(
                            int(job["input"]["model_contract_version"]) - 1
                        )
                    job["input_fingerprint"] = fingerprint_for(job)
                    self.assertNotEqual(original["input_fingerprint"], job["input_fingerprint"])
                    self.assertTrue(validate_registered_job(job))

    def test_pressure_accept_optional_positioning_with_the_review_field_types(self):
        registry, pressure = contract_for("reader.pressure")
        _, reader = contract_for("reader.engagement_audit")
        self.assertEqual("4", registry["version"])
        self.assertEqual({"chapter_id", "current_reading_order", "author_request", "sources"},
                         set(pressure["input_contract"]["required"]))
        for field in READING_POSITION:
            self.assertEqual(reader["input_contract"]["properties"][field],
                             pressure["input_contract"]["properties"][field])
        for positioning in ({}, READING_POSITION):
            with self.subTest(positioning=bool(positioning)):
                payload = {**pressure_payload(), **positioning}
                job = make_contract_job("reader.pressure", SUBJECT, payload)
                self.assertEqual([], validate_registered_job(job))
                self.assertEqual(payload, job["input"]["payload"])

    def test_positioning_changes_are_fingerprinted_and_invalid_types_fail(self):
        original = make_contract_job("reader.pressure", SUBJECT, {**pressure_payload(), **READING_POSITION})
        for field in READING_POSITION:
            with self.subTest(field=field):
                payload = {**pressure_payload(), **READING_POSITION}
                payload[field] = "high" if field == "reader_grip" else "Different explicit positioning."
                changed = make_contract_job("reader.pressure", SUBJECT, payload)
                self.assertNotEqual(original["input_fingerprint"], changed["input_fingerprint"])
                payload[field] = {} if field != "reader_grip" else "unsupported"
                with self.assertRaises(ValueError):
                    make_contract_job("reader.pressure", SUBJECT, payload)
        with self.assertRaisesRegex(ValueError, "unexpected field"):
            make_contract_job("reader.pressure", SUBJECT, {**pressure_payload(), "arbitrary_context": {}})

    def test_pressure_is_a_prediction_and_allows_no_discrete_pressure_points(self):
        job = make_contract_job("reader.pressure", SUBJECT, pressure_payload())
        rubric = " ".join(job["rubric"])
        for boundary in (
            "status=pass means only a usable pre-draft proposal",
            "Only a later reading of the actual candidate",
            "if no material delay cost is supported, say so",
            "an empty pressure_points array is valid",
            "Do not invent measurable retention rates",
        ):
            self.assertIn(boundary, rubric)
        report = {
            "confidence": 0.5,
            "status": "pass",
            "summary": "Synthetic shape check only; no realized reading value is asserted.",
            "pressure_points": [],
            "proposed_net_change": "",
            "next_chapter_pull": "",
        }
        self.assertEqual([], validate_typed_value(report, job["output_contract"]))

    def test_realization_projection_keeps_causal_and_private_boundaries_in_thin_strings(self):
        registry, contract = contract_for("scene.realization_project")
        job = make_contract_job("scene.realization_project", SUBJECT, realization_payload())
        self.assertEqual("6", registry["version"])
        self.assertEqual([], validate_registered_job(job))
        rubric = " ".join(job["rubric"])
        for boundary in (
            "Respect pov_boundary", "observable reactions", "writer-eligible",
            "listener-specific", "not a paragraph template", "compress routine",
            "Mark unresolved meaning as uncertain", "Do not prescribe quotas",
            "Explicit complete speech is valid",
        ):
            self.assertIn(boundary, rubric)
        schema = contract["output_contract"]
        self.assertEqual({"confidence", "scene_id", "interaction_trace", "writer_context"},
                         set(schema["required"]))
        for field in ("interaction_trace", "writer_context"):
            self.assertEqual("string", schema["properties"][field]["type"])
        projection = {
            "confidence": 0.5,
            "scene_id": "SCENE-CONTRACT-FIXTURE",
            "interaction_trace": "Synthetic observable action and response.",
            "writer_context": "Synthetic causal constraints, not a paragraph outline.",
        }
        self.assertEqual([], validate_typed_value(projection, schema))
        projection["private_character_state"] = {"secret": "Synthetic private field."}
        self.assertTrue(validate_typed_value(projection, schema))

    def test_editor_owns_flatness_repair_without_a_fixed_generation_mode(self):
        _, contract = contract_for("editor.repair_spec")
        payload = {
            "candidate_fingerprint": CANDIDATE_FP,
            "candidate_text": CANDIDATE_TEXT,
            "reader_assessment": {"report": "Synthetic evidence for contract packaging only."},
            "objective_envelope": {
                "fingerprint": CANDIDATE_FP,
                "objective_items": [{"source_ref": "fixture:objective"}],
                "must_preserve": ["Synthetic authorized causal constraint."],
            },
        }
        job = make_contract_job("editor.repair_spec", SUBJECT, payload)
        self.assertEqual([], validate_registered_job(job))
        rubric = " ".join(job["rubric"])
        for boundary in (
            "SAFE-BUT-FLAT", "realized reading-value failure", "costs that never bind",
            "Do not map a Reader label", "Preserve earned quiet",
            "without inventing unauthorized story facts",
        ):
            self.assertIn(boundary, rubric)
        self.assertEqual(["local_or_bounded_repair", "fresh_realization"],
                         contract["output_contract"]["properties"]["generation_mode"]["enum"])


if __name__ == "__main__":
    unittest.main()
