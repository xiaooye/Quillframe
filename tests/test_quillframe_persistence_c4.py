from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_runtime.workflow_service as workflow_service
from persistence.quillframe_sqlite import QuillframeStore, now_iso
from production_runtime.workflow_service import NovelWorkflowService
from production_runtime.workflow import WorkflowError


RUN_ID = "run_" + "a" * 32


class PersistenceC4WorkflowLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = QuillframeStore(self.root / "store")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create_project(self, project_id: str) -> None:
        self.store.create_project(project_id, f"Project {project_id}", "en")

    def _save_workflow(self, project_id: str, run_id: str = RUN_ID) -> None:
        with self.store.open_project(project_id) as conn:
            stamp = now_iso()
            conn.execute(
                "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (run_id, "DRAFT", "CH001", "awaiting_semantic", "sha256:" + "b" * 64, stamp, stamp),
            )
            conn.commit()
        NovelWorkflowService(self.store).start(
            project_id=project_id,
            run_id=run_id,
            chapter_id="CH001",
            author_profile="guided",
        )

    def _assert_unavailable(self, raised: unittest.case._AssertRaisesContext) -> None:
        self.assertEqual(raised.exception.code, "workflow_project_unavailable")
        self.assertNotIn(str(self.root), str(raised.exception))
        self.assertNotIn("not sqlite", str(raised.exception))

    def test_internal_registry_iterator_is_complete_keyset_and_public_cap_stays_500(self) -> None:
        for index in range(7):
            self._create_project(f"P{index:03d}")
        iterator = getattr(QuillframeStore, "iter_project_ids_internal", None)
        self.assertIsNotNone(iterator)
        iterator_source = __import__("inspect").getsource(iterator)
        self.assertNotIn("OFFSET", iterator_source.upper())
        self.assertEqual(
            list(self.store.iter_project_ids_internal(page_size=2, max_projects=7)),
            [f"P{index:03d}" for index in range(7)],
        )
        self.assertLessEqual(len(self.store.list_projects(limit=500)), 500)

    def test_501st_registry_project_resolves_without_public_projection(self) -> None:
        for index in range(501):
            self._create_project(f"P{index:03d}")
        conn = sqlite3.connect(self.store.global_db)
        try:
            conn.execute(
                "UPDATE project_registry SET last_opened_at=? WHERE project_id != ?",
                ("2026-08-20T00:00:00+00:00", "P500"),
            )
            conn.execute(
                "UPDATE project_registry SET last_opened_at=? WHERE project_id=?",
                ("2000-01-01T00:00:00+00:00", "P500"),
            )
            conn.commit()
        finally:
            conn.close()
        self._save_workflow("P500")
        with patch.object(self.store, "list_projects", side_effect=AssertionError("public projection forbidden")):
            self.assertEqual(NovelWorkflowService(self.store).resolve_project(RUN_ID), "P500")

    def test_cross_project_same_run_is_ambiguous_but_duplicate_rows_in_one_project_are_one_match(self) -> None:
        self._create_project("P1")
        self._save_workflow("P1")
        with self.store.open_project("P1") as conn:
            row = conn.execute(
                "SELECT run_id,state_json,artifact_fingerprint,created_at FROM checkpoints WHERE run_id=?",
                (RUN_ID,),
            ).fetchone()
            conn.execute(
                "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,?,?,?,?)",
                ("workflow:duplicate", RUN_ID, "novel_workflow_v1", row["state_json"], row["artifact_fingerprint"], row["created_at"]),
            )
            conn.commit()
        self.assertEqual(NovelWorkflowService(self.store).resolve_project(RUN_ID), "P1")

        self._create_project("P2")
        self._save_workflow("P2")
        with self.assertRaises(WorkflowError) as raised:
            NovelWorkflowService(self.store).resolve_project(RUN_ID)
        self.assertEqual(raised.exception.code, "workflow_identity_ambiguous")

    def test_missing_or_corrupt_registered_project_is_unavailable(self) -> None:
        self._create_project("P1")
        self.store.location("P1").database.unlink()
        with self.assertRaises(WorkflowError) as raised:
            NovelWorkflowService(self.store).resolve_project(RUN_ID)
        self._assert_unavailable(raised)

        self._create_project("P2")
        self.store.location("P2").database.write_bytes(b"not sqlite")
        with self.assertRaises(WorkflowError) as raised:
            NovelWorkflowService(self.store).resolve_project(RUN_ID)
        self._assert_unavailable(raised)

    def test_identity_corruption_and_unreadable_wal_are_unavailable(self) -> None:
        self._create_project("P1")
        with self.store.open_project("P1") as conn:
            conn.execute("UPDATE project_identity SET project_id='OTHER'")
            conn.commit()
        with self.assertRaises(WorkflowError) as raised:
            NovelWorkflowService(self.store).resolve_project(RUN_ID)
        self._assert_unavailable(raised)

        self._create_project("P2")
        database = self.store.location("P2").database
        database.with_name(database.name + "-wal").write_bytes(b"invalid wal")
        with self.assertRaises(WorkflowError) as raised:
            NovelWorkflowService(self.store).resolve_project(RUN_ID)
        self._assert_unavailable(raised)

    def test_missing_global_registry_is_distinct_from_empty_registry(self) -> None:
        missing = NovelWorkflowService(self.store)
        with self.assertRaises(WorkflowError) as raised:
            missing.resolve_project(RUN_ID)
        self.assertEqual(raised.exception.code, "workflow_project_registry_unavailable")
        self.assertNotIn(str(self.root), str(raised.exception))

        empty_store = QuillframeStore(self.root / "empty")
        empty_store.initialize_global()
        empty_store.projects_root.joinpath("filesystem-only").mkdir(parents=True)
        with self.assertRaises(WorkflowError) as raised:
            NovelWorkflowService(empty_store).resolve_project(RUN_ID)
        self.assertEqual(raised.exception.code, "workflow_not_found")

    def test_registry_path_is_not_a_project_locator(self) -> None:
        self._create_project("P1")
        self._save_workflow("P1")
        external = self.root / "external"
        external.mkdir()
        (external / "project.sqlite").write_bytes(b"external sentinel")
        conn = sqlite3.connect(self.store.global_db)
        try:
            conn.execute(
                "UPDATE project_registry SET project_dir=?,last_opened_at=? WHERE project_id=?",
                (str(external), now_iso(), "P1"),
            )
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(NovelWorkflowService(self.store).resolve_project(RUN_ID), "P1")
        self.assertEqual((external / "project.sqlite").read_bytes(), b"external sentinel")

    def test_internal_registry_iterator_holds_one_read_snapshot_across_pages(self) -> None:
        for index in range(3):
            self._create_project(f"P{index}")
        original_connect = self.store._connect
        select_count = 0

        def connect(path: Path, **kwargs):  # noqa: ANN001
            nonlocal select_count
            conn = original_connect(path, **kwargs)

            def trace(statement: str) -> None:
                nonlocal select_count
                if statement.startswith("SELECT project_id FROM project_registry"):
                    select_count += 1
                    if select_count == 2:
                        writer = sqlite3.connect(self.store.global_db)
                        try:
                            stamp = now_iso()
                            writer.execute(
                                "INSERT INTO project_registry(project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at) VALUES(?,?,?,?,?,?,?)",
                                ("P999", "Late", "en", 1, str(self.root / "external"), stamp, stamp),
                            )
                            writer.commit()
                        finally:
                            writer.close()

            conn.set_trace_callback(trace)
            return conn

        with patch.object(self.store, "_connect", side_effect=connect):
            self.assertEqual(
                list(self.store.iter_project_ids_internal(page_size=1, max_projects=3)),
                ["P0", "P1", "P2"],
            )

    def test_invalid_run_id_is_rejected_before_registry_scan(self) -> None:
        self._create_project("P1")
        service = NovelWorkflowService(self.store)
        with patch.object(
            self.store,
            "iter_project_ids_internal",
            side_effect=AssertionError("scan forbidden"),
            create=True,
        ):
            for invalid in ("", "R", "run_" + "g" * 32, "run_' OR 1=1 --"):
                with self.assertRaises(WorkflowError) as raised:
                    service.resolve_project(invalid)
                self.assertEqual(raised.exception.code, "workflow_invalid_run_id")

    def test_registry_lookup_limit_is_stable_and_not_not_found(self) -> None:
        for index in range(3):
            self._create_project(f"P{index}")
        with patch.object(workflow_service, "MAX_WORKFLOW_PROJECTS", 2, create=True):
            with self.assertRaises(WorkflowError) as raised:
                NovelWorkflowService(self.store).resolve_project(RUN_ID)
        self.assertEqual(raised.exception.code, "workflow_project_lookup_bounded")
        self.assertNotIn(str(self.root), str(raised.exception))


if __name__ == "__main__":
    unittest.main()
