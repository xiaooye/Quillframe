#!/usr/bin/env python3
"""Quillframe top-level deterministic shell.

Quillframe is AI-native: models own semantic fiction work. This CLI exposes only
generic semantic contracts plus deterministic persistence, authority, routing,
state, evaluation and release primitives. It never silently invokes a model or
mutates Project Canon automatically.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FRAMEWORK_VERSION = "0.9.1"

PROJECT_SDK = ROOT / "project_sdk.py"
PROJECT_ADAPTER = ROOT / "project_adapter.py"
SEMANTIC_ROOT = ROOT / "harness" / "semantic_workers"
SEMANTIC = SEMANTIC_ROOT / "semantic_worker_router.py"
REGISTERED_CONTRACT_BINDING = SEMANTIC_ROOT / "registered_contract_binding.py"
PEER_BRIDGE_RECEIPT = SEMANTIC_ROOT / "peer_bridge_receipt.py"

TOOLS: dict[str, Path] = {
    "runtime": ROOT / "harness" / "control_plane" / "control_plane.py",
    "runtime-query": ROOT / "harness" / "control_plane" / "runtime_query.py",
    "resume-preflight": ROOT / "harness" / "session_runtime" / "resume_preflight.py",
    "resume-command": ROOT / "harness" / "session_runtime" / "resume_command.py",
    "runtime-command-authorization": ROOT / "harness" / "session_runtime" / "runtime_command_authorization.py",
    "runtime-command": ROOT / "harness" / "session_runtime" / "runtime_command_executor.py",
    "terminate-preflight": ROOT / "harness" / "session_runtime" / "terminate_preflight.py",
    "terminate-command": ROOT / "harness" / "session_runtime" / "terminate_command.py",
    "terminate-authorization": ROOT / "harness" / "session_runtime" / "terminate_authorization.py",
    "terminate-executor": ROOT / "harness" / "session_runtime" / "terminate_executor.py",
    "capabilities": ROOT / "harness" / "runtime_capabilities.py",
    "context-inspect": ROOT / "harness" / "context_inspector.py",
    "context-runtime": ROOT / "harness" / "context_runtime.py",
    "memory-tiers": ROOT / "harness" / "memory_tiers.py",
    "memory-bank": ROOT / "harness" / "memory_bank.py",
    "scenario-fork": ROOT / "harness" / "scenario_fork.py",
    "settlement": ROOT / "harness" / "settlement_runtime.py",
    "semantic": SEMANTIC,
    "quality-findings": ROOT / "quality" / "findings.py",
    "quality-taxonomy": ROOT / "quality" / "quality_taxonomy.py",
    "repair-policy": ROOT / "quality" / "repair_policy.py",
    "production-readiness": ROOT / "quality" / "production_readiness.py",
    "reader-expectation": ROOT / "quality" / "reader_expectation.py",
    "quality-evolution": ROOT / "quality" / "quality_evolution.py",
    "state-graph": ROOT / "quality" / "state_graph.py",
    "learning": ROOT / "learning" / "learning_store.py",
    "learning-cycle": ROOT / "learning" / "learning_cycle.py",
    "learning-gate": ROOT / "learning" / "promotion_gate.py",
    "learning-work": ROOT / "learning" / "learning_eval.py",
    "bundle": ROOT / "release" / "build_framework_bundle.py",
    "publication": ROOT / "publication" / "compiler.py",
    "semantic-acceptance": ROOT / "evals" / "validate_semantic_acceptance.py",
}

CORPUS_TOOLS = {"scout": ROOT / "corpus" / "corpus_scout.py", "discovery": ROOT / "corpus" / "discovery_runtime.py", "rights": ROOT / "corpus" / "rights_gate.py"}
MCP = ROOT / "harness" / "control_plane" / "mcp_stdio.py"
SESSION = ROOT / "harness" / "session_runtime" / "session_runtime.py"
LOCAL_AGENT = SEMANTIC_ROOT / "adapters" / "local_agent_adapter.py"
PEER_RELAY = SEMANTIC_ROOT / "peer_chat_relay.py"
TASK_MODES = ["DESIGN-BOOK", "DESIGN-VOLUME", "PLAN-UNIT", "PLAN-CHAPTER", "DRAFT", "REVISE", "RESEARCH", "SETTLE", "AUDIT", "CORPUS-INGEST", "LEARN", "SYSTEM-IMPROVE"]

def dump(value: Any) -> None: print(json.dumps(value, ensure_ascii=False, indent=2))
def call(script: Path, args: list[str]) -> int: return subprocess.call([sys.executable, str(script), *args])
def run_json(script: Path, args: list[str]) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
    try:
        value = json.loads(proc.stdout)
        if not isinstance(value, dict): raise ValueError
    except Exception: value = {"valid": False, "errors": [proc.stdout or proc.stderr or f"{script.name} failed"]}
    return proc.returncode, value

def bootstrap(project_root: Path, task_mode: str, build: bool) -> dict[str, Any]:
    project_root = project_root.resolve(); code, validation = run_json(PROJECT_ADAPTER, ["validate", str(project_root)])
    if code != 0 or not validation.get("valid"): return {"schema":"quillframe_bootstrap_v1","ready":False,"task_mode":task_mode,"project_root":str(project_root),"validation":validation}
    build_result = None
    if build:
        code, build_result = run_json(PROJECT_ADAPTER, ["build", str(project_root)])
        if code != 0: return {"schema":"quillframe_bootstrap_v1","ready":False,"task_mode":task_mode,"project_root":str(project_root),"validation":validation,"build_error":build_result}
    resolution = validation.get("resolution", {})
    return {"schema":"quillframe_bootstrap_v1","framework_version":FRAMEWORK_VERSION,"framework_root":str(ROOT),"project_root":str(project_root),"project_id":resolution.get("project_id"),"project_layout":resolution.get("layout"),"framework_lock":resolution.get("framework_lock"),"task_mode":task_mode,"ready":True,"validation":validation,"build":build_result,"required_framework_reads":["HARNESS_MANIFEST.yaml","SKILL.md","harness/HARNESS_AGENT.md"],"ai_native_policy":"Semantic story/character/reader/revision/research judgment belongs to the model through progressively disclosed model-readable contract packs; deterministic code owns invariants, persistence, routing and transactions.","semantic_entry":"quillframe.py semantic prepare-contract","semantic_catalog":"harness/semantic_workers/model_contract_catalog.json","quality_taxonomy":"quality/taxonomy.json","quality_taxonomy_scan":"quillframe.py quality-taxonomy scan <project-profile-or-regression-files>","repair_policy":"quillframe.py repair-policy evaluate --input <repair-policy-payload>","production_reader_contract":"reader.engagement_audit","production_independent_contract":"quality.production_review","production_independence_evidence":"quillframe_project_peer_validation_receipt_v1 from the Project-owned peer bridge; self-declared session ids do not qualify","task_specific_loading":"Resolve through Project Adapter + Harness + sparse Context Manifest; never inject the whole project, corpus, or all semantic packs by default.","capability_policy":"Probe/declare host capabilities before routing external/tool work; undeclared capability is unavailable.","authority_policy":"Model outputs, reader diagnostics, memories, branches and semantic results never grant Canon write authority; accepted Canon mutation must pass settlement transaction checks."}

def doctor() -> dict[str, Any]:
    required = [PROJECT_SDK, PROJECT_ADAPTER, SESSION, MCP, LOCAL_AGENT, PEER_RELAY, REGISTERED_CONTRACT_BINDING, PEER_BRIDGE_RECEIPT, *TOOLS.values(), *CORPUS_TOOLS.values(), SEMANTIC_ROOT / "model_contract_catalog.json", ROOT / "quality" / "taxonomy.json"]
    missing = [str(path.relative_to(ROOT)) for path in dict.fromkeys(required) if not path.exists()]
    forbidden = ["harness/semantic_workers/model_contracts.json"] if (SEMANTIC_ROOT / "model_contracts.json").exists() else []
    return {"schema":"quillframe_doctor_v2","framework_version":FRAMEWORK_VERSION,"framework_root":str(ROOT),"ok":not missing and not forbidden,"missing":missing,"forbidden_pre_release_compatibility":forbidden,"model_execution":False}

def self_test() -> int:
    checks=[(PROJECT_SDK,["self-test"]),(PROJECT_ADAPTER,["self-test"]),(SESSION,["self-test"]),(TOOLS["runtime"],["--db","/tmp/quillframe-cli-control.db","self-test"]),(TOOLS["runtime-query"],["self-test"]),(TOOLS["resume-preflight"],["self-test"]),(TOOLS["resume-command"],["self-test"]),(TOOLS["runtime-command-authorization"],["self-test"]),(TOOLS["runtime-command"],["self-test"]),(TOOLS["terminate-preflight"],["self-test"]),(TOOLS["terminate-command"],["self-test"]),(TOOLS["terminate-authorization"],["self-test"]),(TOOLS["terminate-executor"],["self-test"]),(TOOLS["capabilities"],["self-test"]),(TOOLS["context-inspect"],["self-test"]),(TOOLS["context-runtime"],["self-test"]),(TOOLS["memory-tiers"],["self-test"]),(TOOLS["memory-bank"],["--db","/tmp/quillframe-cli-memory.db","self-test","--path","/tmp/quillframe-cli-memory-selftest.db"]),(TOOLS["scenario-fork"],["--db","/tmp/quillframe-cli-scenario.db","self-test","--path","/tmp/quillframe-cli-scenario-selftest.db"]),(TOOLS["settlement"],["--db","/tmp/quillframe-cli-settlement.db","self-test","--path","/tmp/quillframe-cli-settlement-selftest.db","--project-root","/tmp/quillframe-cli-settlement-project"]),(SEMANTIC,["self-test"]),(REGISTERED_CONTRACT_BINDING,["self-test"]),(PEER_BRIDGE_RECEIPT,["self-test"]),(TOOLS["quality-findings"],["self-test"]),(TOOLS["quality-taxonomy"],["self-test"]),(TOOLS["repair-policy"],["self-test"]),(TOOLS["production-readiness"],["self-test"]),(TOOLS["reader-expectation"],["--db","/tmp/quillframe-cli-reader-expectation.db","self-test","--path","/tmp/quillframe-cli-reader-expectation-selftest.db"]),(TOOLS["quality-evolution"],["--db","/tmp/quillframe-cli-quality.db","self-test","--path","/tmp/quillframe-cli-quality-selftest.db"]),(TOOLS["state-graph"],["self-test"]),(TOOLS["learning"],["--db","/tmp/quillframe-cli-learning.db","self-test"]),(TOOLS["learning-cycle"],["self-test","--path","/tmp/quillframe-cli-learning-cycle.db"]),(TOOLS["learning-work"],["self-test"]),(TOOLS["learning-gate"],["self-test"]),(CORPUS_TOOLS["scout"],["self-test"]),(CORPUS_TOOLS["discovery"],["self-test"]),(CORPUS_TOOLS["rights"],["self-test"]),(MCP,["--self-test"]),(TOOLS["publication"],["self-test"]),(TOOLS["semantic-acceptance"],["self-test"]),(TOOLS["bundle"],["self-test"])]
    results=[]; ok=True
    for script,argv in checks:
        proc=subprocess.run([sys.executable,str(script),*argv],text=True,capture_output=True,check=False); results.append({"script":str(script.relative_to(ROOT)),"returncode":proc.returncode,"stdout":proc.stdout.strip()[:4000],"stderr":proc.stderr.strip()[:2000]}); ok=ok and proc.returncode==0
    d=doctor(); ok=ok and d["ok"]
    dump({"quillframe_cli_contract":"PASS" if ok else "FAIL","framework_version":FRAMEWORK_VERSION,"checks":results,"doctor":d,"settlement_runtime":"harness/settlement_runtime.py","ai_native_semantic_entry":"harness/semantic_workers/semantic_worker_router.py","semantic_catalog":"harness/semantic_workers/model_contract_catalog.json","registered_contract_binding":"harness/semantic_workers/registered_contract_binding.py","peer_bridge_receipt":"harness/semantic_workers/peer_bridge_receipt.py","quality_taxonomy":"quality/taxonomy.json","repair_policy":"quality/repair_policy.py","production_reader_contract":"reader.engagement_audit","production_independent_contract":"quality.production_review","production_independence_evidence":"quillframe_project_peer_validation_receipt_v1","aggregate_semantic_registry_present":False,"model_execution":False}); return 0 if ok else 1

def _forward_tool(name: str, argv: list[str]) -> int:
    """Forward tool argv verbatim so leading tool options remain tool-owned."""
    if not argv and name in {"semantic","context-inspect","context-runtime","memory-tiers","quality-findings","quality-taxonomy","repair-policy","production-readiness","state-graph"}:
        argv=["self-test"] if name!="semantic" else ["catalog"]
    return call(TOOLS[name],argv)

def main() -> int:
    # argparse.REMAINDER does not preserve a child tool option when it is the
    # first token after a subcommand (for example `runtime --db ...`). Route
    # registered tools before top-level argparse so the public CLI acts as a
    # transparent boundary instead of interpreting child-tool flags.
    if len(sys.argv) > 1 and sys.argv[1] in TOOLS:
        return _forward_tool(sys.argv[1],sys.argv[2:])

    parser=argparse.ArgumentParser(description="Quillframe AI-native Adaptive Fiction Agent Framework"); sub=parser.add_subparsers(dest="cmd",required=True)
    boot=sub.add_parser("bootstrap"); boot.add_argument("--project-root",required=True); boot.add_argument("--task-mode",required=True,choices=TASK_MODES); boot.add_argument("--no-build",action="store_true")
    project=sub.add_parser("project"); project.add_argument("args",nargs=argparse.REMAINDER)
    adapter=sub.add_parser("adapter"); adapter.add_argument("args",nargs=argparse.REMAINDER)
    corpus=sub.add_parser("corpus"); corpus.add_argument("args",nargs=argparse.REMAINDER)
    for name in TOOLS:
        tool=sub.add_parser(name); tool.add_argument("args",nargs=argparse.REMAINDER)
    sub.add_parser("doctor"); sub.add_parser("self-test"); args=parser.parse_args()
    if args.cmd=="bootstrap": value=bootstrap(Path(args.project_root),args.task_mode,not args.no_build); dump(value); return 0 if value["ready"] else 1
    if args.cmd=="project":
        if not args.args: dump({"error":"project subcommand required","examples":["init","validate","build","spec-new"]}); return 2
        return call(PROJECT_SDK,args.args)
    if args.cmd=="adapter":
        if not args.args: dump({"error":"adapter subcommand required","examples":["resolve","validate","build"]}); return 2
        return call(PROJECT_ADAPTER,args.args)
    if args.cmd=="corpus":
        if not args.args: dump({"error":"corpus target required","allowed":sorted(CORPUS_TOOLS)}); return 2
        target,*rest=args.args
        if target not in CORPUS_TOOLS: dump({"error":f"unknown corpus target: {target}","allowed":sorted(CORPUS_TOOLS)}); return 2
        return call(CORPUS_TOOLS[target],rest)
    if args.cmd in TOOLS:
        return _forward_tool(args.cmd,args.args)
    if args.cmd=="doctor": value=doctor(); dump(value); return 0 if value["ok"] else 1
    return self_test()

if __name__=="__main__": raise SystemExit(main())
