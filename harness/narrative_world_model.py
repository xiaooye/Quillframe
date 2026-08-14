#!/usr/bin/env python3
"""Narratology-grounded derived memory for long-form fiction.

NovelForge's Narrative World Model (NWM) indexes project-provided, source-bound
records without extracting or inventing story facts. It separates occurrence
order from reveal order, models character knowledge, setup/payoff state and
relationship history, and enforces chapter-safe retrieval. The index is a
derived verification/retrieval view and never becomes Project Canon.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_narrative_world_v1"
INDEX_SCHEMA = "novelforge_narrative_world_index_v1"
KINDS = {"event", "knowledge", "setup", "relationship"}
AUTHORITIES = {"locked", "accepted", "active_plan", "review", "proposal"}
DEFAULT_AUTHORITIES = {"locked", "accepted"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _order(value: Any, field: str, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _refs(value: Any, record_id: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(f"{record_id}.source_refs must be a non-empty string list")
    return list(dict.fromkeys(value))


def normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("record must be object")
    record_id = raw.get("id")
    kind = raw.get("kind")
    authority = raw.get("authority")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record.id required")
    if kind not in KINDS:
        raise ValueError(f"{record_id}.kind must be one of {sorted(KINDS)}")
    if authority not in AUTHORITIES:
        raise ValueError(f"{record_id}.authority invalid")
    source_refs = _refs(raw.get("source_refs"), record_id)
    entities = raw.get("entities", [])
    if not isinstance(entities, list) or not all(isinstance(x, str) and x.strip() for x in entities):
        raise ValueError(f"{record_id}.entities must be string list")
    out: dict[str, Any] = {
        "id": record_id,
        "kind": kind,
        "authority": authority,
        "source_refs": source_refs,
        "entities": list(dict.fromkeys(entities)),
        "attributes": raw.get("attributes", {}) if isinstance(raw.get("attributes", {}), dict) else {},
    }
    if kind == "event":
        out["occurrence_order"] = _order(raw.get("occurrence_order"), f"{record_id}.occurrence_order")
        out["reveal_order"] = _order(raw.get("reveal_order"), f"{record_id}.reveal_order")
        actors = raw.get("actors", [])
        if not isinstance(actors, list) or not all(isinstance(x, str) and x.strip() for x in actors):
            raise ValueError(f"{record_id}.actors must be string list")
        out["actors"] = list(dict.fromkeys(actors))
    elif kind == "knowledge":
        for key in ("character_id", "fact_id"):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValueError(f"{record_id}.{key} required")
            out[key] = raw[key]
        out["learned_order"] = _order(raw.get("learned_order"), f"{record_id}.learned_order")
        out["reveal_order"] = _order(raw.get("reveal_order"), f"{record_id}.reveal_order")
    elif kind == "setup":
        out["introduced_order"] = _order(raw.get("introduced_order"), f"{record_id}.introduced_order")
        out["resolved_order"] = _order(raw.get("resolved_order"), f"{record_id}.resolved_order", optional=True)
        if out["resolved_order"] is not None and out["resolved_order"] < out["introduced_order"]:
            raise ValueError(f"{record_id}.resolved_order precedes introduction")
        out["payoff_ref"] = raw.get("payoff_ref") if isinstance(raw.get("payoff_ref"), str) else None
        out["reveal_order"] = _order(raw.get("reveal_order", out["introduced_order"]), f"{record_id}.reveal_order")
    else:
        relationship_id = raw.get("relationship_id")
        if not isinstance(relationship_id, str) or not relationship_id.strip():
            raise ValueError(f"{record_id}.relationship_id required")
        state = raw.get("state")
        if not isinstance(state, dict):
            raise ValueError(f"{record_id}.state must be object")
        out["relationship_id"] = relationship_id
        out["state_order"] = _order(raw.get("state_order"), f"{record_id}.state_order")
        out["reveal_order"] = _order(raw.get("reveal_order", out["state_order"]), f"{record_id}.reveal_order")
        out["state"] = state
    return out


def build_index(world: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(world, dict):
        raise ValueError("world must be object")
    world_id = world.get("world_id")
    records_raw = world.get("records")
    if not isinstance(world_id, str) or not world_id.strip():
        raise ValueError("world_id required")
    if not isinstance(records_raw, list):
        raise ValueError("records must be list")
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    entity_index: dict[str, list[str]] = {}
    kind_index: dict[str, list[str]] = {kind: [] for kind in sorted(KINDS)}
    for raw in records_raw:
        record = normalize_record(raw)
        if record["id"] in ids:
            raise ValueError(f"duplicate record id: {record['id']}")
        ids.add(record["id"])
        records.append(record)
        kind_index[record["kind"]].append(record["id"])
        tokens = [*record.get("entities", [])]
        for key in ("character_id", "fact_id", "relationship_id"):
            if isinstance(record.get(key), str):
                tokens.append(record[key])
        for token in set(tokens):
            entity_index.setdefault(token, []).append(record["id"])
    records.sort(key=lambda r: (int(r.get("reveal_order", r.get("state_order", 0))), r["id"]))
    return {
        "schema": INDEX_SCHEMA,
        "world_id": world_id,
        "records": records,
        "entity_index": {k: sorted(v) for k, v in sorted(entity_index.items())},
        "kind_index": kind_index,
        "derived": True,
        "authority": False,
        "model_execution": False,
    }


def _visible(record: dict[str, Any], safe_through: int, allowed: set[str]) -> bool:
    reveal = int(record.get("reveal_order", record.get("state_order", 0)))
    return record["authority"] in allowed and reveal <= safe_through


def retrieve(index: dict[str, Any], *, safe_through: int, entities: list[str] | None = None,
             kinds: list[str] | None = None, allowed_authorities: set[str] | None = None) -> dict[str, Any]:
    safe_through = int(_order(safe_through, "safe_through"))
    allowed = allowed_authorities or DEFAULT_AUTHORITIES
    unknown = set(allowed) - AUTHORITIES
    if unknown:
        raise ValueError("unknown authorities: " + ", ".join(sorted(unknown)))
    wanted_entities = set(entities or [])
    wanted_kinds = set(kinds or [])
    if wanted_kinds - KINDS:
        raise ValueError("unknown kinds: " + ", ".join(sorted(wanted_kinds - KINDS)))
    hits = []
    for record in index.get("records", []):
        if not _visible(record, safe_through, allowed):
            continue
        if wanted_kinds and record["kind"] not in wanted_kinds:
            continue
        record_tokens = set(record.get("entities", []))
        for key in ("character_id", "fact_id", "relationship_id"):
            if isinstance(record.get(key), str):
                record_tokens.add(record[key])
        if wanted_entities and not wanted_entities.intersection(record_tokens):
            continue
        hits.append(record)
    return {
        "schema": "novelforge_narrative_retrieval_v1",
        "world_id": index.get("world_id"),
        "safe_through": safe_through,
        "allowed_authorities": sorted(allowed),
        "records": hits,
        "derived": True,
        "authority": False,
        "model_execution": False,
    }


def knowledge_at(index: dict[str, Any], character_id: str, fact_id: str, *, at_order: int,
                 safe_through: int | None = None) -> dict[str, Any]:
    at_order = int(_order(at_order, "at_order"))
    safe = at_order if safe_through is None else int(_order(safe_through, "safe_through"))
    matches = [r for r in index.get("records", []) if r["kind"] == "knowledge" and r.get("character_id") == character_id and r.get("fact_id") == fact_id and _visible(r, safe, DEFAULT_AUTHORITIES)]
    learned = [r for r in matches if int(r["learned_order"]) <= at_order]
    learned.sort(key=lambda r: (r["learned_order"], r["id"]))
    return {
        "schema": "novelforge_narrative_knowledge_query_v1",
        "character_id": character_id,
        "fact_id": fact_id,
        "at_order": at_order,
        "knows": bool(learned),
        "evidence": learned,
        "authority": False,
    }


def setup_status(index: dict[str, Any], setup_id: str, *, at_order: int) -> dict[str, Any]:
    at_order = int(_order(at_order, "at_order"))
    record = next((r for r in index.get("records", []) if r["kind"] == "setup" and r["id"] == setup_id and _visible(r, at_order, DEFAULT_AUTHORITIES)), None)
    if record is None:
        return {"schema": "novelforge_setup_status_v1", "setup_id": setup_id, "at_order": at_order, "status": "not_visible", "authority": False}
    resolved = record.get("resolved_order")
    status = "paid" if resolved is not None and int(resolved) <= at_order else "open"
    return {"schema": "novelforge_setup_status_v1", "setup_id": setup_id, "at_order": at_order, "status": status, "record": record, "authority": False}


def relationship_history(index: dict[str, Any], relationship_id: str, *, safe_through: int) -> dict[str, Any]:
    safe_through = int(_order(safe_through, "safe_through"))
    states = [r for r in index.get("records", []) if r["kind"] == "relationship" and r.get("relationship_id") == relationship_id and _visible(r, safe_through, DEFAULT_AUTHORITIES)]
    states.sort(key=lambda r: (r["state_order"], r["id"]))
    return {"schema": "novelforge_relationship_history_v1", "relationship_id": relationship_id, "safe_through": safe_through, "states": states, "authority": False}


def self_test() -> int:
    world = {
        "world_id": "WORLD-TEST",
        "records": [
            {"id": "EV-SECRET", "kind": "event", "authority": "accepted", "occurrence_order": 2, "reveal_order": 5, "actors": ["CHAR-A"], "entities": ["SECRET-X"], "source_refs": ["canon:CH5"]},
            {"id": "KN-A-X", "kind": "knowledge", "authority": "accepted", "character_id": "CHAR-A", "fact_id": "SECRET-X", "learned_order": 3, "reveal_order": 3, "entities": ["SECRET-X"], "source_refs": ["canon:CH3"]},
            {"id": "SET-GUN", "kind": "setup", "authority": "accepted", "introduced_order": 1, "resolved_order": 6, "reveal_order": 1, "entities": ["GUN"], "payoff_ref": "canon:CH6", "source_refs": ["canon:CH1", "canon:CH6"]},
            {"id": "REL-AB-2", "kind": "relationship", "authority": "accepted", "relationship_id": "REL-AB", "state_order": 2, "reveal_order": 2, "state": {"trust": 1}, "entities": ["CHAR-A", "CHAR-B"], "source_refs": ["canon:CH2"]},
            {"id": "REL-AB-4", "kind": "relationship", "authority": "accepted", "relationship_id": "REL-AB", "state_order": 4, "reveal_order": 4, "state": {"trust": 2}, "entities": ["CHAR-A", "CHAR-B"], "source_refs": ["canon:CH4"]},
            {"id": "PLAN-FUTURE", "kind": "event", "authority": "active_plan", "occurrence_order": 7, "reveal_order": 7, "actors": ["CHAR-A"], "entities": ["FUTURE"], "source_refs": ["plan:CH7"]},
        ],
    }
    index = build_index(world)
    safe4 = retrieve(index, safe_through=4)
    safe7 = retrieve(index, safe_through=7)
    hidden_reveal = all(r["id"] != "EV-SECRET" for r in safe4["records"])
    plan_excluded = all(r["id"] != "PLAN-FUTURE" for r in safe7["records"])
    knows = knowledge_at(index, "CHAR-A", "SECRET-X", at_order=4)["knows"]
    setup_open = setup_status(index, "SET-GUN", at_order=4)["status"] == "open"
    setup_paid = setup_status(index, "SET-GUN", at_order=6)["status"] == "paid"
    rel = relationship_history(index, "REL-AB", safe_through=4)
    relationship_ordered = [x["state"]["trust"] for x in rel["states"]] == [1, 2]
    ok = hidden_reveal and plan_excluded and knows and setup_open and setup_paid and relationship_ordered and index["authority"] is False
    dump({
        "narrative_world_model_contract": "PASS" if ok else "FAIL",
        "occurrence_reveal_separation": hidden_reveal,
        "chapter_safe_retrieval": hidden_reveal and plan_excluded,
        "knowledge_timeline": knows,
        "setup_payoff_tracking": setup_open and setup_paid,
        "relationship_history": relationship_ordered,
        "derived_authority": False,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Narrative World Model")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build"); b.add_argument("--world", required=True); b.add_argument("--output")
    r = sub.add_parser("retrieve"); r.add_argument("--index", required=True); r.add_argument("--safe-through", type=int, required=True); r.add_argument("--entity", action="append", dest="entities"); r.add_argument("--kind", action="append", dest="kinds"); r.add_argument("--include-authority", action="append", dest="authorities"); r.add_argument("--output")
    k = sub.add_parser("knowledge"); k.add_argument("--index", required=True); k.add_argument("--character-id", required=True); k.add_argument("--fact-id", required=True); k.add_argument("--at-order", type=int, required=True); k.add_argument("--safe-through", type=int); k.add_argument("--output")
    s = sub.add_parser("setup-status"); s.add_argument("--index", required=True); s.add_argument("--setup-id", required=True); s.add_argument("--at-order", type=int, required=True); s.add_argument("--output")
    h = sub.add_parser("relationship-history"); h.add_argument("--index", required=True); h.add_argument("--relationship-id", required=True); h.add_argument("--safe-through", type=int, required=True); h.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test": return self_test()
    if args.command == "build": value = build_index(load_json(Path(args.world)))
    elif args.command == "retrieve": value = retrieve(load_json(Path(args.index)), safe_through=args.safe_through, entities=args.entities, kinds=args.kinds, allowed_authorities=set(args.authorities) if args.authorities else None)
    elif args.command == "knowledge": value = knowledge_at(load_json(Path(args.index)), args.character_id, args.fact_id, at_order=args.at_order, safe_through=args.safe_through)
    elif args.command == "setup-status": value = setup_status(load_json(Path(args.index)), args.setup_id, at_order=args.at_order)
    else: value = relationship_history(load_json(Path(args.index)), args.relationship_id, safe_through=args.safe_through)
    dump(value, Path(args.output) if getattr(args, "output", None) else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
