#!/usr/bin/env python3
"""Local launcher/orientation CLI for Novel Production Agent Runtime v6.6.

This CLI resolves runtime/project/policy sources and delegates operational
Control Plane status/self-tests. It does not itself generate prose or mutate Canon.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
CONTROL=ROOT/"harness"/"control_plane"/"control_plane.py"


def dump(v:Any)->None: print(json.dumps(v,ensure_ascii=False,indent=2))

def resolve_project(project_root:Path,policy_root:Path|None)->dict[str,Any]:
    root=project_root.resolve()
    candidates=[]
    # Direct project checkout/root.
    candidates.append((root, policy_root.resolve() if policy_root else None))
    # Current frostloom monorepo layout.
    candidates.append((root/"new cards"/"chinaboy_webnovel", (policy_root.resolve() if policy_root else root/"new cards"/"novel_production_os")))
    for project,policy in candidates:
        project_file=project/"novel_bible"/"PROJECT.md"
        start=project/"novel_bible"/"START_HERE.md"
        context=project/"novel_bible"/"shared"/"database"/"CONTEXT_AND_SETTLEMENT_PROTOCOL.md"
        if project_file.exists() and start.exists() and context.exists():
            if policy is None:
                guessed=project.parent/"novel_production_os"
                policy=guessed if guessed.exists() else None
            return {"project_root":str(project),"policy_root":str(policy.resolve()) if policy and policy.exists() else None,"project_file":str(project_file),"start_here":str(start),"context_protocol":str(context),"prose_profile":str(project/"novel_bible"/"shared"/"PROSE_PROFILE.md") if (project/"novel_bible"/"shared"/"PROSE_PROFILE.md").exists() else None}
    raise ValueError(f"could not resolve project source under {root}")

def bootstrap(args:argparse.Namespace)->dict[str,Any]:
    source=resolve_project(Path(args.project_root),Path(args.policy_root) if args.policy_root else None)
    policy=Path(source["policy_root"]) if source["policy_root"] else None
    policy_files={}
    if policy:
        for name,rel in {"policy_skill":"SKILL.md","surface_runtime":"surface/SURFACE_RUNTIME.md","reader_runtime":"surface/READER_ENGAGEMENT_RUNTIME.md"}.items():
            p=policy/rel; policy_files[name]=str(p) if p.exists() else None
    required_reads=[str(ROOT/"SKILL.md"),str(ROOT/"harness"/"HARNESS_AGENT.md"),source["project_file"],source["start_here"],source["context_protocol"]]
    return {"runtime_version":"6.6.0","runtime_root":str(ROOT),"task_mode":args.task_mode,"source":source,"policy_files":policy_files,"required_reads":required_reads,"authority_rule":"runtime repo owns execution; project/policy source owns story/surface/canon","ready":all(Path(p).exists() for p in required_reads)}

def delegate_control(command:list[str],db:str)->int:
    return subprocess.call([sys.executable,str(CONTROL),"--db",db,*command])

def self_test()->int:
    ok=ROOT.joinpath("SKILL.md").exists() and CONTROL.exists() and ROOT.joinpath("harness/control_plane/mcp_stdio.py").exists()
    dump({"novel_os_cli_contract":"PASS" if ok else "FAIL","runtime_root":str(ROOT),"control_plane_present":CONTROL.exists()});return 0 if ok else 1

def main()->int:
    p=argparse.ArgumentParser(description="Novel Production Agent Runtime CLI");sub=p.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("bootstrap");b.add_argument("--project-root",required=True);b.add_argument("--policy-root");b.add_argument("--task-mode",required=True,choices=["DESIGN-BOOK","DESIGN-VOLUME","PLAN-UNIT","PLAN-CHAPTER","DRAFT","REVISE","RESEARCH","SETTLE","AUDIT","CORPUS-INGEST","LEARN","SYSTEM-IMPROVE"])
    s=sub.add_parser("status");s.add_argument("--db",default=os.getenv("NOVEL_OS_DB",".novel-os/runtime.db"))
    i=sub.add_parser("init");i.add_argument("--db",default=os.getenv("NOVEL_OS_DB",".novel-os/runtime.db"))
    sub.add_parser("self-test");args=p.parse_args()
    try:
        if args.cmd=="bootstrap":dump(bootstrap(args));return 0
        if args.cmd=="status":return delegate_control(["status"],args.db)
        if args.cmd=="init":return delegate_control(["init"],args.db)
        return self_test()
    except Exception as exc:dump({"error":type(exc).__name__,"message":str(exc)});return 1
if __name__=="__main__":raise SystemExit(main())
