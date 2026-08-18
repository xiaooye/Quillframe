#!/usr/bin/env python3
from __future__ import annotations
import json, re, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION="0.9.0"
HIST_PREFIX=("specs/","history/")
HIST_FILES={"CHANGELOG.en.md","CHANGELOG.zh-CN.md"}
TEXT={".py",".json",".yaml",".yml",".toml",".md",".txt",".ts",".tsx",".js",".mjs",".cjs",".css",".html",".sh",".rs",".svg",".cfg",".ini",".lock"}

def rel(p): return p.relative_to(ROOT).as_posix()
def hist(p):
    r=rel(p); return r in HIST_FILES or any(r.startswith(x) for x in HIST_PREFIX)
def rm(p):
    p=ROOT/p
    if p.is_dir(): shutil.rmtree(p)
    elif p.exists(): p.unlink()
def mv(src,dst):
    a,b=ROOT/src,ROOT/dst
    if not a.exists(): return
    b.parent.mkdir(parents=True,exist_ok=True)
    if b.exists(): rm(dst)
    a.rename(b)

def delete_legacy():
    rm("site/godot")
    for p in ROOT.glob("**/*.gd"):
        if p.exists() and not hist(p): p.unlink()
    for p in ROOT.glob("**/*.tscn"):
        if p.exists() and not hist(p): p.unlink()
    for p in ROOT.glob("**/project.godot"):
        if p.exists() and not hist(p): p.unlink()
    for p in ROOT.glob("**/export_presets.cfg"):
        if p.exists() and not hist(p): p.unlink()
    wf=ROOT/".github/workflows"
    if wf.exists():
        for p in wf.iterdir():
            n=p.name.lower()
            if any(x in n for x in ("godot","shadow","route-baseline","product-baseline","product-parity","route-parity")): p.unlink()
    ss=ROOT/"site/scripts"
    if ss.exists():
        for p in ss.iterdir():
            n=p.name.lower()
            if any(x in n for x in ("godot","shadow","baseline","parity","geometry")):
                if p.is_dir(): shutil.rmtree(p)
                else: p.unlink()

def rename_paths():
    items=[p for p in ROOT.rglob("*") if not hist(p)]
    for p in sorted(items,key=lambda x:len(x.parts),reverse=True):
        if not p.exists() or rel(p).startswith(".git/"): continue
        name=p.name.replace("NOVELFORGE","QUILLFRAME").replace("NovelForge","Quillframe").replace("novelforge","quillframe")
        if name==p.name: continue
        d=p.with_name(name)
        if d.exists():
            if p.is_dir() and d.is_dir():
                for c in p.iterdir(): c.rename(d/c.name)
                p.rmdir()
            else: raise RuntimeError(f"rename collision: {rel(p)}")
        else: p.rename(d)

def rewrite():
    reps=[
      ("@novelforge/","@quillframe/"),("NOVELFORGE_","QUILLFRAME_"),
      ("novelforge.toml","quillframe.toml"),("novelforge.lock.json","quillframe.lock.json"),
      (".novelforge",".quillframe"),("novelforge.py","quillframe.py"),
      ("novelforge_","quillframe_"),("novelforge.","quillframe."),("novelforge-","quillframe-"),
      ("novelforge/","quillframe/"),("--nf-","--qf-"),("NovelForge","Quillframe"),
      ("NOVELFORGE","QUILLFRAME"),("novelforge","quillframe"),("0.8.0",VERSION)
    ]
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or hist(p) or rel(p).startswith(".git/") or rel(p)=="scripts/quillframe_0_9_reconstruct.py": continue
        if p.suffix.lower() not in TEXT and p.name not in {"Dockerfile","VERSION"}: continue
        try: t=p.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        old=t
        for a,b in reps: t=t.replace(a,b)
        if t!=old: p.write_text(t,encoding="utf-8")

def packages():
    sp=ROOT/"site/package.json"
    if sp.exists():
        p=json.loads(sp.read_text())
        p["name"]="@quillframe/product-site";p["version"]=VERSION
        p["scripts"]={
          "foundation":"node scripts/sync-weiui.mjs",
          "content":"npm run foundation && node scripts/build-content.mjs",
          "docs:content":"node scripts/build-starlight-content.mjs",
          "dev":"npm run content && vite",
          "build":"npm run content && tsc --noEmit && vite build",
          "preview":"vite preview",
          "quality":"npm run content && npm run docs:content && node scripts/quality.mjs && node scripts/product-hardening-quality.mjs",
          "dev:docs":"npm run docs:content && astro dev --root docs-site",
          "docs:build":"npm run docs:content && astro build --root docs-site && node scripts/verify-starlight-build.mjs"
        }
        sp.write_text(json.dumps(p,indent=2,ensure_ascii=False)+"\n")
    ap=ROOT/"studio/app/package.json"
    if ap.exists():
        p=json.loads(ap.read_text());p["name"]="@quillframe/studio-app";p["version"]=VERSION
        ap.write_text(json.dumps(p,indent=2,ensure_ascii=False)+"\n")

def manifest():
    p=ROOT/"HARNESS_MANIFEST.yaml"
    t=p.read_text()
    t=re.sub(r"(?m)^version:\s*.*$","version: 0.9.0",t,count=1)
    t=re.sub(r"(?m)^name:\s*.*$","name: quillframe",t,count=1)
    t=re.sub(r"(?m)^product_name:\s*.*$","product_name: Quillframe Adaptive Fiction Framework",t,count=1)
    p.write_text(t)

def main():
    mv("docs/8-0-development-inventory.en.md","history/0.8/development-inventory.en.md")
    mv("docs/8-0-development-inventory.zh-CN.md","history/0.8/development-inventory.zh-CN.md")
    delete_legacy();rename_paths();rewrite();rename_paths();packages();manifest()
    (ROOT/"VERSION").write_text("0.9.0\n")
    (ROOT/".quillframe-0.9-migrated").write_text("0.9.0\n")
    print("Quillframe 0.9 repository migration applied")
if __name__=="__main__": main()
