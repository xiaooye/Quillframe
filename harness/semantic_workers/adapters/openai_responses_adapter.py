#!/usr/bin/env python3
"""Optional OpenAI Responses API semantic adapter.

This path is separately metered API usage and is never required for local/peer
chat operation. stdin one semantic job; stdout one typed semantic result.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve(); WORKER_DIR=HERE.parent.parent
if str(WORKER_DIR) not in sys.path: sys.path.insert(0,str(WORKER_DIR))
from semantic_worker_router import validate_job, validate_result  # noqa: E402

SUPPORTED_KINDS={"eval_judge","artifact_audit"}
API_URL="https://api.openai.com/v1/responses"
JUDGMENT_SCHEMA={"type":"object","additionalProperties":False,"required":["verdict","result","codes","evidence","confidence"],"properties":{"verdict":{"type":["string","null"],"enum":["accept","reject",None]},"result":{"type":["string","null"],"enum":["pass","fail",None]},"codes":{"type":"array","items":{"type":"string"}},"evidence":{"type":"array","items":{"type":"string"}},"confidence":{"type":"number","minimum":0,"maximum":1}}}

def dump(v:Any)->None: print(json.dumps(v,ensure_ascii=False,separators=(",",":")))
def empty()->dict[str,Any]: return {"verdict":None,"result":None,"codes":[],"evidence":[],"confidence":0.0}

def bounded_prompt(job:dict[str,Any])->str:
    payload={k:job.get(k) for k in ("kind","subject_id","input_fingerprint","input","rubric","output_contract","permissions","provenance")}
    return "Independent semantic review. Judge only this blind packet. No private chain-of-thought. Return the schema result based on observable evidence. Never settle Canon, promote OS behavior, overwrite durable taste, grant permissions, or change story direction.\n\n"+json.dumps(payload,ensure_ascii=False,indent=2)

def request_body(job:dict[str,Any])->dict[str,Any]:
    model=os.getenv("NOVEL_OS_OPENAI_MODEL","gpt-5.1")
    effort=os.getenv("NOVEL_OS_OPENAI_REASONING_EFFORT","medium")
    return {"model":model,"store":False,"reasoning":{"effort":effort},"input":[{"role":"user","content":[{"type":"input_text","text":bounded_prompt(job)}]}],"text":{"format":{"type":"json_schema","name":"novel_os_semantic_judgment","strict":True,"schema":JUDGMENT_SCHEMA}}}

def typed(job:dict[str,Any],status:str,judgment:dict[str,Any]|None=None,run_ref:str|None=None,errors:list[str]|None=None)->dict[str,Any]:
    lineage=dict(job.get("execution") or {}); lineage["worker_session_id"]=lineage.get("worker_session_id") or "SES-OPENAI-"+uuid.uuid4().hex; lineage["attempt_id"]=lineage.get("attempt_id") or "ATT-"+uuid.uuid4().hex
    return {"job_id":job.get("job_id","unknown"),"subject_id":job.get("subject_id","unknown"),"kind":job.get("kind","eval_judge"),"input_fingerprint":job.get("input_fingerprint","sha256:"+"0"*64),"status":status,"worker":{"provider":"openai","model_or_reviewer":os.getenv("NOVEL_OS_OPENAI_MODEL","gpt-5.1"),"run_reference":run_ref},"judgment":judgment or empty(),"proposals":[],"errors":errors or [],"execution":lineage}

def extract_output(response:dict[str,Any])->dict[str,Any]:
    if isinstance(response.get("output_text"),str):
        obj=json.loads(response["output_text"]); return obj if isinstance(obj,dict) else (_ for _ in ()).throw(ValueError("output_text not object"))
    texts=[]
    for item in response.get("output",[]):
        if not isinstance(item,dict): continue
        for c in item.get("content",[]):
            if isinstance(c,dict) and isinstance(c.get("text"),str): texts.append(c["text"])
    if not texts: raise ValueError("Responses payload contained no output text")
    obj=json.loads(texts[-1]);
    if not isinstance(obj,dict): raise ValueError("judgment not object")
    return obj

def execute(job:dict[str,Any],timeout:int)->dict[str,Any]:
    errors=validate_job(job)
    if errors:return typed(job,"failed",errors=["invalid semantic job: "+"; ".join(errors)])
    if job["kind"] not in SUPPORTED_KINDS:return typed(job,"unsupported",errors=[f"unsupported kind={job['kind']}"])
    key=os.getenv("OPENAI_API_KEY")
    if not key:return typed(job,"failed",errors=["OPENAI_API_KEY is not configured"])
    body=json.dumps(request_body(job),ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(API_URL,data=body,method="POST",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: response=json.loads(r.read().decode("utf-8"))
        judgment=extract_output(response); result=typed(job,"completed",judgment=judgment,run_ref=response.get("id")); binding=validate_result(job,result)
        return result if not binding else typed(job,"failed",run_ref=response.get("id"),errors=["self-validation: "+"; ".join(binding)])
    except (urllib.error.URLError,urllib.error.HTTPError,TimeoutError,json.JSONDecodeError,ValueError) as exc:return typed(job,"failed",errors=[f"OpenAI Responses execution failed: {exc}"])

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--capabilities",action="store_true"); p.add_argument("--dry-run",action="store_true"); p.add_argument("--timeout",type=int,default=180); args=p.parse_args()
    if args.capabilities: dump({"provider":"openai","adapter_version":"0.2","available":bool(os.getenv("OPENAI_API_KEY")),"supported_kinds":sorted(SUPPORTED_KINDS),"store":False,"api_url":API_URL}); return 0
    try: job=json.load(sys.stdin)
    except Exception as exc: dump({"valid":False,"error":str(exc)}); return 1
    if args.dry_run:
        errors=validate_job(job); dump({"valid":not errors,"errors":errors,"request":request_body(job),"authorization_header_included":False}); return 0 if not errors else 1
    result=execute(job,args.timeout); dump(result); return 0 if result.get("status") in {"completed","unsupported"} else 1
if __name__=="__main__": raise SystemExit(main())
