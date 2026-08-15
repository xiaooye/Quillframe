#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

path = Path("docs/documentation_manifest.json")
text = path.read_text(encoding="utf-8")

entries = [
    '{"id":"004-product-site-visual-rewrite-v3-spec","tier":"C","english":"specs/004-novelforge-product-site/visual-rewrite-v3.spec.en.md","chinese":"specs/004-novelforge-product-site/visual-rewrite-v3.spec.zh-CN.md","audience":"product and framework maintainers","purpose":"historical Product Site visual rewrite v3 requirements record","authority_sources":["specs/004-novelforge-product-site/","site/"],"visual_policy":"record","rewrite_policy":"preserve_history","freshness_owner":"historical-record","status":"preserve"}',
    '{"id":"004-product-site-visual-rewrite-v3-plan","tier":"C","english":"specs/004-novelforge-product-site/visual-rewrite-v3.plan.en.md","chinese":"specs/004-novelforge-product-site/visual-rewrite-v3.plan.zh-CN.md","audience":"product and framework maintainers","purpose":"historical Product Site visual rewrite v3 implementation plan","authority_sources":["specs/004-novelforge-product-site/","site/"],"visual_policy":"record","rewrite_policy":"preserve_history","freshness_owner":"historical-record","status":"preserve"}',
    '{"id":"004-product-site-visual-rewrite-v3-tasks","tier":"C","english":"specs/004-novelforge-product-site/visual-rewrite-v3.tasks.en.md","chinese":"specs/004-novelforge-product-site/visual-rewrite-v3.tasks.zh-CN.md","audience":"product and framework maintainers","purpose":"historical Product Site visual rewrite v3 task ledger","authority_sources":["specs/004-novelforge-product-site/","site/"],"visual_policy":"record","rewrite_policy":"preserve_history","freshness_owner":"historical-record","status":"preserve"}',
    '{"id":"005-product-entry-spa-v4-spec","tier":"C","english":"specs/005-product-entry-spa-v4/spec.en.md","chinese":"specs/005-product-entry-spa-v4/spec.zh-CN.md","audience":"product and framework maintainers","purpose":"active Product Entry SPA v4 requirements and acceptance contract","authority_sources":["specs/005-product-entry-spa-v4/","HARNESS_MANIFEST.yaml","studio/","site/"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}',
    '{"id":"005-product-entry-spa-v4-plan","tier":"C","english":"specs/005-product-entry-spa-v4/plan.en.md","chinese":"specs/005-product-entry-spa-v4/plan.zh-CN.md","audience":"product and framework maintainers","purpose":"active Product Entry SPA v4 implementation plan","authority_sources":["specs/005-product-entry-spa-v4/","HARNESS_MANIFEST.yaml","studio/","site/"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}',
    '{"id":"005-product-entry-spa-v4-tasks","tier":"C","english":"specs/005-product-entry-spa-v4/tasks.en.md","chinese":"specs/005-product-entry-spa-v4/tasks.zh-CN.md","audience":"product and framework maintainers","purpose":"active Product Entry SPA v4 implementation task ledger","authority_sources":["specs/005-product-entry-spa-v4/","HARNESS_MANIFEST.yaml","studio/","site/"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}',
]

ids = [json.loads(entry)["id"] for entry in entries]
present = [f'"id":"{doc_id}"' in text for doc_id in ids]
if all(present):
    print("documentation manifest already contains all Product Site v3/v4 registrations")
    raise SystemExit(0)
if any(present):
    raise SystemExit("partial Product Site v3/v4 registration detected; refusing non-atomic repair")

marker = '\n    {"id":"changelog"'
pos = text.find(marker)
if pos < 0:
    raise SystemExit("changelog insertion marker not found")

block = "\n" + "\n".join(f"    {entry}," for entry in entries) + "\n"
updated = text[:pos] + block + text[pos:]
json.loads(updated)
path.write_text(updated, encoding="utf-8")
print({"status": "updated", "registered": ids})
