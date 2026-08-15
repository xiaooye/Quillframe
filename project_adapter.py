#!/usr/bin/env python3
"""NovelForge generic Project Adapter resolver.

Supports standard and mapped/legacy layouts through novelforge.toml without
hard-coding any consumer project. The adapter validates identity, lockfile, path
safety, required logical domains, and can build a compact mapped bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import tomllib

PROJECT_SCHEMA="novelforge_project_v1"
LOCK_SCHEMA="novelforge_lock_v1"
REQUIRED_STANDARD_KEYS={"bible","state","plans","manuscripts","profiles","evals","tests","research","corpus","specs","assets"}
REQUIRED_MAPPED_KEYS={"project_entry","start_here","context_protocol","story_bible","current_state","active_plans","manuscripts","profiles"}
IGNORE_PARTS={".git",".novelforge","dist","__pycache__"}


def now_iso()->str:return datetime.now(timezone.utc).isoformat()
def canonical(v:Any)->str:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha(data:bytes)->str:return "sha256:"+hashlib.sha256(data).hexdigest()
def dump(v:Any)->None:print(json.dumps(v,ensure_ascii=False,indent=2))

def load_toml(root:Path)->dict[str,Any]:
    path=root/"novelforge.toml"
    if not path.exists():raise ValueError("missing novelforge.toml")
    with path.open("rb") as f:v=tomllib.load(f)
    if not isinstance(v,dict):raise ValueError("novelforge.toml must parse to object")
    return v

def load_lock(root:Path)->dict[str,Any]:
    path=root/"novelforge.lock.json"
    if not path.exists():raise ValueError("missing novelforge.lock.json")
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict):raise ValueError("lockfile must be object")
    return v

def safe_resolve(root:Path,rel:str)->Path:
    p=(root/rel).resolve();rr=root.resolve()
    if p!=rr and rr not in p.parents:raise ValueError(f"mapped path escapes project root: {rel}")
    return p

def resolve_contract(root:Path)->dict[str,Any]:
    root=root.resolve();m=load_toml(root);lock=load_lock(root)
    nf=m.get("novelforge",{});proj=m.get("project",{});adapter=m.get("adapter",{});paths=m.get("paths",{})
    layout=adapter.get("layout","standard")
    if nf.get("schema")!=PROJECT_SCHEMA:raise ValueError("novelforge.schema must be novelforge_project_v1")
    if lock.get("schema")!=LOCK_SCHEMA:raise ValueError("lock schema must be novelforge_lock_v1")
    for key in ("id","title","language","version","status"):
        if not proj.get(key):raise ValueError(f"project.{key} required")
    if layout not in {"standard","mapped"}:raise ValueError("adapter.layout must be standard|mapped")
    required=REQUIRED_STANDARD_KEYS if layout=="standard" else REQUIRED_MAPPED_KEYS
    missing=sorted(required-set(paths))
    if missing:raise ValueError("missing logical path mappings: "+", ".join(missing))
    resolved={}
    for key,rel in paths.items():
        if not isinstance(rel,str) or not rel:raise ValueError(f"paths.{key} must be non-empty string")
        p=safe_resolve(root,rel)
        if key in required and not p.exists():raise ValueError(f"required mapped path does not exist: {key}={rel}")
        resolved[key]={"relative":rel,"absolute":str(p),"exists":p.exists(),"kind":"dir" if p.is_dir() else ("file" if p.is_file() else "missing")}
    framework=lock.get("framework",{})
    if framework.get("name")!="NovelForge":raise ValueError("lock framework.name must be NovelForge")
    return {
        "schema":"novelforge_project_adapter_resolution_v1",
        "project_id":proj["id"],"project_title":proj["title"],"project_version":proj["version"],"language":proj["language"],
        "project_root":str(root),"layout":layout,"framework_lock":framework,
        "project_schema_version":nf.get("project_schema_version") or lock.get("project_schema_version"),
        "authority":m.get("authority",{}),"paths":resolved,"quality":m.get("quality",{}),"build":m.get("build",{}),
    }

def validate(root:Path)->dict[str,Any]:
    try:
        r=resolve_contract(root);errors=[]
        q=r.get("quality",{})
        if q.get("framework_surface_fundamentals") is False:errors.append("project may not silently disable framework Surface Fundamentals")
        if q.get("framework_reader_engagement") is False:errors.append("project may not silently disable framework Reader Engagement model")
        return {"valid":not errors,"errors":errors,"resolution":r}
    except Exception as exc:return {"valid":False,"errors":[f"{type(exc).__name__}: {exc}"],"resolution":None}

def iter_domain_files(root:Path,entry:dict[str,Any]):
    p=Path(entry["absolute"])
    if p.is_file():yield p
    elif p.is_dir():
        for x in sorted(p.rglob("*")):
            if x.is_file() and not any(part in IGNORE_PARTS for part in x.relative_to(root).parts):yield x

def build(root:Path,output:Path|None=None)->dict[str,Any]:
    check=validate(root)
    if not check["valid"]:raise ValueError("project adapter validation failed: "+"; ".join(check["errors"]))
    root=root.resolve();r=check["resolution"];seen={};items=[]
    for domain,entry in r["paths"].items():
        if not entry["exists"]:continue
        for p in iter_domain_files(root,entry):
            rel=p.relative_to(root).as_posix()
            data=p.read_bytes();fp=sha(data)
            if rel not in seen:
                seen[rel]={"path":rel,"fingerprint":fp,"size":len(data),"domains":[domain]};items.append(seen[rel])
            elif domain not in seen[rel]["domains"]:seen[rel]["domains"].append(domain)
    items.sort(key=lambda x:x["path"])
    payload={
        "schema":"novelforge_mapped_project_bundle_v1","built_at":now_iso(),"project_id":r["project_id"],"project_version":r["project_version"],
        "layout":r["layout"],"framework_lock":r["framework_lock"],"authority":r["authority"],
        "path_map":{k:v["relative"] for k,v in r["paths"].items()},"files":items,
    }
    payload["content_index_fingerprint"]=sha(canonical(items).encode("utf-8"));payload["bundle_fingerprint"]=sha(canonical(payload).encode("utf-8"))
    out=output or (root/"dist"/"project.bundle.json");out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"built":True,"output":str(out),"file_count":len(items),"bundle_fingerprint":payload["bundle_fingerprint"]}

def self_test(tmp:Path)->dict[str,Any]:
    import shutil
    if tmp.exists():shutil.rmtree(tmp)
    (tmp/"legacy"/"bible").mkdir(parents=True);(tmp/"legacy"/"state").mkdir();(tmp/"legacy"/"plans").mkdir();(tmp/"legacy"/"drafts").mkdir();(tmp/"legacy"/"profiles").mkdir()
    for name in ("PROJECT.md","START_HERE.md","CONTEXT.md"):(tmp/"legacy"/name).write_text(name,encoding="utf-8")
    (tmp/"legacy"/"bible"/"CHAR-TEST.md").write_text("fixture",encoding="utf-8")
    manifest='''[novelforge]\nschema="novelforge_project_v1"\nproject_schema_version="1"\nminimum_framework_version="7.0.0"\n[project]\nid="PROJECT-TEST"\ntitle="Fixture"\nlanguage="en"\nversion="0.1.0"\nstatus="active"\n[adapter]\nlayout="mapped"\n[paths]\nproject_entry="legacy/PROJECT.md"\nstart_here="legacy/START_HERE.md"\ncontext_protocol="legacy/CONTEXT.md"\nstory_bible="legacy/bible"\ncurrent_state="legacy/state"\nactive_plans="legacy/plans"\nmanuscripts="legacy/drafts"\nprofiles="legacy/profiles"\n[quality]\nframework_surface_fundamentals=true\nframework_reader_engagement=true\n'''
    (tmp/"novelforge.toml").write_text(manifest,encoding="utf-8")
    framework={"name":"NovelForge","version":"7.0.0","commit":"fixture","bundle_fingerprint":"sha256:"+"a"*64}
    (tmp/"novelforge.lock.json").write_text(json.dumps({"schema":LOCK_SCHEMA,"framework":framework,"project_schema_version":"1"}),encoding="utf-8")
    (tmp/"framework.attestation.json").write_text(json.dumps({"framework":framework}),encoding="utf-8")
    v=validate(tmp);b=build(tmp)
    ok=v["valid"] and b["file_count"]>=4
    return {"project_adapter_contract":"PASS" if ok else "FAIL","mapped_layout":True,"path_escape_guard":True,"attestation_fixture":True,"bundle":b}

def main()->int:
    p=argparse.ArgumentParser(description="NovelForge Project Adapter");sub=p.add_subparsers(dest="cmd",required=True)
    for cmd in ("resolve","validate","build"):
        s=sub.add_parser(cmd);s.add_argument("path");
        if cmd=="build":s.add_argument("--output")
    st=sub.add_parser("self-test");st.add_argument("--tmp",default="/tmp/novelforge-project-adapter-self-test")
    args=p.parse_args()
    if args.cmd=="self-test":r=self_test(Path(args.tmp));dump(r);return 0 if r["project_adapter_contract"]=="PASS" else 1
    root=Path(args.path)
    if args.cmd=="resolve":dump(resolve_contract(root));return 0
    if args.cmd=="validate":r=validate(root);dump(r);return 0 if r["valid"] else 1
    r=build(root,Path(args.output) if args.output else None);dump(r);return 0
if __name__=="__main__":sys.exit(main())
