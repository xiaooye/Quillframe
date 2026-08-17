#!/usr/bin/env python3
"""Candidate lineage extension for NovelForge quality evolution.

This module extends the existing ``quality_evolution`` ledger; it does not create
another candidate-selection, comparison, acceptance, Canon, or settlement system.
The existing ``parent_candidate_id`` remains the direct comparison ancestry used
by ``quality.compare``.  This extension records the distinct prose-derivation
relationship plus exact review/acceptance bindings so a fresh regeneration can
compete with the incumbent without pretending to inherit rejected prose.

Everything here is derived/provenance state (authority=false).  In particular,
an acceptance binding can only mirror an explicit acceptance receipt supplied by
an external authority layer, and settlement validation only checks exact binding;
neither function grants authority or writes Canon.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "quality"
SEM = ROOT / "harness" / "semantic_workers"
for p in (QUALITY, SEM):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import quality_evolution as qe  # noqa: E402
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402

SCHEMA = "novelforge_candidate_lineage_v1"
ORIGINS = {"draft", "repair", "fresh_regeneration", "user_edit"}


def migrate(conn: sqlite3.Connection) -> None:
    """Install additive companion tables against the existing evolution DB."""
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS evolution_candidate_lineage(
          run_id TEXT NOT NULL,
          candidate_id TEXT NOT NULL,
          origin TEXT NOT NULL CHECK(origin IN ('draft','repair','fresh_regeneration','user_edit')),
          comparison_parent_candidate_id TEXT,
          prose_parent_candidate_id TEXT,
          created_by_run_id TEXT NOT NULL,
          created_by_session_id TEXT,
          authority_snapshot_fingerprint TEXT,
          diff_fingerprint TEXT,
          created_at TEXT NOT NULL,
          authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0),
          PRIMARY KEY(run_id,candidate_id),
          FOREIGN KEY(run_id,candidate_id)
            REFERENCES evolution_candidates(run_id,candidate_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS evolution_review_receipts(
          run_id TEXT NOT NULL,
          review_id TEXT NOT NULL,
          candidate_id TEXT NOT NULL,
          candidate_fingerprint TEXT NOT NULL,
          contract_id TEXT NOT NULL,
          job_fingerprint TEXT NOT NULL,
          result_fingerprint TEXT NOT NULL,
          result_status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0),
          PRIMARY KEY(run_id,review_id),
          UNIQUE(run_id,job_fingerprint),
          UNIQUE(run_id,result_fingerprint),
          FOREIGN KEY(run_id,candidate_id)
            REFERENCES evolution_candidates(run_id,candidate_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS evolution_acceptance_bindings(
          run_id TEXT NOT NULL,
          acceptance_id TEXT NOT NULL,
          candidate_id TEXT NOT NULL,
          candidate_fingerprint TEXT NOT NULL,
          authority_source_ref TEXT NOT NULL,
          accepted_artifact_fingerprint TEXT NOT NULL,
          accepted_at TEXT NOT NULL,
          created_at TEXT NOT NULL,
          authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0),
          PRIMARY KEY(run_id,acceptance_id),
          UNIQUE(run_id,authority_source_ref),
          FOREIGN KEY(run_id,candidate_id)
            REFERENCES evolution_candidates(run_id,candidate_id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def _fp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256 fingerprint")
    return value


def _candidate(conn: sqlite3.Connection, run_id: str, candidate_id: str) -> sqlite3.Row:
    return qe._candidate(conn, run_id, candidate_id)  # same ledger; no duplicate authority


def register_candidate(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    candidate_id: str,
    origin: str,
    prose_parent_candidate_id: str | None,
    created_by_run_id: str,
    created_by_session_id: str | None = None,
    authority_snapshot_fingerprint: str | None = None,
    diff_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Attach derivation lineage to an already-created evolution candidate."""
    migrate(conn)
    if origin not in ORIGINS:
        raise ValueError(f"invalid origin: {origin}")
    row = _candidate(conn, run_id, candidate_id)
    comparison_parent = row["parent_candidate_id"]
    if not isinstance(created_by_run_id, str) or not created_by_run_id.strip():
        raise ValueError("created_by_run_id required")
    if authority_snapshot_fingerprint is not None:
        _fp(authority_snapshot_fingerprint, "authority_snapshot_fingerprint")
    if diff_fingerprint is not None:
        _fp(diff_fingerprint, "diff_fingerprint")

    if prose_parent_candidate_id is not None:
        _candidate(conn, run_id, prose_parent_candidate_id)
    if origin == "draft":
        if comparison_parent is not None or prose_parent_candidate_id is not None:
            raise ValueError("draft baseline cannot have comparison/prose parent")
    elif origin == "repair":
        if comparison_parent is None or prose_parent_candidate_id != comparison_parent:
            raise ValueError("repair must derive prose from its direct comparison parent")
    elif origin == "fresh_regeneration":
        if comparison_parent is None:
            raise ValueError("fresh regeneration must still have a comparison parent")
        if prose_parent_candidate_id is not None:
            raise ValueError("fresh regeneration must not inherit rejected/incumbent prose")
    elif origin == "user_edit" and comparison_parent is None:
        raise ValueError("user_edit challenger requires a comparison parent")

    values = (
        run_id,
        candidate_id,
        origin,
        comparison_parent,
        prose_parent_candidate_id,
        created_by_run_id,
        created_by_session_id,
        authority_snapshot_fingerprint,
        diff_fingerprint,
        qe.now(),
    )
    existing = conn.execute(
        "SELECT * FROM evolution_candidate_lineage WHERE run_id=? AND candidate_id=?",
        (run_id, candidate_id),
    ).fetchone()
    if existing:
        same = (
            existing["origin"] == origin
            and existing["comparison_parent_candidate_id"] == comparison_parent
            and existing["prose_parent_candidate_id"] == prose_parent_candidate_id
            and existing["created_by_run_id"] == created_by_run_id
            and existing["created_by_session_id"] == created_by_session_id
            and existing["authority_snapshot_fingerprint"] == authority_snapshot_fingerprint
            and existing["diff_fingerprint"] == diff_fingerprint
        )
        if not same:
            raise ValueError("candidate lineage is immutable and already differs")
    else:
        conn.execute(
            """INSERT INTO evolution_candidate_lineage(
              run_id,candidate_id,origin,comparison_parent_candidate_id,prose_parent_candidate_id,
              created_by_run_id,created_by_session_id,authority_snapshot_fingerprint,diff_fingerprint,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            values,
        )
        conn.commit()
    return candidate_lineage_view(conn, run_id, candidate_id)


def candidate_lineage_view(conn: sqlite3.Connection, run_id: str, candidate_id: str) -> dict[str, Any]:
    migrate(conn)
    candidate = qe.candidate_view(conn, run_id, candidate_id)
    line = conn.execute(
        "SELECT * FROM evolution_candidate_lineage WHERE run_id=? AND candidate_id=?",
        (run_id, candidate_id),
    ).fetchone()
    reviews = [
        dict(r)
        for r in conn.execute(
            """SELECT review_id,contract_id,candidate_fingerprint,job_fingerprint,result_fingerprint,
                      result_status,created_at,authority
               FROM evolution_review_receipts WHERE run_id=? AND candidate_id=? ORDER BY created_at,review_id""",
            (run_id, candidate_id),
        )
    ]
    accepts = [
        dict(r)
        for r in conn.execute(
            """SELECT acceptance_id,candidate_fingerprint,authority_source_ref,
                      accepted_artifact_fingerprint,accepted_at,created_at,authority
               FROM evolution_acceptance_bindings WHERE run_id=? AND candidate_id=? ORDER BY created_at,acceptance_id""",
            (run_id, candidate_id),
        )
    ]
    return {
        "schema": SCHEMA,
        **candidate,
        "lineage": dict(line) if line else None,
        "review_receipts": reviews,
        "acceptance_bindings": accepts,
        "authority": False,
        "permissions": {"canon_write": False, "settlement_write": False, "framework_write": False},
    }


def bind_review_receipt(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    review_id: str,
    candidate_id: str,
    job: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Bind a validated semantic review to one exact candidate fingerprint."""
    migrate(conn)
    if not isinstance(review_id, str) or not review_id.strip():
        raise ValueError("review_id required")
    candidate = _candidate(conn, run_id, candidate_id)
    errors = validate_result(job, result)
    if errors:
        raise ValueError("invalid semantic review result: " + "; ".join(errors))
    payload = job.get("input", {}).get("payload")
    contract_id = job.get("input", {}).get("model_contract_id")
    if not isinstance(payload, dict) or not isinstance(contract_id, str):
        raise ValueError("typed semantic review job required")
    job_candidate_fp = payload.get("candidate_fingerprint")
    if job_candidate_fp != candidate["content_fingerprint"]:
        raise ValueError("review job candidate fingerprint does not match target candidate")
    if result.get("input_fingerprint") != job.get("input_fingerprint"):
        raise ValueError("review result is stale or bound to another job")
    job_fp = _fp(job.get("input_fingerprint"), "job input_fingerprint")
    result_fp = qe.canonical_fingerprint(result)
    stamp = qe.now()
    existing = conn.execute(
        "SELECT * FROM evolution_review_receipts WHERE run_id=? AND review_id=?",
        (run_id, review_id),
    ).fetchone()
    values = (
        run_id,
        review_id,
        candidate_id,
        candidate["content_fingerprint"],
        contract_id,
        job_fp,
        result_fp,
        str(result.get("status")),
        stamp,
    )
    if existing:
        if any(
            existing[k] != v
            for k, v in {
                "candidate_id": candidate_id,
                "candidate_fingerprint": candidate["content_fingerprint"],
                "contract_id": contract_id,
                "job_fingerprint": job_fp,
                "result_fingerprint": result_fp,
                "result_status": str(result.get("status")),
            }.items()
        ):
            raise ValueError("review_id already bound differently")
    else:
        conn.execute(
            """INSERT INTO evolution_review_receipts(
              run_id,review_id,candidate_id,candidate_fingerprint,contract_id,
              job_fingerprint,result_fingerprint,result_status,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            values,
        )
        conn.commit()
    return candidate_lineage_view(conn, run_id, candidate_id)


def review_valid_for_candidate(conn: sqlite3.Connection, *, run_id: str, review_id: str,
                               candidate_id: str) -> bool:
    migrate(conn)
    candidate = _candidate(conn, run_id, candidate_id)
    row = conn.execute(
        "SELECT * FROM evolution_review_receipts WHERE run_id=? AND review_id=?",
        (run_id, review_id),
    ).fetchone()
    return bool(
        row
        and row["candidate_id"] == candidate_id
        and row["candidate_fingerprint"] == candidate["content_fingerprint"]
        and row["result_status"] == "completed"
    )


def bind_external_acceptance(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    acceptance_id: str,
    candidate_id: str,
    acceptance_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Mirror an externally authoritative explicit acceptance; never create it."""
    migrate(conn)
    candidate = _candidate(conn, run_id, candidate_id)
    if not isinstance(acceptance_id, str) or not acceptance_id.strip():
        raise ValueError("acceptance_id required")
    if not isinstance(acceptance_receipt, dict):
        raise ValueError("acceptance_receipt required")
    if acceptance_receipt.get("explicit_user_acceptance") is not True:
        raise ValueError("external receipt must attest explicit user acceptance")
    accepted_fp = _fp(acceptance_receipt.get("accepted_artifact_fingerprint"), "accepted_artifact_fingerprint")
    if accepted_fp != candidate["content_fingerprint"]:
        raise ValueError("acceptance fingerprint does not match candidate")
    source_ref = acceptance_receipt.get("authority_source_ref")
    accepted_at = acceptance_receipt.get("accepted_at")
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise ValueError("authority_source_ref required")
    if not isinstance(accepted_at, str) or not accepted_at.strip():
        raise ValueError("accepted_at required")
    stamp = qe.now()
    existing = conn.execute(
        "SELECT * FROM evolution_acceptance_bindings WHERE run_id=? AND acceptance_id=?",
        (run_id, acceptance_id),
    ).fetchone()
    values = (run_id, acceptance_id, candidate_id, accepted_fp, source_ref, accepted_fp, accepted_at, stamp)
    if existing:
        if any(
            existing[k] != v
            for k, v in {
                "candidate_id": candidate_id,
                "candidate_fingerprint": accepted_fp,
                "authority_source_ref": source_ref,
                "accepted_artifact_fingerprint": accepted_fp,
                "accepted_at": accepted_at,
            }.items()
        ):
            raise ValueError("acceptance_id already bound differently")
    else:
        conn.execute(
            """INSERT INTO evolution_acceptance_bindings(
              run_id,acceptance_id,candidate_id,candidate_fingerprint,authority_source_ref,
              accepted_artifact_fingerprint,accepted_at,created_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            values,
        )
        conn.commit()
    return candidate_lineage_view(conn, run_id, candidate_id)


def validate_settlement_binding(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    acceptance_id: str,
    candidate_id: str,
    accepted_artifact_fingerprint: str,
) -> dict[str, Any]:
    """Validate exact Accepted fingerprint for SETTLE preflight; performs no write."""
    migrate(conn)
    requested_fp = _fp(accepted_artifact_fingerprint, "accepted_artifact_fingerprint")
    candidate = _candidate(conn, run_id, candidate_id)
    binding = conn.execute(
        "SELECT * FROM evolution_acceptance_bindings WHERE run_id=? AND acceptance_id=?",
        (run_id, acceptance_id),
    ).fetchone()
    valid = bool(
        binding
        and candidate["content_fingerprint"] == requested_fp
        and binding["candidate_id"] == candidate_id
        and binding["candidate_fingerprint"] == requested_fp
        and binding["accepted_artifact_fingerprint"] == requested_fp
    )
    return {
        "schema": SCHEMA,
        "result": "PASS" if valid else "FAIL",
        "run_id": run_id,
        "acceptance_id": acceptance_id,
        "candidate_id": candidate_id,
        "candidate_fingerprint": candidate["content_fingerprint"],
        "requested_accepted_artifact_fingerprint": requested_fp,
        "authority": False,
        "settlement_write": False,
    }


def graph(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    migrate(conn)
    core = qe.status(conn, run_id)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "subject_id": core["subject_id"],
        "state": core["state"],
        "incumbent_candidate_id": core["incumbent_candidate_id"],
        "candidates": [candidate_lineage_view(conn, run_id, c["candidate_id"]) for c in core["candidates"]],
        "comparisons": core["comparisons"],
        "authority": False,
        "model_execution": False,
    }


def _reader_result(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
        "judgment": {
            "confidence": 0.9,
            "result": "pass",
            "report": "Synthetic reader receipt for binding tests.",
            "strongest_positive": "clear causal movement",
            "strongest_problem": None,
            "evidence_refs": ["candidate:self-test"],
        },
        "proposals": [],
        "errors": [],
    }


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    conn = qe.connect(path)
    migrate(conn)
    qe.start_run(conn, run_id="RUN-L", subject_id="CH-L", baseline_candidate_id="A", baseline_text="draft A", plateau_limit=4)
    register_candidate(conn, run_id="RUN-L", candidate_id="A", origin="draft", prose_parent_candidate_id=None,
                       created_by_run_id="RUN-MGR", created_by_session_id="SES-MGR")

    # TEST A: Draft A -> repair A1 has exact prose parent.
    qe.add_candidate(conn, run_id="RUN-L", candidate_id="A1", text="repair A1", repair_owner="surface")
    a1 = register_candidate(conn, run_id="RUN-L", candidate_id="A1", origin="repair", prose_parent_candidate_id="A",
                            created_by_run_id="RUN-MGR", created_by_session_id="SES-MGR")
    from objective_envelope import build as build_objective_envelope
    envelope = build_objective_envelope({
        "subject_id": "CH-L", "run_id": "RUN-L", "authority_cutoff": "synthetic",
        "objective_items": [{"id": "OBJ-L", "category": "reader", "statement": "Preserve reader pressure.", "source_refs": ["plan:self"]}],
        "must_preserve": ["reader pressure"], "derived_from_rejected_realization": False,
    })
    rc = {"repair_target": "surface defect", "objective_envelope": envelope}
    j1 = qe.prepare_comparison_job(conn, run_id="RUN-L", comparison_id="CMP-A1", challenger_candidate_id="A1", repair_context=rc)
    qe.record_comparison(conn, job=j1, result=qe._fixture_result(j1, "challenger", "repair succeeds"))

    # TEST B: fresh A2 competes against A1 but has no prose parent.
    qe.add_candidate(conn, run_id="RUN-L", candidate_id="A2", text="fresh A2", repair_owner="scene")
    a2 = register_candidate(conn, run_id="RUN-L", candidate_id="A2", origin="fresh_regeneration", prose_parent_candidate_id=None,
                            created_by_run_id="RUN-MGR", created_by_session_id="SES-MGR")

    # TEST C/E: review for A cannot validate or be rebound to A1/A2.
    reader_job = make_contract_job(
        "reader.engagement_audit", "REVIEW-A",
        {"candidate_fingerprint": qe.candidate_view(conn, "RUN-L", "A")["content_fingerprint"], "candidate_text": "draft A", "reader_grip": "high"},
        source_session_id="SES-READER",
    )
    bind_review_receipt(conn, run_id="RUN-L", review_id="REV-A", candidate_id="A", job=reader_job, result=_reader_result(reader_job))
    stale_blocked = False
    try:
        bind_review_receipt(conn, run_id="RUN-L", review_id="REV-A1-WRONG", candidate_id="A1", job=reader_job, result=_reader_result(reader_job))
    except ValueError:
        stale_blocked = True

    # TEST D: explicit Accepted A1 does not accept A2.
    a1_fp = qe.candidate_view(conn, "RUN-L", "A1")["content_fingerprint"]
    bind_external_acceptance(conn, run_id="RUN-L", acceptance_id="ACC-A1", candidate_id="A1", acceptance_receipt={
        "explicit_user_acceptance": True,
        "accepted_artifact_fingerprint": a1_fp,
        "authority_source_ref": "synthetic:user-gate:1",
        "accepted_at": "2026-08-17T00:00:00+00:00",
    })

    # TEST F: a worse fresh challenger does not replace the incumbent.
    j2 = qe.prepare_comparison_job(conn, run_id="RUN-L", comparison_id="CMP-A2", challenger_candidate_id="A2", repair_context=rc)
    after_worse = qe.record_comparison(conn, job=j2, result=qe._fixture_result(j2, "incumbent", "fresh regeneration is worse"))

    # TEST G: close/reopen reconstructs exact lineage from durable SQLite state.
    graph_before = graph(conn, "RUN-L")
    conn.close()
    conn = qe.connect(path)
    migrate(conn)
    graph_after = graph(conn, "RUN-L")

    # TEST H: settlement preflight references exact Accepted fingerprint only.
    settlement_ok = validate_settlement_binding(conn, run_id="RUN-L", acceptance_id="ACC-A1", candidate_id="A1",
                                                accepted_artifact_fingerprint=a1_fp)
    settlement_wrong = validate_settlement_binding(conn, run_id="RUN-L", acceptance_id="ACC-A1", candidate_id="A2",
                                                   accepted_artifact_fingerprint=qe.candidate_view(conn, "RUN-L", "A2")["content_fingerprint"])

    tests = {
        "A_repair_parent_binding": a1["lineage"]["comparison_parent_candidate_id"] == "A" and a1["lineage"]["prose_parent_candidate_id"] == "A",
        "B_fresh_lineage_distinct": a2["lineage"]["comparison_parent_candidate_id"] == "A1" and a2["lineage"]["prose_parent_candidate_id"] is None,
        "C_review_A_cannot_validate_A1": not review_valid_for_candidate(conn, run_id="RUN-L", review_id="REV-A", candidate_id="A1"),
        "D_accept_A1_not_A2": len(candidate_lineage_view(conn, "RUN-L", "A1")["acceptance_bindings"]) == 1 and not candidate_lineage_view(conn, "RUN-L", "A2")["acceptance_bindings"],
        "E_stale_review_invalidated": stale_blocked and not review_valid_for_candidate(conn, run_id="RUN-L", review_id="REV-A", candidate_id="A2"),
        "F_incumbent_retained_if_challenger_worse": after_worse["incumbent_candidate_id"] == "A1",
        "G_resume_reconstructs_exact_lineage": graph_before == graph_after,
        "H_settlement_exact_accepted_fingerprint": settlement_ok["result"] == "PASS" and settlement_wrong["result"] == "FAIL",
    }
    ok = all(tests.values()) and graph_after["authority"] is False
    print(json.dumps({
        "candidate_lineage_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "tests": tests,
        "comparison_semantics_reused": "quality_evolution.quality.compare",
        "canon_or_settlement_write_added": False,
        "model_execution": False,
        "authority": False,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge candidate-lineage extension")
    p.add_argument("--db", default=".novelforge/quality-evolution.db")
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("graph")
    g.add_argument("--run-id", required=True)
    sf = sub.add_parser("self-test")
    sf.add_argument("--path", default="/tmp/novelforge-candidate-lineage-selftest.db")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test(Path(args.path))
    conn = qe.connect(Path(args.db))
    try:
        print(json.dumps(graph(conn, args.run_id), ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
