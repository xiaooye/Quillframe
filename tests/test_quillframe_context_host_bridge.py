from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.context_runtime import build_candidate_pool, derive_semantic_profile, fingerprint, freeze_context, pack_budget, validate_context_decision
from persistence.context_repository import ContextRepository
from persistence.quillframe_sqlite import QuillframeStore
from studio import host_bridge


class ContextHostBridgeTests(unittest.TestCase):
    def test_read_only_context_projection_is_host_neutral(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            store.create_project("PBRIDGE", "Bridge")
            with store.open_project("PBRIDGE") as conn:
                conn.execute("INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES(?,?,?,?,?)", ("SES-B", "running", 1, "now", "now"))
                conn.execute("INSERT INTO runs(run_id,session_id,task_mode,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", ("RUN-B", "SES-B", "SYSTEM-IMPROVE", "running", fingerprint("r"), "now", "now"))
                conn.commit()
            source_fp = fingerprint("character")
            profile = derive_semantic_profile(
                {"object_id":"CHAR-B","object_type":"character","source_fingerprint":source_fp,"text":"character"},
                {"description":"Character B","trigger_when":"when active","estimated_tokens":4,"semantic_tags":["character"],"stage_affinities":["draft"]},
                generator_provenance={"kind":"test","fingerprint":fingerprint("job")}, generated_at="now")
            item = {"object_id":"CHAR-B","object_type":"character","authority":"accepted","lifecycle":"accepted","domain":"character","source_fingerprint":source_fp,"stages":["draft"],"profile":profile}
            pool = build_candidate_pool(run_id="RUN-B", stage_id="draft", items=[item])
            dec = validate_context_decision(pool,{"selections":[{"profile_id":profile["profile_id"],"stage_id":"draft","priority":1,"reason_code":"active","reason":"active character"}]},selector={"kind":"agent","id":"test"})
            green = pack_budget(dec,hard_budget=10)
            freeze = freeze_context(run_id="RUN-B",task_mode="SYSTEM-IMPROVE",pools=[pool],greenlights=[green])
            repo = ContextRepository(store); repo.save_stage_selection("PBRIDGE",pool,green); repo.save_freeze("PBRIDGE",freeze)
            req={"schema":host_bridge.REQUEST_SCHEMA,"request_id":"ctx","operation":"inspector.context.runtime","surface":"local_app","args":{"project_id":"PBRIDGE","run_id":"RUN-B"},"authority":False}
            with patch.object(host_bridge,"store",return_value=store):
                out=host_bridge.invoke(req)
            self.assertEqual(out["status"],"ok")
            self.assertEqual(out["data"]["schema"],"quillframe_context_inspector_projection_v4")
            self.assertFalse(out["data"]["authority"])
            self.assertFalse(out["data"]["private_chain_of_thought_exposed"])
            self.assertNotIn("cloudflare", str(out["data"]).lower())


if __name__ == "__main__": unittest.main()
