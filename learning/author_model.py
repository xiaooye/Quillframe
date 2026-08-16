#!/usr/bin/env python3
"""NovelForge Author Model evidence persistence and selective projection.

This module reuses LearningStore rather than creating a second preference
system. Models interpret review feedback; deterministic code validates scope and
write authority, persists evidence, applies CAS-backed hypothesis updates, and
exposes an active-preference index. A manager/model must explicitly select which
active hypotheses enter a production context; active does not mean universally
relevant.

It never grants Canon, Framework, Project-profile, or durable user-taste write
authority by itself. Durable user-taste activation requires BOTH an explicit
write-authority signal and a current passing promotion prerequisite whose
semantic evidence review is bound to the same candidate.
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
SOURCE_MAP = {
    "explicit_rule": "explicit_rule",
    "user_edit": "user_edit",
    "rejection": "rejection",
    "acceptance": "acceptance",
    "repeated_pattern": "repeated_pattern",
    "human_review": "human_review",
}


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


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
    if not isinstance(value, dict):
        raise ValueError("interpretation must be object")
    scope = value.get("scope_candidate")
    if scope not in SCOPES:
        raise ValueError("invalid scope_candidate")
    polarity = value.get("polarity", "mixed")
    if polarity not in POLARITIES:
        raise ValueError("invalid polarity")
    source = value.get("evidence_source", "human_review")
    if source not in SOURCE_MAP:
        raise ValueError("invalid evidence_source")
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
        "applicability": value.get("applicability", {}) if isinstance(value.get("applicability", {}), dict) else {},
        "contradicts_hypothesis_ids": _string_list(value.get("contradicts_hypothesis_ids", []), "contradicts_hypothesis_ids"),
    }


def _load_hypothesis(store: LearningStore, hypothesis_id: str) -> dict[str, Any] | None:
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM preference_hypotheses WHERE hypothesis_id=?", (hypothesis_id,)).fetchone()
    if row is None:
        return None
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


def _supersede(store: LearningStore, old_id: str, *, contradiction_ref: str) -> dict[str, Any]:
    old = _load_hypothesis(store, old_id)
    if old is None:
        raise ValueError(f"unknown contradicted hypothesis: {old_id}")
    contradiction_ids = list(dict.fromkeys([*old["contradiction_ids"], contradiction_ref]))
    return store.upsert_hypothesis({
        "hypothesis_id": old_id,
        "subject_scope": old["subject_scope"],
        "project_id": old["project_id"],
        "dimension": old["dimension"],
        "statement": old["statement"],
        "mechanism": old["mechanism"],
        "state": "superseded",
        "confidence": old["confidence"],
        "positive_weight": old["positive_weight"],
        "negative_weight": old["negative_weight"],
        "evidence_ids": old["evidence_ids"],
        "contradiction_ids": contradiction_ids,
        "applicability": old["applicability"],
    }, expected_version=old["version"])


def _user_taste_prerequisite(activation: dict[str, Any], interpretation: dict[str, Any]) -> dict[str, Any]:
    candidate = activation.get("user_taste_promotion_candidate")
    if candidate is None:
        return {
            "provided": False,
            "status": "missing",
            "ready": False,
            "blockers": ["durable user_taste activation requires promotion-gate prerequisite evidence"],
        }
    if not isinstance(candidate, dict):
        raise ValueError("activation.user_taste_promotion_candidate must be object")
    schema_mismatch = candidate.get("schema") != PROMOTION_CANDIDATE_SCHEMA
    report = evaluate_promotion_candidate(candidate)
    binding_blockers: list[str] = []
    if schema_mismatch:
        binding_blockers.append("promotion candidate schema mismatch")
    if report.get("scope") != "user_taste":
        binding_blockers.append("promotion candidate scope must be user_taste")
    if report.get("mechanism") != interpretation["mechanism"]:
        binding_blockers.append("promotion candidate mechanism must match interpreted mechanism")
    blockers = list(report.get("blockers") or []) + binding_blockers
    ready = report.get("status") == "ready_for_activation" and not blockers
    return {
        "provided": True,
        "status": report.get("status"),
        "ready": ready,
        "candidate_id": report.get("candidate_id"),
        "blockers": blockers,
        "semantic_evidence_count_threshold_used": report.get("semantic_evidence_count_threshold_used"),
        "behavior_write_authority": False,
        "durable_user_taste_write_authority": False,
    }


def capture_feedback(store: LearningStore, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("capture request must be object")
    if request.get("schema") not in {None, CAPTURE_SCHEMA}:
        raise ValueError("invalid capture schema")
    interpretation = normalize_interpretation(request.get("interpretation"))
    project_id = request.get("project_id")
    if project_id is not None:
        project_id = _nonempty(project_id, "project_id")
    if interpretation["scope_candidate"] == "project" and not project_id:
        raise ValueError("project scope requires project_id")

    activation = request.get("activation", {})
    if not isinstance(activation, dict):
        raise ValueError("activation must be object")
    project_write = activation.get("project_preference_write_authorized", False)
    taste_write = activation.get("durable_user_taste_write_authorized", False)
    if not isinstance(project_write, bool) or not isinstance(taste_write, bool):
        raise ValueError("activation flags must be boolean")

    taste_prerequisite = {
        "provided": False,
        "status": "not_applicable",
        "ready": False,
        "blockers": [],
    }
    if interpretation["scope_candidate"] == "user_taste" and taste_write:
        taste_prerequisite = _user_taste_prerequisite(activation, interpretation)

    source_ref = _nonempty(request.get("feedback_ref"), "feedback_ref")
    evidence_payload = {
        "subject_scope": interpretation["scope_candidate"],
        "project_id": project_id,
        "source": SOURCE_MAP[interpretation["evidence_source"]],
        "polarity": interpretation["polarity"],
        "observed_problem": interpretation["observed_problem"],
        "mechanism": interpretation["mechanism"],
        "user_words_or_reference": source_ref,
        "artifact_ref": request.get("artifact_ref"),
        "artifact_fingerprint": request.get("artifact_fingerprint"),
        "confidence": interpretation["confidence"],
        "desired_behavior": interpretation["desired_behavior"],
        "avoid_behavior": interpretation["avoid_behavior"],
        "exceptions": interpretation["exceptions"],
    }
    evidence = store.add_evidence(evidence_payload)

    scope = interpretation["scope_candidate"]
    state = "candidate"
    if scope == "project" and project_write:
        state = "active"
    elif scope == "user_taste" and taste_write and taste_prerequisite["ready"]:
        state = "active"
    # one_off is deliberately not durable production behavior; general_craft
    # never becomes active through this production-side capture path.

    applicability = dict(interpretation["applicability"])
    applicability["desired_behavior"] = interpretation["desired_behavior"]
    applicability["avoid_behavior"] = interpretation["avoid_behavior"]
    applicability["exceptions"] = interpretation["exceptions"]
    hypothesis = store.upsert_hypothesis({
        "subject_scope": scope,
        "project_id": project_id,
        "dimension": interpretation["dimension"],
        "statement": interpretation["statement"],
        "mechanism": interpretation["mechanism"],
        "state": state,
        "confidence": interpretation["confidence"],
        "positive_weight": 1.0 if interpretation["polarity"] in {"positive", "mixed"} else 0.0,
        "negative_weight": 1.0 if interpretation["polarity"] in {"negative", "mixed"} else 0.0,
        "evidence_ids": [evidence["evidence_id"]],
        "contradiction_ids": [],
        "applicability": applicability,
    }, expected_version=0)

    superseded = []
    for old_id in interpretation["contradicts_hypothesis_ids"]:
        if old_id == hypothesis["hypothesis_id"]:
            raise ValueError("new hypothesis cannot contradict itself")
        superseded.append(_supersede(store, old_id, contradiction_ref=evidence["evidence_id"]))

    return {
        "schema": CAPTURE_SCHEMA,
        "evidence_id": evidence["evidence_id"],
        "hypothesis_id": hypothesis["hypothesis_id"],
        "scope": scope,
        "hypothesis_state": state,
        "active_for_future_production": state == "active" and scope in {"project", "user_taste"},
        "user_taste_activation_prerequisite": taste_prerequisite,
        "superseded_hypothesis_ids": [x["hypothesis_id"] for x in superseded],
        "general_craft_auto_promoted": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False},
        "model_execution": False,
    }


def _projection_row(row: Any) -> dict[str, Any]:
    return {
        "hypothesis_id": row["hypothesis_id"],
        "scope": row["subject_scope"],
        "project_id": row["project_id"],
        "dimension": row["dimension"],
        "statement": row["statement"],
        "mechanism": row["mechanism"],
        "confidence": row["confidence"],
        "applicability": json.loads(row["applicability_json"]),
        "evidence_ids": json.loads(row["evidence_ids_json"]),
        "version": row["version"],
    }


def project_author_model(
    store: LearningStore,
    *,
    project_id: str | None,
    explicit_intent: list[dict[str, Any]] | None = None,
    selected_hypothesis_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Project only manager/model-selected active hypotheses into working context.

    `active` is durable eligibility, not semantic relevance. The runtime exposes
    a compact index and exact IDs; the semantic caller chooses which active
    hypotheses are useful for the current task. Deterministic code then verifies
    the selected IDs are active and Project-compatible before exposing details.
    """
    explicit_intent = explicit_intent or []
    if not isinstance(explicit_intent, list) or any(not isinstance(x, dict) for x in explicit_intent):
        raise ValueError("explicit_intent must be object array")
    selected = _string_list(selected_hypothesis_ids or [], "selected_hypothesis_ids")

    with store.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM preference_hypotheses WHERE state='active' AND subject_scope IN ('project','user_taste') ORDER BY updated_at ASC, hypothesis_id ASC"
        ).fetchall()
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
        "hypothesis_id": row["hypothesis_id"],
        "scope": row["subject_scope"],
        "project_id": row["project_id"],
        "dimension": row["dimension"],
        "mechanism": row["mechanism"],
        "applicability": json.loads(row["applicability_json"]),
        "version": row["version"],
    } for row in eligible]
    projected = [_projection_row(by_id[hypothesis_id]) for hypothesis_id in selected]

    return {
        "schema": PROJECTION_SCHEMA,
        "project_id": project_id,
        "priority_order": ["current_explicit_request", "selected_project_active", "selected_user_taste_active"],
        "explicit_intent": explicit_intent,
        "available_active_hypothesis_ids": [row["hypothesis_id"] for row in eligible],
        "active_preference_index": index,
        "selected_hypothesis_ids": selected,
        "active_preferences": projected,
        "all_active_preferences_auto_included": False,
        "semantic_relevance_judged_by_runtime": False,
        "candidate_hypotheses_included": False,
        "one_off_history_included": False,
        "general_craft_candidates_included": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def self_test(path: Path | None = None) -> dict[str, Any]:
    db = path or Path(tempfile.gettempdir()) / "novelforge-author-model-selftest.db"
    if db.exists():
        db.unlink()
    store = LearningStore(db)
    store.init()

    base = {
        "schema": CAPTURE_SCHEMA,
        "project_id": "P1",
        "feedback_ref": "review:1",
        "artifact_ref": "draft:1",
        "artifact_fingerprint": "sha256:" + "a" * 64,
        "activation": {"project_preference_write_authorized": False, "durable_user_taste_write_authorized": False},
    }
    r1 = capture_feedback(store, {**base, "interpretation": {
        "scope_candidate": "project", "dimension": "paragraph_rhythm", "mechanism": "functional paragraphing",
        "statement": "Prefer functional paragraphs over mechanical fragmentation.", "polarity": "negative",
        "confidence": 1.0, "evidence_source": "human_review", "avoid_behavior": ["mechanical one-sentence paragraph default"]
    }})
    p0 = project_author_model(store, project_id="P1")
    unauthorized_project_inactive = r1["hypothesis_state"] == "candidate" and not p0["available_active_hypothesis_ids"]

    r2 = capture_feedback(store, {**base, "feedback_ref": "review:2", "activation": {"project_preference_write_authorized": True, "durable_user_taste_write_authorized": False}, "interpretation": {
        "scope_candidate": "project", "dimension": "paragraph_rhythm", "mechanism": "functional paragraphing",
        "statement": "Use mixed, functional paragraph units; pace through events.", "polarity": "mixed", "confidence": 1.0,
        "evidence_source": "explicit_rule", "desired_behavior": ["functional multi-sentence paragraphs"],
        "avoid_behavior": ["mechanical fragmentation"], "contradicts_hypothesis_ids": [r1["hypothesis_id"]]
    }})
    p1 = project_author_model(store, project_id="P1", explicit_intent=[{"dimension":"current_request","statement":"Keep this scene terse."}])
    p1_selected = project_author_model(store, project_id="P1", selected_hypothesis_ids=[r2["hypothesis_id"]])
    old = _load_hypothesis(store, r1["hypothesis_id"])
    project_active = r2["active_for_future_production"] and r2["hypothesis_id"] in p1["available_active_hypothesis_ids"]
    active_not_auto_injected = project_active and not p1["active_preferences"] and p1["all_active_preferences_auto_included"] is False
    explicit_selection_projects = any(x["hypothesis_id"] == r2["hypothesis_id"] for x in p1_selected["active_preferences"])
    unknown_selection_blocked = False
    try:
        project_author_model(store, project_id="P1", selected_hypothesis_ids=["HYP-NOT-ACTIVE"])
    except ValueError:
        unknown_selection_blocked = True
    contradiction_supersedes = old is not None and old["state"] == "superseded"

    r3 = capture_feedback(store, {**base, "feedback_ref": "review:3", "interpretation": {
        "scope_candidate": "user_taste", "dimension": "narration", "mechanism": "low narrator commentary",
        "statement": "Prefer lower narrator commentary.", "polarity": "negative", "confidence": 0.8, "evidence_source": "human_review"
    }})
    r4 = capture_feedback(store, {**base, "feedback_ref": "review:4", "interpretation": {
        "scope_candidate": "general_craft", "dimension": "dialogue", "mechanism": "agenda dialogue serialization",
        "statement": "Private character agenda should not be serialized into dialogue.", "polarity": "negative", "confidence": 0.9,
        "evidence_source": "human_review"
    }})
    nonproject_not_autoactive = r3["hypothesis_state"] == "candidate" and r4["hypothesis_state"] == "candidate" and not r4["general_craft_auto_promoted"]

    r5 = capture_feedback(store, {**base, "feedback_ref": "review:5", "activation": {
        "project_preference_write_authorized": False, "durable_user_taste_write_authorized": True
    }, "interpretation": {
        "scope_candidate": "user_taste", "dimension": "narration", "mechanism": "low narrator commentary",
        "statement": "Prefer lower narrator commentary when scene action can carry the implication.", "polarity": "negative", "confidence": 0.9,
        "evidence_source": "explicit_rule", "applicability": {"scene_types": ["dramatic"]}
    }})
    write_authority_alone_not_enough = (
        r5["hypothesis_state"] == "candidate"
        and r5["user_taste_activation_prerequisite"]["status"] == "missing"
    )

    refs = ["review:5", "EVAL-UT-1"]
    promotion_candidate = {
        "schema": PROMOTION_CANDIDATE_SCHEMA,
        "candidate_id": "UT-GOOD",
        "scope": "user_taste",
        "mechanism": "low narrator commentary",
        "evidence": {"evidence_refs": refs},
    }
    promotion_candidate["semantic_review_binding"] = _promotion_semantic_binding(
        "UT-GOOD", "user_taste", "low narrator commentary", refs
    )
    r6 = capture_feedback(store, {**base, "feedback_ref": "review:6", "activation": {
        "project_preference_write_authorized": False,
        "durable_user_taste_write_authorized": True,
        "user_taste_promotion_candidate": promotion_candidate,
    }, "interpretation": {
        "scope_candidate": "user_taste", "dimension": "narration", "mechanism": "low narrator commentary",
        "statement": "Prefer lower narrator commentary when scene action can carry the implication.", "polarity": "negative", "confidence": 0.9,
        "evidence_source": "explicit_rule", "applicability": {"scene_types": ["dramatic"]}
    }})
    user_taste_gate_and_write_required = (
        r6["hypothesis_state"] == "active"
        and r6["active_for_future_production"]
        and r6["user_taste_activation_prerequisite"]["ready"] is True
        and r6["user_taste_activation_prerequisite"]["semantic_evidence_count_threshold_used"] is False
        and r6["user_taste_activation_prerequisite"]["durable_user_taste_write_authority"] is False
    )

    result = {
        "schema": SCHEMA,
        "author_model_contract": "PASS" if all([
            unauthorized_project_inactive,
            project_active,
            active_not_auto_injected,
            explicit_selection_projects,
            unknown_selection_blocked,
            contradiction_supersedes,
            nonproject_not_autoactive,
            write_authority_alone_not_enough,
            user_taste_gate_and_write_required,
        ]) else "FAIL",
        "unauthorized_project_feedback_not_activated": unauthorized_project_inactive,
        "authorized_project_feedback_activated": project_active,
        "all_active_preferences_auto_included": False,
        "agent_selected_active_preferences_only": active_not_auto_injected and explicit_selection_projects,
        "unknown_or_cross_project_selection_blocked": unknown_selection_blocked,
        "semantic_relevance_judged_by_runtime": False,
        "contradiction_supersedes": contradiction_supersedes,
        "user_taste_and_general_craft_not_autoactivated": nonproject_not_autoactive,
        "user_taste_write_authority_alone_not_enough": write_authority_alone_not_enough,
        "user_taste_requires_promotion_prerequisite_and_write_authority": user_taste_gate_and_write_required,
        "candidate_hypotheses_excluded_from_projection": p1["candidate_hypotheses_included"] is False,
        "authority": False,
        "model_execution": False,
    }
    if db.exists():
        db.unlink()
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
        if a.cmd == "capture":
            out = capture_feedback(store, _load(a.request))
        else:
            explicit = _load(a.explicit_intent) if a.explicit_intent else []
            selected = _load(a.selected_hypothesis_ids) if a.selected_hypothesis_ids else []
            out = project_author_model(store, project_id=a.project_id, explicit_intent=explicit, selected_hypothesis_ids=selected)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("author_model_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())