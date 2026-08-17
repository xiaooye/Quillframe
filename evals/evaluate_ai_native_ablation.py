#!/usr/bin/env python3
"""Fingerprint-bound gate for paired AI-native semantic ablations."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from collections import Counter
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; ABL=ROOT/'evals/ai_native_ablation_manifest.json'; EVAL=ROOT/'evals/eval_manifest.json'; SEM=ROOT/'harness/semantic_workers'
if str(SEM) not in sys.path:sys.path.insert(0,str(SEM))
from build_judge_queue import build as build_blind_queue
from evaluation_execution_identity import fingerprint,validate_identity
from registered_contract_binding import validate_registered_job
from semantic_worker_router import make_contract_job,make_eval_jobs,validate_result
PACKET='novelforge_ai_native_ablation_observations_v2'; EVIDENCE='novelforge_ai_native_ablation_evidence_v2'; CONTRACT='quality.ablation_compare'
REL={'INCUMBENT_BETTER','CHALLENGER_BETTER','NO_MATERIAL_DIFFERENCE','INCONCLUSIVE'}; ORD={'INCUMBENT_FIRST','CHALLENGER_FIRST'}
OBS_KEYS={'pair_id','replicate_id','presentation_order','candidate_fingerprint','condition_execution_identity','incumbent_result','challenger_result','pair_review_execution_identity','pair_review_job','pair_review_result'}
def load(p:Path)->Any:return json.loads(p.read_text(encoding='utf-8'))
def dump(v:Any,p:Path|None=None)->None:
 s=json.dumps(v,ensure_ascii=False,indent=2)+'\n'; p.write_text(s,encoding='utf-8') if p else print(s,end='')
def cfp(text:str)->str:return fingerprint({'candidate_text':text})
def json_file_fp(v:Any)->str:return 'sha256:'+hashlib.sha256((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
def cases()->dict[str,dict[str,Any]]:
 out={}
 for row in load(EVAL).get('cases',[]):
  if isinstance(row.get('file'),str):
   c=load(EVAL.parent/row['file']); cid=c.get('id')
   if isinstance(cid,str):out[cid]=c
 return out
def eval_ctx()->tuple[dict[str,Any],dict[str,dict[str,Any]],str]:
 q=build_blind_queue(EVAL); jobs={j['subject_id']:j for j in make_eval_jobs(q).get('jobs',[])}; return q,jobs,json_file_fp(q)
def manifest_errors(m:dict[str,Any],cs:dict[str,dict[str,Any]])->list[str]:
 e=[]; p=m.get('decision_protocol',{})
 if m.get('schema')!='novelforge_ai_native_ablation_manifest_v1':e.append('manifest schema mismatch')
 if m.get('model_execution_required_for_semantic_outcomes') is not True:e.append('model execution must be required')
 if m.get('manager_self_judgment_allowed') is not False:e.append('manager self-judgment must be forbidden')
 for k,v in [('pair_review_contract',CONTRACT),('required_condition_replicates',3),('reviews_per_replicate',2),('required_pair_reviews',6),('require_exact_counterbalance',True)]:
  if p.get(k)!=v:e.append(f'{k} mismatch')
 if set(p.get('semantic_relations',[]))!=REL:e.append('semantic relation enum mismatch')
 seen=set()
 for pair in m.get('pairs',[]):
  pid=pair.get('id')
  if not isinstance(pid,str) or not pid:e.append('pair id required');continue
  if pid in seen:e.append(f'duplicate pair id: {pid}')
  seen.add(pid)
  if pair.get('simpler_arm') not in {'incumbent','challenger'}:e.append(f'{pid}: invalid simpler_arm')
  if not isinstance(pair.get('observe'),list) or not pair['observe']:e.append(f'{pid}: observe criteria required')
  a=cs.get(pair.get('incumbent_case')); b=cs.get(pair.get('challenger_case'))
  if not a or not b:e.append(f'{pid}: missing case');continue
  af=a.get('fixture',{}); bf=b.get('fixture',{}); ref=pair.get('same_candidate_ref')
  if af.get('candidate_ref')!=ref or bf.get('candidate_ref')!=ref:e.append(f'{pid}: candidate_ref mismatch')
  if not isinstance(af.get('candidate_text'),str) or af.get('candidate_text')!=bf.get('candidate_text'):e.append(f'{pid}: candidate_text mismatch')
 return e
def projection(i:dict[str,Any],*,condition:bool)->dict[str,Any]:
 ev=i.get('evaluation',{}); keys=['suite_version','domain','blind','capabilities_fingerprint','harness_fingerprint']
 if condition:keys.append('queue_fingerprint')
 return {'candidate':i.get('candidate'),'reviewer':i.get('reviewer'),'evaluation':{k:ev.get(k) for k in keys},'environment':i.get('environment'),'resource_budget':i.get('resource_budget')}
def worker_matches(i:dict[str,Any],r:dict[str,Any])->bool:
 return r.get('worker',{}).get('provider')==i.get('reviewer',{}).get('provider') and r.get('worker',{}).get('model_or_reviewer')==i.get('reviewer',{}).get('model_id')
def invocation(r:dict[str,Any])->str|None:
 ex=r.get('execution') or {}; w=r.get('worker') or {}; vals=[ex.get('worker_session_id'),ex.get('attempt_id'),w.get('run_reference')]; vals=[str(x) for x in vals if x]; return '|'.join(vals) if vals else None
def subject(pid:str,rep:str,order:str)->str:return f"ABL-COMPARE-{pid}-{rep}-{'INC-FIRST' if order=='INCUMBENT_FIRST' else 'CHAL-FIRST'}"
def condition(label:str,job:dict[str,Any],result:dict[str,Any])->dict[str,Any]:return {'condition_id':label,'input_fingerprint':job['input_fingerprint'],'result_fingerprint':fingerprint(result),'judgment':result['judgment']}
def review_payload(pair:dict[str,Any],rep:str,order:str,cand:str,ij:dict[str,Any],cj:dict[str,Any],ir:dict[str,Any],cr:dict[str,Any])->dict[str,Any]:
 inc=condition('A' if order=='INCUMBENT_FIRST' else 'B',ij,ir); chal=condition('B' if order=='INCUMBENT_FIRST' else 'A',cj,cr)
 a=inc if inc['condition_id']=='A' else chal; b=chal if chal['condition_id']=='B' else inc
 return {'comparison_id':subject(pair['id'],rep,order),'candidate_fingerprint':cand,'condition_a':a,'condition_b':b,'observation_criteria':list(pair['observe'])}
def map_relation(order:str,r:str)->str:
 if r in {'NO_MATERIAL_DIFFERENCE','INCONCLUSIVE'}:return r
 if order=='INCUMBENT_FIRST':return 'INCUMBENT_BETTER' if r=='A_BETTER' else 'CHALLENGER_BETTER'
 return 'CHALLENGER_BETTER' if r=='A_BETTER' else 'INCUMBENT_BETTER'
def regression(pair:dict[str,Any],order:str,mark:str)->str:
 if mark in {'NEITHER','UNCLEAR'}:return mark
 arm='incumbent' if (order=='INCUMBENT_FIRST' and mark=='A') or (order=='CHALLENGER_FIRST' and mark=='B') else 'challenger'
 return 'SIMPLER' if arm==pair['simpler_arm'] else 'OTHER'
def arm_errors(pair:dict[str,Any],jobs:dict[str,dict[str,Any]],identity:dict[str,Any],ir:dict[str,Any],cr:dict[str,Any])->list[str]:
 e=[]
 for side,jid,res in [('incumbent',pair['incumbent_case'],ir),('challenger',pair['challenger_case'],cr)]:
  job=jobs.get(jid)
  if not job:e.append(f'{side} expected job missing');continue
  if not isinstance(res,dict):e.append(f'{side} result required');continue
  e += [f'{side} result: {x}' for x in validate_result(job,res)]
  if res.get('status')!='completed':e.append(f'{side} result must be completed')
  if not worker_matches(identity,res):e.append(f'{side} result worker/condition identity mismatch')
  if not invocation(res):e.append(f'{side} result missing independent invocation lineage')
 return e
def build_review_job(pair:dict[str,Any],rep:str,order:str,cs:dict[str,dict[str,Any]],jobs:dict[str,dict[str,Any]],ir:dict[str,Any],cr:dict[str,Any])->dict[str,Any]:
 cand=cfp(cs[pair['incumbent_case']]['fixture']['candidate_text']); payload=review_payload(pair,rep,order,cand,jobs[pair['incumbent_case']],jobs[pair['challenger_case']],ir,cr)
 return make_contract_job(CONTRACT,subject(pair['id'],rep,order),payload)
def validate_obs(o:dict[str,Any],pair:dict[str,Any],cs:dict[str,dict[str,Any]],jobs:dict[str,dict[str,Any]],queue_fp:str)->tuple[list[str],dict[str,Any]|None]:
 pid=pair['id']; e=[]; extra=sorted(set(o)-OBS_KEYS); missing=sorted(OBS_KEYS-set(o))
 if extra:e.append(f'{pid}: unexpected observation fields: {", ".join(extra)}')
 if missing:return e+[f'{pid}: missing observation fields: {", ".join(missing)}'],None
 rep=o.get('replicate_id'); order=o.get('presentation_order')
 if o.get('pair_id')!=pid:e.append(f'{pid}: pair_id mismatch')
 if not isinstance(rep,str) or not re.fullmatch(r'R[1-3]',rep):e.append(f'{pid}: replicate_id must be R1..R3')
 if order not in ORD:e.append(f'{pid}: invalid presentation_order')
 cand=cfp(cs[pair['incumbent_case']]['fixture']['candidate_text'])
 if o.get('candidate_fingerprint')!=cand:e.append(f'{pid}: candidate fingerprint mismatch')
 ci=o.get('condition_execution_identity'); ri=o.get('pair_review_execution_identity')
 if not isinstance(ci,dict):e.append(f'{pid}: condition execution identity required')
 else:
  e += [f'{pid}: condition identity: {x}' for x in validate_identity(ci)]
  if ci.get('evaluation',{}).get('queue_fingerprint')!=queue_fp:e.append(f'{pid}: condition queue fingerprint does not bind current blind queue')
 if isinstance(ci,dict):e += [f'{pid}: {x}' for x in arm_errors(pair,jobs,ci,o.get('incumbent_result'),o.get('challenger_result'))]
 if not isinstance(ri,dict):e.append(f'{pid}: pair review execution identity required')
 else:
  e += [f'{pid}: pair review identity: {x}' for x in validate_identity(ri)]
  if isinstance(ci,dict) and ri.get('candidate')!=ci.get('candidate'):e.append(f'{pid}: pair review candidate/framework identity mismatch')
  if isinstance(ci,dict) and ri.get('identity_fingerprint')==ci.get('identity_fingerprint'):e.append(f'{pid}: pair review must use separate execution identity')
 job=o.get('pair_review_job'); result=o.get('pair_review_result'); derived=None
 if not isinstance(job,dict):e.append(f'{pid}: pair review job required')
 else:
  e += [f'{pid}: pair review job: {x}' for x in validate_registered_job(job)]
  if isinstance(rep,str) and order in ORD and job.get('subject_id')!=subject(pid,rep,order):e.append(f'{pid}: pair review subject mismatch')
  if job.get('input',{}).get('model_contract_id')!=CONTRACT:e.append(f'{pid}: pair review contract mismatch')
  if isinstance(rep,str) and order in ORD and isinstance(o.get('incumbent_result'),dict) and isinstance(o.get('challenger_result'),dict):
   expected=review_payload(pair,rep,order,cand,jobs[pair['incumbent_case']],jobs[pair['challenger_case']],o['incumbent_result'],o['challenger_result'])
   if job.get('input',{}).get('payload')!=expected:e.append(f'{pid}: pair review payload does not bind exact arm results/order')
 if not isinstance(result,dict):e.append(f'{pid}: pair review result required')
 elif isinstance(job,dict):
  e += [f'{pid}: pair review result: {x}' for x in validate_result(job,result)]
  if result.get('status')!='completed':e.append(f'{pid}: pair review result must be completed')
  if isinstance(ri,dict) and not worker_matches(ri,result):e.append(f'{pid}: pair review result worker/review identity mismatch')
  if not invocation(result):e.append(f'{pid}: pair review result missing independent invocation lineage')
 if not e:
  j=result['judgment']; rel=j.get('relation'); mark=j.get('regression_in')
  if rel not in {'A_BETTER','B_BETTER','NO_MATERIAL_DIFFERENCE','INCONCLUSIVE'}:e.append(f'{pid}: invalid pair relation')
  if mark not in {'A','B','NEITHER','UNCLEAR'}:e.append(f'{pid}: invalid regression marker')
  if not e:derived={'relation':map_relation(order,rel),'regression':regression(pair,order,mark),'evidence':list(j.get('evidence',[])),'condition_identity':ci['identity_fingerprint'],'review_identity':ri['identity_fingerprint'],'inc_result':fingerprint(o['incumbent_result']),'chal_result':fingerprint(o['challenger_result']),'review_job':job['input_fingerprint'],'review_result':fingerprint(result),'inc_invocation':invocation(o['incumbent_result']),'chal_invocation':invocation(o['challenger_result']),'review_invocation':invocation(result)}
 return e,derived
def decide(pair:dict[str,Any],rows:list[dict[str,Any]],p:dict[str,Any])->dict[str,Any]:
 base={'recommendation':'NO_CHANGE','simpler_arm_noninferior':None}; need=p['required_pair_reviews']
 if not rows:return {**base,'status':'PENDING_MODEL','reason':'no real semantic observations supplied'}
 if len(rows)!=need:return {**base,'status':'PENDING_MODEL','reason':f'need exactly {need} validated pair reviews'}
 cp=[projection(x['condition_execution_identity'],condition=True) for x in rows]; rp=[projection(x['pair_review_execution_identity'],condition=False) for x in rows]
 if any(x!=cp[0] for x in cp[1:]):return {**base,'status':'PENDING_MODEL','reason':'condition execution configuration drift'}
 if any(x!=rp[0] for x in rp[1:]):return {**base,'status':'PENDING_MODEL','reason':'pair review execution configuration drift'}
 grouped={r:[x for x in rows if x['replicate_id']==r] for r in {'R1','R2','R3'}}
 if any(len(v)!=2 or {x['presentation_order'] for x in v}!=ORD for v in grouped.values()):return {**base,'status':'PENDING_MODEL','reason':'each of R1..R3 requires one review in each order'}
 cond_ids=[]; review_ids=[]; arm_inv=[]; review_inv=[]
 for rep,vals in grouped.items():
  c={x['derived']['condition_identity'] for x in vals}; i={x['derived']['inc_result'] for x in vals}; h={x['derived']['chal_result'] for x in vals}
  if len(c)!=1 or len(i)!=1 or len(h)!=1:return {**base,'status':'PENDING_MODEL','reason':f'{rep} reviews must share exact arm outputs'}
  cond_ids.append(next(iter(c))); review_ids += [x['derived']['review_identity'] for x in vals]
  ii={x['derived']['inc_invocation'] for x in vals}; ci={x['derived']['chal_invocation'] for x in vals}
  if len(ii)!=1 or len(ci)!=1 or next(iter(ii))==next(iter(ci)):return {**base,'status':'PENDING_MODEL','reason':f'{rep} arm invocations are not independent'}
  arm_inv += [next(iter(ii)),next(iter(ci))]; review_inv += [x['derived']['review_invocation'] for x in vals]
 if len(set(cond_ids))!=3:return {**base,'status':'PENDING_MODEL','reason':'condition replicate execution identity reused'}
 if len(set(review_ids))!=6 or set(review_ids)&set(cond_ids):return {**base,'status':'PENDING_MODEL','reason':'pair review execution identity reused'}
 if len(set(arm_inv))!=6:return {**base,'status':'PENDING_MODEL','reason':'condition arm invocation reused across replicates'}
 if len(set(review_inv))!=6 or set(review_inv)&set(arm_inv):return {**base,'status':'PENDING_MODEL','reason':'pair review invocation lineage reused'}
 if Counter(x['presentation_order'] for x in rows)!=Counter({'INCUMBENT_FIRST':3,'CHALLENGER_FIRST':3}):return {**base,'status':'PENDING_MODEL','reason':'presentation order is not exactly counterbalanced 3:3'}
 regs=[x['derived']['regression'] for x in rows]
 if 'SIMPLER' in regs:return {'status':'KEEP','recommendation':'KEEP_CURRENT','reason':'confirmed regression in declared simpler arm','simpler_arm_noninferior':False}
 if 'UNCLEAR' in regs:return {**base,'status':'INCONCLUSIVE','reason':'regression evidence is unclear'}
 rel=[x['derived']['relation'] for x in rows]; counts=dict(Counter(rel))
 if 'INCONCLUSIVE' in counts:return {**base,'status':'INCONCLUSIVE','reason':'reviewer reported INCONCLUSIVE','relations':counts}
 simpler=pair['simpler_arm']; good={'NO_MATERIAL_DIFFERENCE','INCUMBENT_BETTER' if simpler=='incumbent' else 'CHALLENGER_BETTER'}; bad='CHALLENGER_BETTER' if simpler=='incumbent' else 'INCUMBENT_BETTER'
 if bad in rel and any(x in good for x in rel):return {**base,'status':'INCONCLUSIVE','reason':'stochastic pair judgments conflict','relations':counts}
 if all(x==bad for x in rel):return {'status':'KEEP','recommendation':'KEEP_CURRENT','reason':'all pair reviews judge the simpler arm semantically worse','relations':counts,'simpler_arm_noninferior':False}
 if all(x in good for x in rel):return {'status':'SIMPLIFY','recommendation':f'SIMPLIFY_TO_{simpler.upper()}','reason':'six independent counterbalanced reviews find the simpler arm non-inferior or better with no regression veto','relations':counts,'simpler_arm_noninferior':True}
 return {**base,'status':'INCONCLUSIVE','reason':'evidence does not satisfy decision protocol','relations':counts}
def evaluate(packet:dict[str,Any],m:dict[str,Any],cs:dict[str,dict[str,Any]])->dict[str,Any]:
 if packet.get('schema')!=PACKET:raise ValueError('packet schema mismatch')
 me=manifest_errors(m,cs)
 if me:raise ValueError('; '.join(me))
 _,jobs,qfp=eval_ctx(); pairs={x['id']:x for x in m['pairs']}; grouped={k:[] for k in pairs}; seen=set()
 for o in packet.get('observations',[]):
  if not isinstance(o,dict) or o.get('pair_id') not in pairs:raise ValueError('unknown/malformed observation')
  e,d=validate_obs(o,pairs[o['pair_id']],cs,jobs,qfp)
  if e:raise ValueError('; '.join(e))
  if d['review_job'] in seen:raise ValueError('duplicate pair review job fingerprint')
  seen.add(d['review_job']); grouped[o['pair_id']].append({**o,'derived':d})
 rows=[]
 for pid,pair in pairs.items():
  obs=grouped[pid]; dec=decide(pair,obs,m['decision_protocol']); text=cs[pair['incumbent_case']]['fixture']['candidate_text']
  rows.append({'pair_id':pid,'incumbent_case':pair['incumbent_case'],'challenger_case':pair['challenger_case'],'simpler_arm':pair['simpler_arm'],'complexity_basis':pair.get('complexity_basis'),'candidate_ref':pair['same_candidate_ref'],'candidate_fingerprint':cfp(text),'comparability':{'pair_review_count':len(obs),'required_pair_reviews':6,'condition_replicates':len({x['replicate_id'] for x in obs}),'required_condition_replicates':3,'exact_counterbalance':bool(obs) and Counter(x['presentation_order'] for x in obs)==Counter({'INCUMBENT_FIRST':3,'CHALLENGER_FIRST':3})},'semantic_evidence':{'complete':dec['status']!='PENDING_MODEL','source_contract':CONTRACT if obs else None},'provenance':{'blind_queue_fingerprint':qfp,'condition_execution_identities':[x['derived']['condition_identity'] for x in obs],'pair_review_execution_identities':[x['derived']['review_identity'] for x in obs],'pair_review_job_fingerprints':[x['derived']['review_job'] for x in obs],'pair_review_result_fingerprints':[x['derived']['review_result'] for x in obs],'incumbent_result_fingerprints':[x['derived']['inc_result'] for x in obs],'challenger_result_fingerprints':[x['derived']['chal_result'] for x in obs]},'decision':dec})
 out={'schema':EVIDENCE,'manifest_fingerprint':fingerprint(m),'blind_queue_fingerprint':qfp,'packet_fingerprint':fingerprint(packet),'pairs':rows};out['evidence_fingerprint']=fingerprint(out);return out
def prepare(m:dict[str,Any],cs:dict[str,dict[str,Any]])->dict[str,Any]:
 e=manifest_errors(m,cs)
 if e:raise ValueError('; '.join(e))
 _,jobs,qfp=eval_ctx(); plan=[]
 for pair in m['pairs']:
  text=cs[pair['incumbent_case']]['fixture']['candidate_text']; reps=[]
  for n in range(1,4):
   rep=f'R{n}'; reps.append({'replicate_id':rep,'review_subjects':[{'presentation_order':o,'subject_id':subject(pair['id'],rep,o)} for o in ('INCUMBENT_FIRST','CHALLENGER_FIRST')]})
  plan.append({'pair_id':pair['id'],'candidate_ref':pair['same_candidate_ref'],'candidate_fingerprint':cfp(text),'incumbent_case':pair['incumbent_case'],'challenger_case':pair['challenger_case'],'incumbent_input_fingerprint':jobs[pair['incumbent_case']]['input_fingerprint'],'challenger_input_fingerprint':jobs[pair['challenger_case']]['input_fingerprint'],'replicates':reps})
 return {'schema':PACKET,'pair_review_contract':CONTRACT,'blind_queue_fingerprint':qfp,'required_condition_replicates':3,'reviews_per_replicate':2,'required_pair_reviews':6,'manager_self_judgment_allowed':False,'execution_plan':plan,'observations':[]}
def tid(model:str,run:str,qfp:str)->dict[str,Any]:
 i={'schema':'novelforge_evaluation_execution_identity_v1','candidate':{'commit':'a'*40,'framework_version':'9.9.9'},'reviewer':{'provider':'openai','model_id':model,'model_revision_binding':'provider_managed_unpinned','reasoning_effort':'medium','sampling':{'binding':'provider_defaults_unpinned'}},'evaluation':{'suite_version':'test','domain':'ablation','blind':True,'queue_fingerprint':qfp,'jobs_fingerprint':'sha256:'+hashlib.sha256(run.encode()).hexdigest(),'capabilities_fingerprint':'sha256:'+'3'*64,'harness_fingerprint':'sha256:'+'4'*64},'environment':{'runner_os':'Linux','runner_arch':'X64','python_version':'3.11'},'resource_budget':{'binding':'same-test-budget'},'provenance':{'github_run_id':run}};i['identity_fingerprint']=fingerprint(i);return i
def arm_result(job:dict[str,Any],tag:str)->dict[str,Any]:return {'job_id':job['job_id'],'subject_id':job['subject_id'],'kind':job['kind'],'input_fingerprint':job['input_fingerprint'],'status':'completed','worker':{'provider':'openai','model_or_reviewer':'arm-model'},'judgment':{'confidence':.8,'verdict':'accept','codes':[],'evidence':[tag]},'proposals':[],'errors':[],'execution':{'worker_session_id':f'SES-ARM-{tag}','attempt_id':f'ATT-ARM-{tag}'}}
def rev_result(job:dict[str,Any],tag:str,rel:str='NO_MATERIAL_DIFFERENCE',reg:str='NEITHER')->dict[str,Any]:return {'job_id':job['job_id'],'subject_id':job['subject_id'],'kind':job['kind'],'input_fingerprint':job['input_fingerprint'],'status':'completed','worker':{'provider':'openai','model_or_reviewer':'review-model'},'judgment':{'confidence':.8,'relation':rel,'regression_in':reg,'reason':'synthetic evidence','evidence':[tag]},'proposals':[],'errors':[],'execution':{'worker_session_id':f'SES-REV-{tag}','attempt_id':f'ATT-REV-{tag}'}}
def synthetic(m:dict[str,Any],cs:dict[str,dict[str,Any]])->dict[str,Any]:
 _,jobs,qfp=eval_ctx(); pair=m['pairs'][0]; cand=cfp(cs[pair['incumbent_case']]['fixture']['candidate_text']); obs=[]
 for n in range(1,4):
  rep=f'R{n}'; ci=tid('arm-model',f'C{n}',qfp); ir=arm_result(jobs[pair['incumbent_case']],f'inc-{rep}'); cr=arm_result(jobs[pair['challenger_case']],f'chal-{rep}')
  for order,suf in [('INCUMBENT_FIRST','I'),('CHALLENGER_FIRST','C')]:
   job=build_review_job(pair,rep,order,cs,jobs,ir,cr); ri=tid('review-model',f'P{n}{suf}','sha256:'+hashlib.sha256(subject(pair['id'],rep,order).encode()).hexdigest())
   obs.append({'pair_id':pair['id'],'replicate_id':rep,'presentation_order':order,'candidate_fingerprint':cand,'condition_execution_identity':ci,'incumbent_result':ir,'challenger_result':cr,'pair_review_execution_identity':ri,'pair_review_job':job,'pair_review_result':rev_result(job,f'{rep}-{suf}')})
 return {'schema':PACKET,'observations':obs}
def self_test()->int:
 m=load(ABL);cs=cases();checks={'manifest_valid':not manifest_errors(m,cs),'execution_plan_3x2':all(len(p['replicates'])==3 and all(len(r['review_subjects'])==2 for r in p['replicates']) for p in prepare(m,cs)['execution_plan']),'missing_semantic_pending':all(x['decision']['status']=='PENDING_MODEL' for x in evaluate({'schema':PACKET,'observations':[]},m,cs)['pairs'])}; packet=synthetic(m,cs);pid=m['pairs'][0]['id'];checks['six_reviews_can_simplify']=next(x for x in evaluate(packet,m,cs)['pairs'] if x['pair_id']==pid)['decision']['status']=='SIMPLIFY'
 directional=json.loads(json.dumps(packet))
 for o in directional['observations']:o['pair_review_result']['judgment']['relation']='B_BETTER' if o['presentation_order']=='INCUMBENT_FIRST' else 'A_BETTER'
 checks['swapped_order_maps_anonymous_AB']=next(x for x in evaluate(directional,m,cs)['pairs'] if x['pair_id']==pid)['decision']['status']=='SIMPLIFY'
 _,jobs,_=eval_ctx();pair=m['pairs'][0];ir=arm_result(jobs[pair['incumbent_case']],'leak-i');cr=arm_result(jobs[pair['challenger_case']],'leak-c');payload=review_payload(pair,'R1','INCUMBENT_FIRST',cfp(cs[pair['incumbent_case']]['fixture']['candidate_text']),jobs[pair['incumbent_case']],jobs[pair['challenger_case']],ir,cr);payload['simpler_arm']='challenger'
 try:make_contract_job(CONTRACT,'LEAK',payload);checks['simplification_intent_leak_blocked']=False
 except ValueError:checks['simplification_intent_leak_blocked']=True
 bad=json.loads(json.dumps(packet));bad['observations'][0]['semantic_relation']='CHALLENGER_BETTER'
 try:evaluate(bad,m,cs);checks['free_semantic_fields_rejected']=False
 except ValueError:checks['free_semantic_fields_rejected']=True
 bad=json.loads(json.dumps(packet));bad['observations'][0]['pair_review_job']['input']['payload']['condition_a']['result_fingerprint']='sha256:'+'0'*64
 try:evaluate(bad,m,cs);checks['result_binding_tamper_rejected']=False
 except ValueError:checks['result_binding_tamper_rejected']=True
 short=json.loads(json.dumps(packet));short['observations']=short['observations'][:-1];checks['incomplete_counterbalance_pending']=next(x for x in evaluate(short,m,cs)['pairs'] if x['pair_id']==pid)['decision']['status']=='PENDING_MODEL'
 safety=json.loads(json.dumps(packet));o=safety['observations'][0];simp=m['pairs'][0]['simpler_arm'];o['pair_review_result']['judgment']['regression_in']='A' if (simp=='incumbent' and o['presentation_order']=='INCUMBENT_FIRST') or (simp=='challenger' and o['presentation_order']=='CHALLENGER_FIRST') else 'B';checks['safety_regression_veto']=next(x for x in evaluate(safety,m,cs)['pairs'] if x['pair_id']==pid)['decision']['status']=='KEEP'
 checks['deterministic_output']=evaluate(packet,m,cs)==evaluate(packet,m,cs);ok=all(checks.values());print(json.dumps({'paired_ablation_contract':'PASS' if ok else 'FAIL',**checks,'semantic_superiority_inferred_by_python':False,'model_execution':False},indent=2));return 0 if ok else 1
def main()->int:
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True);s.add_parser('self-test');q=s.add_parser('prepare');q.add_argument('--output');r=s.add_parser('review-job');r.add_argument('--pair',required=True);r.add_argument('--replicate',choices=['R1','R2','R3'],required=True);r.add_argument('--order',choices=sorted(ORD),required=True);r.add_argument('--incumbent-result',required=True);r.add_argument('--challenger-result',required=True);r.add_argument('--output');v=s.add_parser('evaluate');v.add_argument('--observations',required=True);v.add_argument('--output');a=p.parse_args();m=load(ABL);cs=cases()
 if a.cmd=='self-test':return self_test()
 if a.cmd=='prepare':dump(prepare(m,cs),Path(a.output) if a.output else None);return 0
 if a.cmd=='review-job':
  e=manifest_errors(m,cs)
  if e:raise ValueError('; '.join(e))
  pair=next((x for x in m['pairs'] if x['id']==a.pair),None)
  if not pair:raise ValueError('unknown pair')
  _,jobs,_=eval_ctx();ir=load(Path(a.incumbent_result));cr=load(Path(a.challenger_result));errs=[]
  for side,jid,res in [('incumbent',pair['incumbent_case'],ir),('challenger',pair['challenger_case'],cr)]:
   errs += [f'{side}: {x}' for x in validate_result(jobs[jid],res)]
   if res.get('status')!='completed':errs.append(f'{side}: result must be completed')
  if errs:raise ValueError('; '.join(errs))
  dump(build_review_job(pair,a.replicate,a.order,cs,jobs,ir,cr),Path(a.output) if a.output else None);return 0
 dump(evaluate(load(Path(a.observations)),m,cs),Path(a.output) if a.output else None);return 0
if __name__=='__main__':raise SystemExit(main())
