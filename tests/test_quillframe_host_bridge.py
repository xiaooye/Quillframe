from __future__ import annotations
import os,tempfile,unittest
from studio.host_bridge import REQUEST_SCHEMA,invoke

class BridgeTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); os.environ["QUILLFRAME_DATA_DIR"]=self.tmp.name
    def tearDown(self): os.environ.pop("QUILLFRAME_DATA_DIR",None); self.tmp.cleanup()
    def req(self,op,args=None,surface="local_app"):return {"schema":REQUEST_SCHEMA,"request_id":"R1","operation":op,"surface":surface,"args":args or {},"authority":False}
    def test_no_generic_dispatch(self): self.assertEqual(invoke(self.req("command.invoke"))["status"],"invalid")
    def test_project_revision_and_exact_audit(self):
        self.assertEqual(invoke(self.req("project.create",{"project_id":"P1","title":"书"}))["status"],"ok")
        self.assertEqual(invoke(self.req("document.create",{"project_id":"P1","document_id":"D1","title":"第一章"}))["status"],"ok")
        saved=invoke(self.req("document.revision.save",{"project_id":"P1","document_id":"D1","content":"正文","source":"autosave"})); self.assertEqual(saved["status"],"ok")
        audit=invoke(self.req("author.run.start",{"project_id":"P1","task_mode":"AUDIT","payload":{"rewrite":True}})); self.assertEqual(audit["status"],"failed"); self.assertEqual(audit["error"]["code"],"audit_is_non_mutating")
    def test_feedback_does_not_promote(self):
        invoke(self.req("project.create",{"project_id":"P2","title":"书"}))
        out=invoke(self.req("feedback.observe",{"project_id":"P2","evidence_kind":"rejection","payload":{"text":"no"}})); self.assertFalse(out["data"]["promotion_eligible"])

if __name__=="__main__":unittest.main()
