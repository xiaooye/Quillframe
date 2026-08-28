from __future__ import annotations

import os
import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_bytes, fingerprint_text, now_iso


class PublicationRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.ops = CoreOperations(self.store)
        self.store.create_project("P", "Project P", "zh-CN")
        with self.store.open_project("P") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH001','chapter',1,'Chapter','{}')")
            conn.commit()
        self.store.create_document("P", "DOC", "Chapter", story_node_id="CH001")
        first = self.store.save_revision("P", "DOC", "incumbent", expected_parent_revision_id=None, source="test")
        second = self.store.save_revision(
            "P", "DOC", "candidate", expected_parent_revision_id=first["revision_id"], source="test", authority_class="review"
        )
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute(
                "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                ("RUN", "DRAFT", "DOC", "completed", "sha256:req", stamp, stamp),
            )
            conn.execute(
                "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("C", "DOC", second["revision_id"], "RUN", "DRAFT", "draft", "review_draft", second["content_fingerprint"], "PASS", stamp),
            )
            for mechanism in ("reader_engagement", "character_simulation", "continuity", "independent_semantic_gate", "user_visible_gate"):
                payload = {
                    "mechanism": mechanism,
                    "stage_result_fingerprint": f"sha256:{mechanism}",
                    "judgment": {"status": "pass"},
                    "private_reasoning_exposed": False,
                }
                conn.execute(
                    "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                    (f"R-{mechanism}", "RUN", "production_stage", f"RUN:{mechanism}", canonical_json(payload), stamp),
                )
            review = {
                "model_contract_id": "quality.production_review",
                "production_readiness": {"ready_for_user_visible_review": True},
                "private_reasoning_exposed": False,
            }
            conn.execute(
                "INSERT INTO review_evidence(review_id,candidate_id,evidence_kind,result_json,candidate_fingerprint,reviewer_fingerprint,independent,stale,created_at) VALUES(?,?,?,?,?,?,1,0,?)",
                ("REV", "C", "quality.production_review", canonical_json(review), second["content_fingerprint"], "sha256:peer", stamp),
            )
            release = {
                "schema": "quillframe_production_release_v1",
                "candidate_fingerprint": second["content_fingerprint"],
                "production_readiness_fingerprint": "sha256:" + "a" * 64,
                "base_production_readiness": True,
                "pre_independent_qualification_required": True,
                "pre_independent_qualification_fingerprint": "sha256:" + "b" * 64,
                "independent_pass_can_override_qualification_failure": False,
                "required_structural_receipts": ["context_assembly", "user_visible_gate"],
                "structural_receipts": [],
                "missing_structural_receipts": [],
                "blocking_structural_receipts": [],
                "pending_structural_receipts": [],
                "structural_ready": True,
                "ready_for_user_visible_review": True,
                "semantic_pass_can_override_missing_structural_receipt": False,
                "authority": False,
                "permissions": {"canon_write": False, "framework_write": False},
                "model_execution": False,
            }
            release["release_fingerprint"] = fingerprint_text(canonical_json(release))
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("R-RELEASE", "RUN", "production_release", "RUN:production_release", canonical_json(release), stamp),
            )
            conn.commit()
        self.acceptance = self.ops.accept_candidate(
            "P",
            candidate_id="C",
            candidate_fingerprint=second["content_fingerprint"],
            authorized_by="user",
            authorization={"intent": "accept"},
            idempotency_key="accept-1",
        )
        self.acceptance_id = self.acceptance["acceptance_id"]
        self.content = "candidate"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_fresh_schema_has_publication_attempt_ledger_and_identity_indexes(self):
        with self.store.open_project("P") as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(publication_build_attempts)")}
            build_columns = {row[1] for row in conn.execute("PRAGMA table_info(publication_builds)")}
            indexes = {row[1] for row in conn.execute("PRAGMA index_list(publication_builds)")}
        self.assertTrue({
            "build_id", "identity_fingerprint", "project_id", "source_acceptance_id", "format",
            "compiler_contract", "source_fingerprint", "state", "stage_ref", "final_ref",
            "artifact_fingerprint", "byte_size", "created_at", "updated_at",
        } <= columns)
        self.assertIn("compiler_contract", build_columns)
        self.assertTrue(any("identity" in name for name in indexes))

    def test_file_validator_rejects_same_inode_overwrite_and_append(self):
        from publication.recovery import PublicationRecoveryError, _safe_file_bytes

        target = self.store.location("P").exports / "validator.bin"
        original = b"abc"
        expected = fingerprint_bytes(original)
        for mode in ("overwrite", "append"):
            target.write_bytes(original)
            directory_fd = os.open(self.store.location("P").exports, os.O_RDONLY | os.O_DIRECTORY)
            try:
                entry = os.lstat(target)

                def mutate(_point, mode=mode):
                    if mode == "overwrite":
                        with target.open("r+b") as handle:
                            handle.write(b"xyz")
                    else:
                        with target.open("ab") as handle:
                            handle.write(b"!")

                with self.assertRaises(PublicationRecoveryError):
                    _safe_file_bytes(
                        directory_fd,
                        target.name,
                        expected_fingerprint=expected,
                        expected_size=len(original),
                        expected_inode=(entry.st_dev, entry.st_ino),
                        stage=False,
                        mutation_hook=mutate,
                    )
            finally:
                os.close(directory_fd)

    def test_same_inode_mutation_is_rejected_during_stage_validation(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        def mutate(phase, _build_id):
            if phase == "file_stage_before_second_read":
                with self.store.open_project("P") as conn:
                    ref = conn.execute("SELECT stage_ref FROM publication_build_attempts").fetchone()["stage_ref"]
                target = self.store.location("P").directory / ref
                with target.open("r+b") as handle:
                    handle.seek(0)
                    handle.write(b"mutated!!")

        with self.assertRaises(PublicationRecoveryError):
            PublicationRecovery(self.store, fault_injector=mutate).build("P", self.acceptance_id, "md")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)

    def test_same_inode_mutation_is_rejected_during_final_validation(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        def mutate(phase, _build_id):
            if phase == "file_final_before_second_read":
                with self.store.open_project("P") as conn:
                    ref = conn.execute("SELECT final_ref FROM publication_build_attempts").fetchone()["final_ref"]
                with (self.store.location("P").directory / ref).open("r+b") as handle:
                    handle.seek(0)
                    handle.write(b"mutated!!")

        with self.assertRaises(PublicationRecoveryError):
            PublicationRecovery(self.store, fault_injector=mutate).build("P", self.acceptance_id, "md")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)

    def test_same_inode_mutation_is_rejected_during_recovery_validation(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        recovery = PublicationRecovery(
            self.store,
            fault_injector=lambda phase, _build_id: (_ for _ in ()).throw(RuntimeError(phase)) if phase == "before_finalize_insert" else None,
        )
        with self.assertRaises(PublicationRecoveryError):
            recovery.build("P", self.acceptance_id, "md")

        def mutate(phase, _build_id):
            if phase == "file_final_before_second_read":
                with self.store.open_project("P") as conn:
                    ref = conn.execute("SELECT final_ref FROM publication_build_attempts").fetchone()["final_ref"]
                with (self.store.location("P").directory / ref).open("r+b") as handle:
                    handle.seek(0)
                    handle.write(b"mutated!!")

        with self.assertRaises(PublicationRecoveryError):
            PublicationRecovery(self.store, fault_injector=mutate).recover("P")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)

    def test_same_inode_mutation_is_rejected_during_committed_replay(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        built = PublicationRecovery(self.store).build("P", self.acceptance_id, "md")

        def mutate(phase, _build_id):
            if phase == "file_final_before_second_read":
                with (self.store.location("P").directory / built["output_ref"]).open("r+b") as handle:
                    handle.seek(0)
                    handle.write(b"mutated!!")

        with self.assertRaises(PublicationRecoveryError):
            PublicationRecovery(self.store, fault_injector=mutate).build("P", self.acceptance_id, "md")

    def test_committed_replay_rejects_compiler_contract_drift(self):
        built = self.ops.publication_build("P", self.acceptance_id, "md")
        with self.store.open_project("P") as conn:
            conn.execute("UPDATE publication_builds SET compiler_contract='future.compiler' WHERE build_id=?", (built["build_id"],))
            conn.commit()
        with self.assertRaises(OperationError) as raised:
            self.ops.publication_recover("P", build_id=built["build_id"])
        self.assertIn(raised.exception.code, {"publication_attempt_invalid", "publication_identity_conflict"})

    def test_recovery_boundaries_accept_32_reject_33_and_validate_limits_before_open(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        def insert_attempts(count):
            with self.store.open_project("P") as conn:
                for index in range(count):
                    token = f"{index:064x}"
                    build_id = "pub_" + token
                    source_fp = "sha256:" + token
                    identity_fp = "sha256:" + token
                    conn.execute(
                        """INSERT INTO publication_build_attempts(
                        build_id,identity_fingerprint,project_id,source_acceptance_id,format,compiler_contract,
                        source_fingerprint,artifact_fingerprint,byte_size,stage_ref,final_ref,owner_token,state,
                        error_code,created_at,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'published',NULL,?,?)""",
                        (
                            build_id,
                            identity_fp,
                            "P",
                            self.acceptance_id,
                            "md",
                            "quillframe_core_publication_text_v1",
                            source_fp,
                            "sha256:" + "f" * 64,
                            0,
                            f"exports/.{build_id}.stage",
                            f"exports/{build_id}.md",
                            "qfpub:" + identity_fp,
                            now_iso(),
                            now_iso(),
                        ),
                    )
                conn.commit()

        recovery = PublicationRecovery(self.store)
        insert_attempts(32)
        with patch.object(recovery, "_recover_one", return_value={"build_id": "synthetic"}) as recover_one:
            result = recovery.recover("P", limit=32)
        self.assertEqual(len(result["items"]), 32)
        self.assertEqual(recover_one.call_count, 32)

        with self.store.open_project("P") as conn:
            conn.execute("DELETE FROM publication_build_attempts")
            conn.commit()
        insert_attempts(33)
        with patch.object(recovery, "_recover_one", return_value={"build_id": "synthetic"}) as recover_one:
            with self.assertRaises(PublicationRecoveryError) as raised:
                recovery.recover("P", limit=32)
        self.assertEqual(raised.exception.code, "publication_recovery_bounded")
        self.assertEqual(recover_one.call_count, 0)

        for invalid in (True, 0, 33, "32"):
            with self.subTest(limit=invalid):
                with patch.object(self.store, "open_project", side_effect=AssertionError("opened before validating limit")):
                    with self.assertRaises(PublicationRecoveryError) as raised:
                        recovery.recover("P", limit=invalid)
                self.assertEqual(raised.exception.code, "publication_recovery_bounded")

    def test_file_descriptors_close_on_publication_success(self):
        import publication.recovery as recovery_module

        closed = []
        original_close = recovery_module.os.close

        def close(fd):
            closed.append(fd)
            original_close(fd)

        with patch.object(recovery_module.os, "close", side_effect=close):
            result = self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(result["format"], "md")
        self.assertTrue(closed)

    def test_validator_failure_closes_its_read_descriptor(self):
        import publication.recovery as recovery_module
        from publication.recovery import PublicationRecoveryError, _safe_file_bytes

        target = self.store.location("P").exports / "validator-failure.bin"
        target.write_bytes(b"abc")
        directory_fd = os.open(self.store.location("P").exports, os.O_RDONLY | os.O_DIRECTORY)
        entry = os.lstat(target)
        closed = []
        original_close = recovery_module.os.close

        def close(fd):
            closed.append(fd)
            original_close(fd)

        try:
            with patch.object(recovery_module.os, "close", side_effect=close):
                with self.assertRaises(PublicationRecoveryError):
                    _safe_file_bytes(
                        directory_fd,
                        target.name,
                        expected_fingerprint="sha256:" + "0" * 64,
                        expected_size=3,
                        expected_inode=(entry.st_dev, entry.st_ino),
                        stage=False,
                    )
        finally:
            os.close(directory_fd)
        self.assertTrue(closed)

    def test_build_is_deterministic_and_exact_replay(self):
        first = self.ops.publication_build("P", self.acceptance_id, "md")
        second = self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(first, second)
        self.assertEqual(first["output_ref"], f"exports/{first['build_id']}.md")
        output = self.store.location("P").directory / first["output_ref"]
        self.assertEqual(output.read_bytes(), self.content.encode("utf-8"))
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_build_attempts").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT state FROM publication_build_attempts").fetchone()[0], "committed")

    def test_same_identity_concurrent_builds_replay_one_committed_build(self):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def run():
            try:
                barrier.wait(timeout=5)
                results.append(self.ops.publication_build("P", self.acceptance_id, "txt"))
            except Exception as exc:  # pragma: no cover - assertion below reports details
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 1)

    def test_fault_after_stage_commit_leaves_bounded_recoverable_attempt(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        recovery = PublicationRecovery(self.store, fault_injector=lambda phase, _build_id: (_ for _ in ()).throw(RuntimeError(phase)) if phase == "after_stage_commit" else None)
        with self.assertRaises(PublicationRecoveryError) as raised:
            recovery.build("P", self.acceptance_id, "md")
        self.assertEqual(raised.exception.code, "publication_fault")
        with self.store.open_project("P") as conn:
            attempt = conn.execute("SELECT state,stage_ref,final_ref FROM publication_build_attempts").fetchone()
        self.assertEqual(attempt["state"], "staged")
        self.assertFalse((self.store.location("P").directory / attempt["stage_ref"]).exists())
        replay = self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(replay["format"], "md")

    def test_fault_after_publish_is_recovered_from_final_owned_inode(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        recovery = PublicationRecovery(
            self.store,
            fault_injector=lambda phase, _build_id: (_ for _ in ()).throw(RuntimeError(phase)) if phase == "after_publish" else None,
        )
        with self.assertRaises(PublicationRecoveryError) as raised:
            recovery.build("P", self.acceptance_id, "md")
        self.assertEqual(raised.exception.code, "publication_fault")
        with self.store.open_project("P") as conn:
            row = conn.execute("SELECT state,final_ref FROM publication_build_attempts").fetchone()
        self.assertEqual(row["state"], "staged")
        self.assertTrue((self.store.location("P").directory / row["final_ref"]).is_file())
        result = self.ops.publication_recover("P")
        self.assertEqual(result["items"][0]["build_id"], row["final_ref"].split("/")[-1][:-3])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT state FROM publication_build_attempts").fetchone()[0], "committed")

    def test_finalize_failure_rolls_back_projection_and_retry_reuses_published_artifact(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        for phase in ("before_finalize_insert", "before_finalize_commit"):
            with self.subTest(phase=phase):
                recovery = PublicationRecovery(
                    self.store,
                    fault_injector=lambda current, _build_id, phase=phase: (_ for _ in ()).throw(RuntimeError(current)) if current == phase else None,
                )
                with self.assertRaises(PublicationRecoveryError) as raised:
                    recovery.build("P", self.acceptance_id, "md")
                self.assertEqual(raised.exception.code, "publication_fault")
                with self.store.open_project("P") as conn:
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)
                result = self.ops.publication_build("P", self.acceptance_id, "md")
                self.assertEqual(result["format"], "md")
                with self.store.open_project("P") as conn:
                    conn.execute("DELETE FROM publication_builds")
                    conn.execute("UPDATE publication_build_attempts SET state='staged',final_dev=NULL,final_ino=NULL")
                    conn.commit()

    def test_recovery_rejects_source_change_and_symlink_without_external_write(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        recovery = PublicationRecovery(
            self.store,
            fault_injector=lambda phase, _build_id: (_ for _ in ()).throw(RuntimeError(phase)) if phase == "after_temp_fsync" else None,
        )
        with self.assertRaises(PublicationRecoveryError):
            recovery.build("P", self.acceptance_id, "md")
        with self.store.open_project("P") as conn:
            row = conn.execute("SELECT stage_ref FROM publication_build_attempts").fetchone()
            revision = conn.execute("SELECT revision_id FROM document_revisions WHERE content='candidate'").fetchone()
            conn.execute("UPDATE document_revisions SET content='changed',content_fingerprint=? WHERE revision_id=?", (fingerprint_text("changed"), revision["revision_id"]))
            conn.execute("UPDATE candidates SET content_fingerprint=? WHERE candidate_id='C'", (fingerprint_text("changed"),))
            conn.execute("UPDATE acceptance_evidence SET candidate_fingerprint=? WHERE acceptance_id=?", (fingerprint_text("changed"), self.acceptance_id))
            conn.commit()
        stage = self.store.location("P").directory / row["stage_ref"]
        outside = Path(self.temp.name) / "outside-sentinel"
        outside.write_bytes(b"sentinel")
        if stage.exists() or stage.is_symlink():
            stage.unlink()
            stage.symlink_to(outside)
        with self.assertRaises(OperationError) as raised:
            self.ops.publication_recover("P")
        self.assertIn(raised.exception.code, {"publication_source_changed", "publication_stage_invalid"})
        self.assertEqual(outside.read_bytes(), b"sentinel")

    def test_final_competitor_is_not_clobbered(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        recovery = PublicationRecovery(self.store, fault_injector=lambda phase, _build_id: (_ for _ in ()).throw(RuntimeError(phase)) if phase == "after_temp_fsync" else None)
        with self.assertRaises(PublicationRecoveryError):
            recovery.build("P", self.acceptance_id, "md")
        with self.store.open_project("P") as conn:
            row = conn.execute("SELECT build_id,final_ref FROM publication_build_attempts").fetchone()
        competitor = self.store.location("P").directory / row["final_ref"]
        competitor.write_bytes(b"competitor")
        with self.assertRaises(OperationError) as raised:
            self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(raised.exception.code, "publication_target_exists")
        self.assertEqual(competitor.read_bytes(), b"competitor")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)

    def test_publish_race_revalidates_final_inode_before_recording_ownership(self):
        import publication.recovery as recovery_module

        original = recovery_module._rename_noreplace

        def race(source_fd, source_name, target_fd, target_name):
            original(source_fd, source_name, target_fd, target_name)
            target = self.store.location("P").exports / target_name
            target.unlink()
            target.write_bytes(b"competitor")

        with patch.object(recovery_module, "_rename_noreplace", side_effect=race):
            with self.assertRaises(OperationError) as raised:
                self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(raised.exception.code, "publication_artifact_invalid")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)
        with self.store.open_project("P") as conn:
            row = conn.execute("SELECT final_ref FROM publication_build_attempts").fetchone()
        self.assertEqual((self.store.location("P").directory / row["final_ref"]).read_bytes(), b"competitor")

    def test_tampered_committed_artifact_fails_closed(self):
        built = self.ops.publication_build("P", self.acceptance_id, "md")
        target = self.store.location("P").directory / built["output_ref"]
        target.write_bytes(b"tampered")
        with self.assertRaises(OperationError) as raised:
            self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(raised.exception.code, "publication_artifact_invalid")

    def test_failed_attempt_requires_explicit_retry(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError

        recovery = PublicationRecovery(
            self.store,
            fault_injector=lambda phase, _build_id: (_ for _ in ()).throw(RuntimeError(phase)) if phase == "after_temp_fsync" else None,
        )
        with self.assertRaises(PublicationRecoveryError):
            recovery.build("P", self.acceptance_id, "md")
        with self.store.open_project("P") as conn:
            row = conn.execute("SELECT final_ref FROM publication_build_attempts").fetchone()
        competitor = self.store.location("P").directory / row["final_ref"]
        competitor.write_bytes(b"competitor")
        with self.assertRaises(OperationError):
            self.ops.publication_recover("P")
        with self.assertRaises(OperationError) as raised:
            self.ops.publication_build("P", self.acceptance_id, "md")
        self.assertEqual(raised.exception.code, "publication_attempt_failed")
        competitor.unlink()
        retry = PublicationRecovery(self.store).retry("P", row["final_ref"].split("/")[-1][:-3])
        self.assertEqual(retry["format"], "md")

    def test_recovery_unknown_build_id_is_not_empty_success(self):
        with self.assertRaises(OperationError) as raised:
            self.ops.publication_recover("P", build_id="pub_" + "0" * 64)
        self.assertEqual(raised.exception.code, "publication_missing")

    def _settle_publication_fixture(self, acceptance_id: str) -> None:
        """Seed deterministic publication prerequisites, not semantic evidence."""
        with self.store.open_project("P") as conn:
            row = conn.execute(
                """SELECT a.candidate_id,c.document_id,c.revision_id,c.content_fingerprint,d.story_node_id
                FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
                JOIN documents d ON d.document_id=c.document_id WHERE a.acceptance_id=?""", (acceptance_id,),
            ).fetchone()
            state = {key: row[key] for key in ("candidate_id", "document_id", "revision_id", "content_fingerprint")}
            state["acceptance_id"] = acceptance_id
            head_fp = fingerprint_text(canonical_json(state))
            target = f"chapter:{row['story_node_id']}"
            conn.execute(
                "INSERT INTO settlements(settlement_id,acceptance_id,target_ref,before_fingerprint,after_fingerprint,state_delta_json,status,receipt_json,created_at,completed_at) VALUES(?,?,?,?,?,?,'settled',?,?,?)",
                (f"SET-{acceptance_id}", acceptance_id, target, "sha256:" + "0" * 64, head_fp, "{}", '{"test_fixture":true}', now_iso(), now_iso()),
            )
            conn.execute(
                """INSERT INTO canon_state(state_key,value_json,authority_class,evidence_ref,content_fingerprint,updated_at)
                VALUES(?,?,'accepted',?,?,?) ON CONFLICT(state_key) DO UPDATE SET value_json=excluded.value_json,
                evidence_ref=excluded.evidence_ref,content_fingerprint=excluded.content_fingerprint,updated_at=excluded.updated_at""",
                (target, canonical_json(state), acceptance_id, head_fp, now_iso()),
            )
            conn.commit()

    def _second_publication_fixture(self) -> str:
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH002','chapter',2,'Second','{}')")
            conn.commit()
        self.store.create_document("P", "DOC-CH002", "Second", story_node_id="CH002")
        revision = self.store.save_revision("P", "DOC-CH002", "第二章。", expected_parent_revision_id=None, source="test")
        with self.store.open_project("P") as conn:
            conn.execute("UPDATE document_revisions SET authority_class='accepted' WHERE revision_id=?", (revision["revision_id"],))
            conn.execute("INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES('RUN2','DRAFT','chapter:CH002','completed',?,?,?)", (fingerprint_text("request2"), stamp, stamp))
            conn.execute(
                "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES('C2','DOC-CH002',?,'RUN2','DRAFT','draft','accepted',?,'PASS',?)",
                (revision["revision_id"], revision["content_fingerprint"], stamp),
            )
            conn.execute(
                "INSERT INTO acceptance_evidence(acceptance_id,candidate_id,candidate_fingerprint,authorized_by,authorization_json,created_at) VALUES('A2','C2',?,'test-author',?,?)",
                (revision["content_fingerprint"], '{"test_fixture":true}', stamp),
            )
            conn.commit()
        self._settle_publication_fixture(self.acceptance_id)
        self._settle_publication_fixture("A2")
        return "A2"

    def test_artifact_returns_exact_bytes_and_rejects_tamper_and_paths(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError
        runtime = PublicationRecovery(self.store)
        built = runtime.build("P", self.acceptance_id)
        result = runtime.artifact("P", built["build_id"])
        self.assertEqual(base64.b64decode(result["content_base64"], validate=True), self.content.encode("utf-8"))
        self.assertEqual(result["artifact_fingerprint"], built["artifact_fingerprint"])
        self.assertEqual(result["source_acceptance_ids"], [self.acceptance_id])
        for bad in ("../project.sqlite", built["build_id"] + "/x"):
            with self.assertRaises(PublicationRecoveryError):
                runtime.artifact("P", bad)
        target = self.store.location("P").directory / built["output_ref"]
        target.write_text("x" * len(self.content), encoding="utf-8")
        with self.assertRaises(PublicationRecoveryError) as rejected:
            runtime.artifact("P", built["build_id"])
        self.assertEqual(rejected.exception.code, "publication_artifact_invalid")

    def test_collection_has_ordered_bytes_real_members_and_idempotency(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError
        second = self._second_publication_fixture()
        runtime = PublicationRecovery(self.store)
        ids = [self.acceptance_id, second]
        result = runtime.build_collection("P", ids, idempotency_key="book", user_authorized=True)
        replay = runtime.build_collection("P", ids, idempotency_key="book", user_authorized=True)
        self.assertEqual(result, replay)
        artifact = runtime.artifact("P", result["build_id"])
        self.assertEqual(base64.b64decode(artifact["content_base64"], validate=True), "candidate\n\n第二章。".encode("utf-8"))
        self.assertEqual(artifact["source_acceptance_ids"], ids)
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_builds").fetchone()[0], 0)
            self.assertEqual([row[0] for row in conn.execute("SELECT acceptance_id FROM publication_collection_members ORDER BY ordinal")], ids)
        with self.assertRaises(PublicationRecoveryError) as rejected:
            runtime.build_collection("P", ids, "txt", idempotency_key="book", user_authorized=True)
        self.assertEqual(rejected.exception.code, "publication_identity_conflict")

    def test_collection_rejects_repeated_unordered_or_unsettled_sources(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError
        second = self._second_publication_fixture()
        runtime = PublicationRecovery(self.store)
        for ids in ([self.acceptance_id, self.acceptance_id], [second, self.acceptance_id]):
            with self.assertRaises(PublicationRecoveryError):
                runtime.build_collection("P", ids, idempotency_key="invalid", user_authorized=True)
        with self.assertRaises(PublicationRecoveryError) as unauthorized:
            runtime.build_collection("P", [self.acceptance_id, second], idempotency_key="book", user_authorized=False)
        self.assertEqual(unauthorized.exception.code, "publication_authorization_required")
        with self.store.open_project("P") as conn:
            conn.execute("DELETE FROM canon_state WHERE state_key='chapter:CH002'")
            conn.commit()
        with self.assertRaises(PublicationRecoveryError) as unsettled:
            runtime.build_collection("P", [self.acceptance_id, second], idempotency_key="book", user_authorized=True)
        self.assertEqual(unsettled.exception.code, "publication_source_changed")

    def test_collection_dependency_check_uses_selected_run_not_old_history(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError
        second = self._second_publication_fixture()
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            source_fp = conn.execute("SELECT content_fingerprint FROM canon_state WHERE state_key='chapter:CH001'").fetchone()[0]
            conn.execute("INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES('RUN2-OLD','DRAFT','chapter:CH002','completed',?,?,?)", (fingerprint_text("old"), stamp, stamp))
            conn.execute("INSERT INTO chapter_dependencies(chapter_id,source_chapter_id,source_fingerprint,run_id,status,created_at,updated_at) VALUES('CH002','CH001',?,'RUN2-OLD','stale',?,?)", (source_fp, stamp, stamp))
            conn.execute("INSERT INTO chapter_dependencies(chapter_id,source_chapter_id,source_fingerprint,run_id,status,created_at,updated_at) VALUES('CH002','CH001',?,'RUN2','current',?,?)", (source_fp, stamp, stamp))
            conn.commit()
        runtime = PublicationRecovery(self.store)
        built = runtime.build_collection("P", [self.acceptance_id, second], idempotency_key="book", user_authorized=True)
        with self.store.open_project("P") as conn:
            conn.execute("UPDATE chapter_dependencies SET status='stale' WHERE run_id='RUN2'")
            conn.commit()
        with self.assertRaises(PublicationRecoveryError) as stale:
            runtime.build_collection("P", [self.acceptance_id, second], idempotency_key="stale", user_authorized=True)
        self.assertEqual(stale.exception.code, "publication_source_changed")
        # Existing build bytes remain an immutable historical artifact.
        self.assertEqual(runtime.artifact("P", built["build_id"])["source_acceptance_ids"], [self.acceptance_id, second])

    def test_collection_recovers_after_file_publish_without_duplicate_build(self):
        from publication.recovery import PublicationRecovery, PublicationRecoveryError
        second = self._second_publication_fixture()

        def fail(phase, _build_id):
            if phase == "after_publish":
                raise RuntimeError("simulated interruption")

        with self.assertRaises(PublicationRecoveryError):
            PublicationRecovery(self.store, fault_injector=fail).build_collection("P", [self.acceptance_id, second], idempotency_key="book", user_authorized=True)
        with self.store.open_project("P") as conn:
            build_id = conn.execute("SELECT build_id FROM publication_collection_attempts").fetchone()[0]
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM publication_collection_builds").fetchone()[0], 0)
        runtime = PublicationRecovery(self.store)
        recovered = runtime.recover("P", build_id=build_id)
        self.assertEqual(recovered["items"][0]["build_id"], build_id)
        self.assertEqual(runtime.artifact("P", build_id)["source_acceptance_ids"], [self.acceptance_id, second])


if __name__ == "__main__":
    unittest.main()
