#!/usr/bin/env python3
"""Metadata-only run observability receipts for NovelForge.

A receipt records what a run actually loaded/executed: artifact fingerprints,
context-selection fingerprints, question→evidence loading, semantic job
identities, and deterministic guard outcomes. It never stores candidate prose,
creates memory claims, or gains Canon/Framework authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from control_plane import ControlPlane, EVENT_SCHEMA, now_iso  # noqa: E402

RECEIPT_SCHEMA = "novelforge_run_receipt_v1"
TOP_KEYS = {
    "schema", "receipt_id", "resource_id", "session_id", "run_id", "stage",
    "subject_id", "artifact_fingerprints", "context", "semantic_jobs",
    "guards", "created_at", "authority",
}
CONTEXT_KEYS = {
    "selection_fingerprint", "loaded_block_ids", "visibility_excluded_block_ids",
    "question_grounding", "unresolved_questions", "grounding_incomplete_due_budget",
}
GROUNDING_KEYS = {
    "question_id", "model_support", "support_block_ids", "loaded_support_block_ids",
    "dropped_support_block_ids", "loading_status",
}
SEMANTIC_JOB_KEYS = {
    "job_id", "contract_id", "input_fingerprint", "status",
    "result_fingerprint", "worker_ref",
}
GUARD_KEYS = {"guard_id", "status", "evidence_refs"}
MODEL_SUPPORT = {"sufficient", "partial", "none"}
LOADING_STATUS = {"all_loaded", "partially_loaded", "not_loaded", "no_support_identified"}
JOB_STATUS = {"prepared", "pending", "completed", "semantic_reject", "invalid", "failed", "unsupported"}
GUARD_STATUS = {"pass", "fail", "pending"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(x) for x in value)


def _unexpected(value: dict[str, Any], allowed: set[str], path: str, errors: list[str]) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        errors.append(f"{path}: unexpected fields: {', '.join(extra)}")


def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt must be object"]
    _unexpected(receipt, TOP_KEYS, "$", errors)
    missing = sorted(TOP_KEYS - set(receipt))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
        return errors
    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("invalid receipt schema")
    for key in ("receipt_id", "resource_id", "session_id", "run_id", "stage", "subject_id", "created_at"):
        if not _nonempty(receipt.get(key)):
            errors.append(f"{key} must be non-empty string")
    if receipt.get("authority") is not False:
        errors.append("run receipt authority must be false")
    if not _string_list(receipt.get("artifact_fingerprints")):
        errors.append("artifact_fingerprints must be non-empty-string list")

    context = receipt.get("context")
    if not isinstance(context, dict):
        errors.append("context must be object")
    else:
        _unexpected(context, CONTEXT_KEYS, "$.context", errors)
        missing_context = sorted(CONTEXT_KEYS - set(context))
        if missing_context:
            errors.append("context missing: " + ", ".join(missing_context))
        sf = context.get("selection_fingerprint")
        if sf is not None and not _nonempty(sf):
            errors.append("context.selection_fingerprint must be string|null")
        for key in ("loaded_block_ids", "visibility_excluded_block_ids", "unresolved_questions", "grounding_incomplete_due_budget"):
            if not _string_list(context.get(key)) and context.get(key) != []:
                errors.append(f"context.{key} must be string list")
        grounding = context.get("question_grounding")
        if not isinstance(grounding, list):
            errors.append("context.question_grounding must be list")
        else:
            seen_questions: set[str] = set()
            for i, row in enumerate(grounding):
                path = f"$.context.question_grounding[{i}]"
                if not isinstance(row, dict):
                    errors.append(f"{path}: must be object"); continue
                _unexpected(row, GROUNDING_KEYS, path, errors)
                missing_row = sorted(GROUNDING_KEYS - set(row))
                if missing_row:
                    errors.append(f"{path}: missing {', '.join(missing_row)}"); continue
                qid = row.get("question_id")
                if not _nonempty(qid):
                    errors.append(f"{path}.question_id required")
                elif qid in seen_questions:
                    errors.append(f"{path}.question_id duplicate: {qid}")
                else:
                    seen_questions.add(qid)
                if row.get("model_support") not in MODEL_SUPPORT:
                    errors.append(f"{path}.model_support invalid")
                if row.get("loading_status") not in LOADING_STATUS:
                    errors.append(f"{path}.loading_status invalid")
                for key in ("support_block_ids", "loaded_support_block_ids", "dropped_support_block_ids"):
                    if not _string_list(row.get(key)) and row.get(key) != []:
                        errors.append(f"{path}.{key} must be string list")
                support = set(row.get("support_block_ids", []))
                loaded = set(row.get("loaded_support_block_ids", []))
                dropped = set(row.get("dropped_support_block_ids", []))
                if loaded & dropped:
                    errors.append(f"{path}: loaded and dropped support overlap")
                if loaded | dropped != support:
                    errors.append(f"{path}: loaded+dropped support must exactly partition support_block_ids")
                expected_loading = (
                    "no_support_identified" if not support else
                    "all_loaded" if loaded == support else
                    "partially_loaded" if loaded else
                    "not_loaded"
                )
                if row.get("loading_status") != expected_loading:
                    errors.append(f"{path}: loading_status does not match loaded/dropped evidence")
        if isinstance(grounding, list):
            qids = {row.get("question_id") for row in grounding if isinstance(row, dict)}
            for key in ("unresolved_questions", "grounding_incomplete_due_budget"):
                unknown = sorted(set(context.get(key, [])) - qids)
                if unknown:
                    errors.append(f"context.{key} references unknown questions: {', '.join(unknown)}")

    jobs = receipt.get("semantic_jobs")
    if not isinstance(jobs, list):
        errors.append("semantic_jobs must be list")
    else:
        seen_jobs: set[str] = set()
        for i, row in enumerate(jobs):
            path = f"$.semantic_jobs[{i}]"
            if not isinstance(row, dict):
                errors.append(f"{path}: must be object"); continue
            _unexpected(row, SEMANTIC_JOB_KEYS, path, errors)
            for key in ("job_id", "contract_id", "input_fingerprint", "status"):
                if key not in row:
                    errors.append(f"{path}: missing {key}")
            jid = row.get("job_id")
            if _nonempty(jid):
                if jid in seen_jobs: errors.append(f"{path}.job_id duplicate: {jid}")
                seen_jobs.add(jid)
            else:
                errors.append(f"{path}.job_id required")
            if not _nonempty(row.get("contract_id")): errors.append(f"{path}.contract_id required")
            if not _nonempty(row.get("input_fingerprint")): errors.append(f"{path}.input_fingerprint required")
            if row.get("status") not in JOB_STATUS: errors.append(f"{path}.status invalid")
            for key in ("result_fingerprint", "worker_ref"):
                if row.get(key) is not None and not _nonempty(row.get(key)):
                    errors.append(f"{path}.{key} must be string|null")

    guards = receipt.get("guards")
    if not isinstance(guards, list):
        errors.append("guards must be list")
    else:
        seen_guards: set[str] = set()
        for i, row in enumerate(guards):
            path = f"$.guards[{i}]"
            if not isinstance(row, dict):
                errors.append(f"{path}: must be object"); continue
            _unexpected(row, GUARD_KEYS, path, errors)
            missing_guard = sorted(GUARD_KEYS - set(row))
            if missing_guard:
                errors.append(f"{path}: missing {', '.join(missing_guard)}"); continue
            gid = row.get("guard_id")
            if not _nonempty(gid):
                errors.append(f"{path}.guard_id required")
            elif gid in seen_guards:
                errors.append(f"{path}.guard_id duplicate: {gid}")
            else:
                seen_guards.add(gid)
            if row.get("status") not in GUARD_STATUS:
                errors.append(f"{path}.status invalid")
            if not _string_list(row.get("evidence_refs")) and row.get("evidence_refs") != []:
                errors.append(f"{path}.evidence_refs must be string list")
    return errors


def receipt_event(receipt: dict[str, Any], *, source_kind: str,
                  actor: str | None = None, transport: str | None = None) -> dict[str, Any]:
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("invalid run receipt: " + "; ".join(errors))
    if not _nonempty(source_kind):
        raise ValueError("source_kind required")
    rid = receipt["receipt_id"]
    event_suffix = hashlib.sha256(rid.encode("utf-8")).hexdigest()[:24]
    return {
        "schema": EVENT_SCHEMA,
        "event_id": "EV-RCPT-" + event_suffix,
        "event_type": "run.receipt_recorded",
        "source": {"kind": source_kind, "actor": actor, "transport": transport, "external_ref": None},
        "resource_id": receipt["resource_id"],
        "session_id": receipt["session_id"],
        "run_id": receipt["run_id"],
        "handoff_id": None,
        "authority_scope": "observation",
        "idempotency_key": "run-receipt:" + rid,
        "artifact_fingerprints": list(receipt["artifact_fingerprints"]),
        "created_at": receipt["created_at"],
        "payload": {"receipt": receipt},
    }


def record_receipt(db_path: str | Path, receipt: dict[str, Any], *, source_kind: str,
                   actor: str | None = None, transport: str | None = None) -> dict[str, Any]:
    event = receipt_event(receipt, source_kind=source_kind, actor=actor, transport=transport)
    cp = ControlPlane(db_path)
    cp.init()
    result = cp.ingest_event(event)
    return {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": receipt["receipt_id"],
        "recorded": result["accepted"],
        "duplicate": result["duplicate"],
        "event_id": result["event_id"],
        "event_payload_hash": result["payload_hash"],
        "authority": False,
    }


def fixture() -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": "RCPT-SELF",
        "resource_id": "BOOK-SELF",
        "session_id": "SES-SELF",
        "run_id": "RUN-SELF",
        "stage": "context-freeze",
        "subject_id": "SCN-SELF",
        "artifact_fingerprints": ["sha256:" + "a" * 64],
        "context": {
            "selection_fingerprint": "sha256:" + "b" * 64,
            "loaded_block_ids": ["M-A"],
            "visibility_excluded_block_ids": ["M-HIDDEN"],
            "question_grounding": [
                {
                    "question_id": "Q-A",
                    "model_support": "partial",
                    "support_block_ids": ["M-A", "M-B"],
                    "loaded_support_block_ids": ["M-A"],
                    "dropped_support_block_ids": ["M-B"],
                    "loading_status": "partially_loaded",
                }
            ],
            "unresolved_questions": ["Q-A"],
            "grounding_incomplete_due_budget": ["Q-A"],
        },
        "semantic_jobs": [
            {
                "job_id": "SEM-A",
                "contract_id": "context.select",
                "input_fingerprint": "sha256:" + "c" * 64,
                "status": "completed",
                "result_fingerprint": "sha256:" + "d" * 64,
                "worker_ref": "SES-WORKER-A",
            }
        ],
        "guards": [
            {"guard_id": "context-budget", "status": "pass", "evidence_refs": ["RCPT-SELF:context"]}
        ],
        "created_at": now_iso(),
        "authority": False,
    }


def self_test(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path)
    if db.exists(): db.unlink()
    good = fixture()
    valid = not validate_receipt(good)
    first = record_receipt(db, good, source_kind="self_test", actor="run_receipt.py")
    duplicate = record_receipt(db, good, source_kind="self_test", actor="run_receipt.py")

    arbitrary_payload_blocked = False
    bad = json.loads(json.dumps(good)); bad["candidate_text"] = "must never be stored in receipt"
    arbitrary_payload_blocked = bool(validate_receipt(bad))
    authority_guard = False
    bad = json.loads(json.dumps(good)); bad["authority"] = True
    authority_guard = bool(validate_receipt(bad))
    partition_guard = False
    bad = json.loads(json.dumps(good)); bad["context"]["question_grounding"][0]["loaded_support_block_ids"] = []
    partition_guard = bool(validate_receipt(bad))
    idempotency_conflict = False
    changed = json.loads(json.dumps(good)); changed["stage"] = "different-stage"
    try:
        record_receipt(db, changed, source_kind="self_test", actor="run_receipt.py")
    except ValueError:
        idempotency_conflict = True
    ok = all((valid, first["recorded"], duplicate["duplicate"], arbitrary_payload_blocked,
              authority_guard, partition_guard, idempotency_conflict))
    return {
        "run_receipt_contract": "PASS" if ok else "FAIL",
        "metadata_only": arbitrary_payload_blocked,
        "authority": False,
        "question_evidence_partition_guard": partition_guard,
        "idempotent_replay": duplicate["duplicate"],
        "same_receipt_id_changed_payload_conflict": idempotency_conflict,
        "durable_store": "control_plane_event_log",
        "model_execution": False,
    }


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("JSON root must be object")
    return value


def dump(value: Any, path: str | Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path: Path(path).write_text(text, encoding="utf-8")
    else: print(text, end="")


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge metadata-only run receipt boundary")
    p.add_argument("--db", default=os.getenv("NOVELFORGE_DB", ".novelforge/runtime.db"))
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate"); v.add_argument("--receipt", required=True)
    e = sub.add_parser("event"); e.add_argument("--receipt", required=True); e.add_argument("--source-kind", required=True); e.add_argument("--actor"); e.add_argument("--transport"); e.add_argument("--output")
    r = sub.add_parser("record"); r.add_argument("--receipt", required=True); r.add_argument("--source-kind", required=True); r.add_argument("--actor"); r.add_argument("--transport")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        result = self_test(args.db); dump(result); return 0 if result["run_receipt_contract"] == "PASS" else 1
    receipt = load(args.receipt)
    if args.command == "validate":
        errors = validate_receipt(receipt); dump({"valid": not errors, "errors": errors}); return 0 if not errors else 1
    if args.command == "event":
        value = receipt_event(receipt, source_kind=args.source_kind, actor=args.actor, transport=args.transport); dump(value, args.output); return 0
    value = record_receipt(args.db, receipt, source_kind=args.source_kind, actor=args.actor, transport=args.transport); dump(value); return 0


if __name__ == "__main__":
    raise SystemExit(main())
