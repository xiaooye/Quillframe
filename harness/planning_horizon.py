#!/usr/bin/env python3
"""Portable planning commitment-horizon contract for Quillframe.

This deterministic tool controls admission to known planning depths and selects
an evidence-bounded first rebalance frontier. It does not judge story quality,
run semantic reconciliation, mutate an active plan, create propagation debt, or
grant Canon/Project/Framework/Settlement authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

POLICY_SCHEMA = "quillframe_planning_horizon_policy_v1"
REGION_SCHEMA = "quillframe_planning_horizon_region_v1"
REGION_REQUEST_SCHEMA = "quillframe_planning_horizon_region_request_v1"
ADMISSION_REQUEST_SCHEMA = "quillframe_planning_horizon_admission_request_v1"
ADMISSION_RESULT_SCHEMA = "quillframe_planning_horizon_admission_result_v1"
TRANSITION_REQUEST_SCHEMA = "quillframe_planning_horizon_transition_request_v1"
TRANSITION_RESULT_SCHEMA = "quillframe_planning_horizon_transition_result_v1"
REBALANCE_REQUEST_SCHEMA = "quillframe_planning_rebalance_frontier_request_v1"
REBALANCE_RESULT_SCHEMA = "quillframe_planning_rebalance_frontier_result_v1"

DEPTHS = ("arc_boundary", "beat", "scene_intent", "chapter_detail")
DEPTH_RANK = {name: idx for idx, name in enumerate(DEPTHS)}
STRENGTHS = ("open", "soft", "hard")
ARTIFACT_DEPTH = {
    "arc_role": "arc_boundary",
    "beat_sheet": "beat",
    "scene_card": "scene_intent",
    "chapter_plan": "chapter_detail",
}
KNOWN_ACTOR_CLASSES = {
    "user",
    "authorized_human",
    "authorized_planner",
    "manager",
    "writer",
    "semantic_worker",
}
AUTHORITY_FALSE = {
    "authority": False,
    "canon_authority": False,
    "project_write_authority": False,
    "framework_write_authority": False,
    "settlement_authority": False,
    "model_execution": False,
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty string")
    return value.strip()


def sha(value: Any, field: str) -> str:
    value = nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be sha256:<64 hex>") from exc
    return value


def string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be array")
    out = []
    for idx, item in enumerate(value):
        out.append(nonempty(item, f"{field}[{idx}]"))
    if len(set(out)) != len(out):
        raise ValueError(f"{field} must not contain duplicates")
    return out


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def normalize_policy(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != POLICY_SCHEMA:
        raise ValueError(f"policy.schema must be {POLICY_SCHEMA}")
    allowed = {
        "schema",
        "profile_id",
        "strength_depth_ceiling",
        "allowed_promoter_actor_classes",
    }
    if set(raw) - allowed:
        raise ValueError("policy has unsupported fields")
    profile_id = nonempty(raw.get("profile_id"), "policy.profile_id")
    ceilings = raw.get("strength_depth_ceiling")
    if not isinstance(ceilings, dict) or set(ceilings) != set(STRENGTHS):
        raise ValueError(f"policy.strength_depth_ceiling must define exactly {list(STRENGTHS)}")
    normalized_ceilings: dict[str, str] = {}
    for strength in STRENGTHS:
        depth = nonempty(ceilings.get(strength), f"policy.strength_depth_ceiling.{strength}")
        if depth not in DEPTH_RANK:
            raise ValueError(f"unknown planning depth: {depth}")
        normalized_ceilings[strength] = depth
    if not (
        DEPTH_RANK[normalized_ceilings["open"]]
        <= DEPTH_RANK[normalized_ceilings["soft"]]
        <= DEPTH_RANK[normalized_ceilings["hard"]]
    ):
        raise ValueError("policy ceilings must be monotonic open <= soft <= hard")
    actors = string_list(raw.get("allowed_promoter_actor_classes"), "policy.allowed_promoter_actor_classes")
    if not actors:
        raise ValueError("policy.allowed_promoter_actor_classes must not be empty")
    unknown = sorted(set(actors) - KNOWN_ACTOR_CLASSES)
    if unknown:
        raise ValueError(f"unknown actor classes: {unknown}")
    if {"writer", "semantic_worker"} & set(actors):
        raise ValueError("writer/semantic_worker cannot be horizon promoter classes")
    out = {
        "schema": POLICY_SCHEMA,
        "profile_id": profile_id,
        "strength_depth_ceiling": normalized_ceilings,
        "allowed_promoter_actor_classes": actors,
    }
    out["policy_fingerprint"] = fp(out)
    out.update(AUTHORITY_FALSE)
    return out


def policy_payload(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "profile_id": policy["profile_id"],
        "strength_depth_ceiling": policy["strength_depth_ceiling"],
        "allowed_promoter_actor_classes": policy["allowed_promoter_actor_classes"],
    }


def verify_policy(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("policy must be object")
    normalized = normalize_policy(policy_payload(raw) if "policy_fingerprint" in raw else raw)
    if "policy_fingerprint" in raw:
        supplied = sha(raw.get("policy_fingerprint"), "policy.policy_fingerprint")
        if supplied != normalized["policy_fingerprint"]:
            raise ValueError("policy fingerprint mismatch")
    return normalized


def region_payload(region: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": REGION_SCHEMA,
        "project_id": region["project_id"],
        "region_id": region["region_id"],
        "plan_ref": region["plan_ref"],
        "semantic_scope": region.get("semantic_scope"),
        "story_order": region.get("story_order"),
        "commitment_strength": region["commitment_strength"],
        "max_planning_depth": region["max_planning_depth"],
        "assumption_refs": region["assumption_refs"],
        "dependency_refs": region["dependency_refs"],
        "unresolved_decision_refs": region["unresolved_decision_refs"],
        "policy_fingerprint": region["policy_fingerprint"],
        "version": region["version"],
    }


def _normalize_story_order(value: Any) -> dict[str, int | None] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - {"start", "end"}:
        raise ValueError("story_order must contain only start/end")
    start, end = value.get("start"), value.get("end")
    for name, item in (("start", start), ("end", end)):
        if item is not None and (not isinstance(item, int) or item < 0):
            raise ValueError(f"story_order.{name} must be null or non-negative integer")
    if start is not None and end is not None and start > end:
        raise ValueError("story_order.start must be <= story_order.end")
    return {"start": start, "end": end}


def create_region(policy_raw: Any, request: Any) -> dict[str, Any]:
    policy = verify_policy(policy_raw)
    if not isinstance(request, dict) or request.get("schema") != REGION_REQUEST_SCHEMA:
        raise ValueError(f"request.schema must be {REGION_REQUEST_SCHEMA}")
    allowed = {
        "schema", "project_id", "region_id", "plan_ref", "semantic_scope", "story_order",
        "commitment_strength", "max_planning_depth", "assumption_refs", "dependency_refs",
        "unresolved_decision_refs",
    }
    if set(request) - allowed:
        raise ValueError("region request has unsupported fields")
    strength = nonempty(request.get("commitment_strength"), "commitment_strength")
    if strength not in STRENGTHS:
        raise ValueError(f"commitment_strength must be one of {list(STRENGTHS)}")
    depth = nonempty(request.get("max_planning_depth"), "max_planning_depth")
    if depth not in DEPTH_RANK:
        raise ValueError(f"unknown planning depth: {depth}")
    profile_ceiling = policy["strength_depth_ceiling"][strength]
    if DEPTH_RANK[depth] > DEPTH_RANK[profile_ceiling]:
        raise ValueError(f"region depth {depth} exceeds profile ceiling {profile_ceiling} for strength {strength}")
    semantic_scope = request.get("semantic_scope")
    if semantic_scope is not None:
        semantic_scope = nonempty(semantic_scope, "semantic_scope")
    region = {
        "schema": REGION_SCHEMA,
        "project_id": nonempty(request.get("project_id"), "project_id"),
        "region_id": nonempty(request.get("region_id"), "region_id"),
        "plan_ref": nonempty(request.get("plan_ref"), "plan_ref"),
        "semantic_scope": semantic_scope,
        "story_order": _normalize_story_order(request.get("story_order")),
        "commitment_strength": strength,
        "max_planning_depth": depth,
        "assumption_refs": string_list(request.get("assumption_refs"), "assumption_refs"),
        "dependency_refs": string_list(request.get("dependency_refs"), "dependency_refs"),
        "unresolved_decision_refs": string_list(request.get("unresolved_decision_refs"), "unresolved_decision_refs"),
        "policy_fingerprint": policy["policy_fingerprint"],
        "version": 1,
    }
    region["artifact_fingerprint"] = fp(region_payload(region))
    region.update(AUTHORITY_FALSE)
    return region


def verify_region(policy_raw: Any, raw: Any) -> dict[str, Any]:
    policy = verify_policy(policy_raw)
    if not isinstance(raw, dict) or raw.get("schema") != REGION_SCHEMA:
        raise ValueError(f"region.schema must be {REGION_SCHEMA}")
    required = {
        "project_id", "region_id", "plan_ref", "commitment_strength", "max_planning_depth",
        "assumption_refs", "dependency_refs", "unresolved_decision_refs", "policy_fingerprint",
        "version", "artifact_fingerprint",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"region missing fields: {missing}")
    if raw.get("policy_fingerprint") != policy["policy_fingerprint"]:
        raise ValueError("region policy fingerprint does not match current policy")
    if not isinstance(raw.get("version"), int) or raw["version"] < 1:
        raise ValueError("region.version must be positive integer")
    request = {
        "schema": REGION_REQUEST_SCHEMA,
        "project_id": raw.get("project_id"), "region_id": raw.get("region_id"), "plan_ref": raw.get("plan_ref"),
        "semantic_scope": raw.get("semantic_scope"), "story_order": raw.get("story_order"),
        "commitment_strength": raw.get("commitment_strength"), "max_planning_depth": raw.get("max_planning_depth"),
        "assumption_refs": raw.get("assumption_refs"), "dependency_refs": raw.get("dependency_refs"),
        "unresolved_decision_refs": raw.get("unresolved_decision_refs"),
    }
    normalized = create_region(policy, request)
    normalized["version"] = raw["version"]
    normalized["artifact_fingerprint"] = fp(region_payload(normalized))
    supplied_fp = sha(raw.get("artifact_fingerprint"), "region.artifact_fingerprint")
    if supplied_fp != normalized["artifact_fingerprint"]:
        raise ValueError("region artifact fingerprint mismatch")
    return normalized


def admit_realization(policy_raw: Any, region_raw: Any, request: Any) -> dict[str, Any]:
    policy = verify_policy(policy_raw)
    region = verify_region(policy, region_raw)
    if not isinstance(request, dict) or request.get("schema") != ADMISSION_REQUEST_SCHEMA:
        raise ValueError(f"request.schema must be {ADMISSION_REQUEST_SCHEMA}")
    if set(request) - {"schema", "region_id", "expected_version", "expected_fingerprint", "artifact_kind"}:
        raise ValueError("admission request has unsupported fields")
    if request.get("region_id") != region["region_id"]:
        raise ValueError("admission region_id mismatch")
    if request.get("expected_version") != region["version"]:
        raise ValueError("admission before-state version mismatch")
    if request.get("expected_fingerprint") != region["artifact_fingerprint"]:
        raise ValueError("admission before-state fingerprint mismatch")
    kind = nonempty(request.get("artifact_kind"), "artifact_kind")
    if kind not in ARTIFACT_DEPTH:
        raise ValueError(f"unknown planning artifact kind: {kind}")
    required_depth = ARTIFACT_DEPTH[kind]
    profile_ceiling = policy["strength_depth_ceiling"][region["commitment_strength"]]
    effective_ceiling_rank = min(DEPTH_RANK[region["max_planning_depth"]], DEPTH_RANK[profile_ceiling])
    allowed = DEPTH_RANK[required_depth] <= effective_ceiling_rank
    return {
        "schema": ADMISSION_RESULT_SCHEMA,
        "status": "allowed" if allowed else "blocked_depth_ceiling",
        "project_id": region["project_id"], "region_id": region["region_id"],
        "region_version": region["version"], "region_fingerprint": region["artifact_fingerprint"],
        "artifact_kind": kind, "required_depth": required_depth,
        "region_depth_ceiling": region["max_planning_depth"], "profile_depth_ceiling": profile_ceiling,
        "realization_write_performed": False,
        **AUTHORITY_FALSE,
    }


def transition_region(policy_raw: Any, region_raw: Any, request: Any) -> dict[str, Any]:
    policy = verify_policy(policy_raw)
    region = verify_region(policy, region_raw)
    if not isinstance(request, dict) or request.get("schema") != TRANSITION_REQUEST_SCHEMA:
        raise ValueError(f"request.schema must be {TRANSITION_REQUEST_SCHEMA}")
    allowed = {
        "schema", "region_id", "actor_class", "expected_version", "expected_fingerprint",
        "target_commitment_strength", "target_max_planning_depth", "reason", "evidence_refs",
    }
    if set(request) - allowed:
        raise ValueError("transition request has unsupported fields")
    if request.get("region_id") != region["region_id"]:
        raise ValueError("transition region_id mismatch")
    if request.get("expected_version") != region["version"]:
        raise ValueError("transition before-state version mismatch")
    if request.get("expected_fingerprint") != region["artifact_fingerprint"]:
        raise ValueError("transition before-state fingerprint mismatch")
    actor = nonempty(request.get("actor_class"), "actor_class")
    if actor not in KNOWN_ACTOR_CLASSES:
        raise ValueError(f"unknown actor_class: {actor}")
    if actor not in policy["allowed_promoter_actor_classes"]:
        raise ValueError(f"actor_class {actor} is not authorized by policy")
    strength = nonempty(request.get("target_commitment_strength"), "target_commitment_strength")
    if strength not in STRENGTHS:
        raise ValueError(f"target_commitment_strength must be one of {list(STRENGTHS)}")
    depth = nonempty(request.get("target_max_planning_depth"), "target_max_planning_depth")
    if depth not in DEPTH_RANK:
        raise ValueError(f"unknown planning depth: {depth}")
    profile_ceiling = policy["strength_depth_ceiling"][strength]
    if DEPTH_RANK[depth] > DEPTH_RANK[profile_ceiling]:
        raise ValueError(f"target depth {depth} exceeds profile ceiling {profile_ceiling} for strength {strength}")
    reason = nonempty(request.get("reason"), "reason")
    evidence_refs = string_list(request.get("evidence_refs"), "evidence_refs")
    if not evidence_refs:
        raise ValueError("transition.evidence_refs must not be empty")
    new_region = deepcopy(region)
    for key in AUTHORITY_FALSE:
        new_region.pop(key, None)
    new_region["commitment_strength"] = strength
    new_region["max_planning_depth"] = depth
    new_region["version"] = region["version"] + 1
    new_region["artifact_fingerprint"] = fp(region_payload(new_region))
    new_region.update(AUTHORITY_FALSE)
    return {
        "schema": TRANSITION_RESULT_SCHEMA, "status": "transition_proposed", "actor_class": actor,
        "reason": reason, "evidence_refs": evidence_refs,
        "before_region_fingerprint": region["artifact_fingerprint"],
        "after_region_fingerprint": new_region["artifact_fingerprint"], "new_region": new_region,
        "active_plan_write_performed": False, **AUTHORITY_FALSE,
    }


def _normalize_dependency(dep: Any, idx: int) -> dict[str, Any]:
    if not isinstance(dep, dict):
        raise ValueError(f"dependencies[{idx}] must be object")
    allowed = {
        "dependency_ref", "dependency_fingerprint", "source_ref", "dependent_ref", "dependent_fingerprint",
        "scope", "assumption_refs", "required_action", "propagation_debt_ref",
    }
    if set(dep) - allowed:
        raise ValueError(f"dependencies[{idx}] has unsupported fields")
    scope = nonempty(dep.get("scope"), f"dependencies[{idx}].scope")
    if scope not in {"all_source_changes", "assumptions"}:
        raise ValueError(f"dependencies[{idx}].scope invalid")
    assumptions = string_list(dep.get("assumption_refs"), f"dependencies[{idx}].assumption_refs")
    if scope == "assumptions" and not assumptions:
        raise ValueError(f"dependencies[{idx}] assumption scope requires assumption_refs")
    if scope == "all_source_changes" and assumptions:
        raise ValueError(f"dependencies[{idx}] all_source_changes must not declare assumption_refs")
    action = nonempty(dep.get("required_action"), f"dependencies[{idx}].required_action")
    if action != "replan":
        raise ValueError("planning horizon frontier only accepts required_action=replan")
    debt = dep.get("propagation_debt_ref")
    if debt is not None:
        debt = nonempty(debt, f"dependencies[{idx}].propagation_debt_ref")
    return {
        "dependency_ref": nonempty(dep.get("dependency_ref"), f"dependencies[{idx}].dependency_ref"),
        "dependency_fingerprint": sha(dep.get("dependency_fingerprint"), f"dependencies[{idx}].dependency_fingerprint"),
        "source_ref": nonempty(dep.get("source_ref"), f"dependencies[{idx}].source_ref"),
        "dependent_ref": nonempty(dep.get("dependent_ref"), f"dependencies[{idx}].dependent_ref"),
        "dependent_fingerprint": sha(dep.get("dependent_fingerprint"), f"dependencies[{idx}].dependent_fingerprint"),
        "scope": scope, "assumption_refs": assumptions, "required_action": action, "propagation_debt_ref": debt,
    }


def select_rebalance_frontier(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != REBALANCE_REQUEST_SCHEMA:
        raise ValueError(f"request.schema must be {REBALANCE_REQUEST_SCHEMA}")
    if set(request) - {"schema", "project_id", "source_change", "dependencies"}:
        raise ValueError("rebalance request has unsupported fields")
    project_id = nonempty(request.get("project_id"), "project_id")
    source = request.get("source_change")
    if not isinstance(source, dict):
        raise ValueError("source_change must be object")
    if set(source) - {"source_ref", "before_fingerprint", "after_fingerprint", "changed_assumption_refs", "evidence_ref", "evidence_fingerprint"}:
        raise ValueError("source_change has unsupported fields")
    source_ref = nonempty(source.get("source_ref"), "source_change.source_ref")
    before = sha(source.get("before_fingerprint"), "source_change.before_fingerprint")
    after = sha(source.get("after_fingerprint"), "source_change.after_fingerprint")
    changed_assumptions = string_list(source.get("changed_assumption_refs"), "source_change.changed_assumption_refs")
    evidence_ref = nonempty(source.get("evidence_ref"), "source_change.evidence_ref")
    evidence_fp = sha(source.get("evidence_fingerprint"), "source_change.evidence_fingerprint")
    deps_raw = request.get("dependencies")
    if not isinstance(deps_raw, list):
        raise ValueError("dependencies must be array")
    deps = [_normalize_dependency(dep, idx) for idx, dep in enumerate(deps_raw)]
    seen_dep_refs: dict[str, str] = {}
    for dep in deps:
        prior = seen_dep_refs.get(dep["dependency_ref"])
        if prior is not None and prior != dep["dependency_fingerprint"]:
            raise ValueError("same dependency_ref supplied with conflicting fingerprints")
        seen_dep_refs[dep["dependency_ref"]] = dep["dependency_fingerprint"]

    selected: dict[str, dict[str, Any]] = {}
    if before != after:
        changed = set(changed_assumptions)
        for dep in deps:
            if dep["source_ref"] != source_ref:
                continue
            matched_assumptions: list[str] = []
            if dep["scope"] == "all_source_changes":
                match = True
            else:
                matched_assumptions = sorted(changed & set(dep["assumption_refs"]))
                match = bool(matched_assumptions)
            if not match:
                continue
            target = selected.setdefault(dep["dependent_ref"], {
                "dependent_ref": dep["dependent_ref"], "dependent_fingerprint": dep["dependent_fingerprint"],
                "matched_dependency_refs": [], "matched_assumption_refs": [], "propagation_debt_refs": [],
                "required_action": "replan",
            })
            if target["dependent_fingerprint"] != dep["dependent_fingerprint"]:
                raise ValueError("matched dependencies disagree on dependent fingerprint")
            target["matched_dependency_refs"].append(dep["dependency_ref"])
            target["matched_assumption_refs"].extend(matched_assumptions)
            if dep["propagation_debt_ref"]:
                target["propagation_debt_refs"].append(dep["propagation_debt_ref"])

    targets: list[dict[str, Any]] = []
    for dependent_ref in sorted(selected):
        target = selected[dependent_ref]
        target["matched_dependency_refs"] = sorted(set(target["matched_dependency_refs"]))
        target["matched_assumption_refs"] = sorted(set(target["matched_assumption_refs"]))
        target["propagation_debt_refs"] = sorted(set(target["propagation_debt_refs"]))
        targets.append(target)
    return {
        "schema": REBALANCE_RESULT_SCHEMA,
        "status": "frontier_selected" if targets else "no_matching_dependency",
        "project_id": project_id, "source_ref": source_ref,
        "source_before_fingerprint": before, "source_after_fingerprint": after,
        "source_evidence_ref": evidence_ref, "source_evidence_fingerprint": evidence_fp,
        "changed_assumption_refs": changed_assumptions, "targets": targets, "frontier_depth": 1,
        "adjacency_used": False, "plan_reconcile_executed": False, "propagation_debt_created": False,
        "active_plan_write_performed": False, **AUTHORITY_FALSE,
    }


def self_test() -> dict[str, Any]:
    h = lambda label: "sha256:" + hashlib.sha256(label.encode()).hexdigest()
    serialized = normalize_policy({
        "schema": POLICY_SCHEMA, "profile_id": "serialized-adaptive",
        "strength_depth_ceiling": {"open": "arc_boundary", "soft": "beat", "hard": "chapter_detail"},
        "allowed_promoter_actor_classes": ["user", "authorized_human", "authorized_planner"],
    })
    soft = create_region(serialized, {
        "schema": REGION_REQUEST_SCHEMA, "project_id": "P", "region_id": "ARC-4", "plan_ref": "PLAN:ARC-4",
        "semantic_scope": "far future arc", "story_order": {"start": 40, "end": 60},
        "commitment_strength": "soft", "max_planning_depth": "beat",
        "assumption_refs": ["ASSUME-A", "ASSUME-B"], "dependency_refs": ["DEP-NONADJ"],
        "unresolved_decision_refs": ["DEC-OPAQUE"],
    })
    block = admit_realization(serialized, soft, {
        "schema": ADMISSION_REQUEST_SCHEMA, "region_id": "ARC-4", "expected_version": 1,
        "expected_fingerprint": soft["artifact_fingerprint"], "artifact_kind": "chapter_plan",
    })
    beat_ok = admit_realization(serialized, soft, {
        "schema": ADMISSION_REQUEST_SCHEMA, "region_id": "ARC-4", "expected_version": 1,
        "expected_fingerprint": soft["artifact_fingerprint"], "artifact_kind": "beat_sheet",
    })
    promoted = transition_region(serialized, soft, {
        "schema": TRANSITION_REQUEST_SCHEMA, "region_id": "ARC-4", "actor_class": "authorized_planner",
        "expected_version": 1, "expected_fingerprint": soft["artifact_fingerprint"],
        "target_commitment_strength": "hard", "target_max_planning_depth": "chapter_detail",
        "reason": "near-term outline approved for deeper planning", "evidence_refs": ["EVIDENCE:1"],
    })
    chapter_ok = admit_realization(serialized, promoted["new_region"], {
        "schema": ADMISSION_REQUEST_SCHEMA, "region_id": "ARC-4", "expected_version": 2,
        "expected_fingerprint": promoted["new_region"]["artifact_fingerprint"], "artifact_kind": "chapter_plan",
    })

    writer_blocked = stale_blocked = unknown_kind_blocked = False
    try:
        transition_region(serialized, soft, {
            "schema": TRANSITION_REQUEST_SCHEMA, "region_id": "ARC-4", "actor_class": "writer",
            "expected_version": 1, "expected_fingerprint": soft["artifact_fingerprint"],
            "target_commitment_strength": "hard", "target_max_planning_depth": "chapter_detail",
            "reason": "writer wants detail", "evidence_refs": ["EVIDENCE:BAD"],
        })
    except ValueError:
        writer_blocked = True
    try:
        transition_region(serialized, soft, {
            "schema": TRANSITION_REQUEST_SCHEMA, "region_id": "ARC-4", "actor_class": "authorized_planner",
            "expected_version": 2, "expected_fingerprint": soft["artifact_fingerprint"],
            "target_commitment_strength": "hard", "target_max_planning_depth": "chapter_detail",
            "reason": "stale", "evidence_refs": ["EVIDENCE:2"],
        })
    except ValueError:
        stale_blocked = True
    try:
        admit_realization(serialized, soft, {
            "schema": ADMISSION_REQUEST_SCHEMA, "region_id": "ARC-4", "expected_version": 1,
            "expected_fingerprint": soft["artifact_fingerprint"], "artifact_kind": "mystery_freeform_kind",
        })
    except ValueError:
        unknown_kind_blocked = True

    frontier = select_rebalance_frontier({
        "schema": REBALANCE_REQUEST_SCHEMA, "project_id": "P",
        "source_change": {
            "source_ref": "PLAN:ARC-4", "before_fingerprint": h("before"), "after_fingerprint": h("after"),
            "changed_assumption_refs": ["ASSUME-A"], "evidence_ref": "CHANGE:1", "evidence_fingerprint": h("change"),
        },
        "dependencies": [
            {"dependency_ref": "DEP-NONADJ", "dependency_fingerprint": h("dep-nonadj"),
             "source_ref": "PLAN:ARC-4", "dependent_ref": "PLAN:ARC-9", "dependent_fingerprint": h("arc9"),
             "scope": "assumptions", "assumption_refs": ["ASSUME-A"], "required_action": "replan",
             "propagation_debt_ref": "DEBT-ARC9"},
            {"dependency_ref": "DEP-UNRELATED", "dependency_fingerprint": h("dep-unrelated"),
             "source_ref": "PLAN:ARC-4", "dependent_ref": "PLAN:ARC-5", "dependent_fingerprint": h("arc5"),
             "scope": "assumptions", "assumption_refs": ["ASSUME-Z"], "required_action": "replan"},
            {"dependency_ref": "DEP-OTHER-SOURCE", "dependency_fingerprint": h("dep-other"),
             "source_ref": "PLAN:ARC-3", "dependent_ref": "PLAN:ARC-5", "dependent_fingerprint": h("arc5"),
             "scope": "all_source_changes", "assumption_refs": [], "required_action": "replan"},
        ],
    })
    selected_refs = [x["dependent_ref"] for x in frontier["targets"]]

    tight = normalize_policy({
        "schema": POLICY_SCHEMA, "profile_id": "tight-short",
        "strength_depth_ceiling": {"open": "arc_boundary", "soft": "chapter_detail", "hard": "chapter_detail"},
        "allowed_promoter_actor_classes": ["user", "authorized_planner"],
    })
    tight_soft = create_region(tight, {
        "schema": REGION_REQUEST_SCHEMA, "project_id": "P2", "region_id": "WHOLE", "plan_ref": "PLAN:WHOLE",
        "commitment_strength": "soft", "max_planning_depth": "chapter_detail",
    })
    tight_allows_detail = admit_realization(tight, tight_soft, {
        "schema": ADMISSION_REQUEST_SCHEMA, "region_id": "WHOLE", "expected_version": 1,
        "expected_fingerprint": tight_soft["artifact_fingerprint"], "artifact_kind": "chapter_plan",
    })["status"] == "allowed"

    discovery = normalize_policy({
        "schema": POLICY_SCHEMA, "profile_id": "discovery",
        "strength_depth_ceiling": {"open": "arc_boundary", "soft": "scene_intent", "hard": "chapter_detail"},
        "allowed_promoter_actor_classes": ["user", "authorized_planner"],
    })
    discovery_near = create_region(discovery, {
        "schema": REGION_REQUEST_SCHEMA, "project_id": "P3", "region_id": "NEXT", "plan_ref": "PLAN:NEXT",
        "commitment_strength": "soft", "max_planning_depth": "scene_intent",
    })

    checks = {
        "soft_beat_blocks_chapter_plan": block["status"] == "blocked_depth_ceiling",
        "soft_beat_allows_beat_sheet": beat_ok["status"] == "allowed",
        "authorized_transition_advances_exactly_once": (
            promoted["new_region"]["version"] == 2
            and promoted["before_region_fingerprint"] == soft["artifact_fingerprint"]
            and promoted["after_region_fingerprint"] == promoted["new_region"]["artifact_fingerprint"]
        ),
        "promoted_region_allows_chapter_plan": chapter_ok["status"] == "allowed",
        "writer_cannot_promote": writer_blocked,
        "stale_transition_blocked": stale_blocked,
        "unknown_artifact_kind_fails_closed": unknown_kind_blocked,
        "non_adjacent_evidence_link_selected": "PLAN:ARC-9" in selected_refs,
        "adjacent_unlinked_excluded": "PLAN:ARC-5" not in selected_refs,
        "assumption_scope_respected": frontier["targets"][0]["matched_assumption_refs"] == ["ASSUME-A"],
        "frontier_one_wave_no_auto_action": (
            frontier["frontier_depth"] == 1 and frontier["plan_reconcile_executed"] is False
            and frontier["propagation_debt_created"] is False and frontier["adjacency_used"] is False
        ),
        "tight_short_profile_can_allow_deep_soft_planning": tight_allows_detail,
        "discovery_near_future_can_remain_soft": (
            discovery_near["commitment_strength"] == "soft" and discovery_near["max_planning_depth"] == "scene_intent"
        ),
        "opaque_decision_refs_preserved_without_dependency": soft["unresolved_decision_refs"] == ["DEC-OPAQUE"],
        "authority_false_everywhere": all(
            obj.get("authority") is False and obj.get("canon_authority") is False
            and obj.get("project_write_authority") is False and obj.get("framework_write_authority") is False
            and obj.get("settlement_authority") is False and obj.get("model_execution") is False
            for obj in (serialized, soft, block, promoted, frontier, discovery_near)
        ),
    }
    return {
        "planning_horizon_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": "quillframe_planning_horizon_self_test_v1", "checks": checks,
        "artifact_depth_registry": ARTIFACT_DEPTH, "planning_depth_order": list(DEPTHS),
        "authority": False, "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("self-test")
    p = sub.add_parser("create-region"); p.add_argument("--policy", required=True); p.add_argument("--request", required=True); p.add_argument("--output")
    p = sub.add_parser("admit"); p.add_argument("--policy", required=True); p.add_argument("--region", required=True); p.add_argument("--request", required=True); p.add_argument("--output")
    p = sub.add_parser("transition"); p.add_argument("--policy", required=True); p.add_argument("--region", required=True); p.add_argument("--request", required=True); p.add_argument("--output")
    p = sub.add_parser("frontier"); p.add_argument("--request", required=True); p.add_argument("--output")
    args = parser.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["planning_horizon_contract"] == "PASS" else 1
    if args.cmd == "create-region":
        result = create_region(load(Path(args.policy)), load(Path(args.request)))
    elif args.cmd == "admit":
        result = admit_realization(load(Path(args.policy)), load(Path(args.region)), load(Path(args.request)))
    elif args.cmd == "transition":
        result = transition_region(load(Path(args.policy)), load(Path(args.region)), load(Path(args.request)))
    else:
        result = select_rebalance_frontier(load(Path(args.request)))
    dump(result, Path(args.output) if args.output else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
