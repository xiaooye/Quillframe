"""Safety and authority tests for the private user-taste layer."""
from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from learning.promotion_gate import (
    SCHEMA as PROMOTION_SCHEMA,
    _eval_binding,
    _semantic_binding,
    evaluate,
)
from learning.user_taste import (
    UserTasteService,
    materialize_selection,
    selection_payload,
    validate_snapshot,
)

CANDIDATE_ARTIFACT_FP = "sha256:" + "a" * 64
CRAFT_PACK_FP = "sha256:" + "b" * 64
TAMPERED_FP = "sha256:" + "f" * 64


class UserTasteServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "author.sqlite"
        self.service = UserTasteService(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _candidate(*, candidate_id: str, mechanism: str, refs: list[str],
                   eval_result: str = "pass") -> dict:
        candidate = {
            "schema": PROMOTION_SCHEMA,
            "candidate_id": candidate_id,
            "scope": "user_taste",
            "mechanism": mechanism,
            "evidence": {
                "evidence_refs": refs,
                "contradiction_review": {"status": "pass"},
            },
        }
        candidate["semantic_review_binding"] = _semantic_binding(
            candidate_id, "user_taste", mechanism, refs
        )
        candidate["independent_eval_binding"] = _eval_binding(
            candidate_id, "user_taste", mechanism, result=eval_result
        )
        return candidate

    def _ingest(self, *, suffix: str = "A", eval_result: str = "pass") -> dict:
        mechanism = "causal_consequence_before_explanation_" + suffix.lower()
        refs = ["public-corpus:PC-TEST:work-" + suffix]
        return self.service.ingest_corpus_candidate({
            "dimension": "causal_progression",
            "statement": "Prefer consequence-bearing action before optional explanation.",
            "mechanism": mechanism,
            "corpus_evidence_refs": refs,
            "applicability": {
                "applies_when": ["pressure_scene"],
                "avoid_when": ["deliberate_reflective_pause"],
            },
            "artifact_ref": "public-corpus:PC-TEST:aggregate-v1",
            "artifact_fingerprint": "sha256:" + "1" * 64,
            "promotion_candidate": self._candidate(
                candidate_id="UT-" + suffix,
                mechanism=mechanism,
                refs=refs,
                eval_result=eval_result,
            ),
        })

    def test_policy_is_revocable_versioned_user_authority(self) -> None:
        initial = self.service.get_policy()
        self.assertFalse(initial["enabled"])
        enabled = self.service.set_policy({
            "enabled": True,
            "expected_version": initial["policy_version"],
            "source_kinds": ["corpus", "feedback", "user_edit"],
            "authorization_ref": "user:standing-policy:test",
        })
        self.assertTrue(enabled["enabled"])
        self.assertFalse(enabled["framework_write"])
        self.assertFalse(enabled["canon_write"])
        with self.assertRaisesRegex(ValueError, "policy version mismatch"):
            self.service.set_policy({
                "enabled": False,
                "expected_version": initial["policy_version"],
                "authorization_ref": "user:stale-revoke",
            })
        revoked = self.service.set_policy({
            "enabled": False,
            "expected_version": enabled["policy_version"],
            "authorization_ref": "user:revoke:test",
        })
        self.assertFalse(revoked["enabled"])
        self.assertIsNotNone(revoked["revoked_at"])

    def test_readonly_snapshot_does_not_create_an_empty_database(self) -> None:
        untouched = Path(self.temp.name) / "readonly" / "author.sqlite"
        snapshot = UserTasteService.snapshot_readonly(untouched)
        self.assertFalse(snapshot["policy"]["enabled"])
        self.assertEqual(snapshot["candidates"], [])
        self.assertFalse(untouched.exists())
        self.assertFalse(untouched.parent.exists())

    def test_corpus_candidate_auto_activates_only_after_all_gates(self) -> None:
        initial = self.service.get_policy()
        self.service.set_policy({
            "enabled": True,
            "expected_version": initial["policy_version"],
            "source_kinds": ["corpus"],
            "authorization_ref": "user:standing-policy:test",
        })
        blocked = self._ingest(suffix="BLOCKED", eval_result="fail")
        self.assertEqual(blocked["preference"]["state"], "candidate")
        self.assertEqual(blocked["auto_activation"]["status"], "blocked")

        activated = self._ingest(suffix="ACTIVE")
        self.assertEqual(activated["preference"]["state"], "active")
        self.assertEqual(activated["auto_activation"]["status"], "activated")
        self.assertFalse(activated["auto_activation"]["receipt"]["authority"])

        snapshot = self.service.snapshot()
        self.assertEqual(snapshot, UserTasteService.snapshot_readonly(self.db))
        validate_snapshot(snapshot)
        encoded = repr(snapshot)
        self.assertNotIn("public-corpus:PC-TEST:work-ACTIVE", encoded)
        self.assertNotIn("artifact_ref", encoded)
        self.assertNotIn("evidence_ids", encoded)
        self.assertNotIn("statement", encoded)
        tampered = deepcopy(snapshot)
        tampered["policy"]["framework_write"] = True
        from harness.context_runtime import fingerprint
        tampered["snapshot_fingerprint"] = fingerprint({
            key: value for key, value in tampered.items() if key != "snapshot_fingerprint"
        })
        with self.assertRaisesRegex(ValueError, "policy fingerprint changed"):
            validate_snapshot(tampered)

    def test_pause_withdraw_and_invalidation_are_version_checked(self) -> None:
        initial = self.service.get_policy()
        self.service.set_policy({
            "enabled": True,
            "expected_version": initial["policy_version"],
            "source_kinds": ["corpus"],
            "authorization_ref": "user:standing-policy:test",
        })
        activated = self._ingest(suffix="STATE")["preference"]
        with self.assertRaisesRegex(ValueError, "preference version mismatch"):
            self.service.pause(
                hypothesis_id=activated["hypothesis_id"],
                expected_version=activated["version"] - 1,
                reason="stale request",
            )
        paused = self.service.suspend_invalidated(
            activated["evidence_ids"], reason="public corpus release invalidated"
        )
        self.assertEqual(paused["suspended_hypothesis_ids"], [activated["hypothesis_id"]])
        contested = self.service.get_preference(activated["hypothesis_id"])
        self.assertEqual(contested["state"], "contested")
        withdrawn = self.service.withdraw(
            hypothesis_id=contested["hypothesis_id"],
            expected_version=contested["version"],
            reason="user withdrew preference",
        )
        self.assertEqual(withdrawn["preference"]["state"], "deprecated")
        with self.assertRaisesRegex(ValueError, "invalid preference state transition"):
            self.service.pause(
                hypothesis_id=contested["hypothesis_id"],
                expected_version=withdrawn["preference"]["version"],
                reason="cannot revive a withdrawn preference by pausing it",
            )

    def test_writer_selection_can_choose_none_and_exposes_only_safe_mechanisms(self) -> None:
        initial = self.service.get_policy()
        self.service.set_policy({
            "enabled": True,
            "expected_version": initial["policy_version"],
            "source_kinds": ["corpus"],
            "authorization_ref": "user:standing-policy:test",
        })
        active = self._ingest(suffix="SELECT")["preference"]
        snapshot = self.service.snapshot()
        payload = selection_payload(
            snapshot,
            request="Write a reflective transition without manufactured conflict.",
            scene_context={"scene_type": "transition"},
        )
        self.assertIsNotNone(payload)
        self.assertIsNone(materialize_selection(snapshot, [], binding_fingerprint="sha256:" + "2" * 64))
        guidance = materialize_selection(
            snapshot,
            [{"hypothesis_id": active["hypothesis_id"], "reason": "Relevant to causal exposition."}],
            binding_fingerprint="sha256:" + "3" * 64,
        )
        self.assertEqual(guidance["preferences"][0]["mechanism"], active["mechanism"])
        self.assertNotIn("reason", guidance["preferences"][0])
        with self.assertRaisesRegex(ValueError, "unknown or repeated"):
            materialize_selection(
                snapshot,
                [{"hypothesis_id": "PH-UNKNOWN", "reason": "Not in frozen inventory."}],
                binding_fingerprint="sha256:" + "4" * 64,
            )

    def test_corpus_ingest_rejects_raw_or_identifying_fields(self) -> None:
        payload = {
            "dimension": "dialogue_voice",
            "statement": "Keep each line shaped by identity and stakes.",
            "mechanism": "identity_shaped_dialogue",
            "corpus_evidence_refs": ["public-corpus:PC-TEST:work-X"],
            "applicability": {},
            "artifact_ref": "public-corpus:PC-TEST:aggregate-v1",
            "artifact_fingerprint": "sha256:" + "5" * 64,
            "promotion_candidate": self._candidate(
                candidate_id="UT-X",
                mechanism="identity_shaped_dialogue",
                refs=["public-corpus:PC-TEST:work-X"],
            ),
            "raw_text": "synthetic source passage",
        }
        with self.assertRaisesRegex(ValueError, "source-identifying or raw"):
            self.service.ingest_corpus_candidate(payload)

    def test_general_craft_promotion_needs_cross_work_counterexample_and_boundary(self) -> None:
        refs = ["public-corpus:PC-TEST:work-A", "public-corpus:PC-TEST:work-B"]
        candidate = {
            "schema": PROMOTION_SCHEMA,
            "candidate_id": "GC-TEST",
            "scope": "general_craft",
            "mechanism": "consequence_changes_scene_state",
            "candidate_artifact_fingerprint": CANDIDATE_ARTIFACT_FP,
            "craft_pack_fingerprint": CRAFT_PACK_FP,
            "evidence": {
                "evidence_refs": refs,
                "version_target": "1.1.0",
                "rollback_binding": {
                    "rollback_ref": "git:baseline",
                    "candidate_artifact_fingerprint": CANDIDATE_ARTIFACT_FP,
                    "craft_pack_fingerprint": CRAFT_PACK_FP,
                },
                "framework_ci": {
                    "conclusion": "success",
                    "commit": "0123456789abcdef0123456789abcdef01234567",
                    "candidate_artifact_fingerprint": CANDIDATE_ARTIFACT_FP,
                    "craft_pack_fingerprint": CRAFT_PACK_FP,
                },
                "provenance_refs": refs,
                "logical_work_refs": refs,
                "counterexample_refs": ["public-corpus:PC-TEST:work-C"],
                "profile_boundary": {"profiles": ["general", "adult_explicit_separate"]},
                "public_corpus_version": "PC-TEST-v1",
            },
        }
        candidate["semantic_review_binding"] = _semantic_binding(
            "GC-TEST", "general_craft", "consequence_changes_scene_state", refs,
            candidate_artifact_fingerprint=CANDIDATE_ARTIFACT_FP,
            craft_pack_fingerprint=CRAFT_PACK_FP,
        )
        candidate["independent_eval_binding"] = _eval_binding(
            "GC-TEST", "general_craft", "consequence_changes_scene_state",
            candidate_artifact_fingerprint=CANDIDATE_ARTIFACT_FP,
            craft_pack_fingerprint=CRAFT_PACK_FP,
        )
        promoted = evaluate(candidate)
        self.assertEqual(promoted["status"], "promotable")
        self.assertTrue(promoted["artifact_binding"]["all_bound"])
        self.assertEqual(
            promoted["artifact_binding"]["candidate_artifact_fingerprint"],
            CANDIDATE_ARTIFACT_FP,
        )
        self.assertEqual(
            promoted["artifact_binding"]["craft_pack_fingerprint"],
            CRAFT_PACK_FP,
        )
        for component in ("semantic_review", "independent_eval", "framework_ci", "rollback"):
            self.assertTrue(
                promoted["artifact_binding"][component]["matches_expected"],
                component,
            )
        self.assertTrue(promoted["artifact_binding"]["framework_ci"]["binding_valid"])
        self.assertTrue(promoted["artifact_binding"]["rollback"]["binding_valid"])
        self.assertEqual(
            "git:baseline",
            promoted["artifact_binding"]["rollback"]["rollback_ref"],
        )
        narrowed = deepcopy(candidate)
        narrowed["evidence"].pop("counterexample_refs")
        report = evaluate(narrowed)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("general_craft requires counterexample_refs", report["blockers"])

        for field in ("candidate_artifact_fingerprint", "craft_pack_fingerprint"):
            with self.subTest(component="candidate", field=field):
                tampered = deepcopy(candidate)
                tampered[field] = TAMPERED_FP
                report = evaluate(tampered)
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(report["artifact_binding"]["all_bound"])

            for component in ("semantic_review", "independent_eval", "framework_ci", "rollback"):
                with self.subTest(component=component, field=field):
                    tampered = deepcopy(candidate)
                    pair = {
                        "candidate_artifact_fingerprint": CANDIDATE_ARTIFACT_FP,
                        "craft_pack_fingerprint": CRAFT_PACK_FP,
                    }
                    pair[field] = TAMPERED_FP
                    if component == "semantic_review":
                        tampered["semantic_review_binding"] = _semantic_binding(
                            "GC-TEST",
                            "general_craft",
                            "consequence_changes_scene_state",
                            refs,
                            **pair,
                        )
                    elif component == "independent_eval":
                        tampered["independent_eval_binding"] = _eval_binding(
                            "GC-TEST",
                            "general_craft",
                            "consequence_changes_scene_state",
                            **pair,
                        )
                    elif component == "framework_ci":
                        tampered["evidence"]["framework_ci"][field] = TAMPERED_FP
                    else:
                        tampered["evidence"]["rollback_binding"][field] = TAMPERED_FP
                    report = evaluate(tampered)
                    self.assertEqual(report["status"], "blocked")
                    self.assertFalse(report["artifact_binding"]["all_bound"])

        for field in ("candidate_artifact_fingerprint", "craft_pack_fingerprint"):
            with self.subTest(component="candidate_format", field=field):
                malformed = deepcopy(candidate)
                malformed[field] = "not-a-fingerprint"
                report = evaluate(malformed)
                self.assertEqual(report["status"], "blocked")
                self.assertIn(
                    f"general_craft requires valid {field}",
                    report["blockers"],
                )


if __name__ == "__main__":
    unittest.main()
