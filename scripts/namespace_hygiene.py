#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SKIP_PREFIX=(".git/","specs/","history/","migration/")
SKIP_FILES={"CHANGELOG.en.md","CHANGELOG.zh-CN.md","scripts/namespace_hygiene.py"}
TEXT_EXT={".py",".json",".yaml",".yml",".toml",".md",".ts",".tsx",".js",".mjs",".css",".html",".sh",".rs",".svg"}
forbidden=("Novel"+"Forge","novel"+"forge","NOVEL"+"FORGE","@"+"quillframe/","--"+"nf-")
violations=[]
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    rel=p.relative_to(ROOT).as_posix()
    if rel in SKIP_FILES or rel.startswith("docs/migration-0.8-to-0.9.") or any(rel.startswith(x) for x in SKIP_PREFIX): continue
    if any(x.lower() in rel.lower() for x in forbidden[:3]): violations.append({"path":rel,"kind":"path"})
    if p.suffix.lower() not in TEXT_EXT: continue
    try: text=p.read_text(encoding="utf-8")
    except UnicodeDecodeError: continue
    hits=[x for x in forbidden if x in text]
    if hits: violations.append({"path":rel,"kind":"content","tokens":hits})
print(json.dumps({"schema":"quillframe_namespace_hygiene_v1","ok":not violations,"violations":violations},ensure_ascii=False,indent=2))
raise SystemExit(0 if not violations else 1)
