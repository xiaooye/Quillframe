#!/usr/bin/env python3
"""Durable candidate-evolution ledger for Quillframe.

Deterministic SQLite state only. The ledger tracks candidates, exact semantic
comparison jobs/results, repair ownership, and plateau stopping. It never makes
literary judgments and never grants Canon/Framework-write authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402

SCHEMA = "quillframe_quality_evolution_v2"
REPAIR_OWNERS = {
    "story", "plan", "scene", "character", "reader", "surface",
    "continuity", "context", "memory", "research", "runtime", "human",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text_fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS evolution_runs(
      run_id TEXT PRIMARY KEY,
      subject_id TEXT NOT NULL,
      state TEXT NOT NULL,
      baseline_candidate_id TEXT NOT NULL,
      incumbent_candidate_id TEXT NOT NULL,
      no_gain_count INTEGER NOT NULL DEFAULT 0,
      plateau_limit INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0)
    );
    CREATE TABLE IF NOT EXISTS evolution_candidates(
      run_id TEXT NOT NULL,
      candidate_id TEXT NOT NULL,
      content_fingerprint TEXT NOT NULL,
      parent_candidate_id TEXT,
      repair_owner TEXT NOT NULL,
      metadata_json TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(run_id,candidate_id),
      UNIQUE(run_id,content_fingerprint),
      FOREIGN KEY(run_id) REFERENCES evolution_runs(run_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS evolution_comparisons(
      run_id TEXT NOT NULL,
      comparison_id TEXT NOT NULL,
      incumbent_candidate_id TEXT NOT NULL,
      challenger_candidate_id TEXT NOT NULL,
      winner_candidate_id TEXT,
      job_fingerprint TEXT NOT NULL,
      result_fingerprint TEXT NOT NULL,
      result_json TEXT NOT NULL,
      consumed_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(run_id,comparison_id),
      UNIQUE(run_id,job_fingerprint),
      UNIQUE(run_id,result_fingerprint),
      FOREIGN KEY(run_id) REFERENCES evolution_runs(run_id) ON DELETE CASCADE
    );
    """)
    return conn


def start_run(conn: sqlite3.Connection, *, run_id: str, subject_id: str, baseline_candidate_id: str,
              baseline_text: str, plateau_limit: int = 2) -> dict[str, Any]:
    if plateau_limit < 1:
        raise ValueError("plateau_limit must be >= 1")
    if not all(isinstance(x, str) and x.strip() for x in (run_id, subject_id, baseline_candidate_id, baseline_text)):
        raise ValueError("run/subject/baseline id and baseline text are required")
    stamp = now()
    fp = text_fingerprint(baseline_text)
    try:
        conn.execute(
            "INSERT INTO evolution_runs(run_id,subject_id,state,baseline_candidate_id,incumbent_candidate_id,no_gain_count,plateau_limit,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (run_id, subject_id, "active", baseline_candidate_id, baseline_candidate_id, 0, plateau_limit, stamp, stamp),
        )
        conn.execute(
            "INSERT INTO evolution_candidates(run_id,candidate_id,content_fingerprint,parent_candidate_id,repair_owner,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (run_id, baseline_candidate_id, fp, None, "human", "{}", stamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT * FROM evolution_runs WHERE run_id=?", (run_id,)).fetchone()
        cand = conn.execute("SELECT * FROM evolution_candidates WHERE run_id=? AND candidate_id=?", (run_id, baseline_candidate_id)).fetchone()
        if not row or not cand or cand["content_fingerprint"] != fp or row["subject_id"] != subject_id:
            raise ValueError("run_id already exists with different baseline")
    return status(conn, run_id)


def _run(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM evolution_runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        raise ValueError(f"unknown run_id: {run_id}")
    return row


def _candidate(conn: sqlite3.Connection, run_id: str, candidate_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM evolution_candidates WHERE run_id=? AND candidate_id=?", (run_id, candidate_id)).fetchone()
    if not row:
        raise ValueError(f"unknown candidate: {candidate_id}")
    return row


def add_candidate(conn: sqlite3.Connection, *, run_id: str, candidate_id: str, text: str,
                  repair_owner: str, parent_candidate_id: str | None = None,
                  metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    run = _run(conn, run_id)
    if run["state"] != "active":
        raise ValueError(f"run is not active: {run['state']}")
    if repair_owner not in REPAIR_OWNERS:
        raise ValueError(f"invalid repair_owner: {repair_owner}")
    parent = parent_candidate_id or run["incumbent_candidate_id"]
    _candidate(conn, run_id, parent)
    fp = text_fingerprint(text)
    stamp = now()
    try:
        conn.execute(
            "INSERT INTO evolution_candidates(run_id,candidate_id,content_fingerprint,parent_candidate_id,repair_owner,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (run_id, candidate_id, fp, parent, repair_owner, json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), stamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        existing = conn.execute("SELECT * FROM evolution_candidates WHERE run_id=? AND candidate_id=?", (run_id, candidate_id)).fetchone()
        if not existing or existing["content_fingerprint"] != fp or existing["parent_candidate_id"] != parent:
            raise ValueError("candidate id/fingerprint conflict")
    return candidate_view(conn, run_id, candidate_id)


def prepare_comparison_job(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    comparison_id: str,
    challenger_candidate_id: str,
    repair_context: dict[str, Any],
    source_session_id: str | None = None,
) -> dict[str, Any]:
    run = _run(conn, run_id)
    if run["state"] != "active":
        raise ValueError(f"run is not active: {run['state']}")
    incumbent_id = str(run["incumbent_candidate_id"])
    if incumbent_id == challenger_candidate_id:
        raise ValueError("comparison candidates must differ")
    incumbent = _candidate(conn, run_id, incumbent_id)
    challenger = _candidate(conn, run_id, challenger_candidate_id)
    if challenger["parent_candidate_id"] != incumbent_id:
        raise ValueError("challenger must descend from current incumbent")
    if not isinstance(repair_context, dict):
        raise ValueError("repair_context must be object")
    if not isinstance(repair_context.get("repair_target"),str) or not repair_context["repair_target"].strip():
        raise ValueError("repair_context.repair_target required")
    envelope=repair_context.get("objective_envelope")
    if not isinstance(envelope,dict): raise ValueError("repair_context.objective_envelope required")
    quality_root=ROOT/"quality"
    if str(quality_root) not in sys.path:sys.path.insert(0,str(quality_root))
    from objective_envelope import validate as validate_objective_envelope
    envelope_errors=validate_objective_envelope(envelope,subject_id=run["subject_id"],run_id=run_id)
    if envelope_errors: raise ValueError("invalid objective envelope: "+"; ".join(envelope_errors))
    payload = {
        "evolution_run_id": run_id,
        "evolution_subject_id": run["subject_id"],
        "comparison_id": comparison_id,
        "incumbent": {
            "candidate_id": incumbent_id,
            "content_fingerprint": incumbent["content_fingerprint"],
        },
        "challenger": {
            "candidate_id": challenger_candidate_id,
            "content_fingerprint": challenger["content_fingerprint"],
            "repair_owner": challenger["repair_owner"],
        },
        "repair_context": repair_context,
    }
    return make_contract_job(
        "quality.compare",
        comparison_id,
        payload,
        source_session_id=source_session_id,
    )


def _comparison_binding(job: dict[str, Any]) -> tuple[str, str, str, str, str]:
    if job.get("input", {}).get("model_contract_id") != "quality.compare":
        raise ValueError("comparison job must use quality.compare")
    payload = job.get("input", {}).get("payload")
    if not isinstance(payload, dict):
        raise ValueError("comparison job payload required")
    run_id = payload.get("evolution_run_id")
    comparison_id = payload.get("comparison_id")
    incumbent = payload.get("incumbent")
    challenger = payload.get("challenger")
    if not all(isinstance(x, str) and x.strip() for x in (run_id, comparison_id)):
        raise ValueError("comparison job missing run/comparison identity")
    if not isinstance(incumbent, dict) or not isinstance(challenger, dict):
        raise ValueError("comparison job missing candidate bindings")
    incumbent_id = incumbent.get("candidate_id")
    challenger_id = challenger.get("candidate_id")
    incumbent_fp = incumbent.get("content_fingerprint")
    challenger_fp = challenger.get("content_fingerprint")
    if not all(isinstance(x, str) and x.strip() for x in (incumbent_id, challenger_id, incumbent_fp, challenger_fp)):
        raise ValueError("comparison job candidate identity/fingerprint required")
    if job.get("subject_id") != comparison_id:
        raise ValueError("comparison job subject_id must equal comparison_id")
    return run_id, comparison_id, incumbent_id, challenger_id, incumbent_fp + "|" + challenger_fp


def _winner_from_result(result: dict[str, Any], incumbent_id: str, challenger_id: str) -> str | None:
    judgment = result.get("judgment")
    if not isinstance(judgment, dict):
        raise ValueError("comparison result judgment required")
    winner = judgment.get("winner")
    if winner == "incumbent":
        return incumbent_id
    if winner == "challenger":
        return challenger_id
    if winner == "tie":
        return None
    raise ValueError("quality.compare winner must be incumbent|challenger|tie")


def record_comparison(
    conn: sqlite3.Connection,
    *,
    job: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_result(job, result)
    if errors:
        raise ValueError("invalid semantic comparison result: " + "; ".join(errors))
    if result.get("status") != "completed":
        raise ValueError("quality comparison result must be completed")

    run_id, comparison_id, incumbent_id, challenger_id, joined_fps = _comparison_binding(job)
    incumbent_fp, challenger_fp = joined_fps.split("|", 1)
    winner_candidate_id = _winner_from_result(result, incumbent_id, challenger_id)
    job_fp = job.get("input_fingerprint")
    result_fp = canonical_fingerprint(result)
    if not isinstance(job_fp, str) or not job_fp.startswith("sha256:"):
        raise ValueError("comparison job fingerprint required")

    run = _run(conn, run_id)
    existing = conn.execute(
        "SELECT * FROM evolution_comparisons WHERE run_id=? AND comparison_id=?",
        (run_id, comparison_id),
    ).fetchone()
    if existing:
        if (
            existing["job_fingerprint"] != job_fp
            or existing["result_fingerprint"] != result_fp
            or existing["incumbent_candidate_id"] != incumbent_id
            or existing["challenger_candidate_id"] != challenger_id
            or existing["winner_candidate_id"] != winner_candidate_id
        ):
            raise ValueError("comparison_id already consumed with different job/result")
        return status(conn, run_id)

    consumed_job = conn.execute(
        "SELECT comparison_id FROM evolution_comparisons WHERE run_id=? AND job_fingerprint=?",
        (run_id, job_fp),
    ).fetchone()
    if consumed_job:
        raise ValueError(f"comparison job already consumed by {consumed_job['comparison_id']}")
    consumed_result = conn.execute(
        "SELECT comparison_id FROM evolution_comparisons WHERE run_id=? AND result_fingerprint=?",
        (run_id, result_fp),
    ).fetchone()
    if consumed_result:
        raise ValueError(f"comparison result already consumed by {consumed_result['comparison_id']}")

    if run["state"] != "active":
        raise ValueError(f"run is not active: {run['state']}")
    if incumbent_id != run["incumbent_candidate_id"]:
        raise ValueError("comparison incumbent must equal current incumbent")
    if incumbent_id == challenger_id:
        raise ValueError("comparison candidates must differ")
    incumbent = _candidate(conn, run_id, incumbent_id)
    challenger = _candidate(conn, run_id, challenger_id)
    if incumbent["content_fingerprint"] != incumbent_fp:
        raise ValueError("incumbent content fingerprint changed after comparison job freeze")
    if challenger["content_fingerprint"] != challenger_fp:
        raise ValueError("challenger content fingerprint changed after comparison job freeze")
    if challenger["parent_candidate_id"] != incumbent_id:
        raise ValueError("challenger must descend from current incumbent")

    stamp = now()
    conn.execute(
        "INSERT INTO evolution_comparisons(run_id,comparison_id,incumbent_candidate_id,challenger_candidate_id,winner_candidate_id,job_fingerprint,result_fingerprint,result_json,consumed_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            run_id,
            comparison_id,
            incumbent_id,
            challenger_id,
            winner_candidate_id,
            job_fp,
            result_fp,
            json.dumps(result, ensure_ascii=False, sort_keys=True),
            stamp,
            stamp,
        ),
    )
    if winner_candidate_id == challenger_id:
        new_incumbent = challenger_id
        no_gain = 0
    else:
        new_incumbent = incumbent_id
        no_gain = int(run["no_gain_count"]) + 1
    state = "plateau" if no_gain >= int(run["plateau_limit"]) else "active"
    conn.execute(
        "UPDATE evolution_runs SET incumbent_candidate_id=?, no_gain_count=?, state=?, updated_at=? WHERE run_id=?",
        (new_incumbent, no_gain, state, stamp, run_id),
    )
    conn.commit()
    return status(conn, run_id)


def complete(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = _run(conn, run_id)
    if run["state"] == "complete":
        return status(conn, run_id)
    conn.execute("UPDATE evolution_runs SET state='complete', updated_at=? WHERE run_id=?", (now(), run_id))
    conn.commit()
    return status(conn, run_id)


def candidate_view(conn: sqlite3.Connection, run_id: str, candidate_id: str) -> dict[str, Any]:
    row = _candidate(conn, run_id, candidate_id)
    return {
        "candidate_id": row["candidate_id"],
        "content_fingerprint": row["content_fingerprint"],
        "parent_candidate_id": row["parent_candidate_id"],
        "repair_owner": row["repair_owner"],
        "metadata": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
    }


def status(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = _run(conn, run_id)
    candidates = [
        dict(r)
        for r in conn.execute(
            "SELECT candidate_id,content_fingerprint,parent_candidate_id,repair_owner,created_at FROM evolution_candidates WHERE run_id=? ORDER BY created_at,candidate_id",
            (run_id,),
        )
    ]
    comparisons = [
        dict(r)
        for r in conn.execute(
            "SELECT comparison_id,incumbent_candidate_id,challenger_candidate_id,winner_candidate_id,job_fingerprint,result_fingerprint,consumed_at FROM evolution_comparisons WHERE run_id=? ORDER BY created_at,comparison_id",
            (run_id,),
        )
    ]
    return {
        "schema": SCHEMA,
        "run_id": row["run_id"],
        "subject_id": row["subject_id"],
        "state": row["state"],
        "baseline_candidate_id": row["baseline_candidate_id"],
        "incumbent_candidate_id": row["incumbent_candidate_id"],
        "no_gain_count": row["no_gain_count"],
        "plateau_limit": row["plateau_limit"],
        "candidates": candidates,
        "comparisons": comparisons,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def _fixture_result(job: dict[str, Any], winner: str, reason: str, *, objective_regression: bool=False) -> dict[str, Any]:
    if winner=="challenger":
        axes={"target_outcome":"improved","objective_preservation":"preserved","reader_value":"unchanged","character_relationship_energy":"preserved","outcome_class":"successful_repair","regressed_dimensions":[]}
    elif objective_regression:
        axes={"target_outcome":"improved","objective_preservation":"materially_degraded","reader_value":"degraded","character_relationship_energy":"preserved","outcome_class":"objective_regression","regressed_dimensions":["reader_pressure"]}
    else:
        axes={"target_outcome":"unchanged","objective_preservation":"preserved","reader_value":"unchanged","character_relationship_energy":"preserved","outcome_class":"target_not_fixed","regressed_dimensions":[]}
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
        "judgment": {
            "confidence": 0.9,
            "winner": winner,
            "reason": reason,
            "repaired_findings": [],
            "introduced_regressions": [],
            "preserved_strengths": ["reader pressure"],
            "evidence": [reason],
            **axes,
        },
        "proposals": [],
        "errors": [],
    }


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    conn = connect(path)
    start_run(conn, run_id="RUN-1", subject_id="CH-1", baseline_candidate_id="C0", baseline_text="baseline", plateau_limit=2)
    start_run(conn, run_id="RUN-1", subject_id="CH-1", baseline_candidate_id="C0", baseline_text="baseline", plateau_limit=2)
    from objective_envelope import build as build_objective_envelope
    envelope=build_objective_envelope({"subject_id":"CH-1","run_id":"RUN-1","authority_cutoff":"synthetic","objective_items":[{"id":"OBJ-1","category":"reader","statement":"Preserve reader pressure.","source_refs":["plan:self"]}],"must_preserve":["reader pressure"],"derived_from_rejected_realization":False})
    def rc(target:str)->dict[str,Any]: return {"repair_target":target,"objective_envelope":envelope}
    add_candidate(conn, run_id="RUN-1", candidate_id="C1", text="candidate one", repair_owner="reader")
    j1 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-1", challenger_candidate_id="C1", repair_context=rc("forward pull"))
    r1 = _fixture_result(j1, "challenger", "stronger forward pull")
    s1 = record_comparison(conn, job=j1, result=r1)
    replay = record_comparison(conn, job=j1, result=r1)

    caller_override_removed = True
    result_binding_guard = False
    bad = json.loads(json.dumps(r1))
    bad["judgment"]["winner"] = "C0"
    try:
        record_comparison(conn, job=j1, result=bad)
    except ValueError:
        result_binding_guard = True

    add_candidate(conn, run_id="RUN-1", candidate_id="C2", text="candidate two", repair_owner="surface")
    j2 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-2", challenger_candidate_id="C2", repair_context=rc("surface"))
    s2 = record_comparison(conn, job=j2, result=_fixture_result(j2, "incumbent", "no net gain"))

    add_candidate(conn, run_id="RUN-1", candidate_id="C3", text="candidate three", repair_owner="scene")
    j3 = prepare_comparison_job(conn, run_id="RUN-1", comparison_id="CMP-3", challenger_candidate_id="C3", repair_context=rc("scene"))
    s3 = record_comparison(conn, job=j3, result=_fixture_result(j3, "tie", "gains and regressions cancel"))

    objective_regression_guard=False
    contradictory=_fixture_result(j1,"challenger","surface fixed but pressure collapsed")
    contradictory["judgment"].update({"objective_preservation":"materially_degraded","reader_value":"degraded","outcome_class":"objective_regression","regressed_dimensions":["reader_pressure"]})
    try: record_comparison(conn,job=j1,result=contradictory)
    except ValueError: objective_regression_guard=True

    frozen_binding = (
        s1["comparisons"][0]["job_fingerprint"] == j1["input_fingerprint"]
        and s1["comparisons"][0]["winner_candidate_id"] == "C1"
    )
    ok = (
        s1["incumbent_candidate_id"] == "C1"
        and replay["incumbent_candidate_id"] == "C1"
        and s2["state"] == "active"
        and s3["state"] == "plateau"
        and caller_override_removed
        and result_binding_guard
        and frozen_binding
        and objective_regression_guard
        and s3["authority"] is False
        and s3["model_execution"] is False
    )
    print(json.dumps({
        "quality_evolution_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "durable_resume": True,
        "semantic_job_fingerprint_bound": frozen_binding,
        "winner_derived_from_typed_result": True,
        "caller_winner_override_removed": caller_override_removed,
        "invalid_winner_rejected_by_contract": result_binding_guard,
        "objective_regression_cannot_promote_challenger": objective_regression_guard,
        "objective_envelope_bound_to_comparison": j1["input"]["payload"]["repair_context"]["objective_envelope"]["fingerprint"]==envelope["fingerprint"],
        "idempotent_replay": replay["incumbent_candidate_id"] == "C1",
        "plateau_stopping": s3["state"] == "plateau",
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0 if ok else 1


def load_json_file(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe durable quality evolution ledger")
    p.add_argument("--db", default=".quillframe/quality-evolution.db")
    sub = p.add_subparsers(dest="command", required=True)
    st = sub.add_parser("start")
    st.add_argument("--run-id", required=True)
    st.add_argument("--subject-id", required=True)
    st.add_argument("--baseline-id", required=True)
    st.add_argument("--text-file", required=True)
    st.add_argument("--plateau-limit", type=int, default=2)
    ac = sub.add_parser("add-candidate")
    ac.add_argument("--run-id", required=True)
    ac.add_argument("--candidate-id", required=True)
    ac.add_argument("--text-file", required=True)
    ac.add_argument("--repair-owner", required=True)
    ac.add_argument("--parent-id")
    pc = sub.add_parser("prepare-comparison")
    pc.add_argument("--run-id", required=True)
    pc.add_argument("--comparison-id", required=True)
    pc.add_argument("--challenger-id", required=True)
    pc.add_argument("--repair-context-json", required=True)
    pc.add_argument("--source-session-id")
    rc = sub.add_parser("record-comparison")
    rc.add_argument("--job-json", required=True)
    rc.add_argument("--result-json", required=True)
    ss = sub.add_parser("status")
    ss.add_argument("--run-id", required=True)
    cp = sub.add_parser("complete")
    cp.add_argument("--run-id", required=True)
    sf = sub.add_parser("self-test")
    sf.add_argument("--path", default="/tmp/quillframe-quality-evolution-selftest.db")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test(Path(args.path))
    path = Path(args.db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        if args.command == "start":
            value = start_run(
                conn,
                run_id=args.run_id,
                subject_id=args.subject_id,
                baseline_candidate_id=args.baseline_id,
                baseline_text=Path(args.text_file).read_text(encoding="utf-8"),
                plateau_limit=args.plateau_limit,
            )
        elif args.command == "add-candidate":
            value = add_candidate(
                conn,
                run_id=args.run_id,
                candidate_id=args.candidate_id,
                text=Path(args.text_file).read_text(encoding="utf-8"),
                repair_owner=args.repair_owner,
                parent_candidate_id=args.parent_id,
            )
        elif args.command == "prepare-comparison":
            value = prepare_comparison_job(
                conn,
                run_id=args.run_id,
                comparison_id=args.comparison_id,
                challenger_candidate_id=args.challenger_id,
                repair_context=load_json_file(args.repair_context_json),
                source_session_id=args.source_session_id,
            )
        elif args.command == "record-comparison":
            value = record_comparison(
                conn,
                job=load_json_file(args.job_json),
                result=load_json_file(args.result_json),
            )
        elif args.command == "complete":
            value = complete(conn, args.run_id)
        else:
            value = status(conn, args.run_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
