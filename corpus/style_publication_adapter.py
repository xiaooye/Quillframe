"""Host-injected loader from trusted StyleStudyRunner receipts to Publisher input.

This module does not release an atlas and owns no signing key.  It converts an
exact, reverified local completion receipt plus a Host-owned persisted
provenance review into the closed candidate record accepted by
``StyleAtlasPublisher``.  Callers cannot supply a candidate bundle, identity
policy, study identifier, or provenance fingerprint to the lookup operation.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from corpus.style_publication import (
    PERSISTED_CANDIDATE_SCHEMA,
    canonicalize_identity_terms,
    fingerprint,
    identity_policy_fingerprint,
    make_gate_attestation_payload,
)
from corpus.style_study_runner import StyleStudyRunner


TRUSTED_PROVENANCE_RECEIPT_SCHEMA = "quillframe_trusted_style_provenance_receipt_v1"
PROVENANCE_REGISTERED_CONTRACT = "corpus.provenance.public_abstraction"
_FINGERPRINT_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PROVENANCE_RECEIPT_KEYS = {
    "schema",
    "registered_contract",
    "status",
    "independent",
    "performed",
    "authority_scope",
    "legal_safety_claim",
    "completion_receipt_fingerprint",
    "candidate_bundle_fingerprint",
    "style_artifact_fingerprint",
    "craft_artifact_fingerprint",
    "identity_policy_fingerprint",
    "source_dependency_set_fingerprint",
    "review_result_fingerprint",
    "receipt_fingerprint",
}


class StylePublicationCandidateLoaderError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _valid_fingerprint(value: Any) -> bool:
    return isinstance(value, str) and _FINGERPRINT_RE.fullmatch(value) is not None


def _dependency_set_fingerprint(values: Any) -> str:
    if (
        not isinstance(values, list)
        or not values
        or any(not _valid_fingerprint(value) for value in values)
        or len(values) != len(set(values))
    ):
        raise StylePublicationCandidateLoaderError("style_source_dependency_receipts_invalid")
    return fingerprint(
        {
            "schema": "quillframe_style_source_dependency_set_v1",
            "dependency_fingerprints": values,
        }
    )


class TrustedStylePublicationCandidateLoader:
    """Callable candidate loader suitable for ``StyleAtlasPublisher``.

    ``provenance_receipt_resolver`` is a production Host dependency that must
    look up an already-persisted independent review by completion receipt
    fingerprint.  It is deliberately constructor-injected and never accepted
    from an operation request.
    """

    def __init__(
        self,
        *,
        runner: StyleStudyRunner,
        provenance_receipt_resolver: Callable[[str], Mapping[str, Any]],
    ) -> None:
        if not isinstance(runner, StyleStudyRunner):
            raise StylePublicationCandidateLoaderError("style_runner_invalid")
        if not callable(provenance_receipt_resolver):
            raise StylePublicationCandidateLoaderError("style_provenance_resolver_invalid")
        self._runner = runner
        self._provenance_receipt_resolver = provenance_receipt_resolver

    def __call__(self, completion_receipt_fingerprint: str) -> dict[str, Any]:
        if not _valid_fingerprint(completion_receipt_fingerprint):
            raise StylePublicationCandidateLoaderError(
                "style_completion_receipt_fingerprint_invalid"
            )
        try:
            material = self._runner.trusted_publication_material_for_receipt(
                completion_receipt_fingerprint
            )
        except Exception as exc:
            raise StylePublicationCandidateLoaderError(
                "trusted_style_publication_material_unavailable"
            ) from exc
        if (
            not isinstance(material, Mapping)
            or material.get("schema")
            != "quillframe_corpus_trusted_style_publication_material_v1"
            or material.get("source_dependencies_current") is not True
        ):
            raise StylePublicationCandidateLoaderError(
                "trusted_style_publication_material_invalid"
            )
        candidate = material.get("candidate_bundle")
        completion_receipt = material.get("completion_receipt")
        if not isinstance(candidate, Mapping) or not isinstance(completion_receipt, Mapping):
            raise StylePublicationCandidateLoaderError(
                "trusted_style_publication_material_invalid"
            )

        identity_terms = canonicalize_identity_terms(
            material.get("forbidden_identity_terms", [])
        )
        if not identity_terms:
            raise StylePublicationCandidateLoaderError("style_identity_policy_incomplete")
        identity_fingerprint = identity_policy_fingerprint(identity_terms)
        dependency_fingerprint = _dependency_set_fingerprint(
            material.get("source_dependency_fingerprints")
        )

        try:
            provenance = self._provenance_receipt_resolver(
                completion_receipt_fingerprint
            )
        except Exception as exc:
            raise StylePublicationCandidateLoaderError(
                "style_provenance_receipt_unavailable"
            ) from exc
        if not isinstance(provenance, Mapping) or set(provenance) != _PROVENANCE_RECEIPT_KEYS:
            raise StylePublicationCandidateLoaderError("style_provenance_receipt_invalid")
        provenance_base = {
            key: value for key, value in provenance.items() if key != "receipt_fingerprint"
        }
        expected_bindings = {
            "schema": TRUSTED_PROVENANCE_RECEIPT_SCHEMA,
            "registered_contract": PROVENANCE_REGISTERED_CONTRACT,
            "status": "pass",
            "independent": True,
            "performed": True,
            "authority_scope": "evidence_only",
            "legal_safety_claim": False,
            "completion_receipt_fingerprint": completion_receipt_fingerprint,
            "candidate_bundle_fingerprint": candidate.get("bundle_fingerprint"),
            "style_artifact_fingerprint": candidate.get("candidate_artifact_fingerprint"),
            "craft_artifact_fingerprint": candidate.get("craft_pack_fingerprint"),
            "identity_policy_fingerprint": identity_fingerprint,
            "source_dependency_set_fingerprint": dependency_fingerprint,
        }
        if (
            any(provenance.get(key) != value for key, value in expected_bindings.items())
            or not _valid_fingerprint(provenance.get("review_result_fingerprint"))
            or provenance.get("receipt_fingerprint") != fingerprint(provenance_base)
        ):
            raise StylePublicationCandidateLoaderError("style_provenance_receipt_invalid")

        persisted = {
            "schema": PERSISTED_CANDIDATE_SCHEMA,
            "candidate_bundle": dict(candidate),
            "completion_receipt": dict(completion_receipt),
            "forbidden_identity_terms": identity_terms,
            "identity_policy_complete": True,
            "identity_policy_fingerprint": identity_fingerprint,
            "provenance_receipt_fingerprint": provenance["receipt_fingerprint"],
        }
        try:
            # This public helper exercises the Publisher's exact persisted-record
            # validator but creates no signature and grants no release authority.
            make_gate_attestation_payload(
                "provenance", "pass", persisted, provenance["receipt_fingerprint"]
            )
        except Exception as exc:
            raise StylePublicationCandidateLoaderError(
                "style_persisted_candidate_invalid"
            ) from exc
        return persisted


__all__ = [
    "PROVENANCE_REGISTERED_CONTRACT",
    "TRUSTED_PROVENANCE_RECEIPT_SCHEMA",
    "StylePublicationCandidateLoaderError",
    "TrustedStylePublicationCandidateLoader",
]
