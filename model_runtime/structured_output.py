"""A deliberately small, locally verifiable native JSON Schema transport profile.

This constrains response shape, not semantic conclusions. Unsupported schemas
fail before dispatch; returned text is validated without repairing its bytes.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any


_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}
_COMMON = {"type", "enum", "title", "description"}
_KEYWORDS = {
    "object": {"properties", "required", "additionalProperties"},
    "array": {"items", "minItems", "maxItems"},
    "string": {"minLength", "maxLength"},
    "number": {"minimum", "maximum"},
    "integer": {"minimum", "maximum"},
    "boolean": set(), "null": set(),
}


def _matches_type(value: Any, kind: str) -> bool:
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    if kind in {"number", "integer"}:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and (not isinstance(value, float) or math.isfinite(value))
                and (kind == "number" or isinstance(value, int) or value.is_integer()))
    return False


def validate_output_schema(schema: Any) -> None:
    """Validate our explicit strict subset, not every possible JSON Schema."""
    property_count = 0
    enum_count = 0
    string_size = 0

    def visit(node: Any, path: str, depth: int) -> None:
        nonlocal property_count, enum_count, string_size
        if not isinstance(node, dict) or depth > 10:
            raise ValueError(f"{path}: schema must be an object with depth at most 10")
        raw_type = node.get("type")
        kinds = raw_type if isinstance(raw_type, list) else [raw_type]
        if (not kinds or any(not isinstance(t, str) or t not in _TYPES for t in kinds)
                or len(kinds) != len(set(kinds))
                or (len(kinds) > 1 and (len(kinds) != 2 or "null" not in kinds))):
            raise ValueError(f"{path}: expected one declared type, optionally nullable")
        allowed = _COMMON | set().union(*(_KEYWORDS[t] for t in kinds))
        if set(node) - allowed:
            raise ValueError(f"{path}: unsupported output schema keywords")
        for key in ("title", "description"):
            if key in node and not isinstance(node[key], str):
                raise ValueError(f"{path}.{key}: expected string")
        if "enum" in node:
            values = node["enum"]
            if (not isinstance(values, list) or not values
                    or any(isinstance(v, (dict, list)) or not any(_matches_type(v, t) for t in kinds) for v in values)):
                raise ValueError(f"{path}.enum: expected nonempty typed scalar values")
            enum_count += len(values)
            enum_size = sum(len(value) for value in values if isinstance(value, str))
            string_size += enum_size
            if enum_count > 1000 or (len(values) > 250 and enum_size > 15_000):
                raise ValueError(f"{path}.enum: native output enum limit exceeded")
            if any(value == earlier and isinstance(value, bool) == isinstance(earlier, bool)
                   for index, value in enumerate(values) for earlier in values[:index]):
                raise ValueError(f"{path}.enum: duplicate enum values")
        if "object" in kinds:
            props, required = node.get("properties"), node.get("required")
            if (not isinstance(props, dict) or any(not isinstance(k, str) for k in props)
                    or not isinstance(required, list) or any(not isinstance(k, str) for k in required)
                    or len(required) != len(set(required)) or set(required) != set(props)
                    or node.get("additionalProperties") is not False):
                raise ValueError(f"{path}: objects must be closed and require all declared properties")
            property_count += len(props)
            string_size += sum(len(key) for key in props)
            if property_count > 5000:
                raise ValueError("output schema exceeds 5000 properties")
            for key, child in props.items():
                visit(child, f"{path}.properties.{key}", depth + 1)
        if string_size > 120_000:
            raise ValueError("native output schema string limit exceeded")
        if "array" in kinds:
            visit(node.get("items"), f"{path}.items", depth + 1)
        for lower, upper, integral in (("minimum", "maximum", False), ("minLength", "maxLength", True), ("minItems", "maxItems", True)):
            for key in (lower, upper):
                if key in node:
                    value = node[key]
                    if (not _matches_type(value, "number") or (integral and (not isinstance(value, int) or value < 0))):
                        raise ValueError(f"{path}.{key}: invalid bound")
            if lower in node and upper in node and node[lower] > node[upper]:
                raise ValueError(f"{path}: inconsistent bounds")

    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("output schema root must be an object")
    visit(schema, "$", 0)


def required_only_output_schema(contract: dict[str, Any]) -> dict[str, Any]:
    """An explicit narrower profile: omit optional fields, never invent nulls.

    Callers must opt in for a reviewed contract. Free text retains semantic
    expression; every emitted object still satisfies the original contract.
    Open maps and unsupported required subtrees are rejected, not approximated.
    """
    def project(node: Any) -> dict[str, Any]:
        if not isinstance(node, dict):
            raise ValueError("output contract schema must be an object")
        result = deepcopy(node)
        if "type" not in result and isinstance(result.get("enum"), list) and result["enum"]:
            values = result["enum"]
            inferred = next((t for t in ("string", "boolean", "integer", "number", "null")
                             if all(_matches_type(v, t) for v in values)), None)
            if inferred is not None:
                result["type"] = inferred
        kinds = result.get("type") if isinstance(result.get("type"), list) else [result.get("type")]
        if "object" in kinds:
            props, required = result.get("properties"), result.get("required", [])
            if (result.get("additionalProperties") is not False or not isinstance(props, dict)
                    or not isinstance(required, list) or any(not isinstance(k, str) or k not in props for k in required)):
                raise ValueError("required-only profile needs a closed object contract")
            result["properties"] = {key: project(value) for key, value in props.items() if key in required}
            result["required"] = required
        if "array" in kinds:
            result["items"] = project(result.get("items"))
        return result

    schema = project(contract)
    validate_output_schema(schema)
    return schema


def validate_structured_text(text: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Strictly validate the entire response; never trim or reconstruct it."""
    validate_output_schema(schema)

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def invalid_constant(_: str) -> None:
        raise ValueError("non-finite JSON number")

    value = json.loads(text, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)

    def visit(item: Any, node: dict[str, Any], path: str) -> None:
        kinds = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(_matches_type(item, t) for t in kinds):
            raise ValueError(f"{path}: output type mismatch")
        if "enum" in node and not any(item == option and isinstance(item, bool) == isinstance(option, bool) for option in node["enum"]):
            raise ValueError(f"{path}: output enum mismatch")
        if isinstance(item, dict):
            if set(item) != set(node["properties"]):
                raise ValueError(f"{path}: output properties mismatch")
            for key, child in item.items():
                visit(child, node["properties"][key], f"{path}.{key}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, node["items"], f"{path}[{index}]")
        if isinstance(item, (str, list)):
            lower, upper = ("minLength", "maxLength") if isinstance(item, str) else ("minItems", "maxItems")
            if (lower in node and len(item) < node[lower]) or (upper in node and len(item) > node[upper]):
                raise ValueError(f"{path}: output length out of bounds")
        if _matches_type(item, "number"):
            if ("minimum" in node and item < node["minimum"]) or ("maximum" in node and item > node["maximum"]):
                raise ValueError(f"{path}: output number out of bounds")

    visit(value, schema, "$")
    return value
