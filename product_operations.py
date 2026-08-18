#!/usr/bin/env python3
"""Product-facing Core projections for Quillframe Studio 0.9."""
from __future__ import annotations
import base64,json,os,shutil,sqlite3,uuid
from typing import Any
from agent_runtime.runtime import QuillframeAgentRuntime
from model_runtime.secrets import MemorySecretStore
from persistence.portable_project import MAX_PORTABLE_BYTES, PortableProjectService
from persistence.quillframe_sqlite import QuillframeStore

class ProductOperationError(RuntimeError):
    def __init__(self,code:str,message:str,detail:Any=None)->None: super().__init__(message); self.code=code; self.detail=detail

class ProductOperations:
    def __init__(self,store:QuillframeStore|None=None)->None:
        self.store=store or QuillframeStore(); self.portable=PortableProjectService(self.store); self._secrets=MemorySecretStore(); self.agent_runtime=QuillframeAgentRuntime(secret_store=self._secrets,store=self.store)
    def project_list_portable(self)->dict[str,Any]:
        self.store.initialize_global()
        with sqlite3.connect(self.store.global_db,timeout=5.0) as conn:
            conn.row_factory=sqlite3.Row; rows=[dict(r) for r in conn.execute("SELECT project_id,title,language,project_schema_version,registered_at,last_opened_at FROM project_registry ORDER BY last_opened_at DESC,project_id")]
        return {"schema":"quillframe_project_list_v1","items":rows,"authority":False}
    def project_delete(self,project_id:str,*,confirm_project_id:str,user_authorized:bool,backup_first:bool=True)->dict[str,Any]:
        if not user_authorized or confirm_project_id!=project_id: raise ProductOperationError("authorization_required","project.delete requires explicit authorization and exact id confirmation")
        loc=self.store.location(project_id)
        if not loc.directory.exists(): return {"schema":"quillframe_project_delete_result_v1","project_id":project_id,"deleted":False,"already_absent":True,"authority":False}
        backup_ref=self.store.backup_project(project_id).name if backup_first else None; tomb=loc.directory.with_name(loc.directory.name+".delete-"+uuid.uuid4().hex); os.replace(loc.directory,tomb)
        try:
            self.store.initialize_global()
            with sqlite3.connect(self.store.global_db,timeout=5.0) as conn: conn.execute("BEGIN IMMEDIATE"); conn.execute("DELETE FROM project_registry WHERE project_id=?",(project_id,)); conn.commit()
        except Exception:
            if tomb.exists() and not loc.directory.exists(): os.replace(tomb,loc.directory)
            raise
        shutil.rmtree(tomb); return {"schema":"quillframe_project_delete_result_v1","project_id":project_id,"deleted":True,"backup_ref":backup_ref,"authority":False}
    def project_export(self,project_id:str)->dict[str,Any]: return self.portable.export_project(project_id)
    def project_import(self,artifact_ref:str,*,replace:bool=False)->dict[str,Any]:
        path=self.portable.resolve_import_artifact(artifact_ref)
        try: return self.portable.import_project(path,replace=replace)
        finally: path.unlink(missing_ok=True)
    def artifact_read(self,artifact_ref:str)->dict[str,Any]:
        path=self.portable.resolve_export_artifact(artifact_ref); payload=path.read_bytes()
        if len(payload)>MAX_PORTABLE_BYTES: raise ProductOperationError("artifact_too_large","portable project exceeds transfer limit")
        return {"schema":"quillframe_artifact_read_result_v1","artifact_ref":artifact_ref,"file_name":path.name,"media_type":"application/vnd.quillframe.project+zip","payload_base64":base64.b64encode(payload).decode("ascii"),"byte_size":len(payload),"authority":False}
    def artifact_upload(self,file_name:str,payload_base64:str)->dict[str,Any]:
        try: payload=base64.b64decode(payload_base64,validate=True)
        except Exception as exc: raise ProductOperationError("invalid_base64","artifact payload is not valid base64") from exc
        ref=self.portable.stage_import_payload(file_name,payload); return {"schema":"quillframe_artifact_upload_result_v1","artifact_ref":ref,"file_name":file_name,"byte_size":len(payload),"authority":False}
    def document_list(self,project_id:str,document_kind:str|None=None)->dict[str,Any]:
        with self.store.open_project(project_id) as conn:
            sql="""SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at,r.revision_id AS latest_revision_id,r.content_fingerprint AS latest_content_fingerprint,r.authority_class AS latest_authority_class,r.created_at AS latest_revision_at FROM documents d LEFT JOIN document_revisions r ON r.revision_id=(SELECT revision_id FROM document_revisions x WHERE x.document_id=d.document_id ORDER BY x.created_at DESC,x.rowid DESC LIMIT 1)"""; params:tuple[Any,...]=()
            if document_kind: sql+=" WHERE d.document_kind=?"; params=(document_kind,)
            items=[dict(r) for r in conn.execute(sql+" ORDER BY d.created_at,d.document_id",params)]
        return {"schema":"quillframe_document_list_v1","project_id":project_id,"items":items,"authority":False}
    def document_get(self,project_id:str,document_id:str)->dict[str,Any]:
        with self.store.open_project(project_id) as conn:
            doc=conn.execute("SELECT * FROM documents WHERE document_id=?",(document_id,)).fetchone()
            if not doc: raise ProductOperationError("document_not_found",document_id)
            rev=self.store.latest_revision(conn,document_id)
        return {"schema":"quillframe_document_projection_v1","project_id":project_id,"document":dict(doc),"latest_revision":dict(rev) if rev else None,"authority":False}
    def revision_list(self,project_id:str,document_id:str,limit:int=100)->dict[str,Any]:
        with self.store.open_project(project_id) as conn: rows=[dict(r) for r in conn.execute("SELECT revision_id,document_id,parent_revision_id,content_fingerprint,created_at,source,authority_class,provenance_json FROM document_revisions WHERE document_id=? ORDER BY created_at DESC,rowid DESC LIMIT ?",(document_id,max(1,min(limit,500))))]
        for row in rows: row["provenance"]=json.loads(row.pop("provenance_json") or "{}")
        return {"schema":"quillframe_document_revision_list_v1","project_id":project_id,"document_id":document_id,"items":rows,"authority":False}
    def story_projection(self,project_id:str)->dict[str,Any]:
        with self.store.open_project(project_id) as c:
            nodes=[dict(r) for r in c.execute("SELECT * FROM story_nodes ORDER BY parent_id,ordinal,node_id")]; chars=[dict(r) for r in c.execute("SELECT * FROM characters ORDER BY name,character_id")]; rel=[dict(r) for r in c.execute("SELECT * FROM relationships ORDER BY relationship_id")]; world=[dict(r) for r in c.execute("SELECT * FROM world_entities ORDER BY entity_type,name,entity_id")]; timeline=[dict(r) for r in c.execute("SELECT * FROM timeline_events ORDER BY story_order,event_id")]; claims=[dict(r) for r in c.execute("SELECT * FROM canon_claims ORDER BY authority_class,subject_ref,predicate,claim_id")]
        return {"schema":"quillframe_story_projection_v1","project_id":project_id,"story_nodes":nodes,"characters":chars,"relationships":rel,"world_entities":world,"timeline_events":timeline,"canon_claims":claims,"authority":False,"mutation_supported":False}
    def plan_projection(self,project_id:str)->dict[str,Any]:
        with self.store.open_project(project_id) as c: plans=[dict(r) for r in c.execute("SELECT * FROM plans ORDER BY updated_at DESC,plan_id")]; cards=[dict(r) for r in c.execute("SELECT * FROM scene_cards ORDER BY plan_id,scene_card_id")]
        for p in plans: p["plan"]=json.loads(p.pop("plan_json") or "{}")
        for x in cards: x["plotlines"]=json.loads(x.pop("plotlines_json") or "[]"); x["dependencies"]=json.loads(x.pop("dependencies_json") or "[]"); x["card"]=json.loads(x.pop("card_json") or "{}")
        return {"schema":"quillframe_plan_projection_v1","project_id":project_id,"plans":plans,"scene_cards":cards,"authority":False,"mutation_supported":False}
    def research_projection(self,project_id:str)->dict[str,Any]:
        with self.store.open_project(project_id) as c: sources=[dict(r) for r in c.execute("SELECT * FROM research_sources ORDER BY created_at DESC,source_id")]; claims=[dict(r) for r in c.execute("SELECT * FROM research_claims ORDER BY created_at DESC,research_claim_id")]; corpus=[dict(r) for r in c.execute("SELECT * FROM corpus_references ORDER BY created_at DESC,corpus_ref_id")]; benchmarks=[dict(r) for r in c.execute("SELECT * FROM benchmark_references ORDER BY benchmark_ref_id")]
        return {"schema":"quillframe_research_corpus_projection_v1","project_id":project_id,"research_sources":sources,"research_claims":claims,"corpus_references":corpus,"benchmark_references":benchmarks,"research_is_canon":False,"corpus_is_canon":False,"authority":False}
    def candidate_list(self,project_id:str,limit:int=100)->dict[str,Any]:
        with self.store.open_project(project_id) as c: rows=[dict(r) for r in c.execute("""SELECT c.*,(SELECT acceptance_id FROM acceptance_evidence a WHERE a.candidate_id=c.candidate_id ORDER BY a.created_at DESC LIMIT 1) AS acceptance_id,(SELECT status FROM settlements s WHERE s.acceptance_id=(SELECT acceptance_id FROM acceptance_evidence a2 WHERE a2.candidate_id=c.candidate_id ORDER BY a2.created_at DESC LIMIT 1) ORDER BY s.created_at DESC LIMIT 1) AS settlement_status FROM candidates c ORDER BY c.created_at DESC LIMIT ?""",(max(1,min(limit,500)),))]
        return {"schema":"quillframe_candidate_list_v1","project_id":project_id,"items":rows,"authority":False}
    def candidate_get(self,project_id:str,candidate_id:str)->dict[str,Any]:
        with self.store.open_project(project_id) as c:
            candidate=c.execute("SELECT * FROM candidates WHERE candidate_id=?",(candidate_id,)).fetchone()
            if not candidate: raise ProductOperationError("candidate_not_found",candidate_id)
            revision=c.execute("SELECT * FROM document_revisions WHERE revision_id=?",(candidate["revision_id"],)).fetchone() if candidate["revision_id"] else None; reviews=[dict(r) for r in c.execute("SELECT * FROM review_evidence WHERE candidate_id=? ORDER BY created_at",(candidate_id,))]; acceptance=c.execute("SELECT * FROM acceptance_evidence WHERE candidate_id=? ORDER BY created_at DESC LIMIT 1",(candidate_id,)).fetchone(); settlements=[dict(r) for r in c.execute("SELECT * FROM settlements WHERE acceptance_id=? ORDER BY created_at",(acceptance["acceptance_id"],))] if acceptance else []
        for r in reviews: r["result"]=json.loads(r.pop("result_json") or "{}")
        return {"schema":"quillframe_candidate_projection_v1","project_id":project_id,"candidate":dict(candidate),"revision":dict(revision) if revision else None,"reviews":reviews,"acceptance":dict(acceptance) if acceptance else None,"settlements":settlements,"authority":False}
    def model_connect(self,endpoint:str,access_token:str)->dict[str,Any]:
        if not access_token.strip(): raise ProductOperationError("invalid_args","access_token is required")
        r=self.agent_runtime.connect(endpoint,access_token); r["credential_persistence"]="session_only"; r["credential_value_persisted"]=False; return r
    def _present(self,service_id:str)->bool:
        if self.agent_runtime.repository is None:return False
        try:
            ref=self.agent_runtime.repository.get_internal(service_id).get("credential_ref"); return bool(ref and self._secrets.get(ref))
        except Exception:return False
    def model_list(self)->dict[str,Any]:
        r=self.agent_runtime.list_model_services()
        for x in r.get("items",[]): x["credential_present"]=self._present(str(x.get("service_id") or "")); x["credential_persistence"]="session_only"
        return r
    def model_get(self,service_id:str)->dict[str,Any]:
        r=self.agent_runtime.get_model_service(service_id); r["credential_present"]=self._present(service_id); r["credential_persistence"]="session_only"; return r
    def inspector_table(self,project_id:str,table:str,limit:int=100)->dict[str,Any]:
        order={"sessions":"updated_at DESC","runs":"updated_at DESC","checkpoints":"created_at DESC","context_manifests":"created_at DESC","receipts":"created_at DESC","candidates":"created_at DESC","learning_evidence":"created_at DESC","review_evidence":"created_at DESC","settlements":"created_at DESC"}
        if table not in order: raise ProductOperationError("unsupported_projection",table)
        with self.store.open_project(project_id) as c: rows=[dict(r) for r in c.execute(f"SELECT * FROM {table} ORDER BY {order[table]} LIMIT ?",(max(1,min(limit,500)),))]
        for row in rows:
            for key in list(row):
                if any(term in key.lower() for term in ("secret","credential","provider_session")): row.pop(key,None)
        return {"schema":"quillframe_inspector_projection_v1","kind":table,"project_id":project_id,"items":rows,"authority":False}
