#!/usr/bin/env python3
"""Quillframe 1.0 local product command surface."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from persistence.quillframe_sqlite import QuillframeStore
from quillframe.launch import LaunchError, launch_project


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def framework_root() -> Path:
    configured = os.environ.get("QUILLFRAME_FRAMEWORK_DIR")
    candidates = [Path(configured).expanduser() if configured else None, Path(__file__).resolve().parents[1]]
    for candidate in candidates:
        if candidate is None:
            continue
        root = candidate.resolve()
        if (
            (root / "HARNESS_MANIFEST.yaml").is_file()
            and (root / "project_resolution.py").is_file()
            and (root / "quillframe" / "launch.py").is_file()
        ):
            return root
    raise RuntimeError(
        "Quillframe Framework source checkout not found; use an editable source install "
        "or set QUILLFRAME_FRAMEWORK_DIR to the exact checkout"
    )


def doctor(project_id: str | None = None, *, fix: bool = False, data_dir: str | None = None) -> dict[str, Any]:
    root: Path | None = None
    root_error: str | None = None
    try:
        root = framework_root()
    except Exception as exc:  # source checkout is required for authoring/bootstrap, not SQLite itself
        root_error = str(exc)
    store = QuillframeStore(Path(data_dir).expanduser().resolve() if data_dir else None)
    persistence = store.doctor(project_id, fix=fix)
    checks = {
        "python": {"ok": sys.version_info >= (3, 11), "version": sys.version.split()[0]},
        "framework_source": {"ok": root is not None, "path": str(root) if root else None, "error": root_error},
        "persistence": persistence,
    }
    ok = checks["python"]["ok"] and checks["framework_source"]["ok"] and bool(persistence.get("ok"))
    return {"schema": "quillframe_cli_doctor_v1", "ok": ok, "fix": fix, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quillframe", description="Quillframe local authoring/runtime utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    doctor_cmd = sub.add_parser("doctor", help="Check local Framework source and SQLite health")
    doctor_cmd.add_argument("--project-id")
    doctor_cmd.add_argument("--data-dir")
    doctor_cmd.add_argument("--fix", action="store_true")

    launch_cmd = sub.add_parser("launch", help="Open the all-in-one Quillframe Studio")
    launch_cmd.add_argument("project", nargs="?")
    launch_cmd.add_argument("--new", action="store_true")
    launch_cmd.add_argument("--profile", choices=("local", "cloud"), default="local")
    launch_cmd.add_argument("--id")
    launch_cmd.add_argument("--title")
    launch_cmd.add_argument("--language", default="en")
    launch_cmd.add_argument("--port", type=int, default=0)
    launch_cmd.add_argument("--no-browser", action="store_true")
    launch_cmd.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "launch":
            launched = launch_project(
                project=Path(args.project).expanduser() if args.project else None,
                new=args.new,
                profile=args.profile,
                project_id=args.id,
                title=args.title,
                language=args.language,
                port=args.port,
                no_browser=args.no_browser,
            )
            if args.json:
                print(json.dumps(launched.receipt, ensure_ascii=False, separators=(",", ":")))
            else:
                dump(launched.receipt)
            launched.serve_forever()
            return 0
        if args.cmd == "doctor":
            result = doctor(args.project_id, fix=args.fix, data_dir=args.data_dir)
            dump(result)
            return 0 if result["ok"] else 1
        raise RuntimeError(f"unsupported command: {args.cmd}")
    except Exception as exc:
        dump({"ok": False, "code": getattr(exc, "code", type(exc).__name__), "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
