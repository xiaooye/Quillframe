from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
import threading
import textwrap
import unittest
import zipfile
import ast
import inspect
from pathlib import Path
from unittest.mock import patch

import persistence.quillframe_sqlite as sqlite_persistence
from persistence.quillframe_sqlite import (
    QuillframeStore,
    RestoreError,
    RestoreIncompleteError,
    RestoreReplacementUnavailable,
)


class PersistenceC3BRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        source = QuillframeStore(self.root / "source")
        source.create_project("P1", "Source", "en")
        source.put_blob("P1", b"C3B blob payload", "text/plain")
        self.bundle = source.backup_project("P1")
        with zipfile.ZipFile(self.bundle) as archive:
            self.database_bytes = archive.read("project.sqlite")
            manifest = json.loads(archive.read("manifest.json"))
            self.blob_bytes = {
                row["relative_path"]: archive.read(row["relative_path"])
                for row in manifest["blobs"]
            }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
        if not os.path.lexists(root):
            return {}
        snapshot: dict[str, tuple[str, bytes | str | None]] = {}
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            stat_result = os.lstat(path)
            if os.path.islink(path):
                snapshot[relative] = ("symlink", os.readlink(path))
            elif stat.S_ISDIR(stat_result.st_mode):
                snapshot[relative] = ("dir", None)
            elif stat.S_ISREG(stat_result.st_mode):
                snapshot[relative] = ("file", path.read_bytes())
            else:
                snapshot[relative] = ("other", None)
            snapshot[relative + "#mode"] = ("mode", str(stat_result.st_mode))
        return snapshot

    @staticmethod
    def _registry_snapshot(store: QuillframeStore) -> list[tuple[object, ...]]:
        if not store.global_db.exists():
            return []
        conn = sqlite3.connect(store.global_db)
        try:
            return conn.execute(
                "SELECT project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at "
                "FROM project_registry ORDER BY project_id"
            ).fetchall()
        finally:
            conn.close()

    @staticmethod
    def _append_synthetic_journal(
        store: QuillframeStore,
        *,
        project_id: str,
        nonce: str,
        sequence: int,
        phase: str,
    ) -> Path:
        """Publish a schema-valid journal record without creating project state."""

        store.ensure_layout()
        root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(store.root, root_flags)
        try:
            record = QuillframeStore._restore_record(
                project_id=project_id,
                nonce=nonce,
                sequence=sequence,
                phase=phase,
                stage_name=f".{project_id}.restore-stage-{nonce}",
                stage_inode=None,
                target_inode=None,
                identity={
                    "project_id": project_id,
                    "title": f"Synthetic {project_id}",
                    "language": "en",
                    "project_schema_version": sqlite_persistence.SCHEMA_VERSION,
                },
                database_fingerprint=sqlite_persistence.fingerprint_bytes(b"synthetic"),
                blob_rows=(),
            )
            name = f".{project_id}.restore-{nonce}-{sequence:04d}.journal"
            sqlite_persistence._restore_write_journal(root_fd, name, record)
            return store.root / name
        finally:
            os.close(root_fd)

    def test_existing_target_replace_false_is_zero_write(self) -> None:
        store = QuillframeStore(self.root / "restore")
        store.create_project("P1", "Old", "zh-CN")
        before_registry = self._registry_snapshot(store)
        before_tree = self._tree_snapshot(store.root)
        with self.assertRaises(FileExistsError):
            store.restore_project(self.bundle, replace=False)
        self.assertEqual(self._tree_snapshot(store.root), before_tree)
        self.assertEqual(self._registry_snapshot(store), before_registry)

    def test_existing_target_replace_true_is_explicitly_unavailable_zero_write(self) -> None:
        store = QuillframeStore(self.root / "restore-replacement")
        store.create_project("P1", "Old", "zh-CN")
        before_tree = self._tree_snapshot(store.root)
        with self.assertRaises(RestoreReplacementUnavailable) as raised:
            store.restore_project(self.bundle, replace=True)
        self.assertEqual(raised.exception.code, "restore_replacement_unavailable")
        self.assertEqual(self._tree_snapshot(store.root), before_tree)

    def test_new_restore_uses_validated_bytes_and_no_legacy_writer(self) -> None:
        store = QuillframeStore(self.root / "restore")
        with patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("extractall forbidden")):
            with patch.object(QuillframeStore, "create_project", side_effect=AssertionError("create_project forbidden")):
                location = store.restore_project(self.bundle)
        self.assertEqual(location.database.read_bytes(), self.database_bytes)
        for relative_path, payload in self.blob_bytes.items():
            self.assertEqual((location.directory / relative_path).read_bytes(), payload)
        self.assertFalse(location.database.with_name("project.sqlite-wal").exists())
        self.assertFalse(location.database.with_name("project.sqlite-shm").exists())
        self.assertEqual(self._registry_snapshot(store)[0][0], "P1")
        self.assertEqual(self._registry_snapshot(store)[0][4], str(location.directory))

    def test_success_has_same_filesystem_and_terminal_journal_evidence(self) -> None:
        store = QuillframeStore(self.root / "restore")
        store.restore_project(self.bundle)
        self.assertEqual(os.stat(store.projects_root).st_dev, os.stat(store.location("P1").directory).st_dev)
        self.assertEqual(list(store.projects_root.glob(".P1.restore-stage-*")), [])
        journals = sorted(store.root.glob(".P1.restore-*.journal"))
        self.assertEqual(len(journals), 5)
        phases = [json.loads(path.read_text(encoding="utf-8"))["phase"] for path in journals]
        self.assertEqual(phases, ["STAGING", "PREPARED", "NEW_SWAPPED", "REGISTRY_UPSERTED", "COMMITTED"])
        self.assertEqual(json.loads(journals[-1].read_text(encoding="utf-8"))["retention"]["authority"], False)
        self.assertEqual(json.loads(journals[-1].read_text(encoding="utf-8"))["retention"]["contains_absolute_path"], False)
        before_recovery = [path.read_bytes() for path in journals]
        self.assertEqual(store.restore_recovery(), ["P1"])
        self.assertEqual([path.read_bytes() for path in journals], before_recovery)

    def test_competitor_created_before_noreplace_is_not_clobbered(self) -> None:
        store = QuillframeStore(self.root / "competitor")
        original = sqlite_persistence._rename_noreplace
        competitor = store.location("P1").directory
        sentinel = self.root / "competitor-sentinel"

        def race(source_fd: int, source_name: str, target_fd: int, target_name: str) -> None:
            competitor.mkdir(parents=True)
            (competitor / "sentinel").write_bytes(b"competitor")
            sentinel.write_bytes(b"outside")
            original(source_fd, source_name, target_fd, target_name)

        with patch.object(sqlite_persistence, "_rename_noreplace", side_effect=race):
            with self.assertRaises(RestoreError) as raised:
                store.restore_project(self.bundle)
        self.assertEqual(raised.exception.code, "restore_target_exists")
        self.assertEqual((competitor / "sentinel").read_bytes(), b"competitor")
        self.assertEqual(sentinel.read_bytes(), b"outside")
        self.assertEqual(len(list(store.projects_root.glob(".P1.restore-stage-*"))), 1)
        self.assertTrue(list(store.root.glob(".P1.restore-*.journal")))

    def _assert_recovery_closes_failure(self, phase: str) -> None:
        store = QuillframeStore(self.root / f"failure-{phase.lower()}")

        def inject(current_phase: str) -> None:
            if current_phase == phase:
                raise RuntimeError(f"injected {phase}")

        with patch.object(store, "_restore_fault_inject", side_effect=inject, create=True):
            with self.assertRaises(RestoreError):
                store.restore_project(self.bundle)
        self.assertTrue(list(store.root.glob(".P1.restore-*.journal")))
        self.assertTrue(store.location("P1").directory.is_dir())
        store.restore_recovery()
        self.assertEqual(store.location("P1").database.read_bytes(), self.database_bytes)
        self.assertEqual(len(self._registry_snapshot(store)), 1)
        journals_after_recovery = sorted(store.root.glob(".P1.restore-*.journal"))
        self.assertTrue(journals_after_recovery)
        terminal = json.loads(journals_after_recovery[-1].read_text(encoding="utf-8"))
        self.assertEqual(terminal["phase"], "COMMITTED")
        self.assertEqual(list(store.projects_root.glob(".P1.restore-stage-*")), [])
        snapshot = [path.read_bytes() for path in journals_after_recovery]
        self.assertEqual(store.restore_recovery(), ["P1"])
        self.assertEqual([path.read_bytes() for path in journals_after_recovery], snapshot)

    def test_injected_postpublish_failure_recovery(self) -> None:
        self._assert_recovery_closes_failure("NEW_SWAPPED")

    def test_injected_registry_failure_recovery(self) -> None:
        self._assert_recovery_closes_failure("REGISTRY_UPSERTED")

    def test_injected_commit_failure_recovery(self) -> None:
        self._assert_recovery_closes_failure("COMMITTED")

    def test_prepared_failure_retains_stage_and_aborted_evidence(self) -> None:
        store = QuillframeStore(self.root / "prepared-failure")

        def inject(current_phase: str) -> None:
            if current_phase == "PREPARED":
                raise RuntimeError("injected prepared")

        with patch.object(store, "_restore_fault_inject", side_effect=inject, create=True):
            with self.assertRaises(RestoreError):
                store.restore_project(self.bundle)
        self.assertFalse(store.location("P1").directory.exists())
        self.assertEqual(self._registry_snapshot(store), [])
        self.assertEqual(len(list(store.projects_root.glob(".P1.restore-stage-*"))), 1)
        journals = sorted(store.root.glob(".P1.restore-*.journal"))
        self.assertEqual(json.loads(journals[-1].read_text(encoding="utf-8"))["phase"], "ABORTED")

    def test_stage_write_failure_retains_stage_and_aborted_evidence(self) -> None:
        store = QuillframeStore(self.root / "write-failure")
        original = sqlite_persistence._restore_write_bytes_at

        def fail_once(directory_fd: int, relative_path: str, payload: bytes) -> None:
            if relative_path == "project.sqlite":
                raise OSError("injected stage write")
            original(directory_fd, relative_path, payload)

        with patch.object(sqlite_persistence, "_restore_write_bytes_at", side_effect=fail_once):
            with self.assertRaises(RestoreError):
                store.restore_project(self.bundle)
        self.assertEqual(len(list(store.projects_root.glob(".P1.restore-stage-*"))), 1)
        journals = sorted(store.root.glob(".P1.restore-*.journal"))
        self.assertEqual(json.loads(journals[-1].read_text(encoding="utf-8"))["phase"], "ABORTED")

    def test_restore_paths_have_no_destructive_cleanup_calls(self) -> None:
        forbidden = {"unlink", "rmdir", "remove", "replace", "extractall"}
        for method in (QuillframeStore.restore_project, QuillframeStore.restore_recovery):
            tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
            calls = {
                node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and (isinstance(node.func, ast.Attribute) or isinstance(node.func, ast.Name))
            }
            self.assertTrue(forbidden.isdisjoint(calls), (method.__name__, calls & forbidden))
        source = inspect.getsource(sqlite_persistence)
        self.assertNotIn("_restore_remove_owned_tree", source)
        self.assertNotIn("_restore_remove_owned_file", source)

    def test_journal_grouping_is_bounded_and_nonce_scoped(self) -> None:
        store = QuillframeStore(self.root / "bounded")
        store.restore_project(self.bundle)
        journals = sorted(store.root.glob(".P1.restore-*.journal"))
        self.assertLessEqual(len(journals), sqlite_persistence.MAX_RESTORE_JOURNAL_RECORDS)
        records = [json.loads(path.read_text(encoding="utf-8")) for path in journals]
        self.assertEqual(len({record["nonce"] for record in records}), 1)
        self.assertEqual([record["sequence"] for record in records], list(range(1, len(records) + 1)))

    def test_terminal_histories_do_not_consume_active_recovery_cap(self) -> None:
        store = QuillframeStore(self.root / "terminal-overflow")

        def inject(phase: str) -> None:
            if phase == "NEW_SWAPPED":
                raise RuntimeError("leave one active operation")

        with patch.object(store, "_restore_fault_inject", side_effect=inject, create=True):
            with self.assertRaises(RestoreError):
                store.restore_project(self.bundle)

        terminal_count = sqlite_persistence.MAX_RESTORE_JOURNAL_RECORDS + 1
        terminal_bytes: dict[Path, bytes] = {}
        for index in range(terminal_count):
            project_id = f"T{index:03d}"
            nonce = f"{index + 1:032x}"
            path = self._append_synthetic_journal(
                store,
                project_id=project_id,
                nonce=nonce,
                sequence=1,
                phase="ABORTED",
            )
            terminal_bytes[path] = path.read_bytes()

        recovered = store.restore_recovery()
        self.assertIn("P1", recovered)
        self.assertEqual(store.location("P1").database.read_bytes(), self.database_bytes)
        self.assertEqual(len(self._registry_snapshot(store)), 1)
        self.assertEqual({path: path.read_bytes() for path in terminal_bytes}, terminal_bytes)

    def test_nonterminal_active_records_still_fail_closed_at_cap(self) -> None:
        store = QuillframeStore(self.root / "active-overflow")
        active_count = max(
            sqlite_persistence.MAX_RESTORE_JOURNAL_RECORDS,
            sqlite_persistence.MAX_RESTORE_ACTIVE_OPERATIONS,
        ) + 1
        journal_bytes: dict[Path, bytes] = {}
        for index in range(active_count):
            project_id = f"A{index:03d}"
            nonce = f"{index + 1:032x}"
            path = self._append_synthetic_journal(
                store,
                project_id=project_id,
                nonce=nonce,
                sequence=1,
                phase="STAGING",
            )
            journal_bytes[path] = path.read_bytes()

        with self.assertRaises(RestoreIncompleteError) as raised:
            store.restore_recovery()
        self.assertEqual(raised.exception.code, "restore_incomplete")
        self.assertEqual({path: path.read_bytes() for path in journal_bytes}, journal_bytes)

    def test_latest_sequence_and_nonce_groups_exclude_terminal_history(self) -> None:
        store = QuillframeStore(self.root / "mixed-journal-groups")
        first_nonce = "a" * 32
        second_nonce = "b" * 32
        self._append_synthetic_journal(
            store,
            project_id="MIX",
            nonce=first_nonce,
            sequence=1,
            phase="STAGING",
        )
        first_terminal = self._append_synthetic_journal(
            store,
            project_id="MIX",
            nonce=first_nonce,
            sequence=2,
            phase="ABORTED",
        )
        second_terminal = self._append_synthetic_journal(
            store,
            project_id="MIX",
            nonce=second_nonce,
            sequence=1,
            phase="ABORTED",
        )
        other_terminal = self._append_synthetic_journal(
            store,
            project_id="OTHER",
            nonce="c" * 32,
            sequence=1,
            phase="ABORTED",
        )

        records = store._restore_recovery_records()
        latest = {
            (record["project_id"], record["nonce"]): record
            for _, record in records
        }
        self.assertEqual(latest[("MIX", first_nonce)]["phase"], "ABORTED")
        self.assertEqual(latest[("MIX", second_nonce)]["phase"], "ABORTED")
        self.assertEqual(latest[("OTHER", "c" * 32)]["phase"], "ABORTED")
        before = {
            path: path.read_bytes()
            for path in (first_terminal, second_terminal, other_terminal)
        }
        self.assertCountEqual(store.restore_recovery(), ["MIX", "MIX", "OTHER"])
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_unknown_journal_fails_closed_and_is_retained(self) -> None:
        store = QuillframeStore(self.root / "recovery")
        store.ensure_layout()
        journal = store.root / ".P1.restore-unknown-00000000000000000000000000000000-0001.journal"
        journal.write_text(json.dumps({"schema": "wrong", "project_id": "P1"}), encoding="utf-8")
        with self.assertRaises(RestoreIncompleteError):
            store.restore_recovery()
        self.assertTrue(journal.exists())

    def test_recovery_directory_entry_budget_accepts_exact_boundary(self) -> None:
        store = QuillframeStore(self.root / "directory-boundary")
        store.ensure_layout()
        budget = getattr(sqlite_persistence, "MAX_RESTORE_DIRECTORY_ENTRIES", None)
        self.assertIsInstance(budget, int)
        self.assertGreater(budget, 0)
        existing = len(list(store.root.iterdir()))
        for index in range(max(0, budget - existing)):
            (store.root / f"unrelated-{index:05d}").write_bytes(b"sentinel")
        self.assertEqual(len(list(store.root.iterdir())), budget)
        source = inspect.getsource(QuillframeStore._restore_recovery_records)
        self.assertNotIn("list(os.scandir", source)
        self.assertIn("with os.scandir", source)
        self.assertEqual(store.restore_recovery(), [])

    def test_recovery_directory_entry_budget_rejects_overflow_without_writes(self) -> None:
        store = QuillframeStore(self.root / "directory-overflow")
        store.ensure_layout()
        budget = getattr(sqlite_persistence, "MAX_RESTORE_DIRECTORY_ENTRIES", None)
        self.assertIsInstance(budget, int)
        self.assertGreater(budget, 0)
        existing = len(list(store.root.iterdir()))
        for index in range(max(0, budget + 1 - existing)):
            (store.root / f"unrelated-{index:05d}").write_bytes(b"sentinel")
        before = {
            path.name: path.read_bytes()
            for path in store.root.iterdir()
            if path.is_file()
        }
        with self.assertRaises(RestoreIncompleteError) as raised:
            store.restore_recovery()
        self.assertEqual(raised.exception.code, "restore_incomplete")
        after = {
            path.name: path.read_bytes()
            for path in store.root.iterdir()
            if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertEqual(len(list(store.root.iterdir())), budget + 1)

    def test_target_ancestor_symlink_fails_without_external_write(self) -> None:
        store = QuillframeStore(self.root / "symlink-target")
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_bytes(b"keep")
        store.root.mkdir()
        (store.root / "projects").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(RestoreError) as raised:
            store.restore_project(self.bundle)
        self.assertEqual(raised.exception.code, "restore_path")
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.assertFalse((outside / "P1").exists())

    def test_two_restore_writers_serialize_and_only_one_publishes(self) -> None:
        root = self.root / "serialized"
        barrier = threading.Barrier(2)
        results: list[object] = []
        stores = [QuillframeStore(root), QuillframeStore(root)]

        def run(store: QuillframeStore) -> None:
            def hook(phase: str) -> None:
                if phase == "BEFORE_GLOBAL_LOCK":
                    barrier.wait(timeout=5)

            with patch.object(store, "_restore_fault_inject", side_effect=hook, create=True):
                try:
                    results.append(store.restore_project(self.bundle, replace=False))
                except Exception as exc:  # result is asserted below
                    results.append(exc)

        threads = [threading.Thread(target=run, args=(store,)) for store in stores]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(isinstance(result, Exception) for result in results), 1)
        self.assertEqual(sum(not isinstance(result, Exception) for result in results), 1)
        self.assertEqual(len(self._registry_snapshot(stores[0])), 1)
        self.assertEqual(stores[0].location("P1").database.read_bytes(), self.database_bytes)


if __name__ == "__main__":
    unittest.main()
