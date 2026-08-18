#!/usr/bin/env python3
"""Deterministic architecture ablation for candidate lineage.

This is not a literary-quality judge. It tests whether the legacy evolution ledger
can represent prose derivation independently from comparison ancestry, and
whether the lineage extension closes that observability/provenance gap without
adding semantic calls or changing winner selection.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "quality"
if str(QUALITY) not in sys.path:
    sys.path.insert(0, str(QUALITY))

import candidate_lineage as cl  # noqa: E402
import quality_evolution as qe  # noqa: E402

SCHEMA = "quillframe_candidate_lineage_ablation_v1"


def run(path: Path) -> dict:
    if path.exists():
        path.unlink()
    conn = qe.connect(path)
    cl.migrate(conn)
    qe.start_run(conn, run_id="ABL-L", subject_id="CH-ABL", baseline_candidate_id="A", baseline_text="baseline", plateau_limit=3)
    cl.register_candidate(conn, run_id="ABL-L", candidate_id="A", origin="draft", prose_parent_candidate_id=None,
                          created_by_run_id="RUN-ABL")

    qe.add_candidate(conn, run_id="ABL-L", candidate_id="R", text="repair", repair_owner="surface")
    legacy_repair = qe.candidate_view(conn, "ABL-L", "R")
    repair = cl.register_candidate(conn, run_id="ABL-L", candidate_id="R", origin="repair", prose_parent_candidate_id="A",
                                   created_by_run_id="RUN-ABL")

    # We intentionally do not promote R: both challengers below have the same legacy
    # comparison parent A, demonstrating why parent_candidate_id alone cannot say
    # whether prose was inherited.
    qe.add_candidate(conn, run_id="ABL-L", candidate_id="F", text="fresh", repair_owner="scene")
    legacy_fresh = qe.candidate_view(conn, "ABL-L", "F")
    fresh = cl.register_candidate(conn, run_id="ABL-L", candidate_id="F", origin="fresh_regeneration", prose_parent_candidate_id=None,
                                  created_by_run_id="RUN-ABL")

    legacy_same_shape = (
        legacy_repair["parent_candidate_id"] == "A"
        and legacy_fresh["parent_candidate_id"] == "A"
        and "origin" not in legacy_repair
        and "prose_parent_candidate_id" not in legacy_repair
    )
    lineage_distinguishes = (
        repair["lineage"]["origin"] == "repair"
        and repair["lineage"]["prose_parent_candidate_id"] == "A"
        and fresh["lineage"]["origin"] == "fresh_regeneration"
        and fresh["lineage"]["prose_parent_candidate_id"] is None
        and fresh["lineage"]["comparison_parent_candidate_id"] == "A"
    )
    core_unchanged = qe.status(conn, "ABL-L")["incumbent_candidate_id"] == "A"
    conn.close()
    passed = legacy_same_shape and lineage_distinguishes and core_unchanged
    return {
        "schema": SCHEMA,
        "result": "PASS" if passed else "FAIL",
        "hypothesis": "explicit derivation lineage removes ambiguity without replacing comparison semantics",
        "condition_legacy": {
            "comparison_parent_visible": True,
            "prose_derivation_visible": False,
            "repair_vs_fresh_disambiguated": False,
        },
        "condition_lineage": {
            "comparison_parent_visible": True,
            "prose_derivation_visible": True,
            "repair_vs_fresh_disambiguated": lineage_distinguishes,
        },
        "actual_result": {
            "legacy_same_shape": legacy_same_shape,
            "lineage_distinguishes": lineage_distinguishes,
            "existing_incumbent_selection_unchanged": core_unchanged,
        },
        "cost": {
            "additional_semantic_calls": 0,
            "additional_writer_context": 0,
            "storage": "three small derived SQLite companion tables",
        },
        "limitations": [
            "This proves representation/binding behavior, not literary-quality gain.",
            "Literary winner selection remains owned by the existing independent semantic comparison contract.",
        ],
        "authority": False,
        "model_execution": False,
    }


def self_test(path: Path) -> int:
    result = run(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Candidate lineage deterministic architecture ablation")
    p.add_argument("command", choices=["run", "self-test"])
    p.add_argument("--path", default="/tmp/quillframe-candidate-lineage-ablation.db")
    args = p.parse_args()
    result = run(Path(args.path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
