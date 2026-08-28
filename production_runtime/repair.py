"""Exact repair inputs and lineage; literary decisions remain model-owned."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from harness.context_runtime import canonical_json, fingerprint
from persistence.quillframe_sqlite import fingerprint_text
from quality.candidate_lineage import validate_derivation
from quality.candidate_qualification import comparison_gate_status
from quality.objective_envelope import build as build_objective_envelope
from quality.objective_envelope import validate as validate_objective_envelope
from quality.repair_policy import evaluate as evaluate_repair_policy

from .contracts import ProductionRunError

LINEAGE_SCHEMA = "quillframe_production_repair_lineage_v1"


def _candidate_id(run_id: str) -> str:
    return "diagnostic:" + run_id


def prior_lineage(source: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Use the existing lineage rules without installing tables in Project DB."""
    previous = source.get("source_lineage")
    source_id = _candidate_id(source["source_run_id"])
    if previous is None:
        if source["source_task_mode"] != "DRAFT":
            raise ProductionRunError("repair_lineage_missing", "a repaired source cannot become a new draft baseline")
        return source["source_run_id"], [{
            "candidate_id": source_id, "candidate_fingerprint": source["candidate_fingerprint"],
            "created_by_run_id": source["source_run_id"], "origin": "draft",
            "comparison_parent_candidate_id": None, "prose_parent_candidate_id": None,
        }]
    if source["source_task_mode"] != "REVISE" or not isinstance(previous, dict) or previous.get("schema") != LINEAGE_SCHEMA or previous.get("authority") is not False:
        raise ProductionRunError("repair_lineage_invalid", "repair source lineage is invalid")
    if previous.get("lineage_fingerprint") != fingerprint({key: value for key, value in previous.items() if key != "lineage_fingerprint"}):
        raise ProductionRunError("repair_lineage_invalid", "repair source lineage fingerprint changed")
    nodes = previous.get("nodes")
    if not isinstance(nodes, list) or len(nodes) < 2:
        raise ProductionRunError("repair_lineage_invalid", "repair source has no derivation history")
    seen = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get("created_by_run_id"), str):
            raise ProductionRunError("repair_lineage_invalid", "repair lineage node is invalid")
        if node.get("candidate_id") != _candidate_id(node["created_by_run_id"]) or node["candidate_id"] in seen:
            raise ProductionRunError("repair_lineage_invalid", "repair lineage identity is invalid")
        expected_parent = nodes[index - 1]["candidate_id"] if index else None
        if node.get("comparison_parent_candidate_id") != expected_parent or (index == 0) != (node.get("origin") == "draft"):
            raise ProductionRunError("repair_lineage_invalid", "repair comparison ancestry changed")
        try:
            validate_derivation(origin=node.get("origin"), comparison_parent_candidate_id=expected_parent,
                                prose_parent_candidate_id=node.get("prose_parent_candidate_id"))
        except ValueError as exc:
            raise ProductionRunError("repair_lineage_invalid", str(exc)) from exc
        seen.add(node["candidate_id"])
    if (nodes[-1]["candidate_id"] != source_id or nodes[-1].get("candidate_fingerprint") != source["candidate_fingerprint"]
            or previous.get("evolution_run_id") != nodes[0]["created_by_run_id"]):
        raise ProductionRunError("repair_lineage_invalid", "repair lineage does not bind the exact source candidate")
    binding = (source.get("source_repair_preservation") or {}).get("semantic_binding", {})
    judgment = binding.get("result", {}).get("judgment", {})
    if judgment.get("winner") != "challenger" or comparison_gate_status(judgment) != "pass":
        raise ProductionRunError(
            "repair_incumbent_retained",
            "the rejected repair did not replace its incumbent; it cannot become the next comparison baseline",
        )
    comparison = binding.get("job", {}).get("input", {}).get("payload", {})
    if comparison.get("evolution_run_id") != previous["evolution_run_id"] or any(
            comparison.get(side, {}).get(key) != node[field]
            for side, node in (("incumbent", nodes[-2]), ("challenger", nodes[-1]))
            for key, field in (("candidate_id", "candidate_id"), ("content_fingerprint", "candidate_fingerprint"))):
        raise ProductionRunError("repair_lineage_invalid", "source lineage does not match its actual registered comparison")
    if comparison.get("repair_context", {}).get("objective_envelope", {}).get("fingerprint") != previous.get("objective_envelope_fingerprint"):
        raise ProductionRunError("repair_lineage_invalid", "source lineage changed its compared objective envelope")
    return previous["evolution_run_id"], deepcopy(nodes)


def objective_envelope(source: dict[str, Any], frozen_story: dict[str, Any], *, reading_positioning: dict[str, Any] | None = None) -> dict[str, Any]:
    """Lossless projection of explicit inputs, never objectives inferred from prose."""
    evolution_run_id, _ = prior_lineage(source)
    request = source["source_request"]
    request_ref = "production-request:" + source["source_request_fingerprint"]
    items = [
        {"id": "OBJ-REQUEST", "category": "user_direction", "statement": request["instruction"], "source_refs": [request_ref]},
        {"id": "OBJ-GRIP", "category": "profile", "statement": canonical_json({"reader_grip": request["reader_grip"]}), "source_refs": [request_ref]},
    ]
    previous_envelope = None
    revisions = []
    if source.get("source_lineage") is not None:
        # prior_lineage has bound this Core-built comparison input to the exact
        # verified source run. Inherit explicit author requests only, never old
        # plans, model judgments, rejected prose or a critique trajectory.
        previous_envelope = source["source_repair_preservation"]["semantic_binding"]["job"]["input"]["payload"]["repair_context"]["objective_envelope"]
        errors = validate_objective_envelope(
            previous_envelope, subject_id=source["source_target_context"]["document_id"], run_id=evolution_run_id,
        )
        if errors:
            raise ProductionRunError("repair_lineage_invalid", "source objective envelope is invalid: " + "; ".join(errors))
        revisions = [deepcopy(item) for item in previous_envelope["objective_items"]
                     if item["category"] == "user_direction"
                     and any(ref.startswith("author-revision:") for ref in item["source_refs"])]
    if source.get("source_kind") == "author_revision":
        # Keep chronological requests, with an unambiguous ID for the new one.
        # The runtime records precedence; the Editor judges semantic conflicts.
        for item in revisions:
            if item["id"] == "OBJ-AUTHOR-REVISION":
                item["id"] += "-" + fingerprint(item)[7:]
        revisions.append({
            "id": "OBJ-AUTHOR-REVISION", "category": "user_direction",
            "statement": source["author_revision_request"]["revision_request"]["instruction"],
            "source_refs": ["author-revision:" + source["author_revision_request_fingerprint"]],
        })
    items.extend(revisions)
    if reading_positioning is not None:
        if (not isinstance(reading_positioning, dict)
                or reading_positioning.get("schema") != "quillframe_production_reading_positioning_v1"
                or reading_positioning.get("positioning_fingerprint") != fingerprint(
                    {key: value for key, value in reading_positioning.items() if key != "positioning_fingerprint"})):
            raise ProductionRunError("reader_positioning_mismatch", "repair objective requires the exact current positioning projection")
        items.append({
            "id": "OBJ-CURRENT-READING-POSITIONING", "category": "profile",
            "statement": canonical_json(reading_positioning["reader_fields"]),
            "source_refs": ["reading-positioning:" + reading_positioning["positioning_fingerprint"],
                            "author-target:" + reading_positioning["source_binding"]["author_request_fingerprint"]],
        })
    # The freeze already selected and verified these actual active plans. Copy
    # their explicit content without interpreting or selecting literary goals.
    for row in frozen_story["items"]:
        if row["object_type"] == "plan" and row["authority"] == "active_plan":
            items.append({"id": "OBJ-PLAN-" + row["object_id"], "category": "story",
                          "statement": canonical_json(row["model_view"]),
                          "source_refs": [row["object_id"] + ":" + row["source_fingerprint"]]})
    preferences = source["source_target_context"].get("author_model", {}).get("active_preferences", [])
    if preferences:
        items.append({"id": "OBJ-PREFERENCES", "category": "profile", "statement": canonical_json(preferences),
                      "source_refs": ["author-target:" + source["source_target_context_fingerprint"]]})
    authority_cutoff = "exact original author request and current frozen active plans"
    if revisions:
        authority_cutoff = (
            "exact original author request, chronological author revision requests, and current frozen active plans; "
            "later author revisions take precedence on conflict; preserve earlier user directions only where not "
            "superseded by later author direction, without overriding protected Project authority"
        )
    change = {}
    if previous_envelope is not None and source.get("source_kind") == "author_revision":
        change = {"supersedes_fingerprint": previous_envelope["fingerprint"],
                  "change_authority_ref": "author-revision:" + source["author_revision_request_fingerprint"]}
    return build_objective_envelope({
        "subject_id": source["source_target_context"]["document_id"], "run_id": evolution_run_id,
        "authority_cutoff": authority_cutoff,
        "objective_items": items, "must_preserve": [item["id"] for item in items],
        "derived_from_rejected_realization": False,
        **change,
    })


def editor_payload(source: dict[str, Any], envelope: dict[str, Any], frozen_story: dict[str, Any]) -> dict[str, Any]:
    goal = (
        "Resolve the recorded blocking defects without overruling their valid findings or lowering the required gates. "
        "The objective envelope quotes explicit source inputs; must_preserve lists their objective IDs. "
        "Choose FIX and PRESERVE semantically from these objectives and evidence. "
        "For fresh_realization, write abstract current-state/function constraints, never rejected quotations or concrete surface patches."
    )
    if source.get("source_kind") == "author_revision":
        goal = (
            "The source was released under its historical review contract. Those original judgments are unchanged; "
            "they do not override the author's explicit request for revision in OBJ-AUTHOR-REVISION. "
            "Diagnose the requested change from the actual source prose and choose the owning repair and generation mode. "
            "Preserve the other authorized objectives and all applicable information boundaries. "
            "For fresh_realization, express FIX and PRESERVE as abstract current-state/function constraints; "
            "do not send old prose, quoted critiques, or a complaint transcript to the fresh Writer."
        )
    return {
        "candidate_fingerprint": source["candidate_fingerprint"], "candidate_text": source["candidate_text"],
        "reader_assessment": deepcopy(source["reader_binding"]["result"]["judgment"]),
        "semantic_rule_assessment": deepcopy(source["self_audit_binding"]["result"]["judgment"]),
        "objective_envelope": envelope,
        "current_repair_goal": goal,
        "authorized_story_evidence": deepcopy(frozen_story["items"]),
    }


def generation_plan(editor_binding: dict[str, Any], envelope: dict[str, Any], *, source_kind: str | None = None) -> dict[str, Any]:
    judgment = editor_binding["result"]["judgment"]
    policy = evaluate_repair_policy({"repair_owner": judgment["repair_owner"], "generation_mode": judgment["generation_mode"],
                                     "candidate_rejected": source_kind != "author_revision",
                                     "author_revision_requested": source_kind == "author_revision"})
    # Do not forward reports, evidence quotes, context-strategy explanations, or
    # the complete critique trajectory to a fresh Writer.
    plan = {key: deepcopy(judgment[key]) for key in ("fix", "preserve")}
    if policy["generation_mode"] == "local_or_bounded_repair":
        plan["repair_plan"] = judgment["repair_plan"]
    return {"policy": policy, "objective_envelope": envelope, "editor_fix_and_preserve_plan": plan,
            "editor_binding_fingerprint": editor_binding["binding_fingerprint"], "authority": False}


def generation_instruction(instruction: str, repair: dict[str, Any]) -> str:
    return instruction + (
        "\nThis is a REVISE run. Apply the Editor-selected owning repair and preserve the exact authorized objectives. "
        "All scene/action reconstructions remain non-Canon proposals. For local repair, do not replace the incumbent's "
        "working story merely because a reconstruction proposes an alternative. Return only this stage's normal output. "
        "Repair constraints: " + canonical_json({key: repair[key] for key in ("policy", "objective_envelope", "editor_fix_and_preserve_plan")})
    )


def writer_context(source: dict[str, Any], repair: dict[str, Any], frozen_stage: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(repair)
    result["authority_constraints"] = deepcopy(source["source_request"]["rule_material"])
    if repair["policy"]["generation_mode"] == "fresh_realization":
        result["reconstructed_current_story_state"] = deepcopy(frozen_stage)
    else:
        result["bounded_repair_evidence"] = {
            "candidate_fingerprint": source["candidate_fingerprint"], "candidate_text": source["candidate_text"],
        }
    return result


def candidate_lineage(source: dict[str, Any], run: dict[str, Any], candidate_text: str, repair: dict[str, Any]) -> dict[str, Any]:
    evolution_run_id, nodes = prior_lineage(source)
    parent = nodes[-1]["candidate_id"]
    origin = "fresh_regeneration" if repair["policy"]["generation_mode"] == "fresh_realization" else "repair"
    prose_parent = parent if origin == "repair" else None
    validate_derivation(origin=origin, comparison_parent_candidate_id=parent, prose_parent_candidate_id=prose_parent)
    nodes.append({"candidate_id": _candidate_id(run["run_id"]), "candidate_fingerprint": fingerprint_text(candidate_text),
                  "created_by_run_id": run["run_id"], "origin": origin,
                  "comparison_parent_candidate_id": parent, "prose_parent_candidate_id": prose_parent})
    result = {"schema": LINEAGE_SCHEMA, "evolution_run_id": evolution_run_id, "nodes": nodes,
              "source_fingerprint": source["source_fingerprint"], "editor_binding_fingerprint": repair["editor_binding_fingerprint"],
              "objective_envelope_fingerprint": repair["objective_envelope"]["fingerprint"], "authority": False}
    result["lineage_fingerprint"] = fingerprint(result)
    return result


def comparison_payload(source: dict[str, Any], run: dict[str, Any], candidate_text: str, repair: dict[str, Any], lineage: dict[str, Any]) -> dict[str, Any]:
    return {
        "evolution_run_id": lineage["evolution_run_id"], "evolution_subject_id": source["source_target_context"]["document_id"],
        "comparison_id": "repair:" + run["run_id"],
        "incumbent": {"candidate_id": lineage["nodes"][-2]["candidate_id"],
                      "content_fingerprint": source["candidate_fingerprint"], "text": source["candidate_text"]},
        "challenger": {"candidate_id": lineage["nodes"][-1]["candidate_id"],
                       "content_fingerprint": fingerprint_text(candidate_text), "text": candidate_text,
                       "repair_owner": repair["policy"]["repair_owner"]},
        "repair_context": {"repair_target": repair["editor_fix_and_preserve_plan"]["fix"],
                           "objective_envelope": repair["objective_envelope"],
                           "repair_evidence_refs": [source["source_checkpoint_id"], source["source_fingerprint"]],
                           "incumbent_strengths": repair["editor_fix_and_preserve_plan"]["preserve"]},
    }
