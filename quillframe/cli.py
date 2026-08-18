#!/usr/bin/env python3
"""Quillframe local command surface.

The CLI is intentionally thin. It exposes deterministic Project/bootstrap and
persistence operations without turning the CLI or a third-party host into story
or Framework authority.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from persistence.quillframe_sqlite import QuillframeStore


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def framework_root() -> Path:
    configured = os.environ.get("QUILLFRAME_FRAMEWORK_DIR")
    candidates = [Path(configured).expanduser() if configured else None, Path(__file__).resolve().parents[1]]
    for candidate in candidates:
        if candidate is None:
            continue
        root = candidate.resolve()
        if (root / "HARNESS_MANIFEST.yaml").is_file() and (root / "project_sdk.py").is_file():
            return root
    raise RuntimeError(
        "Quillframe Framework source checkout not found; use an editable source install "
        "or set QUILLFRAME_FRAMEWORK_DIR to the exact checkout"
    )


def _load_source_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_sdk() -> ModuleType:
    root = framework_root()
    return _load_source_module("quillframe_project_sdk_cli", root / "project_sdk.py")


def claude_hook_main() -> int:
    root = framework_root()
    module = _load_source_module("quillframe_claude_hook_cli", root / "harness" / "integrations" / "claude_hook.py")
    return int(module.main())


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
    p = argparse.ArgumentParser(prog="quillframe", description="Quillframe local authoring/runtime utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="Check local Framework source and SQLite health")
    d.add_argument("--project-id")
    d.add_argument("--data-dir")
    d.add_argument("--fix", action="store_true")

    i = sub.add_parser("init", help="Create a fiction Project pinned to this exact Framework checkout")
    i.add_argument("path")
    i.add_argument("--id", required=True)
    i.add_argument("--title", required=True)
    i.add_argument("--language", default="en")
    i.add_argument("--framework-version", default="0.9.0", help="Minimum acceptable Framework version")
    i.add_argument("--framework-root")
    i.add_argument("--force", action="store_true")

    pin = sub.add_parser("pin", help="Explicitly repin an existing Project to an exact clean Framework checkout")
    pin.add_argument("path")
    pin.add_argument("--framework-root")

    v = sub.add_parser("validate", help="Validate Project structure and exact authority readiness")
    v.add_argument("path")

    b = sub.add_parser("build", help="Build the deterministic Project bundle")
    b.add_argument("path")

    s = sub.add_parser("spec-new", help="Create a bilingual structural change spec scaffold")
    s.add_argument("path")
    s.add_argument("--title", required=True)

    sub.add_parser("claude-hook", help=argparse.SUPPRESS)

    args = p.parse_args(argv)
    try:
        if args.cmd == "doctor":
            result = doctor(args.project_id, fix=args.fix, data_dir=args.data_dir)
            dump(result)
            return 0 if result["ok"] else 1
        if args.cmd == "claude-hook":
            return claude_hook_main()

        sdk = project_sdk()
        if args.cmd == "init":
            fw_root = Path(args.framework_root).expanduser() if args.framework_root else framework_root()
            result = sdk.init_project(
                Path(args.path), args.id, args.title, args.language, args.framework_version,
                args.force, fw_root,
            )
        elif args.cmd == "pin":
            fw_root = Path(args.framework_root).expanduser() if args.framework_root else framework_root()
            result = sdk.pin_project(Path(args.path), fw_root)
        elif args.cmd == "validate":
            result = sdk.validate_project(Path(args.path))
        elif args.cmd == "build":
            result = sdk.build_project(Path(args.path))
        else:
            result = sdk.create_spec(Path(args.path), args.title)
        dump(result)
        if args.cmd == "validate":
            return 0 if result["valid"] else 1
        return 0
    except Exception as exc:
        dump({"ok": False, "code": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
