#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import ConflictError, IntegrityError, QuillframeStore


def dump(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe SQLite persistence and product operations")
    p.add_argument("--data-dir")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor"); d.add_argument("--project-id"); d.add_argument("--fix", action="store_true")
    c = sub.add_parser("create-project"); c.add_argument("project_id"); c.add_argument("title"); c.add_argument("--language", default="zh-CN")
    b = sub.add_parser("backup"); b.add_argument("project_id"); b.add_argument("--output")
    v = sub.add_parser("verify-backup"); v.add_argument("bundle")
    r = sub.add_parser("restore"); r.add_argument("bundle"); r.add_argument("--replace", action="store_true")
    s = sub.add_parser("search"); s.add_argument("project_id"); s.add_argument("query"); s.add_argument("--limit", type=int, default=30)
    args = p.parse_args()
    store = QuillframeStore(Path(args.data_dir) if args.data_dir else None)
    try:
        if args.cmd == "doctor": dump(store.doctor(args.project_id, fix=args.fix)); return 0
        if args.cmd == "create-project":
            loc = store.create_project(args.project_id, args.title, args.language); dump({"created": True, "project_id": args.project_id, "data_root": str(store.root), "project_dir": str(loc.directory)}); return 0
        if args.cmd == "backup": dump({"bundle": str(store.backup_project(args.project_id, Path(args.output) if args.output else None))}); return 0
        if args.cmd == "verify-backup": result=store.verify_backup(Path(args.bundle)); dump(result); return 0 if result["valid"] else 1
        if args.cmd == "restore": loc=store.restore_project(Path(args.bundle), replace=args.replace); dump({"restored": True, "project_id": loc.project_id}); return 0
        if args.cmd == "search": dump({"schema":"quillframe_search_results_v1","results":store.search(args.project_id,args.query,args.limit)}); return 0
    except (OperationError, ConflictError, IntegrityError, FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        dump({"ok": False, "code": getattr(exc, "code", type(exc).__name__), "message": str(exc), "detail": getattr(exc, "detail", None)})
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
