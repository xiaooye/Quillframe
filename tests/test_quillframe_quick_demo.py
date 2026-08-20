from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch
from pathlib import Path

from production_runtime.types import CharacterIntent, GenerationPacket, SceneIntent, TransitionConstraints
from production_runtime.workflow import NovelWorkflowEngine


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "demo" / "fixtures" / "ch001_quick_demo.json"
SITE_RUNTIME = ROOT / "site" / "public" / "generated" / "runtime"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packet(source: dict[str, object]) -> GenerationPacket:
    scene = source["scene_intent"]
    character = source["character_intent"]
    transition = source["transition_constraints"]
    assert isinstance(scene, dict) and isinstance(character, dict) and isinstance(transition, dict)
    return GenerationPacket.build(
        project_id=str(source["project_id"]),
        run_id=str(source["run_id"]),
        chapter_id=str(source["chapter_id"]),
        context_freeze_fingerprint=str(source["context_freeze_fingerprint"]),
        scene_intents=(SceneIntent(**scene),),
        character_intents=(CharacterIntent(**character),),
        transition_constraints=TransitionConstraints(**transition),
        task_profile_id=str(source["task_profile_id"]),
    )


class QuickDemoTests(unittest.TestCase):
    def test_quick_demo_fixture_is_ch001_and_matches_real_core(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(fixture["schema"], "quillframe_ch001_quick_demo_fixture_v1")
        self.assertEqual(fixture["chapter_id"], "CH001")
        self.assertEqual(fixture["semantic_evidence"]["source"], "recorded_fixture")
        self.assertIs(fixture["semantic_evidence"]["live_model_called"], False)
        self.assertIs(fixture["semantic_evidence"]["authority"], False)

        packet = _packet(fixture)
        self.assertEqual(packet.packet_fingerprint, fixture["expected"]["packet_fingerprint"])

        with patch("production_runtime.workflow._now", return_value=fixture["fixed_time"]):
            workflow = NovelWorkflowEngine.start(
                project_id=str(fixture["project_id"]),
                run_id=str(fixture["run_id"]),
                chapter_id=str(fixture["chapter_id"]),
                author_profile="guided",
            )
        snapshot = workflow.snapshot()
        self.assertEqual(snapshot["stage"], "intent")
        self.assertIs(snapshot["authority"], False)
        self.assertEqual(snapshot["snapshot_fingerprint"], fixture["expected"]["workflow_fingerprint"])

    def test_site_content_syncs_exact_demo_core_sources(self) -> None:
        manifest = json.loads((SITE_RUNTIME / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "quillframe_browser_core_manifest_v1")
        self.assertEqual(manifest["chapter_scope"], "CH001")
        self.assertIs(manifest["authority"], False)

        for source in ("workflow.py", "types.py"):
            canonical = ROOT / "production_runtime" / source
            browser_copy = SITE_RUNTIME / "production_runtime" / source
            self.assertEqual(browser_copy.read_bytes(), canonical.read_bytes())
            self.assertEqual(manifest["files"][f"production_runtime/{source}"], _sha256(canonical))

        self.assertEqual((SITE_RUNTIME / "ch001_quick_demo.json").read_bytes(), FIXTURE_PATH.read_bytes())

    def test_quick_demo_worker_discloses_execution_truth(self) -> None:
        worker = (ROOT / "site" / "src" / "quickDemo.worker.ts").read_text(encoding="utf-8")
        component = (ROOT / "site" / "src" / "QuickDemo.tsx").read_text(encoding="utf-8")

        self.assertIn("loadPyodide", worker)
        self.assertIn("../../production_runtime/workflow.py?raw", worker)
        self.assertIn("../../production_runtime/types.py?raw", worker)
        self.assertIn("quillframe_ch001_quick_demo_receipt_v1", worker)
        self.assertIn("recorded_fixture", worker)
        self.assertIn("live_model_called", worker)
        self.assertIn("Worker(new URL", component)
        self.assertIn("Deterministic Core", component)
        self.assertIn("Recorded semantic evidence", component)
        self.assertIn("0 uploads", component)
        self.assertIn("CH001", component)
