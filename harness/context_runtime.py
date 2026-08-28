#!/usr/bin/env python3
"""Quillframe semantic Context Runtime.

Deterministic code owns authority/lifecycle eligibility, exact identity and
fingerprint validation, stage isolation, hard budgets, freeze reproducibility,
and public receipts. Models may derive semantic metadata and choose among an
already-eligible candidate universe, but never create authority or bypass the
freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILE_SCHEMA = "quillframe_semantic_context_profile_v1"
PROFILE_OVERRIDE_SCHEMA = "quillframe_context_profile_override_v1"
CANDIDATE_POOL_SCHEMA = "quillframe_context_candidate_pool_v1"
DECISION_SCHEMA = "quillframe_context_decision_v1"
GREENLIGHT_SCHEMA = "quillframe_context_stage_greenlight_v1"
FREEZE_SCHEMA = "quillframe_context_freeze_v1"
FREEZE_VALIDATION_SCHEMA = "quillframe_context_freeze_validation_v1"
INSPECTOR_SCHEMA = "quillframe_context_inspector_projection_v4"
QUERY_SCHEMA = "quillframe_context_query_v1"

AUTHORITIES = {
    "locked", "accepted", "active_plan", "review", "proposal",
    "runtime", "research", "corpus", "learning", "derived",
}
LIFECYCLES = {
    "locked", "accepted", "active_plan", "review", "proposal",
    "active", "derived", "rejected", "superseded", "invalidated", "stale",
}
SOURCE_TYPES = {
    "character", "relationship", "world_fact", "location", "timeline_event",
    "story_node", "plan", "research", "accepted_manuscript", "previous_scene",
    "previous_chapter", "canon_claim", "corpus_evidence", "review_artifact",
    "character_knowledge", "candidate", "runtime_state", "derived_memory",
}
STAGES = {
    "context_freeze", "story_canon_preflight", "scene_simulation",
    "character_simulation", "reader_pressure", "draft", "continuity",
    "surface_realization", "reader_engagement", "independent_review", "research",
}
SENSITIVE_WRITER_TYPES = {"hidden_gold", "regression", "expected_verdict", "answer_key"}
PRIVATE_SIMULATION_TYPES = {"private_character_state", "character_simulation_private", "scene_simulation_private", "writer_reasoning"}
WRITER_STAGES = {"draft", "surface_realization"}
PROFILE_FIELDS = {"description", "trigger_when", "estimated_tokens", "semantic_tags", "stage_affinities"}
FORBIDDEN_REASON_KEYS = {"analysis", "chain_of_thought", "reasoning", "scratchpad", "private_reasoning"}
CHARACTER_CONTEXT_FIELDS = ("identity", "agenda", "knowledge_boundary", "current_task", "location", "relationship_state", "emotional_carryover", "stakes", "misbeliefs", "scene_presence", "known_facts", "unknown_facts")

MANDATORY_PRODUCTION_MECHANISMS = (
    "context_freeze", "story_canon_preflight", "scene_simulation",
    "character_simulation", "reader_pressure", "event_first_raw_draft",
    "surface_realization", "reader_engagement", "continuity",
    "independent_semantic_gate", "user_visible_gate",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _string_list(value: Any, name: str, *, allowed: set[str] | None = None) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{name} must be a string array")
    out = list(dict.fromkeys(x.strip() for x in value))
    if allowed is not None:
        bad = [x for x in out if x not in allowed]
        if bad:
            raise ValueError(f"{name} contains unsupported values: {bad}")
    return out


def _estimated_tokens(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("estimated_tokens must be a non-negative integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("estimated_tokens must be a non-negative integer") from exc
    if number < 0:
        raise ValueError("estimated_tokens must be a non-negative integer")
    return number


def estimate_tokens(text: str) -> int:
    """Conservative provider-neutral estimate used only as a hard-budget cost hint."""
    text = str(text or "")
    if not text:
        return 0
    # Mixed CJK/Latin prose is deliberately estimated conservatively. This is a
    # packing hint, not provider billing truth.
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def profile_id_for(source_object_type: str, source_object_id: str, source_fingerprint: str) -> str:
    """Version-specific profile identity; a source mutation necessarily gets a new id."""
    seed = {"source_object_type": source_object_type, "source_object_id": source_object_id, "source_fingerprint": source_fingerprint}
    return "SCP-" + fingerprint(seed)[7:23]


def normalize_profile_override(value: dict[str, Any] | None, *, source_object_id: str | None = None) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("profile override must be an object")
    if value.get("schema") == PROFILE_OVERRIDE_SCHEMA and isinstance(value.get("fields"), dict):
        target = _nonempty(value.get("source_object_id") or source_object_id, "profile override source_object_id")
        normalized = {
            "schema": PROFILE_OVERRIDE_SCHEMA,
            "override_id": _nonempty(value.get("override_id"), "override_id"),
            "source_object_id": target,
            "fields": deepcopy(value["fields"]),
            "updated_by": _nonempty(value.get("updated_by") or "manual", "profile override updated_by"),
            "updated_at": value.get("updated_at") or now_iso(),
            "authority": False,
        }
        normalized["override_fingerprint"] = value.get("override_fingerprint") or fingerprint({"source_object_id": target, "fields": normalized["fields"], "updated_by": normalized["updated_by"]})
        return normalized
    unknown = set(value) - (PROFILE_FIELDS | {"schema", "source_object_id", "updated_at", "updated_by", "override_id"})
    if unknown:
        raise ValueError(f"unsupported profile override fields: {sorted(unknown)}")
    target = value.get("source_object_id") or source_object_id
    target = _nonempty(target, "profile override source_object_id")
    fields: dict[str, Any] = {}
    for key in PROFILE_FIELDS:
        if key not in value:
            continue
        raw = value[key]
        if key in {"description", "trigger_when"}:
            if not isinstance(raw, str):
                raise ValueError(f"override {key} must be string")
            fields[key] = raw.strip()
        elif key == "estimated_tokens":
            fields[key] = _estimated_tokens(raw)
        elif key == "semantic_tags":
            fields[key] = _string_list(raw, "override semantic_tags")
        elif key == "stage_affinities":
            fields[key] = _string_list(raw, "override stage_affinities", allowed=STAGES)
    updated_by = _nonempty(value.get("updated_by") or "manual", "profile override updated_by")
    body = {
        "schema": PROFILE_OVERRIDE_SCHEMA,
        "override_id": value.get("override_id") or ("SCPO-" + fingerprint({"source_object_id": target, "fields": fields})[7:23]),
        "source_object_id": target,
        "fields": fields,
        "updated_by": updated_by,
        "updated_at": value.get("updated_at") or now_iso(),
        "authority": False,
    }
    body["override_fingerprint"] = fingerprint({k: body[k] for k in ("source_object_id", "fields", "updated_by")})
    return body


def derive_semantic_profile(
    source: dict[str, Any],
    semantic_metadata: dict[str, Any],
    *,
    generator_provenance: dict[str, Any],
    manual_override: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Bind model-derived semantic metadata to one exact Project object fingerprint."""
    if not isinstance(source, dict) or not isinstance(semantic_metadata, dict):
        raise ValueError("source and semantic_metadata must be objects")
    source_object_id = _nonempty(source.get("object_id") or source.get("source_object_id"), "source_object_id")
    source_object_type = _nonempty(source.get("object_type") or source.get("source_object_type"), "source_object_type")
    if source_object_type not in SOURCE_TYPES:
        raise ValueError(f"unsupported source_object_type: {source_object_type}")
    source_fp = _sha(source.get("source_fingerprint"), "source_fingerprint")
    if any(key in semantic_metadata for key in ("authority", "lifecycle", "canon", "accepted", "settled")):
        raise ValueError("semantic metadata cannot create authority/lifecycle state")
    description = str(semantic_metadata.get("description") or "").strip()
    trigger_when = str(semantic_metadata.get("trigger_when") or "").strip()
    tokens = semantic_metadata.get("estimated_tokens")
    if tokens is None:
        tokens = estimate_tokens(str(source.get("model_text") or source.get("text") or description))
    tokens = _estimated_tokens(tokens)
    tags = _string_list(semantic_metadata.get("semantic_tags", []), "semantic_tags")
    affinities = _string_list(semantic_metadata.get("stage_affinities", []), "stage_affinities", allowed=STAGES)
    if not isinstance(generator_provenance, dict) or not generator_provenance:
        raise ValueError("generator_provenance must be a non-empty object")
    generated = {
        "description": description,
        "trigger_when": trigger_when,
        "estimated_tokens": tokens,
        "semantic_tags": tags,
        "stage_affinities": affinities,
    }
    override = normalize_profile_override(manual_override, source_object_id=source_object_id)
    effective = deepcopy(generated)
    if override:
        effective.update(override["fields"])
    binding = {
        "source_object_id": source_object_id,
        "source_object_type": source_object_type,
        "source_fingerprint": source_fp,
        "generated": generated,
        "effective": effective,
        "generator_provenance": generator_provenance,
        "override_fingerprint": override.get("override_fingerprint") if override else None,
    }
    body = {
        "schema": PROFILE_SCHEMA,
        "profile_id": profile_id_for(source_object_type, source_object_id, source_fp),
        "source_object_id": source_object_id,
        "source_object_type": source_object_type,
        "source_fingerprint": source_fp,
        **effective,
        "generated_metadata": generated,
        "manual_override": override,
        "generated_at": generated_at or now_iso(),
        "generator_provenance": deepcopy(generator_provenance),
        "status": "current",
        "stale_reason": None,
        "authority": False,
    }
    body["profile_fingerprint"] = fingerprint(binding)
    return body



def build_semantic_index_plan(items: list[dict[str, Any]], *, generator_id: str) -> dict[str, Any]:
    """Create model-owned profile-derivation work for missing/stale source versions."""
    generator_id = _nonempty(generator_id, "generator_id")
    jobs: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("semantic indexing item must be an object")
        object_id = _nonempty(raw.get("object_id"), "object_id")
        object_type = _nonempty(raw.get("object_type"), "object_type")
        if object_type not in SOURCE_TYPES:
            raise ValueError(f"unsupported source object type: {object_type}")
        source_fp = _sha(raw.get("source_fingerprint"), f"{object_id}.source_fingerprint")
        profile = raw.get("profile")
        current = isinstance(profile, dict) and profile.get("status") == "current" and profile.get("source_fingerprint") == source_fp
        if current and raw.get("regenerate") is not True:
            continue
        jobs.append({
            "contract_id": "context.profile_derive",
            "source": {
                "object_id": object_id,
                "object_type": object_type,
                "source_fingerprint": source_fp,
                "model_view": deepcopy(raw.get("model_view") or {}),
                "stage_hints": _string_list(raw.get("stage_hints", []), f"{object_id}.stage_hints", allowed=STAGES),
            },
            "generator_id": generator_id,
            "reason_code": "explicit_regeneration" if raw.get("regenerate") is True else ("profile_stale" if profile else "profile_missing"),
            "manual_override_present": bool(raw.get("manual_override")),
            "authority": False,
        })
    body = {"schema": "quillframe_semantic_index_plan_v1", "jobs": jobs, "authority": False}
    body["plan_fingerprint"] = fingerprint({"jobs": jobs, "generator_id": generator_id})
    return body


def project_character_context(character: dict[str, Any]) -> dict[str, Any]:
    """Project generic multi-character simulation state; never a chat persona."""
    if not isinstance(character, dict):
        raise ValueError("character projection input must be an object")
    character_id = _nonempty(character.get("character_id") or character.get("object_id"), "character_id")
    fields = {name: deepcopy(character.get(name)) for name in CHARACTER_CONTEXT_FIELDS}
    return {
        "schema": "quillframe_character_context_projection_v1",
        "character_id": character_id,
        **fields,
        "persona_substitute": False,
        "authority": False,
    }


def profile_status(profile: dict[str, Any], current_source_fingerprint: str) -> dict[str, Any]:
    out = deepcopy(profile)
    current = _sha(current_source_fingerprint, "current_source_fingerprint")
    if profile.get("source_fingerprint") != current:
        out["status"] = "stale"
        out["stale_reason"] = "source_fingerprint_changed"
    else:
        out["status"] = "current"
        out["stale_reason"] = None
    return out


def _exclusion(code: str, detail: str, *, category: str) -> dict[str, str]:
    return {"code": code, "detail": detail, "category": category}


def _pinned_stages(item: dict[str, Any]) -> list[str]:
    if not item.get("pinned"):
        return []
    return _string_list(item.get("pinned_stages", item.get("stages", sorted(STAGES))), "pinned_stages", allowed=STAGES)


def evaluate_eligibility(item: dict[str, Any], stage_id: str) -> tuple[bool, dict[str, str] | None, dict[str, Any]]:
    """Mechanical gate. This function intentionally has no relevance score."""
    if stage_id not in STAGES:
        raise ValueError(f"unsupported stage_id: {stage_id}")
    if not isinstance(item, dict):
        raise ValueError("context source item must be an object")
    object_id = _nonempty(item.get("object_id") or item.get("id"), "object_id")
    object_type = _nonempty(item.get("object_type") or item.get("source_object_type") or item.get("class") or "runtime_state", "object_type")
    authority = item.get("authority", "derived")
    if authority not in AUTHORITIES:
        raise ValueError(f"invalid authority for {object_id}: {authority}")
    lifecycle = item.get("lifecycle") or authority
    if lifecycle not in LIFECYCLES:
        raise ValueError(f"invalid lifecycle for {object_id}: {lifecycle}")
    source_fp = _sha(item.get("source_fingerprint"), f"{object_id}.source_fingerprint")
    profile = item.get("profile")
    normalized = {
        **deepcopy(item),
        "object_id": object_id,
        "object_type": object_type,
        "authority": authority,
        "lifecycle": lifecycle,
        "source_fingerprint": source_fp,
    }
    if item.get("hidden") is True:
        return False, _exclusion("visibility_hidden", "source is hidden for this runtime view", category="visibility_excluded"), normalized
    if item.get("invalidated") is True or lifecycle == "invalidated":
        return False, _exclusion("source_invalidated", "source was invalidated before selection", category="lifecycle_excluded"), normalized
    if lifecycle in {"rejected", "superseded"} or item.get("status") in {"rejected", "superseded"}:
        return False, _exclusion("lifecycle_ineligible", f"{lifecycle} sources cannot enter active context", category="lifecycle_excluded"), normalized
    allowed_stages = _string_list(item.get("stages", list(STAGES)), f"{object_id}.stages", allowed=STAGES)
    if stage_id not in allowed_stages:
        return False, _exclusion("stage_ineligible", f"source is not eligible for stage {stage_id}", category="visibility_excluded"), normalized
    if object_type in SENSITIVE_WRITER_TYPES and stage_id in WRITER_STAGES:
        return False, _exclusion("writer_sensitive_excluded", "hidden/regression material cannot enter writer context", category="visibility_excluded"), normalized
    if object_type in PRIVATE_SIMULATION_TYPES and stage_id in WRITER_STAGES:
        return False, _exclusion("private_simulation_excluded", "private simulation state cannot enter writer context", category="visibility_excluded"), normalized
    domain = str(item.get("domain") or object_type)
    if stage_id == "character_simulation" and domain in {"research", "research_evidence"} and object_type != "character_knowledge":
        return False, _exclusion("research_not_character_knowledge", "research evidence is not Character Knowledge", category="lifecycle_excluded"), normalized
    if object_type == "accepted_manuscript" and authority not in {"accepted", "locked"}:
        return False, _exclusion("accepted_type_without_authority", "accepted manuscript context requires accepted/locked authority", category="lifecycle_excluded"), normalized
    if profile is None:
        return False, _exclusion("semantic_profile_missing", "eligible source has no semantic profile", category="stale"), normalized
    if not isinstance(profile, dict):
        raise ValueError(f"{object_id}.profile must be object")
    if profile.get("source_object_id") != object_id:
        return False, _exclusion("profile_source_mismatch", "semantic profile is bound to a different source object", category="invalid"), normalized
    if profile.get("source_fingerprint") != source_fp:
        return False, _exclusion("profile_stale", "semantic profile source fingerprint is stale", category="stale"), normalized
    if profile.get("status") != "current":
        return False, _exclusion("profile_stale", str(profile.get("stale_reason") or "semantic profile is stale"), category="stale"), normalized
    affinity = profile.get("stage_affinities") or []
    if affinity and stage_id not in affinity:
        # Affinity is metadata, not eligibility. Do not exclude: semantic decision may
        # still select it. Preserve this fact for the model packet.
        normalized["profile_stage_affinity_match"] = False
    else:
        normalized["profile_stage_affinity_match"] = True
    return True, None, normalized


def build_candidate_pool(*, run_id: str, stage_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    _nonempty(run_id, "run_id")
    if not isinstance(items, list):
        raise ValueError("items must be an array")
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in items:
        ok, reason, item = evaluate_eligibility(raw, stage_id)
        object_id = item["object_id"]
        if object_id in seen:
            raise ValueError(f"duplicate object_id: {object_id}")
        seen.add(object_id)
        profile = item.get("profile") or {}
        record = {
            "object_id": object_id,
            "object_type": item["object_type"],
            "domain": str(item.get("domain") or item["object_type"]),
            "authority": item["authority"],
            "lifecycle": item["lifecycle"],
            "source_fingerprint": item["source_fingerprint"],
            "profile_id": profile.get("profile_id"),
            "profile_fingerprint": profile.get("profile_fingerprint"),
            "estimated_tokens": int(profile.get("estimated_tokens") or 0),
            "description": profile.get("description") or "",
            "trigger_when": profile.get("trigger_when") or "",
            "semantic_tags": profile.get("semantic_tags") or [],
            "stage_affinities": profile.get("stage_affinities") or [],
            "profile_stage_affinity_match": item.get("profile_stage_affinity_match"),
            "required_for_grounding": bool(item.get("required_for_grounding", False)),
            "pinned": bool(item.get("pinned", False)),
            "pinned_stages": _pinned_stages(item),
            "stages": _string_list(item.get("stages", sorted(STAGES)), f"{object_id}.stages", allowed=STAGES),
        }
        if ok:
            eligible.append(record)
        else:
            excluded.append({**record, "exclusion": reason})
    eligible.sort(key=lambda x: x["object_id"])
    excluded.sort(key=lambda x: x["object_id"])
    universe_binding = {
        "run_id": run_id,
        "stage_id": stage_id,
        "eligible": [
            {k: row[k] for k in ("object_id", "profile_id", "source_fingerprint", "profile_fingerprint", "authority", "lifecycle", "pinned", "pinned_stages", "required_for_grounding")}
            for row in eligible
        ],
    }
    return {
        "schema": CANDIDATE_POOL_SCHEMA,
        "run_id": run_id,
        "stage_id": stage_id,
        "eligible": eligible,
        "excluded": excluded,
        "candidate_count": len(eligible),
        "candidate_universe_fingerprint": fingerprint(universe_binding),
        "semantic_relevance_judged_by_runtime": False,
        "authority": False,
    }


def _short_reason(selection: dict[str, Any]) -> tuple[str, str]:
    forbidden = FORBIDDEN_REASON_KEYS.intersection(selection)
    if forbidden:
        raise ValueError(f"private reasoning fields are forbidden: {sorted(forbidden)}")
    code = str(selection.get("reason_code") or "semantic_relevance").strip()
    reason = str(selection.get("reason") or "selected for bounded stage relevance").strip()
    if not code or len(code) > 64:
        raise ValueError("reason_code must be 1..64 characters")
    if not reason or len(reason) > 240:
        raise ValueError("reason must be 1..240 characters")
    return code, reason


def validate_context_decision(pool: dict[str, Any], decision: dict[str, Any], *, selector: dict[str, Any]) -> dict[str, Any]:
    if pool.get("schema") != CANDIDATE_POOL_SCHEMA:
        raise ValueError("candidate pool schema mismatch")
    if not isinstance(decision, dict):
        raise ValueError("decision must be an object")
    if decision.get("authority") not in {None, False}:
        raise ValueError("context decision cannot grant authority")
    selections = decision.get("selections", [])
    if not isinstance(selections, list):
        raise ValueError("decision.selections must be an array")
    eligible_by_profile = {row["profile_id"]: row for row in pool["eligible"] if row.get("profile_id")}
    selected: list[dict[str, Any]] = []
    # Pinned inputs belong to the task binding, not to the model's selections.
    # A pin never overrides lifecycle, visibility, knowledge, or profile checks.
    errors: list[dict[str, Any]] = [
        {"object_id": row["object_id"], "profile_id": row.get("profile_id"),
         "code": "required_input_ineligible", "exclusion": deepcopy(row["exclusion"])}
        for row in pool.get("excluded", [])
        if pool["stage_id"] in row.get("pinned_stages", [])
    ]
    pinned_inputs = [
        {**deepcopy(row), "stage_id": pool["stage_id"], "required_for_grounding": True,
         "inclusion_source": "task_binding", "reason_code": "task_bound_input",
         "reason": "Required by the exact task binding; not a semantic selection."}
        for row in pool["eligible"] if pool["stage_id"] in row.get("pinned_stages", [])
    ]
    seen: set[str] = set()
    for index, raw in enumerate(selections):
        if not isinstance(raw, dict):
            errors.append({"index": index, "code": "invalid_selection_shape"}); continue
        profile_id = str(raw.get("profile_id") or "").strip()
        stage_id = str(raw.get("stage_id") or pool["stage_id"]).strip()
        row = eligible_by_profile.get(profile_id)
        if not profile_id or row is None:
            errors.append({"index": index, "profile_id": profile_id, "code": "profile_outside_candidate_universe"}); continue
        if stage_id != pool["stage_id"]:
            errors.append({"index": index, "profile_id": profile_id, "code": "stage_mismatch"}); continue
        if profile_id in seen:
            errors.append({"index": index, "profile_id": profile_id, "code": "duplicate_profile_id"}); continue
        try:
            reason_code, reason = _short_reason(raw)
        except ValueError as exc:
            errors.append({"index": index, "profile_id": profile_id, "code": "invalid_reason", "detail": str(exc)}); continue
        priority = raw.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, (int, float)):
            errors.append({"index": index, "profile_id": profile_id, "code": "invalid_priority"}); continue
        seen.add(profile_id)
        selected.append({
            **row,
            "stage_id": stage_id,
            "priority": float(priority),
            "reason_code": reason_code,
            "reason": reason,
            "required_for_grounding": bool(row.get("required_for_grounding") or raw.get("required_for_grounding")),
            "selection_index": index,
        })
    status = ("required_context_unavailable" if any(error["code"] == "required_input_ineligible" for error in errors)
              else "semantic_invalid" if errors else "validated")
    body = {
        "schema": DECISION_SCHEMA,
        "run_id": pool["run_id"],
        "stage_id": pool["stage_id"],
        "candidate_universe_fingerprint": pool["candidate_universe_fingerprint"],
        "selector": deepcopy(selector),
        "selected": selected if not errors else [],
        "pinned_inputs": pinned_inputs if not errors else [],
        "candidate_count": pool["candidate_count"],
        "errors": errors,
        "status": status,
        "proceed": not errors,
        "authority": False,
    }
    body["decision_fingerprint"] = fingerprint({k: body[k] for k in body if k != "errors"} | {"errors": errors})
    return body


def pack_budget(validated: dict[str, Any], *, hard_budget: int, actual_tokens: dict[str, int] | None = None) -> dict[str, Any]:
    if validated.get("status") != "validated":
        raise ValueError("only a validated context decision can be budget-packed")
    if isinstance(hard_budget, bool) or not isinstance(hard_budget, int) or hard_budget < 0:
        raise ValueError("hard_budget must be a non-negative integer")
    actual_tokens = actual_tokens or {}
    pinned = sorted(validated.get("pinned_inputs", []), key=lambda row: (row["object_id"], row["profile_id"]))
    selected_by_profile = {row["profile_id"]: row for row in validated["selected"]}
    pinned_ids = {row["profile_id"] for row in pinned}
    candidates = [
        {**selected_by_profile.get(row["profile_id"], row), "required_for_grounding": True,
         "inclusion_source": "task_binding"}
        for row in pinned
    ]
    candidates.extend(
        {**row, "inclusion_source": "semantic_selection"}
        for row in sorted(validated["selected"], key=lambda x: (-x["priority"], x["selection_index"], x["profile_id"]))
        if row["profile_id"] not in pinned_ids
    )
    loaded: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    used = 0
    required_dropped = False
    for row in candidates:
        estimate = int(row.get("estimated_tokens") or 0)
        if used + estimate > hard_budget:
            dropped.append({**row, "drop_reason": "hard_budget"})
            required_dropped = required_dropped or bool(row.get("required_for_grounding"))
            continue
        used += estimate
        actual = actual_tokens.get(row["profile_id"])
        loaded.append({**row, "actual_tokens": int(actual) if actual is not None else None})
    status = "grounding_incomplete_due_budget" if required_dropped else "packed"
    body = {
        "schema": GREENLIGHT_SCHEMA,
        "run_id": validated["run_id"],
        "stage_id": validated["stage_id"],
        "candidate_universe_fingerprint": validated["candidate_universe_fingerprint"],
        "selector": deepcopy(validated["selector"]),
        "candidate_count": validated.get("candidate_count", len(candidates)),
        "selected_count": len(validated["selected"]),
        "selected_object_ids": [row["object_id"] for row in validated["selected"]],
        "selected_profile_ids": [row["profile_id"] for row in validated["selected"]],
        "pinned_inputs": deepcopy(pinned),
        "pinned_object_ids": [row["object_id"] for row in pinned],
        "pinned_profile_ids": [row["profile_id"] for row in pinned],
        "loaded_object_ids": [row["object_id"] for row in loaded],
        "loaded_profile_ids": [row["profile_id"] for row in loaded],
        "selected": loaded,
        "dropped_due_budget": dropped,
        "estimated_tokens": used,
        "actual_tokens": sum(int(row["actual_tokens"] or 0) for row in loaded) if any(row["actual_tokens"] is not None for row in loaded) else None,
        "hard_budget": hard_budget,
        "grounding_incomplete_due_budget": required_dropped,
        "status": status,
        "authority_classes": sorted({row["authority"] for row in loaded}),
        "source_fingerprints": {row["object_id"]: row["source_fingerprint"] for row in loaded},
        "authority": False,
    }
    body["selection_fingerprint"] = fingerprint({k: body[k] for k in body if k not in {"actual_tokens"}})
    return body


def freeze_context(*, run_id: str, task_mode: str, pools: list[dict[str, Any]], greenlights: list[dict[str, Any]], created_at: str | None = None) -> dict[str, Any]:
    _nonempty(run_id, "run_id"); _nonempty(task_mode, "task_mode")
    by_stage_pool = {p["stage_id"]: p for p in pools}
    by_stage_greenlight = {g["stage_id"]: g for g in greenlights}
    if set(by_stage_greenlight) - set(by_stage_pool):
        raise ValueError("greenlight stage has no frozen candidate pool")
    for stage, greenlight in by_stage_greenlight.items():
        if greenlight.get("candidate_universe_fingerprint") != by_stage_pool[stage].get("candidate_universe_fingerprint"):
            raise ValueError(f"greenlight candidate universe mismatch for {stage}")
        if greenlight.get("status") != "packed" or greenlight.get("grounding_incomplete_due_budget"):
            raise ValueError(f"stage context is not complete within its hard budget: {stage}")
    source_fps: dict[str, str] = {}
    source_state_fps: dict[str, str] = {}
    profile_fps: dict[str, str] = {}
    profiles: dict[str, dict[str, Any]] = {}
    for pool in pools:
        for row in pool.get("eligible", []) + pool.get("excluded", []):
            object_id = row["object_id"]
            source_fps[object_id] = row["source_fingerprint"]
            source_state_fp = fingerprint({
                "source_fingerprint": row["source_fingerprint"],
                "authority": row.get("authority"),
                "lifecycle": row.get("lifecycle"),
                "domain": row.get("domain"),
                "pinned": bool(row.get("pinned")),
                "pinned_stages": _pinned_stages(row),
                "required_for_grounding": bool(row.get("required_for_grounding")),
            })
            # Visibility exclusions belong to a stage's candidate universe.
            # The same source may be allowed for an editor and hidden from a
            # Blind Reader without its global authority/lifecycle changing.
            if object_id in source_state_fps and source_state_fps[object_id] != source_state_fp:
                raise ValueError(f"source state differs between frozen stages: {object_id}")
            source_state_fps[object_id] = source_state_fp
            if row.get("profile_id") and row.get("profile_fingerprint"):
                profile_fps[row["profile_id"]] = row["profile_fingerprint"]
                profiles[row["profile_id"]] = {
                    "profile_id": row["profile_id"], "object_id": object_id,
                    "object_type": row["object_type"], "domain": row["domain"],
                    "authority": row["authority"], "lifecycle": row["lifecycle"],
                    "source_fingerprint": row["source_fingerprint"],
                    "profile_fingerprint": row["profile_fingerprint"],
                    "estimated_tokens": row.get("estimated_tokens", 0),
                    "description": row.get("description", ""), "trigger_when": row.get("trigger_when", ""),
                }
    binding = {
        "run_id": run_id,
        "task_mode": task_mode,
        "candidate_universes": {stage: p["candidate_universe_fingerprint"] for stage, p in sorted(by_stage_pool.items())},
        "stage_selections": {stage: g["selection_fingerprint"] for stage, g in sorted(by_stage_greenlight.items())},
        "source_fingerprints": dict(sorted(source_fps.items())),
        "source_state_fingerprints": dict(sorted(source_state_fps.items())),
        "profile_fingerprints": dict(sorted(profile_fps.items())),
    }
    freeze_fp = fingerprint(binding)
    return {
        "schema": FREEZE_SCHEMA,
        "freeze_id": "CTXF-" + freeze_fp[7:23],
        "run_id": run_id,
        "task_mode": task_mode,
        "candidate_universes": {stage: p["candidate_universe_fingerprint"] for stage, p in sorted(by_stage_pool.items())},
        "stage_greenlights": {stage: deepcopy(g) for stage, g in sorted(by_stage_greenlight.items())},
        "source_fingerprints": dict(sorted(source_fps.items())),
        "source_state_fingerprints": dict(sorted(source_state_fps.items())),
        "profile_fingerprints": dict(sorted(profile_fps.items())),
        "profiles": profiles,
        "created_at": created_at or now_iso(),
        "freeze_fingerprint": freeze_fp,
        "status": "frozen",
        "tracked_db_fetch_after_freeze_allowed": False,
        "extension_requires_new_fingerprint": True,
        "authority": False,
    }


def validate_freeze(freeze: dict[str, Any], current_source_fingerprints: dict[str, str], current_source_states: dict[str, dict[str, Any] | str] | None = None) -> dict[str, Any]:
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise ValueError("freeze schema mismatch")
    changed: list[dict[str, str | None]] = []
    for object_id, expected in freeze.get("source_fingerprints", {}).items():
        actual = current_source_fingerprints.get(object_id)
        if actual != expected:
            changed.append({"object_id": object_id, "expected": expected, "actual": actual})
    if current_source_states is not None:
        for object_id, expected_state_fp in freeze.get("source_state_fingerprints", {}).items():
            state = current_source_states.get(object_id)
            if isinstance(state, str):
                actual_state_fp = state
            elif isinstance(state, dict):
                actual_state_fp = fingerprint({
                    "source_fingerprint": state.get("source_fingerprint"),
                    "authority": state.get("authority"),
                    "lifecycle": state.get("lifecycle"),
                    "domain": state.get("domain"),
                    "pinned": bool(state.get("pinned")),
                    "pinned_stages": _pinned_stages(state),
                    "required_for_grounding": bool(state.get("required_for_grounding")),
                })
            else:
                actual_state_fp = None
            if actual_state_fp != expected_state_fp:
                changed.append({"object_id": object_id, "expected_state": expected_state_fp, "actual_state": actual_state_fp})
    status = "current" if not changed else "stale_conflict"
    return {
        "schema": FREEZE_VALIDATION_SCHEMA,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_fingerprint": freeze.get("freeze_fingerprint"),
        "status": status,
        "proceed": not changed,
        "changed_sources": changed,
        "refresh_required": bool(changed),
        "new_context_fingerprint_required": bool(changed),
        "authority": False,
    }


def stage_context(freeze: dict[str, Any], stage_id: str) -> dict[str, Any]:
    """Return only the frozen stage payload. This function performs no DB read."""
    if freeze.get("schema") != FREEZE_SCHEMA or freeze.get("status") != "frozen":
        raise ValueError("valid frozen context required")
    greenlight = freeze.get("stage_greenlights", {}).get(stage_id)
    if greenlight is None:
        raise KeyError(f"stage was not greenlit in this freeze: {stage_id}")
    selected = []
    for profile_id in greenlight.get("loaded_profile_ids", greenlight.get("selected_profile_ids", [])):
        profile = freeze.get("profiles", {}).get(profile_id)
        if not profile:
            raise ValueError(f"frozen profile missing: {profile_id}")
        selected.append(deepcopy(profile))
    return {
        "schema": "quillframe_frozen_stage_context_v1",
        "freeze_id": freeze["freeze_id"],
        "freeze_fingerprint": freeze["freeze_fingerprint"],
        "stage_id": stage_id,
        "selected": selected,
        "selection_fingerprint": greenlight["selection_fingerprint"],
        "db_fetch_performed": False,
        "authority": False,
    }


def build_inspector_projection(*, run_id: str, pools: list[dict[str, Any]], greenlights: list[dict[str, Any]], freeze: dict[str, Any] | None = None) -> dict[str, Any]:
    green_by_stage = {g["stage_id"]: g for g in greenlights}
    items: list[dict[str, Any]] = []
    for pool in pools:
        stage = pool["stage_id"]
        green = green_by_stage.get(stage)
        selected_ids = set(green.get("selected_profile_ids", [])) if green else set()
        dropped_ids = {row["profile_id"] for row in green.get("dropped_due_budget", [])} if green else set()
        loaded_ids = set(green.get("loaded_profile_ids", [])) if green else set()
        for row in pool.get("eligible", []):
            pid = row.get("profile_id")
            state = "loaded" if pid in loaded_ids else ("dropped_due_budget" if pid in dropped_ids else ("selected" if pid in selected_ids else "considered"))
            items.append({
                "source_object_id": row["object_id"], "profile_id": pid, "domain": row["domain"],
                "authority": row["authority"], "lifecycle": row["lifecycle"], "stage": stage,
                "state": state,
                "reason_code": ("hard_budget" if pid in dropped_ids else next((x.get("reason_code") for x in (green or {}).get("selected", []) if x.get("profile_id") == pid), "eligible_not_selected")),
                "reason": ("context input dropped by hard token budget" if pid in dropped_ids else next((x.get("reason") for x in (green or {}).get("selected", []) if x.get("profile_id") == pid), "mechanically eligible; semantic selector did not load it")),
                "inclusion_source": next((x.get("inclusion_source") for x in (green or {}).get("selected", []) + (green or {}).get("dropped_due_budget", []) if x.get("profile_id") == pid), None),
                "estimated_tokens": row.get("estimated_tokens", 0),
                "actual_tokens": next((x.get("actual_tokens") for x in (green or {}).get("selected", []) if x.get("profile_id") == pid), None),
                "source_fingerprint": row.get("source_fingerprint"), "profile_fingerprint": row.get("profile_fingerprint"),
                "selector": deepcopy((green or {}).get("selector")),
                "receipt": (green or {}).get("selection_fingerprint"),
            })
        for row in pool.get("excluded", []):
            exclusion = row.get("exclusion") or {}
            state = exclusion.get("category") or "invalid"
            items.append({
                "source_object_id": row["object_id"], "profile_id": row.get("profile_id"), "domain": row["domain"],
                "authority": row["authority"], "lifecycle": row["lifecycle"], "stage": stage,
                "state": state, "reason_code": exclusion.get("code"), "reason": exclusion.get("detail"),
                "estimated_tokens": row.get("estimated_tokens", 0), "actual_tokens": None,
                "source_fingerprint": row.get("source_fingerprint"), "profile_fingerprint": row.get("profile_fingerprint"),
                "selector": None, "receipt": pool.get("candidate_universe_fingerprint"),
            })
    items.sort(key=lambda x: (x["stage"], x["state"], x["source_object_id"]))
    return {
        "schema": INSPECTOR_SCHEMA,
        "run_id": run_id,
        "context_freeze_id": freeze.get("freeze_id") if freeze else None,
        "context_fingerprint": freeze.get("freeze_fingerprint") if freeze else None,
        "states": ["eligible", "considered", "selected", "loaded", "dropped_due_budget", "visibility_excluded", "lifecycle_excluded", "stale", "invalid"],
        "items": items,
        "private_chain_of_thought_exposed": False,
        "authority": False,
    }


def validate_context_query(query: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(query, dict):
        raise ValueError("context query must be an object")
    if any(key.lower() in {"sql", "statement", "query_sql", "database_path"} for key in query):
        raise ValueError("physical SQL/schema access is forbidden in Context Query")
    domain = _nonempty(query.get("domain"), "domain")
    filters = query.get("filters", {})
    projection = _string_list(query.get("projection", []), "projection")
    authority_requirement = query.get("authority_requirement")
    if authority_requirement is not None and authority_requirement not in AUTHORITIES:
        raise ValueError("invalid authority_requirement")
    if not isinstance(filters, dict):
        raise ValueError("filters must be object")
    limit = query.get("limit", 50)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("limit must be 1..500")
    body = {
        "schema": QUERY_SCHEMA, "domain": domain, "filters": deepcopy(filters),
        "projection": projection, "limit": limit, "authority_requirement": authority_requirement,
        "physical_schema_independent": True, "authority": False,
    }
    body["query_fingerprint"] = fingerprint({k: body[k] for k in body if k != "authority"})
    return body


def validate_adaptive_graph(plan: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(plan, list):
        raise ValueError("adaptive plan must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for raw in plan:
        if not isinstance(raw, dict):
            raise ValueError("adaptive plan item must be object")
        mechanism = _nonempty(raw.get("mechanism"), "mechanism")
        if mechanism in by_id:
            raise ValueError(f"duplicate mechanism: {mechanism}")
        by_id[mechanism] = raw
    missing = [m for m in MANDATORY_PRODUCTION_MECHANISMS if m not in by_id]
    disabled = [m for m in MANDATORY_PRODUCTION_MECHANISMS if m in by_id and by_id[m].get("run") is False]
    status = "valid" if not missing and not disabled else "invalid_mandatory_graph"
    return {
        "schema": "quillframe_adaptive_graph_validation_v1",
        "status": status, "proceed": status == "valid", "missing_mandatory": missing,
        "disabled_mandatory": disabled, "adaptive_mechanisms_allowed": True,
        "agent_invents_mandatory_graph": False, "authority": False,
    }


def extend_freeze(freeze: dict[str, Any], *, pools: list[dict[str, Any]], greenlights: list[dict[str, Any]], reason_code: str) -> dict[str, Any]:
    _nonempty(reason_code, "reason_code")
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise ValueError("freeze schema mismatch")
    new = freeze_context(run_id=freeze["run_id"], task_mode=freeze["task_mode"], pools=pools, greenlights=greenlights)
    new["supersedes_freeze_id"] = freeze["freeze_id"]
    new["extension_reason_code"] = reason_code
    if new["freeze_fingerprint"] == freeze["freeze_fingerprint"]:
        new["refresh_changed_context"] = False
    else:
        new["refresh_changed_context"] = True
    return new


def self_test() -> dict[str, Any]:
    src_fp = fingerprint("accepted char")
    profile = derive_semantic_profile(
        {"object_id": "CHAR-1", "object_type": "character", "source_fingerprint": src_fp, "text": "A careful negotiator."},
        {"description": "Negotiator", "trigger_when": "When CHAR-1 acts", "estimated_tokens": 12, "semantic_tags": ["character"], "stage_affinities": ["character_simulation", "draft"]},
        generator_provenance={"kind": "semantic_job", "job_fingerprint": fingerprint("profile-job")},
        generated_at="2026-08-18T00:00:00+00:00",
    )
    item = {"object_id": "CHAR-1", "object_type": "character", "authority": "accepted", "lifecycle": "accepted", "domain": "character", "source_fingerprint": src_fp, "stages": ["character_simulation", "draft"], "profile": profile}
    pool = build_candidate_pool(run_id="RUN-SELF", stage_id="draft", items=[item])
    decision = validate_context_decision(pool, {"selections": [{"profile_id": profile["profile_id"], "stage_id": "draft", "priority": 1, "reason_code": "active_character", "reason": "active scene participant"}]}, selector={"kind": "agent", "id": "self-test"})
    green = pack_budget(decision, hard_budget=100)
    frozen_a = freeze_context(run_id="RUN-SELF", task_mode="DRAFT", pools=[pool], greenlights=[green], created_at="A")
    frozen_b = freeze_context(run_id="RUN-SELF", task_mode="DRAFT", pools=[pool], greenlights=[green], created_at="B")
    ok = all([
        profile["authority"] is False,
        pool["candidate_count"] == 1,
        decision["proceed"],
        green["status"] == "packed",
        frozen_a["freeze_fingerprint"] == frozen_b["freeze_fingerprint"],
        stage_context(frozen_a, "draft")["db_fetch_performed"] is False,
        build_inspector_projection(run_id="RUN-SELF", pools=[pool], greenlights=[green], freeze=frozen_a)["private_chain_of_thought_exposed"] is False,
    ])
    return {"schema": "quillframe_context_runtime_self_test_v1", "context_runtime_contract": "PASS" if ok else "FAIL", "authority": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe semantic Context Runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    validate_q = sub.add_parser("validate-query"); validate_q.add_argument("--input", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        out = self_test()
    else:
        out = validate_context_query(json.loads(Path(args.input).read_text(encoding="utf-8")))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("context_runtime_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
