"""Focused tests for the Host-injected Style Publisher candidate loader."""
from __future__ import annotations

import copy
import unittest

from corpus.style_publication import fingerprint, identity_policy_fingerprint
from corpus.style_publication_adapter import (
    PROVENANCE_REGISTERED_CONTRACT,
    TRUSTED_PROVENANCE_RECEIPT_SCHEMA,
    StylePublicationCandidateLoaderError,
    TrustedStylePublicationCandidateLoader,
)
from corpus.style_study_runner import StyleStudyRunner, StyleStudyRunnerError
from tests.test_quillframe_style_publication import bundle, persisted


class _TrustedRunner(StyleStudyRunner):
    def __init__(self, material: dict) -> None:
        self.material = material
        self.calls: list[str] = []
        self.failure: Exception | None = None

    def trusted_publication_material_for_receipt(self, receipt_fingerprint: str) -> dict:
        self.calls.append(receipt_fingerprint)
        if self.failure is not None:
            raise self.failure
        expected = self.material["completion_receipt"]["receipt_fingerprint"]
        if receipt_fingerprint != expected:
            raise StyleStudyRunnerError("style_completion_receipt_lookup_invalid")
        return copy.deepcopy(self.material)


def _fixture() -> tuple[dict, str]:
    candidate = bundle()
    accepted = persisted(candidate)
    receipt_fingerprint = accepted["completion_receipt"]["receipt_fingerprint"]
    material = {
        "schema": "quillframe_corpus_trusted_style_publication_material_v1",
        "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
        "style_run_id": accepted["completion_receipt"]["style_run_id"],
        "study_id": accepted["completion_receipt"]["study_id"],
        "candidate_bundle": accepted["candidate_bundle"],
        "completion_receipt": accepted["completion_receipt"],
        "forbidden_identity_terms": accepted["forbidden_identity_terms"],
        "source_dependency_fingerprints": [
            fingerprint({"source_dependency": "one"}),
            fingerprint({"source_dependency": "two"}),
        ],
        "source_dependencies_current": True,
        "authority": False,
    }
    return material, receipt_fingerprint


def _provenance_receipt(material: dict) -> dict:
    candidate = material["candidate_bundle"]
    completion = material["completion_receipt"]
    terms = material["forbidden_identity_terms"]
    dependency_set_fingerprint = fingerprint(
        {
            "schema": "quillframe_style_source_dependency_set_v1",
            "dependency_fingerprints": material["source_dependency_fingerprints"],
        }
    )
    receipt = {
        "schema": TRUSTED_PROVENANCE_RECEIPT_SCHEMA,
        "registered_contract": PROVENANCE_REGISTERED_CONTRACT,
        "status": "pass",
        "independent": True,
        "performed": True,
        "authority_scope": "evidence_only",
        "legal_safety_claim": False,
        "completion_receipt_fingerprint": completion["receipt_fingerprint"],
        "candidate_bundle_fingerprint": candidate["bundle_fingerprint"],
        "style_artifact_fingerprint": candidate["candidate_artifact_fingerprint"],
        "craft_artifact_fingerprint": candidate["craft_pack_fingerprint"],
        "identity_policy_fingerprint": identity_policy_fingerprint(terms),
        "source_dependency_set_fingerprint": dependency_set_fingerprint,
        "review_result_fingerprint": fingerprint({"registered_review": "persisted"}),
    }
    receipt["receipt_fingerprint"] = fingerprint(receipt)
    return receipt


class TrustedStylePublicationCandidateLoaderTests(unittest.TestCase):
    def test_loader_builds_exact_publisher_candidate_from_receipt_only(self) -> None:
        material, receipt_fingerprint = _fixture()
        runner = _TrustedRunner(material)
        provenance = _provenance_receipt(material)
        resolver_calls: list[str] = []

        def resolver(value: str) -> dict:
            resolver_calls.append(value)
            return copy.deepcopy(provenance)

        loader = TrustedStylePublicationCandidateLoader(
            runner=runner, provenance_receipt_resolver=resolver
        )
        loaded = loader(receipt_fingerprint)

        self.assertEqual(runner.calls, [receipt_fingerprint])
        self.assertEqual(resolver_calls, [receipt_fingerprint])
        self.assertEqual(
            set(loaded),
            {
                "schema",
                "candidate_bundle",
                "completion_receipt",
                "forbidden_identity_terms",
                "identity_policy_complete",
                "identity_policy_fingerprint",
                "provenance_receipt_fingerprint",
            },
        )
        self.assertTrue(loaded["identity_policy_complete"])
        self.assertEqual(
            loaded["provenance_receipt_fingerprint"], provenance["receipt_fingerprint"]
        )
        self.assertEqual(
            loaded["completion_receipt"]["semantic_config_fingerprint"],
            material["completion_receipt"]["semantic_config_fingerprint"],
        )
        self.assertEqual(
            loaded["completion_receipt"]["semantic_evidence_fingerprint"],
            material["completion_receipt"]["semantic_evidence_fingerprint"],
        )
        with self.assertRaises(TypeError):
            loader(  # type: ignore[call-arg]
                receipt_fingerprint,
                provenance_receipt_fingerprint=provenance["receipt_fingerprint"],
            )

    def test_forged_or_unbound_provenance_receipt_fails_closed(self) -> None:
        material, receipt_fingerprint = _fixture()
        runner = _TrustedRunner(material)
        provenance = _provenance_receipt(material)
        provenance["candidate_bundle_fingerprint"] = "sha256:" + "0" * 64
        provenance["receipt_fingerprint"] = fingerprint(
            {key: value for key, value in provenance.items() if key != "receipt_fingerprint"}
        )
        loader = TrustedStylePublicationCandidateLoader(
            runner=runner, provenance_receipt_resolver=lambda _: provenance
        )
        with self.assertRaises(StylePublicationCandidateLoaderError) as raised:
            loader(receipt_fingerprint)
        self.assertEqual(raised.exception.code, "style_provenance_receipt_invalid")

        closed_violation = _provenance_receipt(material)
        closed_violation["caller_claim"] = "pass"
        loader = TrustedStylePublicationCandidateLoader(
            runner=runner, provenance_receipt_resolver=lambda _: closed_violation
        )
        with self.assertRaises(StylePublicationCandidateLoaderError):
            loader(receipt_fingerprint)

    def test_source_drift_blocks_before_provenance_resolver_is_consulted(self) -> None:
        material, receipt_fingerprint = _fixture()
        runner = _TrustedRunner(material)
        runner.failure = StyleStudyRunnerError("style_publication_source_dependency_invalid")
        resolver_calls: list[str] = []
        loader = TrustedStylePublicationCandidateLoader(
            runner=runner,
            provenance_receipt_resolver=lambda value: resolver_calls.append(value) or {},
        )
        with self.assertRaises(StylePublicationCandidateLoaderError) as raised:
            loader(receipt_fingerprint)
        self.assertEqual(
            raised.exception.code, "trusted_style_publication_material_unavailable"
        )
        self.assertEqual(resolver_calls, [])


if __name__ == "__main__":
    unittest.main()
