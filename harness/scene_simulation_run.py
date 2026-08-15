#!/usr/bin/env python3
"""Fingerprint-bound Scene Simulation Run envelope for NovelForge.

Binds bounded character-action semantic results, scene resolution, normalized
Event IR candidates and optional scenario branches to one base story-state
fingerprint. The envelope is operational evidence only and never grants Canon.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_scene_simulation_run_v1"
CHAR_CONTRACT = "character.action_propose"
SCENE_CONTRACT = "scene.resolve_actions"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} required")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    value = _text(value, name)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} invalid hex") from exc
    return value


def _semantic_result(raw: Any, expected_contract: str, name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be object")
    if raw.get("contract_id") != expected_contract:
        raise ValueError(f"{name}.contract_id must be {expected_contract}")
    if raw.get("status") != "completed":
        raise ValueError(f"{name} must be completed")
    input_fingerprint = _sha(raw.get("input_fingerprint"), f"{name}.input_fingerprint")
    result = raw.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"{name}.result required")
    provenance = raw.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError(f"{name}.provenance must be object")
    return {
        "contract_id": expected_contract,
        "input_fingerprint": input_fingerprint,
        "result_fingerprint": fingerprint(result),
        "result": result,
        "provenance": provenance,
    }


def build_run(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    base_fingerprint = _sha(payload.get("base_state_fingerprint"), "base_state_fingerprint")

    character_raw = payload.get("character_results", [])
    if not isinstance(character_raw, list) or not character_raw:
        raise ValueError("character_results must be non-empty list")
    characters: list[dict[str, Any]] = []
    seen_characters: set[str] = set()
    for index, row in enumerate(character_raw):
        if not isinstance(row, dict):
            raise ValueError("character result row must be object")
        character_id = _text(row.get("character_id"), f"character_results[{index}].character_id")
        if character_id in seen_characters:
            raise ValueError(f"duplicate character result: {character_id}")
        seen_characters.add(character_id)
        characters.append({
            "character_id": character_id,
            **_semantic_result(row, CHAR_CONTRACT, f"character_results[{index}]"),
        })

    scene_resolution = _semantic_result(payload.get("scene_resolution"), SCENE_CONTRACT, "scene_resolution")

    events_raw = payload.get("event_ir_candidates", [])
    if not isinstance(events_raw, list) or not events_raw:
        raise ValueError("event_ir_candidates must be non-empty list")
    events: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for index, event in enumerate(events_raw):
        if not isinstance(event, dict) or event.get("schema") != "novelforge_event_ir_v1":
            raise ValueError(f"event_ir_candidates[{index}] must be normalized Event IR")
        if event.get("subject_fingerprint") != base_fingerprint:
            raise ValueError("Event IR subject fingerprint must match base state fingerprint")
        event_id = _text(event.get("event_id"), f"event_ir_candidates[{index}].event_id")
        if event_id in event_ids:
            raise ValueError(f"duplicate event id: {event_id}")
        event_ids.add(event_id)
        event_fingerprint = _sha(event.get("event_fingerprint"), f"event_ir_candidates[{index}].event_fingerprint")
        if event.get("authority") is not False or event.get("canon_write") is not False:
            raise ValueError("Event IR must remain non-authoritative")
        story_order = event.get("story_order")
        if isinstance(story_order, bool) or not isinstance(story_order, int) or story_order < 0:
            raise ValueError(f"event_ir_candidates[{index}].story_order invalid")
        events.append({
            "event_id": event_id,
            "event_fingerprint": event_fingerprint,
            "story_order": story_order,
        })

    branches: list[dict[str, Any]] = []
    branches_raw = payload.get("branches", [])
    if not isinstance(branches_raw, list):
        raise ValueError("branches must be list")
    branch_ids: set[str] = set()
    for index, row in enumerate(branches_raw):
        if not isinstance(row, dict):
            raise ValueError("branch must be object")
        if row.get("base_state_fingerprint") != base_fingerprint:
            raise ValueError("branch base state fingerprint mismatch")
        branch_id = _text(row.get("branch_id"), f"branches[{index}].branch_id")
        if branch_id in branch_ids:
            raise ValueError(f"duplicate branch id: {branch_id}")
        branch_ids.add(branch_id)
        branches.append({
            "branch_id": branch_id,
            "branch_fingerprint": _sha(row.get("branch_fingerprint"), f"branches[{index}].branch_fingerprint"),
            "base_state_fingerprint": base_fingerprint,
            "selected": bool(row.get("selected", False)),
            "authority": False,
        })

    comparison = None
    if payload.get("comparison_result") is not None:
        row = payload["comparison_result"]
        if not isinstance(row, dict):
            raise ValueError("comparison_result must be object")
        if row.get("status") != "completed":
            raise ValueError("comparison_result must be completed")
        result = row.get("result")
        if not isinstance(result, dict):
            raise ValueError("comparison_result.result required")
        comparison = {
            "contract_id": _text(row.get("contract_id"), "comparison_result.contract_id"),
            "input_fingerprint": _sha(row.get("input_fingerprint"), "comparison_result.input_fingerprint"),
            "result_fingerprint": fingerprint(result),
            "status": "completed",
        }

    core = {
        "run_id": _text(payload.get("run_id"), "run_id"),
        "scene_id": _text(payload.get("scene_id"), "scene_id"),
        "base_checkpoint_id": _text(payload.get("base_checkpoint_id"), "base_checkpoint_id"),
        "base_state_fingerprint": base_fingerprint,
        "character_results": characters,
        "scene_resolution": scene_resolution,
        "event_ir_candidates": sorted(events, key=lambda event: (event["story_order"], event["event_id"])),
        "branches": branches,
        "comparison_result": comparison,
    }
    return {
        "schema": SCHEMA,
        **core,
        "run_fingerprint": fingerprint(core),
        "agent_topology": "one_manager_bounded_semantic_invocations",
        "persistent_character_agent_memory": False,
        "authority": False,
        "canon_write": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    base = "sha256:" + "a" * 64
    event = {
        "schema": "novelforge_event_ir_v1",
        "event_id": "EVT-1",
        "story_order": 1,
        "subject_fingerprint": base,
        "event_fingerprint": "sha256:" + "b" * 64,
        "authority": False,
        "canon_write": False,
    }
    payload = {
        "run_id": "SIM-1",
        "scene_id": "SCN-1",
        "base_checkpoint_id": "CP-1",
        "base_state_fingerprint": base,
        "character_results": [{
            "character_id": "A",
            "contract_id": CHAR_CONTRACT,
            "status": "completed",
            "input_fingerprint": "sha256:" + "c" * 64,
            "result": {"proposals": [1]},
        }],
        "scene_resolution": {
            "contract_id": SCENE_CONTRACT,
            "status": "completed",
            "input_fingerprint": "sha256:" + "d" * 64,
            "result": {"trajectory": [1]},
        },
        "event_ir_candidates": [event],
        "branches": [{
            "branch_id": "BR-1",
            "branch_fingerprint": "sha256:" + "e" * 64,
            "base_state_fingerprint": base,
            "selected": True,
        }],
    }
    report = build_run(payload)
    noncanon = report["authority"] is False and report["branches"][0]["authority"] is False and report["persistent_character_agent_memory"] is False
    stale = False
    bad = json.loads(json.dumps(payload))
    bad["event_ir_candidates"][0]["subject_fingerprint"] = "sha256:" + "f" * 64
    try:
        build_run(bad)
    except ValueError:
        stale = True
    incomplete = False
    bad2 = json.loads(json.dumps(payload))
    bad2["scene_resolution"]["status"] = "failed"
    try:
        build_run(bad2)
    except ValueError:
        incomplete = True
    ok = noncanon and stale and incomplete and report["run_fingerprint"].startswith("sha256:")
    print(json.dumps({
        "scene_simulation_run_contract": "PASS" if ok else "FAIL",
        "non_authoritative": noncanon,
        "stale_fingerprint_guard": stale,
        "incomplete_semantic_result_guard": incomplete,
        "bounded_topology": report["agent_topology"],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge Scene Simulation Run envelope")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--input", required=True)
    build_parser.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    report = build_run(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
