from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from harness.context_runtime import fingerprint

from .contracts import ProductionRunError, assert_secret_free


DECLARATION_SCHEMA = "quillframe_reader_positioning_v1"
PROJECTION_SCHEMA = "quillframe_production_reading_positioning_v1"
PROFILE_FIELDS = ("genre_profile", "platform_profile")
READER_FIELDS = ("reader_grip", "chapter_position", *PROFILE_FIELDS)
READER_GRIP_VALUES = {"low", "medium", "high", "very_high"}
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def validate_reader_positioning(value: Any) -> dict[str, str]:
    """Validate an explicit public-label declaration, never classify plan prose.

    The caller declares these labels reader-eligible in the frozen author
    request. This is not a semantic proof that arbitrary source text is public.
    No plan, author-model dictionary or private character state is projected.
    """
    if not isinstance(value, dict) or set(value) - {"schema", "visibility", *PROFILE_FIELDS}:
        raise ProductionRunError("reader_positioning_invalid", "reader positioning requires the closed public-label declaration")
    if value.get("schema") != DECLARATION_SCHEMA or value.get("visibility") != "reader_eligible":
        raise ProductionRunError("reader_positioning_invalid", "reader positioning must explicitly declare reader-eligible labels")
    if not any(key in value for key in PROFILE_FIELDS):
        raise ProductionRunError("reader_positioning_invalid", "reader positioning requires at least one explicit profile label")
    for key in PROFILE_FIELDS:
        if key not in value:
            continue
        label = value[key]
        if not isinstance(label, str) or not label.strip() or len(label) > 160 or any(ord(char) < 32 or ord(char) == 127 for char in label):
            raise ProductionRunError("reader_positioning_invalid", "profile labels must be non-empty single-line strings of at most 160 characters")
    assert_secret_free(value, label="declared reader positioning")
    return deepcopy(value)


def build_reading_positioning(
    *, target_context: dict[str, Any], reader_grip: str, execution_request_fingerprint: str,
) -> dict[str, Any]:
    """Project only frozen author-declared labels and the actual chapter order."""
    if not isinstance(target_context, dict) or target_context.get("schema") != "quillframe_author_run_request_v1":
        raise ProductionRunError("reader_positioning_invalid", "reading positioning requires a Core-frozen author request")
    payload = target_context.get("payload")
    order = target_context.get("current_reading_order")
    if not isinstance(payload, dict) or not isinstance(order, int) or isinstance(order, bool) or order < 0:
        raise ProductionRunError("reader_positioning_invalid", "reading positioning requires a frozen reading order and author payload")
    if not isinstance(reader_grip, str) or reader_grip not in READER_GRIP_VALUES:
        raise ProductionRunError("reader_positioning_invalid", "reading positioning requires the frozen reader grip")
    if not isinstance(execution_request_fingerprint, str) or not _SHA256.fullmatch(execution_request_fingerprint):
        raise ProductionRunError("reader_positioning_invalid", "reading positioning requires the exact execution request fingerprint")
    declaration = validate_reader_positioning(payload["reader_positioning"]) if "reader_positioning" in payload else {}
    fields = {
        "reader_grip": reader_grip,
        # An order is observable positioning. A chapter's planned function,
        # future payoff or a creator's explanation is deliberately not inferred.
        "chapter_position": f"reading_order={order}",
        **{key: declaration[key] for key in PROFILE_FIELDS if key in declaration},
    }
    result = {
        "schema": PROJECTION_SCHEMA,
        "reader_fields": fields,
        "source_binding": {
            "author_request_fingerprint": fingerprint(target_context),
            "execution_request_fingerprint": execution_request_fingerprint,
        },
        "authority": False,
    }
    result["positioning_fingerprint"] = fingerprint(result)
    return result


def reading_positioning_fields(
    value: dict[str, Any], *, target_context: dict[str, Any], reader_grip: str,
    execution_request_fingerprint: str | None = None,
) -> dict[str, str]:
    """Recompute the projection; unknown keys and rewritten bindings fail closed."""
    if not isinstance(value, dict) or not isinstance(value.get("source_binding"), dict):
        raise ProductionRunError("reader_positioning_invalid", "a frozen reading-positioning projection is required")
    source_fingerprint = value["source_binding"].get("execution_request_fingerprint")
    if execution_request_fingerprint is not None and source_fingerprint != execution_request_fingerprint:
        raise ProductionRunError("reader_positioning_mismatch", "reading positioning belongs to another execution request")
    expected = build_reading_positioning(
        target_context=target_context, reader_grip=reader_grip,
        execution_request_fingerprint=source_fingerprint,
    )
    if fingerprint(value) != fingerprint(expected):
        raise ProductionRunError("reader_positioning_mismatch", "reading positioning differs from its frozen source projection")
    return deepcopy(expected["reader_fields"])
