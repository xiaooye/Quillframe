"""Synthetic-only tests for historical qualification verification.

These fabricated jobs/results exercise deterministic boundaries, not real
review or authorization. No production model or project is used.
"""
from __future__ import annotations

from contextlib import redirect_stderr
from copy import deepcopy
import hashlib
import inspect
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
for path in (ROOT, SEM, ROOT / "quality", ROOT / "evals"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import candidate_qualification as qualification
from objective_envelope import build as build_objective_envelope
from production_readiness import evaluate as production_readiness
from qualification_test_fixtures import _binding
from registered_contract_binding import validate_recorded_registered_job, validate_registered_job
from semantic_worker_router import fingerprint_for, make_contract_job


SUBJECT = "CH-RECORDED-QUALIFICATION-FIXTURE"
TEXT = "Synthetic deterministic CI candidate."
FP = "sha256:" + hashlib.sha256(TEXT.encode("utf-8")).hexdigest()
ARCHIVE = SEM / "contracts" / "history" / "quality.v7.json"


def fingerprint(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def rebind(binding):
    job, result = binding["job"], binding["result"]
    job["input_fingerprint"] = fingerprint_for(job)
    result.update({key: job[key] for key in ("job_id", "subject_id", "kind", "input_fingerprint")})


def recorded_binding(binding):
    """Fabricate the exact historical definition, never a production receipt."""
    old = deepcopy(binding)
    current = old["job"]
    job = make_contract_job(
        current["input"]["model_contract_id"], current["subject_id"], current["input"]["payload"],
        registry_path=ARCHIVE, source_session_id="SES-CI-MANAGER",
    )
    # The archived file is trusted by the reader. The historical job itself
    # records the original catalog location, not the archive's new location.
    job["provenance"].update({"pack_id": "quality", "registry_path": str(Path("contracts") / "quality.json")})
    old["job"] = job
    rebind(old)
    return old


def current_payload(*, audit_fails=False):
    audit = {
        "confidence": 1.0, "result": "fail" if audit_fails else "pass", "report": "Synthetic recorded audit.",
        "dimensions": {key: "pass" for key in ("surface", "regression", "character_or_ownership", "natural_realization", "cluster")},
        "findings": [], "evidence_refs": ["synthetic:qualification"],
    }
    if audit_fails:
        audit["dimensions"]["surface"] = "fail"
        audit["findings"] = [{
            "finding_id": "F-SYN", "mechanism_id": "HF-TEST", "severity": "high", "scope": "paragraph",
            "repair_owner": "surface", "blocking": True, "report": "Synthetic defect.",
            "function_assessment": "pass", "ownership_assessment": "pass", "natural_realization_assessment": "fail",
            "evidence_refs": ["synthetic:qualification"],
        }]
    reader = {
        "confidence": 1.0, "result": "pass", "report": "Synthetic recorded Reader.",
        "strongest_positive": "Synthetic control.", "strongest_problem": None, "evidence_refs": ["synthetic:qualification"],
    }
    return {
        "candidate_fingerprint": FP, "subject_id": SUBJECT, "repair_cycle": 0,
        "self_audit": {"status": audit["result"], "semantic_binding": _binding("quality.candidate_self_audit", SUBJECT, FP, audit)},
        "reader_engagement": {"status": "pass", "semantic_binding": _binding("reader.engagement_audit", SUBJECT, FP, reader)},
        "continuity": {"status": "pass", "candidate_fingerprint": FP,
                       "receipt_fingerprint": "sha256:" + "c" * 64, "evidence_refs": ["synthetic:continuity"]},
    }


def with_recorded_quality(payload):
    recorded = deepcopy(payload)
    for key in ("self_audit", "reader_engagement"):
        recorded[key]["semantic_binding"] = recorded_binding(recorded[key]["semantic_binding"])
    return recorded


def expected_recorded_receipt(current, recorded):
    """Only job/result identities change; historical judgments stay identical."""
    expected = qualification.evaluate(current)
    for gate in expected["gates"]:
        binding = recorded.get(gate["gate"], {}).get("semantic_binding")
        if binding:
            gate["job_fingerprint"] = binding["job"]["input_fingerprint"]
            gate["result_fingerprint"] = fingerprint(binding["result"])
    expected["receipt_fingerprint"] = fingerprint({key: value for key, value in expected.items() if key != "receipt_fingerprint"})
    return expected


def with_comparison(payload, *, regression=False):
    value = deepcopy(payload)
    envelope = build_objective_envelope({
        "subject_id": SUBJECT, "run_id": "RUN-CI", "authority_cutoff": "synthetic",
        "objective_items": [{"id": "OBJ-CI", "category": "user_direction", "statement": "Synthetic objective.", "source_refs": ["synthetic:request"]}],
        "must_preserve": ["OBJ-CI"], "derived_from_rejected_realization": False,
    })
    job = make_contract_job("quality.compare", "CMP-CI", {
        "evolution_run_id": "RUN-CI", "evolution_subject_id": SUBJECT, "comparison_id": "CMP-CI",
        "incumbent": {"candidate_id": "C0", "content_fingerprint": "sha256:" + hashlib.sha256(b"Synthetic baseline.").hexdigest(), "text": "Synthetic baseline."},
        "challenger": {"candidate_id": "C1", "content_fingerprint": FP, "text": TEXT, "repair_owner": "surface"},
        "repair_context": {"repair_target": "Synthetic repair.", "objective_envelope": envelope},
    }, source_session_id="SES-CI-MANAGER")
    result = {
        **{key: job[key] for key in ("job_id", "subject_id", "kind", "input_fingerprint")},
        "status": "completed", "worker": {"provider": "self_test", "model_or_reviewer": "synthetic-ci-fixture"},
        "judgment": {
            "confidence": 1.0, "winner": "incumbent" if regression else "challenger", "reason": "Synthetic comparison.",
            "target_outcome": "improved", "objective_preservation": "degraded" if regression else "preserved",
            "reader_value": "unchanged", "character_relationship_energy": "preserved",
            "outcome_class": "objective_regression" if regression else "successful_repair",
            "repaired_findings": ["F-SYN"], "introduced_regressions": ["reader"] if regression else [],
            "regressed_dimensions": ["reader"] if regression else [], "preserved_strengths": [], "evidence": ["synthetic:compare"],
        },
        "proposals": [], "errors": [],
    }
    value.update({"repair_cycle": 1, "repair_preservation": {
        "status": "fail" if regression else "pass", "semantic_binding": {"job": job, "result": result},
    }})
    return value


class RecordedQualificationTests(unittest.TestCase):
    def test_current_and_recorded_use_identical_algorithm_without_mutation(self):
        value = current_payload()
        before = deepcopy(value)
        self.assertEqual(qualification.evaluate(value), qualification.evaluate_recorded(value))
        self.assertEqual(before, value)

    def test_recorded_pass_preserves_exact_receipt_shape_and_judgment(self):
        current = current_payload()
        old = with_recorded_quality(current)
        before = deepcopy(old)
        receipt = qualification.evaluate_recorded(old)
        self.assertEqual(expected_recorded_receipt(current, old), receipt)
        self.assertEqual("quillframe_candidate_qualification_v1", receipt["schema"])
        self.assertEqual("qualified_for_independent", receipt["qualification_status"])
        self.assertFalse(receipt["independent"])
        self.assertFalse(receipt["authority"])
        self.assertFalse(receipt["model_execution"])
        self.assertEqual(before, old)
        self.assertEqual([], qualification.validate_qualification_receipt(receipt, candidate_fingerprint=FP, subject_id=SUBJECT))

    def test_current_evaluate_rejects_each_recorded_gate(self):
        for key in ("self_audit", "reader_engagement"):
            with self.subTest(gate=key):
                value = current_payload()
                value[key]["semantic_binding"] = recorded_binding(value[key]["semantic_binding"])
                self.assertTrue(validate_registered_job(value[key]["semantic_binding"]["job"]))
                with self.assertRaisesRegex(ValueError, "registered job invalid"):
                    qualification.evaluate(value)
                self.assertEqual("qualified_for_independent", qualification.evaluate_recorded(value)["qualification_status"])

    def test_recorded_failure_is_not_promoted_or_relabelled(self):
        current = current_payload(audit_fails=True)
        old = with_recorded_quality(current)
        receipt = qualification.evaluate_recorded(old)
        self.assertEqual(expected_recorded_receipt(current, old), receipt)
        self.assertEqual("repair_required", receipt["qualification_status"])
        self.assertEqual(["self_audit"], receipt["failed_gates"])
        self.assertEqual("F-SYN", receipt["blocking_findings"][0]["finding_id"])
        self.assertTrue(qualification.validate_qualification_receipt(receipt, require_qualified=True))

    def test_recorded_comparison_keeps_existing_axes_and_uses_recorded_validator(self):
        for regression in (False, True):
            with self.subTest(regression=regression):
                current = with_comparison(current_payload(), regression=regression)
                old = with_recorded_quality(current)
                with patch("registered_contract_binding.validate_recorded_registered_job", wraps=validate_recorded_registered_job) as validator:
                    receipt = qualification.evaluate_recorded(old)
                self.assertIn("quality.compare", [call.args[0]["input"]["model_contract_id"] for call in validator.call_args_list])
                self.assertEqual(expected_recorded_receipt(current, old), receipt)
                self.assertEqual("fail" if regression else "pass", receipt["repair_preservation_status"])

    def test_recorded_pending_comparison_stays_ineligible_for_dispatch(self):
        old = with_recorded_quality(current_payload())
        old.update({"repair_cycle": 1, "repair_preservation": {"status": "pending"}})
        receipt = qualification.evaluate_recorded(old)
        self.assertEqual("awaiting_semantic", receipt["qualification_status"])
        self.assertEqual(["repair_preservation"], receipt["pending_gates"])
        self.assertTrue(qualification.validate_qualification_receipt(receipt, require_qualified=True))

    def test_rehashed_historical_definition_tampering_is_rejected(self):
        for field in ("rubric", "purpose", "output_contract", "permissions", "version"):
            with self.subTest(field=field):
                old = with_recorded_quality(current_payload())
                binding = old["reader_engagement"]["semantic_binding"]
                job = binding["job"]
                if field == "rubric":
                    job["rubric"] = ["Synthetic substituted rubric."]
                elif field == "purpose":
                    job["input"]["purpose"] = "Synthetic substituted purpose."
                elif field == "output_contract":
                    job["output_contract"] = {"type": "object"}
                elif field == "permissions":
                    job["permissions"]["allowed_result_scope"] = "observation"
                else:
                    job["input"]["model_contract_version"] = "999"
                    job["provenance"]["registry_version"] = "999"
                rebind(binding)
                with self.assertRaisesRegex(ValueError, "registered job invalid"):
                    qualification.evaluate_recorded(old)

    def test_unpinned_comparison_version_cannot_use_recorded_path(self):
        old = with_recorded_quality(with_comparison(current_payload()))
        binding = old["repair_preservation"]["semantic_binding"]
        binding["job"]["input"]["model_contract_version"] = "999"
        binding["job"]["provenance"]["registry_version"] = "999"
        rebind(binding)
        with self.assertRaisesRegex(ValueError, "repair_preservation registered job invalid"):
            qualification.evaluate_recorded(old)

    def test_archive_bytes_must_match_trusted_index(self):
        old = with_recorded_quality(current_payload())
        original = Path.read_bytes
        def changed_bytes(path):
            return original(path) + b" " if path.resolve() == ARCHIVE.resolve() else original(path)
        with patch.object(Path, "read_bytes", changed_bytes):
            with self.assertRaisesRegex(ValueError, "recorded registry fingerprint mismatch"):
                qualification.evaluate_recorded(old)

    def test_candidate_subject_and_result_binding_remain_exact(self):
        for defect in ("candidate", "subject", "result"):
            with self.subTest(defect=defect):
                old = with_recorded_quality(current_payload())
                binding = old["reader_engagement"]["semantic_binding"]
                if defect == "candidate":
                    binding["job"]["input"]["payload"]["candidate_fingerprint"] = "sha256:" + "d" * 64
                    rebind(binding)
                elif defect == "subject":
                    binding["job"]["subject_id"] = "CH-OTHER"
                    rebind(binding)
                else:
                    binding["result"]["input_fingerprint"] = "sha256:" + "d" * 64
                with self.assertRaises(ValueError):
                    qualification.evaluate_recorded(old)

    def test_recorded_gate_status_cannot_override_its_judgment(self):
        old = with_recorded_quality(current_payload(audit_fails=True))
        old["self_audit"]["status"] = "pass"
        with self.assertRaisesRegex(ValueError, "status contradicts semantic result"):
            qualification.evaluate_recorded(old)

    def test_json_fields_cannot_select_historical_evaluation(self):
        for key in ("recorded", "_recorded", "allow_historical", "binding_validator", "registry_path"):
            with self.subTest(selector=key):
                old = with_recorded_quality(current_payload())
                old[key] = "validate_recorded_registered_job"
                with self.assertRaisesRegex(ValueError, "registered job invalid"):
                    qualification.evaluate(old)
        self.assertEqual(["payload"], list(inspect.signature(qualification.evaluate).parameters))

    def test_cli_has_no_recorded_evaluation_command(self):
        with patch.object(sys, "argv", ["candidate_qualification.py", "evaluate-recorded"]), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                qualification.main()
        self.assertEqual(2, caught.exception.code)

    def test_current_production_readiness_rejects_recorded_reader_evidence(self):
        old = with_recorded_quality(current_payload())
        receipt = qualification.evaluate_recorded(old)
        self.assertEqual("qualified_for_independent", receipt["qualification_status"])
        with self.assertRaisesRegex(ValueError, "registered contract binding invalid"):
            production_readiness({
                "candidate_fingerprint": FP, "policy": {"reader_grip": "very_high", "require_continuity": True},
                "gates": [
                    {"category": "surface", "candidate_fingerprint": FP, "status": "pass"},
                    {"category": "continuity", "candidate_fingerprint": FP, "status": "pass"},
                    {"category": "reader_engagement", "candidate_fingerprint": FP, **old["reader_engagement"]},
                ],
            })


if __name__ == "__main__":
    unittest.main()
