from __future__ import annotations
import importlib.util
import hashlib
import json
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import studio.host_bridge as host_bridge
from studio.host_bridge import BRIDGE_VERSION,REQUEST_SCHEMA,contract,invoke,validate_request
from persistence.quillframe_sqlite import QuillframeStore

CLIENT_PATH = Path(__file__).resolve().parents[1] / "agent-skills" / "quillframe" / "scripts" / "quillframe_bridge.py"
CLIENT_SPEC = importlib.util.spec_from_file_location("quillframe_agent_bridge_client", CLIENT_PATH)
CLIENT = importlib.util.module_from_spec(CLIENT_SPEC)
assert CLIENT_SPEC.loader is not None
CLIENT_SPEC.loader.exec_module(CLIENT)

class BridgeTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); os.environ["QUILLFRAME_DATA_DIR"]=self.tmp.name
    def tearDown(self): os.environ.pop("QUILLFRAME_DATA_DIR",None); self.tmp.cleanup()
    def req(self,op,args=None,surface="local_app"):return {"schema":REQUEST_SCHEMA,"bridge_version":BRIDGE_VERSION,"request_id":"R1","operation":op,"surface":surface,"args":args or {},"authority":False}
    def test_no_generic_dispatch(self): self.assertEqual(invoke(self.req("command.invoke"))["status"],"invalid")

    def test_public_failure_envelope_never_echoes_exception_or_detail(self):
        sentinel = "HOST_BRIDGE_SECRET /var/private/sentinel"

        def unexpected(_args, _surface):
            raise OSError(sentinel)

        def provider_failure(_args, _surface):
            raise host_bridge.BridgeError("provider_failed", sentinel, {"provider_detail": sentinel})

        for handler, expected_code in (
            (unexpected, "bridge_internal_error"),
            (provider_failure, "provider_failed"),
        ):
            with self.subTest(expected_code=expected_code), patch.dict(
                host_bridge.DISPATCH,
                {"project.inspect": handler},
            ):
                response = host_bridge.invoke(
                    self.req("project.inspect", {"project_id": "P1"}, "agent_package")
                )
                self.assertEqual(response["status"], "failed")
                self.assertEqual(
                    response["error"],
                    {"code": expected_code, "mutation_performed": False},
                )
                self.assertNotIn(sentinel, json.dumps(response, ensure_ascii=False))

    def test_agent_package_accepts_queries_and_rejects_every_non_query_kind(self):
        contracts = contract()["operations"]
        self.assertEqual(validate_request(self.req("bridge.describe", surface="agent_package")), [])
        self.assertEqual(
            validate_request(self.req("candidate.visible.get", {"project_id": "P1", "candidate_id": "C1"}, "agent_package")),
            [],
        )
        for operation, metadata in contracts.items():
            if metadata["kind"] == "query":
                continue
            args = {key: "value" for key in metadata.get("required_args", [])}
            errors = validate_request(self.req(operation, args, "agent_package"))
            with self.subTest(operation=operation):
                self.assertIn("agent_package only permits query operations", errors)

    def test_database_doctor_rejects_hidden_repair_argument(self):
        response = invoke(self.req("database.doctor", {"fix": True}, "agent_package"))
        self.assertEqual(response["status"], "invalid")
        self.assertFalse(response["error"]["mutation_performed"])

    def test_agent_query_families_do_not_initialize_runtime_storage(self):
        before = sorted(str(path.relative_to(self.tmp.name)) for path in Path(self.tmp.name).rglob("*"))
        for operation in ("project.list", "model.service.list"):
            response = invoke(self.req(operation, surface="agent_package"))
            self.assertEqual(response["status"], "ok", operation)
        after = sorted(str(path.relative_to(self.tmp.name)) for path in Path(self.tmp.name).rglob("*"))
        self.assertEqual(after, before)

    def test_every_agent_visible_query_is_storage_side_effect_free(self):
        query_operations = [name for name, metadata in contract()["operations"].items() if metadata["kind"] == "query"]
        for operation in query_operations:
            args = {key: "P1" for key in contract()["operations"][operation].get("required_args", [])}
            before = sorted(str(path.relative_to(self.tmp.name)) for path in Path(self.tmp.name).rglob("*"))
            response = invoke(self.req(operation, args, "agent_package"))
            after = sorted(str(path.relative_to(self.tmp.name)) for path in Path(self.tmp.name).rglob("*"))
            with self.subTest(operation=operation, response=response):
                self.assertEqual(after, before)

    def test_every_agent_visible_query_is_storage_side_effect_free_with_existing_project(self):
        QuillframeStore().create_project("P1", "Test")
        query_operations = [name for name, metadata in contract()["operations"].items() if metadata["kind"] == "query"]

        def inventory():
            return {
                str(path.relative_to(self.tmp.name)): (
                    path.stat().st_mtime_ns,
                    path.stat().st_size,
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in Path(self.tmp.name).rglob("*")
                if path.is_file() and not path.name.endswith("-shm")
            }

        for operation in query_operations:
            args = {key: "P1" for key in contract()["operations"][operation].get("required_args", [])}
            before = inventory()
            response = invoke(self.req(operation, args, "agent_package"))
            after = inventory()
            with self.subTest(operation=operation, response=response):
                self.assertEqual(after, before)

    def test_agent_read_only_query_sees_committed_row_in_active_wal_without_writes(self):
        store = QuillframeStore()
        store.create_project("P1", "Test")
        store.create_document("P1", "D1", "第一章", document_kind="note")
        held = store.open_project("P1")
        try:
            held.execute("BEGIN")
            held.execute("SELECT COUNT(*) FROM documents").fetchone()
            store.save_revision("P1", "D1", "WAL latest", expected_parent_revision_id=None, source="test")
            wal = store.location("P1").database.with_name("project.sqlite-wal")
            self.assertTrue(wal.is_file(), "fixture must leave a committed row in the active WAL")

            def inventory():
                return {
                    str(path.relative_to(self.tmp.name)): (
                        path.stat().st_mtime_ns,
                        path.stat().st_size,
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                    for path in Path(self.tmp.name).rglob("*")
                    if path.is_file() and not path.name.endswith("-shm")
                }

            shm = wal.with_name(wal.name[:-4] + "-shm")
            self.assertTrue(shm.is_file(), "active WAL fixture must have a shared-memory sidecar")
            shm_before = (shm.stat().st_size, shm.stat().st_ino)

            before = inventory()
            response = invoke(self.req("document.open", {"project_id": "P1", "document_id": "D1"}, "agent_package"))
            after = inventory()
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["data"]["latest_revision"]["content"], "WAL latest")
            self.assertEqual(after, before)
            self.assertTrue(shm.is_file(), "read-only query must not remove the shared-memory sidecar")
            self.assertEqual((shm.stat().st_size, shm.stat().st_ino), shm_before)
        finally:
            held.rollback()
            held.close()

    def test_agent_read_only_query_fails_closed_when_active_wal_shm_is_missing(self):
        store = QuillframeStore()
        store.create_project("P1", "Test")
        store.create_document("P1", "D1", "第一章", document_kind="note")
        held = store.open_project("P1")
        try:
            held.execute("BEGIN")
            held.execute("SELECT COUNT(*) FROM documents").fetchone()
            store.save_revision("P1", "D1", "WAL latest", expected_parent_revision_id=None, source="test")
            wal = store.location("P1").database.with_name("project.sqlite-wal")
            shm = wal.with_name(wal.name[:-4] + "-shm")
            self.assertTrue(wal.is_file())
            self.assertTrue(shm.is_file())
            shm.unlink()

            response = invoke(self.req("document.open", {"project_id": "P1", "document_id": "D1"}, "agent_package"))

            self.assertEqual(response["status"], "failed")
            self.assertFalse(shm.exists(), "read-only preflight must not recreate a missing WAL sidecar")
        finally:
            held.rollback()
            held.close()

    def test_agent_project_queries_do_not_create_sidecars_and_inspect_succeeds(self):
        store = QuillframeStore()
        store.create_project("P1", "Test")
        before = {
            str(path.relative_to(self.tmp.name)): (path.stat().st_size, path.stat().st_ino)
            for path in Path(self.tmp.name).rglob("*")
            if path.is_file() and (path.name.endswith("-wal") or path.name.endswith("-shm"))
        }

        listing = invoke(self.req("project.list", surface="agent_package"))
        inspection = invoke(self.req("project.inspect", {"project_id": "P1"}, "agent_package"))

        self.assertEqual(listing["status"], "ok")
        self.assertEqual(inspection["status"], "ok")
        after = {
            str(path.relative_to(self.tmp.name)): (path.stat().st_size, path.stat().st_ino)
            for path in Path(self.tmp.name).rglob("*")
            if path.is_file() and (path.name.endswith("-wal") or path.name.endswith("-shm"))
        }
        self.assertEqual(after, before)

    def test_agent_inspector_query_surface_matches_contract(self):
        store = QuillframeStore()
        store.create_project("P1", "Test")
        for operation in (
            "inspector.sessions.list",
            "inspector.runs.list",
            "inspector.context.list",
            "inspector.receipts.list",
            "inspector.candidates.list",
            "inspector.learning.list",
        ):
            with self.subTest(operation=operation):
                response = invoke(self.req(operation, {"project_id": "P1"}, "agent_package"))
                self.assertEqual(response["status"], "ok")
        rejected = invoke(self.req("inspector.checkpoints.list", {"project_id": "P1"}, "agent_package"))
        self.assertEqual(rejected["status"], "invalid")

    def test_portable_preflight_requires_exact_v11_description(self):
        request = self.req("project.list", surface="agent_package")
        description = {
            "schema": "quillframe_host_bridge_description_v1",
            "contract_version": "1",
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
            "settlement_authority": False,
            "direct_core_store_access": False,
            "operation_contracts": {"project.list": {"kind": "query", "required_args": []}},
        }
        errors = CLIENT.preflight(request, description)
        self.assertIn("description schema must be quillframe_host_bridge_description_v11", errors)
        self.assertIn("description contract_version must be exactly 11", errors)

    def test_portable_preflight_rejects_malformed_operation_metadata(self):
        request = self.req("project.list", surface="agent_package")
        base = {
            "schema": "quillframe_host_bridge_description_v11",
            "contract_version": "11",
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
            "settlement_authority": False,
            "direct_core_store_access": False,
        }
        for metadata in (
            {"kind": "query", "required_args": [1]},
            {"kind": "query", "required_args": [], "allowed_surfaces": "cli"},
            {"kind": "query", "required_args": [], "allowed_surfaces": {"agent_package": True}},
            {"kind": "unknown", "required_args": []},
        ):
            with self.subTest(metadata=metadata):
                errors = CLIENT.preflight(request, {**base, "operation_contracts": {"project.list": metadata}})
                self.assertTrue(errors)
                self.assertTrue(any("metadata" in error or "kind" in error or "required_args" in error or "allowed_surfaces" in error for error in errors))

    def test_bridge_description_is_v11_operation_metadata(self):
        response = invoke(self.req("bridge.describe", surface="agent_package"))
        self.assertEqual(response["status"], "ok")
        description = response["data"]
        self.assertEqual(description["schema"], "quillframe_host_bridge_description_v11")
        self.assertEqual(description["contract_version"], "11")
        self.assertEqual(description["operation_contracts"]["project.create"]["kind"], "command")
        self.assertEqual(description["operation_contracts"]["project.create"]["required_args"], ["project_id", "title"])
        self.assertEqual(description["operation_contracts"]["candidate.visible.get"]["allowed_surfaces"], ["cli", "local_app", "hosted_web", "agent_package"])

    def test_project_revision_and_exact_audit(self):
        self.assertEqual(invoke(self.req("project.create",{"project_id":"P1","title":"书"}))["status"],"ok")
        self.assertEqual(invoke(self.req("document.create",{"project_id":"P1","document_id":"D1","title":"创作笔记","document_kind":"note"}))["status"],"ok")
        saved=invoke(self.req("document.revision.save",{"project_id":"P1","document_id":"D1","content":"正文","source":"autosave"})); self.assertEqual(saved["status"],"ok")
        audit=invoke(self.req("author.run.start",{"project_id":"P1","task_mode":"AUDIT","payload":{"chapter_id":"CH001","author_profile":"guided","rewrite":True}})); self.assertEqual(audit["status"],"failed"); self.assertEqual(audit["error"]["code"],"audit_is_non_mutating")
    def test_feedback_does_not_promote(self):
        invoke(self.req("project.create",{"project_id":"P2","title":"书"}))
        out=invoke(self.req("feedback.observe",{"project_id":"P2","evidence_kind":"rejection","payload":{"text":"no"}})); self.assertFalse(out["data"]["promotion_eligible"])

if __name__=="__main__":unittest.main()
