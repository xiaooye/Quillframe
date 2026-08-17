#!/usr/bin/env python3
from __future__ import annotations
import copy, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROD = 'harness/semantic_workers/contracts/production-loop.json'
CAT = 'harness/semantic_workers/model_contract_catalog.json'
DOC = 'docs/documentation_manifest.json'


def git_json(ref: str, path: str):
    raw = subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT, text=True)
    return json.loads(raw)


def write(path: str, obj):
    (ROOT / path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

merge = subprocess.check_output(['git', 'rev-list', '--merges', '--max-count=1', 'HEAD'], cwd=ROOT, text=True).strip()
if not merge:
    raise SystemExit('no merge ancestor found')
p1 = subprocess.check_output(['git', 'rev-parse', f'{merge}^1'], cwd=ROOT, text=True).strip()
p2 = subprocess.check_output(['git', 'rev-parse', f'{merge}^2'], cwd=ROOT, text=True).strip()
# The feature parent contains quality.candidate_self_audit in its catalog; main contains the
# automatic feedback capture/skip form of learning.preference_interpret.
a = git_json(p1, CAT); b = git_json(p2, CAT)
if 'quality.candidate_self_audit' in next(x for x in a['packs'] if x['id']=='quality')['contracts']:
    feature, main = p1, p2
else:
    feature, main = p2, p1

feature_prod = git_json(feature, PROD)
main_prod = git_json(main, PROD)
merged_prod = copy.deepcopy(feature_prod)
merged_prod['version'] = '5'
merged_prod['principle'] = (
    'Production-loop semantic artifacts stay thin. Models decide whether feedback is learnable, '
    'interpret causal scene state, preserve current objectives and choose repair strategy; machines '
    'consume only the small fields needed for authority-safe persistence or routing. Private character '
    'state may drive semantic decisions but is not prose payload, rejected repair trajectories do not '
    'become the fresh Writer objective, and this pack does not duplicate the Blind Reader.'
)
merged_prod['contracts']['learning.preference_interpret'] = copy.deepcopy(
    main_prod['contracts']['learning.preference_interpret']
)
assert 'capture_decision' in merged_prod['contracts']['learning.preference_interpret']['output_contract']['properties']
assert 'objective_envelope' in merged_prod['contracts']['editor.repair_spec']['input_contract']['properties']
write(PROD, merged_prod)

feature_cat = git_json(feature, CAT)
main_cat = git_json(main, CAT)
merged_cat = copy.deepcopy(feature_cat)
merged_cat['version'] = '10'
pp = next(x for x in merged_cat['packs'] if x['id'] == 'production-loop')
pp['description'] = (
    'Automatic feedback-candidate capture/skip interpretation, minimal writer-safe causal projection, '
    'and FIX+PRESERVE Editor repair planning with a compact objective envelope.'
)
pp['load_when'] = (
    'The production loop must decide whether user feedback is learnable and interpret it, project private '
    'simulation into minimal writer-safe causal context, or create a bounded repair plan that fixes the '
    'owning mechanism while preserving current higher-order objectives.'
)
assert 'quality.candidate_self_audit' in next(x for x in merged_cat['packs'] if x['id']=='quality')['contracts']
assert next(x for x in main_cat['packs'] if x['id']=='production-loop')['contracts'] == pp['contracts']
write(CAT, merged_cat)

feature_doc = git_json(feature, DOC)
main_doc = git_json(main, DOC)
merged_doc = copy.deepcopy(feature_doc)
existing = {d['id'] for d in merged_doc['documents']}
for d in main_doc['documents']:
    if d['id'] not in existing:
        merged_doc['documents'].append(copy.deepcopy(d)); existing.add(d['id'])
ids = {d['id'] for d in merged_doc['documents']}
assert '013-automatic-feedback-learning-intake-spec' in ids
assert '014-pre-independent-candidate-qualification-spec' in ids
write(DOC, merged_doc)

print(json.dumps({
    'reconciliation': 'PASS', 'merge_commit': merge, 'feature_parent': feature, 'main_parent': main,
    'production_loop_version': merged_prod['version'], 'catalog_version': merged_cat['version'],
    'feedback_capture_preserved': True, 'qualification_contract_preserved': True,
    'docs_013_and_014': True, 'model_execution': False
}, indent=2))
