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


def host_bootstrap() -> ModuleType:
    root = framework_root()
    return _load_source_module(
        "quillframe_host_bootstrap_cli",
        root / "harness" / "integrations" / "host_bootstrap.py",
    )


def host_scaffold() -> ModuleType:
    root = framework_root()
    return _load_source_module(
        "quillframe_host_scaffold_cli",
        root / "harness" / "integrations" / "host_scaffold.py",
    )


def host_hook_main(host: str) -> int:
    return int(host_bootstrap().main_for_host(host))


def resolve_host_project(path: str | None) -> Path | None:
    module = host_bootstrap()
    start = Path(path).expanduser() if path else Path.cwd()
    return module.find_project_root(start)


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

    init_cmd = sub.add_parser("init", help="Create a fiction Project pinned to this exact Framework checkout")
    init_cmd.add_argument("path")
    init_cmd.add_argument("--id", required=True)
    init_cmd.add_argument("--title", required=True)
    init_cmd.add_argument("--language", default="en")
    init_cmd.add_argument("--framework-version", default="0.9.1", help="Minimum acceptable Framework version")
    init_cmd.add_argument("--framework-root")
    init_cmd.add_argument("--force", action="store_true")

    pin_cmd = sub.add_parser("pin", help="Explicitly repin an existing Project to an exact clean Framework checkout")
    pin_cmd.add_argument("path")
    pin_cmd.add_argument("--framework-root")

    validate_cmd = sub.add_parser("validate", help="Validate Project structure and exact authority readiness")
    validate_cmd.add_argument("path")

    build_cmd = sub.add_parser("build", help="Build the deterministic Project bundle")
    build_cmd.add_argument("path")

    projection_cmd = sub.add_parser("projection", help="Compile/apply/status a mapped Project runtime projection")
    projection_sub = projection_cmd.add_subparsers(dest="projection_cmd", required=True)
    projection_preview_cmd = projection_sub.add_parser("preview", help="Compile the mapped manifest without mutation")
    projection_preview_cmd.add_argument("path")
    projection_apply_cmd = projection_sub.add_parser("apply", help="Apply one exact mapped projection transaction")
    projection_apply_cmd.add_argument("path")
    projection_apply_cmd.add_argument("--data-dir")
    projection_apply_cmd.add_argument("--expected-projection-fingerprint")
    projection_status_cmd = projection_sub.add_parser("status", help="Report mapped projection identity")
    projection_status_cmd.add_argument("path")
    projection_status_cmd.add_argument("--data-dir")
    projection_preflight_cmd = projection_sub.add_parser("preflight", help="Fail-closed zero-model target/context preflight")
    projection_preflight_cmd.add_argument("path")
    projection_preflight_cmd.add_argument("--target-id", required=True)
    projection_preflight_cmd.add_argument("--stage", required=True)
    projection_preflight_cmd.add_argument("--data-dir")

    spec_cmd = sub.add_parser("spec-new", help="Create a bilingual structural change spec scaffold")
    spec_cmd.add_argument("path")
    spec_cmd.add_argument("--title", required=True)

    host_install = sub.add_parser("host-install", help="Install/repair Claude Code and Codex host bootstrap files")
    host_install.add_argument("path")
    host_install.add_argument("--force", action="store_true")

    host_run = sub.add_parser("host-run", help="Inspect or begin the typed Quillframe manager run for a host session")
    host_run_sub = host_run.add_subparsers(dest="host_run_cmd", required=True)
    host_status = host_run_sub.add_parser("status", help="Inspect one exact host manager session")
    host_status.add_argument("--session-id", required=True)
    host_status.add_argument("--project")
    host_begin = host_run_sub.add_parser("begin", help="Resolve exactly one task mode and begin one manager run")
    host_begin.add_argument("--session-id", required=True)
    host_begin.add_argument("--mode", required=True)
    host_begin.add_argument("--project")

    sub.add_parser("claude-hook", help=argparse.SUPPRESS)
    sub.add_parser("codex-hook", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "doctor":
            result = doctor(args.project_id, fix=args.fix, data_dir=args.data_dir)
            dump(result)
            return 0 if result["ok"] else 1
        if args.cmd == "claude-hook":
            return host_hook_main("claude_code")
        if args.cmd == "codex-hook":
            return host_hook_main("codex")
        if args.cmd == "host-run":
            module = host_bootstrap()
            project_root = resolve_host_project(args.project)
            if args.host_run_cmd == "status":
                result = module.run_status(project_root, args.session_id)
            else:
                result = module.begin_run(project_root, args.session_id, args.mode)
            dump(result)
            return 0
        if args.cmd == "host-install":
            result = host_scaffold().install_project_hosts(Path(args.path), force=args.force)
            dump(result)
            return 0 if result.get("installed") else 2

        sdk = project_sdk()
        if args.cmd == "init":
            fw_root = Path(args.framework_root).expanduser() if args.framework_root else framework_root()
            result = sdk.init_project(
                Path(args.path), args.id, args.title, args.language, args.framework_version,
                args.force, fw_root,
            )
            host_result = host_scaffold().install_project_hosts(Path(args.path), force=False)
            result = {**result, "host_bootstrap": host_result}
        elif args.cmd == "pin":
            fw_root = Path(args.framework_root).expanduser() if args.framework_root else framework_root()
            result = sdk.pin_project(Path(args.path), fw_root)
        elif args.cmd == "validate":
            result = sdk.validate_project(Path(args.path))
        elif args.cmd == "build":
            result = sdk.build_project(Path(args.path))
        elif args.cmd == "projection":
            root = Path(args.path)
            data_dir = Path(args.data_dir) if getattr(args, "data_dir", None) else None
            if args.projection_cmd == "preview":
                result = sdk.projection_preview(root)
            elif args.projection_cmd == "apply":
                result = sdk.projection_apply(root, data_dir, args.expected_projection_fingerprint)
            elif args.projection_cmd == "status":
                result = sdk.projection_status(root, data_dir)
            else:
                result = sdk.projection_preflight(root, args.target_id, args.stage, data_dir)
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
