"""Deterministic routing/privacy tests. Synthetic selections are not quality evidence."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from harness.context_runtime import fingerprint
from harness.semantic_workers.registered_contract_binding import (
    validate_recorded_registered_job, validate_registered_job,
)
from harness.semantic_workers.semantic_worker_router import make_contract_job, validate_typed_value
from corpus.style_contract import (
    compile_style_contract,
    compile_writer_projection,
    make_craft_candidate,
)
from production_runtime import ProductionRunError, ProductionRunExecutor
from production_runtime.craft_guidance import (
    LIBRARY_ROOT, OUTLINE_PLUS_STYLE_CONTRACT_MODE, STYLE_CONTRACT_MODE,
    STYLE_PACK_SCHEMA, freeze_craft_library,
    materialize_writer_craft, planning_sources, selection_input,
    validate_craft_snapshot,
)
from production_runtime.repair import author_direction_evidence
from production_runtime.writer_context import build_inventory, model_inventory
import test_quillframe_production_runtime as fixtures


FP = fingerprint("synthetic binding")
METHODS = {"confrontation", "relationship", "mystery", "everyday", "comedy", "wonder"}
V1_HISTORY_HASHES = {
    "registry.json": "cb72b03e3df96740daf31735aea8eda45bd0f0a46b90b80710faa65b05d935d0",
    "core.en.md": "3c41d0a47f692282aa305262346ae6973bb31e27a20a4d02687d2d491a095511",
    "core.zh-CN.md": "3070c80060e70b83a496639775fcd2a561ccad797e34a04ba132fda096ab124d",
}
V2_HISTORY_HASHES = {
    "registry.json": "0625e97a2f465c412956b0a4f13704e9bb9d98d5fc564a7a7832bb3364f9397d",
    "core.en.md": "ee6e98085126bff3c64acf1c6a2228558bca6fc5203608193344d0f0910ce629",
    "core.zh-CN.md": "c185810c6699f1f5682f08f5183f6a41ffacb0779579c94da77769f11088d4be",
}
V3_HISTORY_HASHES = {
    "registry.json": "5e36f0fb09db1d5597540e22d5152b42d78de8c3dc15df8a6273cb1f4c2cde05",
    "core.en.md": "0bdec954a33d96591597b0dd1d7328ef3854768e0730924ba0d84646f2ddb85a",
    "core.zh-CN.md": "58d62e75803b278e31550cff4c11508c07cf5b57cd869fc20f51b7a6d58c9838",
}
STYLE_OPERATIONS = {
    "body_appearance": "Use visible body and appearance details in the viewpoint's actual attention order.",
    "imagery": "Repeat a concrete image only when its meaning changes with the scene.",
}


def _style_evidence(work_id, evidence_id, role):
    evidence_id = "EV-" + str(evidence_id)
    return {
        "work_id": work_id,
        "evidence_id": evidence_id,
        "role": role,
        "evidence_fingerprint": fingerprint(
            {"work_id": work_id, "evidence_id": evidence_id, "role": role}
        ),
    }


def write_style_pack(root, *, content_zone="general", suffix="A"):
    root.mkdir(parents=True, exist_ok=True)
    candidates = []
    for index, (axis, operation) in enumerate(STYLE_OPERATIONS.items(), 1):
        candidates.append(make_craft_candidate(
            record_id=f"CLAIM-{suffix}-{index}",
            axis=axis,
            operation=operation,
            effect="Make description perform scene and viewpoint work.",
            applies_when=["The detail changes attention, judgment, or spatial orientation."],
            avoid_when=["The detail would interrupt a deliberately abstract transition."],
            failure_boundary="Do not invent anatomy, perception, or symbolic meaning absent from the scene.",
            content_zone=content_zone,
            evidence_refs=[
                _style_evidence(f"WORK-{suffix}-A", index * 10 + 1, "support"),
                _style_evidence(f"WORK-{suffix}-B", index * 10 + 2, "support"),
                _style_evidence(f"WORK-{suffix}-C", index * 10 + 3, "counterexample"),
            ],
            supports=["The synthetic operation recurs across two distinct work fixtures."],
            counterexamples=["A remote transition can legitimately omit concrete detail."],
            confidence_ppm=810_000,
        ))
    contract = compile_style_contract(
        f"STYLE-{suffix}", candidates, content_zone=content_zone,
    )
    projection = compile_writer_projection(contract)
    projection_path = "writer_projection.json"
    (root / projection_path).write_text(
        json.dumps(projection, ensure_ascii=False, sort_keys=True), encoding="utf-8",
    )
    pack = {
        "schema": STYLE_PACK_SCHEMA,
        "pack_id": "style-pack-" + suffix.casefold(),
        "version": "1",
        "status": "candidate",
        "default_mode": "baseline",
        "content_zone": content_zone,
        "writer_projection_path": projection_path,
        "writer_projection_fingerprint": projection["projection_fingerprint"],
    }
    pack["craft_pack_fingerprint"] = fingerprint(pack)
    (root / "pack.json").write_text(
        json.dumps(pack, ensure_ascii=False, sort_keys=True), encoding="utf-8",
    )
    projection_file_fp = "sha256:" + hashlib.sha256(
        (root / projection_path).read_bytes()
    ).hexdigest()
    pack_file_fp = "sha256:" + hashlib.sha256(
        (root / "pack.json").read_bytes()
    ).hexdigest()
    manifest = {
        "schema": "quillframe_run_scoped_style_pack_manifest_v2",
        "run_scope": {"project_id": "PROD", "chapter_id": "CH001",
                      "document_id": "DOC-1", "allowed_task_modes": ["DRAFT"],
                      "one_off_opt_in": True},
        "bounded_writer_projection_fingerprint": projection["projection_fingerprint"],
        "bounded_craft_pack_fingerprint": pack["craft_pack_fingerprint"],
        "projection_file_fingerprint": projection_file_fp,
        "pack_file_fingerprint": pack_file_fp,
        "semantic_leakage_gate": {"status": "pass", "independent": True,
                                  "performed": True},
        "raw_source_persisted": False, "source_identity_included": False,
        "authority": False, "activation_performed": False,
        "promotion_performed": False, "publication_performed": False,
    }
    manifest["manifest_fingerprint"] = fingerprint(manifest)
    (root / "run-scope-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8",
    )
    return projection, pack


def style_run_scope(root, run_id="run_scope_fixture"):
    manifest = json.loads((Path(root) / "run-scope-manifest.json").read_text(encoding="utf-8"))
    return {
        "schema": "quillframe_run_scoped_craft_binding_v1",
        "project_id": "PROD", "run_id": run_id,
        "chapter_id": "CH001", "document_id": "DOC-1", "task_mode": "DRAFT",
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "one_off_opt_in": True, "authority": False,
    }


def scene_context():
    return {"mechanism": "scene_simulation", "items": [
        {"object_id": "BOOK", "object_type": "plan", "authority": "active_plan", "lifecycle": "active_plan",
         "source_fingerprint": FP, "model_view": {"plan": "PRIVATE PLANNING SENTINEL"}},
        {"object_id": "OLD", "object_type": "plan", "authority": "active_plan", "lifecycle": "superseded",
         "source_fingerprint": FP, "model_view": {"plan": "OLD PLAN SENTINEL"}},
        {"object_id": "CHAR", "object_type": "character", "authority": "accepted", "lifecycle": "accepted",
         "source_fingerprint": FP, "model_view": {"agenda": "PRIVATE CHARACTER SENTINEL"}},
    ]}


def choose(card_id="relationship", ref="plan:BOOK"):
    return {"card_id": card_id, "source_refs": [ref], "reason": "PRIVATE SELECTION REASON"}


class CraftLibraryTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = freeze_craft_library("outline_driven")
        self.projection = selection_input(self.snapshot, scene_context())

    def materialize(self, selected, snapshot=None, projection=None):
        return materialize_writer_craft(
            self.snapshot if snapshot is None else snapshot, selected,
            projection_input=self.projection if projection is None else projection, binding_fingerprint=FP,
        )

    def test_baseline_does_not_read_candidate_resources(self):
        with patch("production_runtime.craft_guidance._read_resource", side_effect=AssertionError("unexpected read")):
            baseline = freeze_craft_library()
        self.assertEqual([], baseline["cards"])
        self.assertEqual({}, selection_input(baseline, scene_context()))
        self.assertIsNone(self.materialize([], snapshot=baseline, projection={}))
        with self.assertRaises(ProductionRunError):
            self.materialize([choose()], snapshot=baseline, projection={})

    def test_bilingual_inventory_is_versioned_and_positive_only(self):
        registry = json.loads((LIBRARY_ROOT / "registry.json").read_text(encoding="utf-8"))
        sources = json.loads((LIBRARY_ROOT / registry["sources"]).read_text(encoding="utf-8"))
        self.assertEqual("4", registry["version"])
        self.assertEqual("candidate", registry["status"])
        self.assertFalse(sources["external_code_imported"])
        self.assertFalse(sources["external_skills_installed"])
        source_ids = {row["id"] for row in sources["sources"]}
        self.assertTrue({source_id for card in registry["cards"] for source_id in card["source_ids"]} <= source_ids)
        self.assertEqual("analysis_only", next(row for row in sources["sources"]
                                                if row["id"] == "humanize-chinese")["rights_class"])
        for language in ("en", "zh-CN"):
            snapshot = freeze_craft_library("outline_driven", language=language)
            self.assertEqual(METHODS | {"core"}, {c["card_id"] for c in snapshot["cards"]})
            self.assertEqual("4", snapshot["registry_version"])
            self.assertEqual("4", next(card for card in snapshot["cards"] if card["card_id"] == "core")["version"])
            validate_craft_snapshot(json.loads(json.dumps(snapshot)))
            self.assertTrue((LIBRARY_ROOT / registry["diagnostics"][language]).is_file())
            self.assertNotIn("diagnostics", json.dumps(snapshot))
        self.assertEqual(METHODS, {row["card_id"] for row in self.projection["craft_catalog"]["cards"]})
        for row in self.projection["craft_catalog"]["cards"]:
            self.assertNotIn("text", row)
            self.assertGreater(row["utf8_bytes"], 0)

    def test_versioned_writer_resources_are_exact_history_not_current_dispatch(self):
        for version, expected_hashes in (("1", V1_HISTORY_HASHES), ("2", V2_HISTORY_HASHES), ("3", V3_HISTORY_HASHES)):
            history = LIBRARY_ROOT / "history" / ("v" + version)
            for name, expected in expected_hashes.items():
                self.assertEqual(expected, hashlib.sha256((history / name).read_bytes()).hexdigest())
            old_registry = json.loads((history / "registry.json").read_text(encoding="utf-8"))
            self.assertEqual(version, old_registry["version"])
        current_registry = json.loads((LIBRARY_ROOT / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual("4", current_registry["version"])
        self.assertEqual("history/v1/registry.json", current_registry["history"]["1"]["registry"])
        self.assertEqual("history/v2/registry.json", current_registry["history"]["2"]["registry"])
        self.assertEqual("history/v3/registry.json", current_registry["history"]["3"]["registry"])
        self.assertNotEqual((LIBRARY_ROOT / "history" / "v1" / "core.zh-CN.md").read_bytes(),
                            (LIBRARY_ROOT / "cards" / "core.zh-CN.md").read_bytes())
        self.assertNotEqual((LIBRARY_ROOT / "history" / "v2" / "core.zh-CN.md").read_bytes(),
                            (LIBRARY_ROOT / "cards" / "core.zh-CN.md").read_bytes())

        reads = []
        from production_runtime import craft_guidance as module
        original = module._read_resource

        def observe(root, relative):
            reads.append(str(relative))
            return original(root, relative)

        with patch("production_runtime.craft_guidance._read_resource", side_effect=observe):
            freeze_craft_library("outline_driven")
        self.assertFalse(any("history/" in relative for relative in reads))

    def test_only_current_selected_planning_sources_are_projected(self):
        sources = planning_sources(scene_context())
        self.assertEqual(["plan:BOOK"], [row["source_ref"] for row in sources])
        serialized = json.dumps(sources)
        self.assertIn("PRIVATE PLANNING SENTINEL", serialized)
        self.assertNotIn("OLD PLAN SENTINEL", serialized)
        self.assertNotIn("PRIVATE CHARACTER SENTINEL", serialized)
        with self.assertRaises(ProductionRunError):
            planning_sources({"mechanism": "surface_realization", "items": []})

    def test_model_ids_drive_mixed_selection_without_genre_classification(self):
        result = self.materialize([choose("comedy"), choose("everyday")])
        self.assertEqual(["core", "comedy", "everyday"], [row["card_id"] for row in result["cards"]])
        self.assertFalse(result["authority"])
        for excluded in ("PRIVATE SELECTION REASON", "PRIVATE PLANNING SENTINEL", "source_refs", "selection_hint"):
            self.assertNotIn(excluded, json.dumps(result))
        self.assertEqual(FP, result["selection_binding_fingerprint"])
        self.assertNotEqual(result, self.materialize([choose("mystery")]))

    def test_empty_choice_keeps_foundation_and_missing_plans_are_valid(self):
        self.assertEqual(["core"], [row["card_id"] for row in self.materialize([])["cards"]])
        projection = selection_input(self.snapshot, {"mechanism": "scene_simulation", "items": []})
        for ref in ("task:request", "scene:resolved"):
            self.assertEqual(2, len(self.materialize([choose(ref=ref)], projection=projection)["cards"]))

    def test_bad_selection_is_rejected_without_fallback_or_inferred_method(self):
        for selection in (None, {}, [choose("unknown")], [choose("core")], [choose(), choose()],
                          [choose(ref="plan:OLD")], [choose(ref="character:CHAR")],
                          [{**choose(), "source_refs": []}], [{**choose(), "reason": ""}],
                          [{**choose(), "reason": "x" * 801}], [{**choose(), "text": "override"}]):
            with self.subTest(selection=selection), self.assertRaises(ProductionRunError) as caught:
                self.materialize(selection)
            self.assertEqual("semantic_output_invalid", caught.exception.code)

    def test_snapshot_catalog_and_binding_tampering_fail(self):
        for field in ("text", "version", "card_id"):
            snapshot = deepcopy(self.snapshot)
            snapshot["cards"][0][field] += " changed"
            with self.subTest(field=field), self.assertRaises(ProductionRunError):
                self.materialize([], snapshot=snapshot)
        for field in ("title", "selection_hint", "card_id"):
            projection = deepcopy(self.projection)
            projection["craft_catalog"]["cards"][0][field] += " changed"
            with self.subTest(field=field), self.assertRaises(ProductionRunError):
                self.materialize([], projection=projection)
        with self.assertRaises(ProductionRunError):
            materialize_writer_craft(self.snapshot, [], projection_input=self.projection, binding_fingerprint="unbound")

    def test_frozen_content_survives_disk_edits_but_new_freeze_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "craft"
            shutil.copytree(LIBRARY_ROOT, root)
            original = freeze_craft_library("outline_driven", root=root)
            card = root / "cards" / "core.zh-CN.md"
            card.write_text(card.read_text(encoding="utf-8") + "\nNew method edition.\n", encoding="utf-8")
            (root / "diagnostics.zh-CN.md").write_text("DIAGNOSTIC PRIVATE SENTINEL", encoding="utf-8")
            current = freeze_craft_library("outline_driven", root=root)
            self.assertNotEqual(original["snapshot_fingerprint"], current["snapshot_fingerprint"])
            validate_craft_snapshot(original)
            self.assertNotIn("DIAGNOSTIC PRIVATE SENTINEL", json.dumps(current))
            self.assertEqual(self.snapshot, original)

    def test_registry_cannot_self_promote_or_point_writer_at_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "craft"
            shutil.copytree(LIBRARY_ROOT, root)
            path = root / "registry.json"
            original = json.loads(path.read_text(encoding="utf-8"))
            for change in ("status", "default_mode", "diagnostic_path", "escape"):
                registry = deepcopy(original)
                if change == "status":
                    registry["status"] = "promoted"
                elif change == "default_mode":
                    registry["default_mode"] = "outline_driven"
                else:
                    registry["cards"][0]["writer_paths"]["zh-CN"] = (
                        "diagnostics.zh-CN.md" if change == "diagnostic_path" else "../outside.md")
                path.write_text(json.dumps(registry), encoding="utf-8")
                with self.subTest(change=change), self.assertRaises(ProductionRunError):
                    freeze_craft_library("outline_driven", root=root)

    def test_registered_v10_requires_writer_composition_and_preserves_v9_history_only(self):
        directions = author_direction_evidence("Synthetic current request.")
        inventory = build_inventory(
            {"mechanism": "scene_simulation", "items": []},
            character_action_evidence=[], author_model=None,
        )
        payload = {"scene_id": "SCENE", "resolved_trajectory": {}, "character_action_evidence": [],
                   "pov_boundary": {}, "author_direction_evidence": directions,
                   "writer_context_inventory": model_inventory(inventory), **self.projection}
        job = make_contract_job("scene.realization_project", "SCENE", payload)
        self.assertEqual("10", job["input"]["model_contract_version"])
        self.assertTrue(any(
            "at least one and at most eight" in rule and "run_scoped_corpus_style" in rule
            for rule in job["rubric"]
        ))
        self.assertEqual([], validate_registered_job(job))
        judgment = {
            "confidence": 1.0,
            "scene_id": "SCENE",
            "scene_contract": {
                "pov_now": {"visible": ["A synthetic object."], "known": ["It is present."],
                            "misunderstood": ["Its purpose."]},
                "opening_choices": ["Approach it.", "Leave it."],
                "enacted_strategies": [{"character_ref": "fixture", "selected_action": "Approach it.",
                                         "observable_effect": "It blocks the path."}],
                "counterforces": ["The path is narrow."],
                "option_cost_or_relationship_changes": ["Leaving costs time."],
                "required_fact_outcomes": ["The path remains blocked."],
                "protected_subtext_or_information_gaps": ["Its purpose remains unstated."],
                "ending_constraint": "The character must choose another route.",
                "concrete_friction": "The object occupies the doorway.",
            },
            "selected_context_ids": [],
            "director_note": "Let the blocked doorway carry the pressure.",
            "author_objective_items": [{
                "objective_id": "OBJ-SYNTHETIC", "statement": directions[0]["statement"],
                "source_refs": [directions[0]["source_ref"]], "hard": True,
            }],
            "craft_selection": [],
        }
        self.assertEqual([], validate_typed_value(judgment, job["output_contract"]))
        del judgment["craft_selection"]
        self.assertTrue(validate_typed_value(judgment, job["output_contract"]))
        history = fixtures.ROOT / "harness/semantic_workers/contracts/history"
        index = json.loads((history / "index.json").read_text(encoding="utf-8"))
        entry = next(row for row in index["entries"]
                     if row["pack_id"] == "production-loop" and row["version"] == "9")
        raw = (history / entry["path"]).read_bytes()
        self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
        old_payload = {k: v for k, v in payload.items()
                       if k not in {"author_direction_evidence", "writer_context_inventory"}}
        old = make_contract_job("scene.realization_project", "SCENE", old_payload, registry_path=history / entry["path"])
        old["provenance"]["registry_path"] = Path("contracts/production-loop.json").as_posix()
        old["provenance"]["pack_id"] = "production-loop"
        self.assertTrue(validate_registered_job(old))
        self.assertEqual([], validate_recorded_registered_job(old))


class StyleContractCraftPackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "pack"
        self.projection, self.pack = write_style_pack(self.root)
        self.snapshot = freeze_craft_library(
            STYLE_CONTRACT_MODE, root=self.root,
        )
        self.selection = selection_input(self.snapshot, scene_context())

    def tearDown(self):
        self.temporary.cleanup()

    def test_selector_sees_only_source_free_style_metadata_and_writer_gets_only_selection(self):
        validate_craft_snapshot(deepcopy(self.snapshot))
        self.assertEqual("general", self.snapshot["content_zone"])
        self.assertEqual(
            self.pack["craft_pack_fingerprint"],
            self.snapshot["craft_pack_fingerprint"],
        )
        self.assertEqual(
            self.projection["projection_fingerprint"],
            self.snapshot["writer_projection_fingerprint"],
        )
        self.assertNotIn("planning_context", self.selection)
        catalog = self.selection["craft_catalog"]
        expected_hint_keys = {
            "operation", "effect", "applies_when", "avoid_when",
            "failure_boundary", "content_zone",
        }
        for row in catalog["cards"]:
            self.assertIn(row["title"], STYLE_OPERATIONS)
            hint = json.loads(row["selection_hint"])
            self.assertEqual(expected_hint_keys, set(hint))
            self.assertEqual(STYLE_OPERATIONS[row["title"]], hint["operation"])
        encoded_catalog = json.dumps(catalog, ensure_ascii=False)
        for excluded in (
            "style_contract_fingerprint", "writer_projection_fingerprint",
            "craft_pack_fingerprint", "confidence_ppm", "evidence_refs",
            "supporting_work_count", "counterexample_count", "WORK-",
        ):
            self.assertNotIn(excluded, encoded_catalog)

        selected = next(
            card for card in self.snapshot["cards"] if card["axis"] == "body_appearance"
        )
        writer = materialize_writer_craft(
            self.snapshot,
            [choose(selected["card_id"], "scene:resolved")],
            projection_input=self.selection,
            binding_fingerprint=FP,
        )
        self.assertEqual(1, len(writer["cards"]))
        self.assertEqual(
            {
                "axis", "operation", "effect", "applies_when", "avoid_when",
                "failure_boundary", "content_zone",
            },
            set(writer["cards"][0]),
        )
        self.assertEqual("body_appearance", writer["cards"][0]["axis"])
        encoded_writer = json.dumps(writer, ensure_ascii=False)
        self.assertIn(STYLE_OPERATIONS["body_appearance"], encoded_writer)
        self.assertNotIn(STYLE_OPERATIONS["imagery"], encoded_writer)
        self.assertNotIn(selected["card_id"], encoded_writer)
        self.assertIsNone(materialize_writer_craft(
            self.snapshot, [], projection_input=self.selection,
            binding_fingerprint=FP,
        ))

    def test_style_selector_is_bounded_to_eight_cards(self):
        bounded_root = Path(self.temporary.name) / "bounded-pack"
        with patch.dict(STYLE_OPERATIONS, {
            "dialogue_voice": "Let each reply alter the immediate social pressure.",
            "information_flow": "Reveal only the fact that changes the next choice.",
            "syntax_rhythm": "Vary clause length with the viewpoint's processing pressure.",
            "prose_voice": "Keep narration owned by the current viewpoint.",
            "lexical_register": "Use vocabulary plausible for the speaker and pressure.",
            "psychic_distance": "Change distance only with the viewpoint's processing need.",
            "descriptive_attention": "Describe what changes action or judgment.",
            "interiority_summary": "Summarize thought only when it changes the next move.",
        }):
            write_style_pack(bounded_root, suffix="BOUNDED")
        bounded_snapshot = freeze_craft_library(
            STYLE_CONTRACT_MODE, root=bounded_root,
        )
        bounded_input = selection_input(bounded_snapshot, scene_context())
        selected = [
            choose(card["card_id"], "scene:resolved")
            for card in bounded_snapshot["cards"][:8]
        ]
        self.assertEqual(8, len(selected))
        self.assertEqual(8, len(materialize_writer_craft(
            bounded_snapshot, selected, projection_input=bounded_input,
            binding_fingerprint=FP,
        )["cards"]))
        selected.append(choose(bounded_snapshot["cards"][8]["card_id"], "scene:resolved"))
        with self.assertRaises(ProductionRunError) as raised:
            materialize_writer_craft(
                bounded_snapshot, selected, projection_input=bounded_input,
                binding_fingerprint=FP,
            )
        self.assertEqual("semantic_output_invalid", raised.exception.code)

    def test_pack_projection_snapshot_and_path_tampering_fail_closed(self):
        tampered_snapshot = deepcopy(self.snapshot)
        tampered_snapshot["cards"][0]["operation"] += " changed"
        tampered_snapshot["snapshot_fingerprint"] = fingerprint({
            key: value for key, value in tampered_snapshot.items()
            if key != "snapshot_fingerprint"
        })
        with self.assertRaises(ProductionRunError):
            validate_craft_snapshot(tampered_snapshot)

        projection = json.loads(
            (self.root / "writer_projection.json").read_text(encoding="utf-8")
        )
        projection["craft_candidates"][0]["operation"] += " changed"
        (self.root / "writer_projection.json").write_text(
            json.dumps(projection), encoding="utf-8",
        )
        with self.assertRaises(ProductionRunError):
            freeze_craft_library(STYLE_CONTRACT_MODE, root=self.root)

        pack_fp_root = Path(self.temporary.name) / "pack-fingerprint"
        _, pack_fp = write_style_pack(pack_fp_root, suffix="PACKFP")
        pack_fp["version"] = "2"
        (pack_fp_root / "pack.json").write_text(
            json.dumps(pack_fp), encoding="utf-8",
        )
        with self.assertRaises(ProductionRunError):
            freeze_craft_library(STYLE_CONTRACT_MODE, root=pack_fp_root)

        projection_fp_root = Path(self.temporary.name) / "projection-fingerprint"
        _, projection_fp_pack = write_style_pack(projection_fp_root, suffix="PROJFP")
        projection_fp_pack["writer_projection_fingerprint"] = "sha256:" + "f" * 64
        projection_fp_pack["craft_pack_fingerprint"] = fingerprint({
            key: value for key, value in projection_fp_pack.items()
            if key != "craft_pack_fingerprint"
        })
        (projection_fp_root / "pack.json").write_text(
            json.dumps(projection_fp_pack), encoding="utf-8",
        )
        with self.assertRaises(ProductionRunError):
            freeze_craft_library(STYLE_CONTRACT_MODE, root=projection_fp_root)

        closed_root = Path(self.temporary.name) / "closed-pack"
        closed_projection, closed_pack = write_style_pack(closed_root, suffix="CLOSED")
        closed_projection["source"] = {"title": "PRIVATE SOURCE"}
        closed_projection["projection_fingerprint"] = fingerprint({
            key: value for key, value in closed_projection.items()
            if key != "projection_fingerprint"
        })
        (closed_root / "writer_projection.json").write_text(
            json.dumps(closed_projection), encoding="utf-8",
        )
        closed_pack["writer_projection_fingerprint"] = closed_projection["projection_fingerprint"]
        closed_pack["craft_pack_fingerprint"] = fingerprint({
            key: value for key, value in closed_pack.items()
            if key != "craft_pack_fingerprint"
        })
        (closed_root / "pack.json").write_text(
            json.dumps(closed_pack), encoding="utf-8",
        )
        with self.assertRaises(ProductionRunError):
            freeze_craft_library(STYLE_CONTRACT_MODE, root=closed_root)

        escape_root = Path(self.temporary.name) / "escape-pack"
        escaped_projection, escaped_pack = write_style_pack(escape_root, suffix="ESCAPE")
        outside = Path(self.temporary.name) / "outside.json"
        outside.write_text(json.dumps(escaped_projection), encoding="utf-8")
        escaped_pack["writer_projection_path"] = "../outside.json"
        escaped_pack["craft_pack_fingerprint"] = fingerprint({
            key: value for key, value in escaped_pack.items()
            if key != "craft_pack_fingerprint"
        })
        (escape_root / "pack.json").write_text(
            json.dumps(escaped_pack), encoding="utf-8",
        )
        with self.assertRaises(ProductionRunError):
            freeze_craft_library(STYLE_CONTRACT_MODE, root=escape_root)

    def test_adult_explicit_pack_isolated_from_default_general_run(self):
        adult_root = Path(self.temporary.name) / "adult-pack"
        write_style_pack(adult_root, content_zone="adult_explicit", suffix="ADULT")
        with self.assertRaises(ProductionRunError):
            freeze_craft_library(STYLE_CONTRACT_MODE, root=adult_root)
        adult = freeze_craft_library(
            STYLE_CONTRACT_MODE, root=adult_root, content_zone="adult_explicit",
        )
        self.assertEqual("adult_explicit", adult["content_zone"])
        self.assertTrue(all(
            card["content_zone"] == "adult_explicit" for card in adult["cards"]
        ))

    def test_outline_plus_style_closes_both_snapshots_and_composes_one_catalog(self):
        combined = freeze_craft_library(
            OUTLINE_PLUS_STYLE_CONTRACT_MODE, style_pack_root=self.root,
            run_scope=style_run_scope(self.root),
        )
        validate_craft_snapshot(deepcopy(combined))
        self.assertEqual("outline_driven", combined["outline_driven"]["mode"])
        self.assertEqual(STYLE_CONTRACT_MODE, combined["style_contract"]["mode"])
        projected = selection_input(combined, scene_context())
        catalog = projected["craft_catalog"]
        self.assertLessEqual(len(catalog["cards"]), 63)
        self.assertEqual(
            METHODS | {card["card_id"] for card in self.snapshot["cards"]},
            {card["card_id"] for card in catalog["cards"]},
        )
        with self.assertRaises(ProductionRunError) as missing_corpus:
            materialize_writer_craft(
                combined, [], projection_input=projected, binding_fingerprint=FP,
            )
        self.assertEqual("semantic_output_invalid", missing_corpus.exception.code)
        corpus_hints = [json.loads(card["selection_hint"]) for card in catalog["cards"]
                        if card["card_id"].startswith("style-")]
        self.assertTrue(corpus_hints)
        self.assertTrue(all(hint["route_class"] == "run_scoped_corpus_style"
                            for hint in corpus_hints))
        style_card = self.snapshot["cards"][0]
        writer = materialize_writer_craft(
            combined,
            [choose("relationship"), choose(style_card["card_id"], "scene:resolved")],
            projection_input=projected, binding_fingerprint=FP,
        )
        self.assertEqual(
            ["core", "relationship"],
            [card["card_id"] for card in writer["registered_craft"]["cards"]],
        )
        self.assertEqual(1, len(writer["corpus_style"]["cards"]))
        self.assertNotIn(style_card["card_id"], json.dumps(writer))

        tampered = deepcopy(combined)
        tampered["outline_driven"]["cards"][0]["text"] += " changed"
        tampered["snapshot_fingerprint"] = fingerprint({
            key: value for key, value in tampered.items()
            if key != "snapshot_fingerprint"
        })
        with self.assertRaises(ProductionRunError):
            validate_craft_snapshot(tampered)
        changed_scope = deepcopy(combined)
        changed_scope["run_scope"]["authority"] = True
        changed_scope["snapshot_fingerprint"] = fingerprint({
            key: value for key, value in changed_scope.items()
            if key != "snapshot_fingerprint"
        })
        with self.assertRaises(ProductionRunError):
            validate_craft_snapshot(changed_scope)

    def test_outline_plus_style_limits_only_corpus_cards_to_eight(self):
        bounded_root = Path(self.temporary.name) / "combined-bounded"
        with patch.dict(STYLE_OPERATIONS, {
            "dialogue_voice": "Let each reply alter the immediate social pressure.",
            "information_flow": "Reveal only the fact that changes the next choice.",
            "syntax_rhythm": "Vary clause length with viewpoint pressure.",
            "prose_voice": "Keep narration owned by the current viewpoint.",
            "lexical_register": "Use vocabulary plausible for the speaker and pressure.",
            "psychic_distance": "Change distance only with the viewpoint's processing need.",
            "descriptive_attention": "Describe what changes action or judgment.",
            "interiority_summary": "Summarize thought only when it changes the next move.",
        }):
            write_style_pack(bounded_root, suffix="COMBINED")
        combined = freeze_craft_library(
            OUTLINE_PLUS_STYLE_CONTRACT_MODE, style_pack_root=bounded_root,
            run_scope=style_run_scope(bounded_root),
        )
        projected = selection_input(combined, scene_context())
        corpus = combined["style_contract"]["cards"]
        selected = [choose("relationship")] + [
            choose(card["card_id"], "scene:resolved") for card in corpus[:8]
        ]
        writer = materialize_writer_craft(
            combined, selected, projection_input=projected,
            binding_fingerprint=FP,
        )
        self.assertEqual(8, len(writer["corpus_style"]["cards"]))
        selected.append(choose(corpus[8]["card_id"], "scene:resolved"))
        with self.assertRaises(ProductionRunError) as raised:
            materialize_writer_craft(
                combined, selected, projection_input=projected,
                binding_fingerprint=FP,
            )
        self.assertEqual("semantic_output_invalid", raised.exception.code)


class CraftFixtureRuntime(fixtures.FakeAgentRuntime):
    def __init__(self, selected=None):
        super().__init__()
        self.selected = [] if selected is None else selected

    def run(self, job, *, cancellation=None):
        result = super().run(job, cancellation=cancellation)
        if job.runtime_role == "registered_scene_projection":
            output = json.loads(result.final_text)
            output["craft_selection"] = deepcopy(self.selected)
            result.final_text = json.dumps(output)
        return result


class CraftRuntimeTests(unittest.TestCase):
    setUp = fixtures.ProductionRuntimeTests.setUp
    tearDown = fixtures.ProductionRuntimeTests.tearDown
    start = fixtures.ProductionRuntimeTests.start

    def execute(self, runtime, run_id, mode=None, *, style_pack_root=None):
        return runtime.execute("PROD", run_id, service_id="svc", instruction="draft chapter",
                               reader_grip="very_high", rule_material=fixtures.RULE_MATERIAL,
                               independent_provenance=fixtures.PROVENANCE, craft_guidance_mode=mode,
                               style_pack_root=style_pack_root,
                               style_pack_manifest_fingerprint=(
                                   style_run_scope(style_pack_root)["manifest_fingerprint"]
                                   if mode == OUTLINE_PLUS_STYLE_CONTRACT_MODE else None
                               ))

    def test_default_compatibility_and_no_extra_selection_call(self):
        roles = []
        for mode in (None, "outline_driven"):
            fake = CraftFixtureRuntime()
            runtime = ProductionRunExecutor(self.store, fake)
            result = self.execute(runtime, self.start(), mode)
            self.assertEqual("awaiting_external", result["status"])
            roles.append([job.runtime_role for job in fake.calls if job.runtime_role != "context_profile_deriver"])
            for job in fake.calls:
                if job.runtime_role == "surface_realization":
                    self.assertEqual(mode is not None, "craft_guidance" in job.context[0]["writer_pack"])
            self.assertEqual(1, roles[-1].count("registered_scene_projection"))
            self.assertEqual(1, roles[-1].count("surface_realization"))
        self.assertEqual(roles[0], roles[1])

    def test_writer_snapshots_match_and_reader_and_independent_are_blind(self):
        fake = CraftFixtureRuntime([choose("relationship", "scene:resolved"), choose("everyday", "task:request")])
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start(reader_positioning=fixtures.READER_POSITIONING)
        public = self.execute(runtime, run_id, "outline_driven")
        fixtures.assert_public_execution_safe(self, public)
        writers = [job.context[0] for job in fake.calls if job.runtime_role == "surface_realization"]
        self.assertEqual(1, len(writers))
        guidance = writers[0]["writer_pack"]["craft_guidance"]
        self.assertEqual(["core", "relationship", "everyday"], [c["card_id"] for c in guidance["cards"]])
        self.assertEqual("4", guidance["registry_version"])
        foundation = guidance["cards"][0]
        self.assertEqual("4", foundation["version"])
        self.assertIn("Scene Realization Contract", foundation["text"])
        self.assertIn("一次性实现候选正文", foundation["text"])
        self.assertNotIn("Raw Draft", foundation["text"])
        self.assertNotIn("PRIVATE SELECTION REASON", json.dumps(writers[0]))
        self.assertNotIn("craft_selection", json.dumps(writers[0]))
        reader = next(job for job in fake.calls if job.runtime_role == "registered_reader_engagement")
        independent = fixtures.frozen_packet(self.store, run_id)
        for value in (public, reader.context, independent):
            encoded = json.dumps(value, ensure_ascii=False)
            for excluded in ("craft_selection", "craft_guidance", "PRIVATE SELECTION REASON", "planning_context"):
                self.assertNotIn(excluded, encoded)
            for card in guidance["cards"]:
                self.assertNotIn(card["text"], encoded)

    def test_current_plans_reach_selection_without_becoming_reader_context(self):
        stamp = fixtures.now_iso()
        with self.store.open_project("PROD") as conn:
            for plan_id, status, content in (("PLAN-CURRENT", "active", "PRIVATE CURRENT OUTLINE"),
                                              ("PLAN-OLD", "superseded", "STALE OUTLINE")):
                plan = {"content": content}
                conn.execute("INSERT INTO plans(plan_id,task_mode,target_id,status,plan_json,content_fingerprint,created_at,updated_at) "
                             "VALUES(?,?,?,?,?,?,?,?)", (plan_id, "DESIGN-BOOK", "book", status, json.dumps(plan), fingerprint(plan), stamp, stamp))
            conn.commit()
        fake = CraftFixtureRuntime([choose(ref="plan:PLAN-CURRENT")])
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.execute(runtime, run_id, "outline_driven")
        projection = next(job for job in fake.calls if job.runtime_role == "registered_scene_projection")
        planning = projection.context[0]["registered_semantic_job"]["input"]["payload"]["planning_context"]
        self.assertIn("PRIVATE CURRENT OUTLINE", json.dumps(planning))
        self.assertNotIn("STALE OUTLINE", json.dumps(planning))
        for value in (next(job.context for job in fake.calls if job.runtime_role == "registered_reader_engagement"),
                      fixtures.frozen_packet(self.store, run_id)):
            self.assertNotIn("PRIVATE CURRENT OUTLINE", json.dumps(value))

    def test_style_contract_selection_reaches_only_writers_and_reader_review_stays_blind(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "style-pack"
            write_style_pack(root, suffix="RUNTIME")
            frozen = freeze_craft_library(STYLE_CONTRACT_MODE, root=root)
            selected = next(
                card for card in frozen["cards"] if card["axis"] == "body_appearance"
            )
            fake = CraftFixtureRuntime([choose(selected["card_id"], "scene:resolved")])
            runtime = ProductionRunExecutor(self.store, fake)
            run_id = self.start(reader_positioning=fixtures.READER_POSITIONING)
            public = self.execute(
                runtime, run_id, STYLE_CONTRACT_MODE, style_pack_root=root,
            )
            self.assertEqual("awaiting_external", public["status"])
            fixtures.assert_public_execution_safe(self, public)

            scene = next(
                job for job in fake.calls if job.runtime_role == "registered_scene_projection"
            )
            payload = scene.context[0]["registered_semantic_job"]["input"]["payload"]
            self.assertIn("craft_catalog", payload)
            self.assertNotIn("planning_context", payload)
            encoded_payload = json.dumps(payload, ensure_ascii=False)
            for excluded in (
                "style_contract_fingerprint", "writer_projection_fingerprint",
                "craft_pack_fingerprint", "confidence_ppm", "evidence_refs", "WORK-",
            ):
                self.assertNotIn(excluded, encoded_payload)

            writers = [
                job.context[0] for job in fake.calls
                if job.runtime_role == "surface_realization"
            ]
            self.assertEqual(1, len(writers))
            for writer in writers:
                guidance = writer["writer_pack"]["craft_guidance"]
                self.assertEqual(1, len(guidance["cards"]))
                self.assertEqual("body_appearance", guidance["cards"][0]["axis"])
                encoded = json.dumps(guidance, ensure_ascii=False)
                self.assertIn(STYLE_OPERATIONS["body_appearance"], encoded)
                self.assertNotIn(STYLE_OPERATIONS["imagery"], encoded)
                self.assertNotIn(selected["card_id"], encoded)

            reader = next(
                job for job in fake.calls
                if job.runtime_role == "registered_reader_engagement"
            )
            independent = fixtures.frozen_packet(self.store, run_id)
            for value in (public, reader.context, independent):
                encoded = json.dumps(value, ensure_ascii=False)
                for excluded in (
                    "craft_guidance", "craft_selection", "craft_catalog",
                    *STYLE_OPERATIONS.values(),
                ):
                    self.assertNotIn(excluded, encoded)

    def test_outline_plus_style_is_writer_only_and_keeps_registered_core(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "style-pack"
            write_style_pack(root, suffix="COMPOSE")
            frozen = freeze_craft_library(
                OUTLINE_PLUS_STYLE_CONTRACT_MODE, style_pack_root=root,
                run_scope=style_run_scope(root),
            )
            style_card = next(
                card for card in frozen["style_contract"]["cards"]
                if card["axis"] == "body_appearance"
            )
            fake = CraftFixtureRuntime([
                choose("relationship", "scene:resolved"),
                choose(style_card["card_id"], "task:request"),
            ])
            runtime = ProductionRunExecutor(self.store, fake)
            run_id = self.start(reader_positioning=fixtures.READER_POSITIONING)
            public = self.execute(
                runtime, run_id, OUTLINE_PLUS_STYLE_CONTRACT_MODE,
                style_pack_root=root,
            )
            frozen_request = runtime.stage_repository.load_request("PROD", run_id)
            self.assertNotIn("style_pack_root", frozen_request)
            self.assertEqual(run_id, frozen_request["craft_guidance"]["run_scope"]["run_id"])
            self.assertEqual("PROD", frozen_request["craft_guidance"]["run_scope"]["project_id"])
            self.assertEqual(
                style_run_scope(root)["manifest_fingerprint"],
                frozen_request["craft_guidance"]["run_scope"]["manifest_fingerprint"],
            )
            scene = next(
                job for job in fake.calls
                if job.runtime_role == "registered_scene_projection"
            )
            catalog = scene.context[0]["registered_semantic_job"]["input"]["payload"]["craft_catalog"]
            self.assertLessEqual(len(catalog["cards"]), 63)
            writers = [
                job.context[0] for job in fake.calls
                if job.runtime_role == "surface_realization"
            ]
            self.assertEqual(1, len(writers))
            guidance = writers[0]["writer_pack"]["craft_guidance"]
            self.assertEqual(
                ["core", "relationship"],
                [card["card_id"] for card in guidance["registered_craft"]["cards"]],
            )
            self.assertEqual("body_appearance", guidance["corpus_style"]["cards"][0]["axis"])
            for value in (
                public,
                next(job.context for job in fake.calls if job.runtime_role == "registered_reader_engagement"),
                fixtures.frozen_packet(self.store, run_id),
            ):
                encoded = json.dumps(value, ensure_ascii=False)
                self.assertNotIn("registered_craft", encoded)
                self.assertNotIn("corpus_style", encoded)
                self.assertNotIn(STYLE_OPERATIONS["body_appearance"], encoded)

    def test_style_contract_resume_uses_frozen_pack_after_disk_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "style-pack"
            write_style_pack(root, suffix="RESUME")
            frozen = freeze_craft_library(STYLE_CONTRACT_MODE, root=root)
            selected = next(card for card in frozen["cards"] if card["axis"] == "imagery")
            fake = CraftFixtureRuntime([choose(selected["card_id"], "scene:resolved")])
            runtime = ProductionRunExecutor(self.store, fake)
            run_id = self.start()
            persist = runtime._persist_stage_receipt

            def interrupt(project_id, execution_id, public):
                if public["mechanism"] == "surface_realization":
                    raise OSError("synthetic style-pack interruption")
                return persist(project_id, execution_id, public)

            with patch.object(runtime, "_persist_stage_receipt", side_effect=interrupt), \
                    self.assertRaises(OSError):
                self.execute(
                    runtime, run_id, STYLE_CONTRACT_MODE, style_pack_root=root,
                )
            frozen_request = runtime.stage_repository.load_request("PROD", run_id)
            original = frozen_request["craft_guidance"]
            self.assertNotIn("style_pack_root", frozen_request)
            self.assertNotIn(str(root), json.dumps(frozen_request))
            (root / "writer_projection.json").write_text("{}", encoding="utf-8")

            with patch(
                "production_runtime.runtime.freeze_craft_library",
                side_effect=AssertionError("resume must not reload the style pack"),
            ):
                result = ProductionRunExecutor(self.store, fake).resume_execution("PROD", run_id)
            self.assertEqual("awaiting_external", result["status"])
            self.assertEqual(
                original,
                runtime.stage_repository.load_request("PROD", run_id)["craft_guidance"],
            )
            for role in ("registered_scene_projection", "surface_realization"):
                self.assertEqual(1, sum(job.runtime_role == role for job in fake.calls))

    def test_resume_after_interruption_reuses_original_resources_and_calls(self):
        fake = CraftFixtureRuntime([choose(ref="scene:resolved")])
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        persist = runtime._persist_stage_receipt

        def interrupt(project_id, execution_id, public):
            if public["mechanism"] == "surface_realization":
                raise OSError("synthetic interruption after confirmed Surface Writer")
            return persist(project_id, execution_id, public)

        with patch.object(runtime, "_persist_stage_receipt", side_effect=interrupt), self.assertRaises(OSError):
            self.execute(runtime, run_id, "outline_driven")
        original = runtime.stage_repository.load_request("PROD", run_id)["craft_guidance"]
        with patch("production_runtime.runtime.freeze_craft_library", side_effect=AssertionError("must not reload changed disk")):
            result = ProductionRunExecutor(self.store, fake).resume_execution("PROD", run_id)
        self.assertEqual("awaiting_external", result["status"])
        self.assertEqual(original, runtime.stage_repository.load_request("PROD", run_id)["craft_guidance"])
        for role in ("registered_scene_projection", "surface_realization"):
            self.assertEqual(1, sum(job.runtime_role == role for job in fake.calls))
        calls = len(fake.calls)
        with self.assertRaises(ProductionRunError) as caught:
            self.execute(runtime, run_id, "baseline")
        self.assertEqual("execution_request_conflict", caught.exception.code)
        self.assertEqual(calls, len(fake.calls))

    def test_invalid_modes_fail_before_any_model_dispatch(self):
        for mode in ("genre_auto", "", {}, [], True, 1):
            fake = CraftFixtureRuntime()
            with self.subTest(mode=mode), self.assertRaises(ProductionRunError) as caught:
                self.execute(ProductionRunExecutor(self.store, fake), self.start(), mode)
            self.assertEqual("invalid_args", caught.exception.code)
            self.assertEqual([], fake.calls)

    def test_invalid_selected_id_stops_before_writers_without_retry(self):
        fake = CraftFixtureRuntime([choose("unregistered", "task:request")])
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        with self.assertRaises(ProductionRunError) as caught:
            self.execute(runtime, run_id, "outline_driven")
        self.assertEqual("semantic_output_invalid", caught.exception.code)
        count = len(fake.calls)
        with self.assertRaises(ProductionRunError):
            runtime.resume_execution("PROD", run_id)
        self.assertEqual(count, len(fake.calls))
        self.assertFalse(any(job.runtime_role == "surface_realization" for job in fake.calls))

    def test_repair_inherits_source_snapshot_and_new_explicit_run_can_opt_out(self):
        fake = fixtures.RepairFixtureRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        source_id = self.start()
        self.assertEqual("failed_gate", self.execute(runtime, source_id, "outline_driven")["status"])
        original = runtime.stage_repository.load_request("PROD", source_id)["craft_guidance"]
        for mode in (None, "outline_driven", "baseline"):
            source_ref = runtime.status("PROD", source_id)["repair_source"]
            run_id = fixtures.CoreOperations(self.store).start_author_run(
                "PROD", task_mode="REVISE", target_ref="DOC-1",
                payload={"chapter_id": "CH001", "repair_source": source_ref})["run_id"]
            fixtures.NovelWorkflowService(self.store).start(project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided")
            inherits = mode != "baseline"
            kwargs = {"side_effect": AssertionError("must inherit frozen edition")} if inherits else {"wraps": freeze_craft_library}
            with patch("production_runtime.runtime.freeze_craft_library", **kwargs):
                result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                         independent_provenance=fixtures.PROVENANCE, craft_guidance_mode=mode)
            self.assertEqual("awaiting_external", result["status"])
            snapshot = runtime.stage_repository.load_request("PROD", run_id)["craft_guidance"]
            self.assertEqual(original if inherits else freeze_craft_library(), snapshot)


if __name__ == "__main__":
    unittest.main()
