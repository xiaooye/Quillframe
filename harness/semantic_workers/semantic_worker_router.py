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
def validate_contract_input(cid:str,contract:dict[str,Any],input_payload:dict[str,Any])->list[str]:
    e=[]
    blocked=find_named_keys(input_payload,set(contract.get("forbidden_input_keys",[])))
    if blocked:e.append(f"contract {cid} input contains forbidden fields: "+", ".join(blocked))
    schema=contract.get("input_contract")
    if isinstance(schema,dict) and schema:
        e += [f"contract {cid} input_contract {x}" for x in validate_typed_value(input_payload,schema,"$.payload")]
    return e
def semantic_payload(job:dict[str,Any])->dict[str,Any]:return {k:job.get(k,{} if k in {"input","output_contract"} else []) for k in ("kind","subject_id","input","rubric","output_contract")}
def fingerprint_for(job:dict[str,Any])->str:return "sha256:"+hashlib.sha256(canonical(semantic_payload(job))).hexdigest()
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
def make_contract_job(cid:str,subject_id:str,input_payload:dict[str,Any],*,registry_path:Path|None=None,job_id:str|None=None,source_session_id:str|None=None,handoff_id:str|None=None)->dict[str,Any]:
    if not isinstance(subject_id,str) or not subject_id.strip():raise ValueError("subject_id required")
    if not isinstance(input_payload,dict):raise ValueError("semantic contract input must be object")
    pack_id=None
    if registry_path is None:registry_path,pack_id=resolve_contract_registry(cid)
    r=load_contract_registry(registry_path);c=r["contracts"].get(cid)
    if not isinstance(c,dict):raise ValueError(f"contract {cid} not in registry")
    input_errors=validate_contract_input(cid,c,input_payload)
    if input_errors:raise ValueError("; ".join(input_errors))
    job={"job_id":job_id or "SEM-CONTRACT-"+hashlib.sha256(f"{cid}:{subject_id}".encode()).hexdigest()[:16],"kind":c["kind"],"subject_id":subject_id,"created_at":datetime.now(timezone.utc).isoformat(),"input_fingerprint":"","input":{"model_contract_id":cid,"model_contract_version":r.get("version"),"purpose":c.get("purpose"),"payload":input_payload,**({"default_personas":c["default_personas"]} if isinstance(c.get("default_personas"),dict) else {})},"rubric":list(c["rubric"]),"output_contract":c["output_contract"],"permissions":dict(c["permissions"]),"provenance":{"source":"model_contract_pack","registry_schema":r["schema"],"registry_version":r.get("version"),"registry_path":str(registry_path.relative_to(HERE)) if registry_path.is_relative_to(HERE) else str(registry_path),"pack_id":pack_id,"model_contract_id":cid,"input_contract_validated":bool(c.get("input_contract")),"independent_gate":bool(c.get("independent_gate",False))},"execution":{"source_session_id":source_session_id,"worker_session_id":None,"handoff_id":handoff_id,"attempt_id":None}}
    job["input_fingerprint"]=fingerprint_for(job);e=validate_job(job)
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
    q={"blind":True,"suite_version":"self","cases":[{"id":"CASE-1","type":"regression","domain":"reader","fixture":{"text":"x"},"rubric":["judge"],"judgment_contract":{}}]};jobs=make_eval_jobs(q,source_session_id="SES-A",handoff_id="HO-A");ej=jobs["jobs"][0]
    er={"job_id":ej["job_id"],"subject_id":ej["subject_id"],"kind":ej["kind"],"input_fingerprint":ej["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"verdict":"accept","result":None,"codes":[],"evidence":["fixture"],"confidence":1.0},"proposals":[],"errors":[],"execution":{"source_session_id":"SES-A","worker_session_id":"SES-B","handoff_id":"HO-A","attempt_id":"ATT-1"}}
    lineage=fingerprint_for({**ej,"execution":{"source_session_id":"OTHER"}})==ej["input_fingerprint"]
    cj=make_contract_job("reader.reaction","CH-SELF",{"candidate_text":"x","persona_id":"binge_reader"});good={"job_id":cj["job_id"],"subject_id":cj["subject_id"],"kind":cj["kind"],"input_fingerprint":cj["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"fixture"},"judgment":{"confidence":.9,"would_continue":True,"continue_desire":.8,"reason":"momentum"},"proposals":[],"errors":[]};bad=json.loads(json.dumps(good));bad["judgment"]["continue_desire"]=2
    auto=cj["provenance"].get("pack_id")=="quality" and cj["provenance"].get("registry_path")=="contracts/quality.json";typed=any("above maximum" in x for x in validate_result(cj,bad));guard=False
    try:make_contract_job("learning.mechanism_analyze","CORP",{"source":{"raw_text":"forbidden"}})
    except ValueError:guard=True
    typed_input_schema={"type":"object","required":["candidate_text"],"properties":{"candidate_text":{"type":"string","minLength":1}},"additionalProperties":False};typed_input_ok=not validate_contract_input("SELF",{"input_contract":typed_input_schema},{"candidate_text":"x"});typed_input_reject=bool(validate_contract_input("SELF",{"input_contract":typed_input_schema},{"candidate_text":"x","hidden":"no"}))
    ok=not validate_job(ej) and not validate_result(ej,er) and lineage and not validate_job(cj) and not validate_result(cj,good) and auto and typed and guard and typed_input_ok and typed_input_reject
    dump_json({"semantic_router_contract":"PASS" if ok else "FAIL","fingerprint_excludes_runtime_lineage":lineage,"catalog_exact_id_resolution":auto,"typed_input_validation":typed_input_ok and typed_input_reject,"typed_output_validation":typed,"contract_input_guard":guard,"aggregate_registry_required":False,"semantic_intelligence_externalized":True,"model_execution":False});return 0 if ok else 1
def main()->int:
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="command",required=True)
    x=s.add_parser("prepare-evals");x.add_argument("--queue",required=True);x.add_argument("--output");x.add_argument("--source-session-id");x.add_argument("--handoff-id")
    x=s.add_parser("prepare-contract");x.add_argument("--contract",required=True);x.add_argument("--subject-id",required=True);x.add_argument("--input",required=True);x.add_argument("--job-id");x.add_argument("--registry");x.add_argument("--source-session-id");x.add_argument("--handoff-id");x.add_argument("--output")
    x=s.add_parser("list-contracts");x.add_argument("--registry");s.add_parser("catalog")
    x=s.add_parser("validate-jobs");x.add_argument("--jobs",required=True)
    x=s.add_parser("validate-results");x.add_argument("--jobs",required=True);x.add_argument("--results",required=True);x.add_argument("--judgments-output")
    s.add_parser("self-test");a=p.parse_args()
    if a.command=="self-test":return self_test()
    if a.command=="catalog":dump_json(catalog_summary());return 0
    if a.command=="prepare-evals":dump_json(make_eval_jobs(load_json(Path(a.queue)),source_session_id=a.source_session_id,handoff_id=a.handoff_id),Path(a.output) if a.output else None);return 0
    if a.command=="prepare-contract":dump_json(make_contract_job(a.contract,a.subject_id,load_json(Path(a.input)),registry_path=Path(a.registry).resolve() if a.registry else None,job_id=a.job_id,source_session_id=a.source_session_id,handoff_id=a.handoff_id),Path(a.output) if a.output else None);return 0
    if a.command=="list-contracts":
        if a.registry:
            r=load_contract_registry(Path(a.registry));dump_json({"schema":r["schema"],"version":r.get("version"),"contracts":sorted(r["contracts"]),"model_execution":False})
        else:dump_json(catalog_summary())
        return 0
    if a.command=="validate-jobs":
        payload=load_json(Path(a.jobs));e=[f"{j.get('job_id')}: {x}" for j in payload.get("jobs",[]) for x in validate_job(j)]
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
