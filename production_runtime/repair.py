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


def author_direction_evidence(
    instruction: str, repair: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Expose exact chronological author directions for model-owned projection."""

    if repair is None:
        return [{
            "source_ref": "current-production-request",
            "chronology": 0,
            "statement": instruction,
        }]
    envelope = repair["objective_envelope"]
    directions = [
        item for item in envelope["objective_items"]
        if item.get("category") == "user_direction"
    ]
    return [
        {
            "source_ref": item["source_refs"][0],
            "chronology": index,
            "statement": item["statement"],
        }
        for index, item in enumerate(directions)
    ]


def materialize_author_objectives(
    evidence: list[dict[str, Any]], projected_items: Any
) -> dict[str, Any]:
    """Bind the composer's semantic projection to exact author evidence."""

    if not isinstance(evidence, list) or not evidence:
        raise ProductionRunError("author_objectives_invalid", "author direction evidence is missing")
    if not isinstance(projected_items, list) or not projected_items:
        raise ProductionRunError("author_objectives_invalid", "author objective projection is missing")
    available = {item["source_ref"] for item in evidence}
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for item in projected_items:
        if not isinstance(item, dict) or set(item) != {
            "objective_id", "statement", "source_refs", "hard"
        }:
            raise ProductionRunError("author_objectives_invalid", "author objective fields changed")
        objective_id = item.get("objective_id")
        refs = item.get("source_refs")
        if (
            not isinstance(objective_id, str)
            or not objective_id.strip()
            or objective_id in seen
            or not isinstance(item.get("statement"), str)
            or not item["statement"].strip()
            or item.get("hard") is not True
            or not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or any(ref not in available for ref in refs)
        ):
            raise ProductionRunError(
                "author_objectives_invalid",
                "author objective does not bind exact current direction evidence",
            )
        seen.add(objective_id)
        items.append(deepcopy(item))
    value = {
        "schema": "quillframe_current_author_objectives_v1",
        "items": items,
        "source_fingerprint": fingerprint(evidence),
        "priority": "current_explicit_author_direction",
        "authority": False,
    }
    value["objectives_fingerprint"] = fingerprint(value)
    return value


def author_objective_projection(
    instruction: str, repair: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Project current explicit author directions without plans or critique."""
    if repair is None:
        items = [{
            "objective_id": "OBJ-CURRENT-REQUEST",
            "statement": instruction,
            "source_refs": ["current-production-request"],
            "hard": True,
        }]
        source_fingerprint = fingerprint({"instruction": instruction})
    else:
        envelope = repair["objective_envelope"]
        items = [
            {
                "objective_id": item["id"],
                "statement": item["statement"],
                "source_refs": deepcopy(item["source_refs"]),
                "hard": True,
            }
            for item in envelope["objective_items"]
            if item.get("category") == "user_direction"
        ]
        source_fingerprint = envelope["fingerprint"]
    value = {
        "schema": "quillframe_current_author_objectives_v1",
        "items": items,
        "source_fingerprint": source_fingerprint,
        "priority": "current_explicit_author_direction",
        "authority": False,
    }
    value["objectives_fingerprint"] = fingerprint(value)
    return value


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
    targets = deepcopy(judgment["targets"])
    candidate_text = editor_binding["job"]["input"]["payload"]["candidate_text"]
    for target in targets:
        if target["evidence_quote"] not in candidate_text:
            raise ProductionRunError("repair_target_invalid", "repair evidence quote is not in the exact source candidate")
        window = target.get("edit_window_quote")
        if isinstance(window, str) and window not in candidate_text:
            raise ProductionRunError("repair_target_invalid", "bounded edit window is not in the exact source candidate")
    policy = evaluate_repair_policy({"repair_owner": judgment["repair_owner"], "revision_route": judgment["revision_route"],
                                     "targets": targets, "generation_mode": judgment["generation_mode"],
                                     "candidate_rejected": source_kind != "author_revision",
                                     "author_revision_requested": source_kind == "author_revision"})
    # Do not forward reports, evidence quotes, context-strategy explanations, or
    # the complete critique trajectory to a fresh Writer.
    plan = {key: deepcopy(judgment[key]) for key in ("fix", "preserve", "targets")}
    if policy["generation_mode"] == "local_or_bounded_repair":
        plan["repair_plan"] = judgment["repair_plan"]
    return {"policy": policy, "objective_envelope": envelope, "editor_fix_and_preserve_plan": plan,
            "editor_binding_fingerprint": editor_binding["binding_fingerprint"], "authority": False}


def generation_instruction(instruction: str, repair: dict[str, Any]) -> str:
    # The full objective envelope is already present in the writer context.
    # Repeating it in the instruction can add tens of thousands of input
    # tokens on a REVISE run without giving the Writer any new authority.
    instruction_constraints = {
        "revision_route": repair["policy"]["revision_route"],
        "generation_mode": repair["policy"]["generation_mode"],
        "objective_envelope_fingerprint": repair["objective_envelope"]["fingerprint"],
        "fix": repair["editor_fix_and_preserve_plan"]["fix"],
        "preserve": repair["editor_fix_and_preserve_plan"]["preserve"],
    }
    return instruction + (
        "\nREVISE: apply the model-selected route and preserve the bound author objectives. "
        "Return only this stage's normal output. Constraints: " + canonical_json(instruction_constraints)
    )


def _authority_constraint_bindings(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Bind frozen rule material without repeating every full document to Writer."""
    bindings = []
    for item in source["source_request"]["rule_material"]:
        statement = item.get("statement") if isinstance(item, dict) else None
        if not isinstance(statement, str) or not statement:
            raise ProductionRunError(
                "repair_authority_constraint_invalid",
                "repair source rule material requires a non-empty statement",
            )
        binding = {
            key: deepcopy(item[key])
            for key in ("id", "authority", "exceptions")
            if key in item
        }
        binding.update({
            "statement_fingerprint": fingerprint_text(statement),
            "statement_utf8_bytes": len(statement.encode("utf-8")),
        })
        bindings.append(binding)
    return bindings


def writer_context(
    source: dict[str, Any], repair: dict[str, Any], frozen_stage: dict[str, Any],
) -> dict[str, Any]:
    policy = repair["policy"]
    result = {
        "schema": "quillframe_writer_repair_context_v1",
        "repair_owner": policy["repair_owner"],
        "revision_route": policy["revision_route"],
        "generation_mode": policy["generation_mode"],
        "objective_envelope_fingerprint": repair["objective_envelope"]["fingerprint"],
        "editor_binding_fingerprint": repair["editor_binding_fingerprint"],
        "authority": False,
    }
    # Generic framework documents and active plans have already been consumed
    # by the frozen source, Editor, objective envelope, stage guidance and later
    # semantic gates. Keep their exact identities auditable, but do not resend
    # the same full documents to both prose stages.
    result["authority_constraint_bindings"] = _authority_constraint_bindings(source)
    if policy["generation_mode"] == "fresh_realization":
        result["reconstructed_current_story_state"] = {
            "source": "scene_realization_contract",
            "context_bundle_fingerprint": frozen_stage["context_bundle_fingerprint"],
            "freeze_fingerprint": frozen_stage["freeze_fingerprint"],
        }
        result["fresh_context_exclusions"] = list(policy["excluded_writer_context_classes"])
    else:
        windows = [
            {
                "target_id": target["target_id"],
                "scene_ref": target.get("scene_ref"),
                "evidence_quote": target["evidence_quote"],
                "edit_window_quote": target["edit_window_quote"],
                "edit_window_fingerprint": fingerprint_text(target["edit_window_quote"]),
            }
            for target in policy["targets"]
            if target["route"] == "local_edit"
        ]
        evidence = {
            "candidate_fingerprint": source["candidate_fingerprint"],
            "bounded_edit_windows": windows,
            "full_candidate_visible": False,
        }
        result["bounded_repair_evidence"] = evidence
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
