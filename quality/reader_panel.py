#!/usr/bin/env python3
"""Reader-simulation packaging and aggregation for NovelForge 7.2.

This module never calls a model. It creates bounded semantic jobs and aggregates
validated results. A reader panel is diagnostic editorial evidence and never
satisfies a mandatory independent semantic gate by itself.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_DIR = ROOT / "harness" / "semantic_workers"
if str(SEMANTIC_DIR) not in sys.path:
    sys.path.insert(0, str(SEMANTIC_DIR))
from semantic_worker_router import fingerprint_for, validate_result  # type: ignore  # noqa:E402

SCHEMA = "novelforge_reader_panel_v1"
DEFAULT_PERSONAS: dict[str, dict[str, str]] = {
    "binge_reader": {
        "name": "Binge Reader",
        "focus": "Immediate forward pull, momentum, and whether the next chapter feels irresistible.",
    },
    "genre_native_reader": {
        "name": "Genre-Native Reader",
        "focus": "Genre promises, freshness of execution, payoff timing, and familiar-pattern fatigue.",
    },
    "casual_mobile_reader": {
        "name": "Casual Mobile Reader",
        "focus": "Where attention slips, what gets skimmed, confusion, and friction on a small-screen reading session.",
    },
    "investment_reader": {
        "name": "Investment Reader",
        "focus": "Which characters and relationships feel worth caring about, and whether emotional investment changes.",
    },
    "reward_sensitive_reader": {
        "name": "Reward-Sensitive Reader",
        "focus": "Whether the text returns enough reveal, competence, reversal, intimacy, humor, or consequence for the attention spent.",
    },
}
FORBIDDEN_PACKET_KEYS = {"expected", "expected_verdict", "gold", "gold_label", "prior_result", "hidden_gold"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _permissions() -> dict[str, Any]:
    return {
        "canon_write": False,
        "os_behavior_write": False,
        "durable_user_taste_write": False,
        "allowed_result_scope": "reader_diagnostic",
    }


def _result_contract(mode: str) -> dict[str, Any]:
    common = {
        "type": "object",
        "required": ["confidence"],
        "properties": {"confidence": {"type": "number", "minimum": 0, "maximum": 1}},
    }
    if mode == "single":
        common["properties"].update({
            "tension": {"type": "number", "minimum": 0, "maximum": 1},
            "pacing": {"type": "number", "minimum": 0, "maximum": 1},
            "would_continue": {"type": "boolean"},
            "continue_desire": {"type": "number", "minimum": 0, "maximum": 1},
            "confusion": {"type": "array", "items": {"type": "string"}},
            "favorite_beat": {"type": ["string", "null"]},
            "stumble_beat": {"type": ["string", "null"]},
            "emotion": {"type": "array", "items": {"type": "string"}},
            "drop_off_point": {"type": ["string", "null"]},
            "reason": {"type": "string"},
        })
        common["required"] += ["would_continue", "continue_desire", "reason"]
    else:
        common["properties"].update({
            "winner": {"enum": ["A", "B", "tie"]},
            "reason": {"type": "string"},
            "stronger_forward_pull": {"enum": ["A", "B", "tie"]},
            "stronger_character_investment": {"enum": ["A", "B", "tie"]},
            "more_rewarding": {"enum": ["A", "B", "tie"]},
        })
        common["required"] += ["winner", "reason"]
    return common


def _persona_subset(keys: list[str] | None) -> list[tuple[str, dict[str, str]]]:
    if not keys:
        return list(DEFAULT_PERSONAS.items())
    out: list[tuple[str, dict[str, str]]] = []
    for key in keys:
        if key not in DEFAULT_PERSONAS:
            raise ValueError(f"unknown persona: {key}")
        out.append((key, DEFAULT_PERSONAS[key]))
    return out


def _new_job(*, job_id: str, subject_id: str, input_payload: dict[str, Any], output_contract: dict[str, Any]) -> dict[str, Any]:
    job = {
        "job_id": job_id,
        "kind": "external_review",
        "subject_id": subject_id,
        "created_at": "deterministic-package",
        "input_fingerprint": "",
        "input": input_payload,
        "rubric": [
            "Read only the supplied candidate/context and the assigned reader persona.",
            "Judge the reading experience, not whether the prose resembles a preferred author.",
            "Be specific about observable reader effects and avoid inventing unstated Canon.",
            "Return only the declared typed judgment.",
        ],
        "output_contract": output_contract,
        "permissions": _permissions(),
        "provenance": {"source": "novelforge_reader_panel_v1", "independent_gate": False},
        "execution": {"source_session_id": None, "worker_session_id": None, "handoff_id": None, "attempt_id": None},
    }
    job["input_fingerprint"] = fingerprint_for(job)
    return job


def build_single(candidate_id: str, text: str, persona_keys: list[str] | None = None) -> dict[str, Any]:
    if not candidate_id.strip() or not text.strip():
        raise ValueError("candidate_id and text are required")
    jobs = []
    for key, persona in _persona_subset(persona_keys):
        jobs.append(_new_job(
            job_id=f"SEM-READER-{candidate_id}-{key}",
            subject_id=f"reader:{candidate_id}:{key}",
            input_payload={
                "mode": "single",
                "candidate_id": candidate_id,
                "candidate_text": text,
                "persona_id": key,
                "persona_name": persona["name"],
                "persona_focus": persona["focus"],
                "questions": [
                    "Where does momentum rise or fall?",
                    "Would you continue immediately?",
                    "What confused you or made you skim?",
                    "What beat gave you the strongest reward?",
                    "What emotional state do you leave with?",
                ],
            },
            output_contract=_result_contract("single"),
        ))
    return {
        "schema": SCHEMA,
        "mode": "single",
        "candidate_ids": [candidate_id],
        "jobs": jobs,
        "diagnostic_only": True,
        "independent_gate_satisfied": False,
        "model_execution": False,
    }


def build_pairwise(candidate_a_id: str, text_a: str, candidate_b_id: str, text_b: str, persona_keys: list[str] | None = None) -> dict[str, Any]:
    if candidate_a_id == candidate_b_id:
        raise ValueError("pairwise candidates must have different ids")
    if not all(x.strip() for x in (candidate_a_id, candidate_b_id, text_a, text_b)):
        raise ValueError("candidate ids and texts are required")
    jobs: list[dict[str, Any]] = []
    for key, persona in _persona_subset(persona_keys):
        orders = [
            ("ab", candidate_a_id, text_a, candidate_b_id, text_b),
            ("ba", candidate_b_id, text_b, candidate_a_id, text_a),
        ]
        for order_key, first_id, first_text, second_id, second_text in orders:
            jobs.append(_new_job(
                job_id=f"SEM-READER-PAIR-{candidate_a_id}-{candidate_b_id}-{key}-{order_key}",
                subject_id=f"reader-pair:{candidate_a_id}:{candidate_b_id}:{key}:{order_key}",
                input_payload={
                    "mode": "pairwise",
                    "persona_id": key,
                    "persona_name": persona["name"],
                    "persona_focus": persona["focus"],
                    "order_key": order_key,
                    "visible_order": {"A": first_id, "B": second_id},
                    "candidate_A": first_text,
                    "candidate_B": second_text,
                    "comparison_dimensions": [
                        "forward_pull", "reader_reward", "character_investment", "clarity", "pacing",
                    ],
                },
                output_contract=_result_contract("pairwise"),
            ))
    return {
        "schema": SCHEMA,
        "mode": "pairwise",
        "candidate_ids": [candidate_a_id, candidate_b_id],
        "jobs": jobs,
        "diagnostic_only": True,
        "independent_gate_satisfied": False,
        "model_execution": False,
    }


def _normalize_reason(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value)
    return value


def _templated_reason_diagnostic(reasons: list[str]) -> dict[str, Any]:
    normalized = [x for x in (_normalize_reason(r) for r in reasons) if x]
    if len(normalized) < 3:
        return {"detected": False, "identical_ratio": 0.0, "sample_count": len(normalized)}
    counts = Counter(normalized)
    ratio = max(counts.values()) / len(normalized)
    return {"detected": ratio >= 0.75, "identical_ratio": round(ratio, 4), "sample_count": len(normalized)}


def _index_jobs(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for job in packet.get("jobs", []):
        if job.get("job_id") in jobs:
            raise ValueError(f"duplicate job_id: {job.get('job_id')}")
        jobs[job["job_id"]] = job
    return jobs


def aggregate(packet: dict[str, Any], results_payload: dict[str, Any]) -> dict[str, Any]:
    if packet.get("schema") != SCHEMA:
        raise ValueError("reader-panel schema mismatch")
    jobs = _index_jobs(packet)
    completed: list[tuple[dict[str, Any], dict[str, Any]]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for result in results_payload.get("results", []):
        job_id = result.get("job_id")
        if job_id in seen:
            errors.append(f"duplicate result: {job_id}")
            continue
        seen.add(job_id)
        job = jobs.get(job_id)
        if not job:
            errors.append(f"unknown result job: {job_id}")
            continue
        item_errors = validate_result(job, result)
        if item_errors:
            errors.extend(f"{job_id}: {e}" for e in item_errors)
            continue
        if result.get("status") == "completed":
            completed.append((job, result))
    reasons = [str(result.get("judgment", {}).get("reason", "")) for _, result in completed]
    base = {
        "schema": "novelforge_reader_panel_report_v1",
        "mode": packet.get("mode"),
        "candidate_ids": packet.get("candidate_ids", []),
        "completed": len(completed),
        "expected": len(jobs),
        "errors": errors,
        "templated_reason": _templated_reason_diagnostic(reasons),
        "diagnostic_only": True,
        "independent_gate_satisfied": False,
        "authority": False,
    }
    if packet.get("mode") == "single":
        rows = []
        continue_votes: list[bool] = []
        desires: list[float] = []
        for job, result in completed:
            j = result.get("judgment", {})
            persona = job["input"]["persona_id"]
            vote = j.get("would_continue")
            desire = j.get("continue_desire")
            if isinstance(vote, bool):
                continue_votes.append(vote)
            if isinstance(desire, (int, float)) and not isinstance(desire, bool):
                desires.append(float(desire))
            rows.append({
                "persona_id": persona,
                "would_continue": vote,
                "continue_desire": desire,
                "drop_off_point": j.get("drop_off_point"),
                "favorite_beat": j.get("favorite_beat"),
                "stumble_beat": j.get("stumble_beat"),
                "reason": j.get("reason"),
            })
        true_count = sum(1 for x in continue_votes if x)
        false_count = len(continue_votes) - true_count
        disagreement = true_count > 0 and false_count > 0
        base.update({
            "readers": rows,
            "continue_rate": round(true_count / len(continue_votes), 4) if continue_votes else None,
            "mean_continue_desire": round(sum(desires) / len(desires), 4) if desires else None,
            "persona_disagreement": disagreement,
        })
        return base

    pair_rows = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    first_position_wins = 0
    decisive_visible = 0
    normalized_winners: list[str] = []
    for job, result in completed:
        j = result.get("judgment", {})
        visible_winner = j.get("winner")
        order = job["input"]["visible_order"]
        canonical_winner = None
        if visible_winner in {"A", "B"}:
            canonical_winner = order[visible_winner]
            decisive_visible += 1
            if visible_winner == "A":
                first_position_wins += 1
            normalized_winners.append(canonical_winner)
        row = {
            "persona_id": job["input"]["persona_id"],
            "order_key": job["input"]["order_key"],
            "visible_winner": visible_winner,
            "canonical_winner": canonical_winner,
            "reason": j.get("reason"),
        }
        pair_rows.append(row)
        grouped[row["persona_id"]].append(row)
    inconsistent_personas: list[str] = []
    first_shown_biased_personas: list[str] = []
    for persona, rows in grouped.items():
        decisive = [r for r in rows if r["canonical_winner"]]
        if len(decisive) >= 2 and len({r["canonical_winner"] for r in decisive}) > 1:
            inconsistent_personas.append(persona)
            if all(r["visible_winner"] == "A" for r in decisive):
                first_shown_biased_personas.append(persona)
    counts = Counter(normalized_winners)
    top = counts.most_common()
    canonical_consensus = top[0][0] if top and (len(top) == 1 or top[0][1] > top[1][1]) else None
    first_rate = first_position_wins / decisive_visible if decisive_visible else 0.0
    base.update({
        "comparisons": pair_rows,
        "canonical_winner_counts": dict(counts),
        "canonical_consensus": canonical_consensus,
        "persona_inconsistency": inconsistent_personas,
        "first_shown_bias": {
            "detected": bool(first_shown_biased_personas) or (decisive_visible >= 4 and first_rate >= 0.8),
            "first_position_win_rate": round(first_rate, 4),
            "personas": first_shown_biased_personas,
        },
        "persona_disagreement": len(counts) > 1,
    })
    return base


def _result_for(job: dict[str, Any], judgment: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self-test", "model_or_reviewer": "fixture"},
        "judgment": judgment,
        "proposals": [],
        "errors": [],
        "execution": {"source_session_id": None, "worker_session_id": "SELF", "handoff_id": None, "attempt_id": "1"},
    }


def self_test() -> int:
    single = build_single("C1", "A short candidate.", ["binge_reader", "investment_reader"])
    valid_fp = all(job["input_fingerprint"] == fingerprint_for(job) for job in single["jobs"])
    pair = build_pairwise("C1", "Version one.", "C2", "Version two.", ["binge_reader", "genre_native_reader"])
    results = []
    for job in pair["jobs"]:
        # Deliberately choose the first-shown item in both swapped orders and repeat
        # the same reason so self-test can prove the diagnostics are active.
        results.append(_result_for(job, {"winner": "A", "reason": "first one feels stronger", "confidence": 0.8}))
    report = aggregate(pair, {"results": results})
    no_forbidden = all(not FORBIDDEN_PACKET_KEYS.intersection(job["input"]) for job in pair["jobs"])
    ok = (
        valid_fp and no_forbidden and report["first_shown_bias"]["detected"] is True
        and report["templated_reason"]["detected"] is True
        and report["independent_gate_satisfied"] is False
        and pair["model_execution"] is False
    )
    dump({
        "reader_panel_contract": "PASS" if ok else "FAIL",
        "fingerprint_bound": valid_fp,
        "pairwise_order_swap": True,
        "first_shown_bias_detected": report["first_shown_bias"]["detected"],
        "templated_reason_detected": report["templated_reason"]["detected"],
        "independent_gate_satisfied": False,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge reader simulation panel")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("build-single")
    s.add_argument("--candidate-id", required=True); s.add_argument("--text-file", required=True); s.add_argument("--output")
    s.add_argument("--persona", action="append", dest="personas")
    ab = sub.add_parser("build-pairwise")
    ab.add_argument("--candidate-a-id", required=True); ab.add_argument("--candidate-a-file", required=True)
    ab.add_argument("--candidate-b-id", required=True); ab.add_argument("--candidate-b-file", required=True); ab.add_argument("--output")
    ab.add_argument("--persona", action="append", dest="personas")
    ag = sub.add_parser("aggregate")
    ag.add_argument("--packet", required=True); ag.add_argument("--results", required=True); ag.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "build-single":
        payload = build_single(args.candidate_id, Path(args.text_file).read_text(encoding="utf-8"), args.personas)
        dump(payload, Path(args.output) if args.output else None); return 0
    if args.command == "build-pairwise":
        payload = build_pairwise(
            args.candidate_a_id, Path(args.candidate_a_file).read_text(encoding="utf-8"),
            args.candidate_b_id, Path(args.candidate_b_file).read_text(encoding="utf-8"), args.personas,
        )
        dump(payload, Path(args.output) if args.output else None); return 0
    report = aggregate(load_json(Path(args.packet)), load_json(Path(args.results)))
    dump(report, Path(args.output) if args.output else None)
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
