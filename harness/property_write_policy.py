#!/usr/bin/env python3
"""Deterministic property-level write-source policy for NovelForge Projects.

This module does not decide story truth or infer state from prose. It resolves a
Project-owned policy into a typed route describing whether a writer class may
perform a direct mutation or must go through proposal, Settlement, or reconcile.

Existing Projects that do not configure ``paths.property_write_policy`` retain
legacy object-level authority behavior; this module does not reinterpret them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


POLICY_SCHEMA = "novelforge_property_write_policy_v1"
DECISION_SCHEMA = "novelforge_property_write_decision_v1"
POLICY_PATH_KEY = "property_write_policy"

MUTATION_CLASSES = {
    "user_declared",
    "settlement_only",
    "derived_only",
    "proposal_only",
    "runtime_only",
    "locked",
    "mixed_reconcile",
}
WRITER_CLASSES = {
    "user",
    "authorized_human",
    "settlement",
    "semantic_worker",
    "derived_rebuilder",
    "runtime",
}
DECISIONS = {
    "allow_direct",
    "proposal_required",
    "settlement_required",
    "reconcile_required",
    "deny",
    "legacy_unmanaged",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _normalize_rule(value: Any, field: str) -> dict[str, str]:
    if isinstance(value, str):
        mutation_class = value
    elif isinstance(value, dict):
        unknown = set(value) - {"mutation_class"}
        if unknown:
            raise ValueError(f"{field} has unsupported keys: {sorted(unknown)}")
        mutation_class = value.get("mutation_class")
    else:
        raise ValueError(f"{field} must be string or object")
    if mutation_class not in MUTATION_CLASSES:
        raise ValueError(f"{field}.mutation_class must be one of {sorted(MUTATION_CLASSES)}")
    return {"mutation_class": mutation_class}


def validate_policy(value: Any) -> list[str]:
    try:
        normalize_policy(value)
        return []
    except Exception as exc:
        return [f"{type(exc).__name__}: {exc}"]


def normalize_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("policy root must be object")
    if value.get("schema") != POLICY_SCHEMA:
        raise ValueError(f"policy.schema must be {POLICY_SCHEMA}")
    unknown = set(value) - {"schema", "default", "object_types"}
    if unknown:
        raise ValueError(f"policy has unsupported keys: {sorted(unknown)}")
    default = _normalize_rule(value.get("default"), "default")
    raw_objects = value.get("object_types", {})
    if not isinstance(raw_objects, dict):
        raise ValueError("object_types must be object")
    objects: dict[str, Any] = {}
    for raw_type, raw_spec in raw_objects.items():
        object_type = _nonempty_string(raw_type, "object type")
        if not isinstance(raw_spec, dict):
            raise ValueError(f"object_types.{object_type} must be object")
        unknown_spec = set(raw_spec) - {"default", "properties"}
        if unknown_spec:
            raise ValueError(f"object_types.{object_type} has unsupported keys: {sorted(unknown_spec)}")
        object_default = _normalize_rule(raw_spec["default"], f"object_types.{object_type}.default") if "default" in raw_spec else None
        raw_properties = raw_spec.get("properties", {})
        if not isinstance(raw_properties, dict):
            raise ValueError(f"object_types.{object_type}.properties must be object")
        properties: dict[str, Any] = {}
        for raw_name, raw_rule in raw_properties.items():
            name = _nonempty_string(raw_name, f"object_types.{object_type} property")
            properties[name] = _normalize_rule(raw_rule, f"object_types.{object_type}.properties.{name}")
        objects[object_type] = {"default": object_default, "properties": properties}
    return {"schema": POLICY_SCHEMA, "default": default, "object_types": objects}


def load_policy(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("policy must be UTF-8 JSON") from exc
    normalized = normalize_policy(parsed)
    normalized["policy_ref"] = str(path)
    normalized["policy_fingerprint"] = fingerprint_bytes(raw)
    return normalized


def policy_from_project(project_root: Path) -> dict[str, Any] | None:
    from project_adapter import resolve_contract  # noqa: WPS433
    resolution = resolve_contract(project_root)
    entry = resolution.get("paths", {}).get(POLICY_PATH_KEY)
    if entry is None:
        return None
    if entry.get("kind") != "file" or not entry.get("exists"):
        raise ValueError("configured paths.property_write_policy must resolve to an existing file")
    return load_policy(Path(entry["absolute"]))


def _resolved_rule(policy: dict[str, Any], object_type: str, property_name: str) -> tuple[dict[str, str], str]:
    object_type = _nonempty_string(object_type, "object_type")
    property_name = _nonempty_string(property_name, "property_name")
    spec = policy["object_types"].get(object_type)
    if spec is not None:
        prop = spec["properties"].get(property_name)
        if prop is not None:
            return prop, "property_override"
        if spec["default"] is not None:
            return spec["default"], "object_default"
    return policy["default"], "global_default"


def _route(mutation_class: str, writer_class: str) -> tuple[str, str, list[str]]:
    if writer_class not in WRITER_CLASSES:
        raise ValueError(f"writer_class must be one of {sorted(WRITER_CLASSES)}")

    if mutation_class == "locked":
        return "deny", "none", ["ordinary_mutation_forbidden"]
    if mutation_class == "runtime_only":
        if writer_class == "runtime":
            return "allow_direct", "runtime_non_authoritative", ["runtime_scope"]
        return "deny", "none", ["runtime_writer_required"]
    if mutation_class == "mixed_reconcile":
        if writer_class == "runtime":
            return "deny", "none", ["runtime_cannot_reconcile_story_authority"]
        return "reconcile_required", "none", ["typed_reconcile", "expected_before"]
    if mutation_class == "proposal_only":
        if writer_class == "runtime":
            return "deny", "none", ["runtime_cannot_write_proposal_owned_property"]
        return "proposal_required", "none", ["proposal_route"]
    if mutation_class == "derived_only":
        if writer_class == "derived_rebuilder":
            return "allow_direct", "derived_non_authoritative", ["source_refs", "source_fingerprints", "expected_before"]
        if writer_class in {"user", "authorized_human", "semantic_worker"}:
            return "proposal_required", "none", ["proposal_route"]
        return "deny", "none", ["derived_rebuilder_required"]
    if mutation_class == "settlement_only":
        if writer_class == "settlement":
            return "allow_direct", "settled_authority", ["accepted_evidence", "expected_before", "settlement_receipt"]
        if writer_class in {"user", "authorized_human"}:
            return "settlement_required", "none", ["accepted_or_explicit_instruction", "expected_before"]
        if writer_class == "semantic_worker":
            return "proposal_required", "none", ["proposal_route", "no_canon_write"]
        return "deny", "none", ["settlement_writer_required"]
    if mutation_class == "user_declared":
        if writer_class in {"user", "authorized_human"}:
            return "allow_direct", "user_declared_authority", ["explicit_user_evidence", "expected_before"]
        if writer_class == "settlement":
            return "allow_direct", "settled_authority", ["accepted_evidence", "expected_before", "settlement_receipt"]
        if writer_class == "semantic_worker":
            return "proposal_required", "none", ["proposal_route", "no_authority_inference"]
        return "deny", "none", ["user_or_settlement_writer_required"]
    raise ValueError(f"unknown mutation_class: {mutation_class}")


def evaluate(policy: dict[str, Any] | None, object_type: str, property_name: str, writer_class: str) -> dict[str, Any]:
    object_type = _nonempty_string(object_type, "object_type")
    property_name = _nonempty_string(property_name, "property_name")
    writer_class = _nonempty_string(writer_class, "writer_class")
    if writer_class not in WRITER_CLASSES:
        raise ValueError(f"writer_class must be one of {sorted(WRITER_CLASSES)}")

    if policy is None:
        return {
            "schema": DECISION_SCHEMA,
            "policy_status": "absent",
            "policy_ref": None,
            "policy_fingerprint": None,
            "object_type": object_type,
            "property_name": property_name,
            "writer_class": writer_class,
            "mutation_class": None,
            "resolution_source": None,
            "decision": "legacy_unmanaged",
            "direct_write_allowed": None,
            "authority_effect": "unchanged_legacy_behavior",
            "ui_direct_editable": None,
            "requirements": [],
            "write_route_authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
            "model_execution": False,
        }

    normalized = normalize_policy({
        "schema": policy.get("schema"),
        "default": policy.get("default"),
        "object_types": policy.get("object_types", {}),
    })
    normalized["policy_ref"] = policy.get("policy_ref")
    normalized["policy_fingerprint"] = policy.get("policy_fingerprint") or fingerprint_bytes(canonical(normalized))
    rule, source = _resolved_rule(normalized, object_type, property_name)
    mutation_class = rule["mutation_class"]
    decision, authority_effect, requirements = _route(mutation_class, writer_class)
    ui_editable = mutation_class == "user_declared"
    return {
        "schema": DECISION_SCHEMA,
        "policy_status": "configured",
        "policy_ref": normalized.get("policy_ref"),
        "policy_fingerprint": normalized.get("policy_fingerprint"),
        "object_type": object_type,
        "property_name": property_name,
        "writer_class": writer_class,
        "mutation_class": mutation_class,
        "resolution_source": source,
        "decision": decision,
        "direct_write_allowed": decision == "allow_direct",
        "authority_effect": authority_effect,
        "ui_direct_editable": ui_editable,
        "requirements": requirements,
        "write_route_authority": True,
        "canon_authority": False,
        "framework_write_authority": False,
        "model_execution": False,
    }


def evaluate_request(policy: dict[str, Any] | None, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("request must be object")
    allowed = {"object_type", "property_name", "writer_class"}
    unknown = set(request) - allowed
    if unknown:
        raise ValueError(f"request has unsupported fields: {sorted(unknown)}")
    return evaluate(policy, request.get("object_type"), request.get("property_name"), request.get("writer_class"))


def _fixture_policy() -> dict[str, Any]:
    return normalize_policy({
        "schema": POLICY_SCHEMA,
        "default": {"mutation_class": "proposal_only"},
        "object_types": {
            "CHAR": {
                "default": {"mutation_class": "settlement_only"},
                "properties": {
                    "display_name": {"mutation_class": "user_declared"},
                    "birth": {"mutation_class": "locked"},
                    "working_summary": {"mutation_class": "derived_only"},
                    "runtime_focus": {"mutation_class": "runtime_only"},
                    "ambiguous_status": {"mutation_class": "mixed_reconcile"},
                },
            }
        },
    })


def self_test() -> int:
    policy = _fixture_policy()
    policy["policy_ref"] = "fixture:property-policy"
    policy["policy_fingerprint"] = fingerprint_bytes(canonical(policy))

    semantic_state = evaluate(policy, "CHAR", "current_location", "semantic_worker")
    settlement_state = evaluate(policy, "CHAR", "current_location", "settlement")
    derived_direct = evaluate(policy, "CHAR", "working_summary", "derived_rebuilder")
    derived_user = evaluate(policy, "CHAR", "working_summary", "user")
    user_direct = evaluate(policy, "CHAR", "display_name", "user")
    locked = evaluate(policy, "CHAR", "birth", "settlement")
    mixed = evaluate(policy, "CHAR", "ambiguous_status", "user")
    runtime_direct = evaluate(policy, "CHAR", "runtime_focus", "runtime")
    broad_default = evaluate(policy, "CHAR", "unlisted_state", "settlement")
    global_default = evaluate(policy, "ORG", "mission", "semantic_worker")
    legacy = evaluate(None, "CHAR", "current_location", "semantic_worker")

    payload_escalation_blocked = False
    try:
        evaluate_request(policy, {
            "object_type": "CHAR",
            "property_name": "birth",
            "writer_class": "semantic_worker",
            "direct_write_allowed": True,
        })
    except ValueError:
        payload_escalation_blocked = True

    tampered_class_blocked = False
    try:
        normalize_policy({"schema": POLICY_SCHEMA, "default": {"mutation_class": "anything_goes"}})
    except ValueError:
        tampered_class_blocked = True

    checks = {
        "semantic_worker_settlement_only_is_proposal": semantic_state["decision"] == "proposal_required" and not semantic_state["direct_write_allowed"],
        "settlement_only_allows_settlement_with_guards": settlement_state["decision"] == "allow_direct" and {"accepted_evidence", "expected_before", "settlement_receipt"}.issubset(set(settlement_state["requirements"])),
        "derived_only_is_non_authoritative": derived_direct["decision"] == "allow_direct" and derived_direct["authority_effect"] == "derived_non_authoritative" and derived_user["decision"] == "proposal_required",
        "payload_cannot_self_escalate": payload_escalation_blocked,
        "ui_editability_comes_from_policy": user_direct["ui_direct_editable"] is True and settlement_state["ui_direct_editable"] is False and locked["ui_direct_editable"] is False,
        "mixed_writer_routes_to_reconcile": mixed["decision"] == "reconcile_required",
        "broad_object_default_works": broad_default["resolution_source"] == "object_default" and broad_default["decision"] == "allow_direct",
        "explicit_user_fact_can_remain_low_ceremony": user_direct["decision"] == "allow_direct" and user_direct["authority_effect"] == "user_declared_authority",
        "policy_absence_preserves_legacy_behavior": legacy["decision"] == "legacy_unmanaged" and legacy["direct_write_allowed"] is None,
        "locked_rejects_ordinary_settlement": locked["decision"] == "deny",
        "runtime_is_noncanon_and_scoped": runtime_direct["decision"] == "allow_direct" and runtime_direct["authority_effect"] == "runtime_non_authoritative",
        "global_default_is_deterministic": global_default["resolution_source"] == "global_default" and global_default["decision"] == "proposal_required",
        "unknown_mutation_class_blocked": tampered_class_blocked,
        "route_authority_is_scoped": all(x["canon_authority"] is False and x["framework_write_authority"] is False and x["model_execution"] is False for x in [semantic_state, settlement_state, derived_direct, user_direct, locked, mixed, runtime_direct, legacy]) and semantic_state["write_route_authority"] is True and legacy["write_route_authority"] is False,
    }
    ok = all(checks.values())
    result = {
        "property_write_policy_contract": "PASS" if ok else "FAIL",
        "schema": POLICY_SCHEMA,
        "decision_schema": DECISION_SCHEMA,
        "mutation_classes": sorted(MUTATION_CLASSES),
        "writer_classes": sorted(WRITER_CLASSES),
        **checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge property-level write-source policy resolver")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--policy")
    validate.add_argument("--project-root")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--policy")
    resolve.add_argument("--project-root")
    resolve.add_argument("--object-type", required=True)
    resolve.add_argument("--property", required=True)
    resolve.add_argument("--writer-class", required=True, choices=sorted(WRITER_CLASSES))
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        return self_test()

    if bool(args.policy) == bool(args.project_root):
        raise ValueError("provide exactly one of --policy or --project-root")
    policy = load_policy(Path(args.policy)) if args.policy else policy_from_project(Path(args.project_root))

    if args.command == "validate":
        result = {
            "schema": "novelforge_property_write_policy_validation_v1",
            "valid": True,
            "policy_status": "absent" if policy is None else "configured",
            "policy_ref": None if policy is None else policy.get("policy_ref"),
            "policy_fingerprint": None if policy is None else policy.get("policy_fingerprint"),
            "write_route_authority": policy is not None,
            "canon_authority": False,
            "framework_write_authority": False,
            "model_execution": False,
        }
    else:
        result = evaluate(policy, args.object_type, args.property, args.writer_class)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
