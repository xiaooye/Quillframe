#!/usr/bin/env python3
"""Paired semantic ablation for pre-independent candidate qualification.

Normal CI only prepares and validates fingerprint-bound jobs. It never executes
an LLM. Independent semantic execution is intentionally separate; absent an
eligible reviewer the truthful status is PENDING_MODEL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SEM=ROOT/'harness'/'semantic_workers'
if str(SEM) not in sys.path:sys.path.insert(0,str(SEM))
from semantic_worker_router import make_eval_jobs, validate_job

PAIRS=[
    {
        'pair_id':'functional_overauthored',
        'fixture':{
            'text':'A parent needs to stop an injured child from lifting a box, but delivers a polished, symmetrical, quote-ready joke mainly optimized to look charming.',
            'speaker_context':'Established as practical, tired, close family relationship, immediate safety goal.',
        },
        'observation':'The AFTER condition should notice that narrative/social function can coexist with visibly over-authored realization.',
    },
    {
        'pair_id':'legitimate_wit_negative_control',
        'fixture':{
            'text':'A quick-witted negotiator uses one concise joke to expose the other party’s bluff and force a concrete concession.',
            'speaker_context':'Established witty voice; public negotiation; joke directly advances leverage.',
        },
        'observation':'The AFTER condition must not flatten legitimately witty, consequential, character-owned speech.',
    },
    {
        'pair_id':'punchline_stacking_cluster',
        'fixture':{
            'text':'Three family turns form setup → clever answer → clever comeback → narrator witty gloss → another punchline. Each line is plausible alone; the block reads like optimized sitcom banter.',
            'speaker_context':'Ordinary family task under time pressure; no reason for every participant to optimize a comeback.',
        },
        'observation':'The AFTER condition should catch cluster-level synthetic banter even if each sentence has a relationship function.',
    },
    {
        'pair_id':'narrator_cleverness',
        'fixture':{
            'text':'A child forgets an ordinary promise and the narrator reframes it as a witty debt-collection metaphor, although the POV has no financial framing and no decision changes.',
            'speaker_context':'Close third-person child POV; narrator otherwise transparent.',
        },
        'observation':'The AFTER condition should test narrator/POV ownership rather than rewarding flavor automatically.',
    },
    {
        'pair_id':'known_regression_recurrence',
        'fixture':{
            'text':'A later candidate repeats an already-modeled punchline-stacking mechanism after the same failure was previously identified and activated as regression evidence.',
            'speaker_context':'The mechanism is known; literal witty language remains legal when contextually owned.',
            'known_regression':'synthetic_punchline_stacking',
        },
        'observation':'The AFTER condition should treat a semantically applicable known recurrence as a pre-user quality-loop failure rather than a fresh preference discovery.',
    },
]

BEFORE_RUBRIC=[
    'Judge the supplied prose unit only for whether it performs at least one narrative/social function such as information, relationship, humor, pressure, timing or voice.',
    'If a meaningful function exists, accept unless the unit is literally redundant. Do not assess whether the wording is over-authored, quote-ready, audience-optimized or unnaturally polished for the speaker.',
    'Return a concise verdict with observable evidence only.',
]
AFTER_RUBRIC=[
    'Judge the same prose at three layers: FUNCTION, OWNERSHIP, and NATURAL REALIZATION.',
    'A unit may have valid narrative/social function and still fail when its wording does not belong to the POV/speaker or is implausibly complete, symmetrical, clever, quote-ready, punchline-first or audience-optimized for the immediate social purpose.',
    'Check local block/cluster rhythm, including punchline stacking and repeated witty comebacks; do not rely on lexical bans or punish legitimate witty/charismatic speech when it is purpose-first, character-owned, situation-appropriate and consequential.',
    'When known regression context is supplied, determine semantic applicability; a recurrence is not a new preference discovery. Return a concise verdict with observable evidence only.',
]
JUDGMENT={
    'type':'object','required':['confidence','verdict','evidence'],'properties':{
        'confidence':{'type':'number','minimum':0,'maximum':1},
        'verdict':{'enum':['accept','reject']},
        'evidence':{'type':'array','items':{'type':'string'}},
    },'additionalProperties':False,
}


def build()->dict[str,Any]:
    cases=[]
    for pair in PAIRS:
        for condition,rubric in [('BEFORE_FUNCTION_ONLY',BEFORE_RUBRIC),('AFTER_THREE_LAYER',AFTER_RUBRIC)]:
            cases.append({
                'id':f"QUAL-ABL-{pair['pair_id']}-{condition}",
                'type':'ablation',
                'domain':'pre_independent_qualification',
                'fixture':{'pair_id':pair['pair_id'],'condition':condition,**pair['fixture']},
                'rubric':rubric,
                'judgment_contract':JUDGMENT,
            })
    queue={'blind':True,'suite_version':'pre-independent-qualification-v1','cases':cases}
    jobs=make_eval_jobs(queue,source_session_id='SES-QUAL-ABLATION',handoff_id='HND-QUAL-ABLATION')
    return {
        'schema':'novelforge_pre_independent_qualification_ablation_v1',
        'semantic_status':'PENDING_MODEL',
        'manager_self_judgment_allowed':False,
        'paired_conditions':['BEFORE_FUNCTION_ONLY','AFTER_THREE_LAYER'],
        'jobs':jobs['jobs'],
        'pair_metadata':[{'pair_id':p['pair_id'],'observation':p['observation']} for p in PAIRS],
        'model_execution':False,
    }


def self_test()->dict[str,Any]:
    packet=build();jobs=packet['jobs']
    by_pair:dict[str,set[str]]={}
    for job in jobs:
        assert not validate_job(job),validate_job(job)
        fixture=job['input']['fixture'];by_pair.setdefault(fixture['pair_id'],set()).add(fixture['condition'])
    hidden=all('observation' not in json.dumps(job,ensure_ascii=False) for job in jobs)
    unique=len({j['input_fingerprint'] for j in jobs})==len(jobs)
    checks={
        'five_pairs':len(by_pair)==5,
        'two_conditions_per_pair':all(v=={'BEFORE_FUNCTION_ONLY','AFTER_THREE_LAYER'} for v in by_pair.values()),
        'fingerprint_bound_unique_jobs':unique,
        'expected_observation_hidden_from_jobs':hidden,
        'negative_wit_control_present':'legitimate_wit_negative_control' in by_pair,
        'known_regression_control_present':'known_regression_recurrence' in by_pair,
        'manager_self_judgment_forbidden':packet['manager_self_judgment_allowed'] is False,
        'missing_model_state_truthful':packet['semantic_status']=='PENDING_MODEL',
        'normal_ci_model_execution':packet['model_execution'] is False,
    }
    return {
        'schema':'novelforge_pre_independent_qualification_ablation_test_v1',
        'pre_independent_qualification_ablation_contract':'PASS' if all(checks.values()) else 'FAIL',
        'checks':checks,
        'model_execution':False,
        'authority':False,
    }


def main()->int:
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--output',required=True)
    sub.add_parser('self-test');args=p.parse_args()
    if args.cmd=='self-test':
        out=self_test();print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if out['pre_independent_qualification_ablation_contract']=='PASS' else 1
    Path(args.output).write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return 0

if __name__=='__main__':raise SystemExit(main())
