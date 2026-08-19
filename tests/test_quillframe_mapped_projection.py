from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from harness.project_projection import apply, fingerprint_bytes, materialize_context, preflight, preview, status
from persistence.quillframe_sqlite import QuillframeStore


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class MappedProjectionTests(unittest.TestCase):
    def _fixture(self, *, create_db: bool = True):
        td = tempfile.TemporaryDirectory(prefix="qf-mapped-projection-")
        root = Path(td.name) / "project"
        root.mkdir(parents=True)
        source = root / "design" / "CH001.md"
        source.parent.mkdir()
        source.write_text("# CH001\n22:30 freeze\n", encoding="utf-8")
        payload = {"chapter_id": "CH001", "title": "冻结点", "stages": ["draft"]}
        manifest = {
            "schema": "quillframe_runtime_context_manifest_v1",
            "project_id": "PROJECT-MAPPED-TEST",
            "sources": [{
                "stable_id": "CH-001",
                "source_path": "design/CH001.md",
                "source_fingerprint": _sha(source.read_bytes()),
                "object_type": "chapter_plan",
                "authority": "active_plan",
                "lifecycle": "planned",
                "domain": "story",
                "allowed_stages": ["draft", "reader_pressure"],
                "target": {"type": "story_node", "id": "CH-001", "kind": "chapter", "parent_id": None, "ordinal": 1, "title": "CH001", "document_id": "CH-001", "document_kind": "plan"},
                "runtime_payload": payload,
            }],
        }
        manifest_path = root / "runtime-context.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        (root / "quillframe.toml").write_text(
            """[quillframe]\nschema=\"quillframe_project_v1\"\nproject_schema_version=\"1\"\n[project]\nid=\"PROJECT-MAPPED-TEST\"\ntitle=\"Mapped\"\nlanguage=\"zh-CN\"\nversion=\"0.1.0\"\nstatus=\"active\"\n[paths]\nruntime_context_manifest=\"runtime-context.json\"\n""",
            encoding="utf-8",
        )
        data = Path(td.name) / "data"
        if create_db:
            QuillframeStore(data).create_project("PROJECT-MAPPED-TEST", "Mapped", "zh-CN")
        return td, root, data

    def test_preview_is_deterministic_and_does_not_mutate(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        first = preview(root)
        second = preview(root)
        self.assertEqual(first["projection_fingerprint"], second["projection_fingerprint"])
        self.assertEqual(first["manifest_fingerprint"], second["manifest_fingerprint"])
        self.assertEqual(first["model_invocations"], 0)
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM project_context_sources").fetchone()[0], 0)

    def test_apply_is_transactional_and_idempotent(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        compiled = preview(root)
        first = apply(root, data_dir=data)
        second = apply(root, data_dir=data)
        self.assertEqual(first, second)
        self.assertEqual(first["projection_fingerprint"], compiled["projection_fingerprint"])
        self.assertFalse(first["accepted"])
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM project_context_sources").fetchone()[0], 1)
            self.assertIsNotNone(conn.execute("SELECT node_id FROM story_nodes WHERE node_id='CH-001'").fetchone())
            self.assertIsNotNone(conn.execute("SELECT document_id FROM documents WHERE document_id='CH-001'").fetchone())
            for table in ("project_context_sources", "project_projection_receipts"):
                columns = {row[1]: row for row in conn.execute(f"PRAGMA table_info({table})")}
                self.assertIn("authority", columns)
                self.assertEqual(columns["authority"][4], "0")
        self.assertTrue(status(root, data_dir=data)["ready"])

    def test_apply_creates_missing_project_and_rolls_back_new_project_on_failure(self):
        td, root, data = self._fixture(create_db=False)
        self.addCleanup(td.cleanup)
        # The fixture's source remains durable, but the runtime DB is absent.
        location = QuillframeStore(data).location("PROJECT-MAPPED-TEST")
        self.assertFalse(location.database.exists())
        receipt = apply(root, data_dir=data)
        self.assertEqual(receipt["status"], "applied")
        self.assertTrue(location.database.exists())

        # A fresh absent DB must not remain after a target conflict during the
        # same transaction.
        td2, root2, data2 = self._fixture(create_db=False)
        self.addCleanup(td2.cleanup)
        source = root2 / "design" / "CH001.md"
        manifest_path = root2 / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["sources"][0]["target"]["title"] = "First"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        # Make a second target row with a conflicting target title while
        # preserving valid source/projection fingerprints.
        manifest["sources"].append({**manifest["sources"][0], "stable_id": "CH-002", "target": {"type": "story_node", "id": "CH-001", "kind": "chapter", "parent_id": None, "ordinal": 1, "title": "Conflict"}})
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        # Source fingerprints remain valid; preview reaches target validation.
        location2 = QuillframeStore(data2).location("PROJECT-MAPPED-TEST")
        with self.assertRaises(ValueError):
            apply(root2, data_dir=data2)
        self.assertFalse(location2.database.exists())

    def test_source_drift_and_authority_escalation_fail_closed(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        apply(root, data_dir=data)
        (root / "design" / "CH001.md").write_text("drift", encoding="utf-8")
        with self.assertRaises(ValueError):
            preview(root)
        # Restore source bytes, then make the Project-owned declaration unsafe.
        (root / "design" / "CH001.md").write_text("# CH001\n22:30 freeze\n", encoding="utf-8")
        manifest_path = root / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["sources"][0]["authority"] = "accepted"
        manifest["sources"][0]["source_fingerprint"] = _sha((root / "design" / "CH001.md").read_bytes())
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        with self.assertRaises(ValueError):
            preview(root)
        self.assertFalse(status(root, data_dir=data)["ready"])

    def test_replacement_requires_previous_projection_cas(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        first = apply(root, data_dir=data)
        source = root / "design" / "CH001.md"
        source.write_text("# CH001\nupdated\n", encoding="utf-8")
        manifest_path = root / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["sources"][0]["source_fingerprint"] = _sha(source.read_bytes())
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        current = preview(root)
        with self.assertRaises(ValueError):
            apply(root, data_dir=data)
        replaced = apply(root, data_dir=data, expected_projection_fingerprint=first["projection_fingerprint"])
        self.assertEqual(replaced["projection_fingerprint"], current["projection_fingerprint"])
        self.assertTrue(status(root, data_dir=data)["ready"])

    def test_foreign_project_database_identity_fails_closed(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        loc = QuillframeStore(data).location("PROJECT-MAPPED-TEST")
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            conn.execute("UPDATE project_identity SET project_id='FOREIGN' WHERE project_id='PROJECT-MAPPED-TEST'")
            conn.commit()
        with self.assertRaises(ValueError):
            apply(root, data_dir=data)
        self.assertFalse(status(root, data_dir=data)["ready"])

    def test_tampered_runtime_row_blocks_replay_and_preflight(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        receipt = apply(root, data_dir=data)
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            conn.execute("UPDATE project_context_sources SET runtime_payload_json='{}' WHERE stable_id='CH-001'")
            conn.commit()
        self.assertFalse(status(root, data_dir=data)["ready"])
        with self.assertRaises(ValueError):
            apply(root, data_dir=data)
        blocked = preflight(root, "CH-001", "draft", data_dir=data)
        self.assertFalse(blocked["ready"])
        self.assertEqual(blocked["model_invocations"], 0)

    def test_declared_context_boundary_rejects_foreign_target(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        manifest_path = root / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["context_set"] = {"allowed_object_ids": ["CH-001"]}
        manifest["target"] = {"story_node_id": "CH-001", "document_id": "CH-001"}
        manifest["sources"][0]["targets"] = ["CH-002"]
        manifest["sources"][0].pop("target", None)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        with self.assertRaises(ValueError):
            preview(root)

    def test_stage_bounded_context_and_zero_model_preflight(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        apply(root, data_dir=data)
        context = materialize_context(root, "draft", data_dir=data)
        self.assertEqual([item["stable_id"] for item in context["objects"]], ["CH-001"])
        self.assertEqual(context["model_invocations"], 0)
        ready = preflight(root, "CH-001", "draft", data_dir=data)
        self.assertTrue(ready["ready"])
        self.assertEqual(ready["model_invocations"], 0)
        missing = preflight(root, "CH-999", "draft", data_dir=data)
        self.assertFalse(missing["ready"])
        self.assertEqual(missing["model_invocations"], 0)

    def test_apply_rechecks_source_snapshot_inside_transaction(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        import harness.project_projection as projection
        original_preview = projection.preview
        calls = {"count": 0}

        def mutate_after_initial_preview(project_root, *, toml_manifest=None):
            result = original_preview(project_root, toml_manifest=toml_manifest)
            calls["count"] += 1
            if calls["count"] == 1:
                (root / "design" / "CH001.md").write_text("changed after preview", encoding="utf-8")
            return result

        projection.preview = mutate_after_initial_preview
        self.addCleanup(setattr, projection, "preview", original_preview)
        with self.assertRaisesRegex(ValueError, "snapshot|drift"):
            apply(root, data_dir=data)
        self.assertFalse(status(root, data_dir=data)["ready"])

    def test_manifest_project_identity_mismatch_fails_closed(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        manifest_path = root / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["project_id"] = "FOREIGN-PROJECT"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "project.*mismatch"):
            preview(root)

    def test_tampered_receipt_never_replays_as_authoritative(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        receipt = apply(root, data_dir=data)
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            conn.execute(
                "UPDATE project_projection_receipts SET receipt_json=? WHERE projection_fingerprint=?",
                (json.dumps({**receipt, "authority": True, "accepted": True, "settled": True}), receipt["projection_fingerprint"]),
            )
            conn.commit()
        with self.assertRaisesRegex(ValueError, "receipt"):
            apply(root, data_dir=data)
        self.assertFalse(status(root, data_dir=data)["ready"])

    def test_target_metadata_tamper_and_obsolete_targets_fail_closed(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        apply(root, data_dir=data)
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            conn.execute("UPDATE story_nodes SET metadata_json=? WHERE node_id='CH-001'", ('{"pov":"FOREIGN"}',))
            conn.commit()
        self.assertFalse(status(root, data_dir=data)["ready"])
        with self.assertRaisesRegex(ValueError, "target|projection"):
            apply(root, data_dir=data)

        # A replacement manifest may not leave a previously materialized
        # target outside the new bounded projection.
        td2, root2, data2 = self._fixture()
        self.addCleanup(td2.cleanup)
        manifest_path = root2 / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source2 = root2 / "design" / "CH002.md"
        source2.write_text("# CH002\n", encoding="utf-8")
        second = dict(manifest["sources"][0])
        second["stable_id"] = "CH-002"
        second["source_path"] = "design/CH002.md"
        second["source_fingerprint"] = _sha(source2.read_bytes())
        second["target"] = {"type": "story_node", "id": "CH-002", "kind": "chapter", "parent_id": None, "ordinal": 2, "title": "CH002", "document_id": "CH-002", "document_kind": "plan"}
        manifest["sources"].append(second)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        first = apply(root2, data_dir=data2)
        manifest["sources"] = [manifest["sources"][0]]
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        current = preview(root2)
        replaced = apply(root2, data_dir=data2, expected_projection_fingerprint=first["projection_fingerprint"])
        self.assertEqual(replaced["projection_fingerprint"], current["projection_fingerprint"])
        self.assertNotEqual(current["projection_fingerprint"], first["projection_fingerprint"])
        with QuillframeStore(data2).open_project("PROJECT-MAPPED-TEST") as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM story_nodes WHERE node_id='CH-002'").fetchone())
        self.assertFalse(preflight(root2, "CH-002", "draft", data_dir=data2)["ready"])

    def test_obsolete_preexisting_targets_are_never_deleted(self):
        td, root, data = self._fixture()
        self.addCleanup(td.cleanup)
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,parent_id,kind,ordinal,title) VALUES('CH-001',NULL,'chapter',1,'CH001')")
            conn.execute("INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES('CH-001','CH-001','plan','CH001','now')")
            conn.commit()
        first = apply(root, data_dir=data)
        manifest_path = root / "runtime-context.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["sources"] = []
        # Keep the manifest contract non-empty while removing the old target.
        source = root / "design" / "CH002.md"
        source.write_text("# CH002\n", encoding="utf-8")
        item = json.loads(json.dumps(manifest["sources"] or [{
            "stable_id": "CH-002", "source_path": "design/CH002.md", "source_fingerprint": _sha(source.read_bytes()),
            "object_type": "chapter_plan", "authority": "active_plan", "lifecycle": "planned", "domain": "story", "allowed_stages": ["draft"],
            "target": {"type": "story_node", "id": "CH-002", "kind": "chapter", "parent_id": None, "ordinal": 2, "title": "CH002", "document_id": "CH-002", "document_kind": "plan"}, "runtime_payload": {"chapter_id": "CH002"}
        }]))
        manifest["sources"] = item
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ownership"):
            apply(root, data_dir=data, expected_projection_fingerprint=first["projection_fingerprint"])
        with QuillframeStore(data).open_project("PROJECT-MAPPED-TEST") as conn:
            self.assertIsNotNone(conn.execute("SELECT 1 FROM story_nodes WHERE node_id='CH-001'").fetchone())
            self.assertIsNotNone(conn.execute("SELECT 1 FROM documents WHERE document_id='CH-001'").fetchone())

if __name__ == "__main__":
    unittest.main()
