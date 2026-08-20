from __future__ import annotations

import sqlite3
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

import model_runtime.persistence as model_persistence
from model_runtime.persistence import SQLiteModelServiceRepository
from persistence import quillframe_sqlite
from persistence.quillframe_sqlite import (
    ProjectStateError,
    QuillframeStore,
    _connect,
    apply_schema,
    fingerprint_text,
)


class _FailingConnection:
    def __init__(self, failure_sql: str) -> None:
        self.failure_sql = failure_sql
        self.closed = False
        self.executed: list[str] = []
        self.row_factory = None

    def execute(self, sql: str, *args):  # noqa: ANN002, ANN003
        self.executed.append(sql)
        if sql == self.failure_sql:
            raise sqlite3.OperationalError("injected PRAGMA failure")
        return self

    def close(self) -> None:
        self.closed = True


class PersistenceSchemaC1Tests(unittest.TestCase):
    def _connect(self, path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def _fresh_global(self, path: Path) -> sqlite3.Connection:
        conn = self._connect(path)
        apply_schema(conn, "global")
        return conn

    def _fresh_project(self, path: Path) -> sqlite3.Connection:
        conn = self._connect(path)
        apply_schema(conn, "project")
        return conn

    def test_fresh_database_applies_all_fragments_and_complete_ledger_atomically(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            fragments = sorted((quillframe_sqlite.SCHEMA_FRAGMENTS_ROOT / "global").glob("*.sql"))
            ledger = [
                tuple(row)
                for row in conn.execute(
                    "SELECT scope,version,name,checksum FROM schema_fragments ORDER BY scope,version"
                )
            ]
            self.assertEqual(
                ledger,
                [
                    ("global", int(fragment.name.split("_", 1)[0]), fragment.name, fingerprint_text(fragment.read_text(encoding="utf-8")))
                    for fragment in fragments
                ],
            )
            self.assertEqual(
                tuple(conn.execute("SELECT scope,release FROM quillframe_schema_identity").fetchone()),
                ("global", "1.0"),
            )
            self.assertIn("model_services", {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
            conn.close()

    def test_existing_missing_ledger_is_rejected_without_repair_or_state_change(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            conn.execute("DELETE FROM schema_fragments WHERE scope='global' AND version=2")
            conn.commit()
            before = [tuple(row) for row in conn.execute("SELECT * FROM schema_fragments ORDER BY scope,version")]
            with self.assertRaises(ProjectStateError):
                apply_schema(conn, "global")
            after = [tuple(row) for row in conn.execute("SELECT * FROM schema_fragments ORDER BY scope,version")]
            self.assertEqual(after, before)
            conn.close()

    def test_existing_extra_ledger_row_is_rejected_without_deletion(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            conn.execute(
                "INSERT INTO schema_fragments(scope,version,name,checksum,applied_at) VALUES(?,?,?,?,?)",
                ("global", 99, "999_extra.sql", "sha256:" + "0" * 64, "now"),
            )
            conn.commit()
            with self.assertRaises(ProjectStateError):
                apply_schema(conn, "global")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_fragments WHERE version=99").fetchone()[0], 1)
            conn.close()

    def test_existing_structure_drift_is_rejected_without_repair(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            conn.execute("ALTER TABLE application_settings ADD COLUMN unexpected TEXT")
            conn.commit()
            with self.assertRaises(ProjectStateError):
                apply_schema(conn, "global")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(application_settings)")}
            self.assertIn("unexpected", columns)
            conn.close()

    def test_existing_missing_required_index_is_rejected_without_recreation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            conn.execute("DROP INDEX idx_discovered_models_service")
            conn.commit()
            with self.assertRaises(ProjectStateError):
                apply_schema(conn, "global")
            self.assertIsNone(
                conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", ("idx_discovered_models_service",)).fetchone()
            )
            conn.close()

    def test_existing_missing_required_trigger_is_rejected_without_recreation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "project.sqlite"
            conn = self._fresh_project(path)
            conn.execute("DROP TRIGGER production_candidate_one_pass_per_run_insert")
            conn.commit()
            with self.assertRaises(ProjectStateError):
                apply_schema(conn, "project")
            self.assertIsNone(
                conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger' AND name=?",
                    ("production_candidate_one_pass_per_run_insert",),
                ).fetchone()
            )
            conn.close()

    def test_existing_identity_drift_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            conn.execute("DELETE FROM quillframe_schema_identity")
            conn.commit()
            with self.assertRaises(ProjectStateError):
                apply_schema(conn, "global")
            self.assertIsNone(conn.execute("SELECT scope,release FROM quillframe_schema_identity").fetchone())
            conn.close()

    def test_fragment_failure_rolls_back_ledger_and_all_schema_objects(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "fragments"
            directory = root / "global"
            directory.mkdir(parents=True)
            (directory / "001_first.sql").write_text("CREATE TABLE first_table (id INTEGER);\n", encoding="utf-8")
            (directory / "002_broken.sql").write_text("CREATE TABLE broken_table (id INTEGER\n", encoding="utf-8")
            conn = self._connect(Path(td) / "global.sqlite")
            with patch.object(quillframe_sqlite, "SCHEMA_FRAGMENTS_ROOT", root):
                with self.assertRaises(ValueError):
                    apply_schema(conn, "global")
            objects = list(conn.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
            self.assertEqual(objects, [])
            conn.close()

    def test_existing_project_open_does_not_create_optional_trigram_search(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "project.sqlite"
            conn = self._fresh_project(path)
            conn.close()
            before_conn = sqlite3.connect(path)
            before = {
                row[0]: tuple(row)
                for row in before_conn.execute(
                    "SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                )
            }
            before_conn.close()
            # The complete native project schema is valid without the optional
            # trigram table. Opening it must not repair or otherwise write it.
            store = QuillframeStore(Path(td) / "root")
            store.projects_root.mkdir(parents=True)
            project_dir = store.location("P").directory
            project_dir.mkdir(parents=True)
            target = project_dir / "project.sqlite"
            target.write_bytes(path.read_bytes())
            before_bytes = hashlib.sha256(target.read_bytes()).hexdigest()
            before_sidecars = sorted(item.name for item in project_dir.iterdir())
            opened = store.open_project("P")
            opened.close()
            after_conn = sqlite3.connect(target)
            after = {
                row[0]: tuple(row)
                for row in after_conn.execute(
                    "SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                )
            }
            after_conn.close()
            self.assertEqual(after, before)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), before_bytes)
            self.assertEqual(sorted(item.name for item in project_dir.iterdir()), before_sidecars)
            check_conn = sqlite3.connect(target)
            self.assertIsNone(check_conn.execute("SELECT name FROM sqlite_master WHERE name='search_trigram'").fetchone())
            check_conn.close()

    def test_schema_fragment_gap_is_rejected_before_fresh_database_write(self):
        with tempfile.TemporaryDirectory() as td:
            fragment_root = Path(td) / "fragments"
            directory = fragment_root / "global"
            directory.mkdir(parents=True)
            (directory / "001_first.sql").write_text("CREATE TABLE first_table (id INTEGER);\n", encoding="utf-8")
            (directory / "003_third.sql").write_text("CREATE TABLE third_table (id INTEGER);\n", encoding="utf-8")
            path = Path(td) / "global.sqlite"
            conn = self._connect(path)
            with patch.object(quillframe_sqlite, "SCHEMA_FRAGMENTS_ROOT", fragment_root):
                with self.assertRaises(quillframe_sqlite.SchemaContractError):
                    apply_schema(conn, "global")
            self.assertEqual(list(conn.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")), [])
            conn.close()

    def test_schema_fragment_gap_is_rejected_without_existing_database_write(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            before = [tuple(row) for row in conn.execute("SELECT * FROM schema_fragments ORDER BY scope,version")]
            fragment_root = Path(td) / "fragments"
            directory = fragment_root / "global"
            directory.mkdir(parents=True)
            (directory / "001_first.sql").write_text("CREATE TABLE first_table (id INTEGER);\n", encoding="utf-8")
            (directory / "003_third.sql").write_text("CREATE TABLE third_table (id INTEGER);\n", encoding="utf-8")
            with patch.object(quillframe_sqlite, "SCHEMA_FRAGMENTS_ROOT", fragment_root):
                with self.assertRaises(quillframe_sqlite.SchemaContractError):
                    apply_schema(conn, "global")
            self.assertEqual([tuple(row) for row in conn.execute("SELECT * FROM schema_fragments ORDER BY scope,version")], before)
            conn.close()

    def test_global_schema_rejects_optional_project_trigram_table_without_write(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "global.sqlite"
            conn = self._fresh_global(path)
            conn.execute("CREATE VIRTUAL TABLE search_trigram USING fts5(entity_type, entity_id, title, body, tokenize='trigram')")
            conn.commit()
            before = [tuple(row) for row in conn.execute("SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")]
            with self.assertRaises(quillframe_sqlite.SchemaContractError):
                apply_schema(conn, "global")
            after = [tuple(row) for row in conn.execute("SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")]
            self.assertEqual(after, before)
            conn.close()


class PersistenceConnectionFailureC1Tests(unittest.TestCase):
    def test_connect_closes_when_pragma_initialization_fails(self):
        with tempfile.TemporaryDirectory() as td:
            fake = _FailingConnection("PRAGMA busy_timeout=5000")
            with patch.object(quillframe_sqlite.sqlite3, "connect", return_value=fake):
                with self.assertRaises(sqlite3.OperationalError):
                    _connect(Path(td) / "global.sqlite")
            self.assertTrue(fake.closed)

    def test_model_repository_connect_closes_when_pragma_initialization_fails(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            store.initialize_global()
            repo = SQLiteModelServiceRepository(store)
            fake = _FailingConnection("PRAGMA busy_timeout=5000")
            with patch.object(model_persistence.sqlite3, "connect", return_value=fake):
                with self.assertRaises(sqlite3.OperationalError):
                    repo._connect()
            self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()
