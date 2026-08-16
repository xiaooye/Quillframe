#!/usr/bin/env python3
"""Authority-aware Context Manifest inspector and overlay controls.

The inspector never mutates Project Canon and never decides semantic relevance.
Context selection belongs to the model-facing `context.select` contract; this
module exposes only authority, stage, author/runtime controls, private-state
isolation, and stable views.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_context_inspector_v3"
PROTECTED_AUTHORITIES = {"locked", "accepted"}
AUTHORITIES = PROTECTED_AUTHORITIES | {"active_plan", "review", "proposal", "runtime", "learning", "corpus", "derived"}
STAGES = {
    "character_simulation", "scene_simulation", "realization_projection",
    "writer_pre_draft", "post_draft_critic", "independent_reviewer", "never",
}
SENSITIVE_CLASSES = {"regression", "hidden_gold", "expected_verdict", "answer_key"}
PRIVATE_SIMULATION_CLASSES = {
    "private_character_state", "character_simulation_private", "scene_simulation_private",
    "writer_reasoning", "critic_patch",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def canonical_fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    items = manifest.get("items", [])
    if not isinstance(items, list):
        raise ValueError("manifest.items must be a list")
    out: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("context item must be an object")
        if "relevance" in raw:
            raise ValueError("context manifest must not carry semantic relevance scores; use context.select")
        item_id = raw.get("id") or raw.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("context item id required")
        if item_id in ids:
            raise ValueError(f"duplicate context item id: {item_id}")
        ids.add(item_id)
        authority = raw.get("authority", "derived")
        if authority not in AUTHORITIES:
            raise ValueError(f"invalid authority for {item_id}: {authority}")
        stages = raw.get("stages") or [raw.get("stage", "writer_pre_draft")]
        if not isinstance(stages, list) or not stages or any(stage not in STAGES for stage in stages):
            raise ValueError(f"invalid stages for {item_id}")
        item_class = str(raw.get("class") or raw.get("kind") or "context")
        if item_class in SENSITIVE_CLASSES and "writer_pre_draft" in stages:
            raise ValueError(f"sensitive context leaked into writer_pre_draft: {item_id}")
        if item_class in PRIVATE_SIMULATION_CLASSES and "writer_pre_draft" in stages:
            raise ValueError(f"private simulation state leaked into writer_pre_draft: {item_id}")
        priority = raw.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, (int, float)):
            raise ValueError(f"priority must be numeric for {item_id}")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"metadata must be object for {item_id}")
        out.append({
            "id": item_id,
            "class": item_class,
            "source": raw.get("source") or raw.get("source_ref"),
            "source_fingerprint": raw.get("source_fingerprint"),
            "authority": authority,
            "inclusion_reason": raw.get("inclusion_reason") or raw.get("reason") or "unspecified",
            "stages": stages,
            "priority": float(priority),
            "pinned": bool(raw.get("pinned", False)),
            "derived": bool(raw.get("derived", authority == "derived")),
            "hidden": bool(raw.get("hidden", False)),
            "invalidated": bool(raw.get("invalidated", False)),
            "metadata": metadata,
        })
    return {"schema": SCHEMA, "manifest_id": manifest.get("manifest_id"), "items": out, "authority": False, "model_execution": False}


def normalize_overlay(overlay: dict[str, Any] | None) -> dict[str, Any]:
    overlay = overlay or {}
    controls = overlay.get("controls", {})
    proposals = overlay.get("proposals", [])
    if not isinstance(controls, dict) or not isinstance(proposals, list):
        raise ValueError("invalid overlay")
    return {"schema": SCHEMA, "controls": controls, "proposals": proposals, "authority": False}


def apply_overlay(manifest: dict[str, Any], overlay: dict[str, Any] | None) -> dict[str, Any]:
    norm = normalize_manifest(manifest); ov = normalize_overlay(overlay)
    for item in norm["items"]:
        control = ov["controls"].get(item["id"], {})
        if not isinstance(control, dict):
            continue
        if "pinned" in control:
            item["pinned"] = bool(control["pinned"])
        if "priority" in control:
            value = control["priority"]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"overlay priority must be numeric: {item['id']}")
            item["priority"] = float(value)
        if "hidden" in control:
            if control["hidden"] and not item["derived"]:
                raise ValueError(f"hide is restricted to derived views: {item['id']}")
            item["hidden"] = bool(control["hidden"])
        if "invalidated" in control:
            if control["invalidated"] and not item["derived"]:
                raise ValueError(f"invalidation is restricted to derived views: {item['id']}")
            item["invalidated"] = bool(control["invalidated"])
    norm["proposals"] = ov["proposals"]
    norm["overlay_fingerprint"] = canonical_fingerprint(ov)
    return norm


def update_control(overlay: dict[str, Any] | None, *, item_id: str, action: str, value: Any = None) -> dict[str, Any]:
    ov = normalize_overlay(overlay); controls = ov["controls"]; current = dict(controls.get(item_id, {}))
    if action == "pin":
        current["pinned"] = True
    elif action == "unpin":
        current["pinned"] = False
    elif action == "priority":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("priority value must be numeric")
        current["priority"] = float(value)
    elif action == "hide-derived":
        current["hidden"] = True
    elif action == "invalidate-derived":
        current["invalidated"] = True
    else:
        raise ValueError(f"unsupported control action: {action}")
    controls[item_id] = current; ov["controls"] = controls; return ov


def request_edit(manifest: dict[str, Any], overlay: dict[str, Any] | None, *, item_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    norm = normalize_manifest(manifest); item = next((x for x in norm["items"] if x["id"] == item_id), None)
    if not item:
        raise ValueError(f"unknown context item: {item_id}")
    if not isinstance(patch, dict) or not patch:
        raise ValueError("patch must be a non-empty object")
    ov = normalize_overlay(overlay)
    proposal = {
        "proposal_id": f"CTX-PROP-{canonical_fingerprint({'item_id': item_id, 'patch': patch})[7:19]}",
        "item_id": item_id,
        "authority": item["authority"],
        "requested_patch": patch,
        "status": "proposal_required" if item["authority"] in PROTECTED_AUTHORITIES else "overlay_proposal",
        "direct_mutation_performed": False,
        "canon_write": False,
    }
    ov["proposals"].append(proposal); return {"overlay": ov, "proposal": proposal}


def inspect(manifest: dict[str, Any], overlay: dict[str, Any] | None = None, *, stage: str | None = None) -> dict[str, Any]:
    if stage is not None and stage not in STAGES:
        raise ValueError(f"invalid stage: {stage}")
    view = apply_overlay(manifest, overlay); items = []
    for item in view["items"]:
        eligible = not item["hidden"] and not item["invalidated"] and (stage is None or stage in item["stages"])
        items.append({**item, "eligible": eligible})
    items.sort(key=lambda x: (not x["pinned"], -x["priority"], x["id"]))
    return {
        "schema": SCHEMA,
        "manifest_id": view.get("manifest_id"),
        "stage": stage,
        "items": items,
        "proposals": view.get("proposals", []),
        "ordering_policy": "pin_then_explicit_priority_then_stable_id",
        "semantic_relevance_field_allowed": False,
        "private_simulation_classes_writer_visible": False,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    manifest = {"manifest_id": "CTX-1", "items": [
        {"id": "CANON-1", "class": "canon", "authority": "accepted", "stages": ["writer_pre_draft", "independent_reviewer"]},
        {"id": "DER-A", "class": "summary", "authority": "derived", "derived": True, "stages": ["writer_pre_draft"], "priority": 0},
        {"id": "DER-B", "class": "summary", "authority": "derived", "derived": True, "stages": ["writer_pre_draft"], "priority": 5},
        {"id": "REG-1", "class": "regression", "authority": "learning", "stages": ["post_draft_critic"]},
        {"id": "PRIVATE-1", "class": "private_character_state", "authority": "derived", "stages": ["character_simulation"]},
        {"id": "PROJ-1", "class": "realization_projection", "authority": "derived", "stages": ["realization_projection", "writer_pre_draft"], "metadata": {"purposes": ["scene_realization"]}},
    ]}
    overlay = update_control(None, item_id="DER-A", action="pin")
    edit = request_edit(manifest, overlay, item_id="CANON-1", patch={"text": "mutated"})
    protected = edit["proposal"]["status"] == "proposal_required" and edit["proposal"]["direct_mutation_performed"] is False
    stage_view = inspect(manifest, edit["overlay"], stage="writer_pre_draft")
    regression_hidden = next(x for x in stage_view["items"] if x["id"] == "REG-1")["eligible"] is False
    private_hidden = next(x for x in stage_view["items"] if x["id"] == "PRIVATE-1")["eligible"] is False
    projection_visible = next(x for x in stage_view["items"] if x["id"] == "PROJ-1")["eligible"] is True
    sim_view = inspect(manifest, edit["overlay"], stage="character_simulation")
    private_sim_visible = next(x for x in sim_view["items"] if x["id"] == "PRIVATE-1")["eligible"] is True
    ids = [x["id"] for x in stage_view["items"]]
    explicit_controls_only = ids.index("DER-A") < ids.index("DER-B") < ids.index("CANON-1")
    relevance_rejected = False
    try:
        normalize_manifest({"items": [{"id":"BAD-R","authority":"derived","relevance":0.5}]})
    except ValueError:
        relevance_rejected = True
    bad_leak_rejected = False
    try:
        normalize_manifest({"items": [{"id": "BAD", "class": "hidden_gold", "authority": "learning", "stages": ["writer_pre_draft"]}]})
    except ValueError:
        bad_leak_rejected = True
    private_leak_rejected = False
    try:
        normalize_manifest({"items": [{"id": "BAD-P", "class": "private_character_state", "authority": "derived", "stages": ["writer_pre_draft"]}]})
    except ValueError:
        private_leak_rejected = True
    ok = all([
        protected, regression_hidden, bad_leak_rejected, private_leak_rejected,
        private_hidden, projection_visible, private_sim_visible, explicit_controls_only,
        relevance_rejected, stage_view["authority"] is False,
    ])
    dump({
        "context_inspector_contract": "PASS" if ok else "FAIL",
        "protected_edit_downgraded_to_proposal": protected,
        "pre_draft_regression_isolation": regression_hidden,
        "hidden_gold_leak_rejected": bad_leak_rejected,
        "private_simulation_writer_leak_rejected": private_leak_rejected,
        "private_state_simulation_stage_supported": private_sim_visible,
        "writer_safe_realization_projection_supported": projection_visible,
        "semantic_relevance_field_allowed": False,
        "semantic_relevance_rejected": relevance_rejected,
        "explicit_control_ordering": explicit_controls_only,
        "authority": False,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Context Manifest inspector"); sub = p.add_subparsers(dest="command", required=True)
    ins = sub.add_parser("inspect"); ins.add_argument("--manifest", required=True); ins.add_argument("--overlay"); ins.add_argument("--stage", choices=sorted(STAGES)); ins.add_argument("--output")
    ctl = sub.add_parser("control"); ctl.add_argument("--overlay"); ctl.add_argument("--item-id", required=True); ctl.add_argument("--action", required=True, choices=["pin", "unpin", "priority", "hide-derived", "invalidate-derived"]); ctl.add_argument("--value", type=float); ctl.add_argument("--output", required=True)
    ed = sub.add_parser("request-edit"); ed.add_argument("--manifest", required=True); ed.add_argument("--overlay"); ed.add_argument("--item-id", required=True); ed.add_argument("--patch-json", required=True); ed.add_argument("--output", required=True)
    sub.add_parser("self-test"); args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "inspect":
        manifest = load_json(Path(args.manifest)); overlay = load_json(Path(args.overlay)) if args.overlay else None
        dump(inspect(manifest, overlay, stage=args.stage), Path(args.output) if args.output else None); return 0
    if args.command == "control":
        overlay = load_json(Path(args.overlay)) if args.overlay else None
        dump(update_control(overlay, item_id=args.item_id, action=args.action, value=args.value), Path(args.output)); return 0
    manifest = load_json(Path(args.manifest)); overlay = load_json(Path(args.overlay)) if args.overlay else None
    dump(request_edit(manifest, overlay, item_id=args.item_id, patch=load_json(Path(args.patch_json))), Path(args.output)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
