#!/usr/bin/env python3
"""Fail closed when live semantic contract references drift from the catalog."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
CATALOG = SEM / "model_contract_catalog.json"
LIVE_ENTRY_DOCS = [
    ROOT / "harness" / "HARNESS_AGENT.en.md",
    ROOT / "harness" / "HARNESS_AGENT.zh-CN.md",
    ROOT / "SKILL.en.md",
    ROOT / "SKILL.zh-CN.md",
]
STALE_ACTIVE_REF = "`semantic_workers/model_contracts.json`"
CATALOG_REF = "model_contract_catalog.json"


def check() -> dict:
    errors: list[str] = []
    if not CATALOG.exists():
        errors.append("missing authoritative model_contract_catalog.json")
        return {"semantic_reference_integrity": "FAIL", "errors": errors, "authority": False, "model_execution": False}
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if catalog.get("schema") != "novelforge_model_contract_catalog_v1":
        errors.append("invalid catalog schema")
    seen: set[str] = set()
    for pack in catalog.get("packs", []):
        pack_id = pack.get("id")
        rel = pack.get("path")
        contracts = pack.get("contracts")
        if not isinstance(pack_id, str) or not pack_id or not isinstance(rel, str) or not rel:
            errors.append("catalog pack missing id/path")
            continue
        path = SEM / rel
        if not path.exists():
            errors.append(f"catalog pack path missing: {rel}")
            continue
        registry = json.loads(path.read_text(encoding="utf-8"))
        actual = set(registry.get("contracts", {}).keys())
        declared = set(contracts or [])
        if actual != declared:
            errors.append(f"catalog/pack contract mismatch: {pack_id}")
        overlap = seen.intersection(declared)
        if overlap:
            errors.append(f"duplicate contract ids across packs: {sorted(overlap)}")
        seen.update(declared)
    for doc in LIVE_ENTRY_DOCS:
        if not doc.exists():
            errors.append(f"missing live entry doc: {doc.relative_to(ROOT)}")
            continue
        text = doc.read_text(encoding="utf-8")
        if STALE_ACTIVE_REF in text:
            errors.append(f"stale active semantic registry ref: {doc.relative_to(ROOT)}")
        if CATALOG_REF not in text:
            errors.append(f"live entry doc does not identify catalog: {doc.relative_to(ROOT)}")
    return {
        "semantic_reference_integrity": "PASS" if not errors else "FAIL",
        "catalog": str(CATALOG.relative_to(ROOT)),
        "contract_count": len(seen),
        "errors": errors,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    out = check()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["semantic_reference_integrity"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
