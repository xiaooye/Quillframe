"""Frozen writing resources and exact projections, never literary selection.

The registered scene model selects methods. This module performs no keyword,
genre, quality or semantic-relevance inference and loads no diagnostic examples.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from harness.context_runtime import fingerprint

from .contracts import ProductionRunError, assert_secret_free


REGISTRY_SCHEMA = "quillframe_craft_registry_v1"
SNAPSHOT_SCHEMA = "quillframe_craft_snapshot_v1"
WRITER_SCHEMA = "quillframe_writer_craft_v1"
COMBINED_WRITER_SCHEMA = "quillframe_writer_craft_composite_v1"
STYLE_PACK_SCHEMA = "quillframe_source_free_craft_pack_v1"
STYLE_CONTRACT_MODE = "style_contract"
OUTLINE_PLUS_STYLE_CONTRACT_MODE = "outline_plus_style_contract"
MODES = {"baseline", "outline_driven", STYLE_CONTRACT_MODE, OUTLINE_PLUS_STYLE_CONTRACT_MODE}
LANGUAGES = {"en", "zh-CN"}
CONTENT_ZONES = {"general", "adult_explicit"}
LIBRARY_ROOT = Path(__file__).resolve().parents[1] / "surface" / "craft"
STYLE_PACK_ROOT = LIBRARY_ROOT / "style_packs" / "active"
_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_FP = re.compile(r"sha256:[0-9a-f]{64}\Z")
_SNAPSHOT_KEYS = {
    "schema", "mode", "language", "registry_version", "registry_fingerprint",
    "base_card_id", "cards", "authority", "snapshot_fingerprint",
}
_CARD_KEYS = {"card_id", "kind", "version", "title", "selection_hint", "text", "content_fingerprint"}
_STYLE_SNAPSHOT_KEYS = _SNAPSHOT_KEYS | {
    "content_zone", "craft_pack_fingerprint", "writer_projection_fingerprint",
}
_COMBINED_SNAPSHOT_KEYS = {
    "schema", "mode", "language", "outline_driven", "style_contract",
    "run_scope", "authority", "snapshot_fingerprint",
}
_RUN_SCOPE_KEYS = {
    "schema", "project_id", "run_id", "chapter_id", "document_id",
    "task_mode", "manifest_fingerprint", "one_off_opt_in", "authority",
}
_STYLE_PACK_KEYS = {
    "schema", "pack_id", "version", "status", "default_mode", "content_zone",
    "writer_projection_path", "writer_projection_fingerprint", "craft_pack_fingerprint",
}
_STYLE_WRITER_CARD_KEYS = {
    "axis", "operation", "effect", "applies_when", "avoid_when",
    "failure_boundary", "content_zone",
}
_STYLE_CARD_KEYS = _STYLE_WRITER_CARD_KEYS | {"card_id", "content_fingerprint"}


def _require(condition: bool, message: str, code: str = "craft_snapshot_invalid") -> None:
    if not condition:
        raise ProductionRunError(code, message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_mode(value: Any) -> str:
    _require(isinstance(value, str) and value in MODES,
             "craft_guidance_mode must be baseline, outline_driven, style_contract, or outline_plus_style_contract",
             "invalid_args")
    return value


def _read_resource(root: Path, relative: Any, *, max_bytes: int = 64_000) -> str:
    _require(isinstance(relative, str) and bool(relative), "missing craft resource path")
    path = (root / relative).resolve()
    try:
        _require(path.is_relative_to(root.resolve()) and path.is_file(), "craft resource must stay in its library")
        _require(path.stat().st_size <= max_bytes, "craft resource exceeds the file-size bound")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProductionRunError("craft_snapshot_invalid", "craft resource could not be read") from exc


def _json_resource(root: Path, relative: str, *, max_bytes: int = 64_000) -> dict[str, Any]:
    try:
        value = json.loads(_read_resource(root, relative, max_bytes=max_bytes))
    except json.JSONDecodeError as exc:
        raise ProductionRunError("craft_snapshot_invalid", "craft resource is not JSON") from exc
    _require(isinstance(value, dict), "craft JSON resource must be an object")
    return value


def _style_selector_hint(card: dict[str, Any]) -> str:
    metadata = {key: deepcopy(card[key]) for key in _STYLE_WRITER_CARD_KEYS if key != "axis"}
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _freeze_style_pack(root: Path, *, content_zone: str) -> dict[str, Any]:
    """Load one closed writer projection; no Corpus evidence enters runtime."""

    _require(content_zone in CONTENT_ZONES, "invalid run content_zone", "invalid_args")
    pack = _json_resource(root, "pack.json")
    _require(set(pack) == _STYLE_PACK_KEYS and pack.get("schema") == STYLE_PACK_SCHEMA,
             "source-free craft pack must use the closed pack schema")
    _require(_text(pack.get("pack_id")) and bool(_ID.fullmatch(pack["pack_id"])), "invalid craft pack ID")
    _require(_text(pack.get("version")) and pack.get("status") == "candidate"
             and pack.get("default_mode") == "baseline", "craft pack cannot self-promote")
    _require(pack.get("content_zone") in CONTENT_ZONES, "invalid craft pack content zone")
    _require(pack["content_zone"] == content_zone,
             "craft pack content zone does not match the run")
    _require(_text(pack.get("writer_projection_path"))
             and pack["writer_projection_path"] != "pack.json",
             "craft pack requires a separate writer projection")
    for key in ("writer_projection_fingerprint", "craft_pack_fingerprint"):
        _require(isinstance(pack.get(key), str) and bool(_FP.fullmatch(pack[key])),
                 f"invalid {key}")
    expected_pack_fingerprint = fingerprint({
        key: value for key, value in pack.items() if key != "craft_pack_fingerprint"
    })
    _require(pack["craft_pack_fingerprint"] == expected_pack_fingerprint,
             "craft pack fingerprint changed")
    projection = _json_resource(
        root, pack["writer_projection_path"], max_bytes=128 * 1024,
    )
    # Lazy import keeps the default production path independent of Corpus
    # analysis code while reusing the exact compile_writer_projection schema.
    from corpus.style_contract import validate_writer_projection
    _require(not validate_writer_projection(projection),
             "craft pack must contain a valid compile_writer_projection output")
    _require(projection["projection_fingerprint"] == pack["writer_projection_fingerprint"],
             "writer projection fingerprint differs from its pack binding")
    _require(projection["content_zone"] == pack["content_zone"],
             "writer projection content zone differs from its pack")
    candidates = projection["craft_candidates"]
    _require(1 <= len(candidates) <= 63, "style craft pack must contain 1..63 cards")
    cards: list[dict[str, Any]] = []
    seen_content: set[str] = set()
    for candidate in candidates:
        safe = {key: deepcopy(candidate[key]) for key in _STYLE_WRITER_CARD_KEYS}
        candidate_fingerprint = fingerprint(safe)
        _require(candidate_fingerprint not in seen_content, "duplicate style craft card")
        seen_content.add(candidate_fingerprint)
        card = {
            "card_id": "style-" + candidate_fingerprint.removeprefix("sha256:")[:24],
            **safe,
        }
        card["content_fingerprint"] = fingerprint(card)
        cards.append(card)
    cards.sort(key=lambda card: (card["axis"], card["card_id"]))
    return {
        "registry_version": pack["version"],
        "registry_fingerprint": pack["craft_pack_fingerprint"],
        "base_card_id": "style-contract",
        "cards": cards,
        "content_zone": pack["content_zone"],
        "craft_pack_fingerprint": pack["craft_pack_fingerprint"],
        "writer_projection_fingerprint": pack["writer_projection_fingerprint"],
    }


def _validate_run_scope_manifest(
    root: Path, run_scope: dict[str, Any], style_snapshot: dict[str, Any],
) -> None:
    manifest = _json_resource(root, "run-scope-manifest.json", max_bytes=128 * 1024)
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_fingerprint"}
    _require(manifest.get("schema") in {
        "quillframe_run_scoped_style_pack_manifest_v1",
        "quillframe_run_scoped_style_pack_manifest_v2",
    } and manifest.get("manifest_fingerprint") == run_scope["manifest_fingerprint"]
    and manifest.get("manifest_fingerprint") == fingerprint(unsigned),
    "run-scoped style manifest fingerprint changed")
    scope = manifest.get("run_scope") or {}
    _require(scope.get("project_id") == run_scope["project_id"]
             and scope.get("chapter_id") == run_scope["chapter_id"]
             and scope.get("document_id") == run_scope["document_id"]
             and run_scope["task_mode"] in scope.get("allowed_task_modes", [])
             and scope.get("one_off_opt_in") is True,
             "run-scoped style manifest target changed")
    _require(manifest.get("bounded_writer_projection_fingerprint")
             == style_snapshot["writer_projection_fingerprint"]
             and manifest.get("bounded_craft_pack_fingerprint")
             == style_snapshot["craft_pack_fingerprint"],
             "run-scoped style manifest pack binding changed")
    for filename, field in (
        ("writer_projection.json", "projection_file_fingerprint"),
        ("pack.json", "pack_file_fingerprint"),
    ):
        raw = _read_resource(root, filename, max_bytes=128 * 1024).encode("utf-8")
        _require(manifest.get(field) == "sha256:" + hashlib.sha256(raw).hexdigest(),
                 "run-scoped style pack file changed")
    gate = manifest.get("semantic_leakage_gate") or {}
    _require(gate.get("status") == "pass" and gate.get("independent") is True
             and gate.get("performed") is True,
             "run-scoped style pack requires independent semantic leakage evidence")
    _require(manifest.get("raw_source_persisted") is False
             and manifest.get("source_identity_included") is False
             and manifest.get("authority") is False
             and manifest.get("activation_performed") is False
             and manifest.get("promotion_performed") is False
             and manifest.get("publication_performed") is False,
             "run-scoped style manifest crossed its authority boundary")


def freeze_craft_library(
    mode: str = "baseline",
    *,
    language: str = "zh-CN",
    root: Path | None = None,
    style_pack_root: Path | None = None,
    run_scope: dict[str, Any] | None = None,
    content_zone: str = "general",
) -> dict[str, Any]:
    """Read once before dispatch; only explicit opt-in loads candidate methods."""
    validate_mode(mode)
    _require(isinstance(language, str) and language in LANGUAGES, "unsupported craft language")
    if mode == OUTLINE_PLUS_STYLE_CONTRACT_MODE:
        _require(isinstance(style_pack_root, (str, Path)),
                 "combined craft requires a run-scoped style pack root", "invalid_args")
        _require(isinstance(run_scope, dict) and set(run_scope) == _RUN_SCOPE_KEYS,
                 "combined craft requires a closed one-run scope", "invalid_args")
        _require(run_scope.get("schema") == "quillframe_run_scoped_craft_binding_v1"
                 and all(_text(run_scope.get(key)) for key in (
                     "project_id", "run_id", "chapter_id", "document_id", "task_mode",
                 )) and run_scope.get("task_mode") in {"DRAFT", "REVISE"}
                 and isinstance(run_scope.get("manifest_fingerprint"), str)
                 and bool(_FP.fullmatch(run_scope["manifest_fingerprint"]))
                 and run_scope.get("one_off_opt_in") is True
                 and run_scope.get("authority") is False,
                 "combined craft run scope is invalid", "invalid_args")
        outline = freeze_craft_library(
            "outline_driven", language=language, root=root, content_zone=content_zone,
        )
        style = freeze_craft_library(
            STYLE_CONTRACT_MODE, language=language, root=style_pack_root,
            content_zone=content_zone,
        )
        _validate_run_scope_manifest(Path(style_pack_root), run_scope, style)
        # scene.realization_project has a fixed semantic catalog budget. The
        # foundation is Writer-only and therefore is not counted here.
        method_count = sum(card["kind"] == "method" for card in outline["cards"])
        _require(method_count + len(style["cards"]) <= 63,
                 "combined craft catalog exceeds 63 cards")
        combined = {
            "schema": SNAPSHOT_SCHEMA, "mode": mode, "language": language,
            "outline_driven": outline, "style_contract": style,
            "run_scope": deepcopy(run_scope), "authority": False,
        }
        combined["snapshot_fingerprint"] = fingerprint(combined)
        validate_craft_snapshot(combined)
        return combined

    _require(run_scope is None, "run_scope is only valid for the combined mode", "invalid_args")
    snapshot: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA, "mode": mode, "language": language,
        "registry_version": None, "registry_fingerprint": None,
        "base_card_id": None, "cards": [], "authority": False,
    }
    if mode == "outline_driven":
        root = LIBRARY_ROOT if root is None else Path(root)
        try:
            registry = json.loads(_read_resource(root, "registry.json"))
        except json.JSONDecodeError as exc:
            raise ProductionRunError("craft_snapshot_invalid", "craft registry is not JSON") from exc
        _require(isinstance(registry, dict) and registry.get("schema") == REGISTRY_SCHEMA, "invalid craft registry")
        _require(registry.get("status") == "candidate" and registry.get("default_mode") == "baseline",
                 "candidate library cannot promote itself to the default")
        _require(_text(registry.get("version")) and isinstance(registry.get("cards"), list)
                 and 1 <= len(registry["cards"]) <= 64, "invalid craft version or cards")
        snapshot.update(registry_version=registry["version"], registry_fingerprint=fingerprint(registry),
                        base_card_id=registry.get("base_card_id"))
        for entry in registry["cards"]:
            _require(isinstance(entry, dict), "invalid craft entry")
            paths, titles, hints = (entry.get(key) for key in ("writer_paths", "title", "selection_hint"))
            _require(all(isinstance(value, dict) and language in value for value in (paths, titles, hints)),
                     "craft entry needs a writer resource and localized metadata")
            _require(paths[language] == f"cards/{entry.get('id')}.{language}.md", "only positive card resources may reach Writer")
            # Only writer_paths are read. Diagnostics and source inventories are
            # human-facing research, never an implicit source of Writer prompts.
            card = {"card_id": entry.get("id"), "kind": entry.get("kind"), "version": entry.get("version"),
                    "title": titles[language], "selection_hint": hints[language],
                    "text": _read_resource(root, paths[language])}
            card["content_fingerprint"] = fingerprint(card)
            snapshot["cards"].append(card)
    elif mode == STYLE_CONTRACT_MODE:
        _require(style_pack_root is None,
                 "style_pack_root is only valid for the combined mode", "invalid_args")
        root = STYLE_PACK_ROOT if root is None else Path(root)
        snapshot.update(_freeze_style_pack(root, content_zone=content_zone))
    snapshot["snapshot_fingerprint"] = fingerprint(snapshot)
    validate_craft_snapshot(snapshot)
    return snapshot


def validate_craft_snapshot(snapshot: Any) -> None:
    """Validate the frozen bytes, not current files or a claimed craft verdict."""
    _require(isinstance(snapshot, dict), "craft snapshot must be an object")
    mode = snapshot.get("mode")
    expected_keys = (
        _COMBINED_SNAPSHOT_KEYS if mode == OUTLINE_PLUS_STYLE_CONTRACT_MODE
        else _STYLE_SNAPSHOT_KEYS if mode == STYLE_CONTRACT_MODE
        else _SNAPSHOT_KEYS
    )
    _require(set(snapshot) == expected_keys, "craft snapshot must be closed and complete")
    _require(snapshot["schema"] == SNAPSHOT_SCHEMA and snapshot["authority"] is False, "invalid craft authority or schema")
    validate_mode(snapshot["mode"])
    _require(isinstance(snapshot["language"], str) and snapshot["language"] in LANGUAGES, "invalid craft language")
    _require(snapshot["snapshot_fingerprint"] == fingerprint({key: value for key, value in snapshot.items()
                                                              if key != "snapshot_fingerprint"}), "craft snapshot hash changed")
    assert_secret_free(snapshot, label="craft snapshot")
    if mode == OUTLINE_PLUS_STYLE_CONTRACT_MODE:
        outline = snapshot["outline_driven"]
        style = snapshot["style_contract"]
        validate_craft_snapshot(outline)
        validate_craft_snapshot(style)
        _require(outline["mode"] == "outline_driven" and style["mode"] == STYLE_CONTRACT_MODE,
                 "combined craft snapshot has invalid nested modes")
        _require(outline["language"] == snapshot["language"] == style["language"],
                 "combined craft snapshot languages differ")
        run_scope = snapshot["run_scope"]
        _require(isinstance(run_scope, dict) and set(run_scope) == _RUN_SCOPE_KEYS
                 and run_scope.get("schema") == "quillframe_run_scoped_craft_binding_v1"
                 and run_scope.get("task_mode") in {"DRAFT", "REVISE"}
                 and all(_text(run_scope.get(key)) for key in (
                     "project_id", "run_id", "chapter_id", "document_id",
                 )) and isinstance(run_scope.get("manifest_fingerprint"), str)
                 and bool(_FP.fullmatch(run_scope["manifest_fingerprint"]))
                 and run_scope.get("one_off_opt_in") is True
                 and run_scope.get("authority") is False,
                 "combined craft run scope changed")
        methods = sum(card["kind"] == "method" for card in outline["cards"])
        _require(methods + len(style["cards"]) <= 63,
                 "combined craft catalog exceeds 63 cards")
        return
    _require(isinstance(snapshot["cards"], list) and len(snapshot["cards"]) <= 64, "invalid craft inventory")
    if snapshot["mode"] == "baseline":
        _require(not snapshot["cards"] and all(snapshot[key] is None for key in
                 ("registry_version", "registry_fingerprint", "base_card_id")), "baseline cannot contain candidate guidance")
        return
    if snapshot["mode"] == STYLE_CONTRACT_MODE:
        _require(_text(snapshot["registry_version"]), "invalid style craft pack version")
        for key in (
            "registry_fingerprint", "craft_pack_fingerprint",
            "writer_projection_fingerprint",
        ):
            _require(isinstance(snapshot[key], str) and bool(_FP.fullmatch(snapshot[key])),
                     f"invalid style snapshot {key}")
        _require(snapshot["registry_fingerprint"] == snapshot["craft_pack_fingerprint"],
                 "style registry and craft pack binding differ")
        _require(snapshot["base_card_id"] == "style-contract",
                 "invalid style selector base binding")
        _require(snapshot["content_zone"] in CONTENT_ZONES,
                 "invalid style snapshot content zone")
        _require(1 <= len(snapshot["cards"]) <= 63,
                 "style snapshot requires 1..63 cards")
        from corpus.style_contract import MAX_SHORT_TEXT_CHARS, STYLE_AXES
        seen_style_ids: set[str] = set()
        for card in snapshot["cards"]:
            _require(isinstance(card, dict) and set(card) == _STYLE_CARD_KEYS,
                     "invalid frozen style craft card")
            _require(card["axis"] in STYLE_AXES, "invalid style craft axis")
            _require(card["content_zone"] == snapshot["content_zone"],
                     "style card crosses its frozen content zone")
            for key in ("operation", "effect", "failure_boundary"):
                _require(_text(card[key]) and len(card[key]) <= MAX_SHORT_TEXT_CHARS,
                         f"invalid style craft {key}")
            for key in ("applies_when", "avoid_when"):
                value = card[key]
                _require(isinstance(value, list) and 1 <= len(value) <= 16
                         and all(_text(item) and len(item) <= MAX_SHORT_TEXT_CHARS for item in value),
                         f"invalid style craft {key}")
                _require(len(value) == len(set(value)),
                         f"invalid style craft {key}")
            card_id = card["card_id"]
            _require(isinstance(card_id, str) and bool(_ID.fullmatch(card_id))
                     and card_id not in seen_style_ids,
                     "duplicate or invalid style craft ID")
            seen_style_ids.add(card_id)
            unsigned = {key: value for key, value in card.items()
                        if key != "content_fingerprint"}
            _require(card["content_fingerprint"] == fingerprint(unsigned),
                     "style craft content hash changed")
            safe = {key: card[key] for key in _STYLE_WRITER_CARD_KEYS}
            expected_id = "style-" + fingerprint(safe).removeprefix("sha256:")[:24]
            _require(card_id == expected_id, "style craft route binding changed")
        return
    _require(_text(snapshot["registry_version"]) and isinstance(snapshot["registry_fingerprint"], str)
             and bool(_FP.fullmatch(snapshot["registry_fingerprint"])), "invalid registry binding")
    seen: set[str] = set()
    foundations: list[str] = []
    for card in snapshot["cards"]:
        _require(isinstance(card, dict) and set(card) == _CARD_KEYS, "invalid frozen craft card")
        card_id = card["card_id"]
        _require(isinstance(card_id, str) and bool(_ID.fullmatch(card_id)) and card_id not in seen, "duplicate or invalid craft ID")
        seen.add(card_id)
        _require(isinstance(card["kind"], str) and card["kind"] in {"foundation", "method"}, "invalid craft kind")
        _require(all(_text(card[key]) for key in ("version", "title", "selection_hint", "text")), "empty craft content")
        _require(len(card["text"].encode("utf-8")) <= 64_000, "craft text exceeds the file-size bound")
        _require(card["content_fingerprint"] == fingerprint({key: value for key, value in card.items()
                                                            if key != "content_fingerprint"}), "craft content hash changed")
        if card["kind"] == "foundation":
            foundations.append(card_id)
    _require(foundations == [snapshot["base_card_id"]], "exactly one registered foundation is required")


def planning_sources(frozen_scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Project only current, already selected scene-stage planning sources."""
    _require(isinstance(frozen_scene, dict) and frozen_scene.get("mechanism") == "scene_simulation",
             "craft planning requires the frozen scene stage")
    sources = []
    seen: set[str] = set()
    for item in frozen_scene.get("items", []):
        if item.get("object_type") not in {"plan", "story_node"}:
            continue
        if item.get("authority") != "active_plan" or item.get("lifecycle") != "active_plan":
            continue
        source_ref = "plan:" + str(item["object_id"])
        _require(source_ref not in seen, "duplicate planning source")
        seen.add(source_ref)
        sources.append({"source_ref": source_ref, "source_fingerprint": item["source_fingerprint"],
                        "authority": "active_plan", "kind": item["object_type"], "content": deepcopy(item["model_view"])})
    return sources


def _catalog(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot["mode"] == OUTLINE_PLUS_STYLE_CONTRACT_MODE:
        outline_catalog = _catalog(snapshot["outline_driven"])
        style_catalog = _catalog(snapshot["style_contract"])
        style_cards = deepcopy(style_catalog["cards"])
        for card in style_cards:
            hint = json.loads(card["selection_hint"])
            hint["route_class"] = "run_scoped_corpus_style"
            hint["composite_requirement"] = (
                "Select at least one and at most eight Corpus style cards that genuinely apply."
            )
            card["selection_hint"] = json.dumps(
                hint, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
            card["utf8_bytes"] = len(card["selection_hint"].encode("utf-8"))
        cards = outline_catalog["cards"] + style_cards
        _require(len(cards) <= 63, "combined craft catalog exceeds 63 cards")
        return {
            "snapshot_fingerprint": snapshot["snapshot_fingerprint"],
            "language": snapshot["language"],
            "base_card_id": snapshot["outline_driven"]["base_card_id"],
            "cards": cards,
        }
    if snapshot["mode"] == STYLE_CONTRACT_MODE:
        return {
            "snapshot_fingerprint": snapshot["snapshot_fingerprint"],
            "language": snapshot["language"],
            "base_card_id": snapshot["base_card_id"],
            "cards": [
                {
                    "card_id": card["card_id"],
                    "title": card["axis"],
                    "selection_hint": _style_selector_hint(card),
                    "utf8_bytes": len(_style_selector_hint(card).encode("utf-8")),
                }
                for card in snapshot["cards"]
            ],
        }
    return {
        "snapshot_fingerprint": snapshot["snapshot_fingerprint"], "language": snapshot["language"],
        "base_card_id": snapshot["base_card_id"],
        "cards": [{"card_id": card["card_id"], "title": card["title"], "selection_hint": card["selection_hint"],
                   "utf8_bytes": len(card["text"].encode("utf-8"))}
                  for card in snapshot["cards"] if card["kind"] == "method"],
    }


def selection_input(snapshot: dict[str, Any], frozen_scene: dict[str, Any]) -> dict[str, Any]:
    validate_craft_snapshot(snapshot)
    if snapshot["mode"] == "baseline":
        return {}
    if snapshot["mode"] == STYLE_CONTRACT_MODE:
        return {"craft_catalog": _catalog(snapshot)}
    return {
        "craft_catalog": _catalog(snapshot),
        "planning_context": planning_sources(frozen_scene),
    }


def _materialize_combined_writer_craft(
    snapshot: dict[str, Any], selection: list[dict[str, Any]], *,
    projection_input: dict[str, Any], binding_fingerprint: str,
) -> dict[str, Any]:
    """Materialize V3 and Corpus independently after one semantic selection."""
    _require(projection_input.get("craft_catalog") == _catalog(snapshot),
             "selection catalog differs from the frozen library", "semantic_output_invalid")
    outline = snapshot["outline_driven"]
    style = snapshot["style_contract"]
    outline_ids = {
        card["card_id"] for card in outline["cards"] if card["kind"] == "method"
    }
    style_ids = {card["card_id"] for card in style["cards"]}
    outline_selection: list[dict[str, Any]] = []
    style_selection: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in selection:
        _require(isinstance(item, dict), "invalid craft selection entry", "semantic_output_invalid")
        card_id = item.get("card_id")
        _require(isinstance(card_id, str) and card_id not in seen,
                 "craft selection cites an unknown or repeated method", "semantic_output_invalid")
        seen.add(card_id)
        if card_id in outline_ids:
            outline_selection.append(item)
        elif card_id in style_ids:
            style_selection.append(item)
        else:
            _require(False, "craft selection cites an unknown or repeated method", "semantic_output_invalid")
    _require(1 <= len(style_selection) <= 8,
             "combined mode requires one to eight scene-relevant Corpus style cards",
             "semantic_output_invalid")
    planning = projection_input.get("planning_context", [])
    outline_guidance = materialize_writer_craft(
        outline, outline_selection,
        projection_input={"craft_catalog": _catalog(outline), "planning_context": planning},
        binding_fingerprint=binding_fingerprint,
    )
    style_guidance = materialize_writer_craft(
        style, style_selection,
        projection_input={"craft_catalog": _catalog(style), "planning_context": planning},
        binding_fingerprint=binding_fingerprint,
    )
    _require(outline_guidance is not None, "combined guidance requires registered V3 core")
    result = {
        "schema": COMBINED_WRITER_SCHEMA,
        "language": snapshot["language"],
        "snapshot_fingerprint": snapshot["snapshot_fingerprint"],
        "selection_binding_fingerprint": binding_fingerprint,
        "registered_craft": {
            "registry_version": outline_guidance["registry_version"],
            "snapshot_fingerprint": outline_guidance["snapshot_fingerprint"],
            "cards": outline_guidance["cards"],
        },
        "corpus_style": {
            "registry_version": style["registry_version"],
            "snapshot_fingerprint": style["snapshot_fingerprint"],
            "cards": [] if style_guidance is None else style_guidance["cards"],
        },
        "authority": False,
    }
    result["guidance_fingerprint"] = fingerprint(result)
    return result


def materialize_writer_craft(snapshot: dict[str, Any], selection: Any, *,
                             projection_input: dict[str, Any], binding_fingerprint: str) -> dict[str, Any] | None:
    """Resolve exactly the model's IDs. Reasons and plan evidence stay private."""
    validate_craft_snapshot(snapshot)
    _require(isinstance(selection, list), "craft_selection must be an array", "semantic_output_invalid")
    if snapshot["mode"] == STYLE_CONTRACT_MODE:
        _require(
            len(selection) <= 8,
            "style_contract selection is limited to eight scene-relevant cards",
            "semantic_output_invalid",
        )
    if snapshot["mode"] == OUTLINE_PLUS_STYLE_CONTRACT_MODE:
        return _materialize_combined_writer_craft(
            snapshot, selection, projection_input=projection_input,
            binding_fingerprint=binding_fingerprint,
        )
    if snapshot["mode"] == "baseline":
        _require(not selection and "craft_catalog" not in projection_input,
                 "disabled craft selection cannot supply methods", "semantic_output_invalid")
        return None
    catalog = projection_input.get("craft_catalog")
    _require(catalog == _catalog(snapshot), "selection catalog differs from the frozen library", "semantic_output_invalid")
    registered = {card["card_id"]: card for card in snapshot["cards"]}
    eligible = (
        set(registered)
        if snapshot["mode"] == STYLE_CONTRACT_MODE
        else {card["card_id"] for card in snapshot["cards"] if card["kind"] == "method"}
    )
    refs = {"task:request", "scene:resolved"}
    planning = projection_input.get("planning_context", [])
    _require(isinstance(planning, list), "planning context must be an array", "semantic_output_invalid")
    for row in planning:
        _require(isinstance(row, dict) and isinstance(row.get("source_ref"), str)
                 and row["source_ref"].startswith("plan:") and row["source_ref"] not in refs
                 and row.get("authority") == "active_plan" and row.get("kind") in ("plan", "story_node"),
                 "unavailable planning source", "semantic_output_invalid")
        refs.add(row["source_ref"])
    chosen = [] if snapshot["mode"] == STYLE_CONTRACT_MODE else [snapshot["base_card_id"]]
    for item in selection:
        _require(isinstance(item, dict) and set(item) == {"card_id", "source_refs", "reason"},
                 "invalid craft selection entry", "semantic_output_invalid")
        card_id = item["card_id"]
        _require(isinstance(card_id, str) and card_id in eligible and card_id not in chosen,
                 "craft selection cites an unknown or repeated method", "semantic_output_invalid")
        cited = item["source_refs"]
        _require(isinstance(cited, list) and bool(cited) and all(isinstance(ref, str) and ref in refs for ref in cited),
                 "craft selection cites unavailable planning evidence", "semantic_output_invalid")
        _require(_text(item["reason"]) and len(item["reason"]) <= 800,
                 "craft selection requires a concise applicability reason", "semantic_output_invalid")
        chosen.append(card_id)
    _require(isinstance(binding_fingerprint, str) and bool(_FP.fullmatch(binding_fingerprint)), "missing selection binding")
    if snapshot["mode"] == STYLE_CONTRACT_MODE and not chosen:
        return None
    if snapshot["mode"] == STYLE_CONTRACT_MODE:
        cards = [
            {key: deepcopy(registered[card_id][key]) for key in _STYLE_WRITER_CARD_KEYS}
            for card_id in chosen
        ]
    else:
        cards = [
            {key: deepcopy(registered[card_id][key])
             for key in ("card_id", "version", "text", "content_fingerprint")}
            for card_id in chosen
        ]
    result = {
        "schema": WRITER_SCHEMA, "language": snapshot["language"], "registry_version": snapshot["registry_version"],
        "snapshot_fingerprint": snapshot["snapshot_fingerprint"], "selection_binding_fingerprint": binding_fingerprint,
        "cards": cards,
        "authority": False,
    }
    result["guidance_fingerprint"] = fingerprint(result)
    return result
