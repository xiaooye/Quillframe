#!/usr/bin/env python3
"""NovelForge deterministic settlement transaction runtime.

The runtime executes only exact, explicitly accepted and authorized project
writes. It never infers State Delta, Canon, acceptance, or literary meaning.
Semantic/project logic supplies the exact before→after intent; this module owns
CAS preconditions, rollback, postconditions, projection receipts, idempotency,
and complete vs settlement_incomplete lifecycle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from project_adapter import resolve_contract  # noqa: E402
from project_sdk import init_project  # noqa: E402

SCHEMA = "novelforge_settlement_runtime_v1"
TX_SCHEMA = "novelforge_settlement_transaction_v1"
RECEIPT_SCHEMA = "novelforge_projection_receipt_v1"
ALLOWED_OPS = {"create", "update", "delete"}
FORBIDDEN_TOP_LEVELS = {".git", ".novelforge", "dist", "__pycache__"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fingerprint_text(text: str) -> str:
    return fingerprint_bytes(text.encode("utf-8"))


def fingerprint_json(value: Any) -> str:
    return fingerprint_bytes(canonical(value))


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settlements(
          tx_id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL,
          project_root TEXT NOT NULL,
          accepted_artifact_ref TEXT NOT NULL,
          accepted_artifact_fingerprint TEXT NOT NULL,
          acceptance_evidence_ref TEXT NOT NULL,
          checkpoint_ref TEXT NOT NULL,
          write_authorization_ref TEXT NOT NULL,
          tx_fingerprint TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL,
          intent_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settlement_writes(
          tx_id TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          path TEXT NOT NULL,
          operation TEXT NOT NULL,
          before_fingerprint TEXT,
          after_fingerprint TEXT,
          PRIMARY KEY(tx_id,ordinal),
          UNIQUE(tx_id,path),
          FOREIGN KEY(tx_id) REFERENCES settlements(tx_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS settlement_projections(
          tx_id TEXT NOT NULL,
          projection_id TEXT NOT NULL,
          target TEXT NOT NULL,
          required INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          latest_attempt_id TEXT,
          output_ref TEXT,
          output_fingerprint TEXT,
          error TEXT,
          updated_at TEXT NOT NULL,
          PRIMARY KEY(tx_id,projection_id),
          FOREIGN KEY(tx_id) REFERENCES settlements(tx_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS projection_attempts(
          tx_id TEXT NOT NULL,
          projection_id TEXT NOT NULL,
          attempt_id TEXT NOT NULL,
          receipt_fingerprint TEXT NOT NULL,
          receipt_json TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(tx_id,projection_id,attempt_id),
          UNIQUE(tx_id,receipt_fingerprint),
          FOREIGN KEY(tx_id,projection_id)
            REFERENCES settlement_projections(tx_id,projection_id) ON DELETE CASCADE
        );
        """
    )
    return conn


def _sha256(value: Any, field: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be sha256:<64 hex>") from exc
    return value


def _safe_path(project_root: Path, rel: Any) -> tuple[str, Path]:
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError("write.path must be non-empty relative path")
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe project write path: {rel}")
    normalized = candidate.as_posix()
    if candidate.parts and candidate.parts[0] in FORBIDDEN_TOP_LEVELS:
        raise ValueError(f"settlement may not write framework/runtime path: {rel}")
    root = project_root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"write path escapes project root: {rel}")
    return normalized, resolved


def _current_fp(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"settlement target must be file: {path}")
    return fingerprint_bytes(path.read_bytes())


def _normalize_intent(project_root: Path, intent: dict[str, Any]) -> dict[str, Any]:
    if intent.get("schema") != TX_SCHEMA:
        raise ValueError(f"intent.schema must be {TX_SCHEMA}")
    tx_id = intent.get("tx_id")
    if not isinstance(tx_id, str) or not tx_id.strip():
        raise ValueError("tx_id required")
    resolution = resolve_contract(project_root)
    project_id = intent.get("project_id")
    if project_id != resolution.get("project_id"):
        raise ValueError("intent.project_id does not match project adapter resolution")

    artifact = intent.get("accepted_artifact")
    acceptance = intent.get("acceptance")
    if not isinstance(artifact, dict):
        raise ValueError("accepted_artifact object required")
    artifact_ref = artifact.get("ref")
    if not isinstance(artifact_ref, str) or not artifact_ref.strip():
        raise ValueError("accepted_artifact.ref required")
    artifact_fp = _sha256(artifact.get("fingerprint"), "accepted_artifact.fingerprint")
    if not isinstance(acceptance, dict) or acceptance.get("status") != "accepted":
        raise ValueError("explicit acceptance receipt with status=accepted required")
    if acceptance.get("actor") not in {"user", "authorized_human"}:
        raise ValueError("acceptance.actor must be user|authorized_human")
    evidence_ref = acceptance.get("evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError("acceptance.evidence_ref required")

    checkpoint_ref = intent.get("checkpoint_ref")
    authorization_ref = intent.get("write_authorization_ref")
    for name, value in (("checkpoint_ref", checkpoint_ref), ("write_authorization_ref", authorization_ref)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} required before consequential write")

    raw_writes = intent.get("writes")
    if not isinstance(raw_writes, list) or not raw_writes:
        raise ValueError("settlement requires at least one exact write")
    writes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_writes:
        if not isinstance(raw, dict):
            raise ValueError("write must be object")
        op = raw.get("operation")
        if op not in ALLOWED_OPS:
            raise ValueError(f"write.operation must be one of {sorted(ALLOWED_OPS)}")
        rel, _ = _safe_path(project_root, raw.get("path"))
        if rel in seen:
            raise ValueError(f"duplicate settlement write path: {rel}")
        seen.add(rel)
        before = raw.get("before_fingerprint")
        after_text = raw.get("after_text")
        if op == "create":
            if before is not None:
                raise ValueError(f"create before_fingerprint must be null: {rel}")
            if not isinstance(after_text, str):
                raise ValueError(f"create requires UTF-8 after_text: {rel}")
            after = fingerprint_text(after_text)
        elif op == "update":
            before = _sha256(before, f"{rel}.before_fingerprint")
            if not isinstance(after_text, str):
                raise ValueError(f"update requires UTF-8 after_text: {rel}")
            after = fingerprint_text(after_text)
        else:
            before = _sha256(before, f"{rel}.before_fingerprint")
            if after_text is not None:
                raise ValueError(f"delete after_text must be null/omitted: {rel}")
            after = None
        supplied_after = raw.get("after_fingerprint")
        if supplied_after is not None and supplied_after != after:
            raise ValueError(f"after_fingerprint mismatch: {rel}")
        writes.append({
            "path": rel,
            "operation": op,
            "before_fingerprint": before,
            "after_fingerprint": after,
            "after_text": after_text if op != "delete" else None,
        })

    raw_projections = intent.get("projections", [])
    if not isinstance(raw_projections, list):
        raise ValueError("projections must be list")
    projections: list[dict[str, Any]] = []
    seen_projection: set[str] = set()
    for raw in raw_projections:
        if not isinstance(raw, dict):
            raise ValueError("projection must be object")
        pid = raw.get("projection_id")
        target = raw.get("target")
        required = raw.get("required", True)
        if not isinstance(pid, str) or not pid.strip() or pid in seen_projection:
            raise ValueError("projection_id must be unique non-empty string")
        if not isinstance(target, str) or not target.strip():
            raise ValueError(f"projection target required: {pid}")
        if not isinstance(required, bool):
            raise ValueError(f"projection.required must be boolean: {pid}")
        seen_projection.add(pid)
        projections.append({"projection_id": pid.strip(), "target": target.strip(), "required": required})

    return {
        "schema": TX_SCHEMA,
        "tx_id": tx_id.strip(),
        "project_id": project_id,
        "accepted_artifact": {"ref": artifact_ref.strip(), "fingerprint": artifact_fp},
        "acceptance": {"status": "accepted", "actor": acceptance["actor"], "evidence_ref": evidence_ref.strip()},
        "checkpoint_ref": checkpoint_ref.strip(),
        "write_authorization_ref": authorization_ref.strip(),
        "writes": writes,
        "projections": projections,
    }


def _tx_fingerprint(intent: dict[str, Any]) -> str:
    payload = {
        "schema": intent["schema"],
        "tx_id": intent["tx_id"],
        "project_id": intent["project_id"],
        "accepted_artifact": intent["accepted_artifact"],
        "acceptance": intent["acceptance"],
        "checkpoint_ref": intent["checkpoint_ref"],
        "write_authorization_ref": intent["write_authorization_ref"],
        "writes": [
            {k: w[k] for k in ("path", "operation", "before_fingerprint", "after_fingerprint")}
            for w in intent["writes"]
        ],
        "projections": intent["projections"],
    }
    return fingerprint_json(payload)


def _verify_before(project_root: Path, writes: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for w in writes:
        _, path = _safe_path(project_root, w["path"])
        actual = _current_fp(path)
        if w["operation"] == "create":
            if actual is not None:
                errors.append(f"{w['path']}: create target already exists")
        elif actual != w["before_fingerprint"]:
            errors.append(f"{w['path']}: before-state mismatch")
    return errors


def _verify_after(project_root: Path, writes: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for w in writes:
        _, path = _safe_path(project_root, w["path"])
        actual = _current_fp(path)
        if w["operation"] == "delete":
            if actual is not None:
                errors.append(f"{w['path']}: delete post-condition failed")
        elif actual != w["after_fingerprint"]:
            errors.append(f"{w['path']}: after-state fingerprint mismatch")
    return errors


def _row(conn: sqlite3.Connection, tx_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM settlements WHERE tx_id=?", (tx_id,)).fetchone()
    if not row:
        raise ValueError(f"unknown tx_id: {tx_id}")
    return row


def _intent(row: sqlite3.Row) -> dict[str, Any]:
    value = json.loads(row["intent_json"])
    if not isinstance(value, dict):
        raise ValueError("stored intent corrupted")
    return value


def prepare(conn: sqlite3.Connection, project_root: Path, raw_intent: dict[str, Any]) -> dict[str, Any]:
    project_root = project_root.resolve()
    intent = _normalize_intent(project_root, raw_intent)
    tx_fp = _tx_fingerprint(intent)
    existing = conn.execute("SELECT * FROM settlements WHERE tx_id=?", (intent["tx_id"],)).fetchone()
    if existing:
        if existing["tx_fingerprint"] != tx_fp or existing["project_root"] != str(project_root):
            raise ValueError("tx_id already exists with different frozen intent")
        return status(conn, intent["tx_id"])

    before_errors = _verify_before(project_root, intent["writes"])
    if before_errors:
        raise ValueError("before-state mismatch; settlement not prepared: " + "; ".join(before_errors))
    stamp = now()
    conn.execute(
        """INSERT INTO settlements(
             tx_id,project_id,project_root,accepted_artifact_ref,accepted_artifact_fingerprint,
             acceptance_evidence_ref,checkpoint_ref,write_authorization_ref,tx_fingerprint,
             status,intent_json,created_at,updated_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            intent["tx_id"], intent["project_id"], str(project_root), intent["accepted_artifact"]["ref"],
            intent["accepted_artifact"]["fingerprint"], intent["acceptance"]["evidence_ref"],
            intent["checkpoint_ref"], intent["write_authorization_ref"], tx_fp, "prepared",
            json.dumps(intent, ensure_ascii=False, sort_keys=True), stamp, stamp,
        ),
    )
    for i, w in enumerate(intent["writes"]):
        conn.execute(
            "INSERT INTO settlement_writes(tx_id,ordinal,path,operation,before_fingerprint,after_fingerprint) VALUES(?,?,?,?,?,?)",
            (intent["tx_id"], i, w["path"], w["operation"], w["before_fingerprint"], w["after_fingerprint"]),
        )
    for p in intent["projections"]:
        conn.execute(
            "INSERT INTO settlement_projections(tx_id,projection_id,target,required,status,updated_at) VALUES(?,?,?,?,?,?)",
            (intent["tx_id"], p["projection_id"], p["target"], int(p["required"]), "pending", stamp),
        )
    conn.commit()
    return status(conn, intent["tx_id"])


def apply_authority(conn: sqlite3.Connection, tx_id: str) -> dict[str, Any]:
    row = _row(conn, tx_id)
    intent = _intent(row)
    root = Path(row["project_root"])
    if row["status"] in {"authority_applied", "settlement_incomplete", "complete"}:
        after_errors = _verify_after(root, intent["writes"])
        if not after_errors:
            return status(conn, tx_id)
        raise ValueError("previously applied settlement no longer matches after-state: " + "; ".join(after_errors))
    if row["status"] != "prepared":
        raise ValueError(f"settlement not applicable from state {row['status']}")

    before_errors = _verify_before(root, intent["writes"])
    if before_errors:
        raise ValueError("before-state mismatch; no writes performed: " + "; ".join(before_errors))

    backups: dict[str, bytes | None] = {}
    applied: list[dict[str, Any]] = []
    try:
        for w in intent["writes"]:
            rel, path = _safe_path(root, w["path"])
            backups[rel] = path.read_bytes() if path.exists() else None
            path.parent.mkdir(parents=True, exist_ok=True)
            if w["operation"] == "delete":
                path.unlink()
            else:
                data = w["after_text"].encode("utf-8")
                fd, temp_name = tempfile.mkstemp(prefix=".novelforge-settle-", dir=str(path.parent))
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(data)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp_name, path)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
            applied.append(w)
        after_errors = _verify_after(root, intent["writes"])
        if after_errors:
            raise RuntimeError("; ".join(after_errors))
    except Exception as exc:
        rollback_errors: list[str] = []
        for w in reversed(applied):
            rel, path = _safe_path(root, w["path"])
            before = backups.get(rel)
            try:
                if before is None:
                    if path.exists():
                        path.unlink()
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(before)
            except Exception as rollback_exc:
                rollback_errors.append(f"{rel}: {rollback_exc}")
        if rollback_errors:
            conn.execute("UPDATE settlements SET status='settlement_incomplete',updated_at=? WHERE tx_id=?", (now(), tx_id))
            conn.commit()
            raise RuntimeError(f"settlement write failed ({exc}); rollback incomplete: " + "; ".join(rollback_errors)) from exc
        raise RuntimeError(f"settlement write failed and was rolled back: {exc}") from exc

    conn.execute("UPDATE settlements SET status='authority_applied',updated_at=? WHERE tx_id=?", (now(), tx_id))
    conn.commit()
    return status(conn, tx_id)


def record_projection(conn: sqlite3.Connection, tx_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
    row = _row(conn, tx_id)
    if row["status"] not in {"authority_applied", "settlement_incomplete"}:
        raise ValueError("projection receipts require authoritative writes to be applied first")
    after_errors = _verify_after(Path(row["project_root"]), _intent(row)["writes"])
    if after_errors:
        raise ValueError("projection receipt rejected because authoritative after-state drifted: " + "; ".join(after_errors))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError(f"receipt.schema must be {RECEIPT_SCHEMA}")
    if receipt.get("tx_id") != tx_id or receipt.get("tx_fingerprint") != row["tx_fingerprint"]:
        raise ValueError("projection receipt transaction binding mismatch")
    pid = receipt.get("projection_id")
    attempt_id = receipt.get("attempt_id")
    result_status = receipt.get("status")
    if not isinstance(pid, str) or not pid:
        raise ValueError("projection_id required")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise ValueError("attempt_id required")
    if result_status not in {"success", "failed"}:
        raise ValueError("projection receipt status must be success|failed")
    projection = conn.execute(
        "SELECT * FROM settlement_projections WHERE tx_id=? AND projection_id=?", (tx_id, pid)
    ).fetchone()
    if not projection:
        raise ValueError(f"undeclared projection_id: {pid}")
    output_fp = receipt.get("output_fingerprint")
    if output_fp is not None:
        _sha256(output_fp, "output_fingerprint")
    if result_status == "success" and receipt.get("error"):
        raise ValueError("successful projection receipt may not contain error")
    if result_status == "failed" and not isinstance(receipt.get("error"), str):
        raise ValueError("failed projection receipt requires error")

    receipt_fp = fingerprint_json(receipt)
    existing = conn.execute(
        "SELECT * FROM projection_attempts WHERE tx_id=? AND projection_id=? AND attempt_id=?",
        (tx_id, pid, attempt_id),
    ).fetchone()
    if existing:
        if existing["receipt_fingerprint"] != receipt_fp:
            raise ValueError("projection attempt_id already exists with different receipt")
        return status(conn, tx_id)
    if projection["status"] == "success":
        raise ValueError(f"projection {pid} already succeeded; later receipts are forbidden")
    stamp = now()
    conn.execute(
        "INSERT INTO projection_attempts(tx_id,projection_id,attempt_id,receipt_fingerprint,receipt_json,status,created_at) VALUES(?,?,?,?,?,?,?)",
        (tx_id, pid, attempt_id, receipt_fp, json.dumps(receipt, ensure_ascii=False, sort_keys=True), result_status, stamp),
    )
    conn.execute(
        """UPDATE settlement_projections
           SET status=?,latest_attempt_id=?,output_ref=?,output_fingerprint=?,error=?,updated_at=?
           WHERE tx_id=? AND projection_id=?""",
        (result_status, attempt_id, receipt.get("output_ref"), output_fp, receipt.get("error"), stamp, tx_id, pid),
    )
    conn.commit()
    return status(conn, tx_id)


def finalize(conn: sqlite3.Connection, tx_id: str) -> dict[str, Any]:
    row = _row(conn, tx_id)
    if row["status"] == "complete":
        return status(conn, tx_id)
    if row["status"] == "prepared":
        raise ValueError("cannot finalize before authoritative writes are applied")
    after_errors = _verify_after(Path(row["project_root"]), _intent(row)["writes"])
    projection_rows = conn.execute(
        "SELECT projection_id,required,status FROM settlement_projections WHERE tx_id=?", (tx_id,)
    ).fetchall()
    unresolved = [p["projection_id"] for p in projection_rows if p["required"] and p["status"] != "success"]
    new_status = "complete" if not after_errors and not unresolved else "settlement_incomplete"
    conn.execute("UPDATE settlements SET status=?,updated_at=? WHERE tx_id=?", (new_status, now(), tx_id))
    conn.commit()
    value = status(conn, tx_id)
    value["finalize_errors"] = after_errors
    value["required_projections_unresolved"] = unresolved
    return value


def status(conn: sqlite3.Connection, tx_id: str) -> dict[str, Any]:
    row = _row(conn, tx_id)
    writes = [dict(r) for r in conn.execute(
        "SELECT ordinal,path,operation,before_fingerprint,after_fingerprint FROM settlement_writes WHERE tx_id=? ORDER BY ordinal",
        (tx_id,),
    )]
    projections = [{**dict(r), "required": bool(r["required"])} for r in conn.execute(
        """SELECT projection_id,target,required,status,latest_attempt_id,output_ref,output_fingerprint,error,updated_at
           FROM settlement_projections WHERE tx_id=? ORDER BY projection_id""",
        (tx_id,),
    )]
    attempts = [dict(r) for r in conn.execute(
        "SELECT projection_id,attempt_id,receipt_fingerprint,status,created_at FROM projection_attempts WHERE tx_id=? ORDER BY created_at,projection_id,attempt_id",
        (tx_id,),
    )]
    return {
        "schema": SCHEMA,
        "tx_id": row["tx_id"],
        "project_id": row["project_id"],
        "project_root": row["project_root"],
        "accepted_artifact_ref": row["accepted_artifact_ref"],
        "accepted_artifact_fingerprint": row["accepted_artifact_fingerprint"],
        "acceptance_evidence_ref": row["acceptance_evidence_ref"],
        "checkpoint_ref": row["checkpoint_ref"],
        "write_authorization_ref": row["write_authorization_ref"],
        "tx_fingerprint": row["tx_fingerprint"],
        "status": row["status"],
        "writes": writes,
        "projections": projections,
        "projection_attempts": attempts,
        "semantic_inference_performed": False,
        "model_execution": False,
    }


def self_test(path: Path, project_root: Path) -> int:
    if path.exists():
        path.unlink()
    if project_root.exists():
        shutil.rmtree(project_root)
    init_project(project_root, "PROJECT-SETTLE-TEST", "Settlement Fixture", "en", "0.8.0", False)
    target = project_root / "state" / "canon" / "TEST.json"
    target.write_text('{"value":"before"}\n', encoding="utf-8")
    before = fingerprint_bytes(target.read_bytes())
    conn = connect(path)
    intent = {
        "schema": TX_SCHEMA,
        "tx_id": "SETTLE-1",
        "project_id": "PROJECT-SETTLE-TEST",
        "accepted_artifact": {"ref": "manuscripts/accepted/CH-1.md", "fingerprint": "sha256:" + "a" * 64},
        "acceptance": {"status": "accepted", "actor": "user", "evidence_ref": "session:user-acceptance-1"},
        "checkpoint_ref": "checkpoint:before-settle-1",
        "write_authorization_ref": "authorization:settle-1",
        "writes": [{
            "path": "state/canon/TEST.json",
            "operation": "update",
            "before_fingerprint": before,
            "after_text": '{"value":"after"}\n',
        }],
        "projections": [
            {"projection_id": "memory", "target": "memory-bank", "required": True},
            {"projection_id": "search-index", "target": "index", "required": False},
        ],
    }
    prepared = prepare(conn, project_root, intent)
    frozen_tx = prepare(conn, project_root, intent)["tx_fingerprint"] == prepared["tx_fingerprint"]

    target.write_text('{"value":"raced"}\n', encoding="utf-8")
    cas_guard = False
    try:
        apply_authority(conn, "SETTLE-1")
    except ValueError as exc:
        cas_guard = "before-state mismatch" in str(exc)
    target.write_text('{"value":"before"}\n', encoding="utf-8")
    applied = apply_authority(conn, "SETTLE-1")
    authority_ok = applied["status"] == "authority_applied" and target.read_text(encoding="utf-8") == '{"value":"after"}\n'
    prepare_after_apply = prepare(conn, project_root, intent)["status"] == "authority_applied"

    record_projection(conn, "SETTLE-1", {
        "schema": RECEIPT_SCHEMA,
        "tx_id": "SETTLE-1",
        "tx_fingerprint": prepared["tx_fingerprint"],
        "projection_id": "memory",
        "attempt_id": "MEM-1",
        "status": "failed",
        "error": "fixture projection failure",
    })
    incomplete = finalize(conn, "SETTLE-1")
    incomplete_guard = incomplete["status"] == "settlement_incomplete" and incomplete["required_projections_unresolved"] == ["memory"]
    record_projection(conn, "SETTLE-1", {
        "schema": RECEIPT_SCHEMA,
        "tx_id": "SETTLE-1",
        "tx_fingerprint": prepared["tx_fingerprint"],
        "projection_id": "memory",
        "attempt_id": "MEM-2",
        "status": "success",
        "output_ref": "memory://SETTLE-1",
        "output_fingerprint": "sha256:" + "b" * 64,
    })
    complete_value = finalize(conn, "SETTLE-1")
    complete_replay = finalize(conn, "SETTLE-1")
    projection_retry = any(x["attempt_id"] == "MEM-2" for x in complete_value["projection_attempts"])
    ok = all((
        frozen_tx, cas_guard, authority_ok, prepare_after_apply, incomplete_guard,
        projection_retry, complete_value["status"] == "complete", complete_replay["status"] == "complete",
    ))
    dump({
        "settlement_runtime_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "exact_before_after_bound": True,
        "acceptance_receipt_required": True,
        "checkpoint_and_authorization_required": True,
        "compare_and_swap_guard": cas_guard,
        "prepare_replay_after_apply": prepare_after_apply,
        "authoritative_postcondition": authority_ok,
        "required_projection_failure_blocks_completion": incomplete_guard,
        "projection_retry_supported": projection_retry,
        "complete_only_after_required_projections": complete_value["status"] == "complete",
        "semantic_inference_performed": False,
        "model_execution": False,
    })
    conn.close()
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge deterministic settlement transaction runtime")
    p.add_argument("--db", default=".novelforge/settlement.db")
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--project-root", required=True)
    prep.add_argument("--intent-json", required=True)
    apply = sub.add_parser("apply-authority")
    apply.add_argument("--tx-id", required=True)
    rec = sub.add_parser("record-projection")
    rec.add_argument("--tx-id", required=True)
    rec.add_argument("--receipt-json", required=True)
    fin = sub.add_parser("finalize")
    fin.add_argument("--tx-id", required=True)
    st = sub.add_parser("status")
    st.add_argument("--tx-id", required=True)
    test = sub.add_parser("self-test")
    test.add_argument("--path", default="/tmp/novelforge-settlement-selftest.db")
    test.add_argument("--project-root", default="/tmp/novelforge-settlement-project")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test(Path(args.path), Path(args.project_root))
    conn = connect(Path(args.db))
    try:
        if args.command == "prepare":
            value = prepare(conn, Path(args.project_root), load_json(args.intent_json))
        elif args.command == "apply-authority":
            value = apply_authority(conn, args.tx_id)
        elif args.command == "record-projection":
            value = record_projection(conn, args.tx_id, load_json(args.receipt_json))
        elif args.command == "finalize":
            value = finalize(conn, args.tx_id)
        else:
            value = status(conn, args.tx_id)
        dump(value)
        return 0 if args.command != "finalize" or value["status"] == "complete" else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
