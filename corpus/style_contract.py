#!/usr/bin/env python3
"""Deterministic, source-free style-contract compiler and leakage gate.

The module deliberately separates two trust domains:

* analyst-side observations and cross-work candidates may contain opaque
  evidence references, but never source prose or bibliographic identity; and
* a compiled style contract and its writer projection contain craft operations
  only.  Evidence identities have no field in either closed output schema.

All literary interpretation remains model/human work.  This module owns only
closed-schema validation, deterministic fingerprints, bounded compilation and
local overlap checks.  Semantic similarity is explicitly an external release
requirement and is never simulated here.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


OBSERVATION_SCHEMA = "quillframe_style_observation_v1"
CRAFT_CANDIDATE_SCHEMA = "quillframe_cross_work_craft_candidate_v1"
STYLE_CONTRACT_SCHEMA = "quillframe_style_contract_v1"
WRITER_PROJECTION_SCHEMA = "quillframe_writer_style_projection_v1"
LEAKAGE_REPORT_SCHEMA = "quillframe_style_leakage_report_v1"

# Style is intentionally multi-dimensional.  ``body_appearance`` is an
# ordinary craft axis: this deterministic layer never infers an adult content
# partition from anatomy, appearance, or any other prose term.
STYLE_AXES = (
    "prose_voice",
    "syntax_rhythm",
    "lexical_register",
    "psychic_distance",
    "descriptive_attention",
    "body_appearance",
    "imagery",
    "dialogue_voice",
    "interiority_summary",
    "information_flow",
)
CRAFT_AXES = STYLE_AXES
CONTENT_ZONES = ("general", "adult_explicit")

MAX_SHORT_TEXT_CHARS = 1_000
MAX_CONDITION_ITEMS = 16
MAX_EVIDENCE_REFS = 64
MAX_CANDIDATES = 160
MAX_SERIALIZED_CONTRACT_BYTES = 512 * 1024
MAX_LEAKAGE_TEXT_CHARS = 500_000
MAX_LEAKAGE_REFERENCES = 256
MAX_LEAKAGE_TOTAL_CHARS = 4_000_000
MIN_CROSS_WORK_SUPPORT = 2

DEFAULT_EXACT_NGRAM_SIZE = 24
DEFAULT_NORMALIZED_NGRAM_SIZE = 32
DEFAULT_SHINGLE_SIZE = 7
DEFAULT_FUZZY_JACCARD_THRESHOLD_PPM = 350_000
DEFAULT_MINHASH_SIGNATURE_SIZE = 64

_ANALYST_KEYS = {
    "schema",
    "record_id",
    "axis",
    "operation",
    "effect",
    "applies_when",
    "avoid_when",
    "failure_boundary",
    "content_zone",
    "evidence_refs",
    "supports",
    "counterexamples",
    "confidence_ppm",
    "record_fingerprint",
}
_EVIDENCE_KEYS = {"work_id", "evidence_id", "role", "evidence_fingerprint"}
_SOURCE_FREE_CRAFT_KEYS = {
    "craft_id",
    "axis",
    "operation",
    "effect",
    "applies_when",
    "avoid_when",
    "failure_boundary",
    "content_zone",
    "confidence_ppm",
    "supporting_work_count",
    "counterexample_count",
}
_STYLE_CONTRACT_KEYS = {
    "schema",
    "contract_id",
    "content_zone",
    "attribution_mode",
    "craft_candidates",
    "leakage_policy",
    "contract_fingerprint",
}
_WRITER_CRAFT_KEYS = {
    "axis",
    "operation",
    "effect",
    "applies_when",
    "avoid_when",
    "failure_boundary",
    "content_zone",
    "confidence_ppm",
}
_WRITER_PROJECTION_KEYS = {
    "schema",
    "style_contract_fingerprint",
    "content_zone",
    "attribution_mode",
    "craft_candidates",
    "semantic_leakage_check",
    "projection_fingerprint",
}
_LEAKAGE_POLICY_KEYS = {
    "exact_ngram_size",
    "normalized_ngram_size",
    "shingle_size",
    "fuzzy_jaccard_threshold_ppm",
    "minhash_signature_size",
    "semantic_check",
}
_LEAKAGE_REPORT_KEYS = {
    "schema",
    "local_status",
    "release_ready",
    "candidate_fingerprint",
    "policy",
    "findings",
    "semantic_check",
    "report_fingerprint",
}
_LEAKAGE_REPORT_POLICY_KEYS = {
    "exact_ngram_size",
    "normalized_ngram_size",
    "shingle_size",
    "fuzzy_jaccard_threshold_ppm",
    "minhash_signature_size",
}
_LEAKAGE_FINDING_KEYS = {
    "reference_id",
    "exact_ngram_hits",
    "normalized_ngram_hits",
    "shingle_jaccard_ppm",
    "minhash_jaccard_estimate_ppm",
    "blocked",
}
_SEMANTIC_CHECK_KEYS = {"status", "performed", "reason"}

# These names describe material which may exist in the analyst enclave but
# must never be accepted by any contract payload.  Exact normalized key
# matching permits safe fields such as ``source_free`` if a future schema uses
# one, while still rejecting source/title/path containers at every depth.
FORBIDDEN_IDENTITY_OR_PROSE_FIELDS = frozenset(
    {
        "author",
        "authors",
        "creator",
        "creators",
        "title",
        "book_title",
        "source_title",
        "source_id",
        "source_name",
        "source_creator",
        "source_author",
        "path",
        "source_path",
        "file_path",
        "filepath",
        "filename",
        "relative_path",
        "relative_locator",
        "quote",
        "quotes",
        "excerpt",
        "excerpts",
        "raw",
        "raw_text",
        "source",
        "source_text",
        "source_prose",
        "passage",
        "text",
        "content",
        "body",
        "url",
        "uri",
    }
)

_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PATH_LIKE_RE = re.compile(
    r"(?:^[A-Za-z]:[\\/]|file:|[\\/](?:Users|home)[\\/]|\.\.[\\/]|~[\\/])",
    re.IGNORECASE,
)
_NAMED_IMITATION_RE = re.compile(
    r"(?:\bin\s+the\s+style\s+of\b|\bwrite\s+like\b|\bimitat(?:e|ing|ion)\b|"
    r"模仿.{0,24}(?:作者|作家|文风|风格)?|仿写|仿.{0,12}(?:作者|作家)|作者风格|作家风格)",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[\u3400-\u9fff]|[^\W_]+", re.UNICODE)


class StyleContractError(ValueError):
    """Stable contract failure with a machine-readable error code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def fingerprint(value: Any) -> str:
    """Return the repository's canonical ``sha256:`` object fingerprint."""

    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _without(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {name: child for name, child in value.items() if name != key}


def _normalized_key(value: Any) -> str:
    return str(value).strip().casefold().replace("-", "_")


def _forbidden_fields(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = _normalized_key(key)
            if normalized in FORBIDDEN_IDENTITY_OR_PROSE_FIELDS or normalized.startswith(
                ("author_", "creator_", "title_", "path_", "quote_", "raw_", "source_")
            ):
                found.add(normalized)
            found.update(_forbidden_fields(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.update(_forbidden_fields(child))
    return found


def _valid_machine_id(value: Any) -> bool:
    return isinstance(value, str) and _MACHINE_ID_RE.fullmatch(value) is not None


def _valid_short_text(value: Any, *, allow_empty: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    if value != value.strip() or "\x00" in value or _PATH_LIKE_RE.search(value):
        return False
    length = len(value)
    return (allow_empty or length > 0) and length <= MAX_SHORT_TEXT_CHARS


def _valid_text_list(value: Any, *, required: bool = True) -> bool:
    if not isinstance(value, list) or len(value) > MAX_CONDITION_ITEMS:
        return False
    if required and not value:
        return False
    return all(_valid_short_text(item) for item in value) and len(set(value)) == len(value)


def _contains_named_imitation(value: Any, forbidden_identity_terms: Iterable[str]) -> bool:
    texts: list[str] = []
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
        elif isinstance(current, str):
            texts.append(current)
    terms = (
        (forbidden_identity_terms,)
        if isinstance(forbidden_identity_terms, str)
        else forbidden_identity_terms
    )
    folded_terms = {
        term.strip().casefold()
        for term in terms
        if isinstance(term, str) and term.strip()
    }
    for text in texts:
        if _NAMED_IMITATION_RE.search(text):
            return True
        folded = text.casefold()
        if any(term in folded for term in folded_terms):
            return True
    return False


def _validate_evidence_ref(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, Mapping):
        return ["evidence_ref_not_object"]
    if set(value) != _EVIDENCE_KEYS:
        errors.append("evidence_ref_schema_not_closed")
        return errors
    if not _valid_machine_id(value.get("work_id")):
        errors.append("evidence_work_id_invalid")
    if not _valid_machine_id(value.get("evidence_id")):
        errors.append("evidence_id_invalid")
    if value.get("role") not in {"support", "counterexample"}:
        errors.append("evidence_role_invalid")
    if not isinstance(value.get("evidence_fingerprint"), str) or not _FINGERPRINT_RE.fullmatch(
        value["evidence_fingerprint"]
    ):
        errors.append("evidence_fingerprint_invalid")
    return errors


def _validate_analyst_record(
    value: Any,
    *,
    expected_schema: str,
    require_cross_work: bool,
    forbidden_identity_terms: Iterable[str] = (),
) -> list[str]:
    errors: set[str] = set()
    if not isinstance(value, Mapping):
        return ["record_not_object"]
    forbidden = _forbidden_fields(value)
    if forbidden:
        errors.add("forbidden_identity_or_prose_field")
    if set(value) != _ANALYST_KEYS:
        errors.add("record_schema_not_closed")
        return sorted(errors)
    if value.get("schema") != expected_schema:
        errors.add("record_schema_invalid")
    if not _valid_machine_id(value.get("record_id")):
        errors.add("record_id_invalid")
    if value.get("axis") not in STYLE_AXES:
        errors.add("axis_invalid")
    for key in ("operation", "effect", "failure_boundary"):
        if not _valid_short_text(value.get(key)):
            errors.add(f"{key}_invalid")
    for key in ("applies_when", "avoid_when", "supports", "counterexamples"):
        if not _valid_text_list(value.get(key)):
            errors.add(f"{key}_invalid")
    if value.get("content_zone") not in CONTENT_ZONES:
        errors.add("content_zone_invalid")
    confidence = value.get("confidence_ppm")
    if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 1_000_000:
        errors.add("confidence_ppm_invalid")
    evidence = value.get("evidence_refs")
    if not isinstance(evidence, list) or not evidence or len(evidence) > MAX_EVIDENCE_REFS:
        errors.add("evidence_refs_invalid")
        evidence = []
    else:
        identities: set[tuple[Any, Any]] = set()
        for item in evidence:
            errors.update(_validate_evidence_ref(item))
            if isinstance(item, Mapping):
                identity = (item.get("work_id"), item.get("evidence_id"))
                if identity in identities:
                    errors.add("evidence_ref_duplicate")
                identities.add(identity)
        support_work_ids = {
            item.get("work_id")
            for item in evidence
            if isinstance(item, Mapping) and item.get("role") == "support"
        }
        counterexample_refs = [
            item for item in evidence
            if isinstance(item, Mapping) and item.get("role") == "counterexample"
        ]
        if not support_work_ids:
            errors.add("support_evidence_required")
        if not counterexample_refs:
            errors.add("counterexample_evidence_required")
        if require_cross_work and len(support_work_ids) < MIN_CROSS_WORK_SUPPORT:
            errors.add("cross_work_support_insufficient")
    supports = value.get("supports")
    counterexamples = value.get("counterexamples")
    if isinstance(supports, list) and isinstance(counterexamples, list):
        if set(supports) & set(counterexamples):
            errors.add("support_counterexample_overlap")
    if value.get("record_fingerprint") != fingerprint(_without(value, "record_fingerprint")):
        errors.add("record_fingerprint_mismatch")
    if _contains_named_imitation(value, forbidden_identity_terms):
        errors.add("named_author_or_identity_imitation_forbidden")
    try:
        if len(_canonical_bytes(value)) > MAX_SERIALIZED_CONTRACT_BYTES:
            errors.add("record_size_limit_exceeded")
    except (TypeError, ValueError):
        errors.add("record_not_canonical_json")
    return sorted(errors)


def validate_observation(
    observation: Any, *, forbidden_identity_terms: Iterable[str] = ()
) -> list[str]:
    """Validate one analyst observation; return stable error codes."""

    return _validate_analyst_record(
        observation,
        expected_schema=OBSERVATION_SCHEMA,
        require_cross_work=False,
        forbidden_identity_terms=forbidden_identity_terms,
    )


def validate_craft_candidate(
    candidate: Any, *, forbidden_identity_terms: Iterable[str] = ()
) -> list[str]:
    """Validate a cross-work claim before source-free compilation."""

    return _validate_analyst_record(
        candidate,
        expected_schema=CRAFT_CANDIDATE_SCHEMA,
        require_cross_work=True,
        forbidden_identity_terms=forbidden_identity_terms,
    )


def _require(errors: Sequence[str]) -> None:
    if errors:
        raise StyleContractError(errors[0], ",".join(errors))


def make_observation(
    *,
    record_id: str,
    axis: str,
    operation: str,
    effect: str,
    applies_when: Sequence[str],
    avoid_when: Sequence[str],
    failure_boundary: str,
    content_zone: str,
    evidence_refs: Sequence[Mapping[str, Any]],
    supports: Sequence[str],
    counterexamples: Sequence[str],
    confidence_ppm: int,
    forbidden_identity_terms: Iterable[str] = (),
) -> dict[str, Any]:
    """Build and validate one fingerprint-bound analyst observation."""

    value: dict[str, Any] = {
        "schema": OBSERVATION_SCHEMA,
        "record_id": record_id,
        "axis": axis,
        "operation": operation,
        "effect": effect,
        "applies_when": list(applies_when),
        "avoid_when": list(avoid_when),
        "failure_boundary": failure_boundary,
        "content_zone": content_zone,
        "evidence_refs": [dict(item) for item in evidence_refs],
        "supports": list(supports),
        "counterexamples": list(counterexamples),
        "confidence_ppm": confidence_ppm,
    }
    value["record_fingerprint"] = fingerprint(value)
    _require(validate_observation(value, forbidden_identity_terms=forbidden_identity_terms))
    return value


def make_craft_candidate(
    *,
    record_id: str,
    axis: str,
    operation: str,
    effect: str,
    applies_when: Sequence[str],
    avoid_when: Sequence[str],
    failure_boundary: str,
    content_zone: str,
    evidence_refs: Sequence[Mapping[str, Any]],
    supports: Sequence[str],
    counterexamples: Sequence[str],
    confidence_ppm: int,
    forbidden_identity_terms: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a multi-source, counterexample-bearing craft claim."""

    value: dict[str, Any] = {
        "schema": CRAFT_CANDIDATE_SCHEMA,
        "record_id": record_id,
        "axis": axis,
        "operation": operation,
        "effect": effect,
        "applies_when": list(applies_when),
        "avoid_when": list(avoid_when),
        "failure_boundary": failure_boundary,
        "content_zone": content_zone,
        "evidence_refs": [dict(item) for item in evidence_refs],
        "supports": list(supports),
        "counterexamples": list(counterexamples),
        "confidence_ppm": confidence_ppm,
    }
    value["record_fingerprint"] = fingerprint(value)
    _require(validate_craft_candidate(value, forbidden_identity_terms=forbidden_identity_terms))
    return value


def _source_free_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    evidence = candidate["evidence_refs"]
    support_work_ids = {
        item["work_id"] for item in evidence if item["role"] == "support"
    }
    counterexample_count = sum(item["role"] == "counterexample" for item in evidence)
    body: dict[str, Any] = {
        "axis": candidate["axis"],
        "operation": candidate["operation"],
        "effect": candidate["effect"],
        "applies_when": list(candidate["applies_when"]),
        "avoid_when": list(candidate["avoid_when"]),
        "failure_boundary": candidate["failure_boundary"],
        "content_zone": candidate["content_zone"],
        "confidence_ppm": candidate["confidence_ppm"],
        "supporting_work_count": len(support_work_ids),
        "counterexample_count": counterexample_count,
    }
    body["craft_id"] = "CRAFT-" + fingerprint(body).removeprefix("sha256:")[:24]
    return body


def _expected_craft_id(value: Mapping[str, Any]) -> str:
    body = {key: child for key, child in value.items() if key != "craft_id"}
    return "CRAFT-" + fingerprint(body).removeprefix("sha256:")[:24]


def _default_leakage_policy() -> dict[str, Any]:
    return {
        "exact_ngram_size": DEFAULT_EXACT_NGRAM_SIZE,
        "normalized_ngram_size": DEFAULT_NORMALIZED_NGRAM_SIZE,
        "shingle_size": DEFAULT_SHINGLE_SIZE,
        "fuzzy_jaccard_threshold_ppm": DEFAULT_FUZZY_JACCARD_THRESHOLD_PPM,
        "minhash_signature_size": DEFAULT_MINHASH_SIGNATURE_SIZE,
        "semantic_check": "required_external",
    }


def _validate_source_free_craft(value: Any, *, writer: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, Mapping):
        return ["craft_not_object"]
    expected_keys = _WRITER_CRAFT_KEYS if writer else _SOURCE_FREE_CRAFT_KEYS
    if set(value) != expected_keys:
        return ["craft_schema_not_closed"]
    if _forbidden_fields(value):
        errors.append("forbidden_identity_or_prose_field")
    if not writer and (
        not isinstance(value.get("craft_id"), str)
        or re.fullmatch(r"CRAFT-[0-9a-f]{24}", value["craft_id"]) is None
    ):
        errors.append("craft_id_invalid")
    elif not writer and value.get("craft_id") != _expected_craft_id(value):
        errors.append("craft_id_binding_mismatch")
    if value.get("axis") not in STYLE_AXES:
        errors.append("axis_invalid")
    for key in ("operation", "effect", "failure_boundary"):
        if not _valid_short_text(value.get(key)):
            errors.append(f"{key}_invalid")
    for key in ("applies_when", "avoid_when"):
        if not _valid_text_list(value.get(key)):
            errors.append(f"{key}_invalid")
    if value.get("content_zone") not in CONTENT_ZONES:
        errors.append("content_zone_invalid")
    confidence = value.get("confidence_ppm")
    if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 1_000_000:
        errors.append("confidence_ppm_invalid")
    if not writer:
        support_count = value.get("supporting_work_count")
        if (
            isinstance(support_count, bool)
            or not isinstance(support_count, int)
            or support_count < MIN_CROSS_WORK_SUPPORT
        ):
            errors.append("supporting_work_count_invalid")
        counterexample_count = value.get("counterexample_count")
        if (
            isinstance(counterexample_count, bool)
            or not isinstance(counterexample_count, int)
            or counterexample_count < 1
        ):
            errors.append("counterexample_count_invalid")
    if _contains_named_imitation(value, ()):
        errors.append("named_author_or_identity_imitation_forbidden")
    return sorted(set(errors))


def compile_source_free_craft_candidate(
    candidate: Mapping[str, Any], *, forbidden_identity_terms: Iterable[str] = ()
) -> dict[str, Any]:
    """Validate and erase all evidence identity from one craft candidate."""

    _require(validate_craft_candidate(candidate, forbidden_identity_terms=forbidden_identity_terms))
    compiled = _source_free_candidate(candidate)
    _require(_validate_source_free_craft(compiled))
    return compiled


def compile_style_contract(
    contract_id: str,
    candidates: Sequence[Mapping[str, Any]],
    *,
    content_zone: str,
    forbidden_identity_terms: Iterable[str] = (),
) -> dict[str, Any]:
    """Compile evidenceful claims into one bounded, source-free contract."""

    if not _valid_machine_id(contract_id):
        raise StyleContractError("contract_id_invalid")
    if content_zone not in CONTENT_ZONES:
        raise StyleContractError("content_zone_invalid")
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise StyleContractError("candidates_invalid")
    if not candidates or len(candidates) > MAX_CANDIDATES:
        raise StyleContractError("candidate_count_invalid")
    identity_terms = (
        (forbidden_identity_terms,)
        if isinstance(forbidden_identity_terms, str)
        else tuple(forbidden_identity_terms)
    )
    compiled: list[dict[str, Any]] = []
    craft_ids: set[str] = set()
    for candidate in candidates:
        craft = compile_source_free_craft_candidate(
            candidate, forbidden_identity_terms=identity_terms
        )
        if craft["content_zone"] != content_zone:
            raise StyleContractError("mixed_content_zone_forbidden")
        if craft["craft_id"] in craft_ids:
            raise StyleContractError("duplicate_craft_candidate")
        craft_ids.add(craft["craft_id"])
        compiled.append(craft)
    compiled.sort(key=lambda item: (STYLE_AXES.index(item["axis"]), item["craft_id"]))
    value: dict[str, Any] = {
        "schema": STYLE_CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "content_zone": content_zone,
        "attribution_mode": "source_free",
        "craft_candidates": compiled,
        "leakage_policy": _default_leakage_policy(),
    }
    if len(_canonical_bytes(value)) > MAX_SERIALIZED_CONTRACT_BYTES:
        raise StyleContractError("contract_size_limit_exceeded")
    value["contract_fingerprint"] = fingerprint(value)
    _require(validate_style_contract(value, forbidden_identity_terms=identity_terms))
    return value


def validate_style_contract(
    contract: Any, *, forbidden_identity_terms: Iterable[str] = ()
) -> list[str]:
    """Validate the complete source-free StyleContract schema."""

    errors: set[str] = set()
    if not isinstance(contract, Mapping):
        return ["contract_not_object"]
    if _forbidden_fields(contract):
        errors.add("forbidden_identity_or_prose_field")
    if set(contract) != _STYLE_CONTRACT_KEYS:
        errors.add("contract_schema_not_closed")
        return sorted(errors)
    if contract.get("schema") != STYLE_CONTRACT_SCHEMA:
        errors.add("contract_schema_invalid")
    if not _valid_machine_id(contract.get("contract_id")):
        errors.add("contract_id_invalid")
    if contract.get("content_zone") not in CONTENT_ZONES:
        errors.add("content_zone_invalid")
    if contract.get("attribution_mode") != "source_free":
        errors.add("attribution_mode_invalid")
    candidates = contract.get("craft_candidates")
    if not isinstance(candidates, list) or not candidates or len(candidates) > MAX_CANDIDATES:
        errors.add("candidate_count_invalid")
        candidates = []
    seen: set[str] = set()
    for candidate in candidates:
        errors.update(_validate_source_free_craft(candidate))
        if isinstance(candidate, Mapping):
            if candidate.get("content_zone") != contract.get("content_zone"):
                errors.add("mixed_content_zone_forbidden")
            craft_id = candidate.get("craft_id")
            if craft_id in seen:
                errors.add("duplicate_craft_candidate")
            if isinstance(craft_id, str):
                seen.add(craft_id)
    policy = contract.get("leakage_policy")
    if not isinstance(policy, Mapping) or set(policy) != _LEAKAGE_POLICY_KEYS:
        errors.add("leakage_policy_schema_not_closed")
    else:
        for key in ("exact_ngram_size", "normalized_ngram_size", "shingle_size"):
            value = policy.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not 2 <= value <= 512:
                errors.add(f"{key}_invalid")
        threshold = policy.get("fuzzy_jaccard_threshold_ppm")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 1_000_000:
            errors.add("fuzzy_jaccard_threshold_ppm_invalid")
        signature_size = policy.get("minhash_signature_size")
        if isinstance(signature_size, bool) or not isinstance(signature_size, int) or not 8 <= signature_size <= 256:
            errors.add("minhash_signature_size_invalid")
        if policy.get("semantic_check") != "required_external":
            errors.add("semantic_check_must_be_external")
    if contract.get("contract_fingerprint") != fingerprint(_without(contract, "contract_fingerprint")):
        errors.add("contract_fingerprint_mismatch")
    if _contains_named_imitation(contract, forbidden_identity_terms):
        errors.add("named_author_or_identity_imitation_forbidden")
    try:
        if len(_canonical_bytes(contract)) > MAX_SERIALIZED_CONTRACT_BYTES:
            errors.add("contract_size_limit_exceeded")
    except (TypeError, ValueError):
        errors.add("contract_not_canonical_json")
    return sorted(errors)


def compile_writer_projection(
    contract: Mapping[str, Any], *, forbidden_identity_terms: Iterable[str] = ()
) -> dict[str, Any]:
    """Compile the minimal writer-visible projection from a valid contract."""

    identity_terms = (
        (forbidden_identity_terms,)
        if isinstance(forbidden_identity_terms, str)
        else tuple(forbidden_identity_terms)
    )
    _require(validate_style_contract(contract, forbidden_identity_terms=identity_terms))
    craft_candidates = [
        {key: candidate[key] for key in _WRITER_CRAFT_KEYS}
        for candidate in contract["craft_candidates"]
    ]
    value: dict[str, Any] = {
        "schema": WRITER_PROJECTION_SCHEMA,
        "style_contract_fingerprint": contract["contract_fingerprint"],
        "content_zone": contract["content_zone"],
        "attribution_mode": "source_free",
        "craft_candidates": craft_candidates,
        "semantic_leakage_check": "required_external",
    }
    value["projection_fingerprint"] = fingerprint(value)
    _require(validate_writer_projection(value, forbidden_identity_terms=identity_terms))
    return value


compile_writer_safe_projection = compile_writer_projection


def validate_writer_projection(
    projection: Any, *, forbidden_identity_terms: Iterable[str] = ()
) -> list[str]:
    errors: set[str] = set()
    if not isinstance(projection, Mapping):
        return ["projection_not_object"]
    if _forbidden_fields(projection):
        errors.add("forbidden_identity_or_prose_field")
    if set(projection) != _WRITER_PROJECTION_KEYS:
        errors.add("projection_schema_not_closed")
        return sorted(errors)
    if projection.get("schema") != WRITER_PROJECTION_SCHEMA:
        errors.add("projection_schema_invalid")
    if not isinstance(projection.get("style_contract_fingerprint"), str) or not _FINGERPRINT_RE.fullmatch(
        projection["style_contract_fingerprint"]
    ):
        errors.add("style_contract_fingerprint_invalid")
    if projection.get("content_zone") not in CONTENT_ZONES:
        errors.add("content_zone_invalid")
    if projection.get("attribution_mode") != "source_free":
        errors.add("attribution_mode_invalid")
    candidates = projection.get("craft_candidates")
    if not isinstance(candidates, list) or not candidates or len(candidates) > MAX_CANDIDATES:
        errors.add("candidate_count_invalid")
        candidates = []
    for candidate in candidates:
        errors.update(_validate_source_free_craft(candidate, writer=True))
        if isinstance(candidate, Mapping) and candidate.get("content_zone") != projection.get("content_zone"):
            errors.add("mixed_content_zone_forbidden")
    if projection.get("semantic_leakage_check") != "required_external":
        errors.add("semantic_check_must_be_external")
    if projection.get("projection_fingerprint") != fingerprint(
        _without(projection, "projection_fingerprint")
    ):
        errors.add("projection_fingerprint_mismatch")
    if _contains_named_imitation(projection, forbidden_identity_terms):
        errors.add("named_author_or_identity_imitation_forbidden")
    try:
        if len(_canonical_bytes(projection)) > MAX_SERIALIZED_CONTRACT_BYTES:
            errors.add("projection_size_limit_exceeded")
    except (TypeError, ValueError):
        errors.add("projection_not_canonical_json")
    return sorted(errors)


def _exact_character_stream(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")


def _normalized_character_stream(value: str) -> str:
    return "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", value)
        if character.isalnum() or "\u3400" <= character <= "\u9fff"
    )


def _ngrams(value: str, size: int) -> set[str]:
    if len(value) < size:
        return set()
    return {value[index:index + size] for index in range(len(value) - size + 1)}


def _tokens(value: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(unicodedata.normalize("NFKC", value))]


def _shingles(value: str, size: int) -> set[str]:
    tokens = _tokens(value)
    if len(tokens) < size:
        return set()
    return {"\x1f".join(tokens[index:index + size]) for index in range(len(tokens) - size + 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _minhash_signature(shingles: set[str], size: int) -> tuple[int, ...]:
    """Build a deterministic one-permutation MinHash-style sketch.

    Independent-permutation MinHash requires ``size * len(shingles)`` hashes.
    The bucketed form keeps the safety gate bounded while retaining the useful
    equality property: an identical shingle always lands in the same bucket
    with the same rank.
    """

    if not shingles:
        return ()
    empty = (1 << 64) - 1
    signature = [empty] * size
    for shingle in shingles:
        digest = hashlib.sha256(shingle.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % size
        rank = int.from_bytes(digest[8:16], "big")
        if rank < signature[bucket]:
            signature[bucket] = rank
    return tuple(signature)


def _signature_similarity(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    empty = (1 << 64) - 1
    comparable = [
        (a, b)
        for a, b in zip(left, right, strict=True)
        if a != empty or b != empty
    ]
    if not comparable:
        return 0.0
    return sum(a == b and a != empty for a, b in comparable) / len(comparable)


def check_local_leakage(
    candidate_text: str,
    reference_texts: Mapping[str, str],
    *,
    exact_ngram_size: int = DEFAULT_EXACT_NGRAM_SIZE,
    normalized_ngram_size: int = DEFAULT_NORMALIZED_NGRAM_SIZE,
    shingle_size: int = DEFAULT_SHINGLE_SIZE,
    fuzzy_jaccard_threshold_ppm: int = DEFAULT_FUZZY_JACCARD_THRESHOLD_PPM,
    minhash_signature_size: int = DEFAULT_MINHASH_SIGNATURE_SIZE,
) -> dict[str, Any]:
    """Run bounded local overlap checks without returning matched source text.

    Exact and normalized character n-grams catch verbatim and formatting/case
    variants.  Token shingles provide deterministic fuzzy Jaccard and MinHash
    estimates.  A clean local result is *not* release approval: semantic
    similarity remains ``required_external`` in every report.
    """

    if not isinstance(candidate_text, str) or not candidate_text or len(candidate_text) > MAX_LEAKAGE_TEXT_CHARS:
        raise StyleContractError("candidate_text_invalid")
    if not isinstance(reference_texts, Mapping) or not reference_texts or len(reference_texts) > MAX_LEAKAGE_REFERENCES:
        raise StyleContractError("reference_texts_invalid")
    if any(not _valid_machine_id(reference_id) for reference_id in reference_texts):
        raise StyleContractError("reference_id_invalid")
    total_characters = len(candidate_text) + sum(
        len(value) for value in reference_texts.values() if isinstance(value, str)
    )
    if total_characters > MAX_LEAKAGE_TOTAL_CHARS:
        raise StyleContractError("leakage_total_size_limit_exceeded")
    for value, code, lower, upper in (
        (exact_ngram_size, "exact_ngram_size_invalid", 2, 512),
        (normalized_ngram_size, "normalized_ngram_size_invalid", 2, 512),
        (shingle_size, "shingle_size_invalid", 2, 64),
        (minhash_signature_size, "minhash_signature_size_invalid", 8, 256),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
            raise StyleContractError(code)
    if (
        isinstance(fuzzy_jaccard_threshold_ppm, bool)
        or not isinstance(fuzzy_jaccard_threshold_ppm, int)
        or not 0 <= fuzzy_jaccard_threshold_ppm <= 1_000_000
    ):
        raise StyleContractError("fuzzy_jaccard_threshold_ppm_invalid")

    candidate_exact = _ngrams(_exact_character_stream(candidate_text), exact_ngram_size)
    candidate_normalized = _ngrams(
        _normalized_character_stream(candidate_text), normalized_ngram_size
    )
    candidate_shingles = _shingles(candidate_text, shingle_size)
    candidate_signature = _minhash_signature(candidate_shingles, minhash_signature_size)
    findings: list[dict[str, Any]] = []
    blocked = False
    for reference_id in sorted(reference_texts):
        reference = reference_texts[reference_id]
        if not isinstance(reference, str) or not reference or len(reference) > MAX_LEAKAGE_TEXT_CHARS:
            raise StyleContractError("reference_text_invalid")
        reference_exact = _ngrams(_exact_character_stream(reference), exact_ngram_size)
        reference_normalized = _ngrams(
            _normalized_character_stream(reference), normalized_ngram_size
        )
        reference_shingles = _shingles(reference, shingle_size)
        exact_hits = len(candidate_exact & reference_exact)
        normalized_hits = len(candidate_normalized & reference_normalized)
        jaccard = _jaccard(candidate_shingles, reference_shingles)
        reference_signature = _minhash_signature(reference_shingles, minhash_signature_size)
        minhash = _signature_similarity(candidate_signature, reference_signature)
        fuzzy_ppm = round(jaccard * 1_000_000)
        minhash_ppm = round(minhash * 1_000_000)
        reference_blocked = (
            exact_hits > 0
            or normalized_hits > 0
            or fuzzy_ppm >= fuzzy_jaccard_threshold_ppm
            or minhash_ppm >= fuzzy_jaccard_threshold_ppm
        )
        blocked = blocked or reference_blocked
        findings.append(
            {
                "reference_id": reference_id,
                "exact_ngram_hits": exact_hits,
                "normalized_ngram_hits": normalized_hits,
                "shingle_jaccard_ppm": fuzzy_ppm,
                "minhash_jaccard_estimate_ppm": minhash_ppm,
                "blocked": reference_blocked,
            }
        )
    base: dict[str, Any] = {
        "schema": LEAKAGE_REPORT_SCHEMA,
        "local_status": "blocked" if blocked else "pass",
        "release_ready": False,
        "candidate_fingerprint": "sha256:" + hashlib.sha256(
            candidate_text.encode("utf-8")
        ).hexdigest(),
        "policy": {
            "exact_ngram_size": exact_ngram_size,
            "normalized_ngram_size": normalized_ngram_size,
            "shingle_size": shingle_size,
            "fuzzy_jaccard_threshold_ppm": fuzzy_jaccard_threshold_ppm,
            "minhash_signature_size": minhash_signature_size,
        },
        "findings": findings,
        "semantic_check": {
            "status": "required_external",
            "performed": False,
            "reason": "semantic similarity requires an independent model or human review",
        },
    }
    base["report_fingerprint"] = fingerprint(base)
    _require(validate_leakage_report(base))
    return base


local_leakage_check = check_local_leakage


def validate_leakage_report(report: Any) -> list[str]:
    """Validate a local report without treating it as semantic approval."""

    errors: set[str] = set()
    if not isinstance(report, Mapping):
        return ["leakage_report_not_object"]
    if set(report) != _LEAKAGE_REPORT_KEYS:
        return ["leakage_report_schema_not_closed"]
    if report.get("schema") != LEAKAGE_REPORT_SCHEMA:
        errors.add("leakage_report_schema_invalid")
    if report.get("local_status") not in {"pass", "blocked"}:
        errors.add("local_status_invalid")
    if report.get("release_ready") is not False:
        errors.add("local_report_cannot_grant_release")
    candidate_fingerprint = report.get("candidate_fingerprint")
    if not isinstance(candidate_fingerprint, str) or _FINGERPRINT_RE.fullmatch(candidate_fingerprint) is None:
        errors.add("candidate_fingerprint_invalid")
    policy = report.get("policy")
    if not isinstance(policy, Mapping) or set(policy) != _LEAKAGE_REPORT_POLICY_KEYS:
        errors.add("leakage_report_policy_schema_not_closed")
    else:
        for key, lower, upper in (
            ("exact_ngram_size", 2, 512),
            ("normalized_ngram_size", 2, 512),
            ("shingle_size", 2, 64),
            ("minhash_signature_size", 8, 256),
        ):
            value = policy.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
                errors.add(f"{key}_invalid")
        threshold = policy.get("fuzzy_jaccard_threshold_ppm")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 1_000_000:
            errors.add("fuzzy_jaccard_threshold_ppm_invalid")
    findings = report.get("findings")
    any_blocked = False
    if not isinstance(findings, list) or not findings or len(findings) > MAX_LEAKAGE_REFERENCES:
        errors.add("leakage_findings_invalid")
        findings = []
    for finding in findings:
        if not isinstance(finding, Mapping) or set(finding) != _LEAKAGE_FINDING_KEYS:
            errors.add("leakage_finding_schema_not_closed")
            continue
        if not _valid_machine_id(finding.get("reference_id")):
            errors.add("reference_id_invalid")
        for key in ("exact_ngram_hits", "normalized_ngram_hits"):
            value = finding.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.add(f"{key}_invalid")
        for key in ("shingle_jaccard_ppm", "minhash_jaccard_estimate_ppm"):
            value = finding.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1_000_000:
                errors.add(f"{key}_invalid")
        if not isinstance(finding.get("blocked"), bool):
            errors.add("finding_blocked_invalid")
        any_blocked = any_blocked or finding.get("blocked") is True
    expected_status = "blocked" if any_blocked else "pass"
    if findings and report.get("local_status") != expected_status:
        errors.add("local_status_finding_mismatch")
    semantic = report.get("semantic_check")
    if not isinstance(semantic, Mapping) or set(semantic) != _SEMANTIC_CHECK_KEYS:
        errors.add("semantic_check_schema_not_closed")
    elif (
        semantic.get("status") != "required_external"
        or semantic.get("performed") is not False
        or not _valid_short_text(semantic.get("reason"))
    ):
        errors.add("semantic_check_must_be_external")
    if report.get("report_fingerprint") != fingerprint(_without(report, "report_fingerprint")):
        errors.add("report_fingerprint_mismatch")
    return sorted(errors)


__all__ = [
    "CRAFT_AXES",
    "CONTENT_ZONES",
    "CRAFT_CANDIDATE_SCHEMA",
    "LEAKAGE_REPORT_SCHEMA",
    "MAX_CANDIDATES",
    "MAX_SERIALIZED_CONTRACT_BYTES",
    "MIN_CROSS_WORK_SUPPORT",
    "OBSERVATION_SCHEMA",
    "STYLE_AXES",
    "STYLE_CONTRACT_SCHEMA",
    "WRITER_PROJECTION_SCHEMA",
    "StyleContractError",
    "check_local_leakage",
    "compile_source_free_craft_candidate",
    "compile_style_contract",
    "compile_writer_projection",
    "compile_writer_safe_projection",
    "fingerprint",
    "local_leakage_check",
    "make_craft_candidate",
    "make_observation",
    "validate_craft_candidate",
    "validate_leakage_report",
    "validate_observation",
    "validate_style_contract",
    "validate_writer_projection",
]
