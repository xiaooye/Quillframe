#!/usr/bin/env python3
"""Candidate lineage extension for Quillframe quality evolution.

This module extends the existing ``quality_evolution`` ledger; it does not create
another candidate-selection, comparison, acceptance, Canon, or settlement system.
The existing ``parent_candidate_id`` remains the direct comparison ancestry used
by ``quality.compare``. This extension records the distinct prose-derivation
relationship plus exact review/evidence bindings so a fresh regeneration can
compete with the incumbent without pretending to inherit rejected prose.

Everything here is derived/provenance state (authority=false). Acceptance evidence
is an opaque external reference: this module can prove that a reference names one
exact candidate fingerprint, but it cannot prove that the referenced event was an
authoritative user acceptance. SETTLE authorization remains outside this module.
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

SCHEMA = "quillframe_candidate_lineage_v1"
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
        CREATE TABLE IF NOT EXISTS evolution_acceptance_evidence(
          run_id TEXT NOT NULL,
          acceptance_evidence_id TEXT NOT NULL,
          candidate_id TEXT NOT NULL,
          candidate_fingerprint TEXT NOT NULL,
          authority_source_ref TEXT NOT NULL,
          authority_receipt_fingerprint TEXT NOT NULL,
          accepted_artifact_fingerprint TEXT NOT NULL,
          accepted_at TEXT NOT NULL,
          created_at TEXT NOT NULL,
          authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0),
          PRIMARY KEY(run_id,acceptance_evidence_id),
          UNIQUE(run_id,authority_source_ref),
          UNIQUE(run_id,authority_receipt_fingerprint),
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
    return qe._candidate(conn, run_id, candidate_id)


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
    """Attach immutable derivation lineage to an existing evolution candidate."""
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

    existing = conn.execute(
        "SELECT * FROM evolution_candidate_lineage WHERE run_id=? AND candidate_id=?",
        (run_id, candidate_id),
    ).fetchone()
    expected = {
        "origin": origin,
        "comparison_parent_candidate_id": comparison_parent,
        "prose_parent_candidate_id": prose_parent_candidate_id,
        "created_by_run_id": created_by_run_id,
        "created_by_session_id": created_by_session_id,
        "authority_snapshot_fingerprint": authority_snapshot_fingerprint,
        "diff_fingerprint": diff_fingerprint,
    }
    if existing:
        if any(existing[k] != v for k, v in expected.items()):
            raise ValueError("candidate lineage is immutable and already differs")
    else:
        conn.execute(
            """INSERT INTO evolution_candidate_lineage(
              run_id,candidate_id,origin,comparison_parent_candidate_id,prose_parent_candidate_id,
              created_by_run_id,created_by_session_id,authority_snapshot_fingerprint,diff_fingerprint,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, candidate_id, origin, comparison_parent, prose_parent_candidate_id,
                created_by_run_id, created_by_session_id, authority_snapshot_fingerprint,
                diff_fingerprint, qe.now(),
            ),
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
    evidence = []
    for row in conn.execute(
        """SELECT acceptance_evidence_id,candidate_fingerprint,authority_source_ref,
                  authority_receipt_fingerprint,accepted_artifact_fingerprint,accepted_at,created_at,authority
           FROM evolution_acceptance_evidence WHERE run_id=? AND candidate_id=?
           ORDER BY created_at,acceptance_evidence_id""",
        (run_id, candidate_id),
    ):
        item = dict(row)
        item["authority_verified"] = False
        item["settlement_authorized"] = False
        evidence.append(item)
    return {
        "schema": SCHEMA,
        **candidate,
        "lineage": dict(line) if line else None,
        "review_receipts": reviews,
        "acceptance_evidence": evidence,
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
    if payload.get("candidate_fingerprint") != candidate["content_fingerprint"]:
        raise ValueError("review job candidate fingerprint does not match target candidate")
    if result.get("input_fingerprint") != job.get("input_fingerprint"):
        raise ValueError("review result is stale or bound to another job")
    job_fp = _fp(job.get("input_fingerprint"), "job input_fingerprint")
    result_fp = qe.canonical_fingerprint(result)
    expected = {
        "candidate_id": candidate_id,
        "candidate_fingerprint": candidate["content_fingerprint"],
        "contract_id": contract_id,
        "job_fingerprint": job_fp,
        "result_fingerprint": result_fp,
        "result_status": str(result.get("status")),
    }
    existing = conn.execute(
        "SELECT * FROM evolution_review_receipts WHERE run_id=? AND review_id=?",
        (run_id, review_id),
    ).fetchone()
    if existing:
        if any(existing[k] != v for k, v in expected.items()):
            raise ValueError("review_id already bound differently")
    else:
        conn.execute(
            """INSERT INTO evolution_review_receipts(
              run_id,review_id,candidate_id,candidate_fingerprint,contract_id,
              job_fingerprint,result_fingerprint,result_status,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                run_id, review_id, candidate_id, candidate["content_fingerprint"], contract_id,
                job_fp, result_fp, str(result.get("status")), qe.now(),
            ),
        )
        conn.commit()
    return candidate_lineage_view(conn, run_id, candidate_id)


def review_valid_for_candidate(
    conn: sqlite3.Connection, *, run_id: str, review_id: str, candidate_id: str
) -> bool:
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


def bind_acceptance_evidence(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    acceptance_evidence_id: str,
    candidate_id: str,
    acceptance_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Bind an opaque external acceptance reference; do not authenticate authority.

    The authority/user-gate layer must verify the source receipt independently.
    This function only checks identifier/fingerprint shape, target-candidate identity,
    and immutable reference consistency.
    """
    migrate(conn)
    candidate = _candidate(conn, run_id, candidate_id)
    if not isinstance(acceptance_evidence_id, str) or not acceptance_evidence_id.strip():
        raise ValueError("acceptance_evidence_id required")
    if not isinstance(acceptance_evidence, dict):
        raise ValueError("acceptance_evidence required")
    accepted_fp = _fp(
        acceptance_evidence.get("accepted_artifact_fingerprint"),
        "accepted_artifact_fingerprint",
    )
    if accepted_fp != candidate["content_fingerprint"]:
        raise ValueError("acceptance evidence fingerprint does not match candidate")
    receipt_fp = _fp(
        acceptance_evidence.get("authority_receipt_fingerprint"),
        "authority_receipt_fingerprint",
    )
    source_ref = acceptance_evidence.get("authority_source_ref")
    accepted_at = acceptance_evidence.get("accepted_at")
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise ValueError("authority_source_ref required")
    if not isinstance(accepted_at, str) or not accepted_at.strip():
        raise ValueError("accepted_at required")

    expected = {
        "candidate_id": candidate_id,
        "candidate_fingerprint": accepted_fp,
        "authority_source_ref": source_ref,
        "authority_receipt_fingerprint": receipt_fp,
        "accepted_artifact_fingerprint": accepted_fp,
        "accepted_at": accepted_at,
    }
    existing = conn.execute(
        """SELECT * FROM evolution_acceptance_evidence
           WHERE run_id=? AND acceptance_evidence_id=?""",
        (run_id, acceptance_evidence_id),
    ).fetchone()
    if existing:
        if any(existing[k] != v for k, v in expected.items()):
            raise ValueError("acceptance_evidence_id already bound differently")
    else:
        conn.execute(
            """INSERT INTO evolution_acceptance_evidence(
              run_id,acceptance_evidence_id,candidate_id,candidate_fingerprint,
              authority_source_ref,authority_receipt_fingerprint,
              accepted_artifact_fingerprint,accepted_at,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                run_id, acceptance_evidence_id, candidate_id, accepted_fp, source_ref,
                receipt_fp, accepted_fp, accepted_at, qe.now(),
            ),
        )
        conn.commit()
    return candidate_lineage_view(conn, run_id, candidate_id)


def check_settlement_reference_consistency(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    acceptance_evidence_id: str,
    candidate_id: str,
    accepted_artifact_fingerprint: str,
) -> dict[str, Any]:
    """Check exact reference consistency only; never authorize SETTLE."""
    migrate(conn)
    requested_fp = _fp(accepted_artifact_fingerprint, "accepted_artifact_fingerprint")
    candidate = _candidate(conn, run_id, candidate_id)
    evidence = conn.execute(
        """SELECT * FROM evolution_acceptance_evidence
           WHERE run_id=? AND acceptance_evidence_id=?""",
        (run_id, acceptance_evidence_id),
    ).fetchone()
    matches = bool(
        evidence
        and candidate["content_fingerprint"] == requested_fp
        and evidence["candidate_id"] == candidate_id
        and evidence["candidate_fingerprint"] == requested_fp
        and evidence["accepted_artifact_fingerprint"] == requested_fp
    )
    return {
        "schema": SCHEMA,
        "result": "REFERENCE_MATCH" if matches else "REFERENCE_MISMATCH",
        "run_id": run_id,
        "acceptance_evidence_id": acceptance_evidence_id,
        "candidate_id": candidate_id,
        "candidate_fingerprint": candidate["content_fingerprint"],
        "requested_accepted_artifact_fingerprint": requested_fp,
        "authority": False,
        "authority_verified": False,
        "settlement_authorized": False,
        "settlement_write": False,
        "requires_external_authority_verification": True,
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
    qe.start_run(
        conn, run_id="RUN-L", subject_id="CH-L", baseline_candidate_id="A",
        baseline_text="draft A", plateau_limit=4,
    )
    register_candidate(
        conn, run_id="RUN-L", candidate_id="A", origin="draft",
        prose_parent_candidate_id=None, created_by_run_id="RUN-MGR",
        created_by_session_id="SES-MGR",
    )

    qe.add_candidate(conn, run_id="RUN-L", candidate_id="A1", text="repair A1", repair_owner="surface")
    a1 = register_candidate(
        conn, run_id="RUN-L", candidate_id="A1", origin="repair",
        prose_parent_candidate_id="A", created_by_run_id="RUN-MGR",
        created_by_session_id="SES-MGR",
    )
    from objective_envelope import build as build_objective_envelope

    envelope = build_objective_envelope({
        "subject_id": "CH-L",
        "run_id": "RUN-L",
        "authority_cutoff": "synthetic",
        "objective_items": [{
            "id": "OBJ-L", "category": "reader", "statement": "Preserve reader pressure.",
            "source_refs": ["plan:self"],
        }],
        "must_preserve": ["reader pressure"],
        "derived_from_rejected_realization": False,
    })
    repair_context = {"repair_target": "surface defect", "objective_envelope": envelope}
    j1 = qe.prepare_comparison_job(
        conn, run_id="RUN-L", comparison_id="CMP-A1",
        challenger_candidate_id="A1", repair_context=repair_context,
    )
    qe.record_comparison(conn, job=j1, result=qe._fixture_result(j1, "challenger", "repair succeeds"))

    qe.add_candidate(conn, run_id="RUN-L", candidate_id="A2", text="fresh A2", repair_owner="scene")
    a2 = register_candidate(
        conn, run_id="RUN-L", candidate_id="A2", origin="fresh_regeneration",
        prose_parent_candidate_id=None, created_by_run_id="RUN-MGR",
        created_by_session_id="SES-MGR",
    )

    reader_job = make_contract_job(
        "reader.engagement_audit",
        "REVIEW-A",
        {
            "candidate_fingerprint": qe.candidate_view(conn, "RUN-L", "A")["content_fingerprint"],
            "candidate_text": "draft A",
            "reader_grip": "high",
        },
        source_session_id="SES-READER",
    )
    bind_review_receipt(
        conn, run_id="RUN-L", review_id="REV-A", candidate_id="A",
        job=reader_job, result=_reader_result(reader_job),
    )
    stale_blocked = False
    try:
        bind_review_receipt(
            conn, run_id="RUN-L", review_id="REV-A1-WRONG", candidate_id="A1",
            job=reader_job, result=_reader_result(reader_job),
        )
    except ValueError:
        stale_blocked = True

    a1_fp = qe.candidate_view(conn, "RUN-L", "A1")["content_fingerprint"]
    receipt_fp = qe.canonical_fingerprint({"synthetic_external_gate_receipt": "A1"})
    bind_acceptance_evidence(
        conn, run_id="RUN-L", acceptance_evidence_id="AE-A1", candidate_id="A1",
        acceptance_evidence={
            "accepted_artifact_fingerprint": a1_fp,
            "authority_source_ref": "synthetic:user-gate:1",
            "authority_receipt_fingerprint": receipt_fp,
            "accepted_at": "2026-08-17T00:00:00+00:00",
        },
    )

    j2 = qe.prepare_comparison_job(
        conn, run_id="RUN-L", comparison_id="CMP-A2",
        challenger_candidate_id="A2", repair_context=repair_context,
    )
    after_worse = qe.record_comparison(
        conn, job=j2, result=qe._fixture_result(j2, "incumbent", "fresh regeneration is worse"),
    )

    graph_before = graph(conn, "RUN-L")
    conn.close()
    conn = qe.connect(path)
    migrate(conn)
    graph_after = graph(conn, "RUN-L")

    settlement_ref_ok = check_settlement_reference_consistency(
        conn, run_id="RUN-L", acceptance_evidence_id="AE-A1", candidate_id="A1",
        accepted_artifact_fingerprint=a1_fp,
    )
    settlement_ref_wrong = check_settlement_reference_consistency(
        conn, run_id="RUN-L", acceptance_evidence_id="AE-A1", candidate_id="A2",
        accepted_artifact_fingerprint=qe.candidate_view(conn, "RUN-L", "A2")["content_fingerprint"],
    )

    a1_view = candidate_lineage_view(conn, "RUN-L", "A1")
    a2_view = candidate_lineage_view(conn, "RUN-L", "A2")
    tests = {
        "A_repair_parent_binding": (
            a1["lineage"]["comparison_parent_candidate_id"] == "A"
            and a1["lineage"]["prose_parent_candidate_id"] == "A"
        ),
        "B_fresh_lineage_distinct": (
            a2["lineage"]["comparison_parent_candidate_id"] == "A1"
            and a2["lineage"]["prose_parent_candidate_id"] is None
        ),
        "C_review_A_cannot_validate_A1": not review_valid_for_candidate(
            conn, run_id="RUN-L", review_id="REV-A", candidate_id="A1"
        ),
        "D_acceptance_evidence_A1_does_not_imply_A2": (
            len(a1_view["acceptance_evidence"]) == 1
            and not a2_view["acceptance_evidence"]
            and a1_view["acceptance_evidence"][0]["authority_verified"] is False
        ),
        "E_stale_review_invalidated": (
            stale_blocked
            and not review_valid_for_candidate(conn, run_id="RUN-L", review_id="REV-A", candidate_id="A2")
        ),
        "F_incumbent_retained_if_challenger_worse": after_worse["incumbent_candidate_id"] == "A1",
        "G_resume_reconstructs_exact_lineage": graph_before == graph_after,
        "H_settlement_reference_exact_not_authorization": (
            settlement_ref_ok["result"] == "REFERENCE_MATCH"
            and settlement_ref_wrong["result"] == "REFERENCE_MISMATCH"
            and settlement_ref_ok["settlement_authorized"] is False
            and settlement_ref_ok["requires_external_authority_verification"] is True
        ),
    }
    ok = all(tests.values()) and graph_after["authority"] is False
    print(json.dumps({
        "candidate_lineage_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "tests": tests,
        "comparison_semantics_reused": "quality_evolution.quality.compare",
        "acceptance_authority_verified_here": False,
        "canon_or_settlement_write_added": False,
        "model_execution": False,
        "authority": False,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe candidate-lineage extension")
    parser.add_argument("--db", default=".quillframe/quality-evolution.db")
    sub = parser.add_subparsers(dest="command", required=True)
    graph_parser = sub.add_parser("graph")
    graph_parser.add_argument("--run-id", required=True)
    self_parser = sub.add_parser("self-test")
    self_parser.add_argument("--path", default="/tmp/quillframe-candidate-lineage-selftest.db")
    args = parser.parse_args()
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
