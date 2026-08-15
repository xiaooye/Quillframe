#!/usr/bin/env python3
"""Thin Agent Skills client for the NovelForge Studio host bridge."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_DESCRIPTION = "novelforge_studio_host_bridge_description_v1"


def candidate_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.getenv("NOVELFORGE_ROOT")
    if env:
        roots.append(Path(env).expanduser())
    roots.extend([Path.cwd(), *Path.cwd().parents])
    here = Path(__file__).resolve()
    roots.extend([here.parent, *here.parents])
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def find_root() -> Path:
    for root in candidate_roots():
        if (root / "novelforge.py").is_file() and (root / "studio" / "host_bridge.py").is_file():
            return root
    raise SystemExit("NovelForge checkout not found. Run inside the checkout or set NOVELFORGE_ROOT.")


def run_bridge(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    root = find_root()
    return subprocess.run(
        [sys.executable, str(root / "studio" / "host_bridge.py"), *args],
        cwd=str(root),
        text=True,
        capture_output=capture,
        check=False,
    )


def self_test() -> dict[str, Any]:
    proc = run_bridge(["describe"], capture=True)
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError:
        value = {}
    checks = {
        "bridge_found": proc.returncode == 0,
        "description_schema": value.get("schema") == EXPECTED_DESCRIPTION,
        "authority_false": value.get("authority") is False,
        "direct_core_store_access_false": value.get("direct_core_store_access") is False,
        "write_command_not_supported": "command.invoke" not in value.get("supported_operations", []),
    }
    return {
        "novelforge_agent_skill_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge Agent Skills bridge client")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("describe")
    inv = sub.add_parser("invoke")
    inv.add_argument("--request", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["novelforge_agent_skill_contract"] == "PASS" else 1

    bridge_args = ["describe"] if args.command == "describe" else ["invoke", "--request", args.request]
    proc = run_bridge(bridge_args)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
