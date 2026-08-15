#!/usr/bin/env python3
"""Executable regressions for the NovelForge propagation-debt ledger."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import propagation_debt as pd


def request(before: str, after: str, dependent: str = "PLAN-CH-010", dep_fp: str = "d", action: str = "replan") -> dict:
    return {
        "schema": pd.OPEN_SCHEMA,
        "project_id": "PROJECT-CI",
        "source_change": {
            "source_ref": "CHAR-1.current_location", "source_authority": "settled",
            "before_fingerprint": "sha256:" + before * 64, "after_fingerprint": "sha256:" + after * 64,
            "evidence_ref": f"settlement:TX-{before}-{after}", "evidence_fingerprint": "sha256:" + "9" * 64,
        },
        "dependency": {
            "dependency_ref": "DEP-CHAR1-PLAN10", "dependency_fingerprint": "sha256:" + "8" * 64,
            "source_ref": "CHAR-1.current_location", "dependent_ref": dependent,
            "dependent_fingerprint": "sha256:" + dep_fp * 64, "required_action": action,
            "reason": "The dependent artifact assumes the earlier location.",
        },
    }


def blocked(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def run_self_test(path: Path) -> int:
    if path.exists(): path.unlink()
    conn = pd.connect(path)
    first = pd.open_debt(conn, request("a", "b"))
    replay = pd.open_debt(conn, request("a", "b"))
    unchanged = pd.open_debt(conn, request("b", "b"))
    one_row = len(pd.list_debts(conn)) == 1

    conflict = request("a", "b"); conflict["dependency"]["reason"] = "Conflicting replay."
    conflicting_replay = blocked(lambda: pd.open_debt(conn, conflict))
    no_dep = request("b", "c"); del no_dep["dependency"]["dependency_ref"]
    global_blocked = blocked(lambda: pd.open_debt(conn, no_dep))

    wrong_discharge = blocked(lambda: pd.discharge(conn, {
        "schema": pd.DISCHARGE_SCHEMA, "debt_id": first["debt_id"],
        "source_after_fingerprint": "sha256:" + "c" * 64, "required_action": "replan",
        "result_ref": "wrong", "result_fingerprint": "sha256:" + "1" * 64,
        "dependent_after_fingerprint": "sha256:" + "2" * 64,
    }))
    receipt = {
        "schema": pd.DISCHARGE_SCHEMA, "debt_id": first["debt_id"],
        "source_after_fingerprint": "sha256:" + "b" * 64, "required_action": "replan",
        "result_ref": "plan:CH-010@new", "result_fingerprint": "sha256:" + "1" * 64,
        "dependent_after_fingerprint": "sha256:" + "2" * 64,
    }
    discharged = pd.discharge(conn, receipt)
    discharge_replay = pd.discharge(conn, receipt)

    old = pd.open_debt(conn, request("b", "c", "PLAN-CH-011", "3"))
    new = pd.open_debt(conn, request("c", "d", "PLAN-CH-011", "3"))
    sup_receipt = {
        "schema": pd.SUPERSEDE_SCHEMA, "debt_id": old["debt_id"], "new_debt_id": new["debt_id"],
        "evidence_ref": "settlement:TX-c-d", "evidence_fingerprint": "sha256:" + "7" * 64,
    }
    superseded = pd.supersede(conn, sup_receipt)
    supersede_replay = pd.supersede(conn, sup_receipt)
    uold = pd.open_debt(conn, request("1", "2", "PLAN-CH-013", "6"))
    unew = pd.open_debt(conn, request("3", "4", "PLAN-CH-013", "6"))
    noncontiguous = blocked(lambda: pd.supersede(conn, {
        "schema": pd.SUPERSEDE_SCHEMA, "debt_id": uold["debt_id"], "new_debt_id": unew["debt_id"],
        "evidence_ref": "settlement:noncontiguous", "evidence_fingerprint": "sha256:" + "6" * 64,
    }))

    target = pd.open_debt(conn, request("d", "e", "REVIEW-CH-012", "4", "revalidate"))
    no_waiver_evidence = blocked(lambda: pd.waive(conn, {
        "schema": pd.WAIVER_SCHEMA, "debt_id": target["debt_id"],
        "source_after_fingerprint": "sha256:" + "e" * 64, "actor_class": "authorized_human",
        "evidence_ref": "", "evidence_fingerprint": "sha256:" + "5" * 64, "reason": "No impact.",
    }))
    waived = pd.waive(conn, {
        "schema": pd.WAIVER_SCHEMA, "debt_id": target["debt_id"],
        "source_after_fingerprint": "sha256:" + "e" * 64, "actor_class": "authorized_human",
        "evidence_ref": "review:impact-012", "evidence_fingerprint": "sha256:" + "5" * 64,
        "reason": "The dependency was reviewed and needs no action.",
    })

    before_restart = pd.summary(conn)["open_debt_ids"]; conn.close()
    conn = pd.connect(path)
    after_restart = pd.summary(conn)["open_debt_ids"]
    restart_replay = pd.open_debt(conn, request("c", "d", "PLAN-CH-011", "3"))
    restart_ok = before_restart == after_restart and restart_replay["open_result"] == "already_exists"

    checks = {
        "explicit_dependency_creates_debt": first["status"] == "open",
        "open_is_idempotent": replay["debt_id"] == first["debt_id"] and replay["open_result"] == "already_exists" and one_row,
        "conflicting_replay_is_rejected": conflicting_replay,
        "unchanged_source_creates_no_debt": unchanged["status"] == "not_created",
        "no_global_invalidation_without_dependency": global_blocked,
        "discharge_binds_latest_source_fingerprint": wrong_discharge and discharged["status"] == "discharged",
        "discharge_is_idempotent": discharge_replay["status"] == "discharged",
        "supersession_requires_contiguous_source_lineage": superseded["status"] == "superseded" and noncontiguous,
        "supersede_is_idempotent": supersede_replay["status"] == "superseded",
        "waiver_requires_evidence": no_waiver_evidence and waived["status"] == "waived_with_evidence",
        "restart_preserves_open_debt_without_duplicate": restart_ok,
        "ledger_is_non_authoritative": all(
            not x["authority"] and not x["canon_authority"] and not x["framework_write_authority"] and not x["auto_action_performed"]
            for x in pd.list_debts(conn)
        ),
    }
    ok = all(checks.values())
    print(json.dumps({
        "propagation_debt_contract": "PASS" if ok else "FAIL", "schema": pd.SCHEMA,
        "required_actions": sorted(pd.ACTIONS), "statuses": sorted(pd.STATUSES), **checks, "model_execution": False,
    }, indent=2))
    conn.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run_self_test(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/novelforge-propagation-debt-selftest.db")))
