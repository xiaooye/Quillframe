"""Deterministic tests for source-free style contracts.

All examples are short synthetic craft statements.  The suite reads no Corpus
source, fixture novel, private path, or external model.
"""
from __future__ import annotations

import copy
import json
import unittest

from corpus import style_contract as sc


REQUIRED_AXES = {
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
}


def _evidence(work: str, ordinal: int, role: str) -> dict[str, str]:
    evidence_id = f"EV-{ordinal}"
    return {
        "work_id": work,
        "evidence_id": evidence_id,
        "role": role,
        "evidence_fingerprint": sc.fingerprint(
            {"work_id": work, "evidence_id": evidence_id, "role": role}
        ),
    }


def _candidate(
    *,
    record_id: str = "CLAIM-1",
    axis: str = "syntax_rhythm",
    operation: str = "Alternate compact and extended sentences at decision beats.",
    effect: str = "Make pressure changes legible without imposing a sentence quota.",
    content_zone: str = "general",
    evidence_refs: list[dict[str, str]] | None = None,
    forbidden_identity_terms: tuple[str, ...] = (),
) -> dict:
    return sc.make_craft_candidate(
        record_id=record_id,
        axis=axis,
        operation=operation,
        effect=effect,
        applies_when=["A choice changes the scene's immediate pressure."],
        avoid_when=["A deliberate still point should remain tonally level."],
        failure_boundary="Rhythmic variation must not distort chronology or point of view.",
        content_zone=content_zone,
        evidence_refs=evidence_refs
        or [
            _evidence("WORK-A", 1, "support"),
            _evidence("WORK-B", 2, "support"),
            _evidence("WORK-C", 3, "counterexample"),
        ],
        supports=["The operation recurs on distinct synthetic scene structures."],
        counterexamples=["A held image can work better without a cadence switch."],
        confidence_ppm=820_000,
        forbidden_identity_terms=forbidden_identity_terms,
    )


def _contract(*candidates: dict, content_zone: str = "general") -> dict:
    return sc.compile_style_contract(
        "STYLE-UNIT",
        list(candidates) or [_candidate()],
        content_zone=content_zone,
    )


class StyleObservationTests(unittest.TestCase):
    def test_required_multi_axis_vocabulary_is_closed_and_includes_body_appearance(self) -> None:
        self.assertEqual(REQUIRED_AXES, set(sc.STYLE_AXES))
        self.assertEqual(sc.STYLE_AXES, sc.CRAFT_AXES)
        self.assertEqual(len(sc.STYLE_AXES), len(set(sc.STYLE_AXES)))

    def test_observation_requires_complete_craft_and_evidence_shape(self) -> None:
        observation = sc.make_observation(
            record_id="OBS-1",
            axis="psychic_distance",
            operation="Move inward through concrete perception before naming emotion.",
            effect="Keep interior access embodied and viewpoint-bound.",
            applies_when=["The viewpoint character receives consequential information."],
            avoid_when=["The scene intentionally uses remote summary."],
            failure_boundary="Do not invent sensations absent from the scene state.",
            content_zone="general",
            evidence_refs=[
                _evidence("WORK-A", 1, "support"),
                _evidence("WORK-A", 2, "counterexample"),
            ],
            supports=["A perception precedes the abstract interpretation."],
            counterexamples=["Remote transitions can summarize emotion directly."],
            confidence_ppm=780_000,
        )
        self.assertEqual([], sc.validate_observation(observation))
        self.assertRegex(observation["record_fingerprint"], r"^sha256:[0-9a-f]{64}$")

        required = {
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
        }
        for field in required:
            with self.subTest(field=field):
                malformed = copy.deepcopy(observation)
                del malformed[field]
                malformed["record_fingerprint"] = sc.fingerprint(
                    {key: value for key, value in malformed.items() if key != "record_fingerprint"}
                )
                self.assertIn("record_schema_not_closed", sc.validate_observation(malformed))

    def test_fingerprint_tampering_is_detected(self) -> None:
        candidate = _candidate()
        candidate["effect"] = "A changed claim must invalidate the old binding."
        self.assertIn("record_fingerprint_mismatch", sc.validate_craft_candidate(candidate))

    def test_closed_schema_and_nested_forbidden_fields_fail_closed(self) -> None:
        candidate = _candidate()
        candidate["evidence_refs"][0]["title"] = "PRIVATE_TITLE_SENTINEL"
        candidate["record_fingerprint"] = sc.fingerprint(
            {key: value for key, value in candidate.items() if key != "record_fingerprint"}
        )
        errors = sc.validate_craft_candidate(candidate)
        self.assertIn("forbidden_identity_or_prose_field", errors)
        self.assertIn("evidence_ref_schema_not_closed", errors)

    def test_text_and_record_size_limits_are_enforced(self) -> None:
        with self.assertRaisesRegex(sc.StyleContractError, "operation_invalid"):
            _candidate(operation="x" * (sc.MAX_SHORT_TEXT_CHARS + 1))


class CrossWorkCandidateTests(unittest.TestCase):
    def test_two_distinct_supporting_works_and_counterexample_are_required(self) -> None:
        same_work = [
            _evidence("WORK-A", 1, "support"),
            _evidence("WORK-A", 2, "support"),
            _evidence("WORK-A", 3, "counterexample"),
        ]
        with self.assertRaisesRegex(sc.StyleContractError, "cross_work_support_insufficient"):
            _candidate(evidence_refs=same_work)

        no_counterexample = [
            _evidence("WORK-A", 1, "support"),
            _evidence("WORK-B", 2, "support"),
        ]
        with self.assertRaisesRegex(sc.StyleContractError, "counterexample_evidence_required"):
            _candidate(evidence_refs=no_counterexample)

    def test_named_author_instruction_and_known_identity_term_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            sc.StyleContractError, "named_author_or_identity_imitation_forbidden"
        ):
            _candidate(operation="Write in the style of a named author.")
        with self.assertRaisesRegex(
            sc.StyleContractError, "named_author_or_identity_imitation_forbidden"
        ):
            _candidate(
                operation="Preserve PRIVATE_IDENTITY_SENTINEL cadence.",
                forbidden_identity_terms=("PRIVATE_IDENTITY_SENTINEL",),
            )

    def test_evidence_reference_identity_is_opaque_and_bounded(self) -> None:
        malformed = _candidate()
        malformed["evidence_refs"][0]["work_id"] = "C:/private/book.txt"
        malformed["record_fingerprint"] = sc.fingerprint(
            {key: value for key, value in malformed.items() if key != "record_fingerprint"}
        )
        self.assertIn("evidence_work_id_invalid", sc.validate_craft_candidate(malformed))

        too_many = [
            _evidence(f"WORK-{index}", index, "support" if index else "counterexample")
            for index in range(sc.MAX_EVIDENCE_REFS + 1)
        ]
        with self.assertRaisesRegex(sc.StyleContractError, "evidence_refs_invalid"):
            _candidate(evidence_refs=too_many)

        duplicate = _candidate()
        duplicate["evidence_refs"][2] = {
            **duplicate["evidence_refs"][0],
            "role": "counterexample",
        }
        duplicate["record_fingerprint"] = sc.fingerprint(
            {key: value for key, value in duplicate.items() if key != "record_fingerprint"}
        )
        self.assertIn("evidence_ref_duplicate", sc.validate_craft_candidate(duplicate))


class StyleCompilationTests(unittest.TestCase):
    def test_candidate_compiler_erases_all_evidence_identity_and_rationale_lists(self) -> None:
        candidate = _candidate()
        compiled = sc.compile_source_free_craft_candidate(candidate)
        serialized = json.dumps(compiled, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "WORK-A",
            "WORK-B",
            "WORK-C",
            "EV-1",
            "evidence_refs",
            "supports",
            "counterexamples",
            "record_id",
            "record_fingerprint",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(2, compiled["supporting_work_count"])
        self.assertEqual(1, compiled["counterexample_count"])

    def test_contract_is_closed_fingerprint_bound_and_order_deterministic(self) -> None:
        syntax = _candidate(record_id="CLAIM-SYNTAX")
        imagery = _candidate(
            record_id="CLAIM-IMAGE",
            axis="imagery",
            operation="Repeat one concrete image only when its meaning changes.",
        )
        first = _contract(imagery, syntax)
        second = _contract(syntax, imagery)
        self.assertEqual(first, second)
        self.assertEqual([], sc.validate_style_contract(first))
        self.assertEqual(
            ["syntax_rhythm", "imagery"],
            [candidate["axis"] for candidate in first["craft_candidates"]],
        )
        self.assertEqual("source_free", first["attribution_mode"])
        self.assertEqual("required_external", first["leakage_policy"]["semantic_check"])

    def test_contract_rejects_unknown_identity_fields_even_with_recomputed_fingerprint(self) -> None:
        contract = _contract()
        contract["author"] = "PRIVATE_IDENTITY_SENTINEL"
        contract["contract_fingerprint"] = sc.fingerprint(
            {key: value for key, value in contract.items() if key != "contract_fingerprint"}
        )
        errors = sc.validate_style_contract(contract)
        self.assertIn("contract_schema_not_closed", errors)
        self.assertIn("forbidden_identity_or_prose_field", errors)

    def test_contract_fingerprint_detects_nested_tampering(self) -> None:
        contract = _contract()
        contract["craft_candidates"][0]["effect"] = "Tampered effect."
        self.assertIn("contract_fingerprint_mismatch", sc.validate_style_contract(contract))

        contract["contract_fingerprint"] = sc.fingerprint(
            {key: value for key, value in contract.items() if key != "contract_fingerprint"}
        )
        self.assertIn("craft_id_binding_mismatch", sc.validate_style_contract(contract))

    def test_duplicate_candidates_and_mixed_content_zones_are_rejected(self) -> None:
        candidate = _candidate()
        with self.assertRaisesRegex(sc.StyleContractError, "duplicate_craft_candidate"):
            _contract(candidate, copy.deepcopy(candidate))

        explicit = _candidate(record_id="CLAIM-X", content_zone="adult_explicit")
        with self.assertRaisesRegex(sc.StyleContractError, "mixed_content_zone_forbidden"):
            _contract(explicit, content_zone="general")

    def test_body_appearance_is_an_ordinary_general_craft_axis(self) -> None:
        body_candidate = _candidate(
            record_id="CLAIM-BODY",
            axis="body_appearance",
            operation="让巨乳、肩线与姿态等外貌细节服从当前视角的注意顺序。",
            effect="让身材描写承担人物判断、关系变化或场景定位，而非脱离叙事。",
        )
        contract = _contract(body_candidate, content_zone="general")
        self.assertEqual("general", contract["content_zone"])
        self.assertEqual("body_appearance", contract["craft_candidates"][0]["axis"])
        self.assertNotIn("quarantine", json.dumps(contract, ensure_ascii=False).casefold())

    def test_writer_projection_has_no_evidence_identity_or_internal_craft_ids(self) -> None:
        contract = _contract()
        projection = sc.compile_writer_safe_projection(contract)
        self.assertEqual([], sc.validate_writer_projection(projection))
        serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "work_id",
            "evidence",
            "supporting_work_count",
            "counterexample_count",
            "craft_id",
            "WORK-A",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual("required_external", projection["semantic_leakage_check"])
        self.assertEqual(contract["contract_fingerprint"], projection["style_contract_fingerprint"])

    def test_writer_projection_is_closed_and_fingerprint_bound(self) -> None:
        projection = sc.compile_writer_projection(_contract())
        projection["craft_candidates"][0]["quote"] = "forbidden"
        projection["projection_fingerprint"] = sc.fingerprint(
            {key: value for key, value in projection.items() if key != "projection_fingerprint"}
        )
        errors = sc.validate_writer_projection(projection)
        self.assertIn("craft_schema_not_closed", errors)
        self.assertIn("forbidden_identity_or_prose_field", errors)


class LocalLeakageGateTests(unittest.TestCase):
    def test_exact_ngram_overlap_blocks_without_returning_matched_text(self) -> None:
        sentinel = "SYNTHETIC_EXACT_SEQUENCE_0123456789"
        report = sc.check_local_leakage(
            f"candidate prefix {sentinel} candidate suffix",
            {"REF-A": f"reference prefix {sentinel} reference suffix"},
            exact_ngram_size=16,
            normalized_ngram_size=32,
        )
        self.assertEqual("blocked", report["local_status"])
        self.assertGreater(report["findings"][0]["exact_ngram_hits"], 0)
        self.assertNotIn(sentinel, json.dumps(report, ensure_ascii=False))

    def test_normalized_ngram_catches_case_width_spacing_and_punctuation_variation(self) -> None:
        candidate = "ＡＢＣ， Synthetic CASE marker：一二三四五六七八九十。"
        reference = "abc synthetic case marker 一二三四五六七八九十"
        report = sc.check_local_leakage(
            candidate,
            {"REF-N": reference},
            exact_ngram_size=64,
            normalized_ngram_size=12,
            fuzzy_jaccard_threshold_ppm=1_000_000,
        )
        finding = report["findings"][0]
        self.assertEqual(0, finding["exact_ngram_hits"])
        self.assertGreater(finding["normalized_ngram_hits"], 0)
        self.assertTrue(finding["blocked"])

    def test_fuzzy_shingle_and_minhash_are_deterministic(self) -> None:
        candidate = "alpha beta gamma delta changed epsilon zeta eta theta"
        reference = "alpha beta gamma delta original epsilon zeta eta theta"
        arguments = {
            "exact_ngram_size": 64,
            "normalized_ngram_size": 64,
            "shingle_size": 2,
            "fuzzy_jaccard_threshold_ppm": 250_000,
            "minhash_signature_size": 64,
        }
        first = sc.check_local_leakage(candidate, {"REF-F": reference}, **arguments)
        second = sc.local_leakage_check(candidate, {"REF-F": reference}, **arguments)
        self.assertEqual(first, second)
        finding = first["findings"][0]
        self.assertGreater(finding["shingle_jaccard_ppm"], 250_000)
        self.assertGreater(finding["minhash_jaccard_estimate_ppm"], 0)
        self.assertEqual("blocked", first["local_status"])

    def test_local_pass_never_claims_semantic_or_release_pass(self) -> None:
        report = sc.check_local_leakage(
            "brief candidate with entirely separate vocabulary",
            {"REF-CLEAN": "unrelated reference tokens form another construction"},
            exact_ngram_size=16,
            normalized_ngram_size=20,
            shingle_size=3,
            fuzzy_jaccard_threshold_ppm=500_000,
        )
        self.assertEqual("pass", report["local_status"])
        self.assertFalse(report["release_ready"])
        self.assertEqual(
            {"status": "required_external", "performed": False},
            {
                "status": report["semantic_check"]["status"],
                "performed": report["semantic_check"]["performed"],
            },
        )
        self.assertEqual([], sc.validate_leakage_report(report))

        forged = copy.deepcopy(report)
        forged["release_ready"] = True
        forged["report_fingerprint"] = sc.fingerprint(
            {key: value for key, value in forged.items() if key != "report_fingerprint"}
        )
        self.assertIn("local_report_cannot_grant_release", sc.validate_leakage_report(forged))

    def test_leakage_gate_validates_bounds_and_opaque_reference_ids(self) -> None:
        with self.assertRaisesRegex(sc.StyleContractError, "reference_id_invalid"):
            sc.check_local_leakage("candidate", {"C:/private/source.txt": "reference"})
        with self.assertRaisesRegex(sc.StyleContractError, "exact_ngram_size_invalid"):
            sc.check_local_leakage("candidate", {"REF-A": "reference"}, exact_ngram_size=1)
        with self.assertRaisesRegex(sc.StyleContractError, "candidate_text_invalid"):
            sc.check_local_leakage("", {"REF-A": "reference"})


if __name__ == "__main__":
    unittest.main()
