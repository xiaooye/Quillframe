from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from persistence.quillframe_sqlite import ConflictError, QuillframeStore


class PersistenceC2RevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = QuillframeStore(self.root)
        self.store.create_project("P1", "Project")
        with self.store.open_project("P1") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH001','chapter',1,'Chapter','{}')")
            conn.commit()
        self.store.create_document("P1", "DOC1", "Document", story_node_id="CH001")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _trace_business_order(self) -> list[str]:
        statements: list[str] = []
        original_connect = self.store._connect

        def connect(path: Path, **kwargs: object):
            conn = original_connect(path, **kwargs)

            def trace(statement: str) -> None:
                normalized = " ".join(statement.split()).upper()
                if (
                    normalized == "BEGIN IMMEDIATE"
                    or "FROM DOCUMENT_REVISIONS" in normalized
                    or "FROM DOCUMENTS" in normalized
                ):
                    statements.append(normalized)

            conn.set_trace_callback(trace)
            return conn

        self.store._connect = connect  # type: ignore[method-assign]
        try:
            self.store.save_revision(
                "P1",
                "DOC1",
                "first",
                expected_parent_revision_id=None,
                source="test",
            )
        finally:
            self.store._connect = original_connect  # type: ignore[method-assign]
        return statements

    def _run_two_writers(self, contents: tuple[str, str]) -> list[tuple[str, object]]:
        barrier = threading.Barrier(2, timeout=15)
        original_connect = self.store._connect
        results: list[tuple[str, object] | None] = [None, None]

        def connect(path: Path, **kwargs: object):
            conn = original_connect(path, **kwargs)

            def trace(statement: str) -> None:
                normalized = " ".join(statement.split()).upper()
                if normalized == "BEGIN IMMEDIATE":
                    barrier.wait()

            conn.set_trace_callback(trace)
            return conn

        def worker(index: int) -> None:
            try:
                result = self.store.save_revision(
                    "P1",
                    "DOC1",
                    contents[index],
                    expected_parent_revision_id=None,
                    source=f"writer-{index}",
                )
                results[index] = ("ok", result)
            except BaseException as exc:  # preserve worker failures for assertions
                results[index] = ("error", exc)

        self.store._connect = connect  # type: ignore[method-assign]
        threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)
            self.assertTrue(all(not thread.is_alive() for thread in threads), results)
        finally:
            self.store._connect = original_connect  # type: ignore[method-assign]
        self.assertTrue(all(result is not None for result in results), results)
        return [result for result in results if result is not None]

    def _assert_write_lock_is_available(self) -> None:
        with self.store.open_project("P1") as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.rollback()

    def _search_rows(self) -> list[tuple[object, ...]]:
        with self.store.open_project("P1") as conn:
            return [
                tuple(row)
                for row in conn.execute(
                    "SELECT entity_type,entity_id,title,body FROM search_index ORDER BY entity_type,entity_id"
                )
            ]

    def test_save_revision_begins_transaction_before_business_reads(self) -> None:
        statements = self._trace_business_order()
        self.assertEqual(statements[0], "BEGIN IMMEDIATE", statements)
        self.assertTrue(any("FROM DOCUMENTS" in statement for statement in statements), statements)
        self.assertTrue(any("FROM DOCUMENT_REVISIONS" in statement for statement in statements), statements)

    def test_different_contents_same_parent_have_one_success_and_one_conflict(self) -> None:
        results = self._run_two_writers(("first writer", "second writer"))
        successes = [payload for status, payload in results if status == "ok"]
        conflicts = [payload for status, payload in results if status == "error" and isinstance(payload, ConflictError)]
        self.assertEqual(len(successes), 1, results)
        self.assertEqual(len(conflicts), 1, results)
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM document_revisions").fetchone()[0], 1)
        self._assert_write_lock_is_available()

    def test_same_contents_same_parent_are_one_insert_and_one_stable_dedup(self) -> None:
        results = self._run_two_writers(("same writer content", "same writer content"))
        successes = [payload for status, payload in results if status == "ok"]
        self.assertEqual(len(successes), 2, results)
        self.assertEqual({payload["revision_id"] for payload in successes}, {successes[0]["revision_id"]})
        self.assertCountEqual([payload["deduplicated"] for payload in successes], [False, True])
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM document_revisions").fetchone()[0], 1)
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM search_index WHERE entity_type='document' AND entity_id='DOC1'"
                ).fetchone()[0],
                1,
            )
        self._assert_write_lock_is_available()

    def test_stale_parent_dedup_is_stable_and_stale_different_content_conflicts(self) -> None:
        first = self.store.save_revision(
            "P1", "DOC1", "first", expected_parent_revision_id=None, source="test"
        )
        duplicate = self.store.save_revision(
            "P1", "DOC1", "first", expected_parent_revision_id=None, source="retry"
        )
        self.assertEqual(duplicate["revision_id"], first["revision_id"])
        self.assertTrue(duplicate["deduplicated"])
        with self.assertRaises(ConflictError):
            self.store.save_revision(
                "P1", "DOC1", "different", expected_parent_revision_id=None, source="test"
            )
        self._assert_write_lock_is_available()

    def test_unknown_document_is_key_error_without_revision_or_search_mutation(self) -> None:
        before_search = self._search_rows()
        with self.assertRaises(KeyError):
            self.store.save_revision(
                "P1", "MISSING", "content", expected_parent_revision_id=None, source="test"
            )
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM document_revisions").fetchone()[0], 0)
        self.assertEqual(self._search_rows(), before_search)
        self._assert_write_lock_is_available()

    def test_index_failure_rolls_back_revision_and_all_search_tables(self) -> None:
        before_search = self._search_rows()
        original_index = self.store.index_search

        def fail_after_index(
            conn: sqlite3.Connection,
            entity_type: str,
            entity_id: str,
            title: str,
            body: str,
            *,
            commit: bool = True,
        ) -> None:
            original_index(conn, entity_type, entity_id, title, body, commit=commit)
            raise sqlite3.OperationalError("injected search index failure")

        with patch.object(self.store, "index_search", side_effect=fail_after_index):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.save_revision(
                    "P1", "DOC1", "rolled back", expected_parent_revision_id=None, source="test"
                )
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM document_revisions").fetchone()[0], 0)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0], len(before_search)
            )
            if conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='search_trigram'"
            ).fetchone():
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM search_trigram").fetchone()[0], len(before_search)
                )
        self.assertEqual(self._search_rows(), before_search)
        self._assert_write_lock_is_available()


if __name__ == "__main__":
    unittest.main()
