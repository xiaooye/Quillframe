"""Typed, fingerprint-bound evidence for an author-approved fiction audition.

This module never runs a canary and never decides literary quality. It checks
that an explicit author selection binds a pre-approved cost plan, every exact
model/scene artifact, both candidate presentation orders, and the selected
provider-visible model version.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .contracts import fingerprint

SCHEMA = "quillframe_fiction_audition_confirmation_v2"
PLAN_SCHEMA = "quillframe_fiction_audition_plan_v1"
ARTIFACT_SCHEMA = "quillframe_fiction_audition_artifact_v1"
PRESENTATION_SCHEMA = "quillframe_fiction_blind_presentation_receipt_v1"
SELECTION_SCHEMA = "quillframe_fiction_author_selection_receipt_v1"


def _text(value: Any, name: str, *, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"fiction audition {name} must be non-empty text")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"fiction audition {name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"fiction audition {name} must be sha256:<64 hex>") from exc
    return value


def _fingerprinted(value: dict[str, Any], key: str, name: str) -> None:
    supplied = _sha(value.get(key), f"{name}.{key}")
    expected = fingerprint({field: item for field, item in value.items() if field != key})
    if supplied != expected:
        raise ValueError(f"fiction audition {name} fingerprint mismatch")


def _plan(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"fiction audition plan must use {PLAN_SCHEMA}")
    exact = {
        "schema", "plan_id", "candidate_models", "scene_fingerprints",
        "voice_source_fingerprints", "max_output_tokens", "max_cost_micros",
        "approved_call_count", "author_cost_authorization_ref", "authority",
        "plan_fingerprint",
    }
    if set(value) != exact or value.get("authority") is not False:
        raise ValueError("fiction audition plan fields/authority invalid")
    _text(value.get("plan_id"), "plan.plan_id", maximum=160)
    _text(value.get("author_cost_authorization_ref"), "plan.author_cost_authorization_ref")
    models = value.get("candidate_models")
    if not isinstance(models, list) or len(models) < 2:
        raise ValueError("fiction audition plan requires at least two candidate models")
    model_versions: list[str] = []
    identities: set[tuple[str, str]] = set()
    for index, model in enumerate(models):
        if not isinstance(model, dict) or set(model) != {
            "service_id", "model_id", "model_version_fingerprint"
        }:
            raise ValueError(f"fiction audition plan candidate_models[{index}] invalid")
        identity = (
            _text(model.get("service_id"), "candidate.service_id", maximum=160),
            _text(model.get("model_id"), "candidate.model_id", maximum=500),
        )
        version = _sha(
            model.get("model_version_fingerprint"),
            f"candidate_models[{index}].model_version_fingerprint",
        )
        if identity in identities or version in model_versions:
            raise ValueError("fiction audition plan candidate identities/versions must be unique")
        identities.add(identity)
        model_versions.append(version)
    scenes = value.get("scene_fingerprints")
    if (
        not isinstance(scenes, list)
        or not scenes
        or len(scenes) != len(set(scenes))
    ):
        raise ValueError("fiction audition plan scenes must be a non-empty unique array")
    for index, scene in enumerate(scenes):
        _sha(scene, f"scene_fingerprints[{index}]")
    voices = value.get("voice_source_fingerprints")
    if not isinstance(voices, list) or len(voices) != len(set(voices)):
        raise ValueError("fiction audition voice sources must be a unique array")
    for index, source in enumerate(voices):
        _sha(source, f"voice_source_fingerprints[{index}]")
    for key in ("max_output_tokens", "max_cost_micros", "approved_call_count"):
        if not isinstance(value.get(key), int) or isinstance(value[key], bool) or value[key] < 1:
            raise ValueError(f"fiction audition plan {key} must be a positive integer")
    required_calls = len(models) * len(scenes)
    if value["approved_call_count"] != required_calls:
        raise ValueError("fiction audition plan call count must exactly cover model/scene candidates")
    _fingerprinted(value, "plan_fingerprint", "plan")
    return deepcopy(value)


def _artifact(value: Any, *, plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"fiction audition artifact must use {ARTIFACT_SCHEMA}")
    exact = {
        "schema", "plan_fingerprint", "scene_fingerprint",
        "model_version_fingerprint", "blind_label", "request_fingerprint",
        "output_fingerprint", "billing_receipt_fingerprint", "authority",
        "artifact_fingerprint",
    }
    if set(value) != exact or value.get("authority") is not False:
        raise ValueError("fiction audition artifact fields/authority invalid")
    if value.get("plan_fingerprint") != plan["plan_fingerprint"]:
        raise ValueError("fiction audition artifact plan binding changed")
    for key in (
        "scene_fingerprint", "model_version_fingerprint", "request_fingerprint",
        "output_fingerprint", "billing_receipt_fingerprint",
    ):
        _sha(value.get(key), f"artifact.{key}")
    _text(value.get("blind_label"), "artifact.blind_label", maximum=80)
    _fingerprinted(value, "artifact_fingerprint", "artifact")
    return deepcopy(value)


def _presentation(value: Any, *, plan: dict[str, Any], labels: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != PRESENTATION_SCHEMA:
        raise ValueError(f"fiction blind presentation must use {PRESENTATION_SCHEMA}")
    exact = {
        "schema", "plan_fingerprint", "scene_fingerprint", "order_variant",
        "ordered_blind_labels", "artifact_fingerprints", "model_identity_hidden",
        "authority", "presentation_fingerprint",
    }
    if set(value) != exact or value.get("authority") is not False:
        raise ValueError("fiction blind presentation fields/authority invalid")
    if value.get("plan_fingerprint") != plan["plan_fingerprint"]:
        raise ValueError("fiction blind presentation plan binding changed")
    _sha(value.get("scene_fingerprint"), "presentation.scene_fingerprint")
    if value.get("order_variant") not in {"forward", "reverse"}:
        raise ValueError("fiction blind presentation order_variant invalid")
    ordered = value.get("ordered_blind_labels")
    artifacts = value.get("artifact_fingerprints")
    if (
        not isinstance(ordered, list)
        or set(ordered) != labels
        or len(ordered) != len(labels)
        or not isinstance(artifacts, list)
        or len(artifacts) != len(ordered)
        or value.get("model_identity_hidden") is not True
    ):
        raise ValueError("fiction blind presentation does not cover exact hidden candidates")
    for index, artifact in enumerate(artifacts):
        _sha(artifact, f"presentation.artifact_fingerprints[{index}]")
    _fingerprinted(value, "presentation_fingerprint", "presentation")
    return deepcopy(value)


def validate_confirmation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError(f"fiction audition confirmation must use {SCHEMA}")
    exact = {
        "schema", "plan", "artifacts", "presentations", "selection",
        "authority", "confirmation_fingerprint",
    }
    if set(value) != exact or value.get("authority") is not False:
        raise ValueError("fiction audition confirmation fields/authority invalid")
    plan = _plan(value.get("plan"))
    model_versions = {
        item["model_version_fingerprint"] for item in plan["candidate_models"]
    }
    scenes = set(plan["scene_fingerprints"])
    raw_artifacts = value.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise ValueError("fiction audition artifacts must be an array")
    artifacts = [_artifact(item, plan=plan) for item in raw_artifacts]
    expected_pairs = {(scene, model) for scene in scenes for model in model_versions}
    observed_pairs = {
        (item["scene_fingerprint"], item["model_version_fingerprint"])
        for item in artifacts
    }
    if len(artifacts) != len(expected_pairs) or observed_pairs != expected_pairs:
        raise ValueError("fiction audition artifacts must cover each model/scene exactly once")
    labels_by_scene: dict[str, set[str]] = {scene: set() for scene in scenes}
    artifact_fps = {item["artifact_fingerprint"] for item in artifacts}
    for item in artifacts:
        labels_by_scene[item["scene_fingerprint"]].add(item["blind_label"])
    if any(len(labels) != len(model_versions) for labels in labels_by_scene.values()):
        raise ValueError("fiction audition blind labels must be unique within each scene")
    raw_presentations = value.get("presentations")
    if not isinstance(raw_presentations, list):
        raise ValueError("fiction audition presentations must be an array")
    presentations = [
        _presentation(item, plan=plan, labels=labels_by_scene.get(item.get("scene_fingerprint"), set()))
        for item in raw_presentations
    ]
    observed_orders = {(item["scene_fingerprint"], item["order_variant"]) for item in presentations}
    expected_orders = {(scene, order) for scene in scenes for order in ("forward", "reverse")}
    if len(presentations) != len(expected_orders) or observed_orders != expected_orders:
        raise ValueError("fiction audition requires forward and reverse blind presentations per scene")
    for item in presentations:
        if not set(item["artifact_fingerprints"]).issubset(artifact_fps):
            raise ValueError("fiction presentation cites an unknown artifact")
    for scene in scenes:
        forward = next(item for item in presentations if item["scene_fingerprint"] == scene and item["order_variant"] == "forward")
        reverse = next(item for item in presentations if item["scene_fingerprint"] == scene and item["order_variant"] == "reverse")
        if reverse["ordered_blind_labels"] != list(reversed(forward["ordered_blind_labels"])):
            raise ValueError("fiction blind presentation order was not exactly swapped")
    selection = value.get("selection")
    if not isinstance(selection, dict) or selection.get("schema") != SELECTION_SCHEMA:
        raise ValueError(f"fiction author selection must use {SELECTION_SCHEMA}")
    selection_exact = {
        "schema", "plan_fingerprint", "selected_service_id", "selected_model_id",
        "selected_model_version_fingerprint", "presentation_fingerprints",
        "author_confirmation_ref", "author_blind_selection", "authority",
        "selection_fingerprint",
    }
    if set(selection) != selection_exact or selection.get("authority") is not False:
        raise ValueError("fiction author selection fields/authority invalid")
    if selection.get("plan_fingerprint") != plan["plan_fingerprint"]:
        raise ValueError("fiction author selection plan binding changed")
    selected_identity = (
        _text(selection.get("selected_service_id"), "selection.selected_service_id", maximum=160),
        _text(selection.get("selected_model_id"), "selection.selected_model_id", maximum=500),
        _sha(selection.get("selected_model_version_fingerprint"), "selection.selected_model_version_fingerprint"),
    )
    candidates = {
        (item["service_id"], item["model_id"], item["model_version_fingerprint"])
        for item in plan["candidate_models"]
    }
    if selected_identity not in candidates:
        raise ValueError("selected fiction model was not in the approved audition plan")
    presentation_fps = selection.get("presentation_fingerprints")
    expected_presentation_fps = {item["presentation_fingerprint"] for item in presentations}
    if not isinstance(presentation_fps, list) or set(presentation_fps) != expected_presentation_fps:
        raise ValueError("author selection does not bind all blind presentations")
    _text(selection.get("author_confirmation_ref"), "selection.author_confirmation_ref")
    if selection.get("author_blind_selection") is not True:
        raise ValueError("fiction audition requires explicit blind author selection")
    _fingerprinted(selection, "selection_fingerprint", "selection")
    _fingerprinted(value, "confirmation_fingerprint", "confirmation")
    return deepcopy(value)


def selected_identity(confirmation: dict[str, Any]) -> tuple[str, str, str]:
    receipt = validate_confirmation(confirmation)
    selection = receipt["selection"]
    return (
        selection["selected_service_id"],
        selection["selected_model_id"],
        selection["selected_model_version_fingerprint"],
    )
