#!/usr/bin/env python3
"""Quillframe 1.0 local product command surface."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from core_operations import CoreOperations
from persistence.quillframe_sqlite import QuillframeStore
from quillframe.launch import LaunchError, launch_project


_USER_TASTE_PREFERENCE_FIELDS = (
    "hypothesis_id",
    "scope",
    "project_id",
    "dimension",
    "statement",
    "mechanism",
    "state",
    "confidence",
    "applicability",
    "evidence_ids",
    "contradiction_ids",
    "version",
)
_USER_TASTE_RECEIPT_FIELDS = (
    "schema",
    "receipt_id",
    "hypothesis_id",
    "action",
    "source_kind",
    "policy_version",
    "before_version",
    "after_version",
    "candidate_id",
    "reason",
    "authority",
)


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


def _json_object(value: str | None) -> dict[str, Any]:
    if value is None:
        return {}
    if value.startswith("@"):
        value = Path(value[1:]).expanduser().read_text(encoding="utf-8")
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("payload must be a JSON object")
    return parsed


def _core(data_dir: str | None) -> CoreOperations:
    root = Path(data_dir).expanduser().resolve() if data_dir else None
    return CoreOperations(QuillframeStore(root))


def _user_taste_abstract(value: Any, fields: tuple[str, ...], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a JSON object")
    return {key: value[key] for key in fields if key in value}


def _user_taste_transition_output(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("user-taste transition result must be a JSON object")
    output = {
        "preference": _user_taste_abstract(
            value.get("preference"), _USER_TASTE_PREFERENCE_FIELDS, "user-taste preference"
        )
    }
    if "receipt" in value:
        output["receipt"] = _user_taste_abstract(
            value["receipt"], _USER_TASTE_RECEIPT_FIELDS, "user-taste receipt"
        )
    return output


def _corpus_semantic_callback(payload: dict[str, Any]) -> Any:
    """Resolve an opt-in semantic adapter without exposing jobs in CLI output."""

    execute = payload.pop("execute_semantic", False)
    adapter_command = payload.pop("semantic_adapter_command", None)
    timeout = payload.pop("semantic_timeout_seconds", 180)
    if not isinstance(execute, bool):
        raise ValueError("execute_semantic must be a boolean")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 600:
        raise ValueError("semantic_timeout_seconds must be an integer from 1 to 600")
    if adapter_command is not None and (
        not isinstance(adapter_command, str) or not adapter_command.strip()
    ):
        raise ValueError("semantic_adapter_command must be a non-empty string")
    if not execute:
        if adapter_command is not None or timeout != 180:
            raise ValueError("semantic adapter options require execute_semantic:true")
        return None

    from harness.semantic_workers import semantic_worker_runner

    command, source = semantic_worker_runner.resolve(adapter_command, timeout=timeout)
    if not command:
        raise RuntimeError("semantic_adapter_unavailable")

    def run(job: dict[str, Any]) -> dict[str, Any]:
        result, execution = semantic_worker_runner.invoke(
            job, command, timeout, source=source
        )
        if result is None:
            code = execution.get("error_code") if isinstance(execution, dict) else None
            raise RuntimeError(str(code or "semantic_adapter_failed"))
        return result

    return run


def _run_corpus(args: argparse.Namespace) -> Any:
    operations = _core(args.data_dir)
    common = {"db_path": args.db_path, "public_root": args.public_root}
    payload = _json_object(getattr(args, "payload", None))
    reserved = sorted(set(payload).intersection(common))
    if reserved:
        raise ValueError("payload contains reserved CLI fields: " + ", ".join(reserved))
    if args.corpus_cmd == "scan":
        return operations.corpus_scan_collection(args.collection, **payload, **common)
    if args.corpus_cmd == "selection":
        handler = getattr(operations, f"corpus_{args.selection_cmd}_selection")
        return handler(**payload, **common)
    if args.corpus_cmd == "study":
        handler_name = (
            "corpus_study_status"
            if args.study_cmd == "status"
            else f"corpus_{args.study_cmd}_study"
        )
        handler = getattr(operations, handler_name)
        if args.study_cmd in {"start", "resume"}:
            callback = _corpus_semantic_callback(payload)
            if callback is not None:
                payload["run_semantic"] = callback
        elif any(
            key in payload
            for key in (
                "execute_semantic",
                "semantic_adapter_command",
                "semantic_timeout_seconds",
            )
        ):
            raise ValueError("semantic execution options are valid only for study start/resume")
        return handler(**payload, **common)
    if args.corpus_cmd == "public":
        handler = getattr(operations, f"corpus_{args.public_cmd}_public")
        return handler(**payload, **common)
    raise RuntimeError(f"unsupported corpus command: {args.corpus_cmd}")


def _run_user_taste(args: argparse.Namespace) -> Any:
    operations = _core(args.data_dir)
    if args.user_taste_cmd == "policy":
        if args.policy_cmd == "get":
            return operations.user_taste_get_policy(db_path=args.db_path)
        return operations.user_taste_set_policy(_json_object(args.payload), db_path=args.db_path)
    if args.user_taste_cmd == "list":
        preferences = operations.user_taste_list_preferences(state=args.state, db_path=args.db_path)
        if not isinstance(preferences, list):
            raise TypeError("user-taste preference list must be a JSON array")
        return [
            _user_taste_abstract(item, _USER_TASTE_PREFERENCE_FIELDS, "user-taste preference")
            for item in preferences
        ]
    if args.user_taste_cmd == "get":
        return _user_taste_abstract(
            operations.user_taste_get_preference(args.preference_id, db_path=args.db_path),
            _USER_TASTE_PREFERENCE_FIELDS,
            "user-taste preference",
        )
    if args.user_taste_cmd in {"pause", "withdraw"}:
        handler = getattr(operations, f"user_taste_{args.user_taste_cmd}_preference")
        return _user_taste_transition_output(
            handler(
                args.preference_id,
                expected_version=args.expected_version,
                reason=args.reason,
                db_path=args.db_path,
            )
        )
    raise RuntimeError(f"unsupported user-taste command: {args.user_taste_cmd}")


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

    corpus_cmd = sub.add_parser("corpus", help="Inspect and govern the local rights-safe Corpus library")
    corpus_cmd.add_argument("--data-dir")
    corpus_cmd.add_argument("--db-path")
    corpus_cmd.add_argument("--public-root")
    corpus_sub = corpus_cmd.add_subparsers(dest="corpus_cmd", required=True)
    corpus_scan = corpus_sub.add_parser("scan", help="Scan a local collection into metadata records")
    corpus_scan.add_argument("collection")
    corpus_scan.add_argument("--payload", help="JSON object, or @path, with scan options")
    corpus_selection = corpus_sub.add_parser("selection", help="Propose, refresh, or confirm a bounded analysis selection")
    selection_sub = corpus_selection.add_subparsers(dest="selection_cmd", required=True)
    for action in ("propose", "refresh", "confirm"):
        command = selection_sub.add_parser(action)
        command.add_argument("--payload", required=True, help="JSON object, or @path")
    corpus_study = corpus_sub.add_parser("study", help="Inspect or control a bounded study")
    study_sub = corpus_study.add_subparsers(dest="study_cmd", required=True)
    for action in ("status", "start", "resume", "cancel"):
        command = study_sub.add_parser(action)
        command.add_argument("--payload", help="JSON object, or @path")
    corpus_public = corpus_sub.add_parser("public", help="Preview, validate, release, or inspect public derived artifacts")
    public_sub = corpus_public.add_subparsers(dest="public_cmd", required=True)
    for action in ("preview", "validate", "release", "list", "get"):
        command = public_sub.add_parser(action)
        command.add_argument(
            "--payload",
            required=action == "release",
            help="JSON object, or @path; release requires preview_token and manifest_fingerprint",
        )

    taste_cmd = sub.add_parser("user-taste", help="Inspect durable user-taste policy and preferences")
    taste_cmd.add_argument("--data-dir")
    taste_cmd.add_argument("--db-path")
    taste_sub = taste_cmd.add_subparsers(dest="user_taste_cmd", required=True)
    taste_policy = taste_sub.add_parser("policy")
    policy_sub = taste_policy.add_subparsers(dest="policy_cmd", required=True)
    policy_sub.add_parser("get")
    policy_set = policy_sub.add_parser("set")
    policy_set.add_argument("--payload", required=True, help="JSON object, or @path")
    taste_list = taste_sub.add_parser("list")
    taste_list.add_argument("--state")
    taste_get = taste_sub.add_parser("get")
    taste_get.add_argument("preference_id")
    for action in ("pause", "withdraw"):
        command = taste_sub.add_parser(action)
        command.add_argument("preference_id")
        command.add_argument("--expected-version", type=int, required=True)
        command.add_argument("--reason", required=True)

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
        if args.cmd == "corpus":
            dump(_run_corpus(args))
            return 0
        if args.cmd == "user-taste":
            dump(_run_user_taste(args))
            return 0
        raise RuntimeError(f"unsupported command: {args.cmd}")
    except Exception as exc:
        dump({"ok": False, "code": getattr(exc, "code", type(exc).__name__), "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
