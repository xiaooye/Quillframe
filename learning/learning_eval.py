#!/usr/bin/env python3
"""Deterministic learning-input boundary for Quillframe semantic contracts.

This module converts already-bounded verified corpus/eval artifacts into semantic
jobs, rejects raw or oversized evidence, protects blind packets, and delegates
semantic job construction to the catalog-resolved generic kernel. It executes
no model and owns no literary judgment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harness.semantic_workers.semantic_worker_router import find_forbidden_keys, find_named_keys, make_contract_job, validate_job

ANALYSIS_QUEUE_SCHEMA = "quillframe_learning_analysis_jobs_v1"
EVAL_QUEUE_SCHEMA = "quillframe_learning_eval_jobs_v1"
FORBIDDEN_RAW = {"full_text", "raw_text", "source_text"}
MAX_EXCERPT_CHARS = 4000

def load(path: str | Path) -> dict[str, Any]:
    value=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("JSON root must be object")
    return value

def dump(value: Any, path: str | Path | None=None) -> None:
    text=json.dumps(value,ensure_ascii=False,indent=2)+"\n"
    if path: Path(path).write_text(text,encoding="utf-8")
    else: print(text,end="")

def bounded_evidence(record: dict[str, Any]) -> dict[str, Any]:
    evidence=record.get("evidence",{})
    if not isinstance(evidence,dict): raise ValueError("verified evidence must be object")
    leakage=find_named_keys(evidence,FORBIDDEN_RAW)
    if leakage: raise ValueError("verified evidence contains forbidden raw source fields: "+", ".join(leakage))
    excerpt=evidence.get("excerpt")
    if excerpt is not None:
        if not isinstance(excerpt,str): raise ValueError("evidence.excerpt must be string when present")
        if len(excerpt)>MAX_EXCERPT_CHARS: raise ValueError(f"evidence.excerpt exceeds {MAX_EXCERPT_CHARS} characters")
    return dict(evidence)

def build_analysis_jobs(verified: dict[str, Any], *, research_question: str, hypothesis_id: str | None=None, source_session_id: str | None=None) -> dict[str, Any]:
    if verified.get("schema")!="quillframe_verified_corpus_discovery_v1": raise ValueError("verified discovery schema required")
    jobs=[]
    for record in verified.get("verified",[]):
        if not isinstance(record,dict) or not record.get("verified"): continue
        subject=str(record.get("corpus_id") or record.get("evidence_fingerprint"))
        payload={"research_question":research_question,"hypothesis_id":hypothesis_id,"source":{"corpus_id":record.get("corpus_id"),"source_title":record.get("source_title"),"source_type":record.get("source_type"),"source_locator":record.get("source_locator"),"work_id":record.get("work_id"),"channel":record.get("channel"),"tool_or_provider":record.get("tool_or_provider"),"rights_class":record.get("rights_class"),"storage_intent":record.get("storage_intent"),"evidence_fingerprint":record.get("evidence_fingerprint"),"metadata":record.get("metadata",{}),"bounded_evidence":bounded_evidence(record)}}
        job=make_contract_job("learning.mechanism_analyze",subject,payload,source_session_id=source_session_id); job["provenance"]["evidence_fingerprint"]=record.get("evidence_fingerprint"); jobs.append(job)
    return {"schema":ANALYSIS_QUEUE_SCHEMA,"blind":True,"research_question":research_question,"hypothesis_id":hypothesis_id,"jobs":jobs}

def build_eval_jobs(request: dict[str, Any], *, source_session_id: str | None=None) -> dict[str, Any]:
    if request.get("schema")!="quillframe_learning_eval_request_v1": raise ValueError("learning eval request schema required")
    leakage=find_forbidden_keys(request)
    if leakage: raise ValueError("learning eval request leaks answer-key fields: "+", ".join(leakage))
    jobs=[]
    for case in request.get("cases",[]):
        if not isinstance(case,dict) or not case.get("id"): raise ValueError("eval case requires id")
        criteria=case.get("rubric",[])
        if not isinstance(criteria,list) or not criteria or not all(isinstance(x,str) and x.strip() for x in criteria): raise ValueError(f"eval case {case['id']} requires evaluation criteria")
        payload={"learning_scope":request.get("scope"),"hypothesis_id":request.get("hypothesis_id"),"mechanism":request.get("mechanism"),"profile_boundary":request.get("profile_boundary",{}),"fixture":case.get("fixture",{}),"evaluation_purpose":case.get("purpose"),"evaluation_criteria":criteria}
        job=make_contract_job("learning.evaluate",str(case["id"]),payload,source_session_id=source_session_id); job["provenance"]["hypothesis_id"]=request.get("hypothesis_id"); jobs.append(job)
    return {"schema":EVAL_QUEUE_SCHEMA,"blind":True,"scope":request.get("scope"),"hypothesis_id":request.get("hypothesis_id"),"jobs":jobs}

def self_test() -> dict[str, Any]:
    verified={"schema":"quillframe_verified_corpus_discovery_v1","verified":[{"verified":True,"corpus_id":"CORP-T","source_title":"Fixture","source_type":"book","source_locator":"fixture://work","work_id":"WORK-T","channel":"user_files","tool_or_provider":"fixture","rights_class":"analysis_only","storage_intent":"derived_only","evidence_fingerprint":"sha256:"+"1"*64,"metadata":{},"evidence":{"mechanism_hint":"pressure changes options","excerpt":"bounded fixture evidence"}}]}
    analysis=build_analysis_jobs(verified,research_question="What creates pace?",hypothesis_id="PH-T"); aj=analysis["jobs"][0]
    analysis_contract=aj["input"].get("model_contract_id")=="learning.mechanism_analyze"; catalog_resolved=aj["provenance"].get("pack_id")=="learning"; fingerprint_valid=not validate_job(aj)
    raw_guard=False
    bad_raw=json.loads(json.dumps(verified)); bad_raw["verified"][0]["evidence"]["raw_text"]="must reject"
    try: build_analysis_jobs(bad_raw,research_question="What creates pace?")
    except ValueError: raw_guard=True
    oversize_guard=False
    bad_long=json.loads(json.dumps(verified)); bad_long["verified"][0]["evidence"]["excerpt"]="x"*(MAX_EXCERPT_CHARS+1)
    try: build_analysis_jobs(bad_long,research_question="What creates pace?")
    except ValueError: oversize_guard=True
    req={"schema":"quillframe_learning_eval_request_v1","scope":"user_taste","hypothesis_id":"PH-T","mechanism":"pace comes from state change","profile_boundary":{"exceptions":["deliberate shock fragment"]},"cases":[{"id":"LE-1","purpose":"distinguish functional pace from fragmentation","fixture":{"text":"fixture"},"rubric":["judge functional pacing mechanism"]}]}
    evaluation=build_eval_jobs(req); ej=evaluation["jobs"][0]; eval_contract=ej["input"].get("model_contract_id")=="learning.evaluate" and ej["provenance"].get("pack_id")=="learning"
    leak_guard=False
    try:
        bad=dict(req); bad["expected"]={"result":"pass"}; build_eval_jobs(bad)
    except ValueError: leak_guard=True
    ok=analysis_contract and catalog_resolved and eval_contract and fingerprint_valid and raw_guard and oversize_guard and leak_guard
    return {"learning_eval_contract":"PASS" if ok else "FAIL","semantic_intelligence_in_model_contracts":analysis_contract and eval_contract,"catalog_resolved_learning_pack":catalog_resolved,"analysis_jobs_fingerprint_bound":fingerprint_valid,"raw_source_text_fail_closed":raw_guard,"oversized_excerpt_fail_closed":oversize_guard,"answer_key_leakage_guard":leak_guard,"silent_semantic_input_rewrite":False,"model_execution":False,"write_authority":False}

def main() -> int:
    p=argparse.ArgumentParser(description="Quillframe deterministic learning semantic-input boundary"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("analysis-jobs"); a.add_argument("--verified",required=True); a.add_argument("--research-question",required=True); a.add_argument("--hypothesis-id"); a.add_argument("--source-session-id"); a.add_argument("--output")
    e=sub.add_parser("eval-jobs"); e.add_argument("--request",required=True); e.add_argument("--source-session-id"); e.add_argument("--output")
    sub.add_parser("self-test"); args=p.parse_args()
    if args.cmd=="self-test": result=self_test(); dump(result); return 0 if result["learning_eval_contract"]=="PASS" else 1
    if args.cmd=="analysis-jobs": result=build_analysis_jobs(load(args.verified),research_question=args.research_question,hypothesis_id=args.hypothesis_id,source_session_id=args.source_session_id)
    else: result=build_eval_jobs(load(args.request),source_session_id=args.source_session_id)
    dump(result,args.output); return 0

if __name__=="__main__": raise SystemExit(main())
