import json
from pathlib import Path
p=Path('docs/documentation_manifest.json')
s=p.read_text(encoding='utf-8')
marker='    {"id":"changelog","tier":"C"'
entry={"id":"product-site-overview","tier":"B","english":"site/README.en.md","chinese":"site/README.zh-CN.md","audience":"product contributors, deployers, and framework maintainers","purpose":"Product Site stack, design boundary, local development, routes, deployment, and authority boundary","authority_sources":["specs/004-novelforge-product-site/","site/package.json","site/scripts/quality.mjs","assets/brand/tokens.json","assets/brand/weiui.integration.json","assets/brand/story-loom.weiui.css"],"visual_policy":"guide","rewrite_policy":"rebuild","freshness_owner":"product-experience","status":"candidate_review"}
d=json.loads(s)
assert entry['id'] not in {x['id'] for x in d['documents']}
assert marker in s
line='    '+json.dumps(entry,ensure_ascii=False,separators=(',',':'))+',\n\n'
p.write_text(s.replace(marker,line+marker,1),encoding='utf-8')
