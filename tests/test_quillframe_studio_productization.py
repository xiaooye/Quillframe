from __future__ import annotations
import shutil,tempfile,unittest,zipfile,json
from pathlib import Path
from persistence.portable_project import PortableProjectService
from persistence.quillframe_sqlite import ConflictError,QuillframeStore

class StudioProductizationTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.store=QuillframeStore(self.root); self.store.create_project("novel","Novel","zh-CN"); self.store.create_document("novel","doc1","第一章")
 def tearDown(self): self.tmp.cleanup()
 def test_revision_compare_and_conflict(self):
  first=self.store.save_revision("novel","doc1","one",expected_parent_revision_id=None,source="test")
  second=self.store.save_revision("novel","doc1","one\ntwo",expected_parent_revision_id=first["revision_id"],source="test")
  self.assertTrue(self.store.compare_revisions("novel",first["revision_id"],second["revision_id"])["diff"])
  with self.assertRaises(ConflictError): self.store.save_revision("novel","doc1","stale",expected_parent_revision_id=first["revision_id"],source="test")
 def test_qfproject_round_trip_excludes_credentials(self):
  saved=self.store.save_revision("novel","doc1","portable text",expected_parent_revision_id=None,source="test")
  service=PortableProjectService(self.store); exported=service.export_project("novel"); path=service.resolve_export_artifact(exported["artifact_ref"])
  raw=path.read_bytes(); self.assertNotIn(b"super-secret-token",raw); self.assertTrue(service.verify(path)["valid"])
  upload=service.stage_import_payload(path.name,raw); staged=service.resolve_import_artifact(upload)
  shutil.rmtree(self.store.location("novel").directory)
  with self.store.initialize_global() and self.store.open_project if False else open(__file__): pass
  import sqlite3
  with sqlite3.connect(self.store.global_db) as c: c.execute("DELETE FROM project_registry WHERE project_id='novel'"); c.commit()
  result=service.import_project(staged); self.assertTrue(result["imported"])
  with self.store.open_project("novel") as c:
   row=c.execute("SELECT content,content_fingerprint FROM document_revisions WHERE document_id='doc1'").fetchone(); self.assertEqual(row["content"],"portable text"); self.assertEqual(row["content_fingerprint"],saved["content_fingerprint"])
 def test_qfproject_rejects_traversal(self):
  bad=self.root/"bad.qfproject"
  with zipfile.ZipFile(bad,"w") as z: z.writestr("../escape","x"); z.writestr("manifest.json",json.dumps({"schema":"quillframe_portable_project_v1","format_version":1})); z.writestr("project.sqlite",b"x")
  result=PortableProjectService(self.store).verify(bad); self.assertFalse(result["valid"]); self.assertTrue(any("unsafe" in x for x in result["errors"]))

if __name__=="__main__": unittest.main()
