#!/usr/bin/env python3
"""Build blind semantic-eval queue without expected/gold fields."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

FORBIDDEN={'expected','expected_verdict','expected_codes','gold','gold_label','blocks_release','prior_result'}

def load(path:Path)->Any:return json.loads(path.read_text(encoding='utf-8'))
def scrub(v:Any)->Any:
    if isinstance(v,dict):return {k:scrub(x) for k,x in v.items() if k not in FORBIDDEN}
    if isinstance(v,list):return [scrub(x) for x in v]
    return v

def find(v:Any,path='$')->list[str]:
    hits=[]
    if isinstance(v,dict):
        for k,x in v.items():
            if k in FORBIDDEN:hits.append(f'{path}.{k}')
            hits.extend(find(x,f'{path}.{k}'))
    elif isinstance(v,list):
        for i,x in enumerate(v):hits.extend(find(x,f'{path}[{i}]'))
    return hits

def build(manifest_path:Path)->dict[str,Any]:
    manifest=load(manifest_path);cases=[]
    for entry in manifest['cases']:
        case=load(manifest_path.parent/entry['file'])
        if case.get('judge') not in {'rubric','hybrid'}:continue
        blind=scrub(case)
        for key in ('id','type','domain','fixture','rubric','judgment_contract'):
            if key not in blind:raise ValueError(f"semantic case {case.get('id')} missing {key}")
        cases.append(blind)
    payload={'schema':'novelforge_blind_eval_queue_v1','suite_version':manifest.get('suite_version'),'blind':True,'cases':cases}
    hits=find(payload)
    if hits:raise ValueError('blind queue leaks forbidden fields: '+', '.join(hits))
    return payload

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--manifest',default=str(Path(__file__).with_name('eval_manifest.json')));p.add_argument('--output');args=p.parse_args()
    payload=build(Path(args.manifest));text=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    if args.output:Path(args.output).write_text(text,encoding='utf-8')
    else:print(text,end='')
    return 0
if __name__=='__main__':raise SystemExit(main())
