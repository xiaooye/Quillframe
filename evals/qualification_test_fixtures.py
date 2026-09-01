#!/usr/bin/env python3
"""Synthetic-only helpers for deterministic qualification contract tests.

Never use these fixtures as production evidence. They exist solely so CI can
exercise hard dispatch/readiness bindings without live model execution.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'harness'/'semantic_workers',ROOT/'quality'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from candidate_qualification import evaluate as qualify
from harness.context_runtime import fingerprint
from semantic_worker_router import make_contract_job

RULES=[{'id':'HF-TEST','authority':'framework','statement':'Synthetic CI rule material only.'}]


def _author_objectives()->dict[str,Any]:
    value={
        'schema':'quillframe_current_author_objectives_v1',
        'items':[{
            'objective_id':'OBJ-CI','statement':'Preserve the bounded synthetic candidate.',
            'source_refs':['fixture:ci'],'hard':True,
        }],
        'source_fingerprint':fingerprint('fixture:ci'),
        'priority':'current_explicit_author_direction','authority':False,
    }
    value['objectives_fingerprint']=fingerprint(value)
    return value


def _binding(contract_id:str, subject_id:str, fp:str, judgment:dict[str,Any])->dict[str,Any]:
    payload={'candidate_fingerprint':fp,'candidate_text':'Synthetic deterministic CI candidate.'}
    if contract_id=='quality.candidate_self_audit':
        payload.update({'rule_material':RULES,'regression_evidence':[],'profile_constraints':[],'voice_constraints':[],
                        'reader_grip':'very_high','author_objectives':_author_objectives()})
    elif contract_id=='reader.engagement_audit':
        payload['reader_grip']='very_high'
    job=make_contract_job(contract_id,subject_id,payload,source_session_id='SES-CI-MANAGER')
    result={
        'job_id':job['job_id'],'subject_id':job['subject_id'],'kind':job['kind'],'input_fingerprint':job['input_fingerprint'],
        'status':'completed','worker':{'provider':'self_test','model_or_reviewer':'synthetic-ci-fixture'},
        'judgment':judgment,'proposals':[],'errors':[],
    }
    return {'job':job,'result':result}


def make_qualified_receipt(fp:str, subject_id:str='CH-CI')->dict[str,Any]:
    audit=_binding('quality.candidate_self_audit',subject_id,fp,{
        'confidence':1.0,'result':'pass','report':'Synthetic CI pass.',
        'dimensions':{'surface':'pass','regression':'pass','character_or_ownership':'pass','natural_realization':'pass','cluster':'pass'},
        'findings':[],'evidence_refs':['synthetic:ci'],
        'objective_assessments':[{'objective_id':'OBJ-CI','status':'met','evidence_refs':['synthetic:ci'],
                                  'impact_scope':'whole_candidate','repair_route':'no_change',
                                  'report':'The bounded synthetic objective is met.'}],
    })
    reader=_binding('reader.engagement_audit',subject_id,fp,{
        'confidence':1.0,'result':'pass','report':'Synthetic CI reader pass.',
        'strongest_positive':'Synthetic control.','strongest_problem':None,'evidence_refs':['synthetic:ci'],
    })
    return qualify({
        'candidate_fingerprint':fp,'subject_id':subject_id,'repair_cycle':0,
        'self_audit':{'status':'pass','semantic_binding':audit},
        'reader_engagement':{'status':'pass','semantic_binding':reader},
        'continuity':{'status':'pass','candidate_fingerprint':fp,'receipt_fingerprint':'sha256:'+'c'*64,'evidence_refs':['synthetic:continuity']},
    })
