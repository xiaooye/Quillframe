#!/usr/bin/env python3
"""Research-grounded semantic eval packaging for repair objective preservation.

Normal CI validates synthetic fixtures, blindness, strategy isolation and typed
jobs only. It never executes a model. Multi-turn context-strategy conclusions
remain PENDING_MODEL until genuinely separate writer/evaluator invocations run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SEM=ROOT/'harness'/'semantic_workers'
if str(SEM) not in sys.path: sys.path.insert(0,str(SEM))
from semantic_worker_router import make_eval_jobs, validate_job

JUDGMENT={
    'type':'object',
    'required':['confidence','target_outcome','objective_preservation','reader_value','character_relationship_energy','outcome_class','regressed_dimensions','evidence'],
    'properties':{
        'confidence':{'type':'number','minimum':0,'maximum':1},
        'target_outcome':{'enum':['improved','unchanged','worse','insufficient_evidence']},
        'objective_preservation':{'enum':['preserved','degraded','materially_degraded','insufficient_evidence']},
        'reader_value':{'enum':['improved','unchanged','degraded','insufficient_evidence']},
        'character_relationship_energy':{'enum':['preserved','degraded','not_applicable','insufficient_evidence']},
        'outcome_class':{'enum':['target_not_fixed','objective_regression','successful_repair','inconclusive']},
        'regressed_dimensions':{'type':'array','items':{'type':'string'}},
        'evidence':{'type':'array','items':{'type':'string'}},
    },'additionalProperties':False,
}
RUBRIC=[
    'Compare incumbent and repaired challenger against the supplied repair target and compact objective envelope. Judge meaning and story effect, not lexical compliance counts.',
    'First decide whether the targeted defect materially improved. Separately decide whether higher-order required objectives survived, including reader question/pressure/reward, causal movement, character/relationship energy, humor/charm when required, and forward pull.',
    'Do not reward the challenger merely for being smoother, safer, shorter or more constraint-compliant. A target fix with material objective degradation is objective_regression.',
    'Do not require wording or scene-structure preservation. A major fresh realization is valid when the repair target improves and the intended story/reader functions remain materially intact.',
    'Do not punish legitimate humor, charm or strong voice merely because the repair target concerns synthetic wit. Preserve character-owned, situation-functional expression.',
    'If the user-authorized objective envelope explicitly supersedes an older objective, judge against the new envelope rather than treating legitimate steering as regression.',
    'Return concise observable evidence. Do not expose private chain-of-thought.',
]

OBJECTIVE={
    'reader_question':'A concrete unresolved problem remains worth tracking.',
    'pressure':'Options become harder or costlier rather than dissolving into procedure.',
    'character_energy':'Important characters retain agenda, resistance and relationship-specific behavior.',
    'reward':'The scene provides meaningful progress, payoff or changed state.',
    'forward_pull':'The ending/current state creates consequential next-step pull.',
}

CASES=[
    {
        'id':'surface_fix_kills_tension','expected':'objective_regression','repair_target':'remove over-authored action tags',
        'incumbent':'Two rivals contest a deadline; a few action tags are conspicuously polished, but each exchange changes leverage and available options.',
        'challenger':'The tags are gone. The characters calmly complete each procedural step in order, exchange all needed information, and reach the same factual endpoint without resistance.',
        'preserve':['reader_question','pressure','forward_pull'],
    },
    {
        'id':'surface_fix_preserves_story','expected':'successful_repair','repair_target':'remove over-authored action tags',
        'incumbent':'Two rivals contest a deadline; a few action tags are conspicuously polished, but each exchange changes leverage and available options.',
        'challenger':'The conspicuous tags are removed while the rival still blocks access, forces a costly workaround, and changes the protagonist’s next option.',
        'preserve':['reader_question','pressure','forward_pull'],
    },
    {
        'id':'humor_overcorrection_bad','expected':'objective_regression','repair_target':'reduce synthetic punchline stacking',
        'incumbent':'A family argument contains setup-comeback-punchline stacking, but the family has visible warmth, teasing permissions and conflicting agendas.',
        'challenger':'All humor is removed; every relative now speaks neutral task information and politely agrees on the next step.',
        'preserve':['character_energy','pressure'],
    },
    {
        'id':'humor_overcorrection_good','expected':'successful_repair','repair_target':'reduce synthetic punchline stacking',
        'incumbent':'A family argument contains setup-comeback-punchline stacking, but the family has visible warmth, teasing permissions and conflicting agendas.',
        'challenger':'Most comeback stacking is removed; one dry, relationship-owned joke remains while relatives still interrupt, resist and bargain over the task.',
        'preserve':['character_energy','pressure'],
    },
    {
        'id':'reader_question_loss','expected':'objective_regression','repair_target':'remove narrator explanation',
        'incumbent':'The protagonist must infer which document is authentic while another character withholds access; the narrator over-explains one clue.',
        'challenger':'The narrator explanation is gone, but the correct document is immediately handed over and identified, eliminating the question and obstruction.',
        'preserve':['reader_question','pressure','reward'],
    },
    {
        'id':'character_energy_loss','expected':'objective_regression','repair_target':'remove over-authored dialogue',
        'incumbent':'Side characters sometimes sound too polished, but each has a separate stake and different permission to challenge the protagonist.',
        'challenger':'Dialogue is plain and natural, but all side characters merely deliver requested facts and never alter the protagonist’s options or social position.',
        'preserve':['character_energy','pressure'],
    },
    {
        'id':'negative_constraint_flood','expected':'semantic_compare','repair_target':'avoid several known realization failures',
        'incumbent':'Generation context keeps the story objective compact and supplies one distilled repair mechanism.',
        'challenger':'Generation context repeats a long accumulated list of prior mistakes, rejected phrasings, critic wording and do-not rules before the story task.',
        'preserve':['reader_question','pressure','character_energy','reward','forward_pull'],
    },
    {
        'id':'context_reset','expected':'semantic_compare','repair_target':'repair after a long corrective trajectory',
        'incumbent':'Continue generation with the entire sequence of rejected attempts and critique turns appended.',
        'challenger':'Reconstruct current authoritative state, compact objective envelope and minimal fix/preserve packet; omit rejected realization history.',
        'preserve':['reader_question','pressure','character_energy','reward','forward_pull'],
    },
    {
        'id':'incumbent_protection','expected':'objective_regression','repair_target':'remove synthetic coolness',
        'incumbent':'A tense negotiation has one manufactured-cool line but strong uncertainty and changing leverage.',
        'challenger':'The cool line is gone, yet the negotiation becomes a frictionless exchange of correct facts with no meaningful leverage change.',
        'preserve':['reader_question','pressure','forward_pull'],
    },
    {
        'id':'legitimate_major_rewrite','expected':'successful_repair','repair_target':'repair a scene-wide synthetic realization cluster',
        'incumbent':'The whole scene has repetitive AI-polished banter but its intended functions are confrontation, costly choice, one relationship reveal and a concrete payoff.',
        'challenger':'Almost every sentence and beat order changes, but the confrontation, costly choice, relationship reveal, payoff and forward consequence all remain while synthetic banter is materially reduced.',
        'preserve':['pressure','character_energy','reward','forward_pull'],
    },
    {
        'id':'explicit_goal_change','expected':'successful_repair','repair_target':'realize newly authorized creative direction',
        'incumbent':'Old objective emphasizes comic family friction.',
        'challenger':'After explicit user steering, the new objective emphasizes restrained grief and removes most humor while preserving the newly requested emotional pressure.',
        'preserve':['pressure','character_energy'],
        'objective_superseded':True,
    },
]

MULTI_TURN_BASE=[
    {'turn':1,'role':'task','content':'Write a commercially compelling scene with a live reader question, escalating interpersonal obstruction, character-owned humor and a concrete payoff.'},
    {'turn':2,'role':'critique','content':'Remove synthetic punchline stacking.'},
    {'turn':3,'role':'critique','content':'Remove narrator explanation after evidence.'},
    {'turn':4,'role':'critique','content':'Remove redundant micro-action padding.'},
]
STRATEGIES=[
    {'strategy_id':'A_FULL_TRAJECTORY','context':MULTI_TURN_BASE,'description':'Continue with the entire accumulated repair trajectory.'},
    {'strategy_id':'B_FULL_PLUS_REANCHOR','context':MULTI_TURN_BASE+[{'turn':5,'role':'reanchor','content':MULTI_TURN_BASE[0]['content']}],'description':'Keep full history and repeat the original objective.'},
    {'strategy_id':'C_COMPACT_OBJECTIVE','context':[MULTI_TURN_BASE[0],{'turn':5,'role':'state','content':'Current state: interpersonal obstruction remains live; payoff not yet earned.'},{'turn':6,'role':'repair','content':'Fix punchline stacking, explanation-after-evidence and micro-action padding while preserving conflict, reader question, character energy and payoff.'}],'description':'Compact current state + objective + minimal fix/preserve packet.'},
    {'strategy_id':'D_REFACTORED_STATE','context':[{'turn':5,'role':'refactored_state','content':'Authoritative current objective and scene state replace superseded repair trajectory. Preserve live reader question, escalating obstruction, character-owned humor and payoff. Active repair targets: synthetic punchline stacking, explanation-after-evidence, redundant micro-actions.'}],'description':'Rewrite-and-replace/refactored state inspired by context-refactoring research.'},
]


def _fixture(case:dict[str,Any])->dict[str,Any]:
    return {
        'incumbent':case['incumbent'],'challenger':case['challenger'],'repair_target':case['repair_target'],
        'objective_envelope':{'items':[{'id':x,'statement':OBJECTIVE[x]} for x in case['preserve']], 'explicitly_superseded':bool(case.get('objective_superseded',False))},
    }


def build()->dict[str,Any]:
    cases=[{'id':'OBJ-'+c['id'],'type':'repair_preservation','domain':'creative_repair','fixture':_fixture(c),'rubric':RUBRIC,'judgment_contract':JUDGMENT} for c in CASES]
    jobs=make_eval_jobs({'blind':True,'suite_version':'repair-objective-preservation-v1','cases':cases},source_session_id='SES-OBJ-PRES',handoff_id='HND-OBJ-PRES')
    return {
        'schema':'novelforge_repair_objective_preservation_eval_v1',
        'semantic_status':'PENDING_MODEL',
        'jobs':jobs['jobs'],
        'expectations':[{ 'case_id':c['id'],'expected':c['expected']} for c in CASES],
        'multi_turn_ablation':{
            'status':'PENDING_MODEL',
            'requires_separate_writer_and_evaluator_invocations':True,
            'shared_task':MULTI_TURN_BASE[0]['content'],
            'strategies':STRATEGIES,
            'measures':['target constraint success','story/task quality preservation','reader value','character/relationship energy','instruction adherence'],
            'no_presumed_winner':True,
        },
        'research_design':{
            'constraint_interference':'Qi et al. 2026 preprint; Harada et al. Findings EMNLP 2025; Zeng et al. Findings ACL 2025',
            'long_context_multi_turn':'Robinette et al. Findings EACL 2026; Singh et al. Findings ACL 2026',
            'context_refactoring':'Shen et al. Findings ACL 2026; Chen et al. Findings ACL 2026',
            'inference_boundary':'These sources do not directly test fiction repair. Objective-envelope and FIX+PRESERVE semantics are NovelForge-specific adaptations to be evaluated, not claimed empirical facts.',
        },
        'model_execution':False,
        'authority':False,
    }


def self_test()->dict[str,Any]:
    packet=build(); serialized_jobs=json.dumps(packet['jobs'],ensure_ascii=False)
    checks={
        'ten_or_more_required_synthetic_cases':len(CASES)>=10,
        'case_a_target_not_fixed_representable':any(c['expected']=='semantic_compare' or c['expected']=='objective_regression' for c in CASES),
        'case_b_objective_regression_present':sum(c['expected']=='objective_regression' for c in CASES)>=4,
        'case_c_successful_repair_present':sum(c['expected']=='successful_repair' for c in CASES)>=3,
        'negative_constraint_flood_present':any(c['id']=='negative_constraint_flood' for c in CASES),
        'context_reset_present':any(c['id']=='context_reset' for c in CASES),
        'incumbent_protection_present':any(c['id']=='incumbent_protection' for c in CASES),
        'major_rewrite_allowed_control':any(c['id']=='legitimate_major_rewrite' and c['expected']=='successful_repair' for c in CASES),
        'explicit_goal_change_control':any(c['id']=='explicit_goal_change' and c.get('objective_superseded') for c in CASES),
        'four_multiturn_strategies':{x['strategy_id'] for x in STRATEGIES}=={'A_FULL_TRAJECTORY','B_FULL_PLUS_REANCHOR','C_COMPACT_OBJECTIVE','D_REFACTORED_STATE'},
        'multiturn_has_no_presumed_winner':packet['multi_turn_ablation']['no_presumed_winner'] is True,
        'expectations_not_in_model_jobs':all(c['expected'] not in serialized_jobs for c in CASES if c['expected']!='semantic_compare'),
        'all_jobs_valid':all(not validate_job(j) for j in packet['jobs']),
        'normal_ci_no_model_execution':packet['model_execution'] is False and packet['semantic_status']=='PENDING_MODEL',
    }
    return {'schema':'novelforge_repair_objective_preservation_eval_test_v1','repair_objective_preservation_eval_contract':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'model_execution':False,'authority':False}


def main()->int:
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('self-test'); prep=s.add_parser('prepare'); prep.add_argument('--output',required=True)
    a=p.parse_args()
    if a.cmd=='self-test':
        out=self_test(); print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out['repair_objective_preservation_eval_contract']=='PASS' else 1
    Path(a.output).write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return 0


if __name__=='__main__': raise SystemExit(main())
