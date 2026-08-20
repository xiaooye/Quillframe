#!/usr/bin/env python3
"""Lineage-aware runtime facade for Quillframe quality evolution.

`quality_evolution` is the private incumbent/challenger storage engine and
`quality.compare` remains the semantic winner owner. This module is the only
1.0 runtime entrypoint: every candidate must have an explicit Candidate Lineage
record before comparison or consumption. Missing provenance fails closed and is
never inferred. This module never grants Canon or settlement authority.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "quality"
if str(QUALITY) not in sys.path:
    sys.path.insert(0, str(QUALITY))

import candidate_lineage as cl  # noqa: E402
import quality_evolution as qe  # noqa: E402

SCHEMA = "quillframe_candidate_lineage_runtime_v1"


def connect(path: Path):
    conn = qe.connect(path)
    cl.migrate(conn)
    return conn


def _expected_parent(conn, run_id: str, parent_candidate_id: str | None) -> str:
    run = qe._run(conn, run_id)
    if run["state"] != "active":
        raise ValueError(f"run is not active: {run['state']}")
    parent = parent_candidate_id or str(run["incumbent_candidate_id"])
    qe._candidate(conn, run_id, parent)
    return parent


def _prevalidate_derivation(
    conn,
    *,
    run_id: str,
    origin: str,
    parent_candidate_id: str | None,
    prose_parent_candidate_id: str | None,
) -> str:
    if origin not in cl.ORIGINS - {"draft"}:
        raise ValueError("challenger origin must be repair|fresh_regeneration|user_edit")
    parent = _expected_parent(conn, run_id, parent_candidate_id)
    if prose_parent_candidate_id is not None:
        qe._candidate(conn, run_id, prose_parent_candidate_id)
    if origin == "repair" and prose_parent_candidate_id != parent:
        raise ValueError("repair must explicitly name its direct comparison parent as prose parent")
    if origin == "fresh_regeneration" and prose_parent_candidate_id is not None:
        raise ValueError("fresh regeneration must not inherit incumbent/rejected prose")
    return parent


def start_run(
    conn,
    *,
    run_id: str,
    subject_id: str,
    baseline_candidate_id: str,
    baseline_text: str,
    created_by_run_id: str,
    created_by_session_id: str | None = None,
    authority_snapshot_fingerprint: str | None = None,
    plateau_limit: int = 2,
) -> dict[str, Any]:
    qe.start_run(
        conn,
        run_id=run_id,
        subject_id=subject_id,
        baseline_candidate_id=baseline_candidate_id,
        baseline_text=baseline_text,
        plateau_limit=plateau_limit,
    )
    cl.register_candidate(
        conn,
        run_id=run_id,
        candidate_id=baseline_candidate_id,
        origin="draft",
        prose_parent_candidate_id=None,
        created_by_run_id=created_by_run_id,
        created_by_session_id=created_by_session_id,
        authority_snapshot_fingerprint=authority_snapshot_fingerprint,
    )
    return status(conn, run_id)


def add_candidate(
    conn,
    *,
    run_id: str,
    candidate_id: str,
    text: str,
    repair_owner: str,
    origin: str,
    prose_parent_candidate_id: str | None,
    created_by_run_id: str,
    created_by_session_id: str | None = None,
    parent_candidate_id: str | None = None,
    authority_snapshot_fingerprint: str | None = None,
    diff_fingerprint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create/recover a challenger and bind explicit derivation provenance.

    Provenance is validated *before* the core candidate mutation. If a process
    crashes between the core insert and lineage registration, the run becomes
    lineage-incomplete and all comparison operations through this facade fail
    closed until the exact provenance is explicitly supplied again.
    """
    parent = _prevalidate_derivation(
        conn,
        run_id=run_id,
        origin=origin,
        parent_candidate_id=parent_candidate_id,
        prose_parent_candidate_id=prose_parent_candidate_id,
    )
    qe.add_candidate(
        conn,
        run_id=run_id,
        candidate_id=candidate_id,
        text=text,
        repair_owner=repair_owner,
        parent_candidate_id=parent,
        metadata=metadata,
    )
    cl.register_candidate(
        conn,
        run_id=run_id,
        candidate_id=candidate_id,
        origin=origin,
        prose_parent_candidate_id=prose_parent_candidate_id,
        created_by_run_id=created_by_run_id,
        created_by_session_id=created_by_session_id,
        authority_snapshot_fingerprint=authority_snapshot_fingerprint,
        diff_fingerprint=diff_fingerprint,
    )
    return cl.candidate_lineage_view(conn, run_id, candidate_id)


def lineage_issues(conn, run_id: str) -> list[dict[str, str]]:
    """Return deterministic provenance defects; never infer a repair."""
    cl.migrate(conn)
    core = qe.status(conn, run_id)
    baseline_id = str(core["baseline_candidate_id"])
    issues: list[dict[str, str]] = []
    for candidate in core["candidates"]:
        cid = str(candidate["candidate_id"])
        line = conn.execute(
            "SELECT * FROM evolution_candidate_lineage WHERE run_id=? AND candidate_id=?",
            (run_id, cid),
        ).fetchone()
        if line is None:
            issues.append({"candidate_id": cid, "code": "MISSING_LINEAGE"})
            continue
        if line["comparison_parent_candidate_id"] != candidate["parent_candidate_id"]:
            issues.append({"candidate_id": cid, "code": "COMPARISON_PARENT_MISMATCH"})
        origin = str(line["origin"])
        prose_parent = line["prose_parent_candidate_id"]
        comparison_parent = candidate["parent_candidate_id"]
        if cid == baseline_id:
            if origin != "draft" or comparison_parent is not None or prose_parent is not None:
                issues.append({"candidate_id": cid, "code": "INVALID_BASELINE_LINEAGE"})
            continue
        if origin == "draft":
            issues.append({"candidate_id": cid, "code": "CHALLENGER_MARKED_DRAFT"})
        elif origin == "repair" and prose_parent != comparison_parent:
            issues.append({"candidate_id": cid, "code": "REPAIR_PROSE_PARENT_MISMATCH"})
        elif origin == "fresh_regeneration" and prose_parent is not None:
            issues.append({"candidate_id": cid, "code": "FRESH_REGENERATION_HAS_PROSE_PARENT"})
        elif origin == "user_edit" and prose_parent is not None:
            try:
                qe._candidate(conn, run_id, str(prose_parent))
            except ValueError:
                issues.append({"candidate_id": cid, "code": "USER_EDIT_PROSE_PARENT_MISSING"})
    return issues


def require_complete_lineage(conn, run_id: str) -> None:
    issues = lineage_issues(conn, run_id)
    if issues:
        detail = ", ".join(f"{i['candidate_id']}:{i['code']}" for i in issues)
        raise ValueError("lineage-aware runtime refuses incomplete/invalid provenance: " + detail)


def prepare_comparison_job(
    conn,
    *,
    run_id: str,
    comparison_id: str,
    challenger_candidate_id: str,
    repair_context: dict[str, Any],
    source_session_id: str | None = None,
) -> dict[str, Any]:
    require_complete_lineage(conn, run_id)
    return qe.prepare_comparison_job(
        conn,
        run_id=run_id,
        comparison_id=comparison_id,
        challenger_candidate_id=challenger_candidate_id,
        repair_context=repair_context,
        source_session_id=source_session_id,
    )


def record_comparison(conn, *, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    payload = job.get("input", {}).get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("evolution_run_id"), str):
        raise ValueError("quality.compare job with evolution_run_id required")
    run_id = payload["evolution_run_id"]
    require_complete_lineage(conn, run_id)
    qe.record_comparison(conn, job=job, result=result)
    return status(conn, run_id)


def complete(conn, run_id: str) -> dict[str, Any]:
    require_complete_lineage(conn, run_id)
    qe.complete(conn, run_id)
    return status(conn, run_id)


def status(conn, run_id: str) -> dict[str, Any]:
    graph = cl.graph(conn, run_id)
    issues = lineage_issues(conn, run_id)
    return {
        "schema": SCHEMA,
        "lineage_schema": cl.SCHEMA,
        "run_id": run_id,
        "subject_id": graph["subject_id"],
        "state": graph["state"],
        "incumbent_candidate_id": graph["incumbent_candidate_id"],
        "lineage_complete": not issues,
        "lineage_issues": issues,
        "graph": graph,
        "authority": False,
        "permissions": {"canon_write": False, "settlement_write": False, "framework_write": False},
        "model_execution": False,
    }


def load_json_file(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    conn = connect(path)
    start_run(
        conn,
        run_id="RUN-RUNTIME",
        subject_id="CH-RUNTIME",
        baseline_candidate_id="A",
        baseline_text="baseline",
        created_by_run_id="RUN-MANAGER",
        created_by_session_id="SES-MANAGER",
        plateau_limit=3,
    )
    add_candidate(
        conn,
        run_id="RUN-RUNTIME",
        candidate_id="A1",
        text="repair",
        repair_owner="surface",
        origin="repair",
        prose_parent_candidate_id="A",
        created_by_run_id="RUN-MANAGER",
    )

    # Simulate corrupted/incomplete state, then prove the runtime fails closed.
    qe.add_candidate(
        conn,
        run_id="RUN-RUNTIME",
        candidate_id="A2",
        text="fresh candidate",
        repair_owner="scene",
    )
    incomplete_state_detected = any(
        i["candidate_id"] == "A2" and i["code"] == "MISSING_LINEAGE"
        for i in lineage_issues(conn, "RUN-RUNTIME")
    )

    from objective_envelope import build as build_objective_envelope

    envelope = build_objective_envelope({
        "subject_id": "CH-RUNTIME",
        "run_id": "RUN-RUNTIME",
        "authority_cutoff": "synthetic",
        "objective_items": [{
            "id": "OBJ-RUNTIME",
            "category": "reader",
            "statement": "Preserve reader pressure.",
            "source_refs": ["plan:self"],
        }],
        "must_preserve": ["reader pressure"],
        "derived_from_rejected_realization": False,
    })
    repair_context = {"repair_target": "fresh realization", "objective_envelope": envelope}
    comparison_blocked = False
    try:
        prepare_comparison_job(
            conn,
            run_id="RUN-RUNTIME",
            comparison_id="CMP-BLOCKED",
            challenger_candidate_id="A2",
            repair_context=repair_context,
        )
    except ValueError:
        comparison_blocked = True

    # Recovery is explicit and idempotent: caller supplies the missing fact;
    # runtime never guesses it from repair_owner or text.
    add_candidate(
        conn,
        run_id="RUN-RUNTIME",
        candidate_id="A2",
        text="fresh candidate",
        repair_owner="scene",
        origin="fresh_regeneration",
        prose_parent_candidate_id=None,
        created_by_run_id="RUN-MANAGER",
    )
    recovered = status(conn, "RUN-RUNTIME")["lineage_complete"] is True
    job = prepare_comparison_job(
        conn,
        run_id="RUN-RUNTIME",
        comparison_id="CMP-A2",
        challenger_candidate_id="A2",
        repair_context=repair_context,
    )
    result = qe._fixture_result(job, "incumbent", "fresh candidate does not improve objectives")
    after = record_comparison(conn, job=job, result=result)

    before_resume = status(conn, "RUN-RUNTIME")
    conn.close()
    conn = connect(path)
    after_resume = status(conn, "RUN-RUNTIME")
    conn.close()

    tests = {
        "baseline_registered": before_resume["graph"]["candidates"][0]["lineage"]["origin"] == "draft",
        "repair_registered": before_resume["graph"]["candidates"][1]["lineage"]["origin"] == "repair",
        "incomplete_state_detected": incomplete_state_detected,
        "comparison_fails_closed_on_missing_lineage": comparison_blocked,
        "explicit_recovery_without_guessing": recovered,
        "fresh_regeneration_has_no_prose_parent": before_resume["graph"]["candidates"][2]["lineage"]["prose_parent_candidate_id"] is None,
        "existing_semantic_comparator_unchanged": after["incumbent_candidate_id"] == "A",
        "resume_exact": before_resume == after_resume,
    }
    ok = all(tests.values()) and before_resume["authority"] is False
    print(json.dumps({
        "candidate_lineage_runtime_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "tests": tests,
        "single_lineage_runtime_entrypoint": True,
        "lineage_aware_runtime_fails_closed": True,
        "semantic_comparator": "quality.compare",
        "additional_model_calls": 0,
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe lineage-aware quality evolution runtime")
    parser.add_argument("--db", default=".quillframe/quality-evolution.db")
    sub = parser.add_subparsers(dest="command", required=True)

    st = sub.add_parser("start")
    st.add_argument("--run-id", required=True)
    st.add_argument("--subject-id", required=True)
    st.add_argument("--baseline-id", required=True)
    st.add_argument("--text-file", required=True)
    st.add_argument("--created-by-run-id", required=True)
    st.add_argument("--created-by-session-id")
    st.add_argument("--authority-snapshot-fingerprint")
    st.add_argument("--plateau-limit", type=int, default=2)

    ac = sub.add_parser("add-candidate")
    ac.add_argument("--run-id", required=True)
    ac.add_argument("--candidate-id", required=True)
    ac.add_argument("--text-file", required=True)
    ac.add_argument("--repair-owner", required=True)
    ac.add_argument("--origin", choices=sorted(cl.ORIGINS - {"draft"}), required=True)
    ac.add_argument("--prose-parent-id")
    ac.add_argument("--parent-id")
    ac.add_argument("--created-by-run-id", required=True)
    ac.add_argument("--created-by-session-id")
    ac.add_argument("--authority-snapshot-fingerprint")
    ac.add_argument("--diff-fingerprint")
    ac.add_argument("--metadata-json")

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
    sf.add_argument("--path", default="/tmp/quillframe-candidate-lineage-runtime-selftest.db")

    args = parser.parse_args()
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
                created_by_run_id=args.created_by_run_id,
                created_by_session_id=args.created_by_session_id,
                authority_snapshot_fingerprint=args.authority_snapshot_fingerprint,
                plateau_limit=args.plateau_limit,
            )
        elif args.command == "add-candidate":
            value = add_candidate(
                conn,
                run_id=args.run_id,
                candidate_id=args.candidate_id,
                text=Path(args.text_file).read_text(encoding="utf-8"),
                repair_owner=args.repair_owner,
                origin=args.origin,
                prose_parent_candidate_id=args.prose_parent_id,
                parent_candidate_id=args.parent_id,
                created_by_run_id=args.created_by_run_id,
                created_by_session_id=args.created_by_session_id,
                authority_snapshot_fingerprint=args.authority_snapshot_fingerprint,
                diff_fingerprint=args.diff_fingerprint,
                metadata=load_json_file(args.metadata_json) if args.metadata_json else None,
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
