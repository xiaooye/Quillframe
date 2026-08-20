from __future__ import annotations

import json
from typing import Any

from harness.context_runtime import MANDATORY_PRODUCTION_MECHANISMS, fingerprint

PRODUCTION_BUNDLE_SCHEMA = "quillframe_production_context_bundle_v1"
PRODUCTION_STAGE_RESULT_SCHEMA = "quillframe_production_stage_result_v1"
PRODUCTION_EXECUTION_SCHEMA = "quillframe_production_execution_result_v1"
PRODUCTION_STATUS_SCHEMA = "quillframe_production_run_status_v1"

# The semantic Context Runtime already has a stable stage vocabulary. Production
# mechanisms bind to that vocabulary rather than inventing a second selector
# ontology. Every worker receives exactly one frozen stage projection.
MECHANISM_CONTEXT_STAGE: dict[str, str] = {
    "story_canon_preflight": "story_canon_preflight",
    "scene_simulation": "scene_simulation",
    "character_simulation": "character_simulation",
    "reader_pressure": "reader_pressure",
    "event_first_raw_draft": "draft",
    "surface_realization": "surface_realization",
    "reader_engagement": "reader_engagement",
    "continuity": "continuity",
    "independent_semantic_gate": "independent_review",
    "user_visible_gate": "independent_review",
}

PRODUCTION_MECHANISMS = tuple(
    mechanism for mechanism in MANDATORY_PRODUCTION_MECHANISMS if mechanism != "context_freeze"
)

if set(PRODUCTION_MECHANISMS) != set(MECHANISM_CONTEXT_STAGE):
    missing = sorted(set(PRODUCTION_MECHANISMS) - set(MECHANISM_CONTEXT_STAGE))
    extra = sorted(set(MECHANISM_CONTEXT_STAGE) - set(PRODUCTION_MECHANISMS))
    raise RuntimeError(f"production/context stage mapping drift: missing={missing}, extra={extra}")

_SECRET_KEYS = {
    "token", "access_token", "api_key", "apikey", "password", "secret",
    "authorization", "credential", "credential_value",
}


class ProductionRunError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def secret_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            child_path = f"{path}.{key}"
            if normalized in _SECRET_KEYS:
                found.append(child_path)
            found.extend(secret_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(secret_paths(child, f"{path}[{index}]"))
    return found


def assert_secret_free(value: Any, *, label: str) -> None:
    paths = secret_paths(value)
    if paths:
        raise ProductionRunError("secret_boundary_violation", f"{label} contains forbidden secret-bearing fields", detail=paths)


def parse_json_object(text: str, *, label: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProductionRunError("semantic_output_invalid", f"{label} did not return one JSON object", detail=str(exc)) from exc
    if not isinstance(value, dict):
        raise ProductionRunError("semantic_output_invalid", f"{label} result must be an object")
    assert_secret_free(value, label=label)
    return value


def public_stage_result(
    *,
    mechanism: str,
    context_stage_id: str,
    context_bundle_fingerprint: str,
    freeze_fingerprint: str,
    stage_context_fingerprint: str,
    agent_input_fingerprint: str,
    model_service_id: str,
    model_id: str,
    protocol: str,
    judgment: dict[str, Any],
) -> dict[str, Any]:
    # Raw draft text and private simulation payloads are deliberately absent.
    public_judgment = {
        "status": judgment.get("status"),
        "summary": judgment.get("summary"),
        "findings": judgment.get("findings", []),
        "artifact_fingerprint": judgment.get("artifact_fingerprint"),
    }
    result = {
        "schema": PRODUCTION_STAGE_RESULT_SCHEMA,
        "mechanism": mechanism,
        "context_stage_id": context_stage_id,
        "context_bundle_fingerprint": context_bundle_fingerprint,
        "freeze_fingerprint": freeze_fingerprint,
        "stage_context_fingerprint": stage_context_fingerprint,
        "agent_input_fingerprint": agent_input_fingerprint,
        "model_service_id": model_service_id,
        "model_id": model_id,
        "protocol": protocol,
        "judgment": public_judgment,
        "private_reasoning_exposed": False,
        "raw_draft_visible": False,
        "authority": False,
    }
    result["stage_result_fingerprint"] = fingerprint(result)
    return result
