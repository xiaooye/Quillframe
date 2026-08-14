#!/usr/bin/env python3
"""NovelForge top-level CLI router.

Stdlib-only orchestration for deterministic framework/project operations. This
CLI does not itself invoke an LLM or mutate project Canon automatically.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROJECT_SDK = ROOT / "project_sdk.py"
CONTROL = ROOT / "harness" / "control_plane" / "control_plane.py"
SESSION = ROOT / "harness" / "session_runtime" / "session_runtime.py"
LEARNING = ROOT / "learning" / "learning_store.py"
CORPUS_SCOUT = ROOT / "corpus" / "corpus_scout.py"
RIGHTS_GATE = ROOT / "corpus" / "rights_gate.py"
MCP = ROOT / "harness" / "control_plane" / "mcp_stdio.py"

TASK_MODES = [
    "DESIGN-BOOK", "DESIGN-VOLUME", "PLAN-UNIT", "PLAN-CHAPTER", "DRAFT",
    "REVISE", "RESEARCH", "SETTLE", "AUDIT", "CORPUS-INGEST", "LEARN",
    "SYSTEM-IMPROVE",
]


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def call(script: Path, args: list[str]) -> int:
    return subprocess.call([sys.executable, str(script), *args])


def bootstrap(project_root: Path, task_mode: str, build: bool) -> dict[str, Any]:
    project_root = project_root.resolve()
    validate = subprocess.run(
        [sys.executable, str(PROJECT_SDK), "validate", str(project_root)],
        text=True, capture_output=True, check=False,
    )
    try:
        validation = json.loads(validate.stdout)
    except json.JSONDecodeError:
        validation = {"valid": False, "errors": [validate.stdout or validate.stderr or "project validation failed"]}
    if not validation.get("valid"):
        return {
            "schema": "novelforge_bootstrap_v1",
            "ready": False,
            "task_mode": task_mode,
            "project_root": str(project_root),
            "validation": validation,
        }
    build_result = None
    if build:
        proc = subprocess.run(
            [sys.executable, str(PROJECT_SDK), "build", str(project_root)],
            text=True, capture_output=True, check=False,
        )
        if proc.returncode != 0:
            return {
                "schema": "novelforge_bootstrap_v1",
                "ready": False,
                "task_mode": task_mode,
                "project_root": str(project_root),
                "validation": validation,
                "build_error": proc.stdout or proc.stderr,
            }
        build_result = json.loads(proc.stdout)
    return {
        "schema": "novelforge_bootstrap_v1",
        "framework_version": "7.0.0",
        "framework_root": str(ROOT),
        "project_root": str(project_root),
        "task_mode": task_mode,
        "ready": True,
        "validation": validation,
        "build": build_result,
        "required_framework_reads": [
            "HARNESS_MANIFEST.yaml",
            "SKILL.md",
            "harness/HARNESS_AGENT.md",
        ],
        "task_specific_loading": "Resolve through Harness + sparse Context Manifest; do not load the whole project/corpus by default.",
    }


def doctor() -> dict[str, Any]:
    required = [PROJECT_SDK, CONTROL, SESSION, LEARNING, CORPUS_SCOUT, RIGHTS_GATE, MCP]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    return {
        "schema": "novelforge_doctor_v1",
        "framework_version": "7.0.0",
        "framework_root": str(ROOT),
        "ok": not missing,
        "missing": missing,
        "model_execution": False,
    }


def self_test() -> int:
    checks = [
        (PROJECT_SDK, ["self-test"]),
        (SESSION, ["self-test"]),
        (CONTROL, ["--db", "/tmp/novelforge-cli-control.db", "self-test"]),
        (LEARNING, ["--db", "/tmp/novelforge-cli-learning.db", "self-test"]),
        (CORPUS_SCOUT, ["self-test"]),
        (RIGHTS_GATE, ["self-test"]),
        (MCP, ["--self-test"]),
    ]
    results = []
    ok = True
    for script, args in checks:
        proc = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
        results.append({
            "script": str(script.relative_to(ROOT)),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:4000],
            "stderr": proc.stderr.strip()[:2000],
        })
        ok = ok and proc.returncode == 0
    dump({"novelforge_cli_contract": "PASS" if ok else "FAIL", "checks": results, "model_execution": False})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Adaptive Fiction Agent Framework")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bootstrap")
    b.add_argument("--project-root", required=True)
    b.add_argument("--task-mode", required=True, choices=TASK_MODES)
    b.add_argument("--no-build", action="store_true")

    pr = sub.add_parser("project")
    pr.add_argument("project_args", nargs=argparse.REMAINDER)

    rt = sub.add_parser("runtime")
    rt.add_argument("runtime_args", nargs=argparse.REMAINDER)

    le = sub.add_parser("learning")
    le.add_argument("learning_args", nargs=argparse.REMAINDER)

    co = sub.add_parser("corpus")
    co.add_argument("corpus_args", nargs=argparse.REMAINDER)

    sub.add_parser("doctor")
    sub.add_parser("self-test")
    args = p.parse_args()

    if args.cmd == "bootstrap":
        result = bootstrap(Path(args.project_root), args.task_mode, not args.no_build)
        dump(result)
        return 0 if result["ready"] else 1
    if args.cmd == "project":
        if not args.project_args:
            dump({"error": "project subcommand required", "examples": ["init", "validate", "build", "spec-new"]})
            return 2
        return call(PROJECT_SDK, args.project_args)
    if args.cmd == "runtime":
        return call(CONTROL, args.runtime_args)
    if args.cmd == "learning":
        return call(LEARNING, args.learning_args)
    if args.cmd == "corpus":
        if not args.corpus_args:
            dump({"error": "corpus subcommand required", "examples": ["scout ...", "rights ..."]})
            return 2
        target, *rest = args.corpus_args
        if target == "scout": return call(CORPUS_SCOUT, rest)
        if target == "rights": return call(RIGHTS_GATE, rest)
        dump({"error": f"unknown corpus target: {target}", "allowed": ["scout", "rights"]})
        return 2
    if args.cmd == "doctor":
        result = doctor(); dump(result); return 0 if result["ok"] else 1
    return self_test()


if __name__ == "__main__":
    raise SystemExit(main())
