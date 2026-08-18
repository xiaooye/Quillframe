from __future__ import annotations

import unittest

from production_runtime import ProductionRunError, ProductionRunExecutor


class RuleMaterialPreflightTests(unittest.TestCase):
    def test_valid_candidate_self_audit_rule_material_passes_dry_contract_validation(self):
        ProductionRunExecutor.validate_rule_material(
            [{"id": "HF-01", "authority": "framework", "statement": "Avoid low-value micro-shot fragmentation."}],
            "very_high",
        )

    def test_unregistered_rule_fields_fail_before_semantic_execution(self):
        with self.assertRaises(ProductionRunError) as caught:
            ProductionRunExecutor.validate_rule_material(
                [{
                    "id": "HF-01",
                    "authority": "framework",
                    "statement": "Avoid low-value micro-shot fragmentation.",
                    "severity": "blocking",
                }],
                "very_high",
            )
        self.assertEqual(caught.exception.code, "quality_rule_material_invalid")
        self.assertIn("unexpected field severity", str(caught.exception))

    def test_empty_rule_material_fails_closed(self):
        with self.assertRaises(ProductionRunError) as caught:
            ProductionRunExecutor.validate_rule_material([], "very_high")
        self.assertEqual(caught.exception.code, "quality_rule_material_required")

    def test_invalid_reader_grip_fails_through_registered_contract(self):
        with self.assertRaises(ProductionRunError) as caught:
            ProductionRunExecutor.validate_rule_material(
                [{"id": "HF-01", "authority": "framework", "statement": "A bounded rule."}],
                "impossible",
            )
        self.assertEqual(caught.exception.code, "quality_rule_material_invalid")
        self.assertIn("value not in enum", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
