#!/usr/bin/env python3
"""NovelForge top-level CLI router.

Stdlib-only orchestration for deterministic framework/project operations. This
CLI never silently invokes an LLM or mutates Project Canon automatically.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FRAMEWORK_VERSION = "7.3.0"
PROJECT_SDK = ROOT / "project_sdk.py"
PROJECT_ADAPTER = ROOT / "project_adapter.py"
CONTROL = ROOT / "harness" / "control_plane" / "control_plane.py"
SESSION = ROOT / "harness" / "session_runtime" / "session_runtime.py"
CAPABILITIES = ROOT / "harness" / "runtime_capabilities.py"
CONTEXT_INSPECTOR = ROOT / "harness" / "context_inspector.py"
MEMORY_TIERS = ROOT / "harness" / "memory_tiers.py"
MEMORY_BANK = ROOT / "harness" / "memory_bank.py"
NARRATIVE_WORLD = ROOT / "harness" / "narrative_world_model.py"
SCENARIO_FORK = ROOT / "harness" / "scenario_fork.py"
LEARNING = ROOT / "learning" / "learning_store.py"
LEARNING_CYCLE = ROOT / "learning" / "learning_cycle.py"
LEARNING_EVAL = ROOT / "learning" / "learning_eval.py"
PROMOTION_GATE = ROOT / "learning" / "promotion_gate.py"
CORPUS_SCOUT = ROOT / "corpus" / "corpus_scout.py"
DISCOVERY = ROOT / "corpus" / "discovery_runtime.py"
RIGHTS_GATE = ROOT / "corpus" / "rights_gate.py"
MCP = ROOT / "harness" / "control_plane" / "mcp_stdio.py"
BUNDLE = ROOT / "release" / "build_framework_bundle.py"
QUALITY_FINDINGS = ROOT / "quality" / "findings.py"
READER_PANEL = ROOT / "quality" / "reader_panel.py"
READER_EXPECTATION = ROOT / "quality" / "reader_expectation.py"
QUALITY_EVOLUTION = ROOT / "quality" / "quality_evolution.py"
REVISION_ORCHESTRATOR = ROOT / "quality" / "revision_orchestrator.py"
CHARACTER_INTEGRITY = ROOT / "quality" / "character_integrity.py"
STATE_GRAPH = ROOT / "quality" / "state_graph.py"

TASK_MODES = [
    "DESIGN-BOOK", "DESIGN-VOLUME", "PLAN-UNIT", "PLAN-CHAPTER", "DRAFT",
    "REVISE", "RESEARCH", "SETTLE", "AUDIT", "CORPUS-INGEST", "LEARN",
    "SYSTEM-IMPROVE",
]


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def call(script: Path, args: list[str]) -> int:
    return subprocess.call([sys.executable, str(script), *args])


def run_json(script: Path, args: list[str]) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
    try:
        value = json.loads(proc.stdout)
        if not isinstance(value, dict):
            raise ValueError("tool output must be object")
    except Exception:
        value = {"valid": False, "errors": [proc.stdout or proc.stderr or f"{script.name} failed"]}
    return proc.returncode, value


def bootstrap(project_root: Path, task_mode: str, build: bool) -> dict[str, Any]:
    project_root = project_root.resolve()
    code, validation = run_json(PROJECT_ADAPTER, ["validate", str(project_root)])
    if code != 0 or not validation.get("valid"):
        return {
            "schema": "novelforge_bootstrap_v1", "ready": False,
            "task_mode": task_mode, "project_root": str(project_root), "validation": validation,
        }
    build_result = None
    if build:
        code, build_result = run_json(PROJECT_ADAPTER, ["build", str(project_root)])
        if code != 0:
            return {
                "schema": "novelforge_bootstrap_v1", "ready": False,
                "task_mode": task_mode, "project_root": str(project_root),
                "validation": validation, "build_error": build_result,
            }
    resolution = validation.get("resolution", {})
    return {
        "schema": "novelforge_bootstrap_v1",
        "framework_version": FRAMEWORK_VERSION,
        "framework_root": str(ROOT),
        "project_root": str(project_root),
        "project_id": resolution.get("project_id"),
        "project_layout": resolution.get("layout"),
        "framework_lock": resolution.get("framework_lock"),
        "task_mode": task_mode,
        "ready": True,
        "validation": validation,
        "build": build_result,
        "required_framework_reads": [
            "HARNESS_MANIFEST.yaml", "SKILL.md", "harness/HARNESS_AGENT.md",
        ],
        "task_specific_loading": "Resolve through Project Adapter + Harness + sparse Context Manifest; never inject the whole project or corpus by default.",
        "capability_policy": "Probe/declare host capabilities before routing external/tool work; undeclared capability is unavailable.",
        "quality_policy": "Reader panels and integrity audits are bounded diagnostics; mandatory independent semantic gates remain separate and fingerprint-bound.",
        "revision_policy": "Use specialist-pass findings and owning-mechanism routing; surface clusters regenerate scenes, reader-flatness returns to Reader Pressure/Scene Simulation, and pairwise evolution decides between candidates.",
        "memory_policy": "Context/memory controls operate on overlays, derived views, or authority-aware memory-bank entries; protected Canon references can only produce proposals.",
        "long_horizon_policy": "Narrative-world retrieval is chapter-safe and accepted/locked by default; reader expectations and scenario branches are diagnostic/exploratory state and never Canon authority.",
    }


def doctor() -> dict[str, Any]:
    required = [
        PROJECT_SDK, PROJECT_ADAPTER, CONTROL, SESSION, CAPABILITIES,
        CONTEXT_INSPECTOR, MEMORY_TIERS, MEMORY_BANK, NARRATIVE_WORLD,
        SCENARIO_FORK, LEARNING, LEARNING_CYCLE, LEARNING_EVAL, PROMOTION_GATE,
        CORPUS_SCOUT, DISCOVERY, RIGHTS_GATE, MCP, BUNDLE, QUALITY_FINDINGS,
        READER_PANEL, READER_EXPECTATION, QUALITY_EVOLUTION,
        REVISION_ORCHESTRATOR, CHARACTER_INTEGRITY, STATE_GRAPH,
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    return {
        "schema": "novelforge_doctor_v1",
        "framework_version": FRAMEWORK_VERSION,
        "framework_root": str(ROOT),
        "ok": not missing,
        "missing": missing,
        "model_execution": False,
    }


def self_test() -> int:
    checks = [
        (PROJECT_SDK, ["self-test"]),
        (PROJECT_ADAPTER, ["self-test"]),
        (SESSION, ["self-test"]),
        (CONTROL, ["--db", "/tmp/novelforge-cli-control.db", "self-test"]),
        (CAPABILITIES, ["self-test"]),
        (CONTEXT_INSPECTOR, ["self-test"]),
        (MEMORY_TIERS, ["self-test"]),
        (MEMORY_BANK, ["--db", "/tmp/novelforge-cli-memory.db", "self-test", "--path", "/tmp/novelforge-cli-memory-selftest.db"]),
        (NARRATIVE_WORLD, ["self-test"]),
        (SCENARIO_FORK, ["--db", "/tmp/novelforge-cli-scenario.db", "self-test", "--path", "/tmp/novelforge-cli-scenario-selftest.db"]),
        (QUALITY_FINDINGS, ["self-test"]),
        (READER_PANEL, ["self-test"]),
        (READER_EXPECTATION, ["--db", "/tmp/novelforge-cli-reader-expectation.db", "self-test", "--path", "/tmp/novelforge-cli-reader-expectation-selftest.db"]),
        (QUALITY_EVOLUTION, ["--db", "/tmp/novelforge-cli-quality.db", "self-test", "--path", "/tmp/novelforge-cli-quality-selftest.db"]),
        (REVISION_ORCHESTRATOR, ["self-test"]),
        (CHARACTER_INTEGRITY, ["self-test"]),
        (STATE_GRAPH, ["self-test"]),
        (LEARNING, ["--db", "/tmp/novelforge-cli-learning.db", "self-test"]),
        (LEARNING_CYCLE, ["self-test", "--path", "/tmp/novelforge-cli-learning-cycle.db"]),
        (LEARNING_EVAL, ["self-test"]),
        (PROMOTION_GATE, ["self-test"]),
        (CORPUS_SCOUT, ["self-test"]),
        (DISCOVERY, ["self-test"]),
        (RIGHTS_GATE, ["self-test"]),
        (MCP, ["--self-test"]),
        (BUNDLE, ["self-test"]),
    ]
    results = []
    ok = True
    for script, args in checks:
        proc = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
        results.append({
            "script": str(script.relative_to(ROOT)), "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:4000], "stderr": proc.stderr.strip()[:2000],
        })
        ok = ok and proc.returncode == 0
    dump({
        "novelforge_cli_contract": "PASS" if ok else "FAIL",
        "framework_version": FRAMEWORK_VERSION,
        "checks": results,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Adaptive Fiction Agent Framework")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bootstrap")
    b.add_argument("--project-root", required=True)
    b.add_argument("--task-mode", required=True, choices=TASK_MODES)
    b.add_argument("--no-build", action="store_true")

    pr = sub.add_parser("project"); pr.add_argument("project_args", nargs=argparse.REMAINDER)
    pa = sub.add_parser("adapter"); pa.add_argument("adapter_args", nargs=argparse.REMAINDER)
    rt = sub.add_parser("runtime"); rt.add_argument("runtime_args", nargs=argparse.REMAINDER)
    ca = sub.add_parser("capabilities"); ca.add_argument("capability_args", nargs=argparse.REMAINDER)
    ci = sub.add_parser("context-inspect"); ci.add_argument("context_args", nargs=argparse.REMAINDER)
    mt = sub.add_parser("memory-tiers"); mt.add_argument("memory_args", nargs=argparse.REMAINDER)
    mb = sub.add_parser("memory-bank"); mb.add_argument("memory_bank_args", nargs=argparse.REMAINDER)
    nw = sub.add_parser("narrative-world"); nw.add_argument("narrative_world_args", nargs=argparse.REMAINDER)
    sf = sub.add_parser("scenario-fork"); sf.add_argument("scenario_fork_args", nargs=argparse.REMAINDER)
    qf = sub.add_parser("quality-findings"); qf.add_argument("quality_finding_args", nargs=argparse.REMAINDER)
    rp = sub.add_parser("reader-panel"); rp.add_argument("reader_args", nargs=argparse.REMAINDER)
    rexp = sub.add_parser("reader-expectation"); rexp.add_argument("reader_expectation_args", nargs=argparse.REMAINDER)
    qe = sub.add_parser("quality-evolution"); qe.add_argument("evolution_args", nargs=argparse.REMAINDER)
    ro = sub.add_parser("revision-orchestrator"); ro.add_argument("revision_args", nargs=argparse.REMAINDER)
    ch = sub.add_parser("character-integrity"); ch.add_argument("character_args", nargs=argparse.REMAINDER)
    sg = sub.add_parser("state-graph"); sg.add_argument("state_graph_args", nargs=argparse.REMAINDER)
    le = sub.add_parser("learning"); le.add_argument("learning_args", nargs=argparse.REMAINDER)
    lc = sub.add_parser("learning-cycle"); lc.add_argument("cycle_args", nargs=argparse.REMAINDER)
    lg = sub.add_parser("learning-gate"); lg.add_argument("gate_args", nargs=argparse.REMAINDER)
    lw = sub.add_parser("learning-work"); lw.add_argument("work_args", nargs=argparse.REMAINDER)
    co = sub.add_parser("corpus"); co.add_argument("corpus_args", nargs=argparse.REMAINDER)
    bu = sub.add_parser("bundle"); bu.add_argument("bundle_args", nargs=argparse.REMAINDER)

    sub.add_parser("doctor")
    sub.add_parser("self-test")
    args = p.parse_args()

    if args.cmd == "bootstrap":
        result = bootstrap(Path(args.project_root), args.task_mode, not args.no_build); dump(result); return 0 if result["ready"] else 1
    if args.cmd == "project":
        if not args.project_args: dump({"error": "project subcommand required", "examples": ["init", "validate", "build", "spec-new"]}); return 2
        return call(PROJECT_SDK, args.project_args)
    if args.cmd == "adapter":
        if not args.adapter_args: dump({"error": "adapter subcommand required", "examples": ["resolve", "validate", "build"]}); return 2
        return call(PROJECT_ADAPTER, args.adapter_args)
    if args.cmd == "runtime": return call(CONTROL, args.runtime_args)
    if args.cmd == "capabilities": return call(CAPABILITIES, args.capability_args or ["probe-local"])
    if args.cmd == "context-inspect": return call(CONTEXT_INSPECTOR, args.context_args or ["self-test"])
    if args.cmd == "memory-tiers": return call(MEMORY_TIERS, args.memory_args or ["self-test"])
    if args.cmd == "memory-bank": return call(MEMORY_BANK, args.memory_bank_args or ["self-test"])
    if args.cmd == "narrative-world": return call(NARRATIVE_WORLD, args.narrative_world_args or ["self-test"])
    if args.cmd == "scenario-fork": return call(SCENARIO_FORK, args.scenario_fork_args or ["self-test"])
    if args.cmd == "quality-findings": return call(QUALITY_FINDINGS, args.quality_finding_args or ["self-test"])
    if args.cmd == "reader-panel": return call(READER_PANEL, args.reader_args or ["self-test"])
    if args.cmd == "reader-expectation": return call(READER_EXPECTATION, args.reader_expectation_args or ["self-test"])
    if args.cmd == "quality-evolution": return call(QUALITY_EVOLUTION, args.evolution_args or ["self-test"])
    if args.cmd == "revision-orchestrator": return call(REVISION_ORCHESTRATOR, args.revision_args or ["self-test"])
    if args.cmd == "character-integrity": return call(CHARACTER_INTEGRITY, args.character_args or ["self-test"])
    if args.cmd == "state-graph": return call(STATE_GRAPH, args.state_graph_args or ["self-test"])
    if args.cmd == "learning": return call(LEARNING, args.learning_args)
    if args.cmd == "learning-cycle": return call(LEARNING_CYCLE, args.cycle_args)
    if args.cmd == "learning-gate": return call(PROMOTION_GATE, args.gate_args)
    if args.cmd == "learning-work": return call(LEARNING_EVAL, args.work_args)
    if args.cmd == "corpus":
        if not args.corpus_args:
            dump({"error": "corpus subcommand required", "allowed": ["scout", "discovery", "rights"]}); return 2
        target, *rest = args.corpus_args
        if target == "scout": return call(CORPUS_SCOUT, rest)
        if target == "discovery": return call(DISCOVERY, rest)
        if target == "rights": return call(RIGHTS_GATE, rest)
        dump({"error": f"unknown corpus target: {target}", "allowed": ["scout", "discovery", "rights"]}); return 2
    if args.cmd == "bundle": return call(BUNDLE, args.bundle_args)
    if args.cmd == "doctor":
        result = doctor(); dump(result); return 0 if result["ok"] else 1
    return self_test()


if __name__ == "__main__":
    raise SystemExit(main())
