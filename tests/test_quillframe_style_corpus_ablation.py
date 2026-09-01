"""Purely synthetic transport tests; no fixture is literary-quality evidence."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from evals.style_corpus_ablation import (
    ARMS,
    BLIND_DIMENSIONS,
    BLIND_PAIR_CONTRACT,
    PAIRINGS,
    SEMANTIC_LEAKAGE_CONTRACT,
    StyleCorpusAblationError,
    blind_reader_queue,
    canonical,
    consume_evidence,
    fingerprint,
    load_suite,
    prepare_evaluation,
    semantic_leakage_queue,
    text_fingerprint,
    validate_prepared,
)
from harness.semantic_workers.semantic_worker_router import (
    load_contract_catalog,
    make_contract_job,
    validate_result,
)


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = "2026-08-29T00:00:00+00:00"


def _reseal(value: dict, field: str) -> None:
    value[field] = fingerprint({key: item for key, item in value.items() if key != field})


def _semantic_result(job: dict, judgment: dict, invocation: str) -> dict:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "synthetic_test",
            "model_or_reviewer": "synthetic-contract-fixture",
        },
        "judgment": judgment,
        "proposals": [],
        "errors": [],
        "execution": {
            "source_session_id": job["execution"]["source_session_id"],
            "worker_session_id": invocation,
            "handoff_id": job["execution"]["handoff_id"],
            "attempt_id": invocation + ":attempt",
        },
    }


def _blind_judgment(
    row: dict,
    preference: str = "tie",
    dimension_leanings: dict[str, str] | None = None,
) -> dict:
    leanings = dimension_leanings or {dimension: "tie" for dimension in BLIND_DIMENSIONS}
    return {
        "confidence": 0.73,
        "comparison_id": row["comparison_id"],
        "preference": preference,
        "dimensions": {
            dimension: {
                "leaning": leanings[dimension],
                "observation": f"Synthetic bounded {dimension} observation; not a quality assertion.",
            }
            for dimension in BLIND_DIMENSIONS
        },
        "blindness_concerns": [],
        "report": "Synthetic result validates transport and binding only.",
    }


def _leak_judgment(row: dict, status: str = "clear", reference_id: str | None = None) -> dict:
    findings = []
    if reference_id is not None:
        findings.append(
            {
                "reference_id": reference_id,
                "risk": "material" if status == "blocked" else "low",
                "reason": "Synthetic semantic-risk record for schema validation.",
            }
        )
    return {
        "confidence": 0.68,
        "review_id": row["review_id"],
        "status": status,
        "findings": findings,
        "report": "Synthetic result validates the independent leakage receipt shape only.",
    }


class StyleCorpusAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = load_suite()
        cls.plan = prepare_evaluation(
            cls.suite,
            run_id="SYNTHETIC-STYLE-ABLATION",
            order_seed="SYNTHETIC-ORDER-SEED",
            created_at=FIXED_TIME,
        )

    def test_preparation_is_deterministic_and_zero_model(self) -> None:
        again = prepare_evaluation(
            deepcopy(self.suite),
            run_id="SYNTHETIC-STYLE-ABLATION",
            order_seed="SYNTHETIC-ORDER-SEED",
            created_at=FIXED_TIME,
        )
        self.assertEqual(self.plan, again)
        self.assertFalse(self.plan["model_execution"])
        self.assertEqual("PENDING_MODEL", self.plan["semantic_status"])
        self.assertTrue(self.plan["test_only"])

    def test_three_arms_expand_to_all_pairs_repeats_and_swapped_orders(self) -> None:
        self.assertEqual(
            len(self.suite["cases"]) * len(PAIRINGS) * self.suite["repeat_count"] * 2,
            len(self.plan["blind_presentations"]),
        )
        grouped: dict[tuple[str, tuple[str, ...], int], list[dict]] = {}
        for row in self.plan["blind_presentations"]:
            key = (row["case_id"], tuple(row["pair_arms"]), row["repeat_index"])
            grouped.setdefault(key, []).append(row)
        self.assertEqual(len(self.suite["cases"]) * len(PAIRINGS) * 2, len(grouped))
        for rows in grouped.values():
            self.assertEqual({"forward", "swapped"}, {row["orientation"] for row in rows})
            by_orientation = {row["orientation"]: row for row in rows}
            forward = by_orientation["forward"]["job"]["input"]["payload"]
            swapped = by_orientation["swapped"]["job"]["input"]["payload"]
            self.assertEqual(forward["sample_a"]["text"], swapped["sample_b"]["text"])
            self.assertEqual(forward["sample_b"]["text"], swapped["sample_a"]["text"])
            self.assertNotEqual(rows[0]["comparison_id"], rows[1]["comparison_id"])

    def test_task_context_and_randomness_are_frozen_once_for_all_three_arms(self) -> None:
        cases = {row["case_id"]: row for row in self.plan["private_cases"]}
        for case_id, case in cases.items():
            generation = case["generation_inputs"]
            self.assertEqual(fingerprint(generation["task"]), case["task_fingerprint"])
            self.assertEqual(fingerprint(generation["context"]), case["context_fingerprint"])
            self.assertEqual(fingerprint(generation["randomness"]), case["randomness_fingerprint"])
            self.assertEqual(fingerprint(generation), case["generation_binding_fingerprint"])
            rows = [row for row in self.plan["blind_presentations"] if row["case_id"] == case_id]
            self.assertTrue(rows)
            for row in rows:
                payload = row["job"]["input"]["payload"]
                self.assertEqual(generation["task"], payload["evaluation_task"])
                self.assertEqual(generation["context"], payload["evaluation_context"])

    def test_blind_payload_is_closed_and_has_no_condition_or_origin_labels(self) -> None:
        queue = blind_reader_queue(self.plan)
        self.assertTrue(queue["blind"])
        self.assertEqual(len(self.plan["blind_presentations"]), len(queue["jobs"]))
        for job in queue["jobs"]:
            payload = job["input"]["payload"]
            self.assertEqual(
                {
                    "comparison_id",
                    "evaluation_task",
                    "evaluation_context",
                    "scene_function",
                    "sample_a",
                    "sample_b",
                    "criteria",
                },
                set(payload),
            )
            encoded = json.dumps(payload, ensure_ascii=False).casefold()
            for label in (*ARMS, "treatment_label", "style_label", "source_label"):
                self.assertNotIn(label.casefold(), encoded)
            self.assertEqual({"sample_id", "text"}, set(payload["sample_a"]))
            self.assertEqual({"sample_id", "text"}, set(payload["sample_b"]))
        private = json.dumps(self.plan, ensure_ascii=False)
        self.assertIn("current_craft_v4", private)
        self.assertNotIn("private_mapping", json.dumps(queue, ensure_ascii=False))

    def test_candidate_is_exact_utf8_text_and_craft_binding_is_canonical(self) -> None:
        case_by_id = {case["case_id"]: case for case in self.suite["cases"]}
        for private in self.plan["private_cases"]:
            original = case_by_id[private["case_id"]]
            for arm in ARMS:
                binding = private["arms"][arm]
                text = original["arms"][arm]["text"]
                self.assertEqual(
                    "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    binding["candidate_fingerprint"],
                )
                self.assertEqual(fingerprint(binding["craft_binding"]), binding["craft_fingerprint"])
                self.assertEqual(text_fingerprint(text), binding["candidate_fingerprint"])

        changed = deepcopy(self.plan)
        changed["private_cases"][0]["arms"]["baseline"]["candidate_fingerprint"] = text_fingerprint("changed")
        _reseal(changed, "plan_fingerprint")
        with self.assertRaisesRegex(StyleCorpusAblationError, "presented candidate fingerprint"):
            validate_prepared(changed)

        changed = deepcopy(self.plan)
        changed["private_cases"][0]["arms"]["baseline"]["craft_binding"]["version"] = "tampered"
        _reseal(changed, "plan_fingerprint")
        with self.assertRaisesRegex(StyleCorpusAblationError, "craft fingerprint"):
            validate_prepared(changed)

    def test_leave_one_work_out_and_scene_function_holdout_are_exact(self) -> None:
        works = set(self.suite["work_universe"])
        scenes = set(self.suite["scene_function_universe"])
        heldout = []
        for case in self.plan["private_cases"]:
            binding = case["arms"]["corpus_candidate"]["craft_binding"]
            heldout.append(case["heldout_work_id"])
            self.assertEqual(works - {case["heldout_work_id"]}, set(binding["evidence_work_ids"]))
            self.assertNotIn(case["heldout_work_id"], binding["evidence_work_ids"])
            self.assertEqual(
                scenes - {case["scene_function"]}, set(binding["training_scene_functions"])
            )
            self.assertNotIn(case["scene_function"], binding["training_scene_functions"])
        self.assertCountEqual(self.suite["work_universe"], heldout)

        bad = deepcopy(self.suite)
        corpus = bad["cases"][0]["arms"]["corpus_candidate"]["craft_binding"]
        corpus["evidence_work_ids"].append(bad["cases"][0]["heldout_work_id"])
        with self.assertRaisesRegex(StyleCorpusAblationError, "leave-one-work-out"):
            prepare_evaluation(bad, run_id="BAD-LOO", order_seed="bad", created_at=FIXED_TIME)

        bad = deepcopy(self.suite)
        corpus = bad["cases"][0]["arms"]["corpus_candidate"]["craft_binding"]
        corpus["training_scene_functions"].append(bad["cases"][0]["scene_function"])
        with self.assertRaisesRegex(StyleCorpusAblationError, "scene-function holdout"):
            prepare_evaluation(bad, run_id="BAD-SCENE", order_seed="bad", created_at=FIXED_TIME)

    def test_body_appearance_and_general_profile_are_ordinary_blind_material(self) -> None:
        body_rows = [
            row for row in self.plan["blind_presentations"] if row["case_id"] == "CASE-BODY"
        ]
        self.assertTrue(body_rows)
        payloads = [row["job"]["input"]["payload"] for row in body_rows]
        self.assertTrue(any("巨乳" in json.dumps(payload, ensure_ascii=False) for payload in payloads))
        for payload in payloads:
            self.assertEqual("general", payload["evaluation_context"]["content_profile"])
            self.assertEqual("body_appearance", payload["scene_function"])
            self.assertNotIn("quarantine", json.dumps(payload, ensure_ascii=False).casefold())

    def test_registered_contracts_are_independent_and_catalogued(self) -> None:
        catalog = load_contract_catalog()
        learning = next(pack for pack in catalog["packs"] if pack["id"] == "learning")
        self.assertEqual("19", catalog["version"])
        self.assertIn(BLIND_PAIR_CONTRACT, learning["contracts"])
        self.assertIn(SEMANTIC_LEAKAGE_CONTRACT, learning["contracts"])
        self.assertIn("corpus.provenance.public_abstraction", learning["contracts"])
        self.assertIn("learning.style_axis_reconcile", learning["contracts"])
        for row in self.plan["blind_presentations"]:
            self.assertTrue(row["job"]["provenance"]["independent_gate"])
            self.assertEqual(BLIND_PAIR_CONTRACT, row["job"]["provenance"]["model_contract_id"])
        for row in self.plan["leakage_reviews"]:
            self.assertTrue(row["job"]["provenance"]["independent_gate"])
            self.assertEqual(
                SEMANTIC_LEAKAGE_CONTRACT, row["job"]["provenance"]["model_contract_id"]
            )

        blind_payload = self.plan["blind_presentations"][0]["job"]["input"]["payload"]
        blind_job = make_contract_job(BLIND_PAIR_CONTRACT, "CONTRACT-CHECK", blind_payload)
        blind_result = _semantic_result(
            blind_job,
            {**_blind_judgment(self.plan["blind_presentations"][0]), "comparison_id": blind_payload["comparison_id"]},
            "contract-check-blind",
        )
        self.assertEqual([], validate_result(blind_job, blind_result))
        missing_dimension = deepcopy(blind_result)
        missing_dimension["judgment"]["dimensions"].pop("originality")
        self.assertTrue(
            any("missing required field originality" in error for error in validate_result(blind_job, missing_dimension))
        )
        unknown_dimension = deepcopy(blind_result)
        unknown_dimension["judgment"]["dimensions"]["overall_reading"] = {
            "leaning": "tie",
            "observation": "A totalizing ninth reader dimension is intentionally forbidden.",
        }
        self.assertTrue(
            any("unexpected field overall_reading" in error for error in validate_result(blind_job, unknown_dimension))
        )

        leak_payload = self.plan["leakage_reviews"][0]["job"]["input"]["payload"]
        leak_job = make_contract_job(SEMANTIC_LEAKAGE_CONTRACT, "LEAK-CHECK", leak_payload)
        leak_result = _semantic_result(
            leak_job,
            {**_leak_judgment(self.plan["leakage_reviews"][0]), "review_id": leak_payload["review_id"]},
            "contract-check-leak",
        )
        self.assertEqual([], validate_result(leak_job, leak_result))

    def test_public_abstraction_provenance_contract_is_closed_independent_and_non_authorizing(self) -> None:
        value = "sha256:" + "a" * 64
        payload = {
            "completion_fingerprint": value,
            "candidate_fingerprint": "sha256:" + "b" * 64,
            "identity_policy_fingerprint": "sha256:" + "c" * 64,
            "provenance_fingerprint": "sha256:" + "d" * 64,
            "declared_rights_class": "analysis_only",
            "declared_rights_basis": "Caller declares lawful analysis and public abstraction only.",
            "source_dependency_current": True,
            "release_target": "public_general_style_atlas",
        }
        job = make_contract_job(
            "corpus.provenance.public_abstraction",
            "PROVENANCE-CONTRACT-CHECK",
            payload,
            source_session_id="PROVENANCE-SOURCE",
            handoff_id="PROVENANCE-HANDOFF",
        )
        self.assertTrue(job["provenance"]["independent_gate"])
        self.assertEqual("evidence_only", job["permissions"]["allowed_result_scope"])
        self.assertFalse(job["permissions"]["canon_write"])
        self.assertFalse(job["permissions"]["framework_behavior_write"])
        self.assertFalse(job["permissions"]["durable_user_taste_write"])
        self.assertEqual(set(payload), set(job["input"]["payload"]))
        encoded = json.dumps(job["input"]["payload"], ensure_ascii=False).casefold()
        for forbidden in ("source_title", "local_path", "source_text", "passage"):
            self.assertNotIn(forbidden, encoded)
        judgment = {
            "confidence": 0.76,
            "status": "pass",
            "findings": [
                {
                    "binding": "rights",
                    "severity": "information",
                    "observation": "The bounded declaration is consistent with abstraction-only review.",
                }
            ],
            "report": "Evidence-only synthetic contract validation.",
            "authority_scope": "evidence_only",
            "legal_safety_claim": False,
        }
        result = _semantic_result(job, judgment, "provenance-independent-invocation")
        self.assertEqual([], validate_result(job, result))
        bad = {**payload, "source_title": "forbidden"}
        with self.assertRaises(ValueError):
            make_contract_job(
                "corpus.provenance.public_abstraction",
                "PROVENANCE-BAD",
                bad,
            )

    def test_learning_v4_and_v5_are_recorded_before_live_v6_contract(self) -> None:
        history_root = ROOT / "harness" / "semantic_workers" / "contracts" / "history"
        index = json.loads((history_root / "index.json").read_text(encoding="utf-8"))
        entry = next(
            row for row in index["entries"] if row["pack_id"] == "learning" and row["version"] == "4"
        )
        archived_path = history_root / entry["path"]
        digest = hashlib.sha256(archived_path.read_bytes()).hexdigest()
        self.assertEqual(entry["sha256"], digest)
        archived = json.loads(archived_path.read_text(encoding="utf-8"))
        live = json.loads(
            (ROOT / "harness" / "semantic_workers" / "contracts" / "learning.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("4", archived["version"])
        self.assertEqual("6", live["version"])
        self.assertIn("axis_observations", archived["contracts"][BLIND_PAIR_CONTRACT]["output_contract"]["properties"])
        self.assertIn("dimensions", live["contracts"][BLIND_PAIR_CONTRACT]["output_contract"]["properties"])
        v5_entry = next(
            row for row in index["entries"]
            if row["pack_id"] == "learning" and row["version"] == "5"
        )
        v5_path = history_root / v5_entry["path"]
        self.assertEqual(v5_entry["sha256"], hashlib.sha256(v5_path.read_bytes()).hexdigest())
        v5 = json.loads(v5_path.read_text(encoding="utf-8"))
        self.assertEqual("5", v5["version"])
        self.assertNotIn("learning.style_axis_reconcile", v5["contracts"])
        self.assertTrue(v5["contracts"]["learning.style_claim_verify"]["independent_gate"])
        self.assertIn("learning.style_axis_reconcile", live["contracts"])
        self.assertFalse(live["contracts"]["learning.style_claim_verify"]["independent_gate"])

    def test_missing_model_results_remain_pending_without_a_fabricated_pass(self) -> None:
        evidence = consume_evidence(self.plan, blind_results=[], leakage_results=[])
        self.assertEqual("PENDING_MODEL", evidence["status"])
        self.assertEqual("PENDING_MODEL", evidence["blind_status"])
        self.assertEqual("PENDING_MODEL", evidence["leakage_status"])
        self.assertFalse(evidence["semantic_results_supplied"])
        self.assertNotIn("literary_quality_score", evidence)
        self.assertNotIn("automatic_winner", evidence)
        self.assertFalse(evidence["aggregation_policy"]["dimension_weights_applied"])
        self.assertFalse(evidence["aggregation_policy"]["total_score_computed"])
        self.assertFalse(evidence["aggregation_policy"]["winner_selected"])
        self.assertTrue(evidence["aggregation_policy"]["leakage_is_independent_gate"])
        self.assertNotIn('"PASS"', json.dumps(evidence, ensure_ascii=False))
        self.assertTrue(all(value is False for value in evidence["authority"].values()))

    def test_synthetic_complete_receipts_validate_but_never_become_live_evidence(self) -> None:
        blind_results = []
        for index, row in enumerate(self.plan["blind_presentations"]):
            preference = ("a", "b", "tie", "both_bad", "insufficient_evidence")[index % 5]
            dimension_leanings = {
                dimension: ("a", "b", "tie", "unclear")[(index + offset) % 4]
                for offset, dimension in enumerate(BLIND_DIMENSIONS)
            }
            blind_results.append(
                _semantic_result(
                    row["job"],
                    _blind_judgment(row, preference, dimension_leanings),
                    f"blind-invocation-{index}",
                )
            )
        leakage_results = [
            _semantic_result(row["job"], _leak_judgment(row), f"leak-invocation-{index}")
            for index, row in enumerate(self.plan["leakage_reviews"])
        ]
        with self.assertRaisesRegex(StyleCorpusAblationError, "test-only"):
            consume_evidence(
                self.plan,
                blind_results=blind_results,
                leakage_results=leakage_results,
            )
        evidence = consume_evidence(
            self.plan,
            blind_results=blind_results,
            leakage_results=leakage_results,
            allow_synthetic=True,
        )
        self.assertEqual("SYNTHETIC_VALIDATION_ONLY", evidence["status"])
        self.assertEqual("SEMANTIC_EVIDENCE_READY", evidence["blind_status"])
        self.assertEqual("SEMANTIC_EVIDENCE_READY", evidence["leakage_status"])
        self.assertEqual(len(self.suite["cases"]) * len(PAIRINGS), len(evidence["pair_summaries"]))
        for summary in evidence["pair_summaries"]:
            self.assertEqual(4, summary["pair_preference"]["observed"])
            self.assertEqual(set(BLIND_DIMENSIONS), set(summary["dimensions"]))
            self.assertTrue(all(value["observed"] == 4 for value in summary["dimensions"].values()))
            self.assertNotIn("score", json.dumps(summary).casefold())
            self.assertNotIn("winner", json.dumps(summary).casefold())
        for observation in evidence["blind_observations"]:
            self.assertEqual(set(BLIND_DIMENSIONS), set(observation["dimensions"]))
            for item in observation["dimensions"].values():
                self.assertIn(item["leaning"], {*ARMS, "tie", "unclear"})
                self.assertGreaterEqual(len(item["observation"]), 1)
                self.assertLessEqual(len(item["observation"]), 800)
        self.assertFalse(evidence["aggregation_policy"]["dimension_weights_applied"])
        self.assertFalse(evidence["aggregation_policy"]["total_score_computed"])
        self.assertFalse(evidence["aggregation_policy"]["winner_selected"])
        self.assertFalse(evidence["authority"]["release"])
        self.assertFalse(evidence["authority"]["framework_promotion"])

    def test_repeated_or_unbound_independent_invocations_are_rejected(self) -> None:
        rows = self.plan["blind_presentations"][:2]
        results = [
            _semantic_result(row["job"], _blind_judgment(row), "reused-invocation") for row in rows
        ]
        with self.assertRaisesRegex(StyleCorpusAblationError, "invocation reused"):
            consume_evidence(
                self.plan,
                blind_results=results,
                leakage_results=[],
                allow_synthetic=True,
            )

        result = _semantic_result(rows[0]["job"], _blind_judgment(rows[0]), "bound-invocation")
        result["judgment"]["comparison_id"] = "CMP-WRONG"
        with self.assertRaises(StyleCorpusAblationError):
            consume_evidence(
                self.plan,
                blind_results=[result],
                leakage_results=[],
                allow_synthetic=True,
            )

    def test_local_and_semantic_leakage_are_separate_non_authorizing_gates(self) -> None:
        queue = semantic_leakage_queue(self.plan)
        self.assertEqual(len(self.suite["cases"]), len(queue["jobs"]))
        self.assertFalse(queue["release_authority"])
        self.assertTrue(all(row["local_report"]["local_status"] == "pass" for row in self.plan["leakage_reviews"]))

        clear_results = [
            _semantic_result(row["job"], _leak_judgment(row), f"clear-{index}")
            for index, row in enumerate(self.plan["leakage_reviews"])
        ]
        evidence = consume_evidence(
            self.plan,
            blind_results=[],
            leakage_results=clear_results,
            allow_synthetic=True,
        )
        self.assertEqual("SEMANTIC_EVIDENCE_READY", evidence["leakage_status"])
        self.assertEqual("SYNTHETIC_VALIDATION_ONLY", evidence["status"])
        self.assertFalse(evidence["authority"]["release"])

        blocked = deepcopy(clear_results)
        blocked[0]["judgment"] = _leak_judgment(
            self.plan["leakage_reviews"][0], status="blocked", reference_id="WORK-A"
        )
        evidence = consume_evidence(
            self.plan,
            blind_results=[],
            leakage_results=blocked,
            allow_synthetic=True,
        )
        self.assertEqual("BLOCKED_SEMANTIC", evidence["leakage_status"])
        self.assertFalse(evidence["authority"]["release"])

    def test_local_overlap_can_block_without_claiming_semantic_review(self) -> None:
        suite = deepcopy(self.suite)
        suite["cases"][0]["arms"]["corpus_candidate"]["text"] = suite["reference_samples"][0]["text"]
        plan = prepare_evaluation(
            suite,
            run_id="SYNTHETIC-LOCAL-BLOCK",
            order_seed="local-block",
            created_at=FIXED_TIME,
        )
        local = next(row for row in plan["leakage_reviews"] if row["case_id"] == "CASE-DIALOGUE")
        self.assertEqual("blocked", local["local_report"]["local_status"])
        self.assertFalse(local["local_report"]["release_ready"])
        self.assertFalse(local["local_report"]["semantic_check"]["performed"])
        evidence = consume_evidence(plan, blind_results=[], leakage_results=[])
        self.assertEqual("BLOCKED_LOCAL", evidence["leakage_status"])
        self.assertEqual("LEAKAGE_BLOCKED", evidence["status"])
        self.assertFalse(evidence["authority"]["release"])

    def test_semantic_leakage_citations_are_bound_to_supplied_reference_ids(self) -> None:
        row = self.plan["leakage_reviews"][0]
        result = _semantic_result(
            row["job"],
            _leak_judgment(row, status="blocked", reference_id="UNKNOWN-REFERENCE"),
            "unknown-reference",
        )
        with self.assertRaisesRegex(StyleCorpusAblationError, "unknown reference"):
            consume_evidence(
                self.plan,
                blind_results=[],
                leakage_results=[result],
                allow_synthetic=True,
            )

    def test_fixture_is_original_synthetic_without_gold_or_model_claims(self) -> None:
        provenance = self.suite["provenance"]
        self.assertEqual("synthetic_test", provenance["evidence_class"])
        self.assertEqual("original_synthetic_assistant_authored", provenance["authorship"])
        self.assertFalse(provenance["derived_from_external_prose"])
        self.assertFalse(provenance["derived_from_consumer"])
        self.assertFalse(provenance["human_quality_validated"])
        self.assertFalse(provenance["model_quality_validated"])
        self.assertEqual(8, len(self.suite["reading_criteria"]))
        self.assertEqual(
            set(BLIND_DIMENSIONS),
            {criterion.split("：", 1)[0] for criterion in self.suite["reading_criteria"]},
        )
        encoded = json.dumps(self.suite, ensure_ascii=False).casefold()
        for forbidden in ("expected_winner", "gold_label", "model_pass", "quality_pass"):
            self.assertNotIn(forbidden, encoded)

    def test_canonical_fingerprint_is_order_stable_but_text_fingerprint_is_exact(self) -> None:
        self.assertEqual(fingerprint({"a": 1, "b": 2}), fingerprint({"b": 2, "a": 1}))
        self.assertEqual(canonical({"b": 2, "a": 1}), canonical({"a": 1, "b": 2}))
        self.assertNotEqual(text_fingerprint("line\n"), text_fingerprint("line\r\n"))


if __name__ == "__main__":
    unittest.main()
