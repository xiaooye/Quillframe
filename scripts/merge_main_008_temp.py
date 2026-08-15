#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], text=True, capture_output=True, check=check)


def insert_after(text: str, anchor: str, addition: str) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise SystemExit(f'manifest anchor missing: {anchor!r}')
    return text.replace(anchor, anchor + addition, 1)


run('config', 'user.name', 'github-actions[bot]')
run('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
run('fetch', 'origin', 'main')
feature_before = run('rev-parse', 'HEAD').stdout.strip()
main_head = run('rev-parse', 'origin/main').stdout.strip()
print(f'feature_before={feature_before} main={main_head}')
merge = run('merge', '--no-commit', '--no-ff', 'origin/main', check=False)
if merge.returncode != 0:
    conflicts = [x for x in run('diff', '--name-only', '--diff-filter=U').stdout.splitlines() if x]
    if conflicts != ['HARNESS_MANIFEST.yaml']:
        print(merge.stdout)
        print(merge.stderr)
        raise SystemExit(f'unexpected merge conflicts: {conflicts}')
    run('checkout', '--theirs', '--', 'HARNESS_MANIFEST.yaml')

path = pathlib.Path('HARNESS_MANIFEST.yaml')
text = path.read_text(encoding='utf-8')

text = insert_after(
    text,
    '  character_relationship:\n    en: core/CHARACTER_SYSTEM.en.md\n    zh_cn: core/CHARACTER_SYSTEM.zh-CN.md\n',
    '  event_ir:\n    tool: core/event_ir.py\n    schema: core/event_ir.schema.json\n    schema_id: novelforge_event_ir_v1\n    authority: false\n',
)
text = insert_after(
    text,
    '  context_inspector: harness/context_inspector.py\n',
    '  context_trace: harness/context_trace.py\n  context_trace_schema_file: harness/context_trace.schema.json\n  context_trace_schema: novelforge_context_trace_v1\n  story_workspace: harness/story_workspace.py\n  story_workspace_schema_file: harness/story_workspace.schema.json\n  story_workspace_schema: novelforge_story_workspace_v1\n  scene_simulation_run: harness/scene_simulation_run.py\n  scene_simulation_run_schema_file: harness/scene_simulation_run.schema.json\n  scene_simulation_run_schema: novelforge_scene_simulation_run_v1\n',
)
text = insert_after(
    text,
    '  state_graph: quality/state_graph.py\n',
    '  candidate_state_delta: quality/candidate_state_delta.py\n  candidate_state_delta_schema_file: quality/candidate_state_delta.schema.json\n  candidate_state_delta_schema: novelforge_candidate_state_delta_v1\n  narrative_verification: quality/narrative_verification.py\n  narrative_verification_schema_file: quality/narrative_verification.schema.json\n  narrative_verification_schema: novelforge_narrative_verification_v1\n',
)
text = insert_after(
    text,
    '    memory_consolidation: memory.consolidate\n',
    '    narrative_verification: narrative.verify\n',
)
text = insert_after(
    text,
    '  reader_expectation_authority: false\n',
    '  story_workspace_authority: false\n  event_ir_authority: false\n  candidate_state_delta_authority: false\n  narrative_verification_authority: false\n',
)

repls = [
    ('context-inspector-self-test,', 'context-inspector-self-test, context-trace-self-test, story-workspace-self-test, scene-simulation-run-self-test,'),
    ('settlement-runtime-self-test,', 'settlement-runtime-self-test, event-ir-self-test,'),
    ('state-graph-self-test,', 'state-graph-self-test, candidate-state-delta-self-test, narrative-verification-self-test,'),
]
for old, new in repls:
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f'normal_ci anchor missing: {old}')
    text = text.replace(old, new, 1)

text = insert_after(
    text,
    '  scenario_branch_grants_canon_authority: false\n',
    '  story_workspace_grants_canon_authority: false\n  event_ir_grants_canon_authority: false\n  candidate_state_delta_grants_canon_authority: false\n  narrative_verification_grants_canon_authority: false\n',
)

path.write_text(text, encoding='utf-8')
run('add', 'HARNESS_MANIFEST.yaml')
unmerged = [x for x in run('diff', '--name-only', '--diff-filter=U').stdout.splitlines() if x]
if unmerged:
    raise SystemExit(f'unresolved conflicts remain: {unmerged}')
run('diff', '--cached', '--check')
run('commit', '-m', 'merge: current main into Story Workspace')
head = run('rev-parse', 'HEAD').stdout.strip()
print(f'merged_head={head}')
run('push', 'origin', 'HEAD:feature/008-story-workspace')
