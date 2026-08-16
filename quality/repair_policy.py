#!/usr/bin/env python3
"""Deterministic writer-context boundary for a semantic Editor repair plan.

The Editor/model owns repair depth and chooses local_or_bounded_repair versus
fresh_realization. This module does not infer that choice from literary owner,
scope, HF code, paragraph metrics, Reader labels or failure clusters. It only
enforces the information boundary implied by the already-made semantic choice.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_repair_policy_v2"
OWNERS = {
    "story", "plan", "scene", "character", "reader_pressure", "surface",
    "continuity", "context", "research", "runtime", "human",
}
GENERATION_MODES = {"local_or_bounded_repair", "fresh_realization"}


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("repair policy payload must be object")
    owner = payload.get("repair_owner")
    if owner not in OWNERS:
        raise ValueError(f"invalid repair_owner: {owner}")
    generation_mode = payload.get("generation_mode")
    if generation_mode not in GENERATION_MODES:
        raise ValueError("generation_mode must be Editor-selected local_or_bounded_repair|fresh_realization")
    candidate_rejected = payload.get("candidate_rejected", True)
    if not isinstance(candidate_rejected, bool):
        raise ValueError("candidate_rejected must be boolean")
    if generation_mode == "fresh_realization" and not candidate_rejected:
        raise ValueError("fresh_realization information boundary requires a rejected candidate")

    fresh = generation_mode == "fresh_realization"
    excluded = []
    required = ["authority_constraints", "editor_repair_plan"]
    if fresh:
        excluded = ["rejected_prose", "concrete_critic_surface_patches", "prior_reviewer_verdict"]
        required += ["current_story_state"]
    else:
        required += ["bounded_repair_evidence"]

    return {
        "schema": SCHEMA,
        "repair_owner": owner,
        "generation_mode": generation_mode,
        "candidate_rejected": candidate_rejected,
        "fresh_realization_required": fresh,
        "rejected_prose_visible_to_writer": not fresh,
        "concrete_critic_surface_patches_visible_to_writer": not fresh,
        "required_writer_context_classes": required,
        "excluded_writer_context_classes": excluded,
        "post_generation_fresh_review_required": fresh,
        "incumbent_comparison_may_happen_after_generation": True,
        "repair_depth_judged_by_runtime": False,
        "literary_owner_to_depth_mapping_used": False,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> dict[str, Any]:
    scene_local = evaluate({"repair_owner": "scene", "generation_mode": "local_or_bounded_repair", "candidate_rejected": True})
    surface_fresh = evaluate({"repair_owner": "surface", "generation_mode": "fresh_realization", "candidate_rejected": True})
    same_owner_fresh = evaluate({"repair_owner": "scene", "generation_mode": "fresh_realization", "candidate_rejected": True})
    same_owner_local = evaluate({"repair_owner": "scene", "generation_mode": "local_or_bounded_repair", "candidate_rejected": True})
    invalid_fresh_accepted = False
    try:
        evaluate({"repair_owner": "scene", "generation_mode": "fresh_realization", "candidate_rejected": False})
    except ValueError:
        invalid_fresh_accepted = True
    missing_semantic_choice = False
    try:
        evaluate({"repair_owner": "scene", "candidate_rejected": True})
    except ValueError:
        missing_semantic_choice = True

    checks = {
        "same_owner_can_route_local": same_owner_local["fresh_realization_required"] is False,
        "same_owner_can_route_fresh": same_owner_fresh["fresh_realization_required"] is True,
        "surface_can_route_fresh_when_editor_selects_it": surface_fresh["fresh_realization_required"] is True,
        "fresh_writer_cannot_see_rejected_prose": same_owner_fresh["rejected_prose_visible_to_writer"] is False,
        "fresh_writer_cannot_see_concrete_patches": same_owner_fresh["concrete_critic_surface_patches_visible_to_writer"] is False,
        "local_writer_can_see_bounded_repair_evidence": scene_local["rejected_prose_visible_to_writer"] is True,
        "fresh_on_accepted_candidate_rejected": invalid_fresh_accepted,
        "missing_editor_generation_mode_rejected": missing_semantic_choice,
        "repair_depth_judged_by_runtime": same_owner_fresh["repair_depth_judged_by_runtime"] is False,
        "literary_owner_to_depth_mapping_used": same_owner_fresh["literary_owner_to_depth_mapping_used"] is False,
    }
    return {
        "repair_policy_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge semantic-repair writer-context boundary")
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