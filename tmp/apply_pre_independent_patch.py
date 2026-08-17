#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def replace_once(path:str, old:str, new:str)->None:
    p=ROOT/path
    text=p.read_text(encoding='utf-8')
    count=text.count(old)
    if count!=1:
        raise SystemExit(f'{path}: expected exactly one replacement, got {count}: {old[:120]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

def dump_json(path:str, data:dict)->None:
    (ROOT/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')

# 1) Semantic self-audit dimensions + known-regression recurrence instruction.
qpath=ROOT/'harness/semantic_workers/contracts/quality.json'
q=json.loads(qpath.read_text(encoding='utf-8'))
audit=q['contracts']['quality.candidate_self_audit']
if not any('known regression' in x.lower() for x in audit['rubric']):
    audit['rubric'].insert(-1,
        "When supplied regression_evidence identifies an already-known mechanism, explicitly check whether the current candidate repeats that mechanism. A known recurrence that remains material is a quality-loop escape risk, not a new preference discovery; judge applicability semantically and do not ban literal phrases.")
out=audit['output_contract']
if 'dimensions' not in out['required']:
    out['required'].insert(3,'dimensions')
out['properties']['dimensions']={
    'type':'object',
    'required':['surface','regression','character_or_ownership','natural_realization','cluster'],
    'properties':{
        'surface':{'enum':['pass','fail','insufficient_evidence','not_applicable']},
        'regression':{'enum':['pass','fail','insufficient_evidence','not_applicable']},
        'character_or_ownership':{'enum':['pass','fail','insufficient_evidence','not_applicable']},
        'natural_realization':{'enum':['pass','fail','insufficient_evidence','not_applicable']},
        'cluster':{'enum':['pass','fail','insufficient_evidence','not_applicable']},
    },
    'additionalProperties':False,
}
dump_json('harness/semantic_workers/contracts/quality.json',q)

# 2) Qualification runtime: bind dimension statuses and expose requested fields.
path='quality/candidate_qualification.py'
replace_once(path,
'''    blockers: list[dict[str, Any]] = []\n    if gate == "self_audit":\n        findings = judgment.get("findings", [])\n''',
'''    blockers: list[dict[str, Any]] = []\n    dimensions: dict[str, str] | None = None\n    if gate == "self_audit":\n        raw_dimensions = judgment.get("dimensions")\n        if not isinstance(raw_dimensions, dict):\n            raise ValueError("self_audit dimensions must be object")\n        dimension_keys = {"surface", "regression", "character_or_ownership", "natural_realization", "cluster"}\n        if set(raw_dimensions) != dimension_keys:\n            raise ValueError("self_audit dimensions must cover exact required dimension set")\n        allowed_dimension_statuses = {"pass", "fail", "insufficient_evidence", "not_applicable"}\n        if any(value not in allowed_dimension_statuses for value in raw_dimensions.values()):\n            raise ValueError("self_audit dimension status invalid")\n        dimensions = {key: str(raw_dimensions[key]) for key in sorted(raw_dimensions)}\n        failed_dimensions = [key for key, value in dimensions.items() if value == "fail"]\n        insufficient_dimensions = [key for key, value in dimensions.items() if value == "insufficient_evidence"]\n        if derived == "pass" and (failed_dimensions or insufficient_dimensions):\n            raise ValueError("self_audit pass contradicts failed/insufficient dimension")\n        if derived == "fail" and not failed_dimensions:\n            raise ValueError("self_audit fail requires at least one failed dimension")\n        if derived == "pending" and not insufficient_dimensions:\n            raise ValueError("self_audit insufficient_evidence requires at least one insufficient dimension")\n        findings = judgment.get("findings", [])\n''')
replace_once(path,
'''        "blocking_findings": blockers,\n    }\n''',
'''        "blocking_findings": blockers,\n        "dimensions": dimensions,\n    }\n''')
replace_once(path,
'''        "blocking_findings": blockers,\n        "qualified_for_independent": status == "qualified_for_independent",\n''',
'''        "blocking_findings": blockers,\n        "surface_audit_status": (self_audit.get("dimensions") or {}).get("surface", self_audit["status"]),\n        "regression_audit_status": (self_audit.get("dimensions") or {}).get("regression", self_audit["status"]),\n        "character_or_ownership_status": (self_audit.get("dimensions") or {}).get("character_or_ownership", self_audit["status"]),\n        "natural_realization_status": (self_audit.get("dimensions") or {}).get("natural_realization", self_audit["status"]),\n        "cluster_audit_status": (self_audit.get("dimensions") or {}).get("cluster", self_audit["status"]),\n        "reader_engagement_status": reader["status"],\n        "continuity_status": continuity["status"],\n        "qualified_for_independent": status == "qualified_for_independent",\n''')
replace_once(path,
'''    if receipt.get("independent") is not False:\n        errors.append("qualification must be independent=false")\n''',
'''    for field in ("surface_audit_status", "regression_audit_status", "character_or_ownership_status", "natural_realization_status", "cluster_audit_status", "reader_engagement_status", "continuity_status"):\n        if receipt.get(field) not in {"pass", "fail", "pending", "insufficient_evidence", "not_applicable"}:\n            errors.append(f"qualification {field} invalid")\n    if receipt.get("independent") is not False:\n        errors.append("qualification must be independent=false")\n''')
replace_once(path,
'''        "report": "No material blocking realization defect remains.",\n        "findings": [],\n''',
'''        "report": "No material blocking realization defect remains.",\n        "dimensions": {"surface":"pass","regression":"pass","character_or_ownership":"pass","natural_realization":"pass","cluster":"pass"},\n        "findings": [],\n''')
replace_once(path,
'''        "report": "A clustered over-authored dialogue rhythm remains.",\n        "findings": [{\n''',
'''        "report": "A clustered over-authored dialogue rhythm remains.",\n        "dimensions": {"surface":"fail","regression":"fail","character_or_ownership":"fail","natural_realization":"fail","cluster":"fail"},\n        "findings": [{\n''')
replace_once(path,
'''            "report": "Purpose is valid but realization is punchline-first and stacked.",\n            "evidence_refs": ["candidate:block-1"],\n''',
'''            "report": "Purpose is valid but realization is punchline-first and stacked.",\n            "function_assessment": "pass",\n            "ownership_assessment": "fail",\n            "natural_realization_assessment": "fail",\n            "evidence_refs": ["candidate:block-1"],\n''')

# 3) Qualification JSON schema requested explicit statuses.
schema_path=ROOT/'quality/candidate_qualification.schema.json'
schema=json.loads(schema_path.read_text(encoding='utf-8'))
new_fields=['surface_audit_status','regression_audit_status','character_or_ownership_status','natural_realization_status','cluster_audit_status','reader_engagement_status','continuity_status']
for field in new_fields:
    if field not in schema['required']:
        schema['required'].insert(schema['required'].index('qualified_for_independent'),field)
    schema['properties'][field]={'enum':['pass','fail','pending','insufficient_evidence','not_applicable']}
dump_json('quality/candidate_qualification.schema.json',schema)

# 4) Semantic router: runtime-only qualification proof and a distinct dispatch validation boundary.
path='harness/semantic_workers/semantic_worker_router.py'
replace_once(path,
'''def semantic_payload(job:dict[str,Any])->dict[str,Any]:return {k:job.get(k,{} if k in {"input","output_contract"} else []) for k in ("kind","subject_id","input","rubric","output_contract")}\ndef fingerprint_for(job:dict[str,Any])->str:return "sha256:"+hashlib.sha256(canonical(semantic_payload(job))).hexdigest()\ndef validate_job(job:dict[str,Any])->list[str]:\n''',
'''def semantic_payload(job:dict[str,Any])->dict[str,Any]:return {k:job.get(k,{} if k in {"input","output_contract"} else []) for k in ("kind","subject_id","input","rubric","output_contract")}\ndef fingerprint_for(job:dict[str,Any])->str:return "sha256:"+hashlib.sha256(canonical(semantic_payload(job))).hexdigest()\ndef worker_job_view(job:dict[str,Any])->dict[str,Any]:\n    """Return only reviewer-visible semantic job fields; runtime dispatch proof stays private."""\n    return {k:json.loads(json.dumps(job[k])) for k in ("job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance","execution") if k in job}\ndef _production_review_qualification_errors(job:dict[str,Any])->list[str]:\n    input_obj=job.get("input")\n    if not isinstance(input_obj,dict) or input_obj.get("model_contract_id")!="quality.production_review":return []\n    proof=job.get("dispatch_proof")\n    if not isinstance(proof,dict):return ["quality.production_review dispatch requires pre-independent qualification receipt"]\n    payload=input_obj.get("payload")\n    if not isinstance(payload,dict):return ["quality.production_review payload required"]\n    quality_root=HERE.parents[1]/"quality"\n    if str(quality_root) not in sys.path:sys.path.insert(0,str(quality_root))\n    from candidate_qualification import validate_qualification_receipt\n    return ["production review qualification: "+x for x in validate_qualification_receipt(proof,candidate_fingerprint=payload.get("candidate_fingerprint"),subject_id=job.get("subject_id"),require_qualified=True)]\ndef validate_dispatchable_job(job:dict[str,Any])->list[str]:\n    return validate_job(job)+_production_review_qualification_errors(job)\ndef validate_job(job:dict[str,Any])->list[str]:\n''')
replace_once(path,
'''def make_contract_job(cid:str,subject_id:str,input_payload:dict[str,Any],*,registry_path:Path|None=None,job_id:str|None=None,source_session_id:str|None=None,handoff_id:str|None=None)->dict[str,Any]:\n''',
'''def make_contract_job(cid:str,subject_id:str,input_payload:dict[str,Any],*,registry_path:Path|None=None,job_id:str|None=None,source_session_id:str|None=None,handoff_id:str|None=None,qualification_receipt:dict[str,Any]|None=None)->dict[str,Any]:\n''')
replace_once(path,
'''    job["input_fingerprint"]=fingerprint_for(job);e=validate_job(job)\n    if e:raise ValueError("prepared contract job invalid: "+"; ".join(e))\n''',
'''    job["input_fingerprint"]=fingerprint_for(job)\n    if cid=="quality.production_review":\n        if qualification_receipt is None:raise ValueError("quality.production_review requires pre-independent qualification receipt")\n        job["dispatch_proof"]=json.loads(json.dumps(qualification_receipt))\n        e=validate_dispatchable_job(job)\n    else:e=validate_job(job)\n    if e:raise ValueError("prepared contract job invalid: "+"; ".join(e))\n''')
replace_once(path,
'''    x=s.add_parser("prepare-contract");x.add_argument("--contract",required=True);x.add_argument("--subject-id",required=True);x.add_argument("--input",required=True);x.add_argument("--job-id");x.add_argument("--registry");x.add_argument("--source-session-id");x.add_argument("--handoff-id");x.add_argument("--output")\n''',
'''    x=s.add_parser("prepare-contract");x.add_argument("--contract",required=True);x.add_argument("--subject-id",required=True);x.add_argument("--input",required=True);x.add_argument("--job-id");x.add_argument("--registry");x.add_argument("--source-session-id");x.add_argument("--handoff-id");x.add_argument("--qualification-receipt");x.add_argument("--output")\n''')
replace_once(path,
'''    x=s.add_parser("validate-jobs");x.add_argument("--jobs",required=True)\n''',
'''    x=s.add_parser("validate-jobs");x.add_argument("--jobs",required=True)\n    x=s.add_parser("validate-dispatchable-jobs");x.add_argument("--jobs",required=True)\n''')
replace_once(path,
'''    if a.command=="prepare-contract":dump_json(make_contract_job(a.contract,a.subject_id,load_json(Path(a.input)),registry_path=Path(a.registry).resolve() if a.registry else None,job_id=a.job_id,source_session_id=a.source_session_id,handoff_id=a.handoff_id),Path(a.output) if a.output else None);return 0\n''',
'''    if a.command=="prepare-contract":dump_json(make_contract_job(a.contract,a.subject_id,load_json(Path(a.input)),registry_path=Path(a.registry).resolve() if a.registry else None,job_id=a.job_id,source_session_id=a.source_session_id,handoff_id=a.handoff_id,qualification_receipt=load_json(Path(a.qualification_receipt)) if a.qualification_receipt else None),Path(a.output) if a.output else None);return 0\n''')
replace_once(path,
'''    if a.command=="validate-jobs":\n        payload=load_json(Path(a.jobs));e=[f"{j.get('job_id')}: {x}" for j in payload.get("jobs",[]) for x in validate_job(j)]\n''',
'''    if a.command in {"validate-jobs","validate-dispatchable-jobs"}:\n        payload=load_json(Path(a.jobs));validator=validate_dispatchable_job if a.command=="validate-dispatchable-jobs" else validate_job;e=[f"{j.get('job_id')}: {x}" for j in payload.get("jobs",[]) for x in validator(j)]\n''')

# 5) Direct runner refuses unqualified dispatch and strips runtime proof before model invocation.
path='harness/semantic_workers/semantic_worker_runner.py'
replace_once(path,
'''from semantic_worker_router import load_json,validate_job,validate_result\n''',
'''from semantic_worker_router import load_json,validate_dispatchable_job,validate_result,worker_job_view\n''')
replace_once(path,
'''    try:proc=subprocess.run(argv,input=json.dumps(job,ensure_ascii=False),text=True,capture_output=True,timeout=timeout,check=False)\n''',
'''    try:proc=subprocess.run(argv,input=json.dumps(worker_job_view(job),ensure_ascii=False),text=True,capture_output=True,timeout=timeout,check=False)\n''')
text=(ROOT/path).read_text(encoding='utf-8')
text=text.replace('errors=validate_job(j)','errors=validate_dispatchable_job(j)')
(ROOT/path).write_text(text,encoding='utf-8')

# 6) Peer-chat relay validates full dispatch proof, then strips it from reviewer packet.
path='harness/semantic_workers/peer_chat_relay.py'
replace_once(path,
'''from semantic_worker_router import validate_job,validate_result  # noqa: E402\n''',
'''from semantic_worker_router import validate_dispatchable_job,validate_job,validate_result,worker_job_view  # noqa: E402\n''')
replace_once(path,
'''    errors=validate_job(job)\n    if errors: raise ValueError("invalid job: "+"; ".join(errors))\n    nonce=secrets.token_urlsafe(24)\n    bounded={k:job.get(k) for k in ("job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance")}\n''',
'''    errors=validate_dispatchable_job(job)\n    if errors: raise ValueError("invalid dispatchable job: "+"; ".join(errors))\n    nonce=secrets.token_urlsafe(24)\n    visible=worker_job_view(job)\n    bounded={k:visible.get(k) for k in ("job_id","kind","subject_id","created_at","input_fingerprint","input","rubric","output_contract","permissions","provenance")}\n''')

# 7) Registered-contract binding self-test does not bypass production dispatch guard.
path='harness/semantic_workers/registered_contract_binding.py'
replace_once(path,
'''    good = make_contract_job(\n        "quality.production_review",\n        "CH-SELF",\n        {"candidate_fingerprint": fp, "candidate_text": "fixture", "reader_grip": "very_high"},\n        source_session_id="SES-MANAGER",\n    )\n''',
'''    good = make_contract_job(\n        "reader.engagement_audit",\n        "CH-SELF",\n        {"candidate_fingerprint": fp, "candidate_text": "fixture", "reader_grip": "very_high"},\n        source_session_id="SES-MANAGER",\n    )\n''')

# 8) Production readiness requires exact qualification when independent review is required.
path='quality/production_readiness.py'
replace_once(path,
'''from semantic_worker_router import make_contract_job, validate_result  # noqa: E402\n''',
'''from semantic_worker_router import make_contract_job, validate_result  # noqa: E402\nfrom candidate_qualification import validate_qualification_receipt  # noqa: E402\n''')
replace_once(path,
'''    if not all(isinstance(x, bool) for x in (require_continuity, require_semantic_rules, require_independent)):\n        raise ValueError("policy requirement flags must be boolean")\n\n    required = ["surface", "reader_engagement"]\n''',
'''    if not all(isinstance(x, bool) for x in (require_continuity, require_semantic_rules, require_independent)):\n        raise ValueError("policy requirement flags must be boolean")\n\n    qualification = payload.get("pre_independent_qualification")\n    qualification_summary = None\n    if require_independent:\n        errors = validate_qualification_receipt(qualification, candidate_fingerprint=candidate, require_qualified=True)\n        if errors:\n            raise ValueError("pre_independent_qualification invalid: " + "; ".join(errors))\n        qualification_summary = {\n            "receipt_fingerprint": qualification.get("receipt_fingerprint"),\n            "qualification_status": qualification.get("qualification_status"),\n            "candidate_fingerprint": qualification.get("candidate_fingerprint"),\n            "independent": qualification.get("independent"),\n        }\n\n    required = ["surface", "reader_engagement"]\n''')
replace_once(path,
'''        "project_bridge_receipt_required_for_independence": require_independent,\n        "semantic_content_reinterpreted_by_runtime": False,\n''',
'''        "project_bridge_receipt_required_for_independence": require_independent,\n        "pre_independent_qualification_required": require_independent,\n        "pre_independent_qualification": qualification_summary,\n        "independent_pass_can_override_qualification_failure": False,\n        "semantic_content_reinterpreted_by_runtime": False,\n''')
replace_once(path,
'''        "project_bridge_receipt_required_for_independence": True,\n        "numeric_quality_aggregation": False,\n''',
'''        "project_bridge_receipt_required_for_independence": True,\n        "pre_independent_qualification_required": True,\n        "independent_pass_can_override_qualification_failure": False,\n        "numeric_quality_aggregation": False,\n''')

# 9) Final release revalidates qualification instead of trusting a mutated readiness boolean.
path='quality/production_release.py'
replace_once(path,
'''from typing import Any\n\nSCHEMA = "novelforge_production_release_v1"\n''',
'''from typing import Any\n\nfrom candidate_qualification import validate_qualification_receipt\n\nSCHEMA = "novelforge_production_release_v1"\n''')
replace_once(path,
'''    base_ready = readiness.get("ready_for_user_visible_review")\n    if not isinstance(base_ready, bool):\n        raise ValueError("production_readiness ready flag required")\n\n    policy = payload.get("structural_policy", {})\n''',
'''    base_ready = readiness.get("ready_for_user_visible_review")\n    if not isinstance(base_ready, bool):\n        raise ValueError("production_readiness ready flag required")\n    readiness_policy = readiness.get("policy", {}) if isinstance(readiness.get("policy"), dict) else {}\n    require_independent = readiness_policy.get("require_independent_semantic") is True\n    qualification = payload.get("pre_independent_qualification")\n    qualification_fp = None\n    if require_independent:\n        errors = validate_qualification_receipt(qualification, candidate_fingerprint=candidate, require_qualified=True)\n        if errors:\n            raise ValueError("pre_independent_qualification invalid at release: " + "; ".join(errors))\n        qualification_fp = qualification.get("receipt_fingerprint")\n\n    policy = payload.get("structural_policy", {})\n''')
replace_once(path,
'''        "base_production_readiness": base_ready,\n        "required_structural_receipts": required,\n''',
'''        "base_production_readiness": base_ready,\n        "pre_independent_qualification_required": require_independent,\n        "pre_independent_qualification_fingerprint": qualification_fp,\n        "independent_pass_can_override_qualification_failure": False,\n        "required_structural_receipts": required,\n''')

print('temporary pre-independent qualification patch applied')
