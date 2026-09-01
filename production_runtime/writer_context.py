"""Mechanical inventory and materialization boundary for direct fiction writing.

The scene projection model owns relevance and selects opaque context IDs.
Core owns eligibility, provenance, exact fingerprints and the prohibition on
rejected prose, private deliberation and review explanations.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from harness.context_runtime import fingerprint
from learning.author_voice import validate_snapshot as validate_voice_snapshot
from persistence.quillframe_sqlite import fingerprint_text

from .contracts import ProductionRunError


INVENTORY_SCHEMA = "quillframe_writer_context_inventory_v1"
PACK_SCHEMA = "quillframe_direct_writer_pack_v1"
WRITER_DIRECTIVE_VERSION = "direct-surface-writer-v2"
ALLOWED_SOURCE_TYPES = {
    "character",
    "relationship",
    "world_fact",
    "location",
    "canon_claim",
    "accepted_manuscript",
}
FORBIDDEN_WRITER_KEYS = {
    "candidate_text",
    "rejected_prose",
    "reviewer_analysis",
    "reader_assessment",
    "semantic_rule_assessment",
    "repair_explanation",
    "private_state",
    "proposals",
    "expectations_of_others",
    "rejection_reason",
}


def _forbidden_paths(value: Any, *, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_WRITER_KEYS:
                hits.append(child_path)
            hits.extend(_forbidden_paths(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_forbidden_paths(child, path=f"{path}[{index}]"))
    return hits


def _item(
    *,
    context_id: str,
    category: str,
    source_fingerprint: str,
    selection_view: dict[str, Any],
    writer_value: dict[str, Any],
) -> dict[str, Any]:
    return {
        "context_id": context_id,
        "category": category,
        "source_fingerprint": source_fingerprint,
        "selection_view": deepcopy(selection_view),
        "writer_value": deepcopy(writer_value),
    }


def build_inventory(
    frozen_scene: dict[str, Any],
    *,
    character_action_evidence: list[dict[str, Any]],
    author_model: dict[str, Any] | None,
) -> dict[str, Any]:
    present_ids = {
        str(item.get("character_id"))
        for item in character_action_evidence
        if isinstance(item, dict) and isinstance(item.get("character_id"), str)
    }
    items: list[dict[str, Any]] = []
    required_context_ids: list[str] = []
    author_model = author_model if isinstance(author_model, dict) else {}

    selected_preference_ids = author_model.get("selected_hypothesis_ids", [])
    active_preferences = author_model.get("active_preferences", [])
    if selected_preference_ids or active_preferences:
        if (
            not isinstance(selected_preference_ids, list)
            or any(not isinstance(value, str) or not value for value in selected_preference_ids)
            or len(selected_preference_ids) != len(set(selected_preference_ids))
            or not isinstance(active_preferences, list)
            or any(not isinstance(value, dict) for value in active_preferences)
        ):
            raise ProductionRunError(
                "selected_author_preference_invalid",
                "frozen selected author preferences are malformed",
            )
        preference_by_id = {
            value.get("hypothesis_id"): value for value in active_preferences
            if isinstance(value.get("hypothesis_id"), str)
        }
        if (
            len(preference_by_id) != len(active_preferences)
            or set(preference_by_id) != set(selected_preference_ids)
        ):
            raise ProductionRunError(
                "selected_author_preference_invalid",
                "frozen preference content does not match the explicit selection",
            )
        for hypothesis_id in selected_preference_ids:
            preference = preference_by_id[hypothesis_id]
            required = ("dimension", "statement", "mechanism", "applicability", "version")
            if (
                any(key not in preference for key in required)
                or any(
                    not isinstance(preference[key], str) or not preference[key].strip()
                    for key in ("dimension", "statement", "mechanism")
                )
                or not isinstance(preference["applicability"], dict)
                or not isinstance(preference["version"], int)
                or isinstance(preference["version"], bool)
                or preference["version"] < 1
            ):
                raise ProductionRunError(
                    "selected_author_preference_invalid",
                    "a frozen selected author preference has invalid writer fields",
                )
            context_id = f"author-preference:{hypothesis_id}:v{preference['version']}"
            source_fp = fingerprint(preference)
            safe = {
                "hypothesis_id": hypothesis_id,
                "dimension": preference["dimension"],
                "statement": preference["statement"],
                "mechanism": preference["mechanism"],
                "applicability": deepcopy(preference["applicability"]),
                "version": preference["version"],
            }
            items.append(_item(
                context_id=context_id,
                category="selected_author_preference",
                source_fingerprint=source_fp,
                selection_view=safe,
                writer_value={**safe, "source_fingerprint": source_fp},
            ))
            required_context_ids.append(context_id)

    voice = author_model.get("author_voice_snapshot")
    if isinstance(voice, dict):
        try:
            validate_voice_snapshot(voice)
        except ValueError as exc:
            raise ProductionRunError("author_voice_snapshot_invalid", str(exc)) from exc
        sheet = voice.get("active_sheet")
        if isinstance(sheet, dict):
            sheet_fp = sheet.get("sheet_fingerprint")
            items.append(_item(
                context_id=f"author-voice:{sheet['sheet_id']}:v{sheet['version']}",
                category="author_voice_sheet",
                source_fingerprint=sheet_fp,
                selection_view={
                    "scope": sheet["scope"],
                    "fields": deepcopy(sheet["fields"]),
                    "uncertainties": deepcopy(sheet["uncertainties"]),
                    "status": voice["status"],
                },
                writer_value={
                    "fields": deepcopy(sheet["fields"]),
                    "uncertainties": deepcopy(sheet["uncertainties"]),
                    "sheet_id": sheet["sheet_id"],
                    "sheet_version": sheet["version"],
                    "sheet_fingerprint": sheet_fp,
                    "author_confirmation_ref": sheet["author_confirmation_ref"],
                },
            ))
        for source in voice.get("eligible_anchors", []):
            items.append(_item(
                context_id=f"voice-anchor:{source['source_id']}:v{source['version']}",
                category="positive_voice_anchor",
                source_fingerprint=source["content_fingerprint"],
                selection_view={
                    "source_kind": source["source_kind"],
                    "applicability": deepcopy(source["applicability"]),
                    "content_text": source["content_text"],
                },
                writer_value={
                    "source_id": source["source_id"],
                    "content_text": source["content_text"],
                    "content_fingerprint": source["content_fingerprint"],
                    "source_kind": source["source_kind"],
                    "applicability": deepcopy(source["applicability"]),
                    "rights_binding": {
                        "rights_class": source["rights"]["rights_class"],
                        "rights_basis": source["rights"]["rights_basis"],
                        "storage_intent": source["rights"]["storage_intent"],
                        "writer_use_authorized": True,
                        "author_confirmed": True,
                    },
                },
            ))

    taste = author_model.get("user_taste_snapshot")
    if isinstance(taste, dict) and taste.get("policy", {}).get("enabled") is True:
        for candidate in taste.get("candidates", []):
            source_fp = fingerprint(candidate)
            items.append(_item(
                context_id=f"user-taste:{candidate['hypothesis_id']}:v{candidate['version']}",
                category="user_taste_mechanism",
                source_fingerprint=source_fp,
                selection_view=deepcopy(candidate),
                writer_value={
                    "dimension": candidate["dimension"],
                    "mechanism": candidate["mechanism"],
                    "applicability": deepcopy(candidate["applicability"]),
                    "version": candidate["version"],
                    "source_fingerprint": source_fp,
                },
            ))

    for source in frozen_scene.get("items", []):
        if not isinstance(source, dict) or source.get("object_type") not in ALLOWED_SOURCE_TYPES:
            continue
        source_type = source["object_type"]
        view = source.get("model_view")
        if not isinstance(view, dict):
            continue
        context_id = str(source["object_id"])
        source_fp = str(source["source_fingerprint"])
        if source_type == "character":
            character_id = view.get("character_id")
            if character_id not in present_ids:
                continue
            safe = {
                key: deepcopy(view[key])
                for key in ("character_id", "name", "voice_notes")
                if key in view
            }
            items.append(_item(
                context_id=context_id,
                category="present_character",
                source_fingerprint=source_fp,
                selection_view=safe,
                writer_value=safe,
            ))
        elif source_type == "relationship":
            participants = {view.get("participant_a"), view.get("participant_b")}
            if not participants or not participants.issubset(present_ids):
                continue
            safe = {
                key: deepcopy(view[key])
                for key in (
                    "relationship_id", "participant_a", "participant_b",
                    "relationship_type", "state",
                )
                if key in view
            }
            items.append(_item(
                context_id=context_id,
                category="relationship",
                source_fingerprint=source_fp,
                selection_view=safe,
                writer_value=safe,
            ))
        elif source_type == "accepted_manuscript":
            content = view.get("content")
            content_fp = view.get("content_fingerprint")
            if (
                not isinstance(content, str)
                or not isinstance(content_fp, str)
                or fingerprint_text(content) != content_fp
            ):
                raise ProductionRunError(
                    "accepted_prose_tail_invalid",
                    "accepted manuscript context does not bind exact prose",
                )
            tail = content[-4000:]
            tail_fp = fingerprint_text(tail)
            selection = {
                "story_node_id": view.get("story_node_id"),
                "reading_order": view.get("reading_order"),
                "title": view.get("title"),
                "content_tail": tail,
            }
            items.append(_item(
                context_id="accepted-tail:" + context_id,
                category="accepted_prose_tail",
                source_fingerprint=content_fp,
                selection_view=selection,
                writer_value={
                    **selection,
                    "content_fingerprint": content_fp,
                    "tail_fingerprint": tail_fp,
                    "acceptance_id": view.get("acceptance_id"),
                    "settlement_head_fingerprint": view.get("settlement_head_fingerprint"),
                },
            ))
        else:
            category = "location" if source_type == "location" else "world_fact"
            items.append(_item(
                context_id=context_id,
                category=category,
                source_fingerprint=source_fp,
                selection_view=deepcopy(view),
                writer_value=deepcopy(view),
            ))

    ids = [item["context_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ProductionRunError("writer_context_inventory_invalid", "context IDs must be unique")
    value = {
        "schema": INVENTORY_SCHEMA,
        "present_character_ids": sorted(present_ids),
        "required_context_ids": required_context_ids,
        "items": items,
        "forbidden_classes": [
            "rejected_prose",
            "reviewer_analysis",
            "repair_explanation",
            "private_character_deliberation",
            "unrelated_plan_or_lore",
            "future_pov_unknown",
            "scripted_quality_diagnostic",
        ],
        "authority": False,
    }
    value["inventory_fingerprint"] = fingerprint(value)
    return value


def model_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    validate_inventory(inventory)
    return {
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "required_context_ids": list(inventory["required_context_ids"]),
        "items": [
            {
                key: deepcopy(item[key])
                for key in ("context_id", "category", "source_fingerprint", "selection_view")
            }
            for item in inventory["items"]
        ],
    }


def validate_inventory(inventory: dict[str, Any]) -> None:
    if not isinstance(inventory, dict) or inventory.get("schema") != INVENTORY_SCHEMA:
        raise ProductionRunError("writer_context_inventory_invalid", "inventory schema mismatch")
    expected = fingerprint({
        key: value for key, value in inventory.items() if key != "inventory_fingerprint"
    })
    if inventory.get("inventory_fingerprint") != expected:
        raise ProductionRunError("writer_context_inventory_invalid", "inventory fingerprint changed")
    ids = [item.get("context_id") for item in inventory.get("items", []) if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        raise ProductionRunError("writer_context_inventory_invalid", "inventory IDs changed")
    required = inventory.get("required_context_ids")
    if (
        not isinstance(required, list)
        or any(not isinstance(value, str) or not value for value in required)
        or len(required) != len(set(required))
        or not set(required).issubset(ids)
    ):
        raise ProductionRunError(
            "writer_context_inventory_invalid",
            "required context IDs are invalid or not eligible",
        )


def materialize_writer_pack(
    inventory: dict[str, Any],
    *,
    selected_context_ids: list[str],
    scene_contract: dict[str, Any],
    director_note: str,
    author_objectives: dict[str, Any],
    source_binding_fingerprint: str,
    craft_guidance: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_inventory(inventory)
    if (
        not isinstance(selected_context_ids, list)
        or any(not isinstance(value, str) or not value for value in selected_context_ids)
        or len(selected_context_ids) != len(set(selected_context_ids))
    ):
        raise ProductionRunError("writer_context_selection_invalid", "selected context IDs are invalid")
    available = {item["context_id"]: item for item in inventory["items"]}
    unknown = [context_id for context_id in selected_context_ids if context_id not in available]
    if unknown:
        raise ProductionRunError(
            "writer_context_selection_invalid",
            "scene projection selected an ineligible context ID",
            detail=unknown,
        )
    missing_required = [
        context_id for context_id in inventory["required_context_ids"]
        if context_id not in selected_context_ids
    ]
    if missing_required:
        raise ProductionRunError(
            "writer_context_selection_invalid",
            "scene projection omitted an explicitly selected author preference",
            detail=missing_required,
        )
    selected = [
        {
            "context_id": context_id,
            "category": available[context_id]["category"],
            "source_fingerprint": available[context_id]["source_fingerprint"],
            "value": deepcopy(available[context_id]["writer_value"]),
        }
        for context_id in selected_context_ids
    ]
    pack = {
        "schema": PACK_SCHEMA,
        "writer_directive_version": WRITER_DIRECTIVE_VERSION,
        "scene_contract": deepcopy(scene_contract),
        "director_note": director_note,
        "author_objectives": deepcopy(author_objectives),
        "selected_context": selected,
        "selection": {
            "inventory_fingerprint": inventory["inventory_fingerprint"],
            "selected_context_ids": list(selected_context_ids),
            "source_binding_fingerprint": source_binding_fingerprint,
        },
        "forbidden_context_confirmed_absent": list(inventory["forbidden_classes"]),
        "authority": False,
    }
    if craft_guidance is not None:
        pack["craft_guidance"] = deepcopy(craft_guidance)
    if repair_context is not None:
        pack["repair_context"] = deepcopy(repair_context)
    forbidden_paths = _forbidden_paths(pack)
    if forbidden_paths:
        raise ProductionRunError(
            "writer_context_boundary_violation",
            "Writer pack contains a forbidden planning, review or rejected-prose field",
            detail=forbidden_paths,
        )
    pack["context_boundary_receipt"] = {
        "checked_forbidden_keys": sorted(FORBIDDEN_WRITER_KEYS),
        "forbidden_paths": [],
        "fresh_repair_projection": (
            isinstance(repair_context, dict)
            and repair_context.get("generation_mode") == "fresh_realization"
        ),
        "authority": False,
    }
    pack["writer_pack_fingerprint"] = fingerprint(pack)
    return pack
