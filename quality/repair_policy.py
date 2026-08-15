#!/usr/bin/env python3
"""Deterministic routing policy for rejected prose repairs.

This module does not decide whether prose is good. It consumes an already-made
repair ownership classification and determines whether the next writer may see
and locally patch rejected prose or must perform a fresh realization from
mechanism-level defects plus unchanged authority constraints.

The purpose is to prevent a structural/reader-pressure failure from collapsing
into an endless checklist patch loop.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_repair_policy_v1"
OWNERS = {
    "story", "plan", "scene", "character", "reader", "surface",
    "continuity", "context", "memory", "research", "runtime", "human",
}
UPSTREAM_FRESH_OWNERS = {"story", "plan", "scene", "character", "reader"}
SCOPES = {"sentence", "paragraph", "block", "scene", "chapter", "multi_chapter", "unknown"}


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("repair policy payload must be object")
    owner = payload.get("repair_owner")
    if owner not in OWNERS:
        raise ValueError(f"invalid repair_owner: {owner}")
    scope = payload.get("failure_scope", "unknown")
    if scope not in SCOPES:
        raise ValueError(f"invalid failure_scope: {scope}")
    cluster = payload.get("cluster", False)
    rejected = payload.get("candidate_rejected", True)
    if not isinstance(cluster, bool) or not isinstance(rejected, bool):
        raise ValueError("cluster and candidate_rejected must be boolean")

    fresh = rejected and (
        owner in UPSTREAM_FRESH_OWNERS
        or (owner == "surface" and (cluster or scope in {"scene", "chapter", "multi_chapter"}))
    )
    generation_mode = "fresh_realization" if fresh else "local_or_bounded_repair"
    excluded = []
    required = ["authority_constraints", "mechanism_level_defects"]
    if fresh:
        excluded = ["rejected_prose", "concrete_critic_surface_patches", "prior_reviewer_verdict"]
        required += ["current_story_state", "repair_owner_goal"]

    return {
        "schema": SCHEMA,
        "repair_owner": owner,
        "failure_scope": scope,
        "cluster": cluster,
        "candidate_rejected": rejected,
        "generation_mode": generation_mode,
        "fresh_realization_required": fresh,
        "rejected_prose_visible_to_writer": not fresh,
        "concrete_critic_surface_patches_visible_to_writer": not fresh,
        "required_writer_context_classes": required,
        "excluded_writer_context_classes": excluded,
        "post_generation_fresh_review_required": fresh,
        "incumbent_comparison_may_happen_after_generation": True,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> dict[str, Any]:
    scene = evaluate({"repair_owner": "scene", "failure_scope": "scene", "candidate_rejected": True})
    reader = evaluate({"repair_owner": "reader", "failure_scope": "chapter", "candidate_rejected": True})
    local = evaluate({"repair_owner": "surface", "failure_scope": "sentence", "cluster": False, "candidate_rejected": True})
    surface_cluster = evaluate({"repair_owner": "surface", "failure_scope": "scene", "cluster": True, "candidate_rejected": True})
    accepted = evaluate({"repair_owner": "scene", "failure_scope": "scene", "candidate_rejected": False})
    checks = {
        "scene_failure_fresh": scene["fresh_realization_required"] is True,
        "reader_failure_fresh": reader["fresh_realization_required"] is True,
        "fresh_writer_cannot_see_rejected_prose": scene["rejected_prose_visible_to_writer"] is False,
        "fresh_writer_cannot_see_concrete_patches": scene["concrete_critic_surface_patches_visible_to_writer"] is False,
        "isolated_surface_can_patch": local["generation_mode"] == "local_or_bounded_repair",
        "surface_cluster_regenerates": surface_cluster["fresh_realization_required"] is True,
        "non_rejected_candidate_not_forced_fresh": accepted["fresh_realization_required"] is False,
    }
    return {
        "repair_policy_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge rejected-prose repair routing policy")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--input", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["repair_policy_contract"] == "PASS" else 1
    value = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(value)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
