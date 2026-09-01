"""Focused Core/CLI/packaging tests for Corpus and user-taste adapters."""
from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
import tomllib
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import persistence.quillframe_sqlite as sqlite_runtime
from core_operations import CoreOperations, OperationError
from learning.learning_store import LearningStore
from persistence.quillframe_sqlite import QuillframeStore, RestoreIncompleteError
from quillframe import cli


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_EVIDENCE_SENTINEL = "PRIVATE_EVIDENCE_PAYLOAD_MUST_NOT_REACH_CLI"
ABSTRACT_PREFERENCE_FIELDS = {
    "hypothesis_id",
    "scope",
    "project_id",
    "dimension",
    "statement",
    "mechanism",
    "state",
    "confidence",
    "applicability",
    "evidence_ids",
    "contradiction_ids",
    "version",
}


def _seed_user_taste_preference(db_path: Path, *, hypothesis_id: str = "PH-PRIVATE") -> None:
    learning = LearningStore(db_path)
    learning.init()
    learning.add_evidence(
        {
            "evidence_id": "PE-PRIVATE",
            "subject_scope": "user_taste",
            "source": "human_review",
            "polarity": "positive",
            "observed_problem": PRIVATE_EVIDENCE_SENTINEL,
            "mechanism": "delay scene answers until a character choice changes the stakes",
            "user_words_or_reference": PRIVATE_EVIDENCE_SENTINEL,
            "artifact_ref": "C:/private/novel-copy.txt",
            "artifact_fingerprint": "sha256:" + "a" * 64,
            "raw_text": PRIVATE_EVIDENCE_SENTINEL,
            "confidence": 0.9,
        }
    )
    learning.upsert_hypothesis(
        {
            "hypothesis_id": hypothesis_id,
            "subject_scope": "user_taste",
            "dimension": "scene_tension",
            "statement": "Prefer delayed answers when choices can change the stakes.",
            "mechanism": "delay scene answers until a character choice changes the stakes",
            "state": "active",
            "confidence": 0.9,
            "evidence_ids": ["PE-PRIVATE"],
            "contradiction_ids": [],
            "applicability": {"scene_types": ["confrontation"]},
        },
        expected_version=0,
    )


class CorpusCoreAdapterTests(unittest.TestCase):
    @staticmethod
    def _project_corpus_runner(runner: dict) -> dict:
        return CoreOperations._corpus_study_projection(
            "status",
            {
                "study_id": "STUDY-1",
                "public_study_id": "PS-" + "1" * 32,
                "profile": "general",
                "status": "confirmed",
                "work_count": 120,
            },
            runner,
            performed=False,
            semantic_execution_performed=False,
        )

    def test_style_projection_exposes_dynamic_cohort_counts_without_semantic_claims(self) -> None:
        runner = {
            "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
            "status": "running",
            "work_count": 120,
            "work_states": {"pending": 105, "running": 6, "complete": 9},
            "cohort_states": {
                "available_unanalysed": 105,
                "activated": 6,
                "analysed": 9,
            },
            "semantic_attempts": 14,
        }
        first = self._project_corpus_runner(runner)
        self.assertEqual(
            first["progress"],
            {
                "completed": 9,
                "total": 120,
                "compatibility_work_count": 120,
                "available_pool_count": 105,
                "activated_count": 6,
                "analysed_count": 9,
                "semantic_attempts": 14,
            },
        )
        self.assertFalse(
            {"evidence_coverage", "coverage", "convergence"}.intersection(
                first["progress"]
            )
        )

        runner["cohort_states"] = {
            "available_unanalysed": 98,
            "activated": 4,
            "analysed": 18,
        }
        runner["semantic_attempts"] = 27
        second = self._project_corpus_runner(runner)
        self.assertEqual(second["progress"]["available_pool_count"], 98)
        self.assertEqual(second["progress"]["activated_count"], 4)
        self.assertEqual(second["progress"]["analysed_count"], 18)
        self.assertEqual(second["progress"]["completed"], 18)
        self.assertEqual(second["progress"]["semantic_attempts"], 27)

    def test_old_style_and_legacy_runner_progress_shapes_remain_compatible(self) -> None:
        old_style = self._project_corpus_runner(
            {
                "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
                "status": "prepared",
                "work_count": 12,
                "work_states": {"pending": 10, "complete": 2},
                "semantic_attempts": 3,
            }
        )
        self.assertEqual(old_style["progress"], {"completed": 2, "total": 12})

        legacy = self._project_corpus_runner(
            {
                "analysis_protocol_id": "quillframe_corpus_three_window_benchmark_v1",
                "status": "running",
                "work_count": 8,
                "work_states": {"pending": 5, "complete": 3},
                # A similarly named extension on another protocol must not
                # silently change its established Core projection.
                "cohort_states": {"unrelated": "legacy-owned"},
            }
        )
        self.assertEqual(legacy["progress"], {"completed": 3, "total": 8})

    def test_style_projection_rejects_unverified_or_open_cohort_count_types(self) -> None:
        valid = {
            "analysis_protocol_id": "quillframe_corpus_style_learning_v1",
            "status": "running",
            "work_count": 20,
            "work_states": {"pending": 15, "complete": 3},
            "cohort_states": {
                "available_unanalysed": 15,
                "activated": 2,
                "analysed": 3,
            },
            "semantic_attempts": 5,
        }
        invalid_runners = []

        not_a_mapping = copy.deepcopy(valid)
        not_a_mapping["cohort_states"] = []
        invalid_runners.append(not_a_mapping)

        open_mapping = copy.deepcopy(valid)
        open_mapping["cohort_states"]["converged"] = True
        invalid_runners.append(open_mapping)

        for field, value in (
            ("available_unanalysed", True),
            ("activated", "2"),
            ("analysed", -1),
        ):
            invalid = copy.deepcopy(valid)
            invalid["cohort_states"][field] = value
            invalid_runners.append(invalid)

        invalid_work_count = copy.deepcopy(valid)
        invalid_work_count["work_count"] = 20.0
        invalid_runners.append(invalid_work_count)

        invalid_attempts = copy.deepcopy(valid)
        invalid_attempts["semantic_attempts"] = False
        invalid_runners.append(invalid_attempts)

        inconsistent_partition = copy.deepcopy(valid)
        inconsistent_partition["cohort_states"]["available_unanalysed"] = 14
        invalid_runners.append(inconsistent_partition)

        for runner in invalid_runners:
            with self.subTest(runner=runner), self.assertRaises(OperationError) as caught:
                self._project_corpus_runner(runner)
            self.assertEqual(caught.exception.code, "corpus_runner_progress_invalid")

    def test_posix_lock_module_is_optional_and_native_restore_fails_closed(self) -> None:
        with patch.object(sqlite_runtime, "fcntl", None):
            with self.assertRaises(RestoreIncompleteError) as caught:
                QuillframeStore._restore_open_lock(-1, "BOOK")
        self.assertEqual(caught.exception.code, "restore_native_unavailable")

    def test_corpus_service_is_lazy_and_forwards_exact_calls(self) -> None:
        calls: list[tuple[object, ...]] = []

        class FakeCorpusLibrary:
            def __init__(self, db_path, public_root=None):
                calls.append(("init", db_path, public_root))
                self.db_path = Path(db_path)

            def scan_collection(self, *args, **kwargs):
                calls.append(("scan", args, kwargs))
                return {"schema": "scan"}

            def propose_selection(self, *args, **kwargs):
                calls.append(("propose", args, kwargs))
                return {"schema": "propose"}

            def confirm_selection(self, *args, **kwargs):
                return {"schema": "confirm"}

            def selection_private_preview(self, *args, **kwargs):
                calls.append(("private_preview", args, kwargs))
                return {"schema": "private-preview", "private_local_only": True}

            def study_status(self, *args, **kwargs):
                return {
                    "schema": "quillframe_corpus_study_status_v1",
                    "study_id": args[0] if args else kwargs.get("study_id"),
                    "public_study_id": "PS-" + "1" * 32,
                    "profile": "general",
                    "status": "confirmed",
                    "work_count": 120,
                    "work_states": {"selected": 120},
                }

            def preview_public(self, *args, **kwargs):
                return {"schema": "preview"}

            def validate_public(self, *args, **kwargs):
                return {"schema": "validate"}

            def release_public(self, *args, **kwargs):
                calls.append(("release", args, kwargs))
                return {"schema": "release"}

            def list_public(self, *args, **kwargs):
                return {"schema": "list"}

            def get_public(self, *args, **kwargs):
                return {"schema": "get"}

        module = types.ModuleType("corpus.library")
        module.CorpusLibrary = FakeCorpusLibrary
        runner_module = types.ModuleType("corpus.study_runner")

        class FakeStudyRunner:
            def __init__(self, db_path, library):
                calls.append(("runner_init", db_path, library.db_path))

            @classmethod
            def inspect_for_study(cls, db_path, study_id):
                return None

            def prepare(self, study_id, **kwargs):
                calls.append(("prepare", study_id, kwargs))
                return {
                    "schema": "quillframe_corpus_study_runner_status_v1",
                    "run_id": "RUN-1",
                    "study_id": study_id,
                    "status": "prepared",
                    "work_count": 120,
                    "work_states": {"pending": 120},
                }

        runner_module.StudyRunner = FakeStudyRunner
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            sys.modules, {"corpus.library": module, "corpus.study_runner": runner_module}
        ):
            root = Path(temporary)
            operations = CoreOperations(QuillframeStore(root))
            result = operations.corpus_scan_collection("collection", language="zh-CN")
            self.assertEqual(result["schema"], "scan")
            self.assertEqual(calls[0], ("init", root / "corpus" / "corpus.sqlite", None))
            self.assertEqual(calls[1], ("scan", ("collection",), {"language": "zh-CN"}))
            private_preview = operations.corpus_selection_private_preview("STUDY-1")
            self.assertEqual(private_preview["schema"], "private-preview")
            self.assertTrue(private_preview["private_local_only"])

            awaiting = operations.corpus_start_study(study_id="STUDY-1")
            self.assertEqual(awaiting["status"], "awaiting_semantic")
            self.assertTrue(awaiting["performed"])
            self.assertFalse(awaiting["semantic_execution_performed"])
            self.assertEqual(awaiting["runner"]["status"], "prepared")
            self.assertFalse(awaiting["authority_granted"])

            with self.assertRaises(OperationError) as caught:
                operations.corpus_release_public(release_id="PUB-1")
            self.assertEqual(caught.exception.code, "corpus_release_confirmation_required")
            released = operations.corpus_release_public(
                release_id="PUB-1",
                preview_token="preview-token",
                manifest_fingerprint="sha256:" + "1" * 64,
            )
            self.assertEqual(released["schema"], "release")
            self.assertEqual(calls[-1][2]["preview_token"], "preview-token")

    def test_corpus_default_root_is_independent_from_project_data_when_configured(self) -> None:
        calls: list[tuple[Path, object]] = []

        class FakeCorpusLibrary:
            def __init__(self, db_path, public_root=None):
                calls.append((Path(db_path), public_root))
                self.db_path = Path(db_path)

        module = types.ModuleType("corpus.library")
        module.CorpusLibrary = FakeCorpusLibrary
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            sys.modules, {"corpus.library": module}
        ):
            root = Path(temporary)
            project_data = root / "project" / ".quillframe" / "data"
            user_corpus = root / "user-data" / "corpus"
            with patch.dict(
                os.environ, {"QUILLFRAME_CORPUS_DIR": str(user_corpus)}
            ):
                operations = CoreOperations(QuillframeStore(project_data))
                operations.corpus_library()
                explicit = root / "explicit" / "corpus.sqlite"
                operations.corpus_library(db_path=explicit)

        self.assertEqual(calls[0], (user_corpus.resolve() / "corpus.sqlite", None))
        self.assertEqual(calls[1], (explicit.resolve(), None))

    def test_user_taste_service_uses_existing_author_database_and_forwards_policy(self) -> None:
        calls: list[tuple[object, ...]] = []

        class FakeUserTasteService:
            def __init__(self, db_path):
                calls.append(("init", db_path))

            def get_policy(self):
                return {"schema": "policy"}

            def set_policy(self, payload):
                calls.append(("set", payload))
                return {"schema": "policy-set"}

            def list_preferences(self, state=None):
                return {"schema": "preferences", "state": state}

            def get_preference(self, preference_id):
                return {"schema": "preference", "id": preference_id}

        module = types.ModuleType("learning.user_taste")
        module.UserTasteService = FakeUserTasteService
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            sys.modules, {"learning.user_taste": module}
        ):
            root = Path(temporary)
            operations = CoreOperations(QuillframeStore(root))
            result = operations.user_taste_set_policy({"enabled": True})
            self.assertEqual(result["schema"], "policy-set")
            self.assertEqual(calls[0], ("init", root / "learning" / "author.sqlite"))
            self.assertEqual(calls[1], ("set", {"enabled": True}))
            self.assertEqual(
                operations.user_taste_list_preferences(state="active")["state"], "active"
            )

    def test_real_user_taste_policy_remains_user_scoped_and_reuses_author_db(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            operations = CoreOperations(QuillframeStore(root))
            policy = operations.user_taste_get_policy()
            self.assertFalse(policy["enabled"])
            self.assertEqual(policy["authority_scope"], "user_taste_only")
            updated = operations.user_taste_set_policy(
                {"enabled": True, "authorization_ref": "user:test", "expected_version": 0}
            )
            self.assertTrue(updated["enabled"])
            self.assertFalse(updated["framework_write"])
            self.assertFalse(updated["canon_write"])
            self.assertEqual(operations.user_taste_list_preferences(), [])
            self.assertTrue((root / "learning" / "author.sqlite").is_file())
            self.assertFalse((root / "learning" / "user-taste.sqlite").exists())

    def test_user_taste_pause_withdraw_transitions_and_stale_cas_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            db_path = root / "learning" / "author.sqlite"
            _seed_user_taste_preference(db_path)
            operations = CoreOperations(QuillframeStore(root))

            paused = operations.user_taste_pause_preference(
                "PH-PRIVATE", expected_version=1, reason="pause while preference is reviewed"
            )
            self.assertEqual(paused["preference"]["state"], "contested")
            self.assertEqual(paused["preference"]["version"], 2)
            self.assertEqual(paused["receipt"]["action"], "pause")

            with self.assertRaisesRegex(ValueError, "preference version mismatch"):
                operations.user_taste_withdraw_preference(
                    "PH-PRIVATE", expected_version=1, reason="stale withdrawal must fail"
                )
            after_stale_write = operations.user_taste_get_preference("PH-PRIVATE")
            self.assertEqual(after_stale_write["state"], "contested")
            self.assertEqual(after_stale_write["version"], 2)

            withdrawn = operations.user_taste_withdraw_preference(
                "PH-PRIVATE", expected_version=2, reason="user withdrew this preference"
            )
            self.assertEqual(withdrawn["preference"]["state"], "deprecated")
            self.assertEqual(withdrawn["preference"]["version"], 3)
            self.assertEqual(withdrawn["receipt"]["action"], "withdraw")


class CorpusCliTests(unittest.TestCase):
    def _run(self, argv: list[str], fake) -> tuple[int, dict]:
        stream = io.StringIO()
        with patch.object(cli, "_core", return_value=fake), redirect_stdout(stream):
            result = cli.main(argv)
        return result, json.loads(stream.getvalue())

    def test_nested_corpus_cli_forwards_json_and_release_confirmation(self) -> None:
        class FakeOperations:
            def corpus_scan_collection(self, collection, **kwargs):
                return {"collection": collection, "kwargs": kwargs}

            def corpus_release_public(self, **kwargs):
                return {"release": kwargs}

        code, output = self._run(
            ["corpus", "--db-path", "corpus.sqlite", "scan", "C:/books", "--payload", '{"language":"zh-CN"}'],
            FakeOperations(),
        )
        self.assertEqual(code, 0)
        self.assertEqual(output["collection"], "C:/books")
        self.assertEqual(output["kwargs"]["language"], "zh-CN")
        self.assertEqual(output["kwargs"]["db_path"], "corpus.sqlite")

        code, output = self._run(
            [
                "corpus", "public", "release", "--payload",
                '{"preview_token":"token","manifest_fingerprint":"sha256:abc"}',
            ],
            FakeOperations(),
        )
        self.assertEqual(code, 0)
        self.assertEqual(output["release"]["preview_token"], "token")

    def test_study_cli_invokes_adapter_only_with_explicit_execute_semantic(self) -> None:
        calls: list[dict] = []

        class FakeOperations:
            def corpus_start_study(self, **kwargs):
                calls.append(kwargs)
                return {
                    "schema": "quillframe_corpus_study_operation_v1",
                    "status": "awaiting_semantic",
                    "semantic_execution_performed": callable(kwargs.get("run_semantic")),
                }

        code, output = self._run(
            ["corpus", "study", "start", "--payload", '{"study_id":"STUDY-1"}'],
            FakeOperations(),
        )
        self.assertEqual(code, 0)
        self.assertFalse(output["semantic_execution_performed"])
        self.assertNotIn("run_semantic", calls[-1])

        from harness.semantic_workers import semantic_worker_runner

        with patch.object(
            semantic_worker_runner, "resolve", return_value=("safe-adapter", "cli")
        ):
            code, output = self._run(
                [
                    "corpus", "study", "start", "--payload",
                    '{"study_id":"STUDY-1","execute_semantic":true}',
                ],
                FakeOperations(),
            )
        self.assertEqual(code, 0)
        self.assertTrue(output["semantic_execution_performed"])
        self.assertTrue(callable(calls[-1]["run_semantic"]))

    def test_user_taste_policy_cli_passes_payload_as_policy_not_authority(self) -> None:
        class FakeOperations:
            def user_taste_set_policy(self, payload, **kwargs):
                return {"payload": payload, "kwargs": kwargs, "authority": False}

        code, output = self._run(
            ["user-taste", "policy", "set", "--payload", '{"allow_durable_learning":true}'],
            FakeOperations(),
        )
        self.assertEqual(code, 0)
        self.assertEqual(output["payload"], {"allow_durable_learning": True})
        self.assertFalse(output["authority"])

    def test_pause_and_withdraw_cli_require_and_forward_cas_inputs(self) -> None:
        calls: list[tuple[object, ...]] = []

        class FakeOperations:
            @staticmethod
            def _result(action: str, version: int) -> dict:
                return {
                    "preference": {
                        "hypothesis_id": "PH-1",
                        "scope": "user_taste",
                        "state": "contested" if action == "pause" else "deprecated",
                        "version": version + 1,
                        "raw_text": PRIVATE_EVIDENCE_SENTINEL,
                        "evidence_payload": {"text": PRIVATE_EVIDENCE_SENTINEL},
                    },
                    "receipt": {
                        "action": action,
                        "before_version": version,
                        "after_version": version + 1,
                        "payload_json": PRIVATE_EVIDENCE_SENTINEL,
                    },
                }

            def user_taste_pause_preference(self, preference_id, **kwargs):
                calls.append(("pause", preference_id, kwargs))
                return self._result("pause", kwargs["expected_version"])

            def user_taste_withdraw_preference(self, preference_id, **kwargs):
                calls.append(("withdraw", preference_id, kwargs))
                return self._result("withdraw", kwargs["expected_version"])

        fake = FakeOperations()
        code, paused = self._run(
            [
                "user-taste", "--db-path", "author.sqlite", "pause", "PH-1",
                "--expected-version", "7", "--reason", "review requested",
            ],
            fake,
        )
        self.assertEqual(code, 0)
        self.assertEqual(paused["preference"]["state"], "contested")
        self.assertEqual(calls[0][2]["expected_version"], 7)
        self.assertEqual(calls[0][2]["reason"], "review requested")

        code, withdrawn = self._run(
            [
                "user-taste", "withdraw", "PH-1", "--expected-version", "8",
                "--reason", "preference withdrawn",
            ],
            fake,
        )
        self.assertEqual(code, 0)
        self.assertEqual(withdrawn["preference"]["state"], "deprecated")
        self.assertEqual(calls[1][2]["expected_version"], 8)
        self.assertNotIn(PRIVATE_EVIDENCE_SENTINEL, json.dumps([paused, withdrawn]))

    def test_real_cli_lists_only_abstract_preferences_not_evidence_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            db_path = root / "learning" / "author.sqlite"
            _seed_user_taste_preference(db_path)
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = cli.main(
                    [
                        "user-taste", "--data-dir", str(root / "runtime"),
                        "--db-path", str(db_path), "list",
                    ]
                )
            serialized = stream.getvalue()
            output = json.loads(serialized)
            self.assertEqual(code, 0)
            self.assertEqual(len(output), 1)
            self.assertEqual(set(output[0]), ABSTRACT_PREFERENCE_FIELDS)
            self.assertEqual(output[0]["evidence_ids"], ["PE-PRIVATE"])
            self.assertNotIn(PRIVATE_EVIDENCE_SENTINEL, serialized)
            self.assertNotIn("payload_json", serialized)
            self.assertNotIn("user_words_or_reference", serialized)
            self.assertNotIn("artifact_ref", serialized)
            self.assertNotIn("raw_text", serialized)


class CorpusPackagingTests(unittest.TestCase):
    def test_corpus_namespace_and_general_schema_resources_are_declared(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        include = config["tool"]["setuptools"]["packages"]["find"]["include"]
        package_data = config["tool"]["setuptools"]["package-data"]
        self.assertIn("corpus*", include)
        self.assertIn("corpus", package_data)
        self.assertIn("**/*.json", package_data["corpus"])


if __name__ == "__main__":
    unittest.main()
