#!/usr/bin/env python3
"""Prepare and validate a three-arm corpus-style ablation without judging it.

The evaluator freezes one task/context/randomness tuple for three generated
artifacts, expands the three unordered arm pairs into repeated, order-swapped
Blind Reader jobs with eight non-weighted dimensions, and prepares a separate
semantic-leakage review as the ninth evidence item.  Arm
identity, craft bindings, leave-one-work-out membership, and scene-function
holdouts stay in the private plan and never enter a Blind Reader payload.

This module performs no model calls.  Missing semantic results remain
``PENDING_MODEL``.  Even complete blind and leakage evidence grants no release,
promotion, Canon, taste, or Framework authority.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from corpus import style_contract  # noqa: E402
from harness.semantic_workers.semantic_worker_router import (  # noqa: E402
    make_contract_job,
    validate_job,
    validate_result,
)


SUITE_SCHEMA = "quillframe_style_corpus_ablation_suite_v1"
PLAN_SCHEMA = "quillframe_style_corpus_ablation_plan_v1"
BLIND_QUEUE_SCHEMA = "quillframe_blind_prose_pair_queue_v1"
LEAKAGE_QUEUE_SCHEMA = "quillframe_prose_semantic_leakage_queue_v1"
EVIDENCE_SCHEMA = "quillframe_style_corpus_ablation_evidence_v1"

BLIND_PAIR_CONTRACT = "learning.blind_prose_pair"
SEMANTIC_LEAKAGE_CONTRACT = "learning.prose_semantic_leakage"

ARMS = ("baseline", "current_craft_v4", "corpus_candidate")
PAIRINGS = tuple(combinations(ARMS, 2))
BLIND_DIMENSIONS = (
    "content_fidelity",
    "causal_movement",
    "target_mechanism",
    "naturalness",
    "readability",
    "engagement",
    "diversity",
    "originality",
)
SCENE_FUNCTIONS = (
    "opening",
    "dialogue",
    "action",
    "interiority",
    "exposition",
    "environment",
    "body_appearance",
    "relationship",
    "transition",
    "ending",
)

DEFAULT_SUITE = Path(__file__).with_name("fixtures") / "style_corpus_ablation_synthetic.json"
MAX_CASES = 32
MAX_TEXT_CHARS = 50_000
MAX_CONTEXT_BYTES = 64 * 1024
MAX_CRAFT_BYTES = 128 * 1024

_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_BLIND_FORBIDDEN_KEY_PARTS = {
    "arm",
    "author",
    "candidate",
    "craft",
    "creator",
    "source",
    "style",
    "title",
    "treatment",
    "work",
}
_TRUE_LABELS = {value.casefold() for value in ARMS}
_PROVENANCE_KEYS = {
    "evidence_class",
    "authorship",
    "derived_from_external_prose",
    "derived_from_consumer",
    "human_quality_validated",
    "model_quality_validated",
}


class StyleCorpusAblationError(ValueError):
    """Closed-contract failure for this evaluator."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def text_fingerprint(text: str) -> str:
    if not isinstance(text, str):
        raise StyleCorpusAblationError("text must be a string")
    try:
        encoded = text.encode("utf-8")
    except UnicodeError as exc:
        raise StyleCorpusAblationError("text must encode as exact UTF-8") from exc
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StyleCorpusAblationError(message)


def _nonempty(value: Any, *, maximum: int | None = None) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and (maximum is None or len(value) <= maximum)
    )


def _machine_id(value: Any) -> bool:
    return isinstance(value, str) and _MACHINE_ID_RE.fullmatch(value) is not None


def _fingerprint(value: Any) -> bool:
    return isinstance(value, str) and _FINGERPRINT_RE.fullmatch(value) is not None


def _closed(value: Any, keys: set[str], message: str) -> None:
    _require(isinstance(value, dict) and set(value) == keys, message)


def _seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = fingerprint({key: item for key, item in value.items() if key != field})
    return value


def _check_seal(value: Mapping[str, Any], field: str) -> None:
    _require(
        value.get(field)
        == fingerprint({key: item for key, item in value.items() if key != field}),
        field + " changed",
    )


def _named_keys(value: Any, names: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in names:
                found.append(key)
            found.extend(_named_keys(child, names))
    elif isinstance(value, list):
        for child in value:
            found.extend(_named_keys(child, names))
    return found


def _blind_payload_errors(value: Any, *, path: str = "$", text_field: bool = False) -> list[str]:
    """Reject treatment metadata while permitting ordinary words inside prose."""

    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            parts = {part for part in re.split(r"[^a-z0-9]+", key.casefold()) if part}
            if parts & _BLIND_FORBIDDEN_KEY_PARTS:
                errors.append(f"{path}.{key}: blind metadata key forbidden")
            errors.extend(
                _blind_payload_errors(
                    child,
                    path=f"{path}.{key}",
                    text_field=key in {"text", "evaluation_task"},
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(
                _blind_payload_errors(child, path=f"{path}[{index}]", text_field=text_field)
            )
    elif isinstance(value, str) and not text_field and value.casefold() in _TRUE_LABELS:
        errors.append(f"{path}: true condition label forbidden")
    return errors


def _validate_provenance(value: Any) -> None:
    _closed(value, _PROVENANCE_KEYS, "provenance schema must be closed")
    _require(
        value["evidence_class"] in {"synthetic_test", "live_frozen"},
        "invalid evidence class",
    )
    for field in (
        "derived_from_external_prose",
        "derived_from_consumer",
        "human_quality_validated",
        "model_quality_validated",
    ):
        _require(isinstance(value[field], bool), f"{field} must be boolean")
    _require(_nonempty(value["authorship"], maximum=160), "authorship required")
    if value["evidence_class"] == "synthetic_test":
        _require(
            value["authorship"] == "original_synthetic_assistant_authored"
            and all(
                value[field] is False
                for field in (
                    "derived_from_external_prose",
                    "derived_from_consumer",
                    "human_quality_validated",
                    "model_quality_validated",
                )
            ),
            "synthetic fixture provenance is not test-only",
        )


def validate_suite(suite: Any) -> None:
    """Validate a frozen suite without inventing fingerprints or expected labels."""

    top = {
        "schema",
        "suite_version",
        "repeat_count",
        "provenance",
        "work_universe",
        "scene_function_universe",
        "reading_criteria",
        "reference_samples",
        "cases",
    }
    _closed(suite, top, "suite schema must be closed")
    _require(suite["schema"] == SUITE_SCHEMA, "suite schema mismatch")
    _require(_nonempty(suite["suite_version"], maximum=80), "suite version required")
    _require(
        isinstance(suite["repeat_count"], int)
        and not isinstance(suite["repeat_count"], bool)
        and 2 <= suite["repeat_count"] <= 3,
        "repeat_count must be two or three",
    )
    _validate_provenance(suite["provenance"])
    _require(
        not _named_keys(
            suite,
            {"expected", "expected_result", "expected_winner", "gold", "gold_label", "pass"},
        ),
        "suite may not contain expected or gold outcomes",
    )

    works = suite["work_universe"]
    scenes = suite["scene_function_universe"]
    _require(
        isinstance(works, list)
        and 3 <= len(works) <= MAX_CASES
        and len(works) == len(set(works))
        and all(_machine_id(value) for value in works),
        "work universe must contain unique opaque ids",
    )
    _require(
        isinstance(scenes, list)
        and 3 <= len(scenes) <= len(SCENE_FUNCTIONS)
        and len(scenes) == len(set(scenes))
        and all(value in SCENE_FUNCTIONS for value in scenes),
        "scene-function universe invalid",
    )
    criteria = suite["reading_criteria"]
    _require(
        isinstance(criteria, list)
        and 3 <= len(criteria) <= 12
        and all(_nonempty(value, maximum=500) for value in criteria),
        "reading criteria invalid",
    )
    references = suite["reference_samples"]
    _require(
        isinstance(references, list) and len(references) == len(works),
        "one reference sample per work is required",
    )
    reference_ids: set[str] = set()
    for row in references:
        _closed(row, {"work_id", "text"}, "reference sample schema must be closed")
        _require(
            row["work_id"] in works and row["work_id"] not in reference_ids,
            "reference work id missing or duplicated",
        )
        reference_ids.add(row["work_id"])
        _require(_nonempty(row["text"], maximum=MAX_TEXT_CHARS), "reference text invalid")
    _require(reference_ids == set(works), "reference sample coverage incomplete")

    cases = suite["cases"]
    _require(
        isinstance(cases, list) and len(cases) == len(works) and len(cases) <= MAX_CASES,
        "leave-one-work-out requires one case per work",
    )
    case_ids: set[str] = set()
    heldout_works: list[str] = []
    heldout_scenes: list[str] = []
    for case in cases:
        _closed(
            case,
            {"case_id", "heldout_work_id", "scene_function", "task", "context", "randomness", "arms"},
            "case schema must be closed",
        )
        _require(
            _machine_id(case["case_id"]) and case["case_id"] not in case_ids,
            "case id missing or duplicated",
        )
        case_ids.add(case["case_id"])
        _require(case["heldout_work_id"] in works, "held-out work outside universe")
        _require(case["scene_function"] in scenes, "held-out scene function outside universe")
        heldout_works.append(case["heldout_work_id"])
        heldout_scenes.append(case["scene_function"])
        _require(_nonempty(case["task"], maximum=5_000), "evaluation task invalid")
        _require(
            isinstance(case["context"], dict)
            and len(canonical(case["context"])) <= MAX_CONTEXT_BYTES,
            "evaluation context invalid or too large",
        )
        _require(
            isinstance(case["randomness"], dict)
            and bool(case["randomness"])
            and len(canonical(case["randomness"])) <= MAX_CONTEXT_BYTES,
            "frozen randomness invalid",
        )
        _require(not _blind_payload_errors(case["context"]), "evaluation context leaks condition metadata")

        arms = case["arms"]
        _require(isinstance(arms, dict) and set(arms) == set(ARMS), "exactly three arms required")
        for arm in ARMS:
            artifact = arms[arm]
            _closed(artifact, {"text", "craft_binding"}, "arm artifact schema must be closed")
            _require(_nonempty(artifact["text"], maximum=MAX_TEXT_CHARS), "arm text invalid")
            _require(
                isinstance(artifact["craft_binding"], dict)
                and bool(artifact["craft_binding"])
                and len(canonical(artifact["craft_binding"])) <= MAX_CRAFT_BYTES,
                "craft binding invalid or too large",
            )

        corpus_binding = arms["corpus_candidate"]["craft_binding"]
        required_binding = {
            "contract",
            "version",
            "evidence_work_ids",
            "excluded_work_id",
            "training_scene_functions",
            "excluded_scene_function",
            "writer_projection",
        }
        _closed(corpus_binding, required_binding, "corpus craft binding schema must be closed")
        _require(
            corpus_binding["contract"] == "source_free_corpus_candidate"
            and _nonempty(corpus_binding["version"], maximum=80),
            "corpus craft contract binding invalid",
        )
        _require(
            corpus_binding["excluded_work_id"] == case["heldout_work_id"]
            and set(corpus_binding["evidence_work_ids"])
            == set(works) - {case["heldout_work_id"]},
            "leave-one-work-out evidence binding invalid",
        )
        _require(
            len(corpus_binding["evidence_work_ids"])
            == len(set(corpus_binding["evidence_work_ids"])),
            "leave-one-work-out evidence contains duplicates",
        )
        _require(
            corpus_binding["excluded_scene_function"] == case["scene_function"]
            and set(corpus_binding["training_scene_functions"])
            == set(scenes) - {case["scene_function"]},
            "scene-function holdout binding invalid",
        )
        _require(
            len(corpus_binding["training_scene_functions"])
            == len(set(corpus_binding["training_scene_functions"])),
            "training scene functions contain duplicates",
        )
        _require(
            isinstance(corpus_binding["writer_projection"], dict)
            and bool(corpus_binding["writer_projection"]),
            "source-free writer projection required",
        )

    _require(
        sorted(heldout_works) == sorted(works),
        "every work must be held out exactly once",
    )
    _require(
        set(heldout_scenes) == set(scenes),
        "every declared scene function must appear as a holdout",
    )


def load_suite(path: Path = DEFAULT_SUITE) -> dict[str, Any]:
    suite = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_suite(suite)
    return suite


def _private_case(suite: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    generation_inputs = {
        "task": deepcopy(case["task"]),
        "context": deepcopy(case["context"]),
        "randomness": deepcopy(case["randomness"]),
    }
    bindings: dict[str, Any] = {}
    for arm in ARMS:
        artifact = case["arms"][arm]
        bindings[arm] = {
            "candidate_fingerprint": text_fingerprint(artifact["text"]),
            "craft_binding": deepcopy(artifact["craft_binding"]),
            "craft_fingerprint": fingerprint(artifact["craft_binding"]),
        }
    return {
        "case_id": case["case_id"],
        "heldout_work_id": case["heldout_work_id"],
        "scene_function": case["scene_function"],
        "generation_inputs": generation_inputs,
        "task_fingerprint": fingerprint(case["task"]),
        "context_fingerprint": fingerprint(case["context"]),
        "randomness_fingerprint": fingerprint(case["randomness"]),
        "generation_binding_fingerprint": fingerprint(generation_inputs),
        "arms": bindings,
    }


def _opaque(prefix: str, value: Any, length: int = 20) -> str:
    return prefix + "-" + fingerprint(value)[7 : 7 + length]


def prepare_evaluation(
    suite: dict[str, Any],
    *,
    run_id: str,
    order_seed: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a private plan and registered queues; perform zero model calls."""

    validate_suite(suite)
    _require(_machine_id(run_id), "run_id must be an opaque machine id")
    _require(_nonempty(order_seed, maximum=500), "order seed required")
    when = created_at or datetime.now(timezone.utc).isoformat()
    _require(_nonempty(when, maximum=160), "created_at required")
    suite_fp = fingerprint(suite)
    private_cases = [_private_case(suite, case) for case in suite["cases"]]
    by_case = {case["case_id"]: case for case in suite["cases"]}
    private_by_case = {case["case_id"]: case for case in private_cases}

    presentations: list[dict[str, Any]] = []
    for case in suite["cases"]:
        private = private_by_case[case["case_id"]]
        for left, right in PAIRINGS:
            pair_id = _opaque("PAIR", [suite_fp, order_seed, case["case_id"], left, right])
            for repeat_index in range(1, suite["repeat_count"] + 1):
                for orientation in ("forward", "swapped"):
                    order = (left, right) if orientation == "forward" else (right, left)
                    comparison_id = _opaque(
                        "CMP",
                        [suite_fp, order_seed, case["case_id"], pair_id, repeat_index, orientation],
                    )
                    payload = {
                        "comparison_id": comparison_id,
                        "evaluation_task": deepcopy(case["task"]),
                        "evaluation_context": deepcopy(case["context"]),
                        "scene_function": case["scene_function"],
                        "sample_a": {"sample_id": "A", "text": case["arms"][order[0]]["text"]},
                        "sample_b": {"sample_id": "B", "text": case["arms"][order[1]]["text"]},
                        "criteria": deepcopy(suite["reading_criteria"]),
                    }
                    errors = _blind_payload_errors(payload)
                    _require(not errors, "; ".join(errors))
                    job = make_contract_job(
                        BLIND_PAIR_CONTRACT,
                        comparison_id,
                        payload,
                        job_id="SEM-BLIND-" + comparison_id[4:],
                        source_session_id="EVAL-" + run_id,
                        handoff_id=run_id + ":" + comparison_id,
                    )
                    job["created_at"] = when
                    presentations.append(
                        {
                            "case_id": case["case_id"],
                            "pair_id": pair_id,
                            "pair_arms": [left, right],
                            "repeat_index": repeat_index,
                            "orientation": orientation,
                            "comparison_id": comparison_id,
                            "private_mapping": {"A": order[0], "B": order[1]},
                            "presented_candidate_fingerprints": {
                                "A": private["arms"][order[0]]["candidate_fingerprint"],
                                "B": private["arms"][order[1]]["candidate_fingerprint"],
                            },
                            "job": job,
                        }
                    )
    presentations.sort(
        key=lambda row: fingerprint([order_seed, row["comparison_id"], "presentation-order"])
    )

    references = {row["work_id"]: row["text"] for row in suite["reference_samples"]}
    leakage_items: list[dict[str, Any]] = []
    for case in suite["cases"]:
        private = private_by_case[case["case_id"]]
        candidate_text = case["arms"]["corpus_candidate"]["text"]
        local_report = style_contract.check_local_leakage(candidate_text, references)
        review_id = _opaque("LEAK", [suite_fp, order_seed, case["case_id"]])
        payload = {
            "review_id": review_id,
            "sample": {
                "text": candidate_text,
                "text_fingerprint": text_fingerprint(candidate_text),
            },
            "reference_samples": [
                {
                    "reference_id": work_id,
                    "text": references[work_id],
                    "text_fingerprint": text_fingerprint(references[work_id]),
                }
                for work_id in sorted(references)
            ],
        }
        job = make_contract_job(
            SEMANTIC_LEAKAGE_CONTRACT,
            review_id,
            payload,
            job_id="SEM-LEAK-" + review_id[5:],
            source_session_id="EVAL-" + run_id,
            handoff_id=run_id + ":" + review_id,
        )
        job["created_at"] = when
        leakage_items.append(
            {
                "case_id": case["case_id"],
                "review_id": review_id,
                "candidate_fingerprint": private["arms"]["corpus_candidate"][
                    "candidate_fingerprint"
                ],
                "craft_fingerprint": private["arms"]["corpus_candidate"]["craft_fingerprint"],
                "local_report": local_report,
                "job": job,
            }
        )

    plan = {
        "schema": PLAN_SCHEMA,
        "run_id": run_id,
        "created_at": when,
        "suite_fingerprint": suite_fp,
        "order_seed_fingerprint": fingerprint(order_seed),
        "test_only": suite["provenance"]["evidence_class"] == "synthetic_test",
        "repeat_count": suite["repeat_count"],
        "work_universe": deepcopy(suite["work_universe"]),
        "scene_function_universe": deepcopy(suite["scene_function_universe"]),
        "private_cases": private_cases,
        "blind_presentations": presentations,
        "leakage_reviews": leakage_items,
        "semantic_status": "PENDING_MODEL",
        "model_execution": False,
        "authority": {
            "release": False,
            "framework_promotion": False,
            "canon_write": False,
            "durable_user_taste_write": False,
        },
    }
    _seal(plan, "plan_fingerprint")
    validate_prepared(plan)
    return plan


def _private_case_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["case_id"]: row for row in plan["private_cases"]}


def validate_prepared(plan: Any) -> None:
    """Fail closed on mapping, fingerprint, holdout, or registered-job drift."""

    _require(isinstance(plan, dict) and plan.get("schema") == PLAN_SCHEMA, "plan schema mismatch")
    _check_seal(plan, "plan_fingerprint")
    _require(plan.get("model_execution") is False, "preparation may not claim model execution")
    _require(plan.get("semantic_status") == "PENDING_MODEL", "prepared status must remain pending")
    authority = plan.get("authority")
    _require(
        isinstance(authority, dict) and authority and all(value is False for value in authority.values()),
        "prepared plan may not grant authority",
    )
    _require(
        isinstance(plan.get("repeat_count"), int) and 2 <= plan["repeat_count"] <= 3,
        "repeat count invalid",
    )
    works = plan.get("work_universe")
    scenes = plan.get("scene_function_universe")
    _require(isinstance(works, list) and len(works) >= 3, "work universe missing")
    _require(isinstance(scenes, list) and len(scenes) >= 3, "scene universe missing")

    private_cases = plan.get("private_cases")
    _require(
        isinstance(private_cases, list) and len(private_cases) == len(works),
        "private case bindings incomplete",
    )
    case_map: dict[str, dict[str, Any]] = {}
    for case in private_cases:
        _require(_machine_id(case.get("case_id")) and case["case_id"] not in case_map, "private case id invalid")
        case_map[case["case_id"]] = case
        generation = case.get("generation_inputs")
        _require(
            isinstance(generation, dict) and set(generation) == {"task", "context", "randomness"},
            "generation input binding invalid",
        )
        _require(case.get("task_fingerprint") == fingerprint(generation["task"]), "task fingerprint mismatch")
        _require(
            case.get("context_fingerprint") == fingerprint(generation["context"]),
            "context fingerprint mismatch",
        )
        _require(
            case.get("randomness_fingerprint") == fingerprint(generation["randomness"]),
            "randomness fingerprint mismatch",
        )
        _require(
            case.get("generation_binding_fingerprint") == fingerprint(generation),
            "generation binding fingerprint mismatch",
        )
        bindings = case.get("arms")
        _require(isinstance(bindings, dict) and set(bindings) == set(ARMS), "private arm binding invalid")
        for arm in ARMS:
            binding = bindings[arm]
            _require(_fingerprint(binding.get("candidate_fingerprint")), "candidate fingerprint invalid")
            _require(
                isinstance(binding.get("craft_binding"), dict)
                and binding.get("craft_fingerprint") == fingerprint(binding["craft_binding"]),
                "craft fingerprint mismatch",
            )
        corpus = bindings["corpus_candidate"]["craft_binding"]
        _require(
            corpus.get("excluded_work_id") == case.get("heldout_work_id")
            and set(corpus.get("evidence_work_ids", [])) == set(works) - {case.get("heldout_work_id")},
            "leave-one-work-out plan binding invalid",
        )
        _require(
            corpus.get("excluded_scene_function") == case.get("scene_function")
            and set(corpus.get("training_scene_functions", [])) == set(scenes) - {case.get("scene_function")},
            "scene-function holdout plan binding invalid",
        )

    expected_presentations = len(private_cases) * len(PAIRINGS) * plan["repeat_count"] * 2
    presentations = plan.get("blind_presentations")
    _require(
        isinstance(presentations, list) and len(presentations) == expected_presentations,
        "blind presentation matrix incomplete",
    )
    seen_comparisons: set[str] = set()
    matrix: set[tuple[str, tuple[str, str], int, str]] = set()
    pair_ids: dict[tuple[str, tuple[str, str]], str] = {}
    for row in presentations:
        case = case_map.get(row.get("case_id"))
        _require(case is not None, "blind presentation references unknown case")
        comparison_id = row.get("comparison_id")
        _require(_machine_id(comparison_id) and comparison_id not in seen_comparisons, "comparison id invalid or duplicated")
        seen_comparisons.add(comparison_id)
        pair = tuple(row.get("pair_arms", []))
        _require(pair in PAIRINGS, "unknown arm pair")
        repeat_index = row.get("repeat_index")
        orientation = row.get("orientation")
        _require(
            isinstance(repeat_index, int)
            and 1 <= repeat_index <= plan["repeat_count"]
            and orientation in {"forward", "swapped"},
            "repeat or orientation invalid",
        )
        identity = (case["case_id"], pair, repeat_index, orientation)
        _require(identity not in matrix, "blind presentation repeated")
        matrix.add(identity)
        pair_key = (case["case_id"], pair)
        previous_pair_id = pair_ids.setdefault(pair_key, row.get("pair_id"))
        _require(previous_pair_id == row.get("pair_id"), "pair id drift across repeats")
        mapping = row.get("private_mapping")
        expected_mapping = (
            {"A": pair[0], "B": pair[1]}
            if orientation == "forward"
            else {"A": pair[1], "B": pair[0]}
        )
        _require(mapping == expected_mapping, "private presentation mapping changed")
        presented = row.get("presented_candidate_fingerprints")
        _require(
            isinstance(presented, dict)
            and set(presented) == {"A", "B"}
            and all(
                presented[label] == case["arms"][mapping[label]]["candidate_fingerprint"]
                for label in ("A", "B")
            ),
            "presented candidate fingerprint mapping changed",
        )
        job = row.get("job")
        _require(isinstance(job, dict) and not validate_job(job), "blind job invalid")
        _require(
            job.get("subject_id") == comparison_id
            and job.get("provenance", {}).get("model_contract_id") == BLIND_PAIR_CONTRACT
            and job.get("provenance", {}).get("independent_gate") is True,
            "blind job must use the registered independent contract",
        )
        payload = job["input"]["payload"]
        _require(payload.get("comparison_id") == comparison_id, "blind comparison binding mismatch")
        _require(not _blind_payload_errors(payload), "blind payload leaks condition metadata")
        _require(
            payload.get("evaluation_task") == case["generation_inputs"]["task"]
            and payload.get("evaluation_context") == case["generation_inputs"]["context"]
            and payload.get("scene_function") == case["scene_function"],
            "blind job does not share the frozen task and context",
        )
        for label, sample_key in (("A", "sample_a"), ("B", "sample_b")):
            sample = payload.get(sample_key, {})
            _require(
                sample.get("sample_id") == label
                and text_fingerprint(sample.get("text")) == presented[label],
                "blind sample exact-text fingerprint mismatch",
            )

    expected_matrix = {
        (case_id, pair, repeat, orientation)
        for case_id in case_map
        for pair in PAIRINGS
        for repeat in range(1, plan["repeat_count"] + 1)
        for orientation in ("forward", "swapped")
    }
    _require(matrix == expected_matrix, "blind pair/order/repeat matrix incomplete")

    leakage_reviews = plan.get("leakage_reviews")
    _require(
        isinstance(leakage_reviews, list) and len(leakage_reviews) == len(private_cases),
        "semantic leakage reviews incomplete",
    )
    seen_cases: set[str] = set()
    for row in leakage_reviews:
        case = case_map.get(row.get("case_id"))
        _require(case is not None and case["case_id"] not in seen_cases, "leakage case invalid or duplicated")
        seen_cases.add(case["case_id"])
        expected = case["arms"]["corpus_candidate"]
        _require(
            row.get("candidate_fingerprint") == expected["candidate_fingerprint"]
            and row.get("craft_fingerprint") == expected["craft_fingerprint"],
            "leakage candidate/craft binding mismatch",
        )
        report = row.get("local_report")
        _require(not style_contract.validate_leakage_report(report), "local leakage report invalid")
        _require(
            report["candidate_fingerprint"] == expected["candidate_fingerprint"],
            "local leakage candidate fingerprint mismatch",
        )
        job = row.get("job")
        _require(isinstance(job, dict) and not validate_job(job), "semantic leakage job invalid")
        _require(
            job.get("subject_id") == row.get("review_id")
            and job.get("provenance", {}).get("model_contract_id") == SEMANTIC_LEAKAGE_CONTRACT
            and job.get("provenance", {}).get("independent_gate") is True,
            "semantic leakage job must use the registered independent contract",
        )
        payload = job["input"]["payload"]
        _require(payload.get("review_id") == row.get("review_id"), "leakage review binding mismatch")
        _require(
            text_fingerprint(payload["sample"]["text"])
            == payload["sample"]["text_fingerprint"]
            == expected["candidate_fingerprint"],
            "semantic leakage sample fingerprint mismatch",
        )
        reference_ids = {reference["reference_id"] for reference in payload["reference_samples"]}
        _require(reference_ids == set(works), "semantic leakage reference coverage mismatch")
        for reference in payload["reference_samples"]:
            _require(
                text_fingerprint(reference["text"]) == reference["text_fingerprint"],
                "semantic leakage reference fingerprint mismatch",
            )


def blind_reader_queue(plan: dict[str, Any]) -> dict[str, Any]:
    """Return reviewer jobs only; the true arm mapping never leaves the plan."""

    validate_prepared(plan)
    return {
        "schema": BLIND_QUEUE_SCHEMA,
        "blind": True,
        "test_only": plan["test_only"],
        "semantic_status": "PENDING_MODEL",
        "jobs": [deepcopy(row["job"]) for row in plan["blind_presentations"]],
        "authority": False,
        "model_execution": False,
    }


def semantic_leakage_queue(plan: dict[str, Any]) -> dict[str, Any]:
    """Return the separate independent semantic-similarity review queue."""

    validate_prepared(plan)
    return {
        "schema": LEAKAGE_QUEUE_SCHEMA,
        "test_only": plan["test_only"],
        "semantic_status": "PENDING_MODEL",
        "jobs": [deepcopy(row["job"]) for row in plan["leakage_reviews"]],
        "authority": False,
        "release_authority": False,
        "model_execution": False,
    }


def _index_results(results: Iterable[dict[str, Any]], allowed: set[str]) -> dict[str, dict[str, Any]]:
    _require(isinstance(results, list), "semantic results must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for result in results:
        _require(isinstance(result, dict), "semantic result must be an object")
        subject = result.get("subject_id")
        _require(subject in allowed, "semantic result references an unknown subject")
        _require(subject not in indexed, "duplicate semantic result subject")
        indexed[subject] = result
    return indexed


def _invocation(result: dict[str, Any]) -> str:
    execution = result.get("execution") if isinstance(result.get("execution"), dict) else {}
    worker = result.get("worker") if isinstance(result.get("worker"), dict) else {}
    value = (
        execution.get("worker_session_id")
        or execution.get("attempt_id")
        or worker.get("run_reference")
    )
    _require(_nonempty(value, maximum=500), "independent invocation lineage required")
    return value


def _validated_completed(job: dict[str, Any], result: dict[str, Any]) -> str | None:
    errors = validate_result(job, result)
    _require(not errors, "; ".join(errors))
    if result.get("status") != "completed":
        return None
    return _invocation(result)


def consume_evidence(
    plan: dict[str, Any],
    *,
    blind_results: list[dict[str, Any]],
    leakage_results: list[dict[str, Any]],
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    """Validate independent evidence; never select or authorize a winning arm."""

    validate_prepared(plan)
    if plan["test_only"] and (blind_results or leakage_results):
        _require(allow_synthetic, "synthetic results are test-only and cannot become live evidence")

    blind_allowed = {row["comparison_id"] for row in plan["blind_presentations"]}
    leak_allowed = {row["review_id"] for row in plan["leakage_reviews"]}
    blind_by_subject = _index_results(blind_results, blind_allowed)
    leak_by_subject = _index_results(leakage_results, leak_allowed)
    invocations: set[str] = set()

    pair_summaries: dict[tuple[str, str], dict[str, Any]] = {}
    blind_observations: list[dict[str, Any]] = []
    blind_pending: list[str] = []
    repeat_pair_choices: dict[tuple[str, int], list[str]] = {}
    repeat_dimension_choices: dict[tuple[str, int, str], list[str]] = {}
    for row in plan["blind_presentations"]:
        result = blind_by_subject.get(row["comparison_id"])
        if result is None:
            blind_pending.append(row["comparison_id"])
            continue
        invocation = _validated_completed(row["job"], result)
        if invocation is None:
            blind_pending.append(row["comparison_id"])
            continue
        _require(invocation not in invocations, "independent invocation reused across reviews")
        invocations.add(invocation)
        judgment = result["judgment"]
        _require(
            judgment.get("comparison_id") == row["comparison_id"],
            "blind result comparison id mismatch",
        )
        preference = judgment["preference"]
        if preference in {"a", "b"}:
            true_preference = row["private_mapping"][preference.upper()]
        else:
            true_preference = preference
        dimensions = judgment.get("dimensions")
        _require(
            isinstance(dimensions, dict) and set(dimensions) == set(BLIND_DIMENSIONS),
            "blind result must preserve all eight dimensions exactly once",
        )
        key = (row["case_id"], row["pair_id"])
        summary = pair_summaries.setdefault(
            key,
            {
                "case_id": row["case_id"],
                "pair_id": row["pair_id"],
                "arms": list(row["pair_arms"]),
                "required_observations": plan["repeat_count"] * 2,
                "pair_preference": {
                    "directional_counts": {
                        row["pair_arms"][0]: 0,
                        row["pair_arms"][1]: 0,
                    },
                    "tie": 0,
                    "both_bad": 0,
                    "insufficient_evidence": 0,
                },
                "dimensions": {
                    dimension: {
                        "directional_counts": {
                            row["pair_arms"][0]: 0,
                            row["pair_arms"][1]: 0,
                        },
                        "tie": 0,
                        "unclear": 0,
                    }
                    for dimension in BLIND_DIMENSIONS
                },
            },
        )
        pair_preference = summary["pair_preference"]
        if true_preference in pair_preference["directional_counts"]:
            pair_preference["directional_counts"][true_preference] += 1
        else:
            pair_preference[true_preference] += 1
        repeat_pair_choices.setdefault((row["pair_id"], row["repeat_index"]), []).append(
            true_preference
        )
        preserved_dimensions: dict[str, dict[str, str]] = {}
        for dimension in BLIND_DIMENSIONS:
            item = dimensions[dimension]
            leaning = item["leaning"]
            true_leaning = (
                row["private_mapping"][leaning.upper()] if leaning in {"a", "b"} else leaning
            )
            observation = item["observation"]
            _require(
                isinstance(observation, str) and 1 <= len(observation) <= 800,
                "dimension observation must remain bounded",
            )
            dimension_summary = summary["dimensions"][dimension]
            if true_leaning in dimension_summary["directional_counts"]:
                dimension_summary["directional_counts"][true_leaning] += 1
            else:
                dimension_summary[true_leaning] += 1
            repeat_dimension_choices.setdefault(
                (row["pair_id"], row["repeat_index"], dimension), []
            ).append(true_leaning)
            preserved_dimensions[dimension] = {
                "leaning": true_leaning,
                "observation": observation,
            }
        blind_observations.append(
            {
                "comparison_id": row["comparison_id"],
                "case_id": row["case_id"],
                "pair_id": row["pair_id"],
                "repeat_index": row["repeat_index"],
                "orientation": row["orientation"],
                "preference": true_preference,
                "dimensions": preserved_dimensions,
                "job_fingerprint": row["job"]["input_fingerprint"],
                "result_fingerprint": fingerprint(result),
                "invocation": invocation,
            }
        )
    for summary in pair_summaries.values():
        pair_preference = summary["pair_preference"]
        pair_preference["observed"] = sum(pair_preference["directional_counts"].values()) + sum(
            pair_preference[field] for field in ("tie", "both_bad", "insufficient_evidence")
        )
        consistency = []
        for repeat in range(1, plan["repeat_count"] + 1):
            values = repeat_pair_choices.get((summary["pair_id"], repeat), [])
            consistency.append(len(values) == 2 and values[0] == values[1])
        pair_preference["order_consistent_repeats"] = sum(consistency)
        for dimension in BLIND_DIMENSIONS:
            dimension_summary = summary["dimensions"][dimension]
            dimension_summary["observed"] = sum(
                dimension_summary["directional_counts"].values()
            ) + dimension_summary["tie"] + dimension_summary["unclear"]
            dimension_consistency = []
            for repeat in range(1, plan["repeat_count"] + 1):
                values = repeat_dimension_choices.get(
                    (summary["pair_id"], repeat, dimension), []
                )
                dimension_consistency.append(len(values) == 2 and values[0] == values[1])
            dimension_summary["order_consistent_repeats"] = sum(dimension_consistency)

    leakage_pending: list[str] = []
    leakage_observations: list[dict[str, Any]] = []
    semantic_leak_statuses: list[str] = []
    local_blocked = any(
        row["local_report"]["local_status"] == "blocked" for row in plan["leakage_reviews"]
    )
    for row in plan["leakage_reviews"]:
        result = leak_by_subject.get(row["review_id"])
        if result is None:
            leakage_pending.append(row["review_id"])
            continue
        invocation = _validated_completed(row["job"], result)
        if invocation is None:
            leakage_pending.append(row["review_id"])
            continue
        _require(invocation not in invocations, "independent invocation reused across reviews")
        invocations.add(invocation)
        judgment = result["judgment"]
        _require(judgment.get("review_id") == row["review_id"], "leakage result review id mismatch")
        allowed_references = {
            value["reference_id"]
            for value in row["job"]["input"]["payload"]["reference_samples"]
        }
        cited = {
            finding["reference_id"]
            for finding in judgment.get("findings", [])
            if isinstance(finding, dict)
        }
        _require(cited <= allowed_references, "semantic leakage result cites unknown reference")
        semantic_leak_statuses.append(judgment["status"])
        leakage_observations.append(
            {
                "case_id": row["case_id"],
                "review_id": row["review_id"],
                "local_status": row["local_report"]["local_status"],
                "semantic_status": judgment["status"],
                "candidate_fingerprint": row["candidate_fingerprint"],
                "craft_fingerprint": row["craft_fingerprint"],
                "local_report_fingerprint": row["local_report"]["report_fingerprint"],
                "job_fingerprint": row["job"]["input_fingerprint"],
                "result_fingerprint": fingerprint(result),
                "invocation": invocation,
            }
        )

    blind_status = "PENDING_MODEL" if blind_pending else "SEMANTIC_EVIDENCE_READY"
    if local_blocked:
        leakage_status = "BLOCKED_LOCAL"
    elif leakage_pending:
        leakage_status = "PENDING_MODEL"
    elif "blocked" in semantic_leak_statuses:
        leakage_status = "BLOCKED_SEMANTIC"
    elif "insufficient_evidence" in semantic_leak_statuses:
        leakage_status = "INSUFFICIENT_EVIDENCE"
    else:
        _require(
            len(semantic_leak_statuses) == len(plan["leakage_reviews"])
            and all(value == "clear" for value in semantic_leak_statuses),
            "semantic leakage status set invalid",
        )
        leakage_status = "SEMANTIC_EVIDENCE_READY"

    supplied = bool(blind_results or leakage_results)
    if plan["test_only"] and supplied:
        status = "SYNTHETIC_VALIDATION_ONLY"
    elif leakage_status.startswith("BLOCKED"):
        status = "LEAKAGE_BLOCKED"
    elif blind_status == "PENDING_MODEL" or leakage_status == "PENDING_MODEL":
        status = "PENDING_MODEL"
    elif leakage_status == "INSUFFICIENT_EVIDENCE":
        status = "INCONCLUSIVE"
    else:
        status = "SEMANTIC_EVIDENCE_READY"

    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "plan_fingerprint": plan["plan_fingerprint"],
        "status": status,
        "blind_status": blind_status,
        "leakage_status": leakage_status,
        "pending_blind_comparisons": blind_pending,
        "pending_leakage_reviews": leakage_pending,
        "pair_summaries": sorted(pair_summaries.values(), key=lambda row: (row["case_id"], row["pair_id"])),
        "blind_observations": blind_observations,
        "leakage_observations": leakage_observations,
        "test_only": plan["test_only"],
        "semantic_results_supplied": supplied,
        "model_execution": False,
        "aggregation_policy": {
            "dimension_weights_applied": False,
            "total_score_computed": False,
            "winner_selected": False,
            "leakage_is_independent_gate": True,
        },
        "authority": {
            "release": False,
            "framework_promotion": False,
            "canon_write": False,
            "durable_user_taste_write": False,
        },
    }
    return _seal(evidence, "evidence_fingerprint")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare"])
    parser.add_argument("--suite", default=str(DEFAULT_SUITE))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--order-seed", required=True)
    parser.add_argument("--created-at")
    args = parser.parse_args()
    plan = prepare_evaluation(
        load_suite(Path(args.suite)),
        run_id=args.run_id,
        order_seed=args.order_seed,
        created_at=args.created_at,
    )
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS",
    "BLIND_DIMENSIONS",
    "BLIND_PAIR_CONTRACT",
    "DEFAULT_SUITE",
    "PAIRINGS",
    "SEMANTIC_LEAKAGE_CONTRACT",
    "StyleCorpusAblationError",
    "blind_reader_queue",
    "canonical",
    "consume_evidence",
    "fingerprint",
    "load_suite",
    "prepare_evaluation",
    "semantic_leakage_queue",
    "text_fingerprint",
    "validate_prepared",
    "validate_suite",
]
