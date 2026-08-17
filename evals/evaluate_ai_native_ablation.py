#!/usr/bin/env python3
"""Deterministic gate for AI-native paired semantic ablation evidence."""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path
from typing import Any
from evaluation_execution_identity import fingerprint, identity_payload, validate_identity

ROOT=Path(__file__).resolve().parents[1]
ABL=ROOT/"evals/ai_native_ablation_manifest.json"
EVAL=ROOT/"evals/eval_manifest.json"
PACKET_SCHEMA="novelforge_ai_native_ablation_observations_v1"
EVIDENCE_SCHEMA="novelforge_ai_native_ablation_evidence_v1"
FP=re.compile(r"^sha256:[0-9a-f]{64}$")
REL={"INCUMBENT_BETTER","CHALLENGER_BETTER","NO_MATERIAL_DIFFERENCE","INCONCLUSIVE"}
ORD={"INCUMBENT_FIRST","CHALLENGER_FIRST"}

def load(p:Path)->Any:return json.loads(p.read_text(encoding="utf-8"))
def dump(v:Any,p:Path|None=None)->None:
    s=json.dumps(v,ensure_ascii=False,indent=2)+"\n"
    p.write_text(s,encoding="utf-8") if p else print(s,end="")
def cfp(text:str)->str:return fingerprint({"candidate_text":text})
def cases()->dict[str,dict[str,Any]]:
    out={}
    for row in load(EVAL).get("cases",[]):
        if isinstance(row.get("file"),str):
            c=load(EVAL.parent/row["file"])
            if isinstance(c.get("id"),str):out[c["id"]]=c
    return out

def validate_manifest(m:dict[str,Any],cs:dict[str,dict[str,Any]])->list[str]:
    e=[]; p=m.get("decision_protocol",{})
    if m.get("schema")!="novelforge_ai_native_ablation_manifest_v1":e.append("manifest schema mismatch")
    if m.get("model_execution_required_for_semantic_outcomes") is not True:e.append("model execution must be required")
    if m.get("manager_self_judgment_allowed") is not False:e.append("manager self-judgment must be forbidden")
    if not isinstance(p.get("minimum_comparable_observations"),int) or p["minimum_comparable_observations"]<2:e.append("minimum observations must be >=2")
    if p.get("require_counterbalanced_presentation_order") is not True:e.append("counterbalanced order must be required")
    if set(p.get("semantic_relations",[]))!=REL:e.append("semantic relation enum mismatch")
    seen=set()
    for pair in m.get("pairs",[]):
        pid=pair.get("id")
        if not isinstance(pid,str) or not pid:e.append("pair id required");continue
        if pid in seen:e.append(f"duplicate pair id: {pid}")
        seen.add(pid)
        if pair.get("simpler_arm") not in {"incumbent","challenger"}:e.append(f"{pid}: invalid simpler_arm")
        a=cs.get(pair.get("incumbent_case")); b=cs.get(pair.get("challenger_case"))
        if not a or not b:e.append(f"{pid}: missing case");continue
        af=a.get("fixture",{}); bf=b.get("fixture",{}); ref=pair.get("same_candidate_ref")
        if af.get("candidate_ref")!=ref or bf.get("candidate_ref")!=ref:e.append(f"{pid}: candidate_ref mismatch")
        if not isinstance(af.get("candidate_text"),str) or af.get("candidate_text")!=bf.get("candidate_text"):e.append(f"{pid}: candidate_text mismatch")
    return e

def projection(i:dict[str,Any])->dict[str,Any]:
    ev=i.get("evaluation",{})
    return {"candidate":i.get("candidate"),"reviewer":i.get("reviewer"),
            "evaluation":{k:ev.get(k) for k in ("suite_version","domain","blind","capabilities_fingerprint","harness_fingerprint")},
            "environment":i.get("environment"),"resource_budget":i.get("resource_budget")}

def validate_obs(o:dict[str,Any],pair:dict[str,Any],cs:dict[str,dict[str,Any]])->list[str]:
    e=[]; pid=pair["id"]
    if o.get("pair_id")!=pid:e.append(f"{pid}: pair_id mismatch")
    if not isinstance(o.get("observation_id"),str) or not o["observation_id"]:e.append(f"{pid}: observation_id required")
    text=cs[pair["incumbent_case"]]["fixture"]["candidate_text"]
    if o.get("candidate_fingerprint")!=cfp(text):e.append(f"{pid}: candidate fingerprint mismatch")
    arm=o.get("condition_execution_identity")
    if not isinstance(arm,dict):e.append(f"{pid}: condition execution identity required"); armfp=None
    else:e += [f"{pid}: condition identity: {x}" for x in validate_identity(arm)]; armfp=arm.get("identity_fingerprint")
    for side in ("incumbent","challenger"):
        rf=o.get(f"{side}_result_fingerprint"); ef=o.get(f"{side}_execution_identity_fingerprint")
        if not isinstance(rf,str) or not FP.fullmatch(rf):e.append(f"{pid}: {side} result fingerprint required")
        if ef!=armfp:e.append(f"{pid}: {side} execution identity mismatch")
    review=o.get("pair_review_execution_identity")
    if not isinstance(review,dict):e.append(f"{pid}: pair review execution identity required")
    else:e += [f"{pid}: pair review identity: {x}" for x in validate_identity(review)]
    if o.get("presentation_order") not in ORD:e.append(f"{pid}: invalid presentation_order")
    if o.get("semantic_relation") not in REL:e.append(f"{pid}: invalid semantic_relation")
    if not isinstance(o.get("simpler_arm_safety_regression"),bool):e.append(f"{pid}: simpler_arm_safety_regression must be boolean")
    if not isinstance(o.get("semantic_evidence"),str) or not o["semantic_evidence"].strip():e.append(f"{pid}: semantic_evidence required")
    if o.get("semantic_source")!="independent_model":e.append(f"{pid}: semantic_source must be independent_model")
    return e

def decide(pair:dict[str,Any],obs:list[dict[str,Any]],protocol:dict[str,Any])->dict[str,Any]:
    need=protocol["minimum_comparable_observations"]; simpler=pair["simpler_arm"]
    base={"recommendation":"NO_CHANGE","simpler_arm_noninferior":None}
    if not obs:return {**base,"status":"PENDING_MODEL","reason":"no real semantic observations supplied"}
    arm=[projection(x["condition_execution_identity"]) for x in obs]
    rev=[projection(x["pair_review_execution_identity"]) for x in obs]
    if any(x!=arm[0] for x in arm[1:]) or any(x!=rev[0] for x in rev[1:]):
        return {**base,"status":"PENDING_MODEL","reason":"execution conditions are not comparable"}
    if len(obs)<need:return {**base,"status":"PENDING_MODEL","reason":f"need at least {need} comparable observations"}
    if protocol["require_counterbalanced_presentation_order"] and {x["presentation_order"] for x in obs}!=ORD:
        return {**base,"status":"PENDING_MODEL","reason":"presentation order is not counterbalanced"}
    if any(x["simpler_arm_safety_regression"] for x in obs):
        return {"status":"KEEP","recommendation":"KEEP_CURRENT","reason":"safety regression veto","simpler_arm_noninferior":False}
    rel=[x["semantic_relation"] for x in obs]; counts=dict(Counter(rel))
    if "INCONCLUSIVE" in counts:return {**base,"status":"INCONCLUSIVE","reason":"reviewer reported INCONCLUSIVE","relations":counts}
    good={"NO_MATERIAL_DIFFERENCE","INCUMBENT_BETTER" if simpler=="incumbent" else "CHALLENGER_BETTER"}
    bad="CHALLENGER_BETTER" if simpler=="incumbent" else "INCUMBENT_BETTER"
    has_good=any(x in good for x in rel); has_bad=bad in rel
    if has_good and has_bad:return {**base,"status":"INCONCLUSIVE","reason":"stochastic judgments conflict","relations":counts}
    if has_bad:return {"status":"KEEP","recommendation":"KEEP_CURRENT","reason":"simpler arm is semantically worse","relations":counts,"simpler_arm_noninferior":False}
    if all(x in good for x in rel):
        return {"status":"SIMPLIFY","recommendation":f"SIMPLIFY_TO_{simpler.upper()}","reason":"externally judged non-inferior or better with no safety veto","relations":counts,"simpler_arm_noninferior":True}
    return {**base,"status":"INCONCLUSIVE","reason":"evidence does not satisfy decision protocol","relations":counts}

def evaluate(packet:dict[str,Any],m:dict[str,Any],cs:dict[str,dict[str,Any]])->dict[str,Any]:
    if packet.get("schema")!=PACKET_SCHEMA:raise ValueError("packet schema mismatch")
    me=validate_manifest(m,cs)
    if me:raise ValueError("; ".join(me))
    ps={x["id"]:x for x in m["pairs"]}; grouped={k:[] for k in ps}; seen=set()
    for o in packet.get("observations",[]):
        if not isinstance(o,dict) or o.get("pair_id") not in ps:raise ValueError("unknown/malformed observation")
        oid=o.get("observation_id")
        if oid in seen:raise ValueError(f"duplicate observation_id: {oid}")
        seen.add(oid); oe=validate_obs(o,ps[o["pair_id"]],cs)
        if oe:raise ValueError("; ".join(oe))
        grouped[o["pair_id"]].append(o)
    rows=[]
    for pid,pair in ps.items():
        o=grouped[pid]; d=decide(pair,o,m["decision_protocol"]); text=cs[pair["incumbent_case"]]["fixture"]["candidate_text"]
        rows.append({"pair_id":pid,"incumbent_case":pair["incumbent_case"],"challenger_case":pair["challenger_case"],
                     "simpler_arm":pair["simpler_arm"],"candidate_ref":pair["same_candidate_ref"],"candidate_fingerprint":cfp(text),
                     "comparability":{"observation_count":len(o),"minimum_required":m["decision_protocol"]["minimum_comparable_observations"],
                                      "counterbalanced_order":bool(o) and {x["presentation_order"] for x in o}==ORD},
                     "semantic_evidence":{"complete":d["status"] not in {"PENDING_MODEL"},"source":"independent_model" if o else None},
                     "provenance":{"observation_fingerprints":[fingerprint(x) for x in o],
                                   "condition_execution_identities":[x["condition_execution_identity"]["identity_fingerprint"] for x in o],
                                   "pair_review_execution_identities":[x["pair_review_execution_identity"]["identity_fingerprint"] for x in o],
                                   "incumbent_result_fingerprints":[x["incumbent_result_fingerprint"] for x in o],
                                   "challenger_result_fingerprints":[x["challenger_result_fingerprint"] for x in o]},
                     "decision":d})
    out={"schema":EVIDENCE_SCHEMA,"manifest_fingerprint":fingerprint(m),"packet_fingerprint":fingerprint(packet),"pairs":rows}
    out["evidence_fingerprint"]=fingerprint(out); return out

def prepare(m:dict[str,Any],cs:dict[str,dict[str,Any]])->dict[str,Any]:
    e=validate_manifest(m,cs)
    if e:raise ValueError("; ".join(e))
    return {"schema":PACKET_SCHEMA,"required_observations_per_pair":m["decision_protocol"]["minimum_comparable_observations"],
            "semantic_source":"independent_model","manager_self_judgment_allowed":False,"observations":[]}

def test_identity(model:str="test-model",run:str="1")->dict[str,Any]:
    i={"schema":"novelforge_evaluation_execution_identity_v1","candidate":{"commit":"a"*40,"framework_version":"9.9.9"},
       "reviewer":{"provider":"openai","model_id":model,"model_revision_binding":"provider_managed_unpinned","reasoning_effort":"medium","sampling":{"binding":"provider_defaults_unpinned"}},
       "evaluation":{"suite_version":"test","domain":"reader","blind":True,"queue_fingerprint":"sha256:"+"1"*64,"jobs_fingerprint":"sha256:"+"2"*64,
                     "capabilities_fingerprint":"sha256:"+"3"*64,"harness_fingerprint":"sha256:"+"4"*64},
       "environment":{"runner_os":"Linux","runner_arch":"X64","python_version":"3.11"},"resource_budget":{"binding":"same-test-budget"},
       "provenance":{"github_run_id":run}}
    i["identity_fingerprint"]=fingerprint(i); return i

def self_test()->int:
    m=load(ABL); cs=cases(); ok_manifest=not validate_manifest(m,cs)
    pending=all(x["decision"]["status"]=="PENDING_MODEL" for x in evaluate(prepare(m,cs),m,cs)["pairs"])
    pair=m["pairs"][0]; cand=cfp(cs[pair["incumbent_case"]]["fixture"]["candidate_text"]); obs=[]
    for n,order in enumerate(("INCUMBENT_FIRST","CHALLENGER_FIRST","INCUMBENT_FIRST"),1):
        arm=test_identity(run=str(n)); rev=test_identity("pair-reviewer",str(n))
        obs.append({"pair_id":pair["id"],"observation_id":f"O{n}","candidate_fingerprint":cand,"condition_execution_identity":arm,
                    "incumbent_result_fingerprint":"sha256:"+"5"*64,"challenger_result_fingerprint":"sha256:"+"6"*64,
                    "incumbent_execution_identity_fingerprint":arm["identity_fingerprint"],"challenger_execution_identity_fingerprint":arm["identity_fingerprint"],
                    "pair_review_execution_identity":rev,"presentation_order":order,"semantic_source":"independent_model",
                    "semantic_relation":"NO_MATERIAL_DIFFERENCE","simpler_arm_safety_regression":False,"semantic_evidence":"synthetic protocol evidence"})
    packet={"schema":PACKET_SCHEMA,"observations":obs}
    simp=next(x for x in evaluate(packet,m,cs)["pairs"] if x["pair_id"]==pair["id"])["decision"]["status"]=="SIMPLIFY"
    safe=json.loads(json.dumps(packet)); safe["observations"][0]["simpler_arm_safety_regression"]=True
    veto=next(x for x in evaluate(safe,m,cs)["pairs"] if x["pair_id"]==pair["id"])["decision"]["status"]=="KEEP"
    bad=json.loads(json.dumps(packet)); bad["observations"][0]["candidate_fingerprint"]="sha256:"+"0"*64
    try:evaluate(bad,m,cs); cand_reject=False
    except ValueError:cand_reject=True
    bad=json.loads(json.dumps(packet)); bad["observations"][0]["challenger_execution_identity_fingerprint"]="sha256:"+"0"*64
    try:evaluate(bad,m,cs); id_reject=False
    except ValueError:id_reject=True
    drift=json.loads(json.dumps(packet)); i=drift["observations"][1]["condition_execution_identity"]; i["reviewer"]["model_id"]="drift"; i["identity_fingerprint"]=fingerprint(identity_payload(i))
    drift["observations"][1]["incumbent_execution_identity_fingerprint"]=i["identity_fingerprint"]; drift["observations"][1]["challenger_execution_identity_fingerprint"]=i["identity_fingerprint"]
    drift_pending=next(x for x in evaluate(drift,m,cs)["pairs"] if x["pair_id"]==pair["id"])["decision"]["status"]=="PENDING_MODEL"
    malformed=json.loads(json.dumps(m)); malformed["pairs"][0]["simpler_arm"]="neither"; malformed_reject=bool(validate_manifest(malformed,cs))
    deterministic=evaluate(packet,m,cs)==evaluate(packet,m,cs)
    ok=all((ok_manifest,pending,simp,veto,cand_reject,id_reject,drift_pending,malformed_reject,deterministic))
    print(json.dumps({"paired_ablation_contract":"PASS" if ok else "FAIL","manifest_valid":ok_manifest,"missing_semantic_judgment_pending":pending,
                      "safety_regression_veto":veto,"mismatched_candidate_rejected":cand_reject,"mismatched_execution_identity_rejected":id_reject,
                      "configuration_drift_pending":drift_pending,"malformed_pair_rejected":malformed_reject,"deterministic_output":deterministic,
                      "semantic_superiority_inferred_by_python":False,"model_execution":False},indent=2))
    return 0 if ok else 1

def main()->int:
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True); s.add_parser("self-test")
    q=s.add_parser("prepare");q.add_argument("--output");q=s.add_parser("evaluate");q.add_argument("--observations",required=True);q.add_argument("--output")
    a=p.parse_args(); m=load(ABL); cs=cases()
    if a.cmd=="self-test":return self_test()
    if a.cmd=="prepare":dump(prepare(m,cs),Path(a.output) if a.output else None);return 0
    dump(evaluate(load(Path(a.observations)),m,cs),Path(a.output) if a.output else None);return 0
if __name__=="__main__":raise SystemExit(main())
