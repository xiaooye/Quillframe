#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "studio" / "tauri_core_sidecar.py"
BIN_DIR = ROOT / "studio" / "app" / "src-tauri" / "binaries"


def host_triple() -> str:
    result = subprocess.run(["rustc", "-vV"], check=True, text=True, capture_output=True)
    for line in result.stdout.splitlines():
        if line.startswith("host: "):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("rustc -vV did not report a host triple")


def add_data(source: Path, destination: str) -> str:
    separator = ";" if os.name == "nt" else ":"
    return f"{source}{separator}{destination}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=None)
    args = parser.parse_args()
    target = args.target or host_triple()
    executable_suffix = ".exe" if "windows" in target else ""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    output = BIN_DIR / f"quillframe-core-{target}{executable_suffix}"

    with tempfile.TemporaryDirectory(prefix="quillframe-tauri-sidecar-") as temp:
        temp_path = Path(temp)
        dist = temp_path / "dist"
        work = temp_path / "work"
        spec = temp_path / "spec"
        command = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--clean", "--onefile",
            "--name", "quillframe-core",
            "--distpath", str(dist),
            "--workpath", str(work),
            "--specpath", str(spec),
            "--paths", str(ROOT),
            "--paths", str(ROOT / "harness" / "semantic_workers"),
            "--paths", str(ROOT / "quality"),
            "--add-data", add_data(ROOT / "studio" / "host_bridge_contract.json", "studio"),
            "--add-data", add_data(ROOT / "persistence" / "migrations", "persistence/migrations"),
            "--add-data", add_data(ROOT / "harness" / "semantic_workers", "harness/semantic_workers"),
            "--add-data", add_data(ROOT / "quality", "quality"),
            "--add-data", add_data(ROOT / "publication", "publication"),
            "--hidden-import", "peer_bridge_receipt",
            "--hidden-import", "peer_chat_relay",
            "--hidden-import", "registered_contract_binding",
            "--hidden-import", "semantic_worker_router",
            "--hidden-import", "candidate_qualification",
            str(SOURCE),
        ]
        subprocess.run(command, cwd=ROOT, check=True)
        built = dist / f"quillframe-core{executable_suffix}"
        subprocess.run([str(built), "self-test"], cwd=ROOT, check=True)
        shutil.copy2(built, output)
        if os.name != "nt":
            output.chmod(output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(json.dumps({
        "schema": "quillframe_tauri_sidecar_build_v1",
        "status": "PASS",
        "target": target,
        "output": str(output.relative_to(ROOT)),
        "source": str(SOURCE.relative_to(ROOT)),
        "model_execution": False,
        "authority": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
