#!/usr/bin/env python3
"""Build/validate bounded peer-chat semantic review packets.

This tool never performs the review itself. It binds a genuinely separate chat
session result to a semantic job through fingerprint + relay nonce.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve();
if str(HERE.parent) not in sys.path: sys.path.insert(0,str(HERE.parent))
from semantic_worker_router import validate_job,validate_result  # noqa: E402

PACKET_SCHEMA="novel_os_peer_review_packet_v1"

def load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding="utf-8"));
    if not isinstance(v,dict): raise ValueError("JSON must be object")
    return v

def dump(v:Any,path:Path|None=None)->None:
    s=json.dumps(v,ensure_ascii=False,indent=2)+"\n"
    if path:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s,encoding="utf-8")
    else:print(s,end="")

def build(job:dict[str,Any])->dict[str,Any]:
    errors=validate_job(job)
    if errors: raise ValueError("invalid job: "+"; ".join(errors))
    nonce=secrets.token_urlsafe(24)
    bounded={k:job.get(k) for k in ("job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance")}
    reviewer_instruction=(
        "You are a genuinely separate independent semantic reviewer. Judge only the blind job below. "
        "Do not ask for or inspect the writer conversation/project files; do not search for expected labels; do not provide private chain-of-thought. "
        "Return ONLY one JSON semantic result with the exact job_id/subject_id/kind/input_fingerprint, status=completed, worker provider=chatgpt_peer_chat (or truthful peer-chat provider), a short evidence-based judgment, empty proposals/errors, and execution.run_reference exactly equal to the relay nonce. "
        "You have no Canon/OS/taste/write authority."
    )
    return {"schema":PACKET_SCHEMA,"relay_nonce":nonce,"input_fingerprint":job["input_fingerprint"],"job":bounded,"reviewer_instruction":reviewer_instruction,"return_binding":{"run_reference":nonce,"fresh_conversation_required":True,"same_project_writer_chat_forbidden":True}}

def validate_packet(packet:dict[str,Any])->list[str]:
    e=[]
    if packet.get("schema")!=PACKET_SCHEMA:e.append("invalid packet schema")
    if not isinstance(packet.get("relay_nonce"),str) or not packet["relay_nonce"]:e.append("relay_nonce required")
    job=packet.get("job")
    if not isinstance(job,dict):e.append("job required");return e
    # Recreate optional execution field only if absent; fingerprint semantics ignore it.
    e.extend(validate_job(job))
    if packet.get("input_fingerprint")!=job.get("input_fingerprint"):e.append("packet/job fingerprint mismatch")
    return e

def validate_peer_result(packet:dict[str,Any],result:dict[str,Any])->list[str]:
    e=validate_packet(packet)
    if e:return e
    job=packet["job"]
    e.extend(validate_result(job,result))
    worker=result.get("worker") or {}
    if worker.get("provider") not in {"chatgpt_peer_chat","claude_peer_chat","gemini_peer_chat","human","other_peer_chat"}:e.append("worker.provider is not a declared peer-chat/human provider")
    run_ref=worker.get("run_reference")
    execution=result.get("execution") or {}
    if run_ref!=packet["relay_nonce"] and execution.get("run_reference")!=packet["relay_nonce"]:e.append("relay nonce/run_reference mismatch")
    return e

def self_test()->int:
    from semantic_worker_router import fingerprint_for
    job={"job_id":"SEM-SELF","kind":"eval_judge","subject_id":"CASE","created_at":"now","input_fingerprint":"","input":{"text":"x"},"rubric":["judge"],"output_contract":{},"permissions":{"canon_write":False,"os_behavior_write":False,"durable_user_taste_write":False,"allowed_result_scope":"observation"},"provenance":{"source":"self"}}
    job["input_fingerprint"]=fingerprint_for(job);packet=build(job)
    result={"job_id":job["job_id"],"subject_id":job["subject_id"],"kind":job["kind"],"input_fingerprint":job["input_fingerprint"],"status":"completed","worker":{"provider":"chatgpt_peer_chat","model_or_reviewer":"independent peer","run_reference":packet["relay_nonce"]},"judgment":{"verdict":"accept","result":None,"codes":[],"evidence":["fixture"],"confidence":0.8},"proposals":[],"errors":[]}
    ok=not validate_packet(packet) and not validate_peer_result(packet,result)
    dump({"peer_chat_relay_contract":"PASS" if ok else "FAIL","fresh_conversation_required":True,"fingerprint_binding":True,"relay_nonce_binding":True});return 0 if ok else 1

def main()->int:
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build");b.add_argument("--job",required=True);b.add_argument("--output")
    v=sub.add_parser("validate-result");v.add_argument("--packet",required=True);v.add_argument("--result",required=True)
    sub.add_parser("self-test");args=p.parse_args()
    if args.cmd=="self-test":return self_test()
    if args.cmd=="build":dump(build(load(Path(args.job))),Path(args.output) if args.output else None);return 0
    errors=validate_peer_result(load(Path(args.packet)),load(Path(args.result)));dump({"valid":not errors,"errors":errors});return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
