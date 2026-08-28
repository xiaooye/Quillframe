from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from model_runtime.persistence import SQLiteModelServiceRepository
from persistence.quillframe_sqlite import QuillframeStore


class SQLiteConnectionHygieneTests(unittest.TestCase):
    def test_project_context_manager_closes_connection(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            store.create_project("P", "P")
            with store.open_project("P") as conn:
                self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
                self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_model_service_repository_closes_every_connection(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            repo = SQLiteModelServiceRepository(store)
            captured: list[sqlite3.Connection] = []
            original = repo._connect

            def capture():
                conn = original()
                captured.append(conn)
                return conn

            repo._connect = capture  # type: ignore[method-assign]
            self.assertEqual(repo.list_services(), [])
            self.assertTrue(captured)
            for conn in captured:
                with self.assertRaises(sqlite3.ProgrammingError):
                    conn.execute("SELECT 1")

    def test_backup_verify_restore_paths_remain_valid_with_closing_factory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = QuillframeStore(root)
            store.create_project("P", "P")
            store.create_document("P", "D", "D", document_kind="note")
            store.save_revision("P", "D", "text", expected_parent_revision_id=None, source="test")
            bundle = store.backup_project("P")
            self.assertTrue(store.verify_backup(bundle)["valid"])
            restored_root = root / "restored"
            restored = QuillframeStore(restored_root)
            loc = restored.restore_project(bundle)
            self.assertEqual(loc.project_id, "P")
            self.assertTrue(restored.doctor("P")["ok"])


if __name__ == "__main__":
    unittest.main()
