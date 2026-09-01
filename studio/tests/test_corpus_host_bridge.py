from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore
from studio import host_bridge


HASH_A = "sha256:" + "a" * 64


def request(operation: str, args: dict, surface: str = "local_app") -> dict:
    return {
        "schema": host_bridge.REQUEST_SCHEMA,
        "bridge_version": host_bridge.BRIDGE_VERSION,
        "request_id": "studio-corpus-test",
        "operation": operation,
        "surface": surface,
        "args": args,
        "authority": False,
    }


class FakeCore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.profile = "general"
        self.returned_profile: str | None = None
        self.returned_study_id: str | None = None

    def corpus_scan_collection(self, *args, **kwargs):
        self.calls.append(("scan", args, kwargs))
        return {"schema": "quillframe_corpus_scan_v1", "status": "completed", "collection_id": "COL-1"}

    def corpus_propose_selection(self, **kwargs):
        self.calls.append(("propose", (), kwargs))
        self.profile = self.returned_profile or kwargs["profile"]
        study_id = self.returned_study_id or kwargs.get("study_id", "STUDY-1")
        return {"schema": "quillframe_corpus_study_status_v1", "study_id": study_id,
                "profile": self.profile, "status": "proposed", "proposal_hash": HASH_A,
                "exclusion_counts": {"source_ineligible": 1, "logical_family_alternate": 3,
                                     "identity_unknown": 2, "below_minimum_chars": 3,
                                     "ambiguous_profile": 2},
                "works": [{"public_work_id": f"PW-{index:032x}", "display_label": "must-not-leak",
                           "creator": "must-not-leak", "relative_locator": "private/source.txt"}
                          for index in range(120)]}

    def corpus_selection_private_preview(self, study_id):
        self.calls.append(("private", (study_id,), {}))
        return {"schema": "quillframe_corpus_selection_private_preview_v1", "study_id": study_id,
                "profile": self.profile, "status": "proposed", "proposal_hash": HASH_A, "work_count": 120,
                "private_local_only": True, "redistributable": False, "raw_text_included": False,
                "works": [{"public_work_id": f"PW-{index:032x}", "display_label": f"Licensed work {index:03d}",
                           "creator": f"Creator {index:03d}", "relative_locator": f"shelf/work-{index:03d}.txt"}
                          for index in range(120)]}

    def corpus_study_status(self, study_id, **kwargs):
        self.calls.append(("status", (study_id,), kwargs))
        return {"schema": "quillframe_corpus_study_status_v1", "study_id": study_id, "profile": self.profile,
                "works": [{"public_work_id": f"PW-{index:032x}"} for index in range(120)]}

    def corpus_confirm_selection(self, *args, **kwargs):
        self.calls.append(("confirm", args, kwargs))
        return {"schema": "quillframe_corpus_study_status_v1", "study_id": args[0], "profile": self.profile,
                "status": "confirmed"}

    def corpus_refresh_selection(self, **kwargs):
        self.calls.append(("refresh", (), kwargs))
        return {"schema": "quillframe_corpus_selection_refresh_v1", "study_id": kwargs["study_id"],
                "profile": kwargs["profile"], "status": "proposed", "proposal_hash": HASH_A,
                "public_study_id": "PS-REFRESH", "identity_preserved": True,
                "works": [{"public_work_id": f"PW-{index:032x}"} for index in range(120)]}

    def corpus_preview_public(self, *args, **kwargs):
        self.calls.append(("preview", args, kwargs))
        return {"schema": "quillframe_public_corpus_manifest_v1", "public_study_id": "PS-1",
                "manifest_fingerprint": HASH_A, "preview_token": "preview-token", "works": []}

    def corpus_validate_public(self, *args, **kwargs):
        self.calls.append(("validate", args, kwargs))
        return {"schema": "quillframe_public_corpus_validation_v1", "valid": True, "errors": []}

    def corpus_release_public(self, *args, **kwargs):
        self.calls.append(("release", args, kwargs))
        return {"schema": "quillframe_public_corpus_release_v1", "status": "released", "release_id": "v1"}


class FakeTasteCore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.policy_payload = None

    def user_taste_get_policy(self):
        return {"schema": "quillframe_user_taste_auto_activation_policy_v1", "enabled": False}

    def user_taste_set_policy(self, payload):
        self.policy_payload = payload
        return {"schema": "quillframe_user_taste_auto_activation_policy_v1", **payload}

    def user_taste_list_preferences(self, *, state=None):
        return [{"hypothesis_id": "UT-1", "scope": "user_taste", "state": state or "candidate"}]

    def user_taste_get_preference(self, hypothesis_id):
        return {"hypothesis_id": hypothesis_id, "scope": "user_taste"}

    def user_taste_pause_preference(self, hypothesis_id, **kwargs):
        self.calls.append(("pause", {"hypothesis_id": hypothesis_id, **kwargs}))
        return {"preference": {"hypothesis_id": hypothesis_id, "state": "contested"},
                "receipt": {"schema": "quillframe_user_taste_activation_receipt_v1", "authority": False}}

    def user_taste_withdraw_preference(self, hypothesis_id, **kwargs):
        self.calls.append(("withdraw", {"hypothesis_id": hypothesis_id, **kwargs}))
        return {"preference": {"hypothesis_id": hypothesis_id, "state": "deprecated"},
                "receipt": {"schema": "quillframe_user_taste_activation_receipt_v1", "authority": False}}


class CorpusHostBridgeTests(unittest.TestCase):
    def test_style_study_start_runs_a_bounded_ai_cycle_with_heldout_verification(self) -> None:
        class SemanticCore:
            def __init__(self) -> None:
                self.forwarded = None

            def corpus_start_study(self, **kwargs):
                callback = kwargs.pop("run_semantic")
                self.forwarded = kwargs
                results = [
                    callback({
                        "job_id": f"JOB-STYLE-{ordinal}",
                        "created_at": "2026-08-29T00:00:00+00:00",
                        "input": {"model_contract_id": contract_id},
                        "execution": {
                            "source_session_id": "SES-STYLE-1",
                            "handoff_id": f"HO-STYLE-{ordinal}",
                        },
                    })
                    for ordinal, contract_id in enumerate(
                        ("corpus.style_observe", "learning.style_claim_verify"), 1
                    )
                ]
                return {
                    "schema": "quillframe_corpus_study_operation_v1",
                    "study_id": kwargs["study_id"],
                    "status": "awaiting_semantic",
                    "semantic_result_statuses": [result["status"] for result in results],
                    "authority": False,
                }

        executions = []

        class FakeExecutor:
            def __init__(self, runtime):
                self.runtime = runtime

            def execute_prepared(self, **kwargs):
                executions.append(kwargs)
                return {"result": {"status": "completed", "judgment": {}}}

        fake = SemanticCore()
        with (
            patch.object(host_bridge, "ops", return_value=fake),
            patch.object(host_bridge, "agent_runtime", return_value=object()),
            patch.object(host_bridge, "RegisteredSemanticExecutor", FakeExecutor),
        ):
            result = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-GENERAL-QUALITY-REBUILD-V5",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "model_id": "MODEL-ANALYST",
                "heldout_model_id": "MODEL-HELDOUT",
                "execute_semantic": True,
            }))
            missing_service = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-GENERAL-QUALITY-REBUILD-V5",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "execute_semantic": True,
            }))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["data"]["semantic_result_statuses"],
            ["completed", "completed"],
        )
        self.assertEqual(fake.forwarded["analysis_protocol_id"], "quillframe_corpus_style_learning_v1")
        self.assertEqual(
            fake.forwarded["max_jobs"],
            host_bridge._CORPUS_SEMANTIC_JOB_BUDGET_DEFAULT,
        )
        self.assertEqual(fake.forwarded["semantic_config"]["service_id"], "SERVICE-1")
        self.assertEqual(
            fake.forwarded["semantic_config"]["claim_verification_role"],
            "heldout_semantic_verifier",
        )
        self.assertNotIn("independent", fake.forwarded["semantic_config"])
        self.assertEqual(len(executions), 2)
        self.assertEqual(executions[0]["service_id"], "SERVICE-1")
        self.assertEqual(executions[0]["runtime_role"], "corpus_style_analyst")
        self.assertEqual(executions[0]["model_preference"], "MODEL-ANALYST")
        self.assertEqual(executions[0]["run"]["session_id"], "SES-STYLE-1:analysis")
        self.assertEqual(
            executions[1]["runtime_role"], "corpus_style_heldout_verifier"
        )
        self.assertEqual(executions[1]["model_preference"], "MODEL-HELDOUT")
        self.assertEqual(
            executions[1]["run"]["session_id"],
            "SES-STYLE-1:heldout-verifier",
        )
        self.assertEqual(missing_service["status"], "failed")
        self.assertEqual(missing_service["error"]["code"], "invalid_args")

    def test_style_semantic_job_budget_is_configurable_bounded_and_not_an_independent_gate(self) -> None:
        class BudgetCore:
            def __init__(self) -> None:
                self.forwarded = None

            def corpus_start_study(self, **kwargs):
                kwargs.pop("run_semantic")
                self.forwarded = kwargs
                return {
                    "schema": "quillframe_corpus_study_operation_v1",
                    "study_id": kwargs["study_id"],
                    "status": "awaiting_semantic",
                    "authority": False,
                }

        fake = BudgetCore()
        with (
            patch.object(host_bridge, "ops", return_value=fake),
            patch.object(host_bridge, "agent_runtime", return_value=object()),
            patch.object(host_bridge, "RegisteredSemanticExecutor", lambda runtime: object()),
        ):
            configured = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "execute_semantic": True,
                "max_jobs": 3,
            }))
            too_low = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "execute_semantic": True,
                "max_jobs": 0,
            }))
            boolean = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "execute_semantic": True,
                "max_jobs": True,
            }))
            too_high = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "execute_semantic": True,
                "max_jobs": host_bridge._CORPUS_SEMANTIC_JOB_BUDGET_MAX + 1,
            }))
            mislabeled = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "execute_semantic": True,
                "independent_model_id": "MODEL-NOT-A-GATE",
            }))
            forged_config = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "service_id": "SERVICE-1",
                "execute_semantic": True,
                "semantic_config": {"claim_verification_role": "independent_gate"},
            }))
            budget_without_execution = host_bridge.invoke(request("corpus.study.start", {
                "study_id": "STUDY-SYNTHETIC",
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "execute_semantic": False,
                "max_jobs": 3,
            }))

        self.assertEqual(configured["status"], "ok")
        self.assertEqual(fake.forwarded["max_jobs"], 3)
        self.assertEqual(too_low["status"], "failed")
        self.assertEqual(boolean["status"], "failed")
        self.assertEqual(too_high["status"], "failed")
        self.assertEqual(mislabeled["status"], "failed")
        self.assertEqual(mislabeled["error"]["code"], "invalid_args")
        self.assertEqual(forged_config["status"], "failed")
        self.assertEqual(forged_config["error"]["code"], "invalid_args")
        self.assertEqual(budget_without_execution["status"], "failed")
        self.assertEqual(
            budget_without_execution["error"]["code"], "invalid_args"
        )

    def test_real_core_scan_proposal_and_confirmation_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="quillframe-studio-corpus-") as temporary:
            root = Path(temporary)
            collection = root / "authorized-copies"
            collection.mkdir()
            for index in range(120):
                (collection / f"R18-explicit-work-{index:03d}.txt").write_text(
                    f"Synthetic rights-safe test work {index:03d}.\n", encoding="utf-8"
                )
            core = CoreOperations(QuillframeStore(root / "data"))
            with patch.object(host_bridge, "ops", return_value=core):
                scan = host_bridge.invoke(request("corpus.collection.scan", {
                    "collection_path": str(collection),
                    "rights": {"rights_class": "analysis_only", "rights_basis": "synthetic test fixtures"},
                }))
                self.assertEqual(scan["status"], "ok")
                proposal = host_bridge.invoke(request("corpus.selection.propose", {
                    "collection_id": scan["data"]["collection_id"], "profile": "adult_explicit",
                    "limit": 120, "seed": "studio-test",
                }))
                self.assertEqual(proposal["status"], "ok")
                reloaded = host_bridge.invoke(request("corpus.selection.propose", {
                    "study_id": proposal["data"]["study_id"], "profile": "adult_explicit", "limit": 120,
                }))
                self.assertEqual(reloaded["status"], "ok")
                work_ids = [row["public_work_id"] for row in proposal["data"]["works"]]
                confirmation = host_bridge.invoke(request("corpus.selection.confirm", {
                    "study_id": proposal["data"]["study_id"], "work_ids": work_ids,
                    "proposal_fingerprint": proposal["data"]["proposal_fingerprint"], "profile": proposal["data"]["profile"],
                }))
            self.assertEqual(len(work_ids), 120)
            self.assertEqual(proposal["data"]["profile"], "adult_explicit")
            self.assertEqual(reloaded["data"]["study_id"], proposal["data"]["study_id"])
            self.assertEqual(reloaded["data"]["proposal_fingerprint"], proposal["data"]["proposal_fingerprint"])
            self.assertEqual([row["public_work_id"] for row in reloaded["data"]["works"]], work_ids)
            self.assertTrue(proposal["data"]["private_local_only"])
            self.assertTrue(reloaded["data"]["private_local_only"])
            self.assertTrue(all(row.get("display_label") for row in proposal["data"]["works"]))
            self.assertTrue(all(row.get("display_label") for row in reloaded["data"]["works"]))
            self.assertTrue(all("relative_locator" not in row for row in proposal["data"]["works"]))
            self.assertTrue(all("relative_locator" not in row for row in reloaded["data"]["works"]))
            self.assertEqual(confirmation["status"], "ok")
            self.assertEqual(confirmation["data"]["status"], "confirmed")

    def test_real_core_user_taste_policy_requires_explicit_persisted_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="quillframe-studio-taste-") as temporary:
            core = CoreOperations(QuillframeStore(Path(temporary) / "data"))
            with patch.object(host_bridge, "ops", return_value=core):
                initial = host_bridge.invoke(request("learning.auto_activation_policy.get", {}))
                enabled = host_bridge.invoke(request("learning.auto_activation_policy.set", {"payload": {
                    "enabled": True, "source_kinds": ["feedback", "corpus"],
                    "expected_version": initial["data"]["policy_version"],
                    "authorization_ref": "studio_test_explicit_authorization",
                }}))
                current = host_bridge.invoke(request("learning.auto_activation_policy.get", {}))
            self.assertEqual(initial["status"], "ok")
            self.assertFalse(initial["data"]["enabled"])
            self.assertEqual(enabled["status"], "ok")
            self.assertTrue(current["data"]["enabled"])
            self.assertEqual(current["data"]["source_kinds"], ["corpus", "feedback"])
            self.assertFalse(current["data"]["framework_write"])
            self.assertFalse(current["data"]["canon_write"])

    def test_hosted_web_rejects_every_corpus_local_path_before_core(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            scan = host_bridge.invoke(request("corpus.collection.scan", {"collection_path": r"C:\\books"}, "hosted_web"))
            nested = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "general",
                "metadata": {"source_path": r"C:\\books\\one.epub"}, "limit": 120,
            }, "hosted_web"))
            disguised = host_bridge.invoke(request("corpus.public.validate", {
                "bundle": {"location": r"C:\\books\\preview.json"},
            }, "hosted_web"))
        self.assertEqual(scan["status"], "invalid")
        self.assertEqual(nested["status"], "invalid")
        self.assertEqual(disguised["status"], "invalid")
        self.assertEqual(fake.calls, [])

    def test_scan_flattens_declared_rights_without_forwarding_host_storage_roots(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            result = host_bridge.invoke(request("corpus.collection.scan", {
                "collection_path": r"C:\\books",
                "rights": {"rights_class": "analysis_only", "rights_basis": "licensed private analysis"},
            }))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(fake.calls, [("scan", (r"C:\\books",), {
            "rights_class": "analysis_only", "rights_basis": "licensed private analysis",
        })])

    def test_proposal_is_exactly_120_and_confirmation_binds_membership_and_hash(self) -> None:
        fake = FakeCore()
        work_ids = [f"PW-{index:032x}" for index in range(120)]
        with patch.object(host_bridge, "ops", return_value=fake):
            proposal = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "general", "limit": 120,
            }))
            confirmation = host_bridge.invoke(request("corpus.selection.confirm", {
                "study_id": "STUDY-1", "work_ids": work_ids, "proposal_fingerprint": HASH_A, "profile": "general",
            }))
            mismatched_profile = host_bridge.invoke(request("corpus.selection.confirm", {
                "study_id": "STUDY-1", "work_ids": work_ids, "proposal_fingerprint": HASH_A,
                "profile": "adult_explicit",
            }))
            short = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "general", "limit": 119,
            }))
        self.assertEqual(proposal["status"], "ok")
        self.assertEqual(proposal["data"]["collection_id"], "COL-1")
        self.assertEqual(proposal["data"]["profile"], "general")
        self.assertEqual(proposal["data"]["proposal_fingerprint"], HASH_A)
        self.assertEqual(proposal["data"]["eligibility_counts"], {"excluded": 4, "quarantined": 7})
        self.assertNotIn("exclusion_counts", proposal["data"])
        self.assertEqual(proposal["data"]["works"][0]["display_label"], "Licensed work 000")
        self.assertEqual(proposal["data"]["works"][0]["creator"], "Creator 000")
        self.assertNotIn("relative_locator", proposal["data"]["works"][0])
        self.assertEqual(confirmation["status"], "ok")
        self.assertEqual(mismatched_profile["status"], "failed")
        self.assertEqual(mismatched_profile["error"]["code"], "selection_profile_mismatch")
        self.assertEqual(short["status"], "invalid")
        self.assertIn(("confirm", ("STUDY-1",), {"expected_hash": HASH_A}), fake.calls)

    def test_refresh_rebuilds_only_the_unconfirmed_exact_proposal(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            refreshed = host_bridge.invoke(request("corpus.selection.refresh", {
                "study_id": "STUDY-GENERAL-QUALITY-REBUILD-V5",
                "profile": "general",
                "expected_proposal_hash": HASH_A,
            }))
            malformed = host_bridge.invoke(request("corpus.selection.refresh", {
                "study_id": "STUDY-GENERAL-QUALITY-REBUILD-V5",
                "profile": "general",
                "expected_proposal_hash": "not-a-hash",
            }))
        self.assertEqual(refreshed["status"], "ok")
        self.assertEqual(refreshed["data"]["study_id"], "STUDY-GENERAL-QUALITY-REBUILD-V5")
        self.assertTrue(refreshed["data"]["identity_preserved"])
        self.assertEqual(refreshed["data"]["proposal_fingerprint"], HASH_A)
        self.assertTrue(refreshed["data"]["private_local_only"])
        self.assertTrue(all("relative_locator" not in row for row in refreshed["data"]["works"]))
        self.assertEqual(malformed["status"], "invalid")
        self.assertEqual(
            [call for call in fake.calls if call[0] == "refresh"],
            [("refresh", (), {
                "study_id": "STUDY-GENERAL-QUALITY-REBUILD-V5",
                "profile": "general",
                "expected_proposal_hash": HASH_A,
            })],
        )

    def test_existing_proposal_load_is_identity_bound_and_fail_closed(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            loaded = host_bridge.invoke(request("corpus.selection.propose", {
                "study_id": "STUDY-EXISTING", "profile": "general", "limit": 120,
            }))
        self.assertEqual(loaded["status"], "ok")
        self.assertEqual(loaded["data"]["study_id"], "STUDY-EXISTING")
        self.assertNotIn("collection_id", loaded["data"])
        self.assertEqual(loaded["data"]["works"][0]["display_label"], "Licensed work 000")
        self.assertNotIn("relative_locator", loaded["data"]["works"][0])
        self.assertIn(("propose", (), {"study_id": "STUDY-EXISTING", "profile": "general"}), fake.calls)
        self.assertTrue(any(call[0] == "private" for call in fake.calls))
        self.assertFalse(any(call[0] == "confirm" for call in fake.calls))

        mismatched_study = FakeCore()
        mismatched_study.returned_study_id = "STUDY-OTHER"
        with patch.object(host_bridge, "ops", return_value=mismatched_study):
            result = host_bridge.invoke(request("corpus.selection.propose", {
                "study_id": "STUDY-EXISTING", "profile": "general", "limit": 120,
            }))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "corpus_projection_invalid")
        self.assertFalse(any(call[0] == "private" for call in mismatched_study.calls))

        mismatched_profile = FakeCore()
        mismatched_profile.returned_profile = "adult_explicit"
        with patch.object(host_bridge, "ops", return_value=mismatched_profile):
            result = host_bridge.invoke(request("corpus.selection.propose", {
                "study_id": "STUDY-EXISTING", "profile": "general", "limit": 120,
            }))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "corpus_projection_invalid")
        self.assertFalse(any(call[0] == "private" for call in mismatched_profile.calls))

    def test_existing_proposal_load_never_falls_back_to_creation_when_study_is_missing(self) -> None:
        class MissingStudy(ValueError):
            code = "study_not_found"

        class WrongCorpusRoot(FakeCore):
            def corpus_study_status(self, study_id, **kwargs):
                self.calls.append(("status", (study_id,), kwargs))
                raise MissingStudy("study_not_found")

        fake = WrongCorpusRoot()
        with patch.object(host_bridge, "ops", return_value=fake):
            result = host_bridge.invoke(request("corpus.selection.propose", {
                "study_id": "STUDY-GENERAL-QUALITY-REBUILD-V5",
                "profile": "general",
                "limit": 120,
            }))

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "study_not_found")
        self.assertEqual([call[0] for call in fake.calls], ["status"])

    def test_proposal_requires_exactly_one_typed_identity(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            missing = host_bridge.invoke(request("corpus.selection.propose", {
                "profile": "general", "limit": 120,
            }))
            both = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "study_id": "STUDY-1", "profile": "general", "limit": 120,
            }))
            malformed = host_bridge.invoke(request("corpus.selection.propose", {
                "study_id": {"private": "value"}, "profile": "general", "limit": 120,
            }))
        self.assertEqual(missing["status"], "invalid")
        self.assertEqual(both["status"], "invalid")
        self.assertEqual(malformed["status"], "invalid")
        self.assertEqual(fake.calls, [])

    def test_hosted_proposal_never_calls_or_returns_private_preview(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            hosted = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "adult_explicit", "limit": 120,
            }, "hosted_web"))
            hosted_existing = host_bridge.invoke(request("corpus.selection.propose", {
                "study_id": "STUDY-EXISTING", "profile": "adult_explicit", "limit": 120,
            }, "hosted_web"))
        self.assertEqual(hosted["status"], "ok")
        self.assertEqual(hosted_existing["status"], "ok")
        self.assertEqual(hosted_existing["data"]["study_id"], "STUDY-EXISTING")
        self.assertEqual(hosted["data"]["profile"], "adult_explicit")
        for projection in (hosted["data"], hosted_existing["data"]):
            self.assertNotIn("private_local_only", projection)
            self.assertNotIn("exclusion_counts", projection)
            self.assertEqual(projection["eligibility_counts"], {"excluded": 4, "quarantined": 7})
            self.assertTrue(all("display_label" not in row and "creator" not in row and "relative_locator" not in row
                                for row in projection["works"]))
        self.assertFalse(any(call[0] == "private" for call in fake.calls))
        agent_fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=agent_fake):
            agent = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "general", "limit": 120,
            }, "agent_package"))
        self.assertEqual(agent["status"], "invalid")
        self.assertEqual(agent_fake.calls, [])

    def test_local_proposal_fails_closed_when_private_preview_is_unavailable(self) -> None:
        fake = FakeCore()
        fake.corpus_selection_private_preview = None
        with patch.object(host_bridge, "ops", return_value=fake):
            result = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "general", "limit": 120,
            }))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "corpus_private_preview_unavailable")

    def test_cli_proposal_uses_the_same_private_local_preview_boundary(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            result = host_bridge.invoke(request("corpus.selection.propose", {
                "collection_id": "COL-1", "profile": "general", "limit": 120,
            }, "cli"))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["private_local_only"])
        self.assertTrue(any(call[0] == "private" for call in fake.calls))
        self.assertTrue(all("relative_locator" not in row for row in result["data"]["works"]))

    def test_public_preview_wraps_exact_manifest_and_release_rechecks_it(self) -> None:
        fake = FakeCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            preview = host_bridge.invoke(request("corpus.public.preview", {"study_id": "STUDY-1"}))
            validation = host_bridge.invoke(request("corpus.public.validate", {"bundle": preview["data"]["bundle"]}))
            release = host_bridge.invoke(request("corpus.public.release", {
                "study_id": "STUDY-1", "corpus_version": "v1", "expected_preview_fingerprint": HASH_A,
            }))
        self.assertEqual(preview["status"], "ok")
        self.assertEqual(preview["data"]["preview_fingerprint"], HASH_A)
        self.assertEqual(validation["status"], "ok")
        self.assertEqual(release["status"], "ok")
        self.assertIn(("release", ("STUDY-1",), {
            "release_id": "v1", "preview_token": "preview-token", "manifest_fingerprint": HASH_A,
        }), fake.calls)

    def test_style_atlas_public_operations_require_explicit_protocol_and_never_auto_release(self) -> None:
        style_protocol = "quillframe_corpus_style_learning_v1"

        class StyleCore:
            def __init__(self) -> None:
                self.calls: list[tuple[str, tuple, dict]] = []

            def corpus_preview_public(self, *args, **kwargs):
                self.calls.append(("preview", args, kwargs))
                return {
                    "schema": "quillframe_public_general_style_atlas_preview_v1",
                    "atlas": {
                        "schema": "quillframe_public_general_style_atlas_v1",
                        "atlas_fingerprint": HASH_A,
                    },
                    "release_gates": {"semantic_leakage": {"status": "pending"}},
                    "preview_token": "style-preview-" + "b" * 64,
                    "preview_fingerprint": HASH_A,
                }

            def corpus_validate_public(self, *args, **kwargs):
                self.calls.append(("validate", args, kwargs))
                return {
                    "schema": "quillframe_public_general_style_atlas_validation_v1",
                    "valid": True,
                    "status": "valid",
                    "authority": False,
                }

            def corpus_list_public(self, *args, **kwargs):
                self.calls.append(("list", args, kwargs))
                return {"schema": "quillframe_public_general_style_index_v1", "items": []}

            def corpus_get_public(self, *args, **kwargs):
                self.calls.append(("get", args, kwargs))
                return {
                    "schema": "quillframe_public_general_style_atlas_v1",
                    "atlas_fingerprint": args[0],
                    "authority": False,
                }

            def corpus_release_public(self, *args, **kwargs):
                self.calls.append(("release", args, kwargs))
                raise OperationError(
                    "corpus_style_release_trusted_receipts_required",
                    "trusted receipt resolver is not installed",
                )

        fake = StyleCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            preview = host_bridge.invoke(request("corpus.public.preview", {
                "study_id": "STUDY-1", "analysis_protocol_id": style_protocol,
            }))
            validation = host_bridge.invoke(request("corpus.public.validate", {
                "analysis_protocol_id": style_protocol,
                "bundle": preview["data"]["bundle"],
            }))
            listed = host_bridge.invoke(request("corpus.public.list", {
                "analysis_protocol_id": style_protocol,
            }))
            loaded = host_bridge.invoke(request("corpus.public.get", {
                "analysis_protocol_id": style_protocol, "corpus_version": HASH_A,
            }))
            release = host_bridge.invoke(request("corpus.public.release", {
                "analysis_protocol_id": style_protocol,
                "study_id": "STUDY-1", "corpus_version": HASH_A,
                "expected_preview_fingerprint": HASH_A,
            }))
        self.assertEqual(preview["status"], "ok")
        self.assertEqual(preview["data"]["analysis_protocol_id"], style_protocol)
        self.assertEqual(preview["data"]["bundle"]["atlas_fingerprint"], HASH_A)
        self.assertFalse(preview["data"]["release_performed"])
        self.assertEqual(validation["status"], "ok")
        self.assertEqual(listed["status"], "ok")
        self.assertEqual(loaded["status"], "ok")
        self.assertEqual(release["status"], "failed")
        self.assertEqual(
            release["error"]["code"], "corpus_style_release_trusted_receipts_required"
        )
        self.assertIn(("preview", ("STUDY-1",), {"analysis_protocol_id": style_protocol}), fake.calls)
        self.assertIn(("validate", (preview["data"]["bundle"],), {
            "analysis_protocol_id": style_protocol,
        }), fake.calls)
        self.assertEqual(sum(call[0] == "preview" for call in fake.calls), 1)

    def test_user_taste_policy_and_reversible_transitions_use_delayed_core_services(self) -> None:
        fake = FakeTasteCore()
        with patch.object(host_bridge, "ops", return_value=fake):
            policy = host_bridge.invoke(request("learning.auto_activation_policy.set", {"payload": {
                "enabled": True, "source_kinds": ["feedback"], "expected_version": 0,
                "authorization_ref": "studio_user_explicit_authorization",
            }}))
            paused = host_bridge.invoke(request("learning.user_taste.pause", {
                "hypothesis_id": "UT-1", "expected_version": 3, "reason": "new contradiction",
            }))
            withdrawn = host_bridge.invoke(request("learning.user_taste.withdraw", {
                "hypothesis_id": "UT-2", "expected_version": 2, "reason": "preference changed",
            }))
        self.assertEqual(policy["status"], "ok")
        self.assertEqual(fake.policy_payload["authorization_ref"], "studio_user_explicit_authorization")
        self.assertEqual(paused["status"], "ok")
        self.assertEqual(withdrawn["status"], "ok")
        self.assertEqual(fake.calls, [
            ("pause", {"hypothesis_id": "UT-1", "expected_version": 3, "reason": "new contradiction"}),
            ("withdraw", {"hypothesis_id": "UT-2", "expected_version": 2, "reason": "preference changed"}),
        ])


if __name__ == "__main__":
    unittest.main()
