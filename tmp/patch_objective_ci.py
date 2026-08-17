#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def rep(path,old,new):
    p=ROOT/path;text=p.read_text(encoding='utf-8');n=text.count(old)
    if n!=1:raise SystemExit(f'{path}: replacement count {n} for {old[:120]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

# This patch runs AFTER tmp/patch_qualification_ci.py, so the three workflows
# already contain the pre-independent qualification fixtures.

path='.github/workflows/novelforge-contracts.yml'
rep(path,
'''          python quality/candidate_qualification.py self-test > candidate-qualification-test.json\n          python quality/regression_escape.py self-test > regression-escape-test.json\n          python evals/pre_independent_qualification.py self-test > pre-independent-qualification-test.json\n''',
'''          python quality/candidate_qualification.py self-test > candidate-qualification-test.json\n          python quality/regression_escape.py self-test > regression-escape-test.json\n          python quality/objective_envelope.py self-test > objective-envelope-test.json\n          python quality/repair_objective_regression.py self-test > repair-objective-regression-test.json\n          python evals/pre_independent_qualification.py self-test > pre-independent-qualification-test.json\n          python evals/repair_objective_preservation.py self-test > repair-objective-preservation-test.json\n''')
rep(path,
'''          root=pathlib.Path('harness/semantic_workers')\n          sys.path.insert(0,str(root))\n          sys.path.insert(0,str(pathlib.Path('evals').resolve()))\n          from registered_contract_binding import validate_registered_job\n''',
'''          root=pathlib.Path('harness/semantic_workers')\n          sys.path.insert(0,str(root))\n          sys.path.insert(0,str(pathlib.Path('evals').resolve()))\n          sys.path.insert(0,str(pathlib.Path('quality').resolve()))\n          from objective_envelope import build as build_objective_envelope\n          from registered_contract_binding import validate_registered_job\n''')
rep(path,
'''          fp='sha256:'+'a'*64\n          fixtures={\n''',
'''          fp='sha256:'+'a'*64\n          objective_envelope=build_objective_envelope({'subject_id':'CH-CI','run_id':'RUN-CI','authority_cutoff':'synthetic-ci','objective_items':[{'id':'OBJ-CI','category':'reader','statement':'Preserve reader pressure and forward pull.','source_refs':['plan:CI']}],'must_preserve':['reader pressure','forward pull'],'derived_from_rejected_realization':False})\n          fixtures={\n''')
rep(path,
'''            'quality.compare': {'evolution_run_id':'RUN-CI','evolution_subject_id':'CH-CI','comparison_id':'CMP-CI','incumbent':{'candidate_id':'C0','content_fingerprint':'sha256:'+'0'*64},'challenger':{'candidate_id':'C1','content_fingerprint':'sha256:'+'1'*64,'repair_owner':'scene'},'repair_context':{'targets':['reader pressure']}},\n''',
'''            'quality.compare': {'evolution_run_id':'RUN-CI','evolution_subject_id':'CH-CI','comparison_id':'CMP-CI','incumbent':{'candidate_id':'C0','content_fingerprint':'sha256:'+'0'*64},'challenger':{'candidate_id':'C1','content_fingerprint':'sha256:'+'1'*64,'repair_owner':'scene'},'repair_context':{'repair_target':'restore reader pressure','objective_envelope':objective_envelope}},\n''')
rep(path,
'''            'editor.repair_spec': {'candidate_fingerprint':fp,'reader_assessment':{'result':'fail','report':'Dialogue over-explains role and risk.','evidence_refs':['candidate:1']}}\n''',
'''            'editor.repair_spec': {'candidate_fingerprint':fp,'reader_assessment':{'result':'fail','report':'Dialogue over-explains role and risk.','evidence_refs':['candidate:1']},'objective_envelope':objective_envelope}\n''')

path='.github/workflows/novelforge-semantic-contract-packs.yml'
rep(path,
'''          root = pathlib.Path('harness/semantic_workers').resolve()\n          sys.path.insert(0, str(root))\n          sys.path.insert(0, str(pathlib.Path('evals').resolve()))\n          from semantic_worker_router import load_contract_registry, make_contract_job, validate_dispatchable_job, validate_job\n''',
'''          root = pathlib.Path('harness/semantic_workers').resolve()\n          sys.path.insert(0, str(root))\n          sys.path.insert(0, str(pathlib.Path('evals').resolve()))\n          sys.path.insert(0, str(pathlib.Path('quality').resolve()))\n          from objective_envelope import build as build_objective_envelope\n          from semantic_worker_router import load_contract_registry, make_contract_job, validate_dispatchable_job, validate_job\n''')
rep(path,
'''          fp = 'sha256:' + 'a' * 64\n          typed_fixtures = {\n''',
'''          fp = 'sha256:' + 'a' * 64\n          objective_envelope = build_objective_envelope({'subject_id':'CH-CI','run_id':'RUN-CI','authority_cutoff':'synthetic-ci','objective_items':[{'id':'OBJ-CI','category':'reader','statement':'Preserve reader pressure and forward pull.','source_refs':['plan:CI']}],'must_preserve':['reader pressure','forward pull'],'derived_from_rejected_realization':False})\n          typed_fixtures = {\n''')
rep(path,
'''              'quality.compare': {\n                  'evolution_run_id': 'RUN-CI',\n                  'evolution_subject_id': 'CH-CI',\n                  'comparison_id': 'CMP-CI',\n                  'incumbent': {'candidate_id': 'C0', 'content_fingerprint': 'sha256:' + '0' * 64},\n                  'challenger': {'candidate_id': 'C1', 'content_fingerprint': 'sha256:' + '1' * 64, 'repair_owner': 'scene'},\n                  'repair_context': {'targets': ['reader pressure']},\n              },\n''',
'''              'quality.compare': {\n                  'evolution_run_id': 'RUN-CI',\n                  'evolution_subject_id': 'CH-CI',\n                  'comparison_id': 'CMP-CI',\n                  'incumbent': {'candidate_id': 'C0', 'content_fingerprint': 'sha256:' + '0' * 64},\n                  'challenger': {'candidate_id': 'C1', 'content_fingerprint': 'sha256:' + '1' * 64, 'repair_owner': 'scene'},\n                  'repair_context': {'repair_target': 'restore reader pressure', 'objective_envelope': objective_envelope},\n              },\n''')
rep(path,
'''              'editor.repair_spec': {\n                  'candidate_fingerprint': fp,\n                  'reader_assessment': {'result': 'fail', 'report': 'Dialogue over-explains role and risk.', 'evidence_refs': ['candidate:1']},\n              },\n''',
'''              'editor.repair_spec': {\n                  'candidate_fingerprint': fp,\n                  'reader_assessment': {'result': 'fail', 'report': 'Dialogue over-explains role and risk.', 'evidence_refs': ['candidate:1']},\n                  'objective_envelope': objective_envelope,\n              },\n''')

path='.github/workflows/novelforge-quality-gate-hardening.yml'
rep(path,
'''      - 'harness/semantic_workers/contracts/quality.json'\n      - 'harness/semantic_workers/peer_chat_relay.py'\n''',
'''      - 'harness/semantic_workers/contracts/quality.json'\n      - 'harness/semantic_workers/contracts/creative-evolution.json'\n      - 'harness/semantic_workers/contracts/production-loop.json'\n      - 'evals/pre_independent_qualification.py'\n      - 'evals/pre_independent_qualification_ablation.py'\n      - 'evals/repair_objective_preservation.py'\n      - 'harness/semantic_workers/peer_chat_relay.py'\n''')
rep(path,
'''          python -m py_compile quality/quality_taxonomy.py quality/repair_policy.py quality/candidate_qualification.py quality/regression_escape.py quality/production_readiness.py quality/production_release.py\n          python -m py_compile evals/pre_independent_qualification.py evals/pre_independent_qualification_ablation.py evals/qualification_test_fixtures.py\n''',
'''          python -m py_compile quality/quality_taxonomy.py quality/repair_policy.py quality/candidate_qualification.py quality/regression_escape.py quality/objective_envelope.py quality/repair_objective_regression.py quality/quality_evolution.py quality/production_readiness.py quality/production_release.py\n          python -m py_compile evals/pre_independent_qualification.py evals/pre_independent_qualification_ablation.py evals/repair_objective_preservation.py evals/qualification_test_fixtures.py\n''')
rep(path,
'''          python quality/candidate_qualification.py self-test\n          python quality/regression_escape.py self-test\n          python evals/pre_independent_qualification.py self-test\n          python evals/pre_independent_qualification_ablation.py self-test\n''',
'''          python quality/candidate_qualification.py self-test\n          python quality/regression_escape.py self-test\n          python quality/objective_envelope.py self-test\n          python quality/repair_objective_regression.py self-test\n          python quality/quality_evolution.py self-test\n          python evals/pre_independent_qualification.py self-test\n          python evals/pre_independent_qualification_ablation.py self-test\n          python evals/repair_objective_preservation.py self-test\n''')
print('objective-preservation permanent CI patch applied')
