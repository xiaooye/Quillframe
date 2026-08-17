#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path:str)->str:
    return (ROOT/path).read_text(encoding='utf-8')

def write(path:str,text:str)->None:
    (ROOT/path).write_text(text,encoding='utf-8')

def replace_once(path:str,old:str,new:str)->None:
    text=read(path); n=text.count(old)
    if n!=1: raise SystemExit(f'{path}: expected one replacement, got {n}: {old[:120]!r}')
    write(path,text.replace(old,new,1))

def dump(path:str,value)->None:
    write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

# ---------------------------------------------------------------------------
# Semantic contracts: Editor emits FIX+PRESERVE; quality.compare becomes the
# single structured repair-outcome comparator rather than adding a duplicate.
# ---------------------------------------------------------------------------
prod_path='harness/semantic_workers/contracts/production-loop.json'
prod=json.loads(read(prod_path)); prod['version']='4'
prod['principle']='Production-loop semantic artifacts stay thin. Models interpret feedback, causal scene state, current objective preservation and repair strategy; machines consume only the small fields needed for authority-safe persistence or routing. Private character state may drive semantic decisions but is not prose payload, and rejected repair trajectories do not become the fresh Writer objective.'
editor=prod['contracts']['editor.repair_spec']
editor['purpose']='Editor integrates bounded Reader/rule findings, authorized story evidence and the current objective envelope, then emits a FIX+PRESERVE repair specification and chooses local repair versus fresh reconstructed realization. Python enforces the chosen information boundary but does not infer literary repair depth.'
editor['input_contract']['required']=['candidate_fingerprint','reader_assessment','objective_envelope']
editor['input_contract']['properties']['objective_envelope']={
    'type':'object','required':['fingerprint','objective_items','must_preserve'],
    'properties':{
        'fingerprint':{'type':'string','minLength':71,'maxLength':71},
        'objective_items':{'type':'array','minItems':1,'items':{'type':'object'}},
        'must_preserve':{'type':'array','minItems':1,'items':{'type':'string','minLength':1}},
        'supersedes_fingerprint':{'type':['string','null']},
        'change_authority_ref':{'type':['string','null']},
    },'additionalProperties':True,
}
editor['rubric']=[
    'Integrate evidence before prescribing repair. The repair target and the higher-order objective are separate: removing a defect is not success if required story/reader/character value is materially damaged.',
    'Return a FIX statement for the owning failure mechanism and a compact PRESERVE list grounded in the supplied objective envelope. Preserve function, reader question/pressure/reward, character or relationship energy, humor/charm, payoff and forward pull only when they are actually required by current evidence.',
    'Choose repair depth and generation mode semantically. Do not map a Reader label, HF code, owner, scope, paragraph count, repair-cycle count or metric to a predetermined local/fresh decision table.',
    'Choose fresh_realization when rejected realization or accumulated critique is likely to anchor the Writer, or when objective regression/contextual inertia/oscillation makes patch continuation unsafe. A fresh realization reconstructs current authoritative state; it does not append the full rejection trajectory.',
    'Do not solve objective regression by weakening valid Surface/Canon/character constraints. Search for a candidate that satisfies both the repair target and the preserved objective.',
    'For material subjective changes, require incumbent/challenger comparison. Do not assume revision is improvement, and do not require wording or beat-order preservation when a major fresh realization keeps the intended functions.',
    'Do not perform the rewrite, mutate Canon, activate Author Model preferences or expose private chain-of-thought.',
]
out=editor['output_contract']; out['required']=['confidence','repair_owner','generation_mode','fix','repair_plan','preserve','comparison_required']
out['properties']['fix']={'type':'string','minLength':1}
out['properties']['preserve']={'type':'array','minItems':1,'items':{'type':'string','minLength':1}}
out['properties']['context_strategy_reason']={'type':['string','null']}
dump(prod_path,prod)

creative_path='harness/semantic_workers/contracts/creative-evolution.json'
creative=json.loads(read(creative_path)); creative['version']='4'
creative['principle']='Creative exploration should produce causally distinct options, while repair comparison must verify both targeted improvement and preservation of the current creative objective. Deterministic ledgers bind candidates, envelopes and results but never manufacture literary improvement signals or weighted quality scores.'
compare=creative['contracts']['quality.compare']
compare['purpose']='Compare an incumbent and repair challenger against an explicit repair target and compact objective envelope. Classify whether the target was not fixed, the target was fixed but a required objective regressed, or the repair succeeded without material higher-order regression.'
compare['input_contract']['properties']['repair_context']={
    'type':'object','required':['repair_target','objective_envelope'],
    'properties':{
        'repair_target':{'type':'string','minLength':1},
        'objective_envelope':{
            'type':'object','required':['schema','subject_id','run_id','fingerprint','objective_items','must_preserve','derived_from_rejected_realization'],
            'properties':{
                'schema':{'enum':['novelforge_objective_envelope_v1']},
                'subject_id':{'type':'string','minLength':1},
                'run_id':{'type':'string','minLength':1},
                'fingerprint':{'type':'string','minLength':71,'maxLength':71},
                'objective_items':{'type':'array','minItems':1,'items':{'type':'object'}},
                'must_preserve':{'type':'array','minItems':1,'items':{'type':'string','minLength':1}},
                'derived_from_rejected_realization':{'enum':[False]},
                'supersedes_fingerprint':{'type':['string','null']},
                'change_authority_ref':{'type':['string','null']},
                'authority_cutoff':{'type':'string'},
                'semantic_completeness_judged_by_runtime':{'type':'boolean'},
                'authority':{'type':'boolean'},
                'permissions':{'type':'object'},
                'model_execution':{'type':'boolean'},
            },'additionalProperties':True,
        },
        'repair_evidence_refs':{'type':'array','items':{'type':'string'}},
        'incumbent_strengths':{'type':'array','items':{'type':'string'}},
    },'additionalProperties':False,
}
compare['rubric']=[
    'Judge only the supplied incumbent, challenger, repair target, objective envelope and bounded evidence. The objective envelope is current run evidence, not a weighted score or a wording-preservation template.',
    'First decide TARGET OUTCOME: whether the challenger materially improves the specified failure mechanism. Separately decide OBJECTIVE PRESERVATION: whether the required story/reader/character functions in the objective envelope survive.',
    'Also compare reader value and character/relationship energy when applicable. Surface cleanliness is a constraint on valid solutions, not the objective function.',
    'Classify TARGET_NOT_FIXED when the defect did not improve; OBJECTIVE_REGRESSION when the target improved but a required higher-order objective materially degraded; SUCCESSFUL_REPAIR only when the target improved without blocking objective regression; INCONCLUSIVE when evidence is insufficient.',
    'A challenger with objective regression must not win merely because it is smoother, shorter, safer or more constraint-compliant. Preserve the incumbent or request another repair.',
    'Do not require wording or structure preservation. A major fresh realization can win when it preserves the intended functions and improves the repair target.',
    'If the supplied objective envelope explicitly supersedes an earlier one under authorized user steering, judge the challenger against the current envelope; legitimate goal change is not regression.',
    'Prefer pairwise observable evidence over absolute scores. Do not use arbitrary weighted sums. Return concise evidence without private chain-of-thought.',
]
compare['output_contract']={
    'type':'object',
    'required':['confidence','winner','reason','target_outcome','objective_preservation','reader_value','character_relationship_energy','outcome_class','repaired_findings','introduced_regressions','regressed_dimensions','preserved_strengths','evidence'],
    'properties':{
        'confidence':{'type':'number','minimum':0,'maximum':1},
        'winner':{'enum':['incumbent','challenger','tie']},
        'reason':{'type':'string','minLength':1},
        'target_outcome':{'enum':['improved','unchanged','worse','insufficient_evidence']},
        'objective_preservation':{'enum':['preserved','degraded','materially_degraded','insufficient_evidence']},
        'reader_value':{'enum':['improved','unchanged','degraded','insufficient_evidence']},
        'character_relationship_energy':{'enum':['preserved','degraded','not_applicable','insufficient_evidence']},
        'outcome_class':{'enum':['target_not_fixed','objective_regression','successful_repair','inconclusive']},
        'repaired_findings':{'type':'array','items':{'type':'string'}},
        'introduced_regressions':{'type':'array','items':{'type':'string'}},
        'regressed_dimensions':{'type':'array','items':{'type':'string'}},
        'preserved_strengths':{'type':'array','items':{'type':'string'}},
        'evidence':{'type':'array','minItems':1,'items':{'type':'string','minLength':1}},
    },'additionalProperties':False,
}
dump(creative_path,creative)

catalog_path='harness/semantic_workers/model_contract_catalog.json'
catalog=json.loads(read(catalog_path)); catalog['version']='9'
for pack in catalog['packs']:
    if pack['id']=='production-loop':
        pack['description']='Review-feedback interpretation, minimal writer-safe causal projection, and FIX+PRESERVE Editor repair planning with a compact objective envelope.'
        pack['load_when']='The production loop must interpret explicit feedback, project private simulation into minimal writer-safe causal context, or create a bounded repair plan that fixes the owning mechanism while preserving current higher-order objectives.'
    if pack['id']=='creative-evolution':
        pack['description']='Causally divergent scenario exploration, objective-preserving repair comparison, and neutral anonymous A/B semantic-ablation comparison without granting simplification authority.'
        pack['load_when']='The workflow needs materially distinct scenario forks, must verify targeted repair improvement without higher-order objective regression, or needs an independent neutral comparison of two anonymous semantic-ablation condition results.'
dump(catalog_path,catalog)

# ---------------------------------------------------------------------------
# Runtime binding: validate objective-envelope identity and internal consistency
# of the model-owned quality.compare classification. Runtime never infers prose.
# ---------------------------------------------------------------------------
router='harness/semantic_workers/semantic_worker_router.py'
replace_once(router,
'''        return e\n    return e\n\ndef validate_contract_input(cid:str,contract:dict[str,Any],input_payload:dict[str,Any])->list[str]:''',
'''        return e\n    if cid=="quality.compare":\n        repair_context=input_payload.get("repair_context",{})\n        envelope=repair_context.get("objective_envelope") if isinstance(repair_context,dict) else None\n        if isinstance(envelope,dict):\n            quality_root=HERE.parents[1]/"quality"\n            if str(quality_root) not in sys.path:sys.path.insert(0,str(quality_root))\n            from objective_envelope import validate as validate_objective_envelope\n            e += ["quality.compare objective envelope: "+x for x in validate_objective_envelope(envelope,subject_id=input_payload.get("evolution_subject_id"),run_id=input_payload.get("evolution_run_id"))]\n        return e\n    return e\n\ndef validate_contract_input(cid:str,contract:dict[str,Any],input_payload:dict[str,Any])->list[str]:''')
replace_once(router,
'''        return e\n    return e\n\ndef semantic_payload(job:dict[str,Any])->dict[str,Any]:''',
'''        return e\n    if cid=="quality.compare":\n        winner=judgment.get("winner"); target=judgment.get("target_outcome"); preservation=judgment.get("objective_preservation")\n        reader=judgment.get("reader_value"); energy=judgment.get("character_relationship_energy"); outcome=judgment.get("outcome_class")\n        regressed=judgment.get("regressed_dimensions",[])\n        if outcome=="successful_repair":\n            if target!="improved" or preservation!="preserved" or reader not in {"improved","unchanged"} or energy not in {"preserved","not_applicable"}:e.append("quality.compare successful_repair contradicts repair axes")\n            if winner!="challenger":e.append("quality.compare successful_repair must select challenger")\n        elif outcome=="objective_regression":\n            if target!="improved" or preservation not in {"degraded","materially_degraded"}:e.append("quality.compare objective_regression contradicts repair axes")\n            if winner=="challenger":e.append("quality.compare objective_regression cannot select challenger")\n            if not isinstance(regressed,list) or not regressed:e.append("quality.compare objective_regression requires regressed_dimensions")\n        elif outcome=="target_not_fixed":\n            if target=="improved":e.append("quality.compare target_not_fixed contradicts target improvement")\n            if winner=="challenger":e.append("quality.compare target_not_fixed cannot select challenger")\n        elif outcome=="inconclusive":\n            if winner!="tie":e.append("quality.compare inconclusive must use tie")\n        return e\n    return e\n\ndef semantic_payload(job:dict[str,Any])->dict[str,Any]:''')

# ---------------------------------------------------------------------------
# Candidate qualification: material repair requires exact quality.compare
# preservation evidence. Baseline candidates are not forced to invent an
# incumbent comparison.
# ---------------------------------------------------------------------------
qual='quality/candidate_qualification.py'
insert='''\n\ndef _repair_preservation_gate(raw: Any, *, candidate: str, subject_id: str) -> dict[str, Any]:\n    if not isinstance(raw, dict):\n        raise ValueError("repair_preservation gate object required for repair_cycle > 0")\n    declared = raw.get("status")\n    if declared not in GATE_STATUSES:\n        raise ValueError("repair_preservation.status must be pass|fail|pending")\n    if declared == "pending":\n        return {"gate":"repair_preservation","status":"pending","contract_id":"quality.compare","job_fingerprint":None,"result_fingerprint":None,"objective_envelope_fingerprint":None,"target_outcome":"insufficient_evidence","objective_preservation":"insufficient_evidence","reader_value":"insufficient_evidence","character_relationship_energy":"insufficient_evidence","outcome_class":"inconclusive","evidence_refs":[]}\n    binding=raw.get("semantic_binding")\n    if not isinstance(binding,dict) or not isinstance(binding.get("job"),dict) or not isinstance(binding.get("result"),dict):\n        raise ValueError("repair_preservation semantic_binding requires job and result")\n    job=binding["job"]; result=binding["result"]\n    validate_registered_job, validate_result = _load_semantic_runtime()\n    job_errors=validate_registered_job(job)\n    if job_errors: raise ValueError("repair_preservation registered job invalid: "+"; ".join(job_errors))\n    result_errors=validate_result(job,result)\n    if result_errors: raise ValueError("repair_preservation semantic result invalid: "+"; ".join(result_errors))\n    if result.get("status")!="completed": raise ValueError("repair_preservation semantic result must be completed")\n    input_obj=job.get("input",{}); payload=input_obj.get("payload",{}) if isinstance(input_obj,dict) else {}\n    if input_obj.get("model_contract_id")!="quality.compare": raise ValueError("repair_preservation requires quality.compare")\n    if payload.get("evolution_subject_id")!=subject_id: raise ValueError("repair_preservation subject mismatch")\n    challenger=payload.get("challenger",{}); repair_context=payload.get("repair_context",{})\n    if not isinstance(challenger,dict) or challenger.get("content_fingerprint")!=candidate: raise ValueError("repair_preservation challenger fingerprint mismatch")\n    envelope=repair_context.get("objective_envelope",{}) if isinstance(repair_context,dict) else {}\n    envelope_fp=envelope.get("fingerprint") if isinstance(envelope,dict) else None\n    _sha(envelope_fp,"repair_preservation objective_envelope_fingerprint")\n    judgment=result.get("judgment",{})\n    target=judgment.get("target_outcome"); preservation=judgment.get("objective_preservation"); reader=judgment.get("reader_value"); energy=judgment.get("character_relationship_energy"); outcome=judgment.get("outcome_class")\n    if "insufficient_evidence" in {target,preservation,reader,energy} or outcome=="inconclusive": derived="pending"\n    elif outcome=="successful_repair" and target=="improved" and preservation=="preserved" and reader in {"improved","unchanged"} and energy in {"preserved","not_applicable"}: derived="pass"\n    else: derived="fail"\n    if declared!=derived: raise ValueError("repair_preservation.status contradicts semantic comparison")\n    return {"gate":"repair_preservation","status":derived,"contract_id":"quality.compare","job_fingerprint":job.get("input_fingerprint"),"result_fingerprint":_result_fingerprint(result),"objective_envelope_fingerprint":envelope_fp,"target_outcome":target,"objective_preservation":preservation,"reader_value":reader,"character_relationship_energy":energy,"outcome_class":outcome,"evidence_refs":_string_list(judgment.get("evidence",[]),"repair_preservation.evidence_refs")}\n'''
replace_once(qual,'\n\ndef _receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:',insert+'\n\ndef _receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:')
replace_once(qual,
'''    continuity = _continuity_gate(payload.get("continuity"), candidate=candidate)\n\n    gates = [self_audit, reader, continuity]\n''',
'''    continuity = _continuity_gate(payload.get("continuity"), candidate=candidate)\n    preservation = _repair_preservation_gate(payload.get("repair_preservation"), candidate=candidate, subject_id=subject_id) if repair_cycle > 0 else {"gate":"repair_preservation","status":"not_applicable","contract_id":"quality.compare","job_fingerprint":None,"result_fingerprint":None,"objective_envelope_fingerprint":None,"target_outcome":"not_applicable","objective_preservation":"not_applicable","reader_value":"not_applicable","character_relationship_energy":"not_applicable","outcome_class":"not_applicable","evidence_refs":[]}\n\n    gates = [self_audit, reader, continuity, preservation]\n''')
replace_once(qual,
'''        "reader_engagement_status": reader["status"],\n        "continuity_status": continuity["status"],\n''',
'''        "reader_engagement_status": reader["status"],\n        "continuity_status": continuity["status"],\n        "repair_preservation_status": preservation["status"],\n        "repair_target_status": preservation["target_outcome"],\n        "objective_preservation_status": preservation["objective_preservation"],\n        "repair_reader_value": preservation["reader_value"],\n        "repair_character_relationship_energy": preservation["character_relationship_energy"],\n        "repair_outcome_class": preservation["outcome_class"],\n        "objective_envelope_fingerprint": preservation["objective_envelope_fingerprint"],\n''')
replace_once(qual,
'''    for field in ("surface_audit_status", "regression_audit_status", "character_or_ownership_status", "natural_realization_status", "cluster_audit_status", "reader_engagement_status", "continuity_status"):\n        if receipt.get(field) not in {"pass", "fail", "pending", "insufficient_evidence", "not_applicable"}:\n            errors.append(f"qualification {field} invalid")\n''',
'''    for field in ("surface_audit_status", "regression_audit_status", "character_or_ownership_status", "natural_realization_status", "cluster_audit_status", "reader_engagement_status", "continuity_status", "repair_preservation_status"):\n        if receipt.get(field) not in {"pass", "fail", "pending", "insufficient_evidence", "not_applicable"}:\n            errors.append(f"qualification {field} invalid")\n    if receipt.get("repair_target_status") not in {"improved","unchanged","worse","insufficient_evidence","not_applicable"}: errors.append("qualification repair_target_status invalid")\n    if receipt.get("objective_preservation_status") not in {"preserved","degraded","materially_degraded","insufficient_evidence","not_applicable"}: errors.append("qualification objective_preservation_status invalid")\n    if receipt.get("repair_reader_value") not in {"improved","unchanged","degraded","insufficient_evidence","not_applicable"}: errors.append("qualification repair_reader_value invalid")\n    if receipt.get("repair_character_relationship_energy") not in {"preserved","degraded","not_applicable","insufficient_evidence"}: errors.append("qualification repair_character_relationship_energy invalid")\n    if receipt.get("repair_outcome_class") not in {"target_not_fixed","objective_regression","successful_repair","inconclusive","not_applicable"}: errors.append("qualification repair_outcome_class invalid")\n    cycle=receipt.get("repair_cycle")\n    if isinstance(cycle,int) and not isinstance(cycle,bool) and cycle>0:\n        if receipt.get("repair_preservation_status")!="pass": errors.append("repaired candidate requires passing repair_preservation")\n        try: _sha(receipt.get("objective_envelope_fingerprint"),"objective_envelope_fingerprint")\n        except ValueError as exc: errors.append(str(exc))\n''')
# Existing baseline self-test should remain baseline; dedicated repair proof is appended below.
replace_once(qual,'        "repair_cycle": 1,\n        "self_audit": {"status": "pass", "semantic_binding": pass_audit},','        "repair_cycle": 0,\n        "self_audit": {"status": "pass", "semantic_binding": pass_audit},')
replace_once(qual,
'''    tampered = json.loads(json.dumps(qualified))\n    tampered["repair_cycle"] = 99\n    tamper_errors = validate_qualification_receipt(tampered, candidate_fingerprint=fp, subject_id=subject)\n\n    checks = {\n''',
'''    tampered = json.loads(json.dumps(qualified))\n    tampered["repair_cycle"] = 99\n    tamper_errors = validate_qualification_receipt(tampered, candidate_fingerprint=fp, subject_id=subject)\n\n    from objective_envelope import build as build_objective_envelope\n    from semantic_worker_router import make_contract_job\n    envelope=build_objective_envelope({"subject_id":subject,"run_id":"RUN-SELF","authority_cutoff":"synthetic","objective_items":[{"id":"OBJ-SELF","category":"reader","statement":"Preserve active pressure.","source_refs":["plan:self"]}],"must_preserve":["active pressure"],"derived_from_rejected_realization":False})\n    compare_payload={"evolution_run_id":"RUN-SELF","evolution_subject_id":subject,"comparison_id":"CMP-SELF","incumbent":{"candidate_id":"C0","content_fingerprint":"sha256:"+"0"*64},"challenger":{"candidate_id":"C1","content_fingerprint":fp,"repair_owner":"surface"},"repair_context":{"repair_target":"remove synthetic realization","objective_envelope":envelope}}\n    compare_job=make_contract_job("quality.compare","CMP-SELF",compare_payload,source_session_id="SES-MANAGER")\n    def compare_result(outcome:str)->dict[str,Any]:\n        if outcome=="successful_repair": judgment={"confidence":.9,"winner":"challenger","reason":"target fixed; objective preserved","target_outcome":"improved","objective_preservation":"preserved","reader_value":"unchanged","character_relationship_energy":"preserved","outcome_class":"successful_repair","repaired_findings":["HF-SELF"],"introduced_regressions":[],"regressed_dimensions":[],"preserved_strengths":["active pressure"],"evidence":["candidate:compare"]}\n        else: judgment={"confidence":.9,"winner":"incumbent","reason":"target fixed but pressure collapsed","target_outcome":"improved","objective_preservation":"materially_degraded","reader_value":"degraded","character_relationship_energy":"preserved","outcome_class":"objective_regression","repaired_findings":["HF-SELF"],"introduced_regressions":["reader_pressure"],"regressed_dimensions":["reader_pressure"],"preserved_strengths":[],"evidence":["candidate:compare"]}\n        return {"job_id":compare_job["job_id"],"subject_id":compare_job["subject_id"],"kind":compare_job["kind"],"input_fingerprint":compare_job["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"comparison-fixture"},"judgment":judgment,"proposals":[],"errors":[]}\n    repaired_ok=evaluate({"candidate_fingerprint":fp,"subject_id":subject,"repair_cycle":1,"self_audit":{"status":"pass","semantic_binding":pass_audit},"reader_engagement":{"status":"pass","semantic_binding":reader},"continuity":continuity,"repair_preservation":{"status":"pass","semantic_binding":{"job":compare_job,"result":compare_result("successful_repair")}}})\n    repaired_regression=evaluate({"candidate_fingerprint":fp,"subject_id":subject,"repair_cycle":1,"self_audit":{"status":"pass","semantic_binding":pass_audit},"reader_engagement":{"status":"pass","semantic_binding":reader},"continuity":continuity,"repair_preservation":{"status":"fail","semantic_binding":{"job":compare_job,"result":compare_result("objective_regression")}}})\n    missing_preservation_guard=False\n    try: evaluate({"candidate_fingerprint":fp,"subject_id":subject,"repair_cycle":1,"self_audit":{"status":"pass","semantic_binding":pass_audit},"reader_engagement":{"status":"pass","semantic_binding":reader},"continuity":continuity})\n    except ValueError: missing_preservation_guard=True\n\n    checks = {\n''')
replace_once(qual,
'''        "runtime_does_not_reinterpret_semantics": qualified["semantic_content_reinterpreted_by_runtime"] is False,\n        "no_write_authority": not any(qualified["permissions"].values()),\n''',
'''        "runtime_does_not_reinterpret_semantics": qualified["semantic_content_reinterpreted_by_runtime"] is False,\n        "repair_success_can_qualify": repaired_ok["qualification_status"]=="qualified_for_independent" and repaired_ok["objective_preservation_status"]=="preserved",\n        "repair_objective_regression_blocks": repaired_regression["qualification_status"]=="repair_required" and repaired_regression["repair_outcome_class"]=="objective_regression",\n        "material_repair_missing_preservation_blocks": missing_preservation_guard,\n        "baseline_preservation_not_applicable": qualified["repair_preservation_status"]=="not_applicable",\n        "no_write_authority": not any(qualified["permissions"].values()),\n''')

# ---------------------------------------------------------------------------
# Repair writer context: keep objective + distilled FIX/PRESERVE; fresh path
# additionally reconstructs state and hides accumulated negative trajectory.
# ---------------------------------------------------------------------------
repair='quality/repair_policy.py'
replace_once(repair,
'''    excluded = []\n    required = ["authority_constraints", "editor_repair_plan"]\n    if fresh:\n        excluded = ["rejected_prose", "concrete_critic_surface_patches", "prior_reviewer_verdict"]\n        required += ["current_story_state"]\n    else:\n        required += ["bounded_repair_evidence"]\n''',
'''    excluded = []\n    required = ["authority_constraints", "objective_envelope", "editor_fix_and_preserve_plan"]\n    if fresh:\n        excluded = ["rejected_prose", "concrete_critic_surface_patches", "prior_reviewer_verdict", "full_repair_trajectory", "raw_user_complaint_chain", "regression_bad_examples"]\n        required += ["reconstructed_current_story_state"]\n    else:\n        required += ["bounded_repair_evidence"]\n''')
replace_once(repair,
'''        "post_generation_fresh_review_required": fresh,\n        "incumbent_comparison_may_happen_after_generation": True,\n''',
'''        "post_generation_fresh_review_required": fresh,\n        "objective_envelope_required": True,\n        "fix_and_preserve_required": True,\n        "full_repair_trajectory_visible_to_fresh_writer": not fresh,\n        "raw_user_complaint_chain_visible_to_fresh_writer": not fresh,\n        "regression_bad_examples_visible_to_fresh_writer": not fresh,\n        "context_reset_trigger_judged_semantically": True,\n        "incumbent_comparison_required_for_material_repair": True,\n''')
replace_once(repair,
'''        "fresh_writer_cannot_see_concrete_patches": same_owner_fresh["concrete_critic_surface_patches_visible_to_writer"] is False,\n        "local_writer_can_see_bounded_repair_evidence": scene_local["rejected_prose_visible_to_writer"] is True,\n''',
'''        "fresh_writer_cannot_see_concrete_patches": same_owner_fresh["concrete_critic_surface_patches_visible_to_writer"] is False,\n        "fresh_writer_cannot_see_full_repair_trajectory": same_owner_fresh["full_repair_trajectory_visible_to_fresh_writer"] is False,\n        "fresh_writer_cannot_see_raw_user_complaint_chain": same_owner_fresh["raw_user_complaint_chain_visible_to_fresh_writer"] is False,\n        "fresh_writer_requires_objective_envelope": same_owner_fresh["objective_envelope_required"] is True and "objective_envelope" in same_owner_fresh["required_writer_context_classes"],\n        "fresh_writer_requires_fix_and_preserve": same_owner_fresh["fix_and_preserve_required"] is True,\n        "context_reset_not_cycle_count_rule": same_owner_fresh["context_reset_trigger_judged_semantically"] is True,\n        "local_writer_can_see_bounded_repair_evidence": scene_local["rejected_prose_visible_to_writer"] is True,\n''')

# ---------------------------------------------------------------------------
# Candidate evolution: every material repair comparison prepared by the ledger
# carries a valid objective envelope. Existing ledger still promotes only a
# semantic challenger winner; router consistency prevents objective-regression
# results from contradictorily selecting the challenger.
# ---------------------------------------------------------------------------
evo='quality/quality_evolution.py'
replace_once(evo,
'''    if not isinstance(repair_context, dict):\n        raise ValueError("repair_context must be object")\n    payload = {\n''',
'''    if not isinstance(repair_context, dict):\n        raise ValueError("repair_context must be object")\n    if not isinstance(repair_context.get("repair_target"),str) or not repair_context["repair_target"].strip():\n        raise ValueError("repair_context.repair_target required")\n    envelope=repair_context.get("objective_envelope")\n    if not isinstance(envelope,dict): raise ValueError("repair_context.objective_envelope required")\n    quality_root=ROOT/"quality"\n    if str(quality_root) not in sys.path:sys.path.insert(0,str(quality_root))\n    from objective_envelope import validate as validate_objective_envelope\n    envelope_errors=validate_objective_envelope(envelope,subject_id=run["subject_id"],run_id=run_id)\n    if envelope_errors: raise ValueError("invalid objective envelope: "+"; ".join(envelope_errors))\n    payload = {\n''')
replace_once(evo,
'''def _fixture_result(job: dict[str, Any], winner: str, reason: str) -> dict[str, Any]:\n    return {\n''',
'''def _fixture_result(job: dict[str, Any], winner: str, reason: str, *, objective_regression: bool=False) -> dict[str, Any]:\n    if winner=="challenger":\n        axes={"target_outcome":"improved","objective_preservation":"preserved","reader_value":"unchanged","character_relationship_energy":"preserved","outcome_class":"successful_repair","regressed_dimensions":[]}\n    elif objective_regression:\n        axes={"target_outcome":"improved","objective_preservation":"materially_degraded","reader_value":"degraded","character_relationship_energy":"preserved","outcome_class":"objective_regression","regressed_dimensions":["reader_pressure"]}\n    else:\n        axes={"target_outcome":"unchanged","objective_preservation":"preserved","reader_value":"unchanged","character_relationship_energy":"preserved","outcome_class":"target_not_fixed","regressed_dimensions":[]}\n    return {\n''')
replace_once(evo,
'''            "preserved_strengths": [],\n            "evidence": [reason],\n''',
'''            "preserved_strengths": ["reader pressure"],\n            "evidence": [reason],\n            **axes,\n''')
replace_once(evo,
'''    add_candidate(conn, run_id="RUN-1", candidate_id="C1", text="candidate one", repair_owner="reader")\n    j1 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-1", challenger_candidate_id="C1", repair_context={"targets": ["forward pull"]})\n''',
'''    from objective_envelope import build as build_objective_envelope\n    envelope=build_objective_envelope({"subject_id":"CH-1","run_id":"RUN-1","authority_cutoff":"synthetic","objective_items":[{"id":"OBJ-1","category":"reader","statement":"Preserve reader pressure.","source_refs":["plan:self"]}],"must_preserve":["reader pressure"],"derived_from_rejected_realization":False})\n    def rc(target:str)->dict[str,Any]: return {"repair_target":target,"objective_envelope":envelope}\n    add_candidate(conn, run_id="RUN-1", candidate_id="C1", text="candidate one", repair_owner="reader")\n    j1 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-1", challenger_candidate_id="C1", repair_context=rc("forward pull"))\n''')
replace_once(evo,'j2 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-2", challenger_candidate_id="C2", repair_context={"targets": ["surface"]})','j2 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-2", challenger_candidate_id="C2", repair_context=rc("surface"))')
replace_once(evo,'j3 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-3", challenger_candidate_id="C3", repair_context={"targets": ["scene"]})','j3 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-3", challenger_candidate_id="C3", repair_context=rc("scene"))')
replace_once(evo,
'''    frozen_binding = (\n''',
'''    objective_regression_guard=False\n    contradictory=_fixture_result(j1,"challenger","surface fixed but pressure collapsed")\n    contradictory["judgment"].update({"objective_preservation":"materially_degraded","reader_value":"degraded","outcome_class":"objective_regression","regressed_dimensions":["reader_pressure"]})\n    try: record_comparison(conn,job=j1,result=contradictory)\n    except ValueError: objective_regression_guard=True\n\n    frozen_binding = (\n''')
replace_once(evo,
'''        and frozen_binding\n        and s3["authority"] is False\n''',
'''        and frozen_binding\n        and objective_regression_guard\n        and s3["authority"] is False\n''')
replace_once(evo,
'''        "invalid_winner_rejected_by_contract": result_binding_guard,\n        "idempotent_replay": replay["incumbent_candidate_id"] == "C1",\n''',
'''        "invalid_winner_rejected_by_contract": result_binding_guard,\n        "objective_regression_cannot_promote_challenger": objective_regression_guard,\n        "objective_envelope_bound_to_comparison": j1["input"]["payload"]["repair_context"]["objective_envelope"]["fingerprint"]==envelope["fingerprint"],\n        "idempotent_replay": replay["incumbent_candidate_id"] == "C1",\n''')

# Existing pre-independent synthetic helper uses a baseline cycle. Objective
# repair behavior is covered by candidate_qualification self-test and the new suite.
pre='evals/pre_independent_qualification.py'
replace_once(pre,"'candidate_fingerprint':fp,'subject_id':SUBJECT,'repair_cycle':1 if not fail else 0,","'candidate_fingerprint':fp,'subject_id':SUBJECT,'repair_cycle':0,")

# ---------------------------------------------------------------------------
# Specs/docs: concise architecture statement. Full research matrix is a
# separate source-controlled artifact.
# ---------------------------------------------------------------------------
for path,heading,body in [
    ('specs/014-pre-independent-candidate-qualification/spec.en.md','## Repair objective preservation addendum','''\nA repaired candidate is not qualified merely because a targeted Surface/AI-realization failure disappears. Material repair uses a compact, fingerprint-bound `objective_envelope` selected semantically from current authorized request/plan/profile/state evidence. Rejected prose is not an objective source.\n\n`quality.compare` is the single repair-outcome comparator. It distinguishes `target_not_fixed`, `objective_regression`, `successful_repair`, and `inconclusive` using separate target, objective-preservation, reader-value, and character/relationship-energy axes. Runtime validates binding and internal consistency; it does not score literature. Only a semantically successful repair can normally advance as challenger.\n\n`editor.repair_spec` emits **FIX + PRESERVE**. Fresh realization receives reconstructed current state + objective envelope + distilled repair plan and hides rejected prose, full critique trajectory, raw complaint chain and regression bad examples. Context reconstruction is selected semantically when warranted; there is no fixed repair-cycle reset threshold.\n\nFor `repair_cycle > 0`, pre-independent qualification requires exact passing repair-preservation evidence in addition to self-audit, Reader and continuity. `repair_induced_objective_regression` is QA observability, not Canon or a deterministic literary verdict.\n\nResearch basis and inference boundaries: [research-objective-preservation.en.md](research-objective-preservation.en.md).\n'''),
    ('specs/014-pre-independent-candidate-qualification/plan.en.md','## Objective-preservation extension','''\n1. Bind a compact current objective envelope before material repair.\n2. Make Editor repair plans carry FIX and PRESERVE.\n3. Isolate fresh realization from rejected trajectories while retaining authoritative current state.\n4. Upgrade incumbent/challenger comparison to classify target-not-fixed vs objective-regression vs successful-repair.\n5. Require repair-preservation evidence before independent dispatch for repaired candidates.\n6. Run deterministic synthetic controls in normal CI; keep multi-turn/negative-context semantic ablations `PENDING_MODEL` until separate writer/evaluator execution is available.\n'''),
    ('specs/014-pre-independent-candidate-qualification/tasks.en.md','## Objective-preservation tasks','''\n- [x] Add fingerprint-bound objective-envelope deterministic contract.\n- [x] Add repair-induced-objective-regression QA receipt.\n- [x] Extend Editor to FIX+PRESERVE and fresh reconstructed context.\n- [x] Extend `quality.compare` with target/preservation/reader/character axes and A/B/C outcome classification.\n- [x] Bind repaired-candidate qualification to exact preservation evidence.\n- [x] Add 10+ synthetic repair-preservation fixtures and four multi-turn context strategies.\n- [ ] Execute independent writer/evaluator multi-turn ablation when an eligible model capability is available; do not substitute manager self-judgment.\n'''),
]:
    text=read(path)
    if heading not in text: write(path,text.rstrip()+f'\n\n{heading}\n'+body)

# Append generic operational docs without embedding story-specific examples.
for path,heading,body in [
    ('docs/quality-assurance.en.md','## Repair objective preservation','''\nA repair has two independent semantic questions: **did the targeted defect improve?** and **did the current higher-order objective survive?** Surface-clean is therefore never a substitute for story/reader quality. Material repair comparison binds incumbent, challenger, repair target and a compact objective envelope. A target fix that materially degrades required reader question, pressure, reward, character/relationship energy or forward pull is `repair_induced_objective_regression`; the incumbent stays protected and another repair is required. No weighted literary score is computed.\n'''),
    ('docs/production-pipeline.en.md','## Objective-preserving repair context','''\nRepair loops preserve a compact current `objective_envelope` across candidate lineage. Editor output is FIX + PRESERVE. When fresh realization is selected, Writer context is reconstructed from current authoritative state, the objective envelope and a distilled repair packet; rejected realization, full critique trajectory and regression bad examples remain outside Writer context. Material repaired candidates must pass objective-preservation comparison before independent dispatch.\n'''),
    ('harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md','## Repair-preservation evidence','''\n`quality.compare` may bind a repair challenger to an `objective_envelope`. The semantic worker separately judges target improvement and higher-order preservation. Runtime may reject an internally contradictory typed result (for example, `objective_regression` that also names the challenger as winner) but may not infer the literary classification itself.\n'''),
]:
    text=read(path)
    if heading not in text: write(path,text.rstrip()+f'\n\n{heading}\n'+body)

# Minimal Chinese operational docs for bilingual contract visibility.
for path,heading,body in [
    ('docs/quality-assurance.zh-CN.md','## 修复中的目标保持','''\n一次修复有两个彼此独立的语义问题：**目标缺陷是否改善**，以及**当前更高阶创作目标是否仍然成立**。Surface clean 不能替代 Story / Reader 质量。Material repair comparison 绑定 incumbent、challenger、repair target 与紧凑 `objective_envelope`；如果缺陷修掉了但 reader question、pressure、reward、人物/关系能量或 forward pull 等当前必保目标发生实质退化，记录为 `repair_induced_objective_regression`，保护 incumbent，并继续寻找新的 repair。系统不计算加权文学总分。\n'''),
    ('docs/production-pipeline.zh-CN.md','## 目标保持式修复上下文','''\nRepair loop 在 candidate lineage 中保持一个紧凑的 current `objective_envelope`。Editor 输出 FIX + PRESERVE。选择 fresh realization 时，Writer context 从 current authoritative state、objective envelope 与 distilled repair packet 重建；rejected realization、完整 critique trajectory 与 regression 坏例不进入 Writer。Material repaired candidate 在 independent dispatch 前必须通过 objective-preservation comparison。\n'''),
    ('harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md','## Repair-preservation evidence','''\n`quality.compare` 可以把 repair challenger 与 `objective_envelope` 精确绑定。Semantic worker 分开判断 target improvement 与 higher-order preservation。Runtime 可以拒绝内部自相矛盾的 typed result（例如 `objective_regression` 却同时把 challenger 判为 winner），但不能自己推断文学分类。\n'''),
]:
    text=read(path)
    if heading not in text: write(path,text.rstrip()+f'\n\n{heading}\n'+body)

print('objective-preservation integration patch applied')
