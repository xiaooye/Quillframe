#!/usr/bin/env python3
"""NovelForge generic eval runner.

Deterministic assertions run locally. Rubric/hybrid cases require external
semantic judgments; missing judgments remain PENDING_MODEL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PASS="PASS"; FAIL="FAIL"; PENDING="PENDING_MODEL"; ERROR="ERROR"

@dataclass
class CaseResult:
    case_id: str
    case_type: str
    domain: str
    result: str
    blocks_release: bool
    details: list[str]


def load_json(path: Path)->Any:
    return json.loads(path.read_text(encoding="utf-8"))

def get_path(obj:Any,dotted:str)->Any:
    cur=obj
    if not dotted:return cur
    for part in dotted.split('.'):
        if isinstance(cur,dict) and part in cur:cur=cur[part]
        elif isinstance(cur,list) and part.isdigit() and int(part)<len(cur):cur=cur[int(part)]
        else:raise KeyError(dotted)
    return cur

def resolve(root:Path,rel:str)->Path:
    p=(root/rel).resolve(); rr=root.resolve()
    if p!=rr and rr not in p.parents:raise ValueError(f"path escapes repository: {rel}")
    return p

def assertion_result(a:dict[str,Any],fixture:dict[str,Any],root:Path)->tuple[bool,str]:
    op=a['op']; value=a.get('value')
    if op=='file_exists':
        p=resolve(root,a['file']);ok=p.exists();return ok,f"file_exists {a['file']} => {ok}"
    if op in {'file_text_contains','file_text_not_contains'}:
        p=resolve(root,a['file'])
        if not p.exists():return False,f"missing file: {a['file']}"
        text=p.read_text(encoding='utf-8');ok=(str(value) in text)
        if op=='file_text_not_contains':ok=not ok
        return ok,f"{op} {a['file']} {value!r} => {ok}"
    actual=get_path(fixture,a.get('path',''))
    if op=='equals':ok=actual==value
    elif op=='not_equals':ok=actual!=value
    elif op=='contains':ok=value in actual
    elif op=='not_contains':ok=value not in actual
    elif op=='regex':ok=re.search(str(value),str(actual),flags=re.MULTILINE) is not None
    elif op=='not_regex':ok=re.search(str(value),str(actual),flags=re.MULTILINE) is None
    elif op=='all_in':ok=all(v in actual for v in value)
    elif op=='none_in':ok=all(v not in actual for v in value)
    elif op=='truthy':ok=bool(actual)
    elif op=='falsy':ok=not bool(actual)
    elif op=='gte':ok=actual>=value
    elif op=='lte':ok=actual<=value
    else:raise ValueError(f"unsupported assertion op: {op}")
    return ok,f"{op} {a.get('path','')}: actual={actual!r} expected={value!r} => {ok}"

def deterministic(case:dict[str,Any],root:Path)->tuple[str,list[str]]:
    details=[]
    try:
        for a in case.get('assertions',[]):
            ok,msg=assertion_result(a,case.get('fixture',{}),root);details.append(msg)
            if not ok:return FAIL,details
        return PASS,details
    except Exception as exc:return ERROR,details+[f"evaluator error: {type(exc).__name__}: {exc}"]

def semantic(case:dict[str,Any],judgments:dict[str,Any])->tuple[str,list[str]]:
    j=judgments.get(case['id'])
    if not j:return PENDING,["independent semantic judgment required"]
    details=[f"evidence: {x}" for x in j.get('evidence',[])]
    expected=case.get('expected',{})
    got_verdict=str(j.get('verdict','')).lower(); expected_verdict=str(expected.get('verdict','')).lower()
    got_codes=set(map(str,j.get('codes',[]))); expected_codes=set(map(str,expected.get('codes',[])))
    if expected_verdict:
        verdict_ok=got_verdict==expected_verdict
        codes_ok=expected_codes.issubset(got_codes)
        details.append(f"verdict={got_verdict!r} expected={expected_verdict!r}")
        if not codes_ok:details.append("missing codes="+','.join(sorted(expected_codes-got_codes)))
        return (PASS if verdict_ok and codes_ok else FAIL),details
    result=str(j.get('result','')).lower()
    if result=='pass':return PASS,details
    if result=='fail':return FAIL,details
    return ERROR,details+["judgment requires matching verdict or result=pass|fail"]

def run_case(case:dict[str,Any],root:Path,judgments:dict[str,Any])->CaseResult:
    judge=case['judge'];details=[]
    if judge=='deterministic':result,details=deterministic(case,root)
    elif judge=='rubric':result,details=semantic(case,judgments)
    elif judge=='hybrid':
        d,dd=deterministic(case,root);details+=dd
        if d!=PASS:result=d
        else:
            result,sd=semantic(case,judgments);details+=sd
    else:result=ERROR;details=[f"unknown judge: {judge}"]
    return CaseResult(case['id'],case['type'],case['domain'],result,bool(case.get('blocks_release',False)),details)

def main()->int:
    p=argparse.ArgumentParser(description='Run NovelForge evals')
    p.add_argument('--root');p.add_argument('--manifest');p.add_argument('--judgments');p.add_argument('--domain',action='append');p.add_argument('--case',dest='case_ids',action='append');p.add_argument('--release',action='store_true');p.add_argument('--json',action='store_true');args=p.parse_args()
    here=Path(__file__).resolve();root=Path(args.root).resolve() if args.root else here.parents[1]
    manifest_path=Path(args.manifest).resolve() if args.manifest else here.with_name('eval_manifest.json')
    manifest=load_json(manifest_path);judgments=load_json(Path(args.judgments)) if args.judgments else {}
    results=[]
    for entry in manifest['cases']:
        case=load_json(manifest_path.parent/entry['file'])
        if args.domain and case['domain'] not in args.domain:continue
        if args.case_ids and case['id'] not in args.case_ids:continue
        results.append(run_case(case,root,judgments))
    counts={PASS:0,FAIL:0,PENDING:0,ERROR:0}
    for r in results:counts[r.result]=counts.get(r.result,0)+1
    blockers=[r for r in results if r.blocks_release and r.result!=PASS]
    payload={'suite_version':manifest.get('suite_version'),'counts':counts,'release_mode':args.release,'release_blockers':[r.case_id for r in blockers],'results':[r.__dict__ for r in results]}
    if args.json:print(json.dumps(payload,ensure_ascii=False,indent=2))
    else:
        for r in results:print(f"[{r.result:13}] [{'BLOCK' if r.blocks_release else 'INFO'}] {r.case_id} ({r.domain})")
        print('Summary:',counts)
    if args.release:return 1 if blockers else 0
    return 1 if any(r.result in {FAIL,ERROR} for r in results) else 0
if __name__=='__main__':sys.exit(main())
