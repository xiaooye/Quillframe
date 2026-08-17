#!/usr/bin/env python3
"""NovelForge Author Model evidence persistence and selective projection.

This module is the deterministic capture/projection layer over LearningStore.
Models own feedback meaning, scope, applicability and hypothesis relation.
Deterministic code owns stable evidence identity, exact hypothesis targets,
version/CAS, authority and selective projection.

Automatic feedback intake is deliberately candidate-first: capture authority is
not activation authority. Current explicit instructions are applied by the
production manager immediately and outrank old learned preferences; this module
only governs durable learning state.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from learning_store import LearningStore
from promotion_gate import SCHEMA as PROMOTION_CANDIDATE_SCHEMA
from promotion_gate import _semantic_binding as _promotion_semantic_binding
from promotion_gate import evaluate as evaluate_promotion_candidate

SCHEMA = "novelforge_author_model_v1"
CAPTURE_SCHEMA = "novelforge_feedback_capture_v1"
PROJECTION_SCHEMA = "novelforge_author_model_projection_v2"
SCOPES = {"one_off", "project", "user_taste", "general_craft"}
POLARITIES = {"positive", "negative", "mixed"}
HYPOTHESIS_ACTIONS = {"create", "strengthen", "contest", "supersede", "split"}
SOURCE_MAP = {
    "explicit_rule": "explicit_rule",
    "user_edit": "user_edit",
    "rejection": "rejection",
    "acceptance": "acceptance",               # legacy capture input
    "reasoned_acceptance": "acceptance",      # v2 semantic contract
    "comparison": "human_review",
    "correction": "human_review",
    "repeated_pattern": "repeated_pattern",
    "human_review": "human_review",
}


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _optional_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, name)


def _string_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be array")
    out = [_nonempty(x, name) for x in value]
    if len(out) != len(set(out)):
        raise ValueError(f"{name} must be unique")
    return out


def _confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be number")
    out = float(value)
    if not 0 <= out <= 1:
        raise ValueError("confidence must be 0..1")
    return out


def normalize_interpretation(value: Any) -> dict[str, Any]:
    """Normalize a semantic *capture* judgment.

    `capture_decision=skip` is consumed by feedback_intake and never reaches the
    Author Model. Legacy callers that omit capture_decision remain valid.
    """
    if not isinstance(value, dict):
        raise ValueError("interpretation must be object")
    decision = value.get("capture_decision", "capture")
    if decision != "capture":
        raise ValueError("Author Model capture requires capture_decision=capture")
    scope = value.get("scope_candidate")
    if scope not in SCOPES:
        raise ValueError("invalid scope_candidate")
    polarity = value.get("polarity", "mixed")
    if polarity not in POLARITIES:
        raise ValueError("invalid polarity")
    source = value.get("evidence_source", "human_review")
    if source not in SOURCE_MAP:
        raise ValueError("invalid evidence_source")
    action = value.get("hypothesis_action", "create")
    if action not in HYPOTHESIS_ACTIONS:
        raise ValueError("invalid hypothesis_action")
    target = _optional_string(value.get("target_hypothesis_id"), "target_hypothesis_id")
    if action == "create" and target is not None:
        raise ValueError("create action must not specify target_hypothesis_id")
    if action != "create" and target is None:
        raise ValueError(f"{action} action requires target_hypothesis_id")
    applicability = value.get("applicability", {})
    if not isinstance(applicability, dict):
        raise ValueError("applicability must be object")
    return {
        "scope_candidate": scope,
        "dimension": _nonempty(value.get("dimension"), "dimension"),
        "mechanism": _nonempty(value.get("mechanism"), "mechanism"),
        "statement": _nonempty(value.get("statement"), "statement"),
        "observed_problem": value.get("observed_problem"),
        "polarity": polarity,
        "confidence": _confidence(value.get("confidence")),
        "evidence_source": source,
        "desired_behavior": _string_list(value.get("desired_behavior", []), "desired_behavior"),
        "avoid_behavior": _string_list(value.get("avoid_behavior", []), "avoid_behavior"),
        "exceptions": _string_list(value.get("exceptions", []), "exceptions"),
        "applicability": applicability,
        "hypothesis_action": action,
        "target_hypothesis_id": target,
        "contradicts_hypothesis_ids": _string_list(value.get("contradicts_hypothesis_ids", []), "contradicts_hypothesis_ids"),
    }


def _row_to_hypothesis(row: Any) -> dict[str, Any]:
    return {
        "hypothesis_id": row["hypothesis_id"],
        "subject_scope": row["subject_scope"],
        "project_id": row["project_id"],
        "dimension": row["dimension"],
        "statement": row["statement"],
        "mechanism": row["mechanism"],
        "state": row["state"],
        "confidence": row["confidence"],
        "positive_weight": row["positive_weight"],
        "negative_weight": row["negative_weight"],
        "evidence_ids": json.loads(row["evidence_ids_json"]),
        "contradiction_ids": json.loads(row["contradiction_ids_json"]),
        "applicability": json.loads(row["applicability_json"]),
        "version": row["version"],
    }


def _load_hypothesis(store: LearningStore, hypothesis_id: str) -> dict[str, Any] | None:
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM preference_hypotheses WHERE hypothesis_id=?", (hypothesis_id,)).fetchone()
    return None if row is None else _row_to_hypothesis(row)


def _hypotheses_for_evidence(store: LearningStore, evidence_id: str) -> list[dict[str, Any]]:
    """Find already-applied logical effects for crash recovery.

    This is used only after LearningStore reports that the deterministic evidence
    row already exists. It prevents a retry after a crash between Author Model
    persistence and feedback-intake receipt completion from creating another
    hypothesis or double-counting the same evidence.
    """
    out: list[dict[str, Any]] = []
    with store.connect() as conn:
        rows = conn.execute("SELECT * FROM preference_hypotheses ORDER BY hypothesis_id").fetchall()
    for row in rows:
        item = _row_to_hypothesis(row)
        if evidence_id in item["evidence_ids"] or evidence_id in item["contradiction_ids"]:
            out.append(item)
    return out


def hypothesis_index(store: LearningStore, *, project_id: str | None, limit: int = 64) -> list[dict[str, Any]]:
    """Compact reconciliation index; no prose/history/user biography is exposed."""
    limit = max(1, min(int(limit), 64))
    with store.connect() as conn:
        rows = conn.execute(
            """SELECT hypothesis_id,subject_scope,project_id,dimension,mechanism,state,applicability_json,version
               FROM preference_hypotheses
               WHERE subject_scope IN ('one_off','project','user_taste')
               ORDER BY updated_at DESC,hypothesis_id ASC LIMIT ?""",
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        if row["subject_scope"] == "project" and row["project_id"] != project_id:
            continue
        out.append({
            "hypothesis_id": row["hypothesis_id"],
            "scope": row["subject_scope"],
            "project_id": row["project_id"],
            "dimension": row["dimension"],
            "mechanism": row["mechanism"],
            "state": row["state"],
            "applicability": json.loads(row["applicability_json"]),
            "version": row["version"],
        })
    return out


def _assert_target_compatible(target: dict[str, Any], *, project_id: str | None, action: str, scope: str) -> None:
    if target["subject_scope"] == "project" and target["project_id"] != project_id:
        raise ValueError("target hypothesis belongs to another Project")
    if action == "strengthen" and target["subject_scope"] != scope:
        raise ValueError("strengthen requires identical hypothesis scope")
    if action == "strengthen" and target["project_id"] != project_id:
        raise ValueError("strengthen requires identical Project binding")
    if target["subject_scope"] == "general_craft":
        raise ValueError("production feedback intake cannot mutate General Craft hypotheses")


def _weights(polarity: str) -> tuple[float, float]:
    return (
        1.0 if polarity in {"positive", "mixed"} else 0.0,
        1.0 if polarity in {"negative", "mixed"} else 0.0,
    )


def _updated_existing(
    store: LearningStore,
    target: dict[str, Any],
    *,
    evidence_id: str,
    interpretation: dict[str, Any],
    state: str | None = None,
    contradiction: bool = False,
) -> dict[str, Any]:
    fresh_evidence = evidence_id not in target["evidence_ids"]
    pos, neg = _weights(interpretation["polarity"])
    if not fresh_evidence:
        pos = neg = 0.0
    evidence_ids = list(dict.fromkeys([*target["evidence_ids"], evidence_id]))
    contradiction_ids = list(target["contradiction_ids"])
    if contradiction:
        contradiction_ids = list(dict.fromkeys([*contradiction_ids, evidence_id]))
    applicability = dict(target["applicability"])
    if interpretation["applicability"]:
        applicability = dict(interpretation["applicability"])
    applicability["desired_behavior"] = interpretation["desired_behavior"]
    applicability["avoid_behavior"] = interpretation["avoid_behavior"]
    applicability["exceptions"] = interpretation["exceptions"]
    desired_state = state or target["state"]
    desired_dimension = interpretation["dimension"] if interpretation["hypothesis_action"] == "strengthen" else target["dimension"]
    desired_statement = interpretation["statement"] if interpretation["hypothesis_action"] == "strengthen" else target["statement"]
    desired_mechanism = interpretation["mechanism"] if interpretation["hypothesis_action"] == "strengthen" else target["mechanism"]
    desired_confidence = interpretation["confidence"] if interpretation["hypothesis_action"] == "strengthen" else target["confidence"]
    # Exact logical retry after the mutation has already landed is a no-op.
    if (
        not fresh_evidence
        and (not contradiction or evidence_id in target["contradiction_ids"])
        and target["state"] == desired_state
        and target["dimension"] == desired_dimension
        and target["statement"] == desired_statement
        and target["mechanism"] == desired_mechanism
        and target["confidence"] == desired_confidence
        and target["applicability"] == applicability
    ):
        return target | {"duplicate_logical_effect": True}
    return store.upsert_hypothesis({
        "hypothesis_id": target["hypothesis_id"],
        "subject_scope": target["subject_scope"],
        "project_id": target["project_id"],
        "dimension": desired_dimension,
        "statement": desired_statement,
        "mechanism": desired_mechanism,
        "state": desired_state,
        "confidence": desired_confidence,
        "positive_weight": target["positive_weight"] + pos,
        "negative_weight": target["negative_weight"] + neg,
        "evidence_ids": evidence_ids,
        "contradiction_ids": contradiction_ids,
        "applicability": applicability,
    }, expected_version=target["version"])


def _user_taste_prerequisite(activation: dict[str, Any], interpretation: dict[str, Any]) -> dict[str, Any]:
    candidate = activation.get("user_taste_promotion_candidate")
    if candidate is None:
        return {"provided": False, "status": "missing", "ready": False, "blockers": ["durable user_taste activation requires promotion-gate prerequisite evidence"]}
    if not isinstance(candidate, dict):
        raise ValueError("activation.user_taste_promotion_candidate must be object")
    report = evaluate_promotion_candidate(candidate)
    blockers = list(report.get("blockers") or [])
    if candidate.get("schema") != PROMOTION_CANDIDATE_SCHEMA:
        blockers.append("promotion candidate schema mismatch")
    if report.get("scope") != "user_taste":
        blockers.append("promotion candidate scope must be user_taste")
    if report.get("mechanism") != interpretation["mechanism"]:
        blockers.append("promotion candidate mechanism must match interpreted mechanism")
    ready = report.get("status") == "ready_for_activation" and not blockers
    return {
        "provided": True, "status": report.get("status"), "ready": ready,
        "candidate_id": report.get("candidate_id"), "blockers": blockers,
        "semantic_evidence_count_threshold_used": report.get("semantic_evidence_count_threshold_used"),
        "behavior_write_authority": False, "durable_user_taste_write_authority": False,
    }


def _new_state(scope: str, project_write: bool, taste_write: bool, taste_prerequisite: dict[str, Any]) -> str:
    if scope == "project" and project_write:
        return "active"
    if scope == "user_taste" and taste_write and taste_prerequisite.get("ready"):
        return "active"
    return "candidate"


def _create_hypothesis(store: LearningStore, *, interpretation: dict[str, Any], project_id: str | None, evidence_id: str, state: str) -> dict[str, Any]:
    pos, neg = _weights(interpretation["polarity"])
    applicability = dict(interpretation["applicability"])
    applicability["desired_behavior"] = interpretation["desired_behavior"]
    applicability["avoid_behavior"] = interpretation["avoid_behavior"]
    applicability["exceptions"] = interpretation["exceptions"]
    return store.upsert_hypothesis({
        "subject_scope": interpretation["scope_candidate"], "project_id": project_id,
        "dimension": interpretation["dimension"], "statement": interpretation["statement"],
        "mechanism": interpretation["mechanism"], "state": state, "confidence": interpretation["confidence"],
        "positive_weight": pos, "negative_weight": neg, "evidence_ids": [evidence_id],
        "contradiction_ids": [], "applicability": applicability,
    }, expected_version=0)


def _recover_duplicate_effect(
    store: LearningStore,
    *,
    evidence_id: str,
    interpretation: dict[str, Any],
    project_id: str | None,
    target: dict[str, Any] | None,
    state: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Recover a prior/partially-completed logical capture after evidence retry."""
    action = interpretation["hypothesis_action"]
    matches = _hypotheses_for_evidence(store, evidence_id)
    affected: list[str] = []
    if action == "create":
        candidates = [x for x in matches if x["subject_scope"] == interpretation["scope_candidate"] and x["project_id"] == project_id and x["mechanism"] == interpretation["mechanism"]]
        if len(candidates) > 1:
            raise ValueError("duplicate evidence maps to multiple create hypotheses")
        return (candidates[0] if candidates else None), affected
    if target is None:
        return None, affected
    current_target = _load_hypothesis(store, target["hypothesis_id"])
    assert current_target is not None
    if action == "strengthen" and evidence_id in current_target["evidence_ids"]:
        return current_target, affected
    if action == "contest" and evidence_id in current_target["contradiction_ids"] and current_target["state"] == "contested":
        return current_target, [current_target["hypothesis_id"]]
    if action in {"supersede", "split"}:
        replacements = [x for x in matches if x["hypothesis_id"] != current_target["hypothesis_id"] and x["subject_scope"] == interpretation["scope_candidate"] and x["project_id"] == project_id and x["mechanism"] == interpretation["mechanism"]]
        if len(replacements) > 1:
            raise ValueError("duplicate evidence maps to multiple replacement hypotheses")
        if replacements:
            desired_old_state = "superseded" if action == "supersede" else "contested"
            _updated_existing(store, current_target, evidence_id=evidence_id, interpretation=interpretation, state=desired_old_state, contradiction=True)
            affected.append(current_target["hypothesis_id"])
            return replacements[0], affected
    return None, affected


def capture_feedback(store: LearningStore, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("capture request must be object")
    if request.get("schema") not in {None, CAPTURE_SCHEMA}:
        raise ValueError("invalid capture schema")
    interpretation = normalize_interpretation(request.get("interpretation"))
    project_id = request.get("project_id")
    if project_id is not None:
        project_id = _nonempty(project_id, "project_id")
    scope = interpretation["scope_candidate"]
    if scope == "project" and not project_id:
        raise ValueError("project scope requires project_id")

    activation = request.get("activation", {})
    if not isinstance(activation, dict):
        raise ValueError("activation must be object")
    project_write = activation.get("project_preference_write_authorized", False)
    taste_write = activation.get("durable_user_taste_write_authorized", False)
    if not isinstance(project_write, bool) or not isinstance(taste_write, bool):
        raise ValueError("activation flags must be boolean")
    taste_prerequisite = {"provided": False, "status": "not_applicable", "ready": False, "blockers": []}
    if scope == "user_taste" and taste_write:
        taste_prerequisite = _user_taste_prerequisite(activation, interpretation)

    source_ref = _nonempty(request.get("feedback_ref"), "feedback_ref")
    evidence_id = request.get("evidence_id")
    if evidence_id is not None:
        evidence_id = _nonempty(evidence_id, "evidence_id")
    evidence_payload = {
        "evidence_id": evidence_id, "subject_scope": scope, "project_id": project_id,
        "source": SOURCE_MAP[interpretation["evidence_source"]], "semantic_evidence_source": interpretation["evidence_source"],
        "polarity": interpretation["polarity"], "observed_problem": interpretation["observed_problem"],
        "mechanism": interpretation["mechanism"], "user_words_or_reference": source_ref,
        "artifact_ref": request.get("artifact_ref"), "artifact_fingerprint": request.get("artifact_fingerprint"),
        "artifact_disposition": "rejected_negative_only" if interpretation["evidence_source"] == "rejection" else "evidence_only",
        "confidence": interpretation["confidence"], "desired_behavior": interpretation["desired_behavior"],
        "avoid_behavior": interpretation["avoid_behavior"], "exceptions": interpretation["exceptions"],
        "feedback_event_ref": request.get("feedback_event_ref"),
    }
    if evidence_id is None:
        evidence_payload.pop("evidence_id")
    evidence = store.add_evidence(evidence_payload)
    evidence_id = evidence["evidence_id"]

    action = interpretation["hypothesis_action"]
    target_id = interpretation["target_hypothesis_id"]
    target = _load_hypothesis(store, target_id) if target_id else None
    if target_id and target is None:
        raise ValueError(f"unknown target hypothesis: {target_id}")
    if target:
        _assert_target_compatible(target, project_id=project_id, action=action, scope=scope)

    state = _new_state(scope, project_write, taste_write, taste_prerequisite)
    recovered: dict[str, Any] | None = None
    affected: list[str] = []
    if evidence.get("duplicate"):
        recovered, affected = _recover_duplicate_effect(store, evidence_id=evidence_id, interpretation=interpretation, project_id=project_id, target=target, state=state)

    if recovered is not None:
        hypothesis = recovered
    elif action == "create":
        hypothesis = _create_hypothesis(store, interpretation=interpretation, project_id=project_id, evidence_id=evidence_id, state=state)
    elif action == "strengthen":
        assert target is not None
        hypothesis = _updated_existing(store, target, evidence_id=evidence_id, interpretation=interpretation)
    elif action == "contest":
        assert target is not None
        hypothesis = _updated_existing(store, target, evidence_id=evidence_id, interpretation=interpretation, state="contested", contradiction=True)
        affected.append(target["hypothesis_id"])
    elif action == "supersede":
        assert target is not None
        hypothesis = _create_hypothesis(store, interpretation=interpretation, project_id=project_id, evidence_id=evidence_id, state=state)
        old = _load_hypothesis(store, target["hypothesis_id"]); assert old is not None
        _updated_existing(store, old, evidence_id=evidence_id, interpretation=interpretation, state="superseded", contradiction=True)
        affected.append(target["hypothesis_id"])
    elif action == "split":
        assert target is not None
        hypothesis = _create_hypothesis(store, interpretation=interpretation, project_id=project_id, evidence_id=evidence_id, state=state)
        old = _load_hypothesis(store, target["hypothesis_id"]); assert old is not None
        _updated_existing(store, old, evidence_id=evidence_id, interpretation=interpretation, state="contested", contradiction=True)
        affected.append(target["hypothesis_id"])
    else:  # pragma: no cover
        raise ValueError("unsupported hypothesis action")

    for old_id in interpretation["contradicts_hypothesis_ids"]:
        if old_id == hypothesis["hypothesis_id"] or old_id in affected:
            continue
        old = _load_hypothesis(store, old_id)
        if old is None:
            raise ValueError(f"unknown contradicted hypothesis: {old_id}")
        _assert_target_compatible(old, project_id=project_id, action="contest", scope=scope)
        if not (evidence_id in old["contradiction_ids"] and old["state"] == "contested"):
            _updated_existing(store, old, evidence_id=evidence_id, interpretation=interpretation, state="contested", contradiction=True)
        affected.append(old_id)

    final = _load_hypothesis(store, hypothesis["hypothesis_id"]); assert final is not None
    return {
        "schema": CAPTURE_SCHEMA, "evidence_id": evidence_id, "evidence_duplicate": evidence.get("duplicate", False),
        "hypothesis_id": final["hypothesis_id"], "hypothesis_action": action, "target_hypothesis_id": target_id,
        "scope": final["subject_scope"], "hypothesis_state": final["state"], "hypothesis_version": final["version"],
        "evidence_ids": final["evidence_ids"], "active_for_future_production": final["state"] == "active" and final["subject_scope"] in {"project", "user_taste"},
        "user_taste_activation_prerequisite": taste_prerequisite, "affected_hypothesis_ids": affected,
        "crash_retry_recovered": recovered is not None,
        "general_craft_auto_promoted": False, "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "project_profile_write": False}, "model_execution": False,
    }


def _projection_row(row: Any) -> dict[str, Any]:
    return {
        "hypothesis_id": row["hypothesis_id"], "scope": row["subject_scope"], "project_id": row["project_id"],
        "dimension": row["dimension"], "statement": row["statement"], "mechanism": row["mechanism"],
        "confidence": row["confidence"], "applicability": json.loads(row["applicability_json"]),
        "evidence_ids": json.loads(row["evidence_ids_json"]), "version": row["version"],
    }


def project_author_model(store: LearningStore, *, project_id: str | None, explicit_intent: list[dict[str, Any]] | None = None, selected_hypothesis_ids: list[str] | None = None) -> dict[str, Any]:
    """Project only manager/model-selected active hypotheses into working context."""
    explicit_intent = explicit_intent or []
    if not isinstance(explicit_intent, list) or any(not isinstance(x, dict) for x in explicit_intent):
        raise ValueError("explicit_intent must be object array")
    selected = _string_list(selected_hypothesis_ids or [], "selected_hypothesis_ids")
    with store.connect() as conn:
        rows = conn.execute("SELECT * FROM preference_hypotheses WHERE state='active' AND subject_scope IN ('project','user_taste') ORDER BY updated_at ASC,hypothesis_id ASC").fetchall()
    eligible = []
    for row in rows:
        if row["subject_scope"] == "project" and row["project_id"] != project_id:
            continue
        eligible.append(row)
    by_id = {row["hypothesis_id"]: row for row in eligible}
    unknown = [hypothesis_id for hypothesis_id in selected if hypothesis_id not in by_id]
    if unknown:
        raise ValueError("selected hypothesis is not active/eligible for this Project: " + ", ".join(unknown))
    index = [{
        "hypothesis_id": row["hypothesis_id"], "scope": row["subject_scope"], "project_id": row["project_id"],
        "dimension": row["dimension"], "mechanism": row["mechanism"], "applicability": json.loads(row["applicability_json"]), "version": row["version"],
    } for row in eligible]
    projected = [_projection_row(by_id[hypothesis_id]) for hypothesis_id in selected]
    return {
        "schema": PROJECTION_SCHEMA, "project_id": project_id,
        "priority_order": ["current_explicit_request", "selected_project_active", "selected_user_taste_active"],
        "explicit_intent": explicit_intent, "available_active_hypothesis_ids": [row["hypothesis_id"] for row in eligible],
        "active_preference_index": index, "selected_hypothesis_ids": selected, "active_preferences": projected,
        "all_active_preferences_auto_included": False, "semantic_relevance_judged_by_runtime": False,
        "candidate_hypotheses_included": False, "one_off_history_included": False, "general_craft_candidates_included": False,
        "authority": False, "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False}, "model_execution": False,
    }


def self_test(path: Path | None = None) -> dict[str, Any]:
    db = path or Path(tempfile.gettempdir()) / "novelforge-author-model-selftest.db"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        if p.exists(): p.unlink()
    store = LearningStore(db); store.init()
    base = {
        "schema": CAPTURE_SCHEMA, "project_id": "P1", "artifact_ref": "draft:1", "artifact_fingerprint": "sha256:" + "a" * 64,
        "activation": {"project_preference_write_authorized": False, "durable_user_taste_write_authorized": False},
    }
    create_request = {**base, "feedback_ref": "review:1", "evidence_id": "PE-STABLE-1", "interpretation": {
        "scope_candidate": "project", "dimension": "dialogue", "mechanism": "relationship-shaped dialogue", "statement": "Dialogue should carry relationship asymmetry.",
        "polarity": "negative", "confidence": 0.9, "evidence_source": "human_review", "hypothesis_action": "create",
    }}
    create = capture_feedback(store, create_request)
    crash_retry = capture_feedback(store, create_request)
    distinct = capture_feedback(store, {**base, "feedback_ref": "review:2", "evidence_id": "PE-STABLE-2", "interpretation": {
        "scope_candidate": "project", "dimension": "dialogue", "mechanism": "relationship-shaped dialogue", "statement": "Dialogue should carry relationship asymmetry.",
        "polarity": "negative", "confidence": 0.95, "evidence_source": "comparison", "hypothesis_action": "strengthen", "target_hypothesis_id": create["hypothesis_id"],
    }})
    merged = _load_hypothesis(store, create["hypothesis_id"]); assert merged is not None
    contest = capture_feedback(store, {**base, "feedback_ref": "review:3", "evidence_id": "PE-STABLE-3", "interpretation": {
        "scope_candidate": "project", "dimension": "dialogue", "mechanism": "opening dialogue compression",
        "statement": "In openings, charm and conflict may outrank detailed professional explanation.", "polarity": "negative", "confidence": 0.9,
        "evidence_source": "correction", "hypothesis_action": "contest", "target_hypothesis_id": create["hypothesis_id"], "applicability": {"scene_types": ["opening"]},
    }})

    manual_active = capture_feedback(store, {**base, "feedback_ref": "rule:active", "evidence_id": "PE-ACTIVE", "activation": {"project_preference_write_authorized": True, "durable_user_taste_write_authorized": False}, "interpretation": {
        "scope_candidate": "project", "dimension": "paragraph_rhythm", "mechanism": "functional paragraphing", "statement": "Prefer functional paragraphs.",
        "polarity": "positive", "confidence": 1.0, "evidence_source": "explicit_rule", "hypothesis_action": "create",
    }})
    projection = project_author_model(store, project_id="P1", explicit_intent=[{"statement":"Current request wins."}])
    selected = project_author_model(store, project_id="P1", selected_hypothesis_ids=[manual_active["hypothesis_id"]])

    user_candidate = capture_feedback(store, {**base, "feedback_ref": "review:user", "evidence_id": "PE-USER", "interpretation": {
        "scope_candidate": "user_taste", "dimension": "language", "mechanism": "avoid heavy code-switching", "statement": "Prefer less code-switching in Chinese fiction.",
        "polarity": "negative", "confidence": 0.9, "evidence_source": "explicit_rule", "hypothesis_action": "create",
    }})
    general_candidate = capture_feedback(store, {**base, "feedback_ref": "review:gc", "evidence_id": "PE-GC", "interpretation": {
        "scope_candidate": "general_craft", "dimension": "detail", "mechanism": "professional detail compression", "statement": "Claimed universal rule remains a candidate only.",
        "polarity": "negative", "confidence": 0.8, "evidence_source": "human_review", "hypothesis_action": "create",
    }})

    user_write_only = capture_feedback(store, {**base, "feedback_ref": "review:user-write-only", "evidence_id": "PE-USER-WRITE-ONLY", "activation": {
        "project_preference_write_authorized": False, "durable_user_taste_write_authorized": True,
    }, "interpretation": {
        "scope_candidate": "user_taste", "dimension": "language", "mechanism": "avoid dense code switching",
        "statement": "Prefer less dense code switching.", "polarity": "negative", "confidence": 0.9,
        "evidence_source": "explicit_rule", "hypothesis_action": "create",
    }})

    promotion_refs = ["review:gate", "EVAL:gate"]
    candidate = {"schema": PROMOTION_CANDIDATE_SCHEMA, "candidate_id": "UT-GOOD", "scope": "user_taste", "mechanism": "low narrator commentary", "evidence": {"evidence_refs": promotion_refs}}
    candidate["semantic_review_binding"] = _promotion_semantic_binding("UT-GOOD", "user_taste", "low narrator commentary", promotion_refs)
    gated = capture_feedback(store, {**base, "feedback_ref": "review:gate", "evidence_id": "PE-GATE", "activation": {
        "project_preference_write_authorized": False, "durable_user_taste_write_authorized": True, "user_taste_promotion_candidate": candidate,
    }, "interpretation": {
        "scope_candidate": "user_taste", "dimension": "narration", "mechanism": "low narrator commentary", "statement": "Prefer lower narrator commentary.",
        "polarity": "negative", "confidence": 0.9, "evidence_source": "explicit_rule", "hypothesis_action": "create",
    }})

    crash_idempotent = crash_retry["crash_retry_recovered"] is True and crash_retry["hypothesis_id"] == create["hypothesis_id"] and crash_retry["hypothesis_version"] == create["hypothesis_version"]
    two_turns_one_hypothesis = len(merged["evidence_ids"]) == 2 and distinct["hypothesis_id"] == create["hypothesis_id"]
    contradiction_first_class = contest["hypothesis_state"] == "contested"
    explicit_priority = projection["priority_order"][0] == "current_explicit_request" and projection["active_preferences"] == []
    active_selective = selected["selected_hypothesis_ids"] == [manual_active["hypothesis_id"]] and len(selected["active_preferences"]) == 1
    authority_safe = user_candidate["hypothesis_state"] == "candidate" and general_candidate["hypothesis_state"] == "candidate" and not general_candidate["general_craft_auto_promoted"]
    write_authority_alone_not_enough = user_write_only["hypothesis_state"] == "candidate" and user_write_only["user_taste_activation_prerequisite"]["ready"] is False
    gated_user_taste = gated["hypothesis_state"] == "active" and gated["user_taste_activation_prerequisite"]["ready"] is True
    ok = all([crash_idempotent, two_turns_one_hypothesis, contradiction_first_class, explicit_priority, active_selective, authority_safe, write_authority_alone_not_enough, gated_user_taste])
    result = {
        "schema": SCHEMA, "author_model_contract": "PASS" if ok else "FAIL",
        "stable_event_evidence_idempotent": crash_idempotent,
        "crash_between_capture_and_receipt_recovers_without_duplicate_hypothesis": crash_idempotent,
        "distinct_turns_can_strengthen_one_hypothesis": two_turns_one_hypothesis,
        "contradiction_is_first_class": contradiction_first_class,
        "current_explicit_request_priority": explicit_priority,
        "active_preferences_require_explicit_selection": active_selective,
        "automatic_candidate_does_not_activate_user_taste_or_general_craft": authority_safe,
        "user_taste_write_authority_alone_not_enough": write_authority_alone_not_enough,
        "user_taste_requires_promotion_prerequisite_and_write_authority": gated_user_taste,
        "all_active_preferences_auto_included": False, "semantic_relevance_judged_by_runtime": False,
        "authority": False, "model_execution": False,
    }
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        if p.exists(): p.unlink()
    return result


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Author Model and review feedback capture")
    p.add_argument("--db", default=".novelforge/learning.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture"); c.add_argument("--request", required=True)
    r = sub.add_parser("project"); r.add_argument("--project-id"); r.add_argument("--explicit-intent"); r.add_argument("--selected-hypothesis-ids")
    s = sub.add_parser("self-test"); s.add_argument("--path")
    a = p.parse_args()
    if a.cmd == "self-test":
        out = self_test(Path(a.path) if a.path else None)
    else:
        store = LearningStore(a.db); store.init()
        if a.cmd == "capture": out = capture_feedback(store, _load(a.request))
        else:
            explicit = _load(a.explicit_intent) if a.explicit_intent else []
            selected_ids = _load(a.selected_hypothesis_ids) if a.selected_hypothesis_ids else []
            out = project_author_model(store, project_id=a.project_id, explicit_intent=explicit, selected_hypothesis_ids=selected_ids)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("author_model_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
