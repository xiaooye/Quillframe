from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from harness.context_runtime import (
    MANDATORY_PRODUCTION_MECHANISMS,
    build_candidate_pool,
    build_semantic_index_plan,
    build_inspector_projection,
    derive_semantic_profile,
    fingerprint,
    freeze_context,
    normalize_profile_override,
    pack_budget,
    project_character_context,
    profile_status,
    stage_context,
    validate_adaptive_graph,
    validate_context_decision,
    validate_context_query,
    validate_freeze,
)
from persistence.context_repository import ContextRepository
from persistence.quillframe_sqlite import QuillframeStore


class ContextRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = QuillframeStore(self.root)
        self.store.create_project("PCTX", "Context test", "en")
        with self.store.open_project("PCTX") as conn:
            conn.execute("INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES(?,?,?,?,?)", ("SES-CTX", "running", 1, "2026-08-18T00:00:00Z", "2026-08-18T00:00:00Z"))
            conn.execute("INSERT INTO runs(run_id,session_id,task_mode,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", ("RUN-CTX", "SES-CTX", "SYSTEM-IMPROVE", "running", fingerprint("request"), "2026-08-18T00:00:00Z", "2026-08-18T00:00:00Z"))
            conn.commit()
        self.repo = ContextRepository(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def _profile(self, object_id="CHAR-1", object_type="character", text="source", *, stages=None, tokens=10, override=None, source_fp=None):
        source_fp = source_fp or fingerprint(text)
        return derive_semantic_profile(
            {"object_id": object_id, "object_type": object_type, "source_fingerprint": source_fp, "text": text},
            {
                "description": f"semantic {object_id}",
                "trigger_when": f"when {object_id} matters",
                "estimated_tokens": tokens,
                "semantic_tags": [object_type],
                "stage_affinities": stages or [],
            },
            generator_provenance={"kind": "semantic_job", "job_fingerprint": fingerprint(object_id + source_fp)},
            manual_override=override,
            generated_at="2026-08-18T00:00:00Z",
        )

    def _item(self, object_id="CHAR-1", object_type="character", *, authority="accepted", lifecycle=None, domain=None, stages=None, tokens=10, required=False, status=None, source_fp=None, profile=None):
        source_fp = source_fp or fingerprint(object_id + ":source")
        profile = profile or self._profile(object_id, object_type if object_type in {
            "character", "relationship", "world_fact", "location", "timeline_event", "story_node", "plan", "research", "accepted_manuscript", "previous_scene", "previous_chapter", "canon_claim", "corpus_evidence", "review_artifact", "character_knowledge", "candidate", "runtime_state", "derived_memory"
        } else "runtime_state", stages=stages, tokens=tokens, source_fp=source_fp)
        return {
            "object_id": object_id,
            "object_type": object_type,
            "authority": authority,
            "lifecycle": lifecycle or authority,
            "domain": domain or object_type,
            "source_fingerprint": source_fp,
            "stages": stages or ["draft", "character_simulation", "continuity", "independent_review", "research"],
            "required_for_grounding": required,
            "status": status,
            "profile": profile,
        }

    def _greenlight(self, stage="draft", items=None, selections=None, budget=100):
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id=stage, items=items or [self._item(stages=[stage])])
        if selections is None:
            selections = [{"profile_id": pool["eligible"][0]["profile_id"], "stage_id": stage, "priority": 1, "reason_code": "relevant", "reason": "needed for this stage"}]
        decision = validate_context_decision(pool, {"selections": selections}, selector={"kind": "agent", "id": "selector-test"})
        green = pack_budget(decision, hard_budget=budget) if decision["proceed"] else None
        return pool, decision, green

    # 1
    def test_semantic_profile_generation_is_derived_and_fingerprint_bound(self):
        source_fp = fingerprint("character-source")
        p = self._profile(source_fp=source_fp)
        self.assertEqual(p["source_fingerprint"], source_fp)
        self.assertFalse(p["authority"])
        self.assertTrue(p["description"])
        self.assertTrue(p["trigger_when"])
        self.assertGreater(p["estimated_tokens"], 0)
        self.assertTrue(p["profile_id"].startswith("SCP-"))
        self.assertTrue(p["profile_fingerprint"].startswith("sha256:"))

    # 2
    def test_source_fingerprint_change_marks_old_profile_stale(self):
        old_fp, new_fp = fingerprint("old"), fingerprint("new")
        old = self._profile(source_fp=old_fp)
        self.repo.save_profile("PCTX", old)
        stale = profile_status(old, new_fp)
        self.assertEqual(stale["status"], "stale")
        new = self._profile(text="new", source_fp=new_fp)
        self.repo.save_profile("PCTX", new)
        rows = self.repo.list_profiles("PCTX", "CHAR-1")
        self.assertEqual({row["status"] for row in rows}, {"current", "stale"})
        self.assertNotEqual(old["profile_id"], new["profile_id"])

    # 3
    def test_manual_override_survives_regeneration(self):
        override = normalize_profile_override({"source_object_id": "CHAR-1", "description": "Manual description", "estimated_tokens": 7, "updated_by": "human"})
        self.repo.save_override("PCTX", override)
        p1 = self._profile(override=override)
        source_fp = p1["source_fingerprint"]
        p2 = derive_semantic_profile(
            {"object_id": "CHAR-1", "object_type": "character", "source_fingerprint": source_fp, "text": "source"},
            {"description": "new auto description", "trigger_when": "new trigger", "estimated_tokens": 99, "semantic_tags": ["changed"], "stage_affinities": []},
            generator_provenance={"kind": "semantic_job", "job_fingerprint": fingerprint("regen")},
            manual_override=self.repo.get_override("PCTX", "CHAR-1"), generated_at="2026-08-18T00:00:01Z",
        )
        self.assertEqual(p2["description"], "Manual description")
        self.assertEqual(p2["estimated_tokens"], 7)
        self.assertEqual(p2["manual_override"]["override_fingerprint"], override["override_fingerprint"])

    # 4
    def test_lifecycle_ineligible_object_never_enters_candidate_pool(self):
        rejected = self._item("CAND-1", "candidate", authority="review", lifecycle="rejected", stages=["draft"])
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id="draft", items=[rejected])
        self.assertEqual(pool["eligible"], [])
        self.assertEqual(pool["excluded"][0]["exclusion"]["code"], "lifecycle_ineligible")

    # 5
    def test_rejected_candidate_cannot_become_canon_context(self):
        rejected = self._item("CAND-2", "candidate", authority="review", lifecycle="rejected", stages=["continuity"], status="rejected")
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id="continuity", items=[rejected])
        bad = validate_context_decision(pool, {"selections": [{"profile_id": rejected["profile"]["profile_id"], "stage_id": "continuity", "reason": "highly relevant"}]}, selector={"kind": "agent", "id": "x"})
        self.assertEqual(bad["status"], "semantic_invalid")
        self.assertFalse(bad["authority"])

    # 6
    def test_research_is_not_character_knowledge(self):
        research = self._item("REF-1", "research", authority="research", lifecycle="active", domain="research", stages=["character_simulation"])
        known = self._item("INFO-1", "character_knowledge", authority="accepted", lifecycle="accepted", domain="character_knowledge", stages=["character_simulation"])
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id="character_simulation", items=[research, known])
        self.assertEqual([x["object_id"] for x in pool["eligible"]], ["INFO-1"])
        self.assertEqual(pool["excluded"][0]["exclusion"]["code"], "research_not_character_knowledge")

    # 7
    def test_stage_specific_greenlights_can_differ(self):
        char = self._item("CHAR-A", "character", stages=["character_simulation", "draft"])
        pressure = self._item("PAY-A", "runtime_state", authority="derived", lifecycle="derived", domain="reader_pressure", stages=["reader_pressure", "draft"])
        char_pool = build_candidate_pool(run_id="RUN-CTX", stage_id="character_simulation", items=[char, pressure])
        draft_pool = build_candidate_pool(run_id="RUN-CTX", stage_id="draft", items=[char, pressure])
        char_dec = validate_context_decision(char_pool, {"selections": [{"profile_id": char_pool["eligible"][0]["profile_id"], "stage_id": "character_simulation", "reason_code": "character", "reason": "character simulation input"}]}, selector={"kind": "agent", "id": "x"})
        draft_ids = [x["profile_id"] for x in draft_pool["eligible"]]
        draft_dec = validate_context_decision(draft_pool, {"selections": [{"profile_id": pid, "stage_id": "draft", "reason_code": "draft", "reason": "writer-safe stage input"} for pid in draft_ids]}, selector={"kind": "agent", "id": "x"})
        self.assertNotEqual({x["profile_id"] for x in char_dec["selected"]}, {x["profile_id"] for x in draft_dec["selected"]})

    # 8
    def test_invalid_model_returned_profile_id_is_rejected_not_guessed(self):
        pool, _, _ = self._greenlight()
        result = validate_context_decision(pool, {"selections": [{"profile_id": "SCP-NOT-ALLOWED", "stage_id": "draft", "reason": "guess"}]}, selector={"kind": "agent", "id": "x"})
        self.assertEqual(result["status"], "semantic_invalid")
        self.assertFalse(result["proceed"])
        self.assertEqual(result["selected"], [])

    # 9
    def test_over_budget_objects_drop_deterministically(self):
        a = self._item("A", "runtime_state", authority="derived", lifecycle="derived", stages=["draft"], tokens=6)
        b = self._item("B", "runtime_state", authority="derived", lifecycle="derived", stages=["draft"], tokens=6)
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id="draft", items=[b, a])
        by_obj = {x["object_id"]: x for x in pool["eligible"]}
        selections = [
            {"profile_id": by_obj["A"]["profile_id"], "stage_id": "draft", "priority": 10, "reason": "first"},
            {"profile_id": by_obj["B"]["profile_id"], "stage_id": "draft", "priority": 1, "reason": "second"},
        ]
        decision = validate_context_decision(pool, {"selections": selections}, selector={"kind": "agent", "id": "x"})
        one = pack_budget(decision, hard_budget=6)
        two = pack_budget(decision, hard_budget=6)
        self.assertEqual(one["loaded_object_ids"], ["A"])
        self.assertEqual(one["dropped_due_budget"][0]["object_id"], "B")
        self.assertEqual(one["selection_fingerprint"], two["selection_fingerprint"])

    # 10
    def test_required_grounding_drop_is_explicitly_incomplete(self):
        item = self._item("REQ", "canon_claim", stages=["draft"], tokens=20, required=True)
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id="draft", items=[item])
        decision = validate_context_decision(pool, {"selections": [{"profile_id": pool["eligible"][0]["profile_id"], "stage_id": "draft", "priority": 1, "reason": "required", "required_for_grounding": True}]}, selector={"kind": "agent", "id": "x"})
        green = pack_budget(decision, hard_budget=5)
        self.assertEqual(green["status"], "grounding_incomplete_due_budget")
        self.assertTrue(green["grounding_incomplete_due_budget"])
        self.assertEqual(green["loaded_profile_ids"], [])

    # 11
    def test_context_freeze_fingerprint_is_reproducible(self):
        pool, _, green = self._greenlight()
        a = freeze_context(run_id="RUN-CTX", task_mode="DRAFT", pools=[pool], greenlights=[green], created_at="one")
        b = freeze_context(run_id="RUN-CTX", task_mode="DRAFT", pools=[pool], greenlights=[green], created_at="two")
        self.assertEqual(a["freeze_fingerprint"], b["freeze_fingerprint"])
        self.assertEqual(a["freeze_id"], b["freeze_id"])

    # 12
    def test_underlying_state_mutation_after_freeze_causes_stale_conflict(self):
        pool, _, green = self._greenlight()
        frozen = freeze_context(run_id="RUN-CTX", task_mode="DRAFT", pools=[pool], greenlights=[green])
        current = dict(frozen["source_fingerprints"])
        target = next(iter(current))
        current[target] = fingerprint("mutated")
        result = validate_freeze(frozen, current)
        self.assertEqual(result["status"], "stale_conflict")
        self.assertFalse(result["proceed"])
        self.assertTrue(result["new_context_fingerprint_required"])
        original = next(iter(frozen["source_fingerprints"]))
        lifecycle_change = validate_freeze(frozen, dict(frozen["source_fingerprints"]), {original:{"source_fingerprint":frozen["source_fingerprints"][original],"authority":"proposal","lifecycle":"proposal","domain":"character","exclusion":None}})
        self.assertEqual(lifecycle_change["status"], "stale_conflict")

    # 13
    def test_stage_context_has_no_untracked_db_fetch_path(self):
        pool, _, green = self._greenlight()
        frozen = freeze_context(run_id="RUN-CTX", task_mode="DRAFT", pools=[pool], greenlights=[green])
        stage = stage_context(frozen, "draft")
        self.assertFalse(stage["db_fetch_performed"])
        sig = inspect.signature(stage_context)
        self.assertEqual(list(sig.parameters), ["freeze", "stage_id"])
        self.assertNotIn("sqlite", inspect.getsource(stage_context).lower())

    # 14
    def test_adaptive_agent_cannot_disable_mandatory_mechanism(self):
        plan = [{"mechanism": name, "run": True} for name in MANDATORY_PRODUCTION_MECHANISMS]
        plan[3]["run"] = False
        result = validate_adaptive_graph(plan)
        self.assertEqual(result["status"], "invalid_mandatory_graph")
        self.assertIn(MANDATORY_PRODUCTION_MECHANISMS[3], result["disabled_mandatory"])

    # 15
    def test_context_receipts_do_not_expose_private_chain_of_thought(self):
        pool, _, green = self._greenlight()
        rejected = validate_context_decision(pool, {"selections": [{"profile_id": pool["eligible"][0]["profile_id"], "stage_id": "draft", "reason": "short", "chain_of_thought": "private"}]}, selector={"kind": "agent", "id": "x"})
        self.assertEqual(rejected["status"], "semantic_invalid")
        projection = build_inspector_projection(run_id="RUN-CTX", pools=[pool], greenlights=[green])
        self.assertFalse(projection["private_chain_of_thought_exposed"])
        self.assertTrue(all("chain_of_thought" not in item and "analysis" not in item and "reasoning" not in item for item in projection["items"]))

    # 16
    def test_backup_restore_retains_context_metadata(self):
        profile = self._profile()
        self.repo.save_profile("PCTX", profile)
        pool, _, green = self._greenlight()
        self.repo.save_stage_selection("PCTX", pool, green)
        frozen = freeze_context(run_id="RUN-CTX", task_mode="SYSTEM-IMPROVE", pools=[pool], greenlights=[green])
        self.repo.save_freeze("PCTX", frozen)
        bundle = self.store.backup_project("PCTX")
        restore = QuillframeStore(self.root / "restored")
        restore.restore_project(bundle)
        restored_repo = ContextRepository(restore)
        self.assertEqual(restored_repo.list_profiles("PCTX")[0]["profile_fingerprint"], profile["profile_fingerprint"])
        self.assertEqual(restored_repo.get_freeze("PCTX", run_id="RUN-CTX")["freeze_fingerprint"], frozen["freeze_fingerprint"])

    # 17
    def test_doctor_applies_and_validates_context_migration(self):
        report = self.store.doctor("PCTX")
        self.assertTrue(report["ok"], json.dumps(report, ensure_ascii=False))
        with self.store.open_project("PCTX") as conn:
            tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"semantic_context_profiles", "context_profile_overrides", "context_stage_selections", "context_freezes"}.issubset(tables))

    # 18
    def test_native_sqlite_wal_and_foreign_key_constraints_remain_active(self):
        with self.store.open_project("PCTX") as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(Exception):
                conn.execute("INSERT INTO context_stage_selections(selection_id,run_id,stage_id,candidate_universe_fingerprint,selection_fingerprint,pool_json,greenlight_json,status,created_at,authority) VALUES('x','MISSING','draft','a','b','{}','{}','packed','now',0)")

    def test_typed_context_query_rejects_physical_sql_contract(self):
        q = validate_context_query({"domain": "character", "filters": {"active": True}, "projection": ["identity", "agenda"], "limit": 20, "authority_requirement": "accepted"})
        self.assertTrue(q["physical_schema_independent"])
        with self.assertRaises(ValueError):
            validate_context_query({"domain": "character", "sql": "select * from characters"})

    def test_inspector_distinguishes_selected_loaded_budget_and_exclusion_states(self):
        a = self._item("A2", "runtime_state", authority="derived", lifecycle="derived", stages=["draft"], tokens=3)
        b = self._item("B2", "runtime_state", authority="derived", lifecycle="derived", stages=["draft"], tokens=9)
        rejected = self._item("R2", "candidate", authority="review", lifecycle="rejected", stages=["draft"])
        pool = build_candidate_pool(run_id="RUN-CTX", stage_id="draft", items=[a, b, rejected])
        by_obj = {x["object_id"]: x for x in pool["eligible"]}
        dec = validate_context_decision(pool, {"selections": [
            {"profile_id": by_obj["A2"]["profile_id"], "stage_id": "draft", "priority": 2, "reason_code": "core", "reason": "core input"},
            {"profile_id": by_obj["B2"]["profile_id"], "stage_id": "draft", "priority": 1, "reason_code": "support", "reason": "support input"},
        ]}, selector={"kind": "agent", "id": "x"})
        green = pack_budget(dec, hard_budget=3)
        projection = build_inspector_projection(run_id="RUN-CTX", pools=[pool], greenlights=[green])
        states = {x["source_object_id"]: x["state"] for x in projection["items"]}
        self.assertEqual(states["A2"], "loaded")
        self.assertEqual(states["B2"], "dropped_due_budget")
        self.assertEqual(states["R2"], "lifecycle_excluded")

    def test_semantic_index_plan_automatically_queues_missing_or_stale_profiles(self):
        fp1 = fingerprint("source-1")
        current = self._profile("CUR", "character", source_fp=fp1)
        plan = build_semantic_index_plan([
            {"object_id":"MISS","object_type":"character","source_fingerprint":fingerprint("m"),"model_view":{"name":"M"}},
            {"object_id":"STALE","object_type":"character","source_fingerprint":fingerprint("new"),"profile":self._profile("STALE","character",source_fp=fingerprint("old"))},
            {"object_id":"CUR","object_type":"character","source_fingerprint":fp1,"profile":current},
        ], generator_id="ctx-indexer")
        self.assertEqual({j["source"]["object_id"] for j in plan["jobs"]}, {"MISS","STALE"})
        self.assertTrue(all(j["contract_id"] == "context.profile_derive" and j["authority"] is False for j in plan["jobs"]))

    def test_stage_visibility_exclusion_is_not_global_source_mutation(self):
        item = self._item("PLAN-PRIVATE", "plan", authority="active_plan", stages=["draft"])
        pools = [build_candidate_pool(run_id="RUN-CTX", stage_id=stage, items=[item])
                 for stage in ("draft", "independent_review")]
        greens = [pack_budget(validate_context_decision(pool, {"selections": []}, selector={"kind": "fixture"}), hard_budget=100)
                  for pool in pools]
        frozen = freeze_context(run_id="RUN-CTX", task_mode="DRAFT", pools=pools, greenlights=greens)
        state = {key: item[key] for key in ("source_fingerprint", "authority", "lifecycle", "domain")}
        self.assertTrue(validate_freeze(frozen, {item["object_id"]: item["source_fingerprint"]}, {item["object_id"]: state})["proceed"])
        self.assertEqual(pools[1]["eligible"], [])
        self.assertEqual(pools[1]["excluded"][0]["exclusion"]["code"], "stage_ineligible")
        state["lifecycle"] = "invalidated"
        self.assertFalse(validate_freeze(frozen, {item["object_id"]: item["source_fingerprint"]}, {item["object_id"]: state})["proceed"])

    def test_character_projection_is_multi_character_state_not_persona(self):
        out = project_character_context({"character_id":"CHAR-X","identity":{"name":"X"},"agenda":"win","knowledge_boundary":["INFO-1"],"current_task":"negotiate","location":"LOC-1","relationship_state":{"REL-1":"strained"},"emotional_carryover":"angry","stakes":"job","misbeliefs":["M1"],"scene_presence":True,"known_facts":["K"],"unknown_facts":["U"]})
        self.assertFalse(out["persona_substitute"])
        self.assertEqual(out["agenda"], "win")
        self.assertEqual(out["unknown_facts"], ["U"])


if __name__ == "__main__":
    unittest.main()
