#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

path = Path('docs/documentation_manifest.json')
text = path.read_text(encoding='utf-8')
entries = [
    '{"id":"006-story-loom-kawaii-atelier-v5-spec","tier":"C","english":"specs/006-story-loom-kawaii-atelier-v5/spec.en.md","chinese":"specs/006-story-loom-kawaii-atelier-v5/spec.zh-CN.md","audience":"product and framework maintainers","purpose":"active Story Loom kawaii atelier v5 visual requirements and acceptance contract","authority_sources":["specs/006-story-loom-kawaii-atelier-v5/","assets/brand/","studio/","site/"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}',
    '{"id":"006-story-loom-kawaii-atelier-v5-plan","tier":"C","english":"specs/006-story-loom-kawaii-atelier-v5/plan.en.md","chinese":"specs/006-story-loom-kawaii-atelier-v5/plan.zh-CN.md","audience":"product and framework maintainers","purpose":"active Story Loom kawaii atelier v5 implementation plan","authority_sources":["specs/006-story-loom-kawaii-atelier-v5/","assets/brand/","studio/","site/"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}',
    '{"id":"006-story-loom-kawaii-atelier-v5-tasks","tier":"C","english":"specs/006-story-loom-kawaii-atelier-v5/tasks.en.md","chinese":"specs/006-story-loom-kawaii-atelier-v5/tasks.zh-CN.md","audience":"product and framework maintainers","purpose":"active Story Loom kawaii atelier v5 implementation task ledger","authority_sources":["specs/006-story-loom-kawaii-atelier-v5/","assets/brand/","studio/","site/"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}',
]
ids = [json.loads(entry)['id'] for entry in entries]
present = [f'"id":"{doc_id}"' in text for doc_id in ids]
if all(present):
    print('manifest already contains all kawaii v5 entries')
    raise SystemExit(0)
if any(present):
    raise SystemExit('partial kawaii v5 manifest registration; refusing non-atomic repair')
marker = '\n    {"id":"changelog"'
pos = text.find(marker)
if pos < 0:
    raise SystemExit('changelog insertion marker not found')
block = '\n' + '\n'.join(f'    {entry},' for entry in entries) + '\n'
updated = text[:pos] + block + text[pos:]
json.loads(updated)
path.write_text(updated, encoding='utf-8')
print({'status':'updated','registered':ids})
