from __future__ import annotations

import json
import sys
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent_runtime import AgentBudget, AgentJob, AgentResult
from harness.context_runtime import canonical_json, fingerprint
from model_runtime.structured_output import required_only_output_schema, validate_output_schema, validate_structured_text

from .contracts import ProductionRunError, assert_secret_free, parse_json_object, validate_bundle_integrity
from .reading_positioning import reading_positioning_fields
from .sources import AgentRuntimeLike

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_ROOT = ROOT / "harness" / "semantic_workers"
QUALITY_ROOT = ROOT / "quality"
for runtime_root in (SEMANTIC_ROOT, QUALITY_ROOT):
    if str(runtime_root) not in sys.path:
        sys.path.insert(0, str(runtime_root))

from peer_bridge_receipt import validate_receipt as validate_peer_bridge_receipt  # noqa: E402
from independent_invocation_receipt import (  # noqa: E402
    SCHEMA as INDEPENDENT_INVOCATION_RECEIPT_SCHEMA,
    validate_receipt as validate_independent_invocation_receipt,
)
from peer_chat_relay import build as build_peer_packet, validate_peer_result  # noqa: E402
from registered_contract_binding import validate_registered_job  # noqa: E402
from semantic_worker_router import (  # noqa: E402
    _character_evidence_rows,
    load_contract_registry,
    make_contract_job,
    resolve_contract_registry,
    validate_contract_input,
    validate_result,
    validate_typed_value,
    worker_job_view,
)

from quality.candidate_qualification import evaluate as evaluate_qualification  # noqa: E402
from quality.candidate_qualification import evaluate_recorded as evaluate_recorded_qualification  # noqa: E402
from quality.candidate_qualification import validate_qualification_receipt  # noqa: E402
from quality.production_readiness import evaluate as evaluate_production_readiness  # noqa: E402
from quality.production_release import aggregate as aggregate_production_release  # noqa: E402
from quality.reader_expectation import FINAL as FINAL_EXPECTATION_STATUSES, STATUSES as EXPECTATION_STATUSES  # noqa: E402


def _reader_expectation_output_profile(
    contract: dict[str, Any], payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Narrow new transport jobs to operations on the exact frozen ledger.

    The registered contract and original model judgment remain unchanged.
    Every branch is a complete strict subset; optional deadlines use separate
    with/without-field branches, never a new nullable output convention.
    """
    live = []
    seen = set()
    rows = payload["existing_expectations"]
    for index, row in enumerate(rows):
        identity, version, status = row.get("expectation_id"), row.get("version"), row.get("status")
        if (not isinstance(identity, str) or not identity.strip() or identity in seen
                or not isinstance(version, int) or isinstance(version, bool) or version < 1
                or not isinstance(status, str) or status not in EXPECTATION_STATUSES):
            raise ValueError(f"existing_expectations[{index}]: expected a unique exact id, positive integer version and known status")
        seen.add(identity)
        if status not in FINAL_EXPECTATION_STATUSES:
            live.append({"expectation_id": identity, "expected_version": version})
    live.sort(key=lambda row: row["expectation_id"])

    schema = required_only_output_schema(contract)
    update = schema["properties"]["expectation_updates"]["items"]
    deadline = contract["properties"]["expectation_updates"]["items"]["properties"]["due_by_order"]
    operations = [operation for operation in update["properties"]["operation"]["enum"] if operation != "open"]
    branches = []

    def add_branches(allowed: list[str], version: int, identities: list[str] | None = None) -> None:
        branch = deepcopy(update)
        branch["properties"]["operation"]["enum"] = allowed
        branch["properties"]["expected_version"]["enum"] = [version]
        if identities is not None:
            branch["properties"]["expectation_id"]["enum"] = identities
        branches.append(branch)
        with_deadline = deepcopy(branch)
        with_deadline["properties"]["due_by_order"] = deepcopy(deadline)
        with_deadline["required"].append("due_by_order")
        branches.append(with_deadline)

    add_branches(["open"], 0)
    # Group only identical versions. Independent id/version enums would admit
    # a wrong cross-product; grouping avoids it without truncating the ledger.
    by_version: dict[int, list[str]] = {}
    for row in live:
        by_version.setdefault(row["expected_version"], []).append(row["expectation_id"])
    for version in sorted(by_version):
        add_branches(operations, version, by_version[version])
    schema["properties"]["expectation_updates"]["items"] = {"anyOf": branches}
    validate_output_schema(schema)
    return schema, {
        "source": "registered_semantic_job.input.payload.existing_expectations",
        "source_fingerprint": fingerprint(rows),
        "new_expectation": {"operation": "open", "expected_version": 0},
        "existing_operations": operations,
        "live_existing_expectations": live,
    }


class RegisteredSemanticExecutor:
    """Run non-independent registered semantic contracts through Model Service.

    This adapter never executes `quality.production_review`; that contract is
    deliberately reserved for the external independent handoff path below.
    """

    def __init__(self, agent_runtime: AgentRuntimeLike, *, invoke: Callable[[AgentJob], AgentResult] | None = None) -> None:
        self.agent_runtime = agent_runtime
        self.invoke = invoke or agent_runtime.run

    def execute(
        self,
        *,
        run: dict[str, Any],
        service_id: str,
        contract_id: str,
        subject_id: str,
        payload: dict[str, Any],
        model_preference: str | None,
        runtime_role: str,
        max_output_tokens: int = 4200,
    ) -> dict[str, Any]:
        if contract_id == "quality.production_review":
            raise ProductionRunError(
                "independent_review_external_required",
                "quality.production_review must be dispatched through the independent peer handoff, not the manager Model Service",
            )
        assert_secret_free(payload, label=f"registered semantic payload {contract_id}")
        try:
            semantic_job = make_contract_job(
                contract_id,
                subject_id,
                payload,
                source_session_id=str(run.get("session_id") or f"session:{run['run_id']}"),
                handoff_id=f"{run['run_id']}:{contract_id}",
            )
        except ValueError as exc:
            raise ProductionRunError("semantic_contract_invalid", str(exc)) from exc
        # A resumed registered call must reconstruct the same exact visible job.
        # The semantic fingerprint excludes timestamps, but AgentJob correctly
        # binds every byte it sends, including this creation metadata.
        if isinstance(run.get("created_at"), str):
            semantic_job["created_at"] = run["created_at"]
        return self.execute_prepared(
            semantic_job=semantic_job, run=run, service_id=service_id,
            model_preference=model_preference, runtime_role=runtime_role,
            max_output_tokens=max_output_tokens,
        )

    def execute_prepared(
        self,
        *,
        semantic_job: dict[str, Any],
        run: dict[str, Any],
        service_id: str,
        model_preference: str | None,
        runtime_role: str,
        max_output_tokens: int = 4200,
    ) -> dict[str, Any]:
        """Execute an already persisted registered job without rebuilding it."""
        if not isinstance(semantic_job, dict):
            raise ProductionRunError("semantic_contract_invalid", "registered semantic job must be an object")
        semantic_job = deepcopy(semantic_job)
        contract_id = semantic_job.get("input", {}).get("model_contract_id") if isinstance(semantic_job.get("input"), dict) else None
        if contract_id == "quality.production_review":
            raise ProductionRunError(
                "independent_review_external_required",
                "quality.production_review must be dispatched through the independent peer handoff, not the manager Model Service",
            )
        binding_errors = validate_registered_job(semantic_job)
        if binding_errors:
            raise ProductionRunError("semantic_contract_invalid", "; ".join(binding_errors))
        assert_secret_free(semantic_job["input"]["payload"], label=f"registered semantic payload {contract_id}")

        visible_job = worker_job_view(semantic_job)
        instruction = (
            "Execute exactly the registered Quillframe semantic contract supplied in context. "
            "Judge only its bounded payload and rubric. Return ONLY the judgment JSON object matching output_contract. "
            "Do not expose chain-of-thought, private reasoning, credentials, Canon writes, Framework writes, or user-taste writes."
        )
        context = [{"registered_semantic_job": visible_job}]
        output_schema = None
        # Explicitly reviewed transport profiles, not inferred from prompt text.
        # The full registered contracts, versions and historical bindings remain
        # unchanged. Only newly dispatched AgentJobs carry this narrower shape.
        if contract_id in {"character.action_propose", "scene.resolve_actions"}:
            try:
                output_schema = required_only_output_schema(semantic_job["output_contract"])
                if contract_id == "character.action_propose":
                    # These are response bindings to the supplied baseline,
                    # not Python-selected motives or constraints on an action.
                    for field in ("character_id", "active_agenda"):
                        output_schema["properties"][field]["enum"] = [semantic_job["input"]["payload"][field]]
                    validate_output_schema(output_schema)
            except ValueError as exc:
                raise ProductionRunError("semantic_output_schema_unsupported", str(exc)) from exc
            instruction += (
                " This invocation uses the native required-only output profile: emit only output_contract required fields, recursively. "
                "Do not fill optional slots or invent null placeholders. Preserve all applicable semantic findings and repair routes. "
                "For character proposals, include relevant motive, tactic, resistance or cost in the free-text action when useful."
            )
        if contract_id == "character.action_propose":
            # Derive this index from the validator's exact canonical paths,
            # without changing the persisted job or extending reference authority.
            context[0]["eligible_evidence_ids"] = [
                evidence_id for evidence_id, _ in _character_evidence_rows(semantic_job["input"]["payload"])
            ]
            instruction += (
                " Copy character_id and active_agenda exactly from the supplied payload, including punctuation and whitespace. "
                "These two echo fields bind this response to the frozen input baseline, which may have been proposed by the preceding AI stage; "
                "they do not make that baseline permanent Canon or prescribe the character's choice. "
                "Judge the action semantically: proposals.action may express hesitation, resistance, a changed tactic or a supported side objective. "
                "Do not paraphrase the echo fields to express that judgment or mechanically repeat them in the action. "
                " In every proposal.knowledge_basis, cite only eligible_evidence_ids from the supplied index. "
                "Use each evidence_id at most once per proposal, even if it has several implications; choose one use. "
                "Do not treat IDs in any other field as reference authority. An empty knowledge_basis is allowed when no indexed evidence was used."
            )
        elif contract_id == "narrative.world":
            context[0]["writable_field_contracts"] = narrative_field_contracts(semantic_job["output_contract"])
            instruction += (
                " For each narrative change, use exactly the writable_field_contracts entry for its entity_type. "
                "Return all and only that schema's required fields, with the declared types. "
                "Existing source_metadata and source_fingerprint are read-only provenance; never copy them into replacement fields. "
                "Keep the exact entity_ref outside fields and cite an exact quote from the final candidate."
            )
        elif contract_id == "reader.expectations":
            try:
                output_schema, operation_constraints = _reader_expectation_output_profile(
                    semantic_job["output_contract"], semantic_job["input"]["payload"],
                )
            except ValueError as exc:
                raise ProductionRunError("semantic_output_schema_unsupported", str(exc)) from exc
            context[0]["reader_expectation_operation_constraints"] = operation_constraints
            instruction += (
                " Use reader_expectation_operation_constraints as the exact frozen ledger identity/version boundary. "
                "When live_existing_expectations is empty, only open with expected_version 0 or an empty expectation_updates array is legal. "
                "Every touch, partial, paid or abandoned operation must copy an exact live id/version pair from that list; terminal entries cannot be updated. "
                "An open operation uses a local label that Core will replace, not an existing ledger identity. "
                "Do not chain open and then touch, partial, paid or abandoned within this observation: newly opened labels are not supplied live entries. "
                "An issue introduced and fully resolved within this chapter does not invent a historical ledger row or justify paid/version 0. "
                "Only propose supported changes to supplied live expectations or supported new live expectations; an empty array is valid. "
                "Return at most one update per existing id. Omit due_by_order when unsupported, never fill null; "
                "for an open operation, a supplied deadline must be at least current_reading_order."
            )
        agent_job = AgentJob(
            job_id=f"agent_{semantic_job['job_id']}",
            session_id=str(run.get("session_id") or f"session:{run['run_id']}"),
            run_id=str(run["run_id"]),
            task_mode=str(run["task_mode"]),
            runtime_role=runtime_role,
            service_id=service_id,
            instruction=instruction,
            context=context,
            tool_grants=set(),
            model_preference=model_preference,
            required_model_capabilities={"text"},
            authority={},
            budgets=AgentBudget(
                max_steps=1,
                max_model_requests=1,
                max_tool_calls=1,
                max_parallel_tool_calls=1,
                max_output_tokens_per_request=max_output_tokens,
                max_total_tokens=64_000,
                max_elapsed_ms=180_000,
            ),
            idempotency_key=f"{run['run_id']}:registered:{contract_id}:{semantic_job['input_fingerprint']}",
            output_schema=output_schema,
        )
        result = self.invoke(agent_job)
        if result.status != "completed":
            raise ProductionRunError(
                "semantic_pending",
                f"registered semantic contract {contract_id} did not complete",
                detail={"agent_status": result.status, "errors": result.errors},
            )
        if output_schema is not None:
            try:
                judgment = validate_structured_text(result.final_text, output_schema)
            except (ValueError, TypeError, RecursionError) as exc:
                raise ProductionRunError("semantic_output_invalid", f"{contract_id}: {exc}") from exc
        else:
            judgment = parse_json_object(result.final_text, label=contract_id)
        semantic_result = {
            "job_id": semantic_job["job_id"],
            "subject_id": semantic_job["subject_id"],
            "kind": semantic_job["kind"],
            "input_fingerprint": semantic_job["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": "quillframe_model_service",
                "model_or_reviewer": result.model_id,
                "model_service_id": result.model_service_id,
                "protocol": result.protocol,
                "agent_job_id": agent_job.job_id,
                "agent_input_fingerprint": agent_job.input_fingerprint,
            },
            "judgment": judgment,
            "proposals": [],
            "errors": [],
            "execution": {
                "source_session_id": semantic_job.get("execution", {}).get("source_session_id"),
                "handoff_id": semantic_job.get("execution", {}).get("handoff_id"),
            },
        }
        result_errors = validate_result(semantic_job, semantic_result)
        if result_errors:
            raise ProductionRunError("semantic_output_invalid", "; ".join(result_errors))
        return {
            "contract_id": contract_id,
            "job": semantic_job,
            "result": semantic_result,
            "binding_fingerprint": fingerprint({"job": semantic_job, "result": semantic_result}),
            "authority": False,
        }


CHARACTER_EVIDENCE_FIELDS = (
    ("immediate_situation", "observables", "observable_id"),
    ("perspective_memory", "episodic_visible_events", "event_id"),
    ("perspective_memory", "visibility_tagged_facts", "fact_id"),
    ("perspective_memory", "situation_patterns", "pattern_id"),
)


def _character_contract() -> dict[str, Any]:
    path, _ = resolve_contract_registry("character.action_propose")
    return load_contract_registry(path)["contracts"]["character.action_propose"]


def character_state_prepare_contract() -> dict[str, Any]:
    """Disclose and enforce the canonical containers before any action call."""
    character = deepcopy(_character_contract()["input_contract"])
    character["properties"] = {key: value for key, value in character["properties"].items() if key in character["required"]}
    # New cast has no accepted state to preserve. Keep its qualitative current
    # perception separate from the typed observations and memories it may cite.
    character["properties"]["perceived_state"] = {
        "type": "object", "properties": {"summary": {"type": "string"}}, "additionalProperties": False,
    }
    for name in ("immediate_situation", "perspective_memory"):
        container = character["properties"][name]
        container["required"] = list(container["properties"])
        container["additionalProperties"] = False
    return {
        "type": "object", "required": ["status", "characters", "summary", "findings"],
        "properties": {
            "status": {"enum": ["pass", "fail"]},
            "characters": {"type": "array", "maxItems": 12, "items": character},
            "summary": {"type": "string"}, "findings": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }


def _project_character_action_payload(payload: dict[str, Any], *, order: int, error_code: str) -> dict[str, Any]:
    """Filter canonical evidence by time; never repair aliases or invent refs."""
    projected = deepcopy(payload)
    if (not isinstance(projected.get("current_story_order"), int)
            or isinstance(projected["current_story_order"], bool) or projected["current_story_order"] != order):
        raise ProductionRunError(error_code, "character input changed the frozen story-time cutoff")
    paths = {(container, field): id_key for container, field, id_key in CHARACTER_EVIDENCE_FIELDS}
    reserved = set(paths.values()) | {"available_from_story_order"}

    def check_locations(value: Any, path: tuple = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in reserved and (len(path) != 3 or path[:2] not in paths or not isinstance(path[2], int)
                                        or key not in {paths[path[:2]], "available_from_story_order"}):
                    raise ProductionRunError(error_code, "character evidence must use the canonical observation and memory arrays")
                check_locations(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check_locations(child, (*path, index))

    check_locations(projected)
    for container, field, _ in CHARACTER_EVIDENCE_FIELDS:
        state = projected.get(container)
        if not isinstance(state, dict) or not isinstance(state.get(field, []), list):
            raise ProductionRunError(error_code, "character evidence containers must be objects with typed arrays")
        state[field] = [row for row in state.get(field, []) if isinstance(row, dict)
                        and isinstance(row.get("available_from_story_order"), int)
                        and not isinstance(row["available_from_story_order"], bool)
                        and 0 <= row["available_from_story_order"] <= order]
    errors = validate_contract_input("character.action_propose", _character_contract(), projected)
    if errors:
        raise ProductionRunError(error_code, "; ".join(errors))
    return projected


def prepared_character_action_payloads(judgment: dict[str, Any], target_context: dict[str, Any]) -> list[dict[str, Any]]:
    errors = validate_typed_value(judgment, character_state_prepare_contract())
    if errors:
        raise ProductionRunError("semantic_output_invalid", "character preparation output_contract: " + "; ".join(errors))
    ids = [value["character_id"] for value in judgment["characters"]]
    if len(ids) != len(set(ids)):
        raise ProductionRunError("semantic_output_invalid", "proposed characters require unique identities")
    return [_project_character_action_payload(value, order=target_context["current_story_order"], error_code="semantic_output_invalid")
            for value in judgment["characters"]]


def character_action_payloads(frozen_stage: dict[str, Any], target_context: dict[str, Any]) -> list[dict[str, Any]]:
    """Project one character's own frozen evidence, never another actor's state.

    This function enforces identity/time eligibility only. The registered worker
    still decides motivation, inference, action and the usefulness of evidence.
    """
    order = target_context.get("current_story_order")
    if not isinstance(order, int) or isinstance(order, bool) or order < 0:
        raise ProductionRunError("target_context_missing", "character simulation requires the frozen story-time cutoff")
    items = frozen_stage.get("items", [])
    characters = [row for row in items if row.get("object_type") == "character"]
    if len(characters) > 12:
        raise ProductionRunError("character_simulation_budget", "selected character count exceeds the bounded simulation budget of 12")
    payloads: list[dict[str, Any]] = []
    for row in characters:
        view = row["model_view"]
        character_id = view.get("character_id")
        agenda = view.get("agenda")
        if not isinstance(character_id, str) or not character_id or not isinstance(agenda, str) or not agenda.strip():
            raise ProductionRunError("character_state_incomplete", "selected character needs an explicit identity and active agenda")
        state = view.get("state") if isinstance(view.get("state"), dict) else {}
        perceived = deepcopy(state.get("perceived_state", state))
        if not isinstance(perceived, dict):
            raise ProductionRunError("character_state_incomplete", "character perceived_state must be an object")
        situation = deepcopy(state.get("immediate_situation") or {})
        memory = deepcopy(state.get("perspective_memory") or {})
        if not isinstance(situation, dict) or not isinstance(memory, dict):
            raise ProductionRunError("character_state_incomplete", "character situation and perspective memory must be objects")
        # Stored private state may include future entries; it is not a bypass of
        # the same cutoff applied to the canonical knowledge table.
        for container, field in ((situation, "observables"), (memory, "episodic_visible_events"),
                                 (memory, "visibility_tagged_facts"), (memory, "situation_patterns")):
            values = container.get(field, [])
            if not isinstance(values, list):
                raise ProductionRunError("character_state_incomplete", f"{field} must be an array")
            container[field] = [deepcopy(value) for value in values if isinstance(value, dict)
                                and isinstance(value.get("available_from_story_order"), int)
                                and not isinstance(value["available_from_story_order"], bool)
                                and 0 <= value["available_from_story_order"] <= order]
        # Do not duplicate unfiltered memory/situation inside perceived_state.
        for field in ("immediate_situation", "perspective_memory"):
            perceived.pop(field, None)
        facts = memory["visibility_tagged_facts"]
        seen = {fact.get("fact_id") for fact in facts}
        for evidence in items:
            if evidence.get("object_type") != "character_knowledge":
                continue
            known = evidence["model_view"]
            available = known.get("available_from_story_order")
            if known.get("character_id") != character_id or not isinstance(available, int) or isinstance(available, bool) or not 0 <= available <= order:
                continue
            fact_id = known.get("knowledge_id")
            if not isinstance(fact_id, str) or not fact_id or fact_id in seen:
                continue
            claim = known.get("fact")
            facts.append({
                "fact_id": fact_id, "claim": claim if isinstance(claim, str) else canonical_json(claim),
                "source_ref": str(known.get("evidence_ref") or evidence["object_id"]),
                "available_from_story_order": available,
            })
            seen.add(fact_id)
        payloads.append(_project_character_action_payload({
            "character_id": character_id, "current_story_order": order, "active_agenda": agenda,
            "perceived_state": perceived, "immediate_situation": situation, "perspective_memory": memory,
        }, order=order, error_code="character_state_incomplete"))
    return payloads


def writer_safe_projection(binding: dict[str, Any], *, scene_id: str) -> dict[str, Any]:
    result = binding["result"]["judgment"]
    if result.get("scene_id") != scene_id:
        raise ProductionRunError("semantic_output_invalid", "realization projection changed the frozen scene identity")
    # Whitelist the registered output. Neither the private job nor action input
    # nor an entire character sheet is a Writer artifact.
    projection = {key: deepcopy(result[key]) for key in (
        "scene_id", "interaction_trace", "writer_context", "observable_event_refs", "unresolved_pressures"
    ) if key in result}
    projection["source_binding_fingerprint"] = binding["binding_fingerprint"]
    projection["projection_fingerprint"] = fingerprint(projection)
    projection["authority"] = False
    return projection


NARRATIVE_SOURCE_TYPES = {"character": "character", "relationship": "relationship", "world_fact": "world",
                          "timeline_event": "timeline", "character_knowledge": "knowledge"}


def narrative_field_contracts(output_contract: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """The registered schema owns projection, model instructions and validation."""
    if output_contract is None:
        path, _ = resolve_contract_registry("narrative.world")
        output_contract = load_contract_registry(path)["contracts"]["narrative.world"]["output_contract"]
    return {branch["properties"]["entity_type"]["enum"][0]: deepcopy(branch["properties"]["fields"])
            for branch in output_contract["properties"]["changes"]["items"]["oneOf"]}


def narrative_before_fingerprint(conn, entity_type: str, entity_id: str) -> str:  # noqa: ANN001
    """Fingerprint the same physical source view used by Context Runtime."""
    tables = {"character": ("characters", "character_id"), "relationship": ("relationships", "relationship_id"),
              "world": ("world_entities", "entity_id"), "timeline": ("timeline_events", "event_id"),
              "knowledge": ("character_knowledge", "knowledge_id")}
    if entity_type not in tables:
        raise ProductionRunError("narrative_proposal_invalid", "unknown narrative entity type")
    table, key = tables[entity_type]
    row = conn.execute(f"SELECT * FROM {table} WHERE {key}=?", (entity_id,)).fetchone()
    if row is None:
        return "absent"
    row = dict(row)
    if entity_type == "character":
        view = {key: entity_id, "name": row["name"], "agenda": row["agenda"], "voice_notes": row["voice_notes"], "state": json.loads(row["state_json"])}
    elif entity_type == "relationship":
        view = {key: entity_id, "participant_a": row["participant_a"], "participant_b": row["participant_b"],
                "relationship_type": row["relationship_type"], "state": json.loads(row["state_json"])}
    elif entity_type == "world":
        view = {key: entity_id, "entity_type": row["entity_type"], "name": row["name"], "truth": json.loads(row["truth_json"])}
    elif entity_type == "timeline":
        view = {key: entity_id, "story_order": row["story_order"], "title": row["title"], "description": row["description"], "source_ref": row["source_ref"]}
    else:
        view = {key: entity_id, "character_id": row["character_id"], "claim_ref": row["claim_ref"], "fact": json.loads(row["fact_json"]),
                "available_from_story_order": row["available_from_story_order"], "evidence_ref": row["evidence_ref"], "confidence": row["confidence"]}
    return fingerprint(view)


def narrative_existing_state(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    contracts = narrative_field_contracts()
    existing = []
    for row in bundle["source_payloads"].values():
        if row["object_type"] not in NARRATIVE_SOURCE_TYPES:
            continue
        kind = NARRATIVE_SOURCE_TYPES[row["object_type"]]
        source = row["model_view"]
        required = set(contracts[kind]["required"])
        if not required.issubset(source):
            raise ProductionRunError("narrative_source_invalid", "frozen narrative source is missing required writable fields")
        existing.append({
            "entity_ref": row["object_id"], "entity_type": kind, "source_fingerprint": row["source_fingerprint"],
            "fields": {key: deepcopy(value) for key, value in source.items() if key in required},
            "source_metadata": {key: deepcopy(value) for key, value in source.items() if key not in required},
        })
    return existing


def build_narrative_state_proposal(binding: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    validate_bundle_integrity(bundle)
    if binding.get("contract_id") != "narrative.world" or binding.get("authority") is not False:
        raise ProductionRunError("narrative_proposal_invalid", "registered narrative.world binding is required")
    job, result = binding.get("job"), binding.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict) or binding.get("binding_fingerprint") != fingerprint({"job": job, "result": result}):
        raise ProductionRunError("narrative_proposal_invalid", "narrative binding fingerprint does not match")
    errors = validate_registered_job(job) + validate_result(job, result)
    if errors or job.get("input", {}).get("model_contract_id") != "narrative.world" or result.get("status") != "completed":
        raise ProductionRunError("narrative_proposal_invalid", "; ".join(errors) or "narrative observation is not completed")
    payload = job["input"]["payload"]
    from persistence.quillframe_sqlite import fingerprint_text
    if fingerprint_text(payload["candidate_text"]) != payload["candidate_fingerprint"]:
        raise ProductionRunError("narrative_proposal_invalid", "narrative candidate fingerprint does not match")
    target = bundle["target_context"]
    if any(payload[key] != target[key] for key in ("chapter_id", "document_id", "current_story_order")):
        raise ProductionRunError("narrative_proposal_invalid", "narrative output changed the frozen target")
    existing_state = narrative_existing_state(bundle)
    if payload["existing_state"] != existing_state:
        raise ProductionRunError("narrative_proposal_invalid", "narrative source projection changed")
    existing = {item["entity_ref"]: item for item in existing_state}
    field_contracts = narrative_field_contracts(job["output_contract"])
    raw_changes = result["judgment"]["changes"]
    refs = [item["entity_ref"] for item in raw_changes]
    if len(refs) != len(set(refs)):
        raise ProductionRunError("narrative_proposal_invalid", "a narrative proposal cannot change an entity twice")
    resolved = {}
    kinds = {key: value["entity_type"] for key, value in existing.items()}
    for change in raw_changes:
        ref = change["entity_ref"]
        kind = change["entity_type"]
        if ref.startswith("local:") and len(ref) > len("local:"):
            resolved[ref] = "NARR-" + fingerprint({"candidate_fingerprint": payload["candidate_fingerprint"], "entity_type": kind, "local_ref": ref})[7:31]
            kinds[ref] = kind
        elif ref not in existing or existing[ref]["entity_type"] != kind:
            raise ProductionRunError("narrative_proposal_invalid", "existing narrative entity is not in the frozen source projection")
        else:
            resolved[ref] = ref
    changes = []
    for raw in raw_changes:
        kind, ref = raw["entity_type"], raw["entity_ref"]
        value = deepcopy(raw["fields"])
        field_contract = field_contracts[kind]
        if set(value) != set(field_contract["required"]):
            raise ProductionRunError("narrative_proposal_invalid", f"{kind} fields must match the typed state contract")
        field_errors = validate_typed_value(value, field_contract, f"$.{kind}.fields")
        if field_errors:
            raise ProductionRunError("narrative_proposal_invalid", "; ".join(field_errors))
        for key in ("story_order", "available_from_story_order"):
            if key in value and not 0 <= value[key] <= target["current_story_order"]:
                raise ProductionRunError("narrative_proposal_invalid", "narrative proposal cannot establish future story facts")
        for key in ("participant_a", "participant_b", "character_id"):
            if key in value:
                character_ref = value[key]
                if kinds.get(character_ref) != "character":
                    raise ProductionRunError("narrative_proposal_invalid", "narrative relationship or knowledge references an unknown character")
                value[key] = resolved.get(character_ref, character_ref)
        quote = raw["evidence_quote"]
        if not quote or quote not in payload["candidate_text"]:
            raise ProductionRunError("narrative_evidence_mismatch", "narrative facts require an exact quote from the final candidate")
        changes.append({"entity_type": kind, "operation": "create" if ref.startswith("local:") else "update",
                        "entity_id": resolved[ref], "before_state_fingerprint": "absent" if ref.startswith("local:") else existing[ref]["source_fingerprint"],
                        "fields": value, "evidence_ref": "candidate:" + payload["candidate_fingerprint"], "evidence_quote": quote})
    proposal = {"schema": "quillframe_narrative_state_proposal_v1", "chapter_id": target["chapter_id"], "document_id": target["document_id"],
                "candidate_fingerprint": payload["candidate_fingerprint"], "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                "registered_binding_fingerprint": binding["binding_fingerprint"], "changes": changes, "authority": False}
    proposal["proposal_fingerprint"] = fingerprint(proposal)
    return proposal


def semantic_status(binding: dict[str, Any]) -> str:
    result = binding.get("result") or {}
    judgment = result.get("judgment") if isinstance(result, dict) else None
    semantic_result = judgment.get("result") if isinstance(judgment, dict) else None
    if semantic_result == "insufficient_evidence":
        return "pending"
    if semantic_result in {"pass", "fail"}:
        return semantic_result
    raise ProductionRunError("semantic_output_invalid", "registered semantic judgment has no supported result")


def build_pre_independent_qualification(
    *,
    subject_id: str,
    candidate_fingerprint: str,
    self_audit_binding: dict[str, Any],
    reader_binding: dict[str, Any],
    continuity_receipt_fingerprint: str,
    repair_cycle: int = 0,
    repair_preservation: dict[str, Any] | None = None,
    _recorded: bool = False,
) -> dict[str, Any]:
    self_status = semantic_status(self_audit_binding)
    reader_status = semantic_status(reader_binding)
    payload: dict[str, Any] = {
        "subject_id": subject_id,
        "candidate_fingerprint": candidate_fingerprint,
        "repair_cycle": repair_cycle,
        "self_audit": {"status": self_status, "semantic_binding": {"job": self_audit_binding["job"], "result": self_audit_binding["result"]}},
        "reader_engagement": {"status": reader_status, "semantic_binding": {"job": reader_binding["job"], "result": reader_binding["result"]}},
        "continuity": {
            "status": "pass",
            "candidate_fingerprint": candidate_fingerprint,
            "receipt_fingerprint": continuity_receipt_fingerprint,
            "evidence_refs": [f"continuity:{continuity_receipt_fingerprint}"],
        },
    }
    if repair_cycle > 0:
        payload["repair_preservation"] = repair_preservation or {"status": "pending"}
    try:
        evaluator = evaluate_recorded_qualification if _recorded else evaluate_qualification
        receipt = evaluator(payload)
    except ValueError as exc:
        raise ProductionRunError("qualification_invalid", str(exc)) from exc
    errors = validate_qualification_receipt(
        receipt,
        candidate_fingerprint=candidate_fingerprint,
        subject_id=subject_id,
        require_qualified=False,
    )
    if errors:
        raise ProductionRunError("qualification_invalid", "; ".join(errors))
    return receipt


def prepare_independent_review(
    *,
    run: dict[str, Any],
    subject_id: str,
    candidate_fingerprint: str,
    candidate_text: str,
    reader_visible_context: list[dict[str, Any]],
    reader_grip: str,
    qualification_receipt: dict[str, Any],
    provenance: dict[str, Any],
    reading_positioning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors = validate_qualification_receipt(
        qualification_receipt,
        candidate_fingerprint=candidate_fingerprint,
        subject_id=subject_id,
        require_qualified=True,
    )
    if errors:
        raise ProductionRunError("not_qualified_for_independent", "; ".join(errors))
    required_provenance = {"project_id", "project_repo", "framework_repo", "framework_commit"}
    if not isinstance(provenance, dict) or not required_provenance.issubset(provenance):
        raise ProductionRunError(
            "independent_provenance_required",
            "independent review dispatch requires project_id/project_repo/framework_repo/framework_commit provenance",
        )
    payload = {
        "candidate_fingerprint": candidate_fingerprint,
        "candidate_text": candidate_text,
        "reader_visible_context": reader_visible_context,
        "reader_grip": reader_grip,
    }
    if reading_positioning is not None:
        payload.update(reading_positioning_fields(
            reading_positioning, target_context=run.get("target_context"), reader_grip=reader_grip,
        ))
    try:
        job = make_contract_job(
            "quality.production_review",
            subject_id,
            payload,
            source_session_id=str(run.get("session_id") or f"session:{run['run_id']}"),
            handoff_id=f"{run['run_id']}:quality.production_review",
            qualification_receipt=qualification_receipt,
        )
    except ValueError as exc:
        raise ProductionRunError("independent_job_invalid", str(exc)) from exc
    job["provenance"].update({key: provenance[key] for key in sorted(required_provenance)})
    try:
        packet = build_peer_packet(job)
    except ValueError as exc:
        raise ProductionRunError("independent_packet_invalid", str(exc)) from exc
    packet["execution_permissions"] = {
        "project_read": False,
        "filesystem": False,
        "shell": False,
        "network": False,
        "memory": False,
        "write": False,
    }
    packet_bytes = canonical_json(packet)
    return {
        "schema": "quillframe_independent_review_handoff_v1",
        "subject_id": subject_id,
        "candidate_fingerprint": candidate_fingerprint,
        "qualification_receipt": qualification_receipt,
        "independent_job": job,
        "peer_packet": packet,
        "peer_packet_bytes": packet_bytes,
        "reader_grip": reader_grip,
        "reader_visible_context": reader_visible_context,
        "authority": False,
    }


def validate_independent_submission(
    *,
    handoff: dict[str, Any],
    peer_packet: dict[str, Any],
    result: dict[str, Any],
    independence_receipt: dict[str, Any],
) -> dict[str, Any]:
    stored_packet = handoff.get("peer_packet")
    stored_packet_bytes = handoff.get("peer_packet_bytes")
    if (
        not isinstance(stored_packet, dict)
        or not isinstance(stored_packet_bytes, str)
        or canonical_json(stored_packet) != stored_packet_bytes
        or canonical_json(peer_packet) != stored_packet_bytes
    ):
        raise ProductionRunError("independent_packet_mismatch", "submitted peer packet does not match the frozen pending handoff")
    peer_errors = validate_peer_result(peer_packet, result)
    if peer_errors:
        raise ProductionRunError("independent_result_invalid", "; ".join(peer_errors))
    if independence_receipt.get("schema") == INDEPENDENT_INVOCATION_RECEIPT_SCHEMA:
        receipt_errors = validate_independent_invocation_receipt(independence_receipt, peer_packet, result)
        if receipt_errors:
            raise ProductionRunError("independent_invocation_receipt_invalid", "; ".join(receipt_errors))
    else:
        receipt_errors = validate_peer_bridge_receipt(independence_receipt, peer_packet, result)
        if receipt_errors:
            raise ProductionRunError("independent_bridge_receipt_invalid", "; ".join(receipt_errors))
    stored_job = handoff.get("independent_job")
    packet_job = peer_packet.get("job")
    if not isinstance(stored_job, dict) or not isinstance(packet_job, dict):
        raise ProductionRunError("independent_job_invalid", "frozen independent job/packet job required")
    for key in ("job_id", "subject_id", "kind", "input_fingerprint"):
        if stored_job.get(key) != packet_job.get(key):
            raise ProductionRunError("independent_job_mismatch", f"peer packet changed independent job binding: {key}")
    return {
        "job": stored_job,
        "result": result,
        "peer_packet": peer_packet,
        "independence_receipt": independence_receipt,
    }


def final_readiness(
    *,
    candidate_fingerprint: str,
    qualification_receipt: dict[str, Any],
    reader_binding: dict[str, Any],
    continuity_receipt_fingerprint: str,
    independent_binding: dict[str, Any],
    reader_grip: str,
) -> dict[str, Any]:
    surface_status = qualification_receipt.get("surface_audit_status")
    if surface_status not in {"pass", "fail"}:
        surface_status = "pending"
    gates = [
        {"category": "surface", "candidate_fingerprint": candidate_fingerprint, "status": surface_status, "evidence_refs": [f"qualification:{qualification_receipt.get('receipt_fingerprint')}"]},
        {"category": "reader_engagement", "candidate_fingerprint": candidate_fingerprint, "status": semantic_status(reader_binding), "semantic_binding": {"job": reader_binding["job"], "result": reader_binding["result"]}},
        {"category": "continuity", "candidate_fingerprint": candidate_fingerprint, "status": "pass", "evidence_refs": [f"continuity:{continuity_receipt_fingerprint}"]},
        {"category": "semantic_independent", "candidate_fingerprint": candidate_fingerprint, "status": semantic_status({"result": independent_binding["result"]}), "semantic_binding": independent_binding},
    ]
    try:
        return evaluate_production_readiness({
            "candidate_fingerprint": candidate_fingerprint,
            "policy": {
                "reader_grip": reader_grip,
                "require_continuity": True,
                "require_semantic_rules": False,
                "require_independent_semantic": True,
            },
            "pre_independent_qualification": qualification_receipt,
            "gates": gates,
        })
    except ValueError as exc:
        raise ProductionRunError("production_readiness_invalid", str(exc)) from exc


def final_release(
    *,
    production_readiness: dict[str, Any],
    qualification_receipt: dict[str, Any],
    candidate_fingerprint: str,
    context_bundle_fingerprint: str,
    freeze_fingerprint: str,
    user_visible_gate_receipt_fingerprint: str,
) -> dict[str, Any]:
    """Aggregate semantic readiness with structural execution receipts.

    This is the only release object that can authorize manuscript visibility.
    A semantic PASS or user-visible stage receipt alone is insufficient.
    """
    structural_receipts = [
        {
            "kind": "context_assembly",
            "status": "pass",
            "candidate_fingerprint": candidate_fingerprint,
            "receipt_fingerprint": context_bundle_fingerprint,
            "evidence_refs": [f"context_bundle:{context_bundle_fingerprint}", f"freeze:{freeze_fingerprint}"],
        },
        {
            "kind": "user_visible_gate",
            "status": "pass",
            "candidate_fingerprint": candidate_fingerprint,
            "receipt_fingerprint": user_visible_gate_receipt_fingerprint,
            "evidence_refs": [f"user_visible_gate:{user_visible_gate_receipt_fingerprint}"],
        },
    ]
    try:
        return aggregate_production_release({
            "production_readiness": production_readiness,
            "pre_independent_qualification": qualification_receipt,
            "structural_policy": {"required_receipts": ["context_assembly", "user_visible_gate"]},
            "structural_receipts": structural_receipts,
        })
    except ValueError as exc:
        raise ProductionRunError("production_release_invalid", str(exc)) from exc
