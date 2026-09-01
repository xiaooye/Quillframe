"""Synthetic transport tests only: never claim writing quality from these outputs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evals.outline_craft_ablation import (
    ARMS, STAGES, blind_batches, human_observation, load_suite, prepare_evaluation,
    record_generation, save_new, selector_job, validate_prepared, writer_job,
)
from harness.context_runtime import fingerprint
from production_runtime.semantic import RegisteredSemanticExecutor
import test_quillframe_production_runtime as fixtures


V2_SUITE = Path(__file__).resolve().parents[1] / "evals" / "fixtures" / "outline_craft_ablation_v2.json"


class CraftAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepare_evaluation(run_id="synthetic-craft-test", order_seed="synthetic-order",
                                         service_id="fixture-service", model_id="fixture-model", reasoning_effort="test-only",
                                         created_at="2026-08-28T00:00:00+00:00")
        fake = fixtures.FakeAgentRuntime()
        cls.bindings, cls.records, cls.results = {}, [], {}
        run = {"run_id": cls.prepared["run_id"], "session_id": "synthetic-selector", "task_mode": "DRAFT"}
        for case in cls.prepared["cases"]:
            cid = case["case_id"]
            binding = RegisteredSemanticExecutor(fake).execute_prepared(
                semantic_job=selector_job(cls.prepared, cid), run=run, service_id="fixture-service",
                model_preference="fixture-model", runtime_role="registered_scene_projection")
            cls.bindings[cid] = binding
            for arm in ARMS:
                for stage in STAGES:
                    job = writer_job(cls.prepared, cid, arm, stage, binding)
                    result = fake.run(job)
                    cls.results[(cid, arm, stage)] = result
                    host = {"host_run_ref": "synthetic-host", "request_ref": job.job_id, "evidence_class": "synthetic_test",
                            "packet_only_context": True, "reasoning_effort": "test-only"}
                    cls.records.append(record_generation(cls.prepared, case_id=cid, arm=arm, stage=stage,
                                                         projection_binding=binding, result=result, host_receipt=host))
        cls.fake_calls = len(fake.calls)

    def test_six_original_held_out_cases_cover_methods_without_gold(self):
        suite = load_suite()
        self.assertEqual(6, len(suite["cases"]))
        self.assertEqual({"confrontation", "relationship", "mystery", "everyday", "comedy", "wonder"},
                         {method for case in suite["cases"] for method in case["coverage_hypothesis"]})
        self.assertFalse(suite["provenance"]["human_quality_validated"])
        self.assertFalse(suite["provenance"]["derived_from_consumer"])
        self.assertNotIn("expected_result", json.dumps(suite))

    def test_v2_suite_is_fresh_original_and_freezes_current_registry_four(self):
        old = load_suite()
        suite = load_suite(V2_SUITE)
        self.assertEqual("2", suite["suite_version"])
        self.assertFalse(suite["provenance"]["prior_suite_case_overlap"])
        self.assertFalse(suite["provenance"]["presented_to_current_reviewer_before_freeze"])
        self.assertFalse({case["case_id"] for case in old["cases"]} & {case["case_id"] for case in suite["cases"]})
        self.assertEqual({"confrontation", "relationship", "mystery", "everyday", "comedy", "wonder"},
                         {method for case in suite["cases"] for method in case["coverage_hypothesis"]})
        plan = prepare_evaluation(run_id="synthetic-v2", order_seed="synthetic-v2-order",
                                  service_id="fixture-service", model_id="fixture-model",
                                  reasoning_effort="test-only", suite_path=V2_SUITE,
                                  created_at="2026-08-28T00:00:00+00:00")
        validate_prepared(plan)
        self.assertEqual("4", plan["craft_snapshot"]["registry_version"])
        self.assertEqual("4", plan["craft_snapshot"]["cards"][0]["version"])
        self.assertIn(V2_SUITE.name, plan["source_file_fingerprints"])

    def test_preparation_is_zero_dispatch_and_full_experiment_has_eighteen_slots(self):
        with patch("subprocess.run", side_effect=AssertionError("no host in preparation")), \
                patch.object(fixtures.FakeAgentRuntime, "run", side_effect=AssertionError("no model in preparation")):
            plan = prepare_evaluation(run_id="offline", order_seed="offline", service_id="not-live",
                                      model_id="not-live", reasoning_effort="not-live")
        self.assertEqual("prepared_not_executed", plan["status"])
        self.assertEqual(18, plan["planned_model_calls"])
        self.assertEqual(18, self.fake_calls)

    def test_selector_receives_plans_but_no_hidden_coverage_or_positive_examples(self):
        for case in self.prepared["cases"]:
            job = selector_job(self.prepared, case["case_id"])
            payload = job["input"]["payload"]
            self.assertEqual(3, len(payload["planning_context"]))
            self.assertNotIn("coverage_hypothesis", json.dumps(job))
            self.assertNotIn("order_seed", json.dumps(job))
            for card in payload["craft_catalog"]["cards"]:
                self.assertNotIn("text", card)

    def test_direct_writer_arms_share_every_visible_input_except_selected_craft(self):
        cid = self.prepared["cases"][0]["case_id"]
        jobs = [writer_job(self.prepared, cid, arm, STAGES[0], self.bindings[cid]) for arm in ARMS]
        self.assertEqual(jobs[0].instruction, jobs[1].instruction)
        self.assertEqual(jobs[0].budgets, jobs[1].budgets)
        self.assertEqual(jobs[0].model_preference, jobs[1].model_preference)
        self.assertNotEqual(jobs[0].session_id, jobs[1].session_id)
        guided = deepcopy(jobs[1].context)
        guide = guided[0]["writer_pack"].pop("craft_guidance")
        guided[0]["writer_pack"].pop("writer_pack_fingerprint")
        baseline = deepcopy(jobs[0].context)
        baseline[0]["writer_pack"].pop("writer_pack_fingerprint")
        self.assertEqual(baseline, guided)
        self.assertEqual(["core"], [row["card_id"] for row in guide["cards"]])
        for job in jobs:
            encoded = json.dumps(job.context)
            for excluded in (
                "planning_context", "craft_selection", "raw_draft",
                "upstream_artifacts", "frozen_stage_context",
            ):
                self.assertNotIn(excluded, encoded)

    def test_surface_is_direct_and_reuses_exact_projection_and_guidance(self):
        cid = self.prepared["cases"][0]["case_id"]
        binding = self.bindings[cid]
        baseline = writer_job(self.prepared, cid, ARMS[0], STAGES[0], binding)
        guided = writer_job(self.prepared, cid, ARMS[1], STAGES[0], binding)
        self.assertEqual("surface_realization", baseline.runtime_role)
        self.assertEqual({"text", "fiction_writing"}, guided.required_model_capabilities)
        pack = guided.context[0]["writer_pack"]
        self.assertIn("scene_contract", pack)
        self.assertIn("director_note", pack)
        self.assertIn("author_objectives", pack)
        self.assertEqual(
            binding["binding_fingerprint"],
            pack["selection"]["source_binding_fingerprint"],
        )
        self.assertIn("craft_guidance", pack)
        self.assertNotIn("craft_guidance", baseline.context[0]["writer_pack"])
        self.assertNotIn("raw_draft", json.dumps(guided.context))

    def test_prepared_and_selection_tampering_is_not_repaired(self):
        plan = deepcopy(self.prepared)
        plan["craft_snapshot"]["cards"][0]["text"] += " changed"
        with self.assertRaises(ValueError):
            validate_prepared(plan)
        cid = self.prepared["cases"][0]["case_id"]
        damaged = deepcopy(self.bindings[cid])
        damaged["result"]["judgment"]["writer_context"] = "changed"
        with self.assertRaisesRegex(ValueError, "invalid selection result|binding changed"):
            writer_job(self.prepared, cid, ARMS[0], STAGES[0], damaged)

    def test_malformed_or_ambiguous_json_is_not_repaired_into_a_sample(self):
        cid = self.prepared["cases"][0]["case_id"]
        for text in ('{}', '```json\n{}\n```', 'NaN',
                     '{"status":"fail","status":"pass","text":"ambiguous","summary":"fixture","findings":[]}'):
            result = deepcopy(self.results[(cid, ARMS[0], STAGES[0])])
            result.final_text = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                record_generation(self.prepared, case_id=cid, arm=ARMS[0], stage=STAGES[0],
                                  projection_binding=self.bindings[cid], result=result,
                                  host_receipt=self.records[0]["host_receipt"])

    def test_blind_export_is_three_batches_of_two_with_closed_prose_projection(self):
        batches = blind_batches(self.prepared, selection_bindings=self.bindings, records=self.records, allow_synthetic=True)
        self.assertEqual([2, 2, 2], [len(batch["pairs"]) for batch in batches])
        self.assertEqual(6, len({pair["pair_id"] for batch in batches for pair in batch["pairs"]}))
        for batch in batches:
            self.assertTrue(batch["synthetic_test_only"])
            for pair in batch["pairs"]:
                self.assertEqual({"pair_id", "reader_context", "A", "B"}, set(pair))
                self.assertIsInstance(pair["A"], str)
                self.assertNotIn("raw_draft", json.dumps(pair))
        encoded = json.dumps(batches)
        for excluded in ("craft_selection", "craft_guidance", "baseline", "outline_driven", "coverage_hypothesis",
                         "order_seed", "planning_context", "host_receipt", "fixture-model"):
            self.assertNotIn(excluded, encoded)

    def test_incomplete_replayed_or_synthetic_records_cannot_be_live_blind_evidence(self):
        with self.assertRaisesRegex(ValueError, "synthetic outputs"):
            blind_batches(self.prepared, selection_bindings=self.bindings, records=self.records)
        with self.assertRaisesRegex(ValueError, "complete six-pair"):
            blind_batches(self.prepared, selection_bindings=self.bindings, records=self.records[:-1], allow_synthetic=True)
        repeated = self.records[:-1] + self.records[:1]
        with self.assertRaisesRegex(ValueError, "duplicate generation"):
            blind_batches(self.prepared, selection_bindings=self.bindings, records=repeated, allow_synthetic=True)
        changed = deepcopy(self.records)
        changed[0]["job"]["context"][0]["hidden_label"] = "tamper"
        changed[0]["record_fingerprint"] = fingerprint({k: v for k, v in changed[0].items() if k != "record_fingerprint"})
        with self.assertRaisesRegex(ValueError, "record changed"):
            blind_batches(self.prepared, selection_bindings=self.bindings, records=changed, allow_synthetic=True)

    def test_human_ties_and_both_bad_are_evidence_not_promotion(self):
        batch = blind_batches(self.prepared, selection_bindings=self.bindings, records=self.records, allow_synthetic=True)[0]
        for choice in ("A", "B", "tie", "both_bad", "insufficient_evidence"):
            observation = human_observation(batch, pair_id=batch["pairs"][0]["pair_id"], choice=choice,
                                             reason="Synthetic human-shape fixture, not a real reading.", reviewer_ref="synthetic-test")
            self.assertEqual(choice, observation["choice"])
            self.assertFalse(observation["authority"])
            self.assertFalse(observation["taste_activation"])
            self.assertFalse(observation["framework_promotion"])
            self.assertFalse(observation["blind_eligible"])
        exposed = human_observation({**batch, "synthetic_test_only": False}, pair_id=batch["pairs"][0]["pair_id"],
                                     choice="tie", reason="Fixture.", reviewer_ref="synthetic-test", prior_exposure=True)
        self.assertFalse(exposed["blind_eligible"])

    def test_preparation_save_is_append_only(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "private" / "prepared.json"
            save_new(target, self.prepared)
            self.assertEqual(self.prepared, json.loads(target.read_text(encoding="utf-8")))
            with self.assertRaises(FileExistsError):
                save_new(target, self.prepared)


if __name__ == "__main__":
    unittest.main()
