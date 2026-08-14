#!/usr/bin/env python3
"""Bounded Character Integrity audit packaging for NovelForge 7.2.

The module packages only the scene excerpt and typed character state required for
an integrity judgment. It rejects hidden/private reasoning and converts completed
semantic results into normalized evidence-chained findings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_DIR = ROOT / "harness" / "semantic_workers"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SEMANTIC_DIR) not in sys.path:
    sys.path.insert(0, str(SEMANTIC_DIR))
from semantic_worker_router import fingerprint_for, validate_result  # type: ignore  # noqa:E402
from quality.findings import make_finding, validate_finding  # noqa:E402

SCHEMA = "novelforge_character_integrity_v1"
MAX_SCENE_CHARS = 16000
FORBIDDEN_KEYS = {
    "private_reasoning", "chain_of_thought", "hidden_gold", "expected",
    "expected_verdict", "gold", "gold_label", "prior_result",
    "regression_bad_examples", "writer_scratchpad",
}
ALLOWED_SNAPSHOT_KEYS = {
    "character_id", "name", "agenda", "knowledge", "voice",
    "relationship_position", "spatial_state", "task_state", "source_refs",
}
CATEGORIES = {
    "agenda_alignment", "knowledge_boundary", "voice_drift",
    "relationship_position", "spatial_task_state", "surprise_consistency",
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


def find_forbidden(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(find_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            hits.extend(find_forbidden(child, f"{path}[{idx}]"))
    return hits


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    leakage = find_forbidden(snapshot)
    if leakage:
        raise ValueError("forbidden character context: " + ", ".join(leakage))
    character_id = snapshot.get("character_id")
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("character_id required")
    normalized = {key: snapshot.get(key) for key in ALLOWED_SNAPSHOT_KEYS if key in snapshot}
    normalized["character_id"] = character_id
    refs = normalized.get("source_refs", [])
    if refs is None:
        refs = []
    if not isinstance(refs, list) or not all(isinstance(x, str) and x.strip() for x in refs):
        raise ValueError("source_refs must be a list of non-empty strings")
    normalized["source_refs"] = refs
    return normalized


def build_job(*, subject_id: str, scene_id: str, scene_excerpt: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scene_excerpt, str) or not scene_excerpt.strip():
        raise ValueError("scene_excerpt required")
    if len(scene_excerpt) > MAX_SCENE_CHARS:
        raise ValueError(f"scene excerpt exceeds bounded limit: {MAX_SCENE_CHARS}")
    character = normalize_snapshot(snapshot)
    job = {
        "job_id": f"SEM-CHAR-{scene_id}-{character['character_id']}",
        "kind": "artifact_audit",
        "subject_id": subject_id,
        "created_at": "deterministic-package",
        "input_fingerprint": "",
        "input": {
            "audit_type": "character_integrity",
            "scene_id": scene_id,
            "scene_excerpt": scene_excerpt,
            "character": character,
            "dimensions": [
                "agenda_alignment", "knowledge_boundary", "voice_drift",
                "relationship_position", "spatial_task_state", "surprise_consistency",
            ],
        },
        "rubric": [
            "Use only the supplied scene excerpt and typed character state.",
            "Do not assume manager knowledge is character knowledge.",
            "Flag only evidence-supported integrity problems; intentional change may be valid when the scene provides transition evidence.",
            "For every finding, identify the candidate-side evidence and the established-state evidence when applicable.",
        ],
        "output_contract": {
            "type": "object",
            "required": ["confidence", "findings"],
            "properties": {
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "findings": {"type": "array"},
            },
        },
        "permissions": {
            "canon_write": False,
            "os_behavior_write": False,
            "durable_user_taste_write": False,
            "allowed_result_scope": "character_integrity_observation",
        },
        "provenance": {"source": SCHEMA, "bounded": True, "independent_gate": False},
        "execution": {"source_session_id": None, "worker_session_id": None, "handoff_id": None, "attempt_id": None},
    }
    job["input_fingerprint"] = fingerprint_for(job)
    return job


def _evidence(value: Any, fallback_ref: str, fallback_summary: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("source_ref"), str) and isinstance(item.get("summary"), str):
                out.append({"source_ref": item["source_ref"], "summary": item["summary"], **({"fingerprint": item["fingerprint"]} if isinstance(item.get("fingerprint"), str) else {})})
            elif isinstance(item, str) and item.strip():
                out.append({"source_ref": fallback_ref, "summary": item.strip()})
        if out:
            return out
    if isinstance(value, str) and value.strip():
        return [{"source_ref": fallback_ref, "summary": value.strip()}]
    return [{"source_ref": fallback_ref, "summary": fallback_summary}]


def normalize_result(job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    errors = validate_result(job, result)
    if errors:
        raise ValueError("invalid semantic result: " + "; ".join(errors))
    if result.get("status") != "completed":
        return {"schema": SCHEMA, "status": result.get("status"), "findings": [], "authority": False}
    judgment = result.get("judgment", {})
    raw_findings = judgment.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ValueError("judgment.findings must be list")
    character = job["input"]["character"]
    scene_id = job["input"]["scene_id"]
    normalized = []
    for idx, raw in enumerate(raw_findings, start=1):
        if not isinstance(raw, dict):
            raise ValueError("finding must be object")
        category = raw.get("category")
        if category not in CATEGORIES:
            raise ValueError(f"unsupported character finding category: {category}")
        severity = raw.get("severity", "warning")
        repair_owner = raw.get("repair_owner", "character")
        confidence = raw.get("confidence", judgment.get("confidence", 0.5))
        candidate_ref = f"scene:{scene_id}"
        authority_ref = character.get("source_refs", [f"character:{character['character_id']}"])
        authority_ref = authority_ref[0] if authority_ref else f"character:{character['character_id']}"
        finding = make_finding(
            finding_id=f"CHAR-{character['character_id']}-{idx}",
            category=category,
            severity=severity,
            repair_owner=repair_owner,
            subject_id=character["character_id"],
            description=str(raw.get("description") or category),
            candidate_evidence=_evidence(raw.get("candidate_evidence"), candidate_ref, "Observed in supplied scene excerpt."),
            authority_evidence=_evidence(raw.get("authority_evidence"), authority_ref, "Compared against supplied typed character state."),
            source_refs=[candidate_ref, authority_ref],
            confidence=float(confidence),
            proposal={"suggestion": raw.get("suggestion"), "direct_mutation": False},
        )
        validation = validate_finding(finding)
        if validation:
            raise ValueError("normalized finding invalid: " + "; ".join(validation))
        normalized.append(finding)
    return {
        "schema": SCHEMA,
        "status": "completed",
        "character_id": character["character_id"],
        "scene_id": scene_id,
        "findings": normalized,
        "authority": False,
        "independent_gate_satisfied": False,
    }


def _fixture_result(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "self-test", "model_or_reviewer": "fixture"},
        "judgment": {
            "confidence": 0.9,
            "findings": [{
                "category": "knowledge_boundary", "severity": "error", "repair_owner": "character",
                "description": "Character acts on information outside the supplied knowledge state.",
                "candidate_evidence": ["The scene has the character name the secret."],
                "authority_evidence": ["The supplied knowledge list does not contain the secret."],
                "confidence": 0.9,
            }],
        },
        "proposals": [], "errors": [],
        "execution": {"source_session_id": None, "worker_session_id": "SELF", "handoff_id": None, "attempt_id": "1"},
    }


def self_test() -> int:
    snapshot = {
        "character_id": "CHAR-1", "name": "A", "agenda": ["win access"],
        "knowledge": ["door is locked"], "voice": {"register": "terse"},
        "relationship_position": {"CHAR-2": "distrust"}, "spatial_state": "hall",
        "task_state": "waiting", "source_refs": ["char:CHAR-1"],
    }
    job = build_job(subject_id="SCN-1/CHAR-1", scene_id="SCN-1", scene_excerpt="A names the secret.", snapshot=snapshot)
    bounded = len(job["input"]["scene_excerpt"]) <= MAX_SCENE_CHARS
    no_forbidden = not find_forbidden(job["input"])
    report = normalize_result(job, _fixture_result(job))
    normalized = len(report["findings"]) == 1 and not validate_finding(report["findings"][0])
    forbidden_rejected = False
    try:
        build_job(subject_id="x", scene_id="x", scene_excerpt="x", snapshot={**snapshot, "private_reasoning": "secret scratchpad"})
    except ValueError:
        forbidden_rejected = True
    ok = bounded and no_forbidden and normalized and forbidden_rejected and report["authority"] is False
    dump({
        "character_integrity_contract": "PASS" if ok else "FAIL",
        "bounded_packet": bounded,
        "forbidden_context_excluded": no_forbidden and forbidden_rejected,
        "evidence_chained_findings": normalized,
        "authority": False,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge character integrity audit packaging")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build"); b.add_argument("--subject-id", required=True); b.add_argument("--scene-id", required=True); b.add_argument("--scene-file", required=True); b.add_argument("--snapshot", required=True); b.add_argument("--output")
    n = sub.add_parser("normalize-result"); n.add_argument("--job", required=True); n.add_argument("--result", required=True); n.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "build":
        job = build_job(subject_id=args.subject_id, scene_id=args.scene_id, scene_excerpt=Path(args.scene_file).read_text(encoding="utf-8"), snapshot=load_json(Path(args.snapshot)))
        dump(job, Path(args.output) if args.output else None); return 0
    report = normalize_result(load_json(Path(args.job)), load_json(Path(args.result)))
    dump(report, Path(args.output) if args.output else None); return 0


if __name__ == "__main__":
    raise SystemExit(main())
