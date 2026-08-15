#!/usr/bin/env python3
"""Portable creative-decision artifact and lifecycle contract for NovelForge.

The tool records unresolved/decided planning-choice provenance without becoming
a plan store, Canon store, or hidden-reasoning archive. It is deterministic:
semantic judgment (whether a choice is material, what to choose, and the
user-visible rationale) belongs to the manager/user/planner before calling it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_creative_decision_v1"
OPEN_REQUEST_SCHEMA = "novelforge_creative_decision_open_request_v1"
RESOLUTION_SCHEMA = "novelforge_creative_decision_resolution_v1"
SUPERSESSION_SCHEMA = "novelforge_creative_decision_supersession_v1"
DROP_SCHEMA = "novelforge_creative_decision_drop_v1"
TRANSITION_SCHEMA = "novelforge_creative_decision_transition_v1"
PROJECTION_SCHEMA = "novelforge_creative_decision_projection_v1"

STATUSES = {"open", "decided", "superseded", "dropped"}
RESOLVER_CLASSES = {"user", "authorized_human", "authorized_planner"}
OPENER_CLASSES = RESOLVER_CLASSES | {"manager", "writer"}
AUDIENCES = {"planner", "writer", "reader", "character"}
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

MAX_ALTERNATIVES = 8
MAX_QUESTION = 1200
MAX_LABEL = 600
MAX_RATIONALE = 1600
MAX_REASON = 800
MAX_RISK = 600


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def nonempty(value: Any, field: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be non-empty string <= {limit}")
    return value.strip()


def sha(value: Any, field: str) -> str:
    value = nonempty(value, field, 71)
    if not SHA_RE.fullmatch(value):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def sorted_unique_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be array")
    out = [nonempty(x, field) for x in value]
    if out != sorted(set(out)):
        raise ValueError(f"{field} must be sorted and unique")
    return out


def exact_fields(value: dict[str, Any], allowed: set[str], field: str) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    if extra or missing:
        raise ValueError(f"{field} fields mismatch missing={missing} extra={extra}")


def normalize_actor(value: Any, *, allow_openers: bool) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("actor must be object")
    exact_fields(value, {"class", "evidence_ref", "evidence_fingerprint"}, "actor")
    classes = OPENER_CLASSES if allow_openers else RESOLVER_CLASSES
    actor_class = nonempty(value.get("class"), "actor.class")
    if actor_class not in classes:
        raise ValueError(f"actor.class must be one of {sorted(classes)}")
    return {
        "class": actor_class,
        "evidence_ref": nonempty(value.get("evidence_ref"), "actor.evidence_ref"),
        "evidence_fingerprint": sha(value.get("evidence_fingerprint"), "actor.evidence_fingerprint"),
    }


def normalize_alternatives(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not (2 <= len(value) <= MAX_ALTERNATIVES):
        raise ValueError(f"alternatives must contain 2..{MAX_ALTERNATIVES} items")
    out = []
    ids = set()
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"alternatives[{i}] must be object")
        exact_fields(item, {"option_id", "label", "scenario_ref"}, f"alternatives[{i}]")
        oid = nonempty(item.get("option_id"), f"alternatives[{i}].option_id", 120)
        if oid in ids:
            raise ValueError("alternative option_id must be unique")
        ids.add(oid)
        label = nonempty(item.get("label"), f"alternatives[{i}].label", MAX_LABEL)
        scenario_ref = item.get("scenario_ref")
        if scenario_ref is not None:
            scenario_ref = nonempty(scenario_ref, f"alternatives[{i}].scenario_ref")
        out.append({"option_id": oid, "label": label, "scenario_ref": scenario_ref})
    return out


def record_payload(decision: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(decision)
    out.pop("artifact_fingerprint", None)
    return out


def with_fingerprint(decision: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(decision)
    out["artifact_fingerprint"] = fp(record_payload(out))
    return out


def validate_artifact(decision: Any) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ValueError("decision artifact must be object")
    fields = {
        "schema", "decision_id", "scope_ref", "question", "resolver_classes",
        "alternatives", "serves_refs", "depends_on_refs", "status", "version",
        "history", "supersedes_decision_id", "superseded_by_decision_id",
        "created_by", "created_source_ref", "created_source_fingerprint",
        "artifact_fingerprint", "authority", "canon_authority",
        "project_write_authority", "framework_write_authority",
        "settlement_authority", "model_execution"
    }
    exact_fields(decision, fields, "decision")
    if decision.get("schema") != SCHEMA:
        raise ValueError("decision schema invalid")
    nonempty(decision.get("decision_id"), "decision_id", 160)
    nonempty(decision.get("scope_ref"), "scope_ref", 300)
    nonempty(decision.get("question"), "question", MAX_QUESTION)
    resolvers = sorted_unique_strings(decision.get("resolver_classes"), "resolver_classes")
    if not resolvers or any(x not in RESOLVER_CLASSES for x in resolvers):
        raise ValueError("resolver_classes invalid")
    normalize_alternatives(decision.get("alternatives"))
    sorted_unique_strings(decision.get("serves_refs"), "serves_refs")
    sorted_unique_strings(decision.get("depends_on_refs"), "depends_on_refs")
    status = decision.get("status")
    if status not in STATUSES:
        raise ValueError("status invalid")
    version = decision.get("version")
    if not isinstance(version, int) or version < 1:
        raise ValueError("version must be positive integer")
    history = decision.get("history")
    if not isinstance(history, list) or len(history) != version:
        raise ValueError("history length must equal version")
    if not history:
        raise ValueError("history required")
    expected_seq = list(range(1, version + 1))
    if [x.get("version") for x in history if isinstance(x, dict)] != expected_seq:
        raise ValueError("history versions must be contiguous")
    for i, entry in enumerate(history):
        if not isinstance(entry, dict):
            raise ValueError(f"history[{i}] must be object")
        if entry.get("status") not in STATUSES:
            raise ValueError(f"history[{i}].status invalid")
        if entry.get("record_fingerprint") != fp({k: v for k, v in entry.items() if k != "record_fingerprint"}):
            raise ValueError(f"history[{i}] record fingerprint mismatch")
    if history[-1].get("status") != status:
        raise ValueError("current status must equal last history status")
    if decision.get("supersedes_decision_id") is not None:
        nonempty(decision.get("supersedes_decision_id"), "supersedes_decision_id", 160)
    if decision.get("superseded_by_decision_id") is not None:
        nonempty(decision.get("superseded_by_decision_id"), "superseded_by_decision_id", 160)
    normalize_actor(decision.get("created_by"), allow_openers=True)
    nonempty(decision.get("created_source_ref"), "created_source_ref")
    sha(decision.get("created_source_fingerprint"), "created_source_fingerprint")
    for field in ("authority", "canon_authority", "project_write_authority",
                  "framework_write_authority", "settlement_authority", "model_execution"):
        if decision.get(field) is not False:
            raise ValueError(f"{field} must be false")
    expected_fp = fp(record_payload(decision))
    if decision.get("artifact_fingerprint") != expected_fp:
        raise ValueError("artifact_fingerprint mismatch")
    return deepcopy(decision)


def event_record(version: int, status: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"version": version, "status": status, "kind": kind, **payload}
    return {**body, "record_fingerprint": fp(body)}


def open_decision(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != OPEN_REQUEST_SCHEMA:
        raise ValueError(f"request.schema must be {OPEN_REQUEST_SCHEMA}")
    fields = {
        "schema", "decision_id", "scope_ref", "question", "resolver_classes",
        "alternatives", "serves_refs", "depends_on_refs", "supersedes_decision_id",
        "created_by", "source_ref", "source_fingerprint"
    }
    exact_fields(raw, fields, "open_request")
    decision_id = nonempty(raw.get("decision_id"), "decision_id", 160)
    question = nonempty(raw.get("question"), "question", MAX_QUESTION)
    actor = normalize_actor(raw.get("created_by"), allow_openers=True)
    resolvers = sorted_unique_strings(raw.get("resolver_classes"), "resolver_classes")
    if not resolvers or any(x not in RESOLVER_CLASSES for x in resolvers):
        raise ValueError("resolver_classes invalid")
    alternatives = normalize_alternatives(raw.get("alternatives"))
    source_ref = nonempty(raw.get("source_ref"), "source_ref")
    source_fp = sha(raw.get("source_fingerprint"), "source_fingerprint")
    supersedes = raw.get("supersedes_decision_id")
    if supersedes is not None:
        supersedes = nonempty(supersedes, "supersedes_decision_id", 160)
        if supersedes == decision_id:
            raise ValueError("decision cannot supersede itself")
    base = {
        "schema": SCHEMA,
        "decision_id": decision_id,
        "scope_ref": nonempty(raw.get("scope_ref"), "scope_ref", 300),
        "question": question,
        "resolver_classes": resolvers,
        "alternatives": alternatives,
        "serves_refs": sorted_unique_strings(raw.get("serves_refs"), "serves_refs"),
        "depends_on_refs": sorted_unique_strings(raw.get("depends_on_refs"), "depends_on_refs"),
        "status": "open",
        "version": 1,
        "history": [],
        "supersedes_decision_id": supersedes,
        "superseded_by_decision_id": None,
        "created_by": actor,
        "created_source_ref": source_ref,
        "created_source_fingerprint": source_fp,
        "artifact_fingerprint": "",
        "authority": False,
        "canon_authority": False,
        "project_write_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }
    base["history"] = [event_record(1, "open", "opened", {
        "actor": actor, "source_ref": source_ref, "source_fingerprint": source_fp
    })]
    return with_fingerprint(base)


def _check_before(before: Any, expected_version: Any, expected_fingerprint: Any) -> dict[str, Any]:
    artifact = validate_artifact(before)
    if expected_version != artifact["version"]:
        raise ValueError(f"before version mismatch expected={expected_version} actual={artifact['version']}")
    if expected_fingerprint != artifact["artifact_fingerprint"]:
        raise ValueError("before fingerprint mismatch")
    return artifact


def decide(before: Any, resolution: Any) -> dict[str, Any]:
    if not isinstance(resolution, dict) or resolution.get("schema") != RESOLUTION_SCHEMA:
        raise ValueError(f"resolution.schema must be {RESOLUTION_SCHEMA}")
    fields = {
        "schema", "expected_version", "expected_fingerprint", "actor",
        "chosen_option_id", "chosen_outcome", "rationale", "rejected_alternatives",
        "accepted_risks", "evidence_ref", "evidence_fingerprint"
    }
    exact_fields(resolution, fields, "resolution")
    artifact = _check_before(before, resolution.get("expected_version"), resolution.get("expected_fingerprint"))
    if artifact["status"] != "open":
        raise ValueError("only open decision may be decided")
    actor = normalize_actor(resolution.get("actor"), allow_openers=False)
    if actor["class"] not in artifact["resolver_classes"]:
        raise ValueError("actor class lacks decision resolution authority")
    option_ids = {x["option_id"] for x in artifact["alternatives"]}
    chosen_id = resolution.get("chosen_option_id")
    if chosen_id is not None:
        chosen_id = nonempty(chosen_id, "chosen_option_id", 120)
        if chosen_id not in option_ids:
            raise ValueError("chosen_option_id is not an offered alternative")
    chosen_outcome = nonempty(resolution.get("chosen_outcome"), "chosen_outcome", MAX_LABEL)
    rationale = nonempty(resolution.get("rationale"), "rationale", MAX_RATIONALE)
    rejected = resolution.get("rejected_alternatives")
    if not isinstance(rejected, list):
        raise ValueError("rejected_alternatives must be array")
    seen = set()
    rejected_norm = []
    for i, item in enumerate(rejected):
        if not isinstance(item, dict):
            raise ValueError(f"rejected_alternatives[{i}] must be object")
        exact_fields(item, {"option_id", "reason"}, f"rejected_alternatives[{i}]")
        oid = nonempty(item.get("option_id"), f"rejected_alternatives[{i}].option_id", 120)
        if oid not in option_ids:
            raise ValueError("rejected alternative not in offered alternatives")
        if oid == chosen_id:
            raise ValueError("chosen option cannot be rejected")
        if oid in seen:
            raise ValueError("rejected alternative duplicated")
        seen.add(oid)
        rejected_norm.append({"option_id": oid, "reason": nonempty(item.get("reason"), "rejected reason", MAX_REASON)})
    risks = resolution.get("accepted_risks")
    if not isinstance(risks, list):
        raise ValueError("accepted_risks must be array")
    risks_norm = [nonempty(x, "accepted_risk", MAX_RISK) for x in risks]
    if risks_norm != sorted(set(risks_norm)):
        raise ValueError("accepted_risks must be sorted and unique")
    evidence_ref = nonempty(resolution.get("evidence_ref"), "evidence_ref")
    evidence_fp = sha(resolution.get("evidence_fingerprint"), "evidence_fingerprint")

    out = deepcopy(artifact)
    version = artifact["version"] + 1
    out["status"] = "decided"
    out["version"] = version
    out["history"].append(event_record(version, "decided", "resolved", {
        "actor": actor,
        "chosen_option_id": chosen_id,
        "chosen_outcome": chosen_outcome,
        "rationale": rationale,
        "rejected_alternatives": rejected_norm,
        "accepted_risks": risks_norm,
        "evidence_ref": evidence_ref,
        "evidence_fingerprint": evidence_fp,
    }))
    return with_fingerprint(out)


def supersede(before: Any, successor: Any, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != SUPERSESSION_SCHEMA:
        raise ValueError(f"request.schema must be {SUPERSESSION_SCHEMA}")
    fields = {
        "schema", "expected_version", "expected_fingerprint", "actor",
        "successor_decision_id", "successor_fingerprint", "reason",
        "evidence_ref", "evidence_fingerprint"
    }
    exact_fields(request, fields, "supersession")
    artifact = _check_before(before, request.get("expected_version"), request.get("expected_fingerprint"))
    if artifact["status"] not in {"open", "decided"}:
        raise ValueError("only open/decided decision may be superseded")
    actor = normalize_actor(request.get("actor"), allow_openers=False)
    if actor["class"] not in artifact["resolver_classes"]:
        raise ValueError("actor class lacks supersession authority")
    next_decision = validate_artifact(successor)
    if next_decision["decision_id"] != request.get("successor_decision_id"):
        raise ValueError("successor_decision_id mismatch")
    if next_decision["artifact_fingerprint"] != request.get("successor_fingerprint"):
        raise ValueError("successor_fingerprint mismatch")
    if next_decision.get("supersedes_decision_id") != artifact["decision_id"]:
        raise ValueError("successor must explicitly supersede this decision")
    if next_decision["scope_ref"] != artifact["scope_ref"]:
        raise ValueError("successor scope_ref must match")
    reason = nonempty(request.get("reason"), "reason", MAX_REASON)
    evidence_ref = nonempty(request.get("evidence_ref"), "evidence_ref")
    evidence_fp = sha(request.get("evidence_fingerprint"), "evidence_fingerprint")

    out = deepcopy(artifact)
    version = artifact["version"] + 1
    out["status"] = "superseded"
    out["version"] = version
    out["superseded_by_decision_id"] = next_decision["decision_id"]
    out["history"].append(event_record(version, "superseded", "superseded", {
        "actor": actor,
        "successor_decision_id": next_decision["decision_id"],
        "successor_fingerprint": next_decision["artifact_fingerprint"],
        "reason": reason,
        "evidence_ref": evidence_ref,
        "evidence_fingerprint": evidence_fp,
    }))
    old_out = with_fingerprint(out)
    return {
        "schema": TRANSITION_SCHEMA,
        "transition": "supersede",
        "before_fingerprint": artifact["artifact_fingerprint"],
        "after_fingerprint": old_out["artifact_fingerprint"],
        "updated_decision": old_out,
        "successor_decision": next_decision,
        "downstream_revalidation_candidates": artifact["serves_refs"],
        "propagation_debt_created": False,
        "active_plan_write_performed": False,
        "authority": False,
        "canon_authority": False,
        "project_write_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def drop(before: Any, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != DROP_SCHEMA:
        raise ValueError(f"request.schema must be {DROP_SCHEMA}")
    fields = {"schema", "expected_version", "expected_fingerprint", "actor", "reason", "evidence_ref", "evidence_fingerprint"}
    exact_fields(request, fields, "drop")
    artifact = _check_before(before, request.get("expected_version"), request.get("expected_fingerprint"))
    if artifact["status"] not in {"open", "decided"}:
        raise ValueError("only open/decided decision may be dropped")
    actor = normalize_actor(request.get("actor"), allow_openers=False)
    if actor["class"] not in artifact["resolver_classes"]:
        raise ValueError("actor class lacks drop authority")
    out = deepcopy(artifact)
    version = artifact["version"] + 1
    out["status"] = "dropped"
    out["version"] = version
    out["history"].append(event_record(version, "dropped", "dropped", {
        "actor": actor,
        "reason": nonempty(request.get("reason"), "reason", MAX_REASON),
        "evidence_ref": nonempty(request.get("evidence_ref"), "evidence_ref"),
        "evidence_fingerprint": sha(request.get("evidence_fingerprint"), "evidence_fingerprint"),
    }))
    return with_fingerprint(out)


def current_resolution(artifact: dict[str, Any]) -> dict[str, Any] | None:
    artifact = validate_artifact(artifact)
    for item in reversed(artifact["history"]):
        if item["kind"] == "resolved":
            return deepcopy(item)
    return None


def project(artifact: Any, audience: str) -> dict[str, Any]:
    value = validate_artifact(artifact)
    if audience not in AUDIENCES:
        raise ValueError(f"audience must be one of {sorted(AUDIENCES)}")
    base = {
        "schema": PROJECTION_SCHEMA,
        "decision_id": value["decision_id"],
        "scope_ref": value["scope_ref"],
        "status": value["status"],
        "audience": audience,
        "source_fingerprint": value["artifact_fingerprint"],
        "authority": False,
        "canon_authority": False,
        "model_execution": False,
    }
    if audience in {"reader", "character"}:
        return {**base, "visible": False, "reason": "future_planning_decision_hidden"}
    if audience == "writer":
        if value["status"] != "open":
            return {**base, "visible": False, "reason": "decided_or_inactive_decision_belongs_in_active_plan_not_writer_decision_context"}
        return {
            **base,
            "visible": True,
            "question": value["question"],
            "warning": "OPEN_DECISION: do not resolve this choice unless the current task carries an allowed resolver class.",
            "resolver_classes": value["resolver_classes"],
            "alternatives_hidden": True,
        }
    return {
        **base,
        "visible": True,
        "question": value["question"],
        "resolver_classes": value["resolver_classes"],
        "alternatives": value["alternatives"],
        "serves_refs": value["serves_refs"],
        "depends_on_refs": value["depends_on_refs"],
        "resolution": current_resolution(value),
        "history": value["history"],
    }


def transition_result(before: dict[str, Any], after: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "schema": TRANSITION_SCHEMA,
        "transition": kind,
        "before_fingerprint": before["artifact_fingerprint"],
        "after_fingerprint": after["artifact_fingerprint"],
        "updated_decision": after,
        "downstream_revalidation_candidates": before["serves_refs"],
        "propagation_debt_created": False,
        "active_plan_write_performed": False,
        "authority": False,
        "canon_authority": False,
        "project_write_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def blocked(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def fixture_open(decision_id: str = "DEC-POV-001", supersedes: str | None = None) -> dict[str, Any]:
    return {
        "schema": OPEN_REQUEST_SCHEMA,
        "decision_id": decision_id,
        "scope_ref": "chapter:CH-010",
        "question": "Which character owns the decisive point-of-view turn in the chapter?",
        "resolver_classes": ["authorized_human", "user"],
        "alternatives": [
            {"option_id": "mei", "label": "Mei owns the turn.", "scenario_ref": "scenario:BR-MEI"},
            {"option_id": "zhou", "label": "Zhou owns the turn.", "scenario_ref": "scenario:BR-ZHOU"},
        ],
        "serves_refs": ["plan:CH-010", "review:CH-010"],
        "depends_on_refs": ["commitment:POV-ARC"],
        "supersedes_decision_id": supersedes,
        "created_by": {
            "class": "writer",
            "evidence_ref": "draft-diagnosis:CH-010",
            "evidence_fingerprint": "sha256:" + "1" * 64,
        },
        "source_ref": "request:CH-010",
        "source_fingerprint": "sha256:" + "2" * 64,
    }


def fixture_resolution(before: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": RESOLUTION_SCHEMA,
        "expected_version": before["version"],
        "expected_fingerprint": before["artifact_fingerprint"],
        "actor": {
            "class": "user",
            "evidence_ref": "user-choice:turn-42",
            "evidence_fingerprint": "sha256:" + "3" * 64,
        },
        "chosen_option_id": "mei",
        "chosen_outcome": "Mei owns the decisive POV turn.",
        "rationale": "This keeps the chapter's emotional cost on the character who must make the irreversible choice.",
        "rejected_alternatives": [
            {"option_id": "zhou", "reason": "It would move the key agency away from the intended arc owner."}
        ],
        "accepted_risks": ["Mei receives less explanatory distance."],
        "evidence_ref": "user-choice:turn-42",
        "evidence_fingerprint": "sha256:" + "3" * 64,
    }


def self_test() -> dict[str, Any]:
    opened = open_decision(fixture_open())
    writer = project(opened, "writer")
    planner = project(opened, "planner")
    reader = project(opened, "reader")
    character = project(opened, "character")

    bad_writer_resolution = fixture_resolution(opened)
    bad_writer_resolution["actor"] = {
        "class": "writer",
        "evidence_ref": "writer:self",
        "evidence_fingerprint": "sha256:" + "4" * 64,
    }
    writer_cannot_resolve = blocked(lambda: decide(opened, bad_writer_resolution))

    stale = fixture_resolution(opened)
    stale["expected_version"] = 99
    stale_guard = blocked(lambda: decide(opened, stale))

    decided = decide(opened, fixture_resolution(opened))
    decided_valid = validate_artifact(decided)
    writer_decided = project(decided, "writer")
    planner_decided = project(decided, "planner")

    successor = open_decision(fixture_open("DEC-POV-002", supersedes=opened["decision_id"]))
    sup_request = {
        "schema": SUPERSESSION_SCHEMA,
        "expected_version": decided["version"],
        "expected_fingerprint": decided["artifact_fingerprint"],
        "actor": {
            "class": "authorized_human",
            "evidence_ref": "author-revision:POV",
            "evidence_fingerprint": "sha256:" + "5" * 64,
        },
        "successor_decision_id": successor["decision_id"],
        "successor_fingerprint": successor["artifact_fingerprint"],
        "reason": "The arc structure changed and the earlier POV decision must be reconsidered.",
        "evidence_ref": "author-revision:POV",
        "evidence_fingerprint": "sha256:" + "5" * 64,
    }
    superseded = supersede(decided, successor, sup_request)
    old_after = superseded["updated_decision"]

    wrong_scope = deepcopy(successor)
    wrong_scope["scope_ref"] = "chapter:CH-999"
    wrong_scope = with_fingerprint(wrong_scope)
    bad_sup = deepcopy(sup_request)
    bad_sup["successor_fingerprint"] = wrong_scope["artifact_fingerprint"]
    bad_scope_blocked = blocked(lambda: supersede(decided, wrong_scope, bad_sup))

    drop_request = {
        "schema": DROP_SCHEMA,
        "expected_version": successor["version"],
        "expected_fingerprint": successor["artifact_fingerprint"],
        "actor": {
            "class": "user",
            "evidence_ref": "user-drop:turn-50",
            "evidence_fingerprint": "sha256:" + "6" * 64,
        },
        "reason": "The question no longer applies after structural revision.",
        "evidence_ref": "user-drop:turn-50",
        "evidence_fingerprint": "sha256:" + "6" * 64,
    }
    dropped = drop(successor, drop_request)

    tampered = deepcopy(decided)
    tampered["question"] = "Tampered question"
    tamper_blocked = blocked(lambda: validate_artifact(tampered))

    checks = {
        "open_decision_is_non_authoritative": opened["status"] == "open" and all(opened[k] is False for k in [
            "authority", "canon_authority", "project_write_authority", "framework_write_authority", "settlement_authority", "model_execution"
        ]),
        "writer_sees_warning_not_alternatives": writer["visible"] is True and writer["alternatives_hidden"] is True and "alternatives" not in writer,
        "reader_and_character_do_not_see_future_choice": reader["visible"] is False and character["visible"] is False,
        "planner_can_inspect_bounded_alternatives": planner["visible"] is True and len(planner["alternatives"]) == 2,
        "writer_cannot_silently_resolve": writer_cannot_resolve,
        "before_state_cas_blocks_stale_resolution": stale_guard,
        "authorized_resolution_records_visible_provenance": decided_valid["status"] == "decided" and current_resolution(decided)["rationale"] == fixture_resolution(opened)["rationale"],
        "decided_choice_not_duplicated_into_writer_context": writer_decided["visible"] is False and planner_decided["resolution"]["chosen_option_id"] == "mei",
        "supersession_preserves_old_history": old_after["status"] == "superseded" and old_after["history"][1]["kind"] == "resolved" and old_after["history"][-1]["kind"] == "superseded",
        "supersession_requires_explicit_successor_lineage": old_after["superseded_by_decision_id"] == "DEC-POV-002" and successor["supersedes_decision_id"] == "DEC-POV-001",
        "supersession_scope_mismatch_fails_closed": bad_scope_blocked,
        "supersession_emits_revalidation_candidates_without_auto_debt": superseded["downstream_revalidation_candidates"] == ["plan:CH-010", "review:CH-010"] and superseded["propagation_debt_created"] is False,
        "decision_transition_never_writes_active_plan": superseded["active_plan_write_performed"] is False,
        "drop_preserves_artifact_history": dropped["status"] == "dropped" and dropped["version"] == 2 and dropped["history"][0]["kind"] == "opened",
        "artifact_fingerprint_detects_tamper": tamper_blocked,
    }
    return {
        "creative_decision_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "statuses": sorted(STATUSES),
        "resolver_classes": sorted(RESOLVER_CLASSES),
        **checks,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge creative-decision artifact contract")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    o = sub.add_parser("open"); o.add_argument("--request", required=True)
    v = sub.add_parser("validate"); v.add_argument("--decision", required=True)
    r = sub.add_parser("resolve"); r.add_argument("--before", required=True); r.add_argument("--resolution", required=True)
    s = sub.add_parser("supersede"); s.add_argument("--before", required=True); s.add_argument("--successor", required=True); s.add_argument("--request", required=True)
    d = sub.add_parser("drop"); d.add_argument("--before", required=True); d.add_argument("--request", required=True)
    q = sub.add_parser("project"); q.add_argument("--decision", required=True); q.add_argument("--audience", choices=sorted(AUDIENCES), required=True)
    args = p.parse_args()
    try:
        if args.command == "self-test":
            out = self_test()
            dump(out)
            return 0 if out["creative_decision_contract"] == "PASS" else 1
        if args.command == "open":
            dump(open_decision(load(Path(args.request)))); return 0
        if args.command == "validate":
            dump(validate_artifact(load(Path(args.decision)))); return 0
        if args.command == "resolve":
            before = load(Path(args.before)); after = decide(before, load(Path(args.resolution)))
            dump(transition_result(validate_artifact(before), after, "resolve")); return 0
        if args.command == "supersede":
            dump(supersede(load(Path(args.before)), load(Path(args.successor)), load(Path(args.request)))); return 0
        if args.command == "drop":
            before = load(Path(args.before)); after = drop(before, load(Path(args.request)))
            dump(transition_result(validate_artifact(before), after, "drop")); return 0
        if args.command == "project":
            dump(project(load(Path(args.decision)), args.audience)); return 0
    except Exception as exc:
        dump({"error": str(exc), "authority": False, "model_execution": False})
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
