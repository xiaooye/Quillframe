#!/usr/bin/env python3
"""Deterministic controls and semantic-job packaging for candidate qualification.

The fixtures are synthetic/anonymized. Expected labels remain local to this
control module and are never inserted into model-facing jobs. Normal CI runs no
model; live semantic execution is a separate optional/manual concern.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SEM=ROOT/'harness'/'semantic_workers'
QUALITY=ROOT/'quality'
for p in (SEM,QUALITY):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

from candidate_qualification import evaluate as qualify, validate_qualification_receipt
from regression_escape import record as record_escape
from semantic_worker_router import make_contract_job, validate_dispatchable_job, validate_job, worker_job_view
from peer_chat_relay import build as build_peer_packet, validate_packet

FP='sha256:'+'a'*64
SUBJECT='SYNTH-CHAPTER'
RULES=[
    {'id':'HF-25','authority':'framework','statement':'Do not explain meaning after the scene has already supplied sufficient evidence.'},
    {'id':'HF-27','authority':'framework','statement':'Meaning and wording must belong to the current semantic owner/POV/speaker.'},
    {'id':'HF-29','authority':'framework','statement':'AI polish or clever framing without sufficient story/social function is a realization defect.'},
    {'id':'RG-08','authority':'framework','statement':'Humor/humanity should be character-owned and arise from agenda, relationship, pressure or history rather than author optimization.'},
]

CASES=[
    {'id':'fragment_punch','expected':'fail','mechanism':'HF-29','text':'“Not because he was weak. Because his hand was wrong.” The contrast adds no decision or correction in context.'},
    {'id':'legitimate_contrast','expected':'pass','mechanism':'control','text':'“Not the left valve—the right one.” She redirects his hand before the pressure spikes.'},
    {'id':'dialogue_padding_cluster','expected':'fail','mechanism':'HF-29','text':'“What?” He looked down. She answered. He looked up at her. She answered again. He smiled. Nothing changes except visible reactions.'},
    {'id':'functional_action','expected':'pass','mechanism':'control','text':'He looked down at the invoice; the surcharge doubled the project risk, so he stopped the signature.'},
    {'id':'random_embodiment_goal','expected':'fail','mechanism':'HF-25','text':'The date looked wrong. His back tightened. He needed to confirm the year. Then he searched for a calendar.'},
    {'id':'direct_causal_action','expected':'pass','mechanism':'control','text':'The date looked wrong. He pulled yesterday’s newspaper from the bin and checked the masthead.'},
    {'id':'explanation_after_evidence','expected':'fail','mechanism':'HF-25','text':'The father lifts the heavy box away from the injured child. The narrator adds: this already counted as caring.'},
    {'id':'synthetic_coolness','expected':'fail','mechanism':'HF-29','text':'He watched for a long moment, lowered his voice, and said, “Fine.” Nothing is decided and no relationship changes.'},
    {'id':'meaningful_short_utterance','expected':'pass','mechanism':'control','text':'The beam cracks above them. “Run!” sends the other person through the exit.'},
    {'id':'history_exposition','expected':'fail','mechanism':'reader','text':'He only needs today’s date, but the narrator pauses for a long explanation of the decade’s political and economic meaning.'},
    {'id':'event_bound_history','expected':'pass','mechanism':'control','text':'The newspaper date is enough to tell him the election has not happened yet; he folds it and changes his next call.'},
    {'id':'regression_isolation','expected':'pass','mechanism':'runtime','text':'First-pass writer context contains no rejected bad-example text; regression evidence becomes eligible only after diagnostic freeze.'},
    {'id':'qualification_missing','expected':'hard_refusal','mechanism':'runtime','text':'Attempt production review without qualification.'},
    {'id':'qualification_failed','expected':'hard_refusal','mechanism':'runtime','text':'Attempt production review with repair_required qualification.'},
    {'id':'qualification_stale','expected':'hard_refusal','mechanism':'runtime','text':'Rewrite candidate, keep old qualification fingerprint.'},
    {'id':'independent_cannot_override','expected':'hard_refusal','mechanism':'runtime','text':'Independent pass is presented while the exact candidate qualification remains blocking.'},
    {'id':'independent_fail_repair','expected':'repair','mechanism':'runtime','text':'Valid independent fail returns to owning mechanism and requires new fingerprint/qualification/review.'},
    {'id':'documentation_order','expected':'pass','mechanism':'runtime','text':'Framework execution docs agree: manager quality loop and qualification precede independent review.'},
    {'id':'normal_ci_no_model','expected':'pass','mechanism':'runtime','text':'Deterministic CI packages/validates only and performs no live paid/model call.'},
    {'id':'no_lexical_ban','expected':'pass','mechanism':'control','text':'She looked, smiled, and said “No, not that one” while identifying the correct switch and changing the group’s action.'},
    {'id':'functional_overwritten_dialogue','expected':'fail','mechanism':'HF-29','known':'functional_overauthored','text':'A father needs to stop an injured child from lifting a box, but delivers a polished, symmetrical, quote-ready joke whose main effect is to make him look charming.'},
    {'id':'natural_purpose_first_dialogue','expected':'pass','mechanism':'control','text':'The father pulls the box away. “Leave it. Yesterday wasn’t enough for you?” The established relationship permits the dry jab.'},
    {'id':'narrator_clever_reframing','expected':'fail','mechanism':'HF-27','known':'functional_overauthored','text':'A child forgets an ordinary promise; the narrator reframes it as a witty debt-collection metaphor although the POV never thinks in financial terms.'},
    {'id':'pov_owned_metaphor','expected':'pass','mechanism':'control','text':'An accountant POV treats the new obligation as an unpaid liability because that framing changes which deal he refuses.'},
    {'id':'punchline_stacking','expected':'fail','mechanism':'HF-29','known':'synthetic_punchline_stacking','text':'Three family turns form setup → clever answer → clever comeback → narrator witty gloss → another punchline; every line is plausible alone, but the cluster reads like optimized sitcom banter.'},
    {'id':'sparse_natural_humor','expected':'pass','mechanism':'control','text':'One sibling makes a relationship-owned dry joke while moving the task forward; everyone else keeps working instead of producing matching comebacks.'},
    {'id':'known_regression_round2','expected':'fail','mechanism':'HF-29','known':'synthetic_punchline_stacking','text':'A later candidate repeats the already-activated synthetic banter mechanism; it should be caught by manager self-audit before user delivery.'},
]


def _payload(case:dict[str,Any])->dict[str,Any]:
    regression=[]
    if case.get('known'):
        regression=[{
            'mechanism_id':case['known'],
            'status':'known_active_regression',
            'source_ref':'regression:synthetic:'+case['known'],
            'summary':'An already-modeled failure mechanism must be checked semantically on this candidate; literal phrases are not banned.',
        }]
    return {
        'candidate_fingerprint':FP,
        'candidate_text':case['text'],
        'rule_material':RULES,
        'regression_evidence':regression,
        'profile_constraints':[{'id':'PROFILE','statement':'Allow genuinely witty/charismatic speech when purpose-first, character-owned, situation-appropriate and consequential.'}],
        'voice_constraints':[],
        'reader_grip':'very_high',
    }


def build_semantic_jobs()->dict[str,Any]:
    jobs=[]
    for case in CASES:
        if case['mechanism']=='runtime':continue
        job=make_contract_job('quality.candidate_self_audit',case['id'],_payload(case),source_session_id='SES-QUAL-ABLATION')
        jobs.append(job)
    return {
        'semantic_worker_queue_version':'2',
        'suite':'pre_independent_candidate_qualification',
        'blind_expected_labels':True,
        'jobs':jobs,
        'model_execution':False,
    }


def expectation_manifest()->dict[str,Any]:
    return {
        'schema':'novelforge_pre_independent_qualification_expectations_v1',
        'cases':[{k:v for k,v in case.items() if k!='text'} for case in CASES],
        'stored_separately_from_semantic_jobs':True,
        'model_execution':False,
    }


def _binding(contract_id:str, subject:str, fp:str, judgment:dict[str,Any])->dict[str,Any]:
    payload={'candidate_fingerprint':fp,'candidate_text':'Synthetic bounded candidate.'}
    if contract_id=='quality.candidate_self_audit':
        payload.update({'rule_material':RULES,'regression_evidence':[],'profile_constraints':[],'voice_constraints':[],'reader_grip':'very_high'})
    elif contract_id=='reader.engagement_audit':
        payload['reader_grip']='very_high'
    job=make_contract_job(contract_id,subject,payload,source_session_id='SES-MANAGER')
    return {'job':job,'result':{
        'job_id':job['job_id'],'subject_id':job['subject_id'],'kind':job['kind'],'input_fingerprint':job['input_fingerprint'],
        'status':'completed','worker':{'provider':'self_test','model_or_reviewer':'semantic-fixture'},
        'judgment':judgment,'proposals':[],'errors':[],
    }}


def _reader(fp:str)->dict[str,Any]:
    return _binding('reader.engagement_audit',SUBJECT,fp,{
        'confidence':.9,'result':'pass','report':'Reader-grip control passes.','strongest_positive':'Purpose moves.','strongest_problem':None,'evidence_refs':['candidate:whole']
    })


def _audit(fp:str, *, fail:bool)->dict[str,Any]:
    if fail:
        judgment={
            'confidence':.9,'result':'fail','report':'Known synthetic banter / over-authored realization remains.',
            'dimensions':{'surface':'fail','regression':'fail','character_or_ownership':'fail','natural_realization':'fail','cluster':'fail'},
            'findings':[{
                'finding_id':'F-SYN-BANTER','mechanism_id':'HF-29','severity':'cluster','scope':'block','repair_owner':'character','blocking':True,
                'report':'Function exists, but ownership/natural-realization fail and punchlines stack.',
                'function_assessment':'pass','ownership_assessment':'fail','natural_realization_assessment':'fail','evidence_refs':['candidate:block-1'],
            }],
            'evidence_refs':['candidate:block-1'],
        }
    else:
        judgment={
            'confidence':.9,'result':'pass','report':'No material known realization defect remains.',
            'dimensions':{'surface':'pass','regression':'pass','character_or_ownership':'pass','natural_realization':'pass','cluster':'pass'},
            'findings':[],'evidence_refs':['candidate:whole'],
        }
    return _binding('quality.candidate_self_audit',SUBJECT,fp,judgment)


def _qualification(fp:str, *, fail:bool)->dict[str,Any]:
    return qualify({
        'candidate_fingerprint':fp,'subject_id':SUBJECT,'repair_cycle':1 if not fail else 0,
        'self_audit':{'status':'fail' if fail else 'pass','semantic_binding':_audit(fp,fail=fail)},
        'reader_engagement':{'status':'pass','semantic_binding':_reader(fp)},
        'continuity':{'status':'pass','candidate_fingerprint':fp,'receipt_fingerprint':'sha256:'+'c'*64,'evidence_refs':['continuity:synthetic']},
    })


def self_test()->dict[str,Any]:
    jobs=build_semantic_jobs()
    serialized=json.dumps(jobs,ensure_ascii=False)
    expected_tokens=('"expected"','hard_refusal')
    hidden_expected=all(token not in serialized for token in expected_tokens)

    failed=_qualification(FP,fail=True)
    qualified=_qualification(FP,fail=False)

    missing_blocked=False
    try:
        make_contract_job('quality.production_review',SUBJECT,{'candidate_fingerprint':FP,'candidate_text':'x','reader_grip':'very_high'})
    except ValueError as exc:
        missing_blocked='qualification' in str(exc)

    failed_blocked=False
    try:
        make_contract_job('quality.production_review',SUBJECT,{'candidate_fingerprint':FP,'candidate_text':'x','reader_grip':'very_high'},qualification_receipt=failed)
    except ValueError as exc:
        failed_blocked='qualified_for_independent' in str(exc) or 'qualification' in str(exc)

    review_job=make_contract_job('quality.production_review',SUBJECT,{'candidate_fingerprint':FP,'candidate_text':'x','reader_grip':'very_high'},qualification_receipt=qualified)
    dispatchable=not validate_dispatchable_job(review_job)
    reviewer_view=worker_job_view(review_job)
    reviewer_isolated='dispatch_proof' not in reviewer_view
    peer_packet=build_peer_packet(review_job)
    peer_isolated='dispatch_proof' not in peer_packet['job'] and not validate_packet(peer_packet)

    stale_blocked=False
    try:
        make_contract_job('quality.production_review',SUBJECT,{'candidate_fingerprint':'sha256:'+'b'*64,'candidate_text':'rewritten','reader_grip':'very_high'},qualification_receipt=qualified)
    except ValueError as exc:
        stale_blocked='fingerprint mismatch' in str(exc)

    known_round2=record_escape({
        'candidate_fingerprint':FP,
        'failure_mechanism':'synthetic_punchline_stacking',
        'where_it_should_have_been_caught':'manager_self_audit',
        'where_it_was_actually_detected':'manager_self_audit',
        'user_detected':False,'previously_known':True,
        'known_evidence_refs':['regression:synthetic:synthetic_punchline_stacking'],
        'detection_evidence_refs':['self-audit:round-2'],
    })
    user_escape=record_escape({
        'candidate_fingerprint':FP,
        'failure_mechanism':'synthetic_punchline_stacking',
        'where_it_should_have_been_caught':'manager_self_audit',
        'where_it_was_actually_detected':'user',
        'user_detected':True,'previously_known':True,
        'known_evidence_refs':['regression:synthetic:synthetic_punchline_stacking'],
        'detection_evidence_refs':['feedback:round-2'],
    })

    # No lexical ban: pass and fail fixtures intentionally share ordinary surface forms.
    lexical_control=any(c['expected']=='pass' and 'look' in c['text'].lower() for c in CASES) and any(c['expected']=='fail' and 'look' in c['text'].lower() for c in CASES)
    wit_control=any(c['id']=='sparse_natural_humor' and c['expected']=='pass' for c in CASES) and any(c['id']=='punchline_stacking' and c['expected']=='fail' for c in CASES)

    checks={
        'requested_control_count':len(CASES)>=27,
        'expected_labels_hidden_from_jobs':hidden_expected,
        'all_semantic_jobs_generic_valid':all(not validate_job(j) for j in jobs['jobs']),
        'missing_qualification_hard_refusal':missing_blocked,
        'failed_qualification_hard_refusal':failed_blocked,
        'qualified_job_dispatchable':dispatchable,
        'qualification_not_visible_to_direct_reviewer':reviewer_isolated,
        'qualification_not_visible_to_peer_reviewer':peer_isolated,
        'repair_changes_fingerprint_stales_qualification':stale_blocked,
        'manager_self_audit_non_independent':qualified['independent'] is False,
        'failed_self_audit_blocks_before_independent':failed['qualification_status']=='repair_required',
        'known_regression_round2_caught_pre_user':not known_round2['quality_loop_escape'],
        'known_regression_user_detection_is_escape':user_escape['user_regression_detector_escape'],
        'no_lexical_ban_control':lexical_control,
        'legitimate_wit_control':wit_control,
        'normal_ci_no_model_execution':jobs['model_execution'] is False,
    }
    return {
        'schema':'novelforge_pre_independent_qualification_test_v1',
        'pre_independent_qualification_contract':'PASS' if all(checks.values()) else 'FAIL',
        'checks':checks,
        'case_count':len(CASES),
        'model_execution':False,
        'authority':False,
    }


def main()->int:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='cmd',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--jobs-output',required=True);prep.add_argument('--expectations-output',required=True)
    sub.add_parser('self-test')
    args=p.parse_args()
    if args.cmd=='self-test':
        out=self_test();print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if out['pre_independent_qualification_contract']=='PASS' else 1
    Path(args.jobs_output).write_text(json.dumps(build_semantic_jobs(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Path(args.expectations_output).write_text(json.dumps(expectation_manifest(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__':raise SystemExit(main())
