#!/usr/bin/env python3
"""Deterministic kernel for model-owned NovelForge semantic contracts."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
CATALOG=HERE/"model_contract_catalog.json"
FORBIDDEN_BLIND_KEYS={"expected","expected_verdict","expected_codes","blocks_release","gold","gold_label","prior_result"}
ALLOWED_KINDS={"eval_judge","corpus_analyze","benchmark_synthesize","external_review","preference_distill","artifact_audit"}
WRITE_KEYS=("canon_write","framework_behavior_write","durable_user_taste_write")

def load_json(path:Path)->Any:return json.loads(path.read_text(encoding="utf-8"))
def dump_json(v:Any,path:Path|None=None)->None:
    s=json.dumps(v,ensure_ascii=False,indent=2)+"\n"
    if path:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s,encoding="utf-8")
    else:print(s,end="")
def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def find_named_keys(v:Any,names:set[str],path:str="$")->list[str]:
    out=[]
    if isinstance(v,dict):
        for k,x in v.items():
            if k in names:out.append(f"{path}.{k}")
            out+=find_named_keys(x,names,f"{path}.{k}")
    elif isinstance(v,list):
        for i,x in enumerate(v):out+=find_named_keys(x,names,f"{path}[{i}]")
    return out
def find_forbidden_keys(v:Any,path:str="$")->list[str]:return find_named_keys(v,FORBIDDEN_BLIND_KEYS,path)
def _type(v:Any,t:str)->bool:return {"object":isinstance(v,dict),"array":isinstance(v,list),"string":isinstance(v,str),"boolean":isinstance(v,bool),"number":isinstance(v,(int,float)) and not isinstance(v,bool),"integer":isinstance(v,int) and not isinstance(v,bool),"null":v is None}.get(t,True)
def validate_typed_value(v:Any,s:Any,path:str="$")->list[str]:
    if not isinstance(s,dict) or not s:return []
    e=[]
    if "enum" in s and v not in s["enum"]:e.append(f"{path}: value not in enum")
    t=s.get("type")
    if t is not None:
        allowed=t if isinstance(t,list) else [t]
        if not any(isinstance(x,str) and _type(v,x) for x in allowed):return e+[f"{path}: type mismatch; expected {allowed}"]
    if isinstance(v,dict):
        for k in s.get("required",[]):
            if k not in v:e.append(f"{path}: missing required field {k}")
        props=s.get("properties",{})
        if isinstance(props,dict):
            for k,child in props.items():
                if k in v:e+=validate_typed_value(v[k],child,f"{path}.{k}")
            if s.get("additionalProperties") is False:e += [f"{path}: unexpected field {k}" for k in sorted(set(v)-set(props))]
    elif isinstance(v,list):
        if isinstance(s.get("minItems"),int) and len(v)<s["minItems"]:e.append(f"{path}: fewer than minItems")
        if isinstance(s.get("maxItems"),int) and len(v)>s["maxItems"]:e.append(f"{path}: more than maxItems")
        if isinstance(s.get("items"),dict):
            for i,x in enumerate(v):e+=validate_typed_value(x,s["items"],f"{path}[{i}]")
    elif isinstance(v,str):
        if isinstance(s.get("minLength"),int) and len(v)<s["minLength"]:e.append(f"{path}: shorter than minLength")
        if isinstance(s.get("maxLength"),int) and len(v)>s["maxLength"]:e.append(f"{path}: longer than maxLength")
    elif isinstance(v,(int,float)) and not isinstance(v,bool):
        if isinstance(s.get("minimum"),(int,float)) and v<s["minimum"]:e.append(f"{path}: below minimum")
        if isinstance(s.get("maximum"),(int,float)) and v>s["maximum"]:e.append(f"{path}: above maximum")
    return e
def load_contract_registry(path:Path)->dict[str,Any]:
    r=load_json(path)
    if not isinstance(r,dict) or r.get("schema")!="novelforge_model_contract_registry_v1":raise ValueError(f"invalid model contract registry: {path}")
    contracts=r.get("contracts")
    if not isinstance(contracts,dict) or not contracts:raise ValueError("registry requires contracts")
    for cid,c in contracts.items():
        if not isinstance(cid,str) or not cid or not isinstance(c,dict):raise ValueError("invalid contract entry")
        if c.get("kind") not in ALLOWED_KINDS:raise ValueError(f"{cid}: unsupported kind")
        rubric=c.get("rubric")
        if not isinstance(rubric,list) or not rubric or not all(isinstance(x,str) and x.strip() for x in rubric):raise ValueError(f"{cid}: invalid rubric")
        input_contract=c.get("input_contract")
        if input_contract is not None and not isinstance(input_contract,dict):raise ValueError(f"{cid}: invalid input_contract")
        if not isinstance(c.get("output_contract"),dict):raise ValueError(f"{cid}: invalid output_contract")
        forbidden=c.get("forbidden_input_keys",[])
        if not isinstance(forbidden,list) or not all(isinstance(x,str) and x.strip() for x in forbidden):raise ValueError(f"{cid}: invalid forbidden_input_keys")
        perms=c.get("permissions")
        if not isinstance(perms,dict) or any(perms.get(k) is not False for k in WRITE_KEYS):raise ValueError(f"{cid}: write permissions must be false")
    return r
def load_contract_catalog(path:Path=CATALOG)->dict[str,Any]:
    c=load_json(path)
    if not isinstance(c,dict) or c.get("schema")!="novelforge_model_contract_catalog_v1" or c.get("loading_policy")!="progressive_disclosure":raise ValueError("invalid contract catalog")
    packs=c.get("packs");seen=set()
    if not isinstance(packs,list) or not packs:raise ValueError("catalog requires packs")
    for p in packs:
        ids=p.get("contracts") if isinstance(p,dict) else None
        if not isinstance(p,dict) or not isinstance(p.get("id"),str) or not isinstance(p.get("path"),str) or not isinstance(ids,list) or not ids:raise ValueError("invalid pack metadata")
        dup=seen&set(ids)
        if dup:raise ValueError("duplicate contracts: "+", ".join(sorted(dup)))
        seen.update(ids)
    return c
def resolve_contract_registry(cid:str,catalog_path:Path=CATALOG)->tuple[Path,str]:
    c=load_contract_catalog(catalog_path);m=[p for p in c["packs"] if cid in p["contracts"]]
    if len(m)!=1:raise ValueError(f"unknown or ambiguous model contract: {cid}")
    p=m[0];path=(catalog_path.parent/p["path"]).resolve();root=catalog_path.parent.resolve()
    if root!=path.parent and root not in path.parents:raise ValueError("contract pack escapes semantic root")
    if cid not in load_contract_registry(path)["contracts"]:raise ValueError(f"catalog/pack mismatch: {cid}")
    return path,p["id"]
def _character_evidence_rows(payload:dict[str,Any])->list[tuple[str,int]]:
    rows:list[tuple[str,int]]=[]
    situation=payload.get("immediate_situation",{}) if isinstance(payload.get("immediate_situation"),dict) else {}
    for row in situation.get("observables",[]) if isinstance(situation.get("observables"),list) else []:
        if isinstance(row,dict) and isinstance(row.get("observable_id"),str):
            rows.append((row["observable_id"],row.get("available_from_story_order")))
    memory=payload.get("perspective_memory",{}) if isinstance(payload.get("perspective_memory"),dict) else {}
    for row in memory.get("episodic_visible_events",[]) if isinstance(memory.get("episodic_visible_events"),list) else []:
        if isinstance(row,dict) and isinstance(row.get("event_id"),str):
            rows.append((row["event_id"],row.get("available_from_story_order")))
    for row in memory.get("visibility_tagged_facts",[]) if isinstance(memory.get("visibility_tagged_facts"),list) else []:
        if isinstance(row,dict) and isinstance(row.get("fact_id"),str):
            rows.append((row["fact_id"],row.get("available_from_story_order")))
    for row in memory.get("situation_patterns",[]) if isinstance(memory.get("situation_patterns"),list) else []:
        if isinstance(row,dict) and isinstance(row.get("pattern_id"),str):
            rows.append((row["pattern_id"],row.get("available_from_story_order")))
    return rows

def validate_contract_input_bindings(cid:str,input_payload:dict[str,Any])->list[str]:
    e=[]
    if cid=="character.action_propose":
        current=input_payload.get("current_story_order"); rows=_character_evidence_rows(input_payload); seen=set()
        for evidence_id,available in rows:
            if evidence_id in seen:e.append(f"character evidence id duplicated: {evidence_id}")
            seen.add(evidence_id)
            if isinstance(current,int) and not isinstance(current,bool) and isinstance(available,int) and not isinstance(available,bool) and available>current:
                e.append(f"character evidence from future story order: {evidence_id}")
        return e
    if cid=="continuity.commitment_audit":
        current=input_payload.get("current_story_order"); candidate=input_payload.get("candidate",{}); seen=set()
        for row in candidate.get("evidence",[]) if isinstance(candidate,dict) and isinstance(candidate.get("evidence"),list) else []:
            if not isinstance(row,dict):continue
            eid=row.get("evidence_id"); order=row.get("story_order")
            if eid in seen:e.append(f"continuity candidate evidence id duplicated: {eid}")
            seen.add(eid)
            if isinstance(current,int) and not isinstance(current,bool) and isinstance(order,int) and not isinstance(order,bool) and order>current:e.append(f"continuity candidate evidence from future story order: {eid}")
        for field,id_key in (("commitments","commitment_id"),("required_transitions","transition_id")):
            ids=[row.get(id_key) for row in input_payload.get(field,[]) if isinstance(row,dict)]
            if len(ids)!=len(set(ids)):e.append(f"duplicate {id_key} in continuity input")
        return e
    if cid=="relationship.memory_reconcile":
        current=input_payload.get("current_story_order"); evidence=input_payload.get("ordered_evidence",[]); seen=set(); source_refs=set()
        participants=input_payload.get("participants",[])
        if isinstance(participants,list) and len(participants)!=len(set(participants)):e.append("relationship participants contain duplicates")
        for row in evidence if isinstance(evidence,list) else []:
            if not isinstance(row,dict):continue
            eid=row.get("evidence_id"); order=row.get("story_order"); ref=row.get("source_ref")
            if eid in seen:e.append(f"relationship evidence id duplicated: {eid}")
            seen.add(eid)
            if isinstance(ref,str):source_refs.add(ref)
            if isinstance(current,int) and not isinstance(current,bool) and isinstance(order,int) and not isinstance(order,bool) and order>current:e.append(f"relationship evidence from future story order: {eid}")
        for snap in input_payload.get("derived_snapshots",[]) if isinstance(input_payload.get("derived_snapshots"),list) else []:
            if not isinstance(snap,dict):continue
            order=snap.get("as_of_story_order")
            if isinstance(current,int) and not isinstance(current,bool) and isinstance(order,int) and not isinstance(order,bool) and order>current:e.append(f"relationship snapshot from future story order: {snap.get('snapshot_id')}")
            refs=snap.get("source_refs",[])
            if isinstance(refs,list):
                unknown=sorted({x for x in refs if isinstance(x,str)}-source_refs)
                if unknown:e.append("relationship snapshot cites unknown source refs: "+", ".join(unknown))
        return e
    return e

def validate_contract_input(cid:str,contract:dict[str,Any],input_payload:dict[str,Any])->list[str]:
    e=[]
    blocked=find_named_keys(input_payload,set(contract.get("forbidden_input_keys",[])))
    if blocked:e.append(f"contract {cid} input contains forbidden fields: "+", ".join(blocked))
    schema=contract.get("input_contract")
    if isinstance(schema,dict) and schema:
        e += [f"contract {cid} input_contract {x}" for x in validate_typed_value(input_payload,schema,"$.payload")]
    if not e:e += validate_contract_input_bindings(cid,input_payload)
    return e

def validate_contract_result_bindings(job:dict[str,Any],judgment:dict[str,Any])->list[str]:
    cid=job.get("input",{}).get("model_contract_id"); payload=job.get("input",{}).get("payload",{}); e=[]
    if not isinstance(payload,dict) or not isinstance(judgment,dict):return e
    if cid=="character.action_propose":
        if judgment.get("character_id")!=payload.get("character_id"):e.append("character action result mismatch: character_id")
        if judgment.get("active_agenda")!=payload.get("active_agenda"):e.append("character action result mismatch: active_agenda")
        evidence={eid for eid,_ in _character_evidence_rows(payload)}
        proposals=judgment.get("proposals",[])
        if isinstance(proposals,list):
            for i,proposal in enumerate(proposals):
                if not isinstance(proposal,dict):continue
                bases=proposal.get("knowledge_basis",[]); seen=set()
                if not isinstance(bases,list):continue
                for basis in bases:
                    if not isinstance(basis,dict):continue
                    evidence_id=basis.get("evidence_id")
                    if evidence_id in seen:e.append(f"proposal {i} duplicates evidence basis: {evidence_id}")
                    seen.add(evidence_id)
                    if evidence_id not in evidence:e.append(f"proposal {i} references unknown character evidence: {evidence_id}")
        return e
    if cid=="continuity.commitment_audit":
        candidate=payload.get("candidate",{}); evidence_ids={row.get("evidence_id") for row in candidate.get("evidence",[]) if isinstance(row,dict)} if isinstance(candidate,dict) else set()
        expected={"commitments":{row.get("commitment_id") for row in payload.get("commitments",[]) if isinstance(row,dict)},"transitions":{row.get("transition_id") for row in payload.get("required_transitions",[]) if isinstance(row,dict)}}
        for field,id_key in (("commitments","commitment_id"),("transitions","transition_id")):
            rows=judgment.get(field,[]); seen=set()
            if not isinstance(rows,list):continue
            for row in rows:
                if not isinstance(row,dict):continue
                rid=row.get(id_key)
                if rid in seen:e.append(f"continuity result duplicates {id_key}: {rid}")
                seen.add(rid)
                if rid not in expected[field]:e.append(f"continuity result references unknown {id_key}: {rid}")
                refs=row.get("evidence_ids",[])
                if isinstance(refs,list):
                    unknown=sorted(set(refs)-evidence_ids)
                    if unknown:e.append(f"continuity {rid} cites unknown evidence ids: "+", ".join(unknown))
                    if row.get("status") in {"advanced","satisfied","supported","violated"} and not refs:e.append(f"continuity {rid} status {row.get('status')} requires evidence ids")
            missing=sorted(expected[field]-seen)
            if missing:e.append(f"continuity result must cover every {id_key}: "+", ".join(missing))
        return e
    if cid=="relationship.memory_reconcile":
        if judgment.get("relationship_id")!=payload.get("relationship_id"):e.append("relationship result mismatch: relationship_id")
        evidence_rows=payload.get("ordered_evidence",[]); allowed_refs={row.get("source_ref") for row in evidence_rows if isinstance(row,dict)}
        refs=judgment.get("source_refs",[])
        if isinstance(refs,list):
            unknown=sorted(set(refs)-allowed_refs)
            if unknown:e.append("relationship result cites unknown source refs: "+", ".join(unknown))
        for row in judgment.get("unresolved_conflicts",[]) if isinstance(judgment.get("unresolved_conflicts"),list) else []:
            if isinstance(row,dict) and isinstance(row.get("source_refs"),list):
                unknown=sorted(set(row["source_refs"])-allowed_refs)
                if unknown:e.append("relationship conflict cites unknown source refs: "+", ".join(unknown))
        snapshot_ids={row.get("snapshot_id") for row in payload.get("derived_snapshots",[]) if isinstance(row,dict)}
        invalidated=judgment.get("invalidated_derived_refs",[])
        if isinstance(invalidated,list):
            unknown=sorted(set(invalidated)-snapshot_ids)
            if unknown:e.append("relationship result invalidates unknown snapshots: "+", ".join(unknown))
        return e
    return e

def semantic_payload(job:dict[str,Any])->dict[str,Any]:return {k:job.get(k,{} if k in {"input","output_contract"} else []) for k in ("kind","subject_id","input","rubric","output_contract")}
def fingerprint_for(job:dict[str,Any])->str:return "sha256:"+hashlib.sha256(canonical(semantic_payload(job))).hexdigest()
def worker_job_view(job:dict[str,Any])->dict[str,Any]:
    """Return only reviewer-visible semantic job fields; runtime dispatch proof stays private."""
    return {k:json.loads(json.dumps(job[k])) for k in ("job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance","execution") if k in job}
def _production_review_qualification_errors(job:dict[str,Any])->list[str]:
    input_obj=job.get("input")
    if not isinstance(input_obj,dict) or input_obj.get("model_contract_id")!="quality.production_review":return []
    proof=job.get("dispatch_proof")
    if not isinstance(proof,dict):return ["quality.production_review dispatch requires pre-independent qualification receipt"]
    payload=input_obj.get("payload")
    if not isinstance(payload,dict):return ["quality.production_review payload required"]
    quality_root=HERE.parents[1]/"quality"
    if str(quality_root) not in sys.path:sys.path.insert(0,str(quality_root))
    from candidate_qualification import validate_qualification_receipt
    return ["production review qualification: "+x for x in validate_qualification_receipt(proof,candidate_fingerprint=payload.get("candidate_fingerprint"),subject_id=job.get("subject_id"),require_qualified=True)]
def validate_dispatchable_job(job:dict[str,Any])->list[str]:
    return validate_job(job)+_production_review_qualification_errors(job)
def validate_job(job:dict[str,Any])->list[str]:
    e=[];required={"job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance"};missing=sorted(required-set(job))
    if missing:return ["missing fields: "+", ".join(missing)]
    if job["kind"] not in ALLOWED_KINDS:e.append(f"unsupported kind: {job['kind']}")
    leaks=find_forbidden_keys({"input":job.get("input"),"rubric":job.get("rubric"),"output_contract":job.get("output_contract")})
    if job["kind"]=="eval_judge" and leaks:e.append("answer-key leakage: "+", ".join(leaks))
    if any(job.get("permissions",{}).get(k) is not False for k in WRITE_KEYS):e.append("semantic job write permissions must be false")
    if job.get("input_fingerprint")!=fingerprint_for(job):e.append("input_fingerprint mismatch")
    x=job.get("execution")
    if x is not None and (not isinstance(x,dict) or set(x)-{"source_session_id","worker_session_id","handoff_id","attempt_id"}):e.append("invalid execution lineage")
    return e
def make_contract_job(cid:str,subject_id:str,input_payload:dict[str,Any],*,registry_path:Path|None=None,job_id:str|None=None,source_session_id:str|None=None,handoff_id:str|None=None,qualification_receipt:dict[str,Any]|None=None)->dict[str,Any]:
    if not isinstance(subject_id,str) or not subject_id.strip():raise ValueError("subject_id required")
    if not isinstance(input_payload,dict):raise ValueError("semantic contract input must be object")
    pack_id=None
    if registry_path is None:registry_path,pack_id=resolve_contract_registry(cid)
    r=load_contract_registry(registry_path);c=r["contracts"].get(cid)
    if not isinstance(c,dict):raise ValueError(f"contract {cid} not in registry")
    input_errors=validate_contract_input(cid,c,input_payload)
    if input_errors:raise ValueError("; ".join(input_errors))
    job={"job_id":job_id or "SEM-CONTRACT-"+hashlib.sha256(f"{cid}:{subject_id}".encode()).hexdigest()[:16],"kind":c["kind"],"subject_id":subject_id,"created_at":datetime.now(timezone.utc).isoformat(),"input_fingerprint":"","input":{"model_contract_id":cid,"model_contract_version":r.get("version"),"purpose":c.get("purpose"),"payload":input_payload,**({"default_personas":c["default_personas"]} if isinstance(c.get("default_personas"),dict) else {})},"rubric":list(c["rubric"]),"output_contract":c["output_contract"],"permissions":dict(c["permissions"]),"provenance":{"source":"model_contract_pack","registry_schema":r["schema"],"registry_version":r.get("version"),"registry_path":str(registry_path.relative_to(HERE)) if registry_path.is_relative_to(HERE) else str(registry_path),"pack_id":pack_id,"model_contract_id":cid,"input_contract_validated":bool(c.get("input_contract")),"independent_gate":bool(c.get("independent_gate",False))},"execution":{"source_session_id":source_session_id,"worker_session_id":None,"handoff_id":handoff_id,"attempt_id":None}}
    job["input_fingerprint"]=fingerprint_for(job)
    if cid=="quality.production_review":
        if qualification_receipt is None:raise ValueError("quality.production_review requires pre-independent qualification receipt")
        job["dispatch_proof"]=json.loads(json.dumps(qualification_receipt))
        e=validate_dispatchable_job(job)
    else:e=validate_job(job)
    if e:raise ValueError("prepared contract job invalid: "+"; ".join(e))
    return job
def make_eval_jobs(queue:dict[str,Any],*,source_session_id:str|None=None,handoff_id:str|None=None)->dict[str,Any]:
    if queue.get("blind") is not True:raise ValueError("eval queue must declare blind=true")
    leaks=find_forbidden_keys(queue)
    if leaks:raise ValueError("blind queue leaks answer keys: "+", ".join(leaks))
    jobs=[]
    for case in queue.get("cases",[]):
        sid=case["id"];job={"job_id":f"SEM-EVAL-{sid}","kind":"eval_judge","subject_id":sid,"created_at":datetime.now(timezone.utc).isoformat(),"input_fingerprint":"","input":{"type":case.get("type"),"domain":case.get("domain"),"fixture":case.get("fixture",{})},"rubric":case.get("rubric",[]),"output_contract":case.get("judgment_contract",{}),"permissions":{"canon_write":False,"framework_behavior_write":False,"durable_user_taste_write":False,"allowed_result_scope":"observation"},"provenance":{"source":"blind_eval_queue","suite_version":queue.get("suite_version")},"execution":{"source_session_id":source_session_id,"worker_session_id":None,"handoff_id":handoff_id,"attempt_id":None}}
        job["input_fingerprint"]=fingerprint_for(job);e=validate_job(job)
        if e:raise ValueError("prepared eval job invalid: "+"; ".join(e))
        jobs.append(job)
    return {"semantic_worker_queue_version":"2","source_suite_version":queue.get("suite_version"),"blind":True,"jobs":jobs}
def validate_result(job:dict[str,Any],result:dict[str,Any])->list[str]:
    e=validate_job(job);required={"job_id","subject_id","kind","input_fingerprint","status","worker","judgment","proposals","errors"};missing=sorted(required-set(result))
    if missing:return e+["result missing fields: "+", ".join(missing)]
    for k in ("job_id","subject_id","kind","input_fingerprint"):
        if result.get(k)!=job.get(k):e.append(f"result/job mismatch: {k}")
    if result.get("status") not in {"completed","unsupported","failed"}:e.append("invalid result status")
    w=result.get("worker",{})
    if not isinstance(w,dict) or not w.get("provider") or not w.get("model_or_reviewer"):e.append("worker.provider/model_or_reviewer required")
    j=result.get("judgment",{});conf=j.get("confidence") if isinstance(j,dict) else None
    if not isinstance(conf,(int,float)) or isinstance(conf,bool) or not 0<=conf<=1:e.append("judgment.confidence must be 0..1")
    if result.get("status")=="completed" and isinstance(job.get("output_contract"),dict) and job["output_contract"].get("type"):e += ["output_contract "+x for x in validate_typed_value(j,job["output_contract"],"$.judgment")]
    if result.get("status")=="completed" and not any(x.startswith("output_contract ") for x in e):e += validate_contract_result_bindings(job,j)
    if result.get("status")=="completed" and job["kind"]=="eval_judge":
        if j.get("verdict") not in {"accept","reject",None}:e.append("eval verdict must be accept|reject|null")
        if j.get("result") not in {"pass","fail",None}:e.append("eval result must be pass|fail|null")
        if j.get("verdict") is None and j.get("result") is None:e.append("completed eval requires verdict or result")
    forbidden={"settle_canon","promote_generic_hard_rule","overwrite_durable_user_taste","grant_permissions"}
    for p in result.get("proposals",[]):
        if isinstance(p,dict) and p.get("action") in forbidden:e.append(f"forbidden direct proposal action: {p.get('action')}")
    lineage=job.get("execution") or {};rx=result.get("execution") or {}
    for k in ("source_session_id","handoff_id"):
        if lineage.get(k) and rx.get(k) not in {None,lineage[k]}:e.append(f"execution lineage mismatch: {k}")
    return e
def load_jobs(payload:dict[str,Any])->dict[str,dict[str,Any]]:
    out={}
    for j in payload.get("jobs",[]):
        if j["job_id"] in out:raise ValueError(f"duplicate job_id: {j['job_id']}")
        out[j["job_id"]]=j
    return out
def validate_results(jobs_payload:dict[str,Any],results_payload:dict[str,Any])->tuple[list[dict[str,Any]],list[str]]:
    jobs=load_jobs(jobs_payload);valid=[];e=[];seen=set()
    for r in results_payload.get("results",[]):
        jid=r.get("job_id")
        if jid in seen:e.append(f"duplicate result job_id: {jid}");continue
        seen.add(jid);j=jobs.get(jid)
        if not j:e.append(f"result references unknown job_id: {jid}");continue
        errs=validate_result(j,r)
        if errs:e += [f"{jid}: {x}" for x in errs]
        else:valid.append(r)
    return valid,e
def eval_judgments(results:list[dict[str,Any]])->dict[str,Any]:
    out={}
    for r in results:
        if r["kind"]!="eval_judge" or r["status"]!="completed":continue
        j=r["judgment"];v={"codes":j.get("codes",[]),"evidence":j.get("evidence",[]),"confidence":j.get("confidence"),"worker":r.get("worker"),"input_fingerprint":r.get("input_fingerprint"),"execution":r.get("execution")}
        if j.get("verdict") is not None:v["verdict"]=j["verdict"]
        if j.get("result") is not None:v["result"]=j["result"]
        out[r["subject_id"]]=v
    return out
def catalog_summary()->dict[str,Any]:
    c=load_contract_catalog();return {"schema":c["schema"],"loading_policy":c["loading_policy"],"packs":[{"id":p["id"],"description":p.get("description"),"contracts":p["contracts"],"load_when":p.get("load_when")} for p in c["packs"]],"model_execution":False}
def self_test()->int:
    q={"blind":True,"suite_version":"self","cases":[{"id":"CASE-1","type":"regression","domain":"reader","fixture":{"text":"x"},"rubric":["judge"],"judgment_contract":{}}]}
    jobs=make_eval_jobs(q,source_session_id="SES-A",handoff_id="HO-A");ej=jobs["jobs"][0]
    er={"job_id":ej["job_id"],"subject_id":ej["subject_id"],"kind":ej["kind"],"input_fingerprint":ej["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"verdict":"accept","result":None,"codes":[],"evidence":["fixture"],"confidence":1.0},"proposals":[],"errors":[],"execution":{"source_session_id":"SES-A","worker_session_id":"SES-B","handoff_id":"HO-A","attempt_id":"ATT-1"}}
    lineage=fingerprint_for({**ej,"execution":{"source_session_id":"OTHER"}})==ej["input_fingerprint"]

    cj=make_contract_job("reader.reaction","CH-SELF",{"candidate_text":"x","persona_id":"binge_reader"})
    good={"job_id":cj["job_id"],"subject_id":cj["subject_id"],"kind":cj["kind"],"input_fingerprint":cj["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"confidence":.9,"would_continue":True,"continue_desire":.8,"reason":"momentum"},"proposals":[],"errors":[]}
    bad=json.loads(json.dumps(good));bad["judgment"]["continue_desire"]=2
    auto=cj["provenance"].get("pack_id")=="quality" and cj["provenance"].get("registry_path")=="contracts/quality.json"
    typed=any("above maximum" in x for x in validate_result(cj,bad));guard=False
    try:make_contract_job("learning.mechanism_analyze","CORP",{"source":{"raw_text":"forbidden"}})
    except ValueError:guard=True
    typed_input_schema={"type":"object","required":["candidate_text"],"properties":{"candidate_text":{"type":"string","minLength":1}},"additionalProperties":False}
    typed_input_ok=not validate_contract_input("SELF",{"input_contract":typed_input_schema},{"candidate_text":"x"})
    typed_input_reject=bool(validate_contract_input("SELF",{"input_contract":typed_input_schema},{"candidate_text":"x","hidden":"no"}))

    character_payload={
        "character_id":"CHAR-SELF","current_story_order":5,"active_agenda":"Keep leverage.",
        "perceived_state":{"beliefs":["The offer is weak."],"goals":["Improve terms."],"fears":[],"assumptions":[]},
        "immediate_situation":{"observables":[{"observable_id":"OBS-1","observation":"The offer changed.","source_ref":"scene:self","available_from_story_order":5}],"pressures":["Time is short."],"available_options":["counter","stall"]},
        "perspective_memory":{"episodic_visible_events":[],"visibility_tagged_facts":[
            {"fact_id":"FACT-1","claim":"The earlier offer was lower.","epistemic_status":"known","acquisition_mode":"directly_observed","source_ref":"accepted:self-1","available_from_story_order":3},
            {"fact_id":"FACT-2","claim":"The other side cannot move.","epistemic_status":"contradicted","acquisition_mode":"told_by","source_ref":"accepted:self-2","available_from_story_order":4}],"situation_patterns":[]},
        "relationship_state":{},"task_state":{},"location":{},"constraints":[]
    }
    char_job=make_contract_job("character.action_propose","CHAR-SELF",character_payload)
    char_result={"job_id":char_job["job_id"],"subject_id":char_job["subject_id"],"kind":char_job["kind"],"input_fingerprint":char_job["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"confidence":.9,"character_id":"CHAR-SELF","active_agenda":"Keep leverage.","proposals":[{"action":"Counter the offer.","tactic":"Anchor higher.","why_now":"The changed offer creates room.","expected_resistance":"Pushback.","motive_basis":"Preserve leverage.","knowledge_basis":[{"evidence_id":"FACT-1","use":"supports"}],"risk_or_cost":"Delay."}]},"proposals":[],"errors":[]}
    character_binding_ok=not validate_result(char_job,char_result)
    bad_ref=json.loads(json.dumps(char_result));bad_ref["judgment"]["proposals"][0]["knowledge_basis"]=[{"evidence_id":"MISSING","use":"supports"}]
    character_unknown_ref_guard=any("unknown character evidence" in x for x in validate_result(char_job,bad_ref))
    semantic_epistemic=json.loads(json.dumps(char_result));semantic_epistemic["judgment"]["proposals"][0]["knowledge_basis"]=[{"evidence_id":"FACT-2","use":"supports"}]
    character_epistemic_semantics_not_reinterpreted=not validate_result(char_job,semantic_epistemic)
    future_input=json.loads(json.dumps(character_payload));future_input["immediate_situation"]["observables"][0]["available_from_story_order"]=6
    character_future_guard=False
    try:make_contract_job("character.action_propose","CHAR-FUTURE",future_input)
    except ValueError as exc:character_future_guard="future story order" in str(exc)

    continuity_payload={
        "candidate":{"source_ref":"candidate:self","evidence":[{"evidence_id":"E-1","statement":"The obligation remains active.","source_ref":"candidate:self#1","story_order":5}]},
        "current_story_order":5,
        "commitments":[{"commitment_id":"COM-1","statement":"Keep the obligation live.","authority":"active_plan","source_ref":"plan:self"}],
        "required_transitions":[{"transition_id":"TR-1","description":"Leverage changes.","authority":"active_plan","source_ref":"plan:self"}],
        "initial_facts":[],"current_story_point":"SCN-5"
    }
    continuity_job=make_contract_job("continuity.commitment_audit","SCN-5",continuity_payload)
    continuity_result={"job_id":continuity_job["job_id"],"subject_id":continuity_job["subject_id"],"kind":continuity_job["kind"],"input_fingerprint":continuity_job["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"confidence":.9,"commitments":[{"commitment_id":"COM-1","status":"preserved","evidence_ids":["E-1"],"reason":"Still live."}],"transitions":[{"transition_id":"TR-1","status":"supported","evidence_ids":["E-1"],"reason":"Evidence shows changed leverage."}],"violations":[],"repair_routes":[]},"proposals":[],"errors":[]}
    continuity_binding_ok=not validate_result(continuity_job,continuity_result)
    continuity_bad=json.loads(json.dumps(continuity_result));continuity_bad["judgment"]["transitions"][0]["evidence_ids"]=["E-MISSING"]
    continuity_unknown_evidence_guard=any("unknown evidence ids" in x for x in validate_result(continuity_job,continuity_bad))
    continuity_missing=json.loads(json.dumps(continuity_result));continuity_missing["judgment"]["commitments"]=[]
    continuity_complete_coverage_guard=any("cover every commitment_id" in x for x in validate_result(continuity_job,continuity_missing))
    continuity_future=json.loads(json.dumps(continuity_payload));continuity_future["candidate"]["evidence"][0]["story_order"]=6
    continuity_future_guard=False
    try:make_contract_job("continuity.commitment_audit","SCN-FUTURE",continuity_future)
    except ValueError as exc:continuity_future_guard="future story order" in str(exc)

    relationship_payload={
        "relationship_id":"REL-SELF","current_story_order":5,"participants":["CHAR-A","CHAR-B"],
        "ordered_evidence":[{"evidence_id":"RE-1","story_order":4,"source_ref":"accepted:rel-1","authority":"accepted","event":"A promise created an obligation.","effects":{"obligation":"open"}}],
        "derived_snapshots":[{"snapshot_id":"RS-1","as_of_story_order":4,"source_refs":["accepted:rel-1"],"shared_state":{"status":"strained"},"per_character_perception":{"CHAR-A":"uneasy","CHAR-B":"guarded"},"open_obligations":["promise"],"emotional_residue":["distrust"]}]
    }
    relationship_job=make_contract_job("relationship.memory_reconcile","REL-SELF",relationship_payload)
    relationship_result={"job_id":relationship_job["job_id"],"subject_id":relationship_job["subject_id"],"kind":relationship_job["kind"],"input_fingerprint":relationship_job["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"confidence":.9,"relationship_id":"REL-SELF","reconciled_state":{"shared_external_state":{"status":"strained"},"per_character_perception":{"CHAR-A":"uneasy","CHAR-B":"guarded"},"open_obligations":["promise"],"emotional_residue":["distrust"]},"source_refs":["accepted:rel-1"],"unresolved_conflicts":[],"invalidated_derived_refs":[]},"proposals":[],"errors":[]}
    relationship_binding_ok=not validate_result(relationship_job,relationship_result)
    relationship_bad=json.loads(json.dumps(relationship_result));relationship_bad["judgment"]["source_refs"]=["accepted:missing"]
    relationship_source_guard=any("unknown source refs" in x for x in validate_result(relationship_job,relationship_bad))
    relationship_future=json.loads(json.dumps(relationship_payload));relationship_future["ordered_evidence"][0]["story_order"]=6
    relationship_future_guard=False
    try:make_contract_job("relationship.memory_reconcile","REL-FUTURE",relationship_future)
    except ValueError as exc:relationship_future_guard="future story order" in str(exc)

    ok=all((not validate_job(ej),not validate_result(ej,er),lineage,not validate_job(cj),not validate_result(cj,good),auto,typed,guard,typed_input_ok,typed_input_reject,character_binding_ok,character_unknown_ref_guard,character_epistemic_semantics_not_reinterpreted,character_future_guard,continuity_binding_ok,continuity_unknown_evidence_guard,continuity_complete_coverage_guard,continuity_future_guard,relationship_binding_ok,relationship_source_guard,relationship_future_guard))
    dump_json({"semantic_router_contract":"PASS" if ok else "FAIL","fingerprint_excludes_runtime_lineage":lineage,"catalog_exact_id_resolution":auto,"typed_input_validation":typed_input_ok and typed_input_reject,"typed_output_validation":typed,"contract_input_guard":guard,"character_evidence_binding":character_binding_ok,"character_unknown_evidence_guard":character_unknown_ref_guard,"character_epistemic_semantics_not_reinterpreted":character_epistemic_semantics_not_reinterpreted,"character_future_evidence_guard":character_future_guard,"continuity_evidence_binding":continuity_binding_ok,"continuity_unknown_evidence_guard":continuity_unknown_evidence_guard,"continuity_complete_coverage_guard":continuity_complete_coverage_guard,"continuity_future_evidence_guard":continuity_future_guard,"relationship_evidence_binding":relationship_binding_ok,"relationship_source_guard":relationship_source_guard,"relationship_future_evidence_guard":relationship_future_guard,"aggregate_registry_required":False,"semantic_intelligence_externalized":True,"model_execution":False})
    return 0 if ok else 1

def main()->int:
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="command",required=True)
    x=s.add_parser("prepare-evals");x.add_argument("--queue",required=True);x.add_argument("--output");x.add_argument("--source-session-id");x.add_argument("--handoff-id")
    x=s.add_parser("prepare-contract");x.add_argument("--contract",required=True);x.add_argument("--subject-id",required=True);x.add_argument("--input",required=True);x.add_argument("--job-id");x.add_argument("--registry");x.add_argument("--source-session-id");x.add_argument("--handoff-id");x.add_argument("--qualification-receipt");x.add_argument("--output")
    x=s.add_parser("list-contracts");x.add_argument("--registry");s.add_parser("catalog")
    x=s.add_parser("validate-jobs");x.add_argument("--jobs",required=True)
    x=s.add_parser("validate-dispatchable-jobs");x.add_argument("--jobs",required=True)
    x=s.add_parser("validate-results");x.add_argument("--jobs",required=True);x.add_argument("--results",required=True);x.add_argument("--judgments-output")
    s.add_parser("self-test");a=p.parse_args()
    if a.command=="self-test":return self_test()
    if a.command=="catalog":dump_json(catalog_summary());return 0
    if a.command=="prepare-evals":dump_json(make_eval_jobs(load_json(Path(a.queue)),source_session_id=a.source_session_id,handoff_id=a.handoff_id),Path(a.output) if a.output else None);return 0
    if a.command=="prepare-contract":dump_json(make_contract_job(a.contract,a.subject_id,load_json(Path(a.input)),registry_path=Path(a.registry).resolve() if a.registry else None,job_id=a.job_id,source_session_id=a.source_session_id,handoff_id=a.handoff_id,qualification_receipt=load_json(Path(a.qualification_receipt)) if a.qualification_receipt else None),Path(a.output) if a.output else None);return 0
    if a.command=="list-contracts":
        if a.registry:
            r=load_contract_registry(Path(a.registry));dump_json({"schema":r["schema"],"version":r.get("version"),"contracts":sorted(r["contracts"]),"model_execution":False})
        else:dump_json(catalog_summary())
        return 0
    if a.command in {"validate-jobs","validate-dispatchable-jobs"}:
        payload=load_json(Path(a.jobs));validator=validate_dispatchable_job if a.command=="validate-dispatchable-jobs" else validate_job;e=[f"{j.get('job_id')}: {x}" for j in payload.get("jobs",[]) for x in validator(j)]
        if e:
            for x in e:print(x,file=sys.stderr)
            return 1
        print(f"validated semantic jobs: {len(payload.get('jobs',[]))}");return 0
    valid,e=validate_results(load_json(Path(a.jobs)),load_json(Path(a.results)))
    if e:
        for x in e:print(x,file=sys.stderr)
        return 1
    j=eval_judgments(valid)
    if a.judgments_output:dump_json(j,Path(a.judgments_output))
    print(f"validated semantic results: {len(valid)}; eval judgments: {len(j)}");return 0
if __name__=="__main__":raise SystemExit(main())