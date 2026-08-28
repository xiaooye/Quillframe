from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path

from persistence.quillframe_sqlite import QuillframeStore, canonical_json, now_iso
from production_runtime.workflow import WorkflowError
from production_runtime.workflow_service import NovelWorkflowService


RUN_ID = "run_" + "a" * 32
SENTINEL = "Q2A-PERSISTENCE-SENTINEL"


class _BeginImmediateBarrierConnection:
    def __init__(self, connection, barrier):
        self._connection = connection
        self._barrier = barrier

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self._connection.__exit__(exc_type, exc, traceback)

    def execute(self, sql, parameters=()):
        if sql.strip().upper() == "BEGIN IMMEDIATE":
            self._barrier.wait(timeout=5)
        return self._connection.execute(sql, parameters)


class _BeginImmediateBarrierStore(QuillframeStore):
    def __init__(self, root, barrier):
        super().__init__(root)
        self._barrier = barrier

    def open_project(self, project_id):
        return _BeginImmediateBarrierConnection(super().open_project(project_id), self._barrier)


class _InjectedFailureConnection:
    def __init__(self, connection, failure_kind):
        self._connection = connection
        self._failure_kind = failure_kind
        self.in_transaction_before_exit = None
        self._commit_failed = False

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.in_transaction_before_exit = self._connection.in_transaction
        return self._connection.__exit__(exc_type, exc, traceback)

    def execute(self, sql, parameters=()):
        normalized = sql.strip().upper()
        if self._failure_kind == "checkpoint" and normalized.startswith("INSERT INTO CHECKPOINTS"):
            raise RuntimeError(SENTINEL)
        if self._failure_kind == "event" and normalized.startswith("INSERT INTO RUNTIME_EVENTS"):
            raise RuntimeError(SENTINEL)
        return self._connection.execute(sql, parameters)

    def commit(self):
        if self._failure_kind == "commit" and not self._commit_failed:
            self._commit_failed = True
            raise RuntimeError(SENTINEL)
        return self._connection.commit()


class _InjectedFailureStore(QuillframeStore):
    def __init__(self, root, failure_kind):
        super().__init__(root)
        self._failure_kind = failure_kind
        self.last_connection = None

    def open_project(self, project_id):
        self.last_connection = _InjectedFailureConnection(super().open_project(project_id), self._failure_kind)
        return self.last_connection


class CoreQ2AWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="qf-q2a-")
        self.root = Path(self.temp.name) / "store"
        self.store = QuillframeStore(self.root)
        self.store.create_native_project("P", "Project P", "en")
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute(
                "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (RUN_ID, "DRAFT", "CH001", "awaiting_semantic", "sha256:" + "b" * 64, stamp, stamp),
            )
            conn.commit()
        self.service = NovelWorkflowService(self.store)
        self.service.start(project_id="P", run_id=RUN_ID, chapter_id="CH001", author_profile="guided")
        engine = self.service.load("P", RUN_ID)
        paused = engine.pause(reason="pause for Q2-A", idempotency_key="pause-q2a")
        self.service.save("P", engine)
        self.pause_cursor = paused["cursor"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run_two_barrier(self, callback):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker(index):
            try:
                results.append(callback(NovelWorkflowService(_BeginImmediateBarrierStore(self.root, barrier)), index))
            except Exception as exc:  # pragma: no cover - asserted by caller
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(0,)), threading.Thread(target=worker, args=(1,))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return results, errors

    def _counts(self):
        with self.store.open_project("P") as conn:
            return (
                conn.execute("SELECT COUNT(*) FROM checkpoints WHERE run_id=?", (RUN_ID,)).fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_kind='novel_workflow_event_v1'", (RUN_ID,)).fetchone()[0],
            )

    def test_resume_different_keys_use_locked_cursor_cas(self):
        results, errors = self._run_two_barrier(
            lambda service, index: service.resume(
                project_id="P", run_id=RUN_ID, cursor=self.pause_cursor,
                idempotency_key=f"resume-q2a-{index}",
            )
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], WorkflowError)
        self.assertEqual(errors[0].code, "cursor_conflict")
        self.assertEqual(results[0]["event_type"], "resumed")
        self.assertEqual(self._counts(), (3, 3))

    def test_cancel_different_keys_use_locked_cursor_cas(self):
        results, errors = self._run_two_barrier(
            lambda service, index: service.cancel(
                project_id="P", run_id=RUN_ID, cursor=self.pause_cursor,
                idempotency_key=f"cancel-q2a-{index}", user_authorized=True,
            )
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], WorkflowError)
        self.assertEqual(errors[0].code, "cursor_conflict")
        self.assertEqual(results[0]["event_type"], "cancelled")
        self.assertEqual(self._counts(), (3, 3))

    def test_cancel_same_key_replays_exact_event_before_old_cursor_conflict(self):
        first = self.service.cancel(
            project_id="P", run_id=RUN_ID, cursor=self.pause_cursor,
            idempotency_key="cancel-q2a-replay", user_authorized=True,
        )
        replay = self.service.cancel(
            project_id="P", run_id=RUN_ID, cursor=self.pause_cursor,
            idempotency_key="cancel-q2a-replay", user_authorized=True,
        )
        self.assertEqual(canonical_json(first), canonical_json(replay))
        self.assertEqual(self._counts(), (3, 3))
        with self.store.open_project("P") as conn:
            row = conn.execute(
                "SELECT payload_json FROM runtime_events WHERE event_id=?",
                (f"workflow:{RUN_ID}:event:{first['cursor']}",),
            ).fetchone()
        self.assertEqual(canonical_json(first), row["payload_json"])

    def test_same_key_cross_action_is_typed_idempotency_conflict(self):
        before = self._counts()
        with self.assertRaises(WorkflowError) as raised:
            self.service.resume(
                project_id="P", run_id=RUN_ID, cursor=self.pause_cursor,
                idempotency_key="pause-q2a",
            )
        self.assertEqual(raised.exception.code, "idempotency_conflict")
        self.assertEqual(self._counts(), before)

    def test_same_key_different_expected_cursor_is_typed_idempotency_conflict(self):
        first = self.service.cancel(
            project_id="P", run_id=RUN_ID, cursor=self.pause_cursor,
            idempotency_key="cancel-q2a-request-bound", user_authorized=True,
        )
        with self.assertRaises(WorkflowError) as raised:
            self.service.cancel(
                project_id="P", run_id=RUN_ID, cursor=first["cursor"],
                idempotency_key="cancel-q2a-request-bound", user_authorized=True,
            )
        self.assertEqual(raised.exception.code, "idempotency_conflict")
        self.assertEqual(self._counts(), (3, 3))

    def test_failed_checkpoint_event_or_commit_rolls_back_and_retry_succeeds(self):
        for failure_kind in ("checkpoint", "event", "commit"):
            temp = tempfile.TemporaryDirectory(prefix=f"qf-q2a-{failure_kind}-")
            try:
                root = Path(temp.name) / "store"
                store = QuillframeStore(root)
                store.create_native_project("P", "Project P", "en")
                stamp = now_iso()
                with store.open_project("P") as conn:
                    conn.execute(
                        "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        (RUN_ID, "DRAFT", "CH001", "awaiting_semantic", "sha256:" + "b" * 64, stamp, stamp),
                    )
                    conn.commit()
                service = NovelWorkflowService(store)
                service.start(project_id="P", run_id=RUN_ID, chapter_id="CH001", author_profile="guided")
                engine = service.load("P", RUN_ID)
                paused = engine.pause(reason="pause", idempotency_key="pause")
                service.save("P", engine)
                failing_store = _InjectedFailureStore(root, failure_kind)
                failing_service = NovelWorkflowService(failing_store)
                with self.assertRaises(WorkflowError) as raised:
                    failing_service.resume(
                        project_id="P", run_id=RUN_ID, cursor=paused["cursor"],
                        idempotency_key=f"resume-failed-{failure_kind}",
                    )
                self.assertEqual(raised.exception.code, "workflow_persistence_failed")
                self.assertNotIn(SENTINEL, str(raised.exception))
                self.assertFalse(failing_store.last_connection.in_transaction_before_exit)
                with store.open_project("P") as conn:
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM checkpoints WHERE run_id=?", (RUN_ID,)).fetchone()[0], 2)
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM runtime_events WHERE run_id=?", (RUN_ID,)).fetchone()[0], 2)
                retry = service.resume(
                    project_id="P", run_id=RUN_ID, cursor=paused["cursor"],
                    idempotency_key=f"resume-retry-{failure_kind}",
                )
                self.assertEqual(retry["event_type"], "resumed")
            finally:
                temp.cleanup()

    def test_load_events_resume_and_cancel_fail_closed_for_row_fingerprint(self):
        before = self._counts()
        with self.store.open_project("P") as conn:
            conn.execute(
                "UPDATE checkpoints SET artifact_fingerprint=? WHERE checkpoint_id=?",
                ("sha256:" + "c" * 64, f"workflow:{RUN_ID}:{self.pause_cursor}"),
            )
            conn.commit()
        for action in (
            lambda: self.service.load("P", RUN_ID),
            lambda: self.service.events(run_id=RUN_ID, cursor=-1),
            lambda: self.service.resume(project_id="P", run_id=RUN_ID, cursor=self.pause_cursor, idempotency_key="bad-fp-resume"),
            lambda: self.service.cancel(project_id="P", run_id=RUN_ID, cursor=self.pause_cursor, idempotency_key="bad-fp-cancel", user_authorized=True),
        ):
            with self.assertRaises(WorkflowError) as raised:
                action()
            self.assertEqual(raised.exception.code, "workflow_snapshot_invalid")
        self.assertEqual(self._counts(), before)

    def test_snapshot_identity_chapter_and_authority_are_checked_without_writes(self):
        cases = (
            ("project_id", "OTHER", "workflow_identity_mismatch"),
            ("run_id", "run_" + "d" * 32, "workflow_identity_mismatch"),
            ("chapter_id", "CH002", "workflow_snapshot_invalid"),
            ("authority", True, "workflow_snapshot_invalid"),
        )
        for field, value, code in cases:
            temp = tempfile.TemporaryDirectory(prefix="qf-q2a-tamper-")
            try:
                root = Path(temp.name) / "store"
                store = QuillframeStore(root)
                store.create_native_project("P", "Project P", "en")
                stamp = now_iso()
                with store.open_project("P") as conn:
                    conn.execute(
                        "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        (RUN_ID, "DRAFT", "CH001", "awaiting_semantic", "sha256:" + "b" * 64, stamp, stamp),
                    )
                    conn.commit()
                service = NovelWorkflowService(store)
                service.start(project_id="P", run_id=RUN_ID, chapter_id="CH001", author_profile="guided")
                with store.open_project("P") as conn:
                    row = conn.execute(
                        "SELECT checkpoint_id,state_json FROM checkpoints WHERE run_id=? ORDER BY rowid DESC LIMIT 1",
                        (RUN_ID,),
                    ).fetchone()
                    snapshot = json.loads(row["state_json"])
                    snapshot[field] = value
                    unsigned = {key: item for key, item in snapshot.items() if key != "snapshot_fingerprint"}
                    snapshot["snapshot_fingerprint"] = "sha256:" + hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
                    conn.execute(
                        "UPDATE checkpoints SET state_json=?,artifact_fingerprint=? WHERE checkpoint_id=?",
                        (canonical_json(snapshot), snapshot["snapshot_fingerprint"], row["checkpoint_id"]),
                    )
                    conn.commit()
                with self.assertRaises(WorkflowError) as raised:
                    service.load("P", RUN_ID)
                self.assertEqual(raised.exception.code, code)
            finally:
                temp.cleanup()

    def test_invalid_cursor_and_ch002_request_are_rejected_without_new_rows(self):
        before = self._counts()
        with self.assertRaises(WorkflowError) as invalid:
            self.service.resume(project_id="P", run_id=RUN_ID, cursor=-2, idempotency_key="invalid")
        self.assertEqual(invalid.exception.code, "invalid_cursor")
        with self.assertRaises(WorkflowError) as invalid_cancel:
            self.service.cancel(project_id="P", run_id=RUN_ID, cursor=-2, idempotency_key="invalid-cancel", user_authorized=True)
        self.assertEqual(invalid_cancel.exception.code, "invalid_cursor")
        self.assertEqual(self._counts(), before)


if __name__ == "__main__":
    unittest.main()
