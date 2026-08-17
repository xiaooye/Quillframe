#!/usr/bin/env python3
"""Documentation-only Quillframe public-brand and SVG integrity checks."""
from __future__ import annotations
import json, re
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PUBLIC_MANIFEST=ROOT/'docs/quillframe_documentation_manifest.json'
DOC_ASSETS=ROOT/'docs/assets'
ERRORS=[]
def err(msg): ERRORS.append(msg)
def load_json(p):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:err(f'{p.relative_to(ROOT)}: invalid JSON: {e}');return {}
def check_public(m):
    if m.get('public_brand')!='Quillframe':err('public manifest brand must be Quillframe')
    if m.get('legacy_technical_namespace')!='novelforge':err('technical namespace must remain novelforge')
    if m.get('target_main')!='84ec25e182b7d9e1e655dede75324dacd6aca752':err('public manifest target_main mismatch')
    for pair in m.get('current_pairs',[]):
        if not isinstance(pair,list) or len(pair)!=2:err('current_pairs entry must be [en, zh-CN]');continue
        for raw in pair:
            p=ROOT/raw
            if not p.exists():err(f'{raw}: missing public-current document');continue
            text=p.read_text(encoding='utf-8')
            if 'Quillframe' not in text:err(f'{raw}: current public surface does not name Quillframe')
            for line_no,line in enumerate(text.splitlines(),1):
                if 'NovelForge' in line:
                    low=line.lower()
                    if not ('legacy' in low or 'technical' in low or 'compatib' in low or 'former' in low or '旧' in line or '兼容' in line):
                        err(f'{raw}:{line_no}: legacy public brand outside compatibility context')
def check_svg(p):
    try:root=ET.fromstring(p.read_text(encoding='utf-8'))
    except Exception as e:err(f'{p.relative_to(ROOT)}: malformed SVG: {e}');return
    if not root.attrib.get('viewBox'):err(f'{p.relative_to(ROOT)}: missing viewBox')
    for tag in ('title','desc'):
        els=[e for e in root.iter() if e.tag.rsplit('}',1)[-1]==tag]
        if not els or not ''.join(els[0].itertext()).strip():err(f'{p.relative_to(ROOT)}: missing <{tag}>')
    raw=p.read_text(encoding='utf-8')
    if '@font-face' in raw or re.search(r'\.(?:woff2?|ttf|otf)\b',raw,re.I):err(f'{p.relative_to(ROOT)}: embedded font forbidden')
    if 'NovelForge' in raw:err(f'{p.relative_to(ROOT)}: legacy public brand in current SVG')
def check_assets(m):
    svgs=sorted(DOC_ASSETS.rglob('*.svg')) if DOC_ASSETS.exists() else []
    if len(svgs)<25:err(f'docs/assets: expected >=25 SVGs, found {len(svgs)}')
    for p in svgs:check_svg(p)
    names={p.name for p in svgs}
    for stem in m.get('canonical_diagrams',[]):
        for lang in ('en','zh-CN'):
            if f'{stem}.{lang}.svg' not in names:err(f'missing {stem}.{lang}.svg')
def main():
    m=load_json(PUBLIC_MANIFEST)
    check_public(m);check_assets(m)
    for raw in m.get('audit_files',[]):
        p=ROOT/raw
        if not p.exists():err(f'{raw}: missing')
        else:load_json(p)
    if ERRORS:
        for e in ERRORS:print('ERROR:',e)
        print(f'quillframe-docs-quality: {len(ERRORS)} error(s)')
        return 1
    print('quillframe-docs-quality: 0 error(s)')
    return 0
if __name__=='__main__':raise SystemExit(main())
