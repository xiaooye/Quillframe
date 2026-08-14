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
FRAMEWORK_VERSION = "7.1.0"
PROJECT_SDK = ROOT / "project_sdk.py"
PROJECT_ADAPTER = ROOT / "project_adapter.py"
CONTROL = ROOT / "harness" / "control_plane" / "control_plane.py"
SESSION = ROOT / "harness" / "session_runtime" / "session_runtime.py"
CAPABILITIES = ROOT / "harness" / "runtime_capabilities.py"
LEARNING = ROOT / "learning" / "learning_store.py"
LEARNING_CYCLE = ROOT / "learning" / "learning_cycle.py"
LEARNING_EVAL = ROOT / "learning" / "learning_eval.py"
PROMOTION_GATE = ROOT / "learning" / "promotion_gate.py"
CORPUS_SCOUT = ROOT / "corpus" / "corpus_scout.py"
DISCOVERY = ROOT / "corpus" / "discovery_runtime.py"
RIGHTS_GATE = ROOT / "corpus" / "rights_gate.py"
MCP = ROOT / "harness" / "control_plane" / "mcp_stdio.py"
BUNDLE = ROOT / "release" / "build_framework_bundle.py"

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
    }


def doctor() -> dict[str, Any]:
    required = [
        PROJECT_SDK, PROJECT_ADAPTER, CONTROL, SESSION, CAPABILITIES, LEARNING,
        LEARNING_CYCLE, LEARNING_EVAL, PROMOTION_GATE, CORPUS_SCOUT, DISCOVERY,
        RIGHTS_GATE, MCP, BUNDLE,
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
