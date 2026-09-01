"""Mocked-library tests for the recoverable Corpus study runner.

These fixtures execute no model and never place source prose in the real
Corpus library.  The semantic callback returns contract-shaped synthetic
judgments so the tests exercise orchestration, validation, resume, and profile
isolation rather than literary evaluation.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from corpus.library import CorpusLibrary, CorpusLibraryError
from corpus.study_runner import DEFAULT_RESEARCH_AXES, StudyRunner


PASSAGE_SENTINEL = "EPHEMERAL_PASSAGE_SENTINEL_MUST_NOT_REACH_RUNNER_SQLITE"
PRIVATE_TITLE = "PRIVATE_SOURCE_TITLE_MUST_NOT_REACH_RUNNER_SQLITE"
PRIVATE_PATH = "C:/Users/private-owner/library/private-source-title.txt"
HASH = "sha256:" + "a" * 64
SCOPES = ("opening", "middle", "closing")
WORK_IDS = ("PW-" + "1" * 32, "PW-" + "2" * 32)


def _fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _object_fingerprint(value: object) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _semantic_result(job: dict, judgment: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "deterministic_fixture",
            "model_or_reviewer": "unit-test",
        },
        "judgment": judgment,
        "proposals": [],
        "errors": [],
    }


def _contract_id(job: dict) -> str:
    return job["input"]["model_contract_id"]


def _payload(job: dict) -> dict:
    return job["input"]["payload"]


def _wrapped_observation(wrapper: dict) -> dict:
    observation = wrapper.get("observation")
    if not isinstance(observation, dict):
        raise AssertionError("derived observations must use an explicit observation wrapper")
    return observation


def _valid_semantic_result(job: dict, *, profile: str) -> dict:
    contract_id = _contract_id(job)
    payload = _payload(job)
    if contract_id == "corpus.range_observe":
        axis = payload["research_axes"][0]
        judgment = {
            "confidence": 0.9,
            "range_id": payload["range_id"],
            "observations": [
                {
                    "level": "scene",
                    "axis": axis,
                    "mechanism": "a choice changes the immediate pressure",
                    "observed_effect": "the next action follows causally",
                    "conditions": ["the choice has a visible consequence"],
                    "failure_boundary": "a reflective pause may legitimately defer action",
                    "confidence": 0.85,
                }
            ],
            "counterexamples": ["a deliberate pause can preserve tension"],
            "uncertainties": [],
        }
    elif contract_id == "learning.work_synthesize":
        judgment = {
            "confidence": 0.88,
            "public_work_id": payload["public_work_id"],
            "mechanisms": [
                {
                    "axis": payload["research_axes"][0],
                    "mechanism": "consequential scene choice",
                }
            ],
            "counterexamples": [{"boundary": "intentional decompression"}],
            "profile_boundaries": [{"profile": profile}],
            "uncertainties": [],
        }
    elif contract_id == "learning.benchmark_synthesize":
        work_ids = [
            _wrapped_observation(wrapper)["public_work_id"]
            for wrapper in payload["work_observations"]
        ]
        judgment = {
            "confidence": 0.86,
            "benchmarks": [
                {
                    "mechanism": "consequential scene choice",
                    "problem": "a scene can move without changing pressure",
                    "positive_pattern": "a choice changes what the next action can achieve",
                    "failure_boundary": "decompression may defer the consequence",
                    "profiles": [profile],
                    "supporting_work_ids": work_ids,
                    "counterexample_work_ids": [work_ids[-1]],
                    "writer_guidance": "Make causal change available; do not impose a quota.",
                }
            ],
            "contested_questions": [],
        }
    else:  # pragma: no cover - a new contract must receive an explicit fixture.
        raise AssertionError(f"unexpected semantic contract: {contract_id}")
    return _semantic_result(job, judgment)


def _contains_key(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold() in forbidden or _contains_key(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key(child, forbidden) for child in value)
    return False


class FakeLibrary:
    """Minimal CorpusLibrary surface with private material kept in memory."""

    def __init__(self, *, profile: str = "general") -> None:
        self.profile = profile
        self.study_id = "STUDY-UNIT"
        self.public_study_id = "PS-" + "3" * 32
        self.state = "confirmed"
        self.start_calls: list[str] = []
        self.prepare_calls: list[tuple[str, str, dict]] = []
        self.materialize_calls: list[str] = []
        self.complete_calls: list[tuple[str, dict]] = []
        self.analyze_calls: list[tuple[str, str]] = []
        self.cancel_calls: list[str] = []
        self.completion_receipts: list[dict] = []
        self.range_to_work: dict[str, str] = {}
        self._ranges: dict[str, dict] = {}

    def study_status(self, study_id: str, *, include_works: bool = True) -> dict:
        self._require_study(study_id)
        result = {
            "schema": "quillframe_corpus_study_status_v1",
            "study_id": self.study_id,
            "public_study_id": self.public_study_id,
            "profile": self.profile,
            "status": self.state,
            "checklist_hash": HASH,
            "work_count": len(WORK_IDS),
        }
        if include_works:
            result["works"] = [
                {
                    "public_work_id": work_id,
                    "ordinal": ordinal,
                    "source_version": 1,
                    "status": "selected",
                    # A runner must select only public fields, even if a faulty
                    # adapter exposes private metadata beside them.
                    "source_title": PRIVATE_TITLE,
                    "source_path": PRIVATE_PATH,
                }
                for ordinal, work_id in enumerate(WORK_IDS, 1)
            ]
        return result

    def start_study(self, study_id: str) -> dict:
        self._require_study(study_id)
        self.start_calls.append(study_id)
        self.state = "running"
        return self.study_status(study_id, include_works=False)

    def prepare_ranges(
        self,
        study_id: str,
        public_work_id: str,
        *,
        rubric: dict,
        max_chars: int,
    ) -> dict:
        self._require_study(study_id)
        if public_work_id not in WORK_IDS:
            raise AssertionError("unknown fake work")
        self.prepare_calls.append(
            (study_id, public_work_id, {"rubric": copy.deepcopy(rubric), "max_chars": max_chars})
        )
        receipts = []
        for scope in SCOPES:
            range_id = f"RANGE-{public_work_id[-4:]}-{scope}"
            passage = (
                f"{PASSAGE_SENTINEL} {PRIVATE_TITLE} {PRIVATE_PATH} "
                f"Synthetic bounded passage for {scope}."
            )
            receipt = {
                "schema": "quillframe_corpus_range_receipt_v1",
                "range_id": range_id,
                "scope": scope,
                "status": "ready",
                "source_fingerprint": _fingerprint(f"source:{public_work_id}"),
                "passage_fingerprint": _fingerprint(passage),
                "job_fingerprint": _fingerprint(f"job:{range_id}"),
                "judgment_fingerprint": None,
                "rubric": copy.deepcopy(rubric),
                "passage_persisted": False,
            }
            self.range_to_work[range_id] = public_work_id
            self._ranges[range_id] = {"receipt": receipt, "passage": passage}
            receipts.append(copy.deepcopy(receipt))
        return {
            "schema": "quillframe_corpus_ephemeral_range_batch_v1",
            "public_study_id": self.public_study_id,
            "public_work_id": public_work_id,
            "range_count": 3,
            "ranges": receipts,
            "passages_persisted": False,
        }

    def materialize_range(self, range_id: str) -> dict:
        self.materialize_calls.append(range_id)
        data = self._ranges[range_id]
        receipt = data["receipt"]
        passage = data["passage"]
        if len(passage) > 4_000:
            raise AssertionError("fake passage exceeded the semantic contract budget")
        return {
            "schema": "quillframe_corpus_ephemeral_range_v1",
            "range_id": range_id,
            "scope": receipt["scope"],
            "passage": passage,
            "char_count": len(passage),
            "source_fingerprint": receipt["source_fingerprint"],
            "passage_fingerprint": receipt["passage_fingerprint"],
            "rubric": copy.deepcopy(receipt["rubric"]),
            "source_title": PRIVATE_TITLE,
            "source_path": PRIVATE_PATH,
            "persisted": False,
        }

    def complete_range(self, range_id: str, judgment: dict) -> dict:
        self.complete_calls.append((range_id, copy.deepcopy(judgment)))
        receipt = copy.deepcopy(self._ranges[range_id]["receipt"])
        receipt["status"] = "complete"
        receipt["judgment_fingerprint"] = _object_fingerprint(judgment)
        return receipt

    def analyze_work(self, study_id: str, public_work_id: str) -> dict:
        self._require_study(study_id)
        self.analyze_calls.append((study_id, public_work_id))
        if {work_id for _study_id, work_id in self.analyze_calls} == set(WORK_IDS):
            self.state = "complete"
        return self.study_status(study_id, include_works=False)

    def cancel_study(self, study_id: str) -> dict:
        self._require_study(study_id)
        self.cancel_calls.append(study_id)
        self.state = "invalidated"
        return self.study_status(study_id, include_works=False)

    def record_semantic_completion(self, **receipt: object) -> dict:
        self._require_study(str(receipt.get("study_id")))
        if receipt.get("range_job_count") != len(WORK_IDS) * 3:
            raise AssertionError("semantic range count was not exact")
        if receipt.get("work_synthesis_count") != len(WORK_IDS):
            raise AssertionError("work synthesis count was not exact")
        self.completion_receipts.append(copy.deepcopy(receipt))
        return {
            "schema": "quillframe_corpus_semantic_completion_receipt_v1",
            **receipt,
            "status": "complete",
            "receipt_fingerprint": _fingerprint(
                json.dumps(receipt, ensure_ascii=False, sort_keys=True)
            ),
        }

    def _require_study(self, study_id: str) -> None:
        if study_id != self.study_id:
            raise AssertionError(f"unexpected study id: {study_id}")


class RecordingSemantic:
    def __init__(self, *, profile: str) -> None:
        self.profile = profile
        self.jobs: list[dict] = []

    def __call__(self, job: dict) -> dict:
        self.jobs.append(copy.deepcopy(job))
        return _valid_semantic_result(job, profile=self.profile)


class RaiseOnSecondSemantic(RecordingSemantic):
    def __call__(self, job: dict) -> dict:
        self.jobs.append(copy.deepcopy(job))
        if len(self.jobs) == 2:
            raise RuntimeError(
                f"callback failure must not persist {PASSAGE_SENTINEL} {PRIVATE_PATH}"
            )
        return _valid_semantic_result(job, profile=self.profile)


class CorpusStudyRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.db_path = self.root / "runner.sqlite"
        size_patch = patch("corpus.study_runner.STUDY_SIZE", 2)
        size_patch.start()
        self.addCleanup(size_patch.stop)

    def _prepared(self, *, profile: str = "general") -> tuple[StudyRunner, FakeLibrary, str]:
        library = FakeLibrary(profile=profile)
        runner = StudyRunner(self.db_path, library)
        prepared = runner.prepare(library.study_id, run_id=f"RUN-{profile}")
        self.assertEqual(prepared["status"], "prepared")
        self.assertEqual(prepared["profile"], profile)
        self.assertEqual(prepared["work_count"], 2)
        return runner, library, prepared["run_id"]

    def _assert_runner_sqlite_has_no_private_material(self) -> None:
        files = list(self.root.glob(f"{self.db_path.name}*"))
        self.assertTrue(files, "runner SQLite files were not created")
        durable_bytes = b"".join(path.read_bytes() for path in files if path.is_file())
        for forbidden in (PASSAGE_SENTINEL, PRIVATE_TITLE, PRIVATE_PATH):
            self.assertNotIn(forbidden.encode("utf-8"), durable_bytes)

    def test_success_dispatches_three_ephemeral_ranges_per_work_and_safe_synthesis(self) -> None:
        runner, library, run_id = self._prepared()
        semantic = RecordingSemantic(profile="general")

        completed = runner.execute(run_id, semantic)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(runner.status(run_id)["range_states"], {"complete": 6})
        self.assertEqual(library.start_calls, [library.study_id])
        self.assertEqual([call[1] for call in library.prepare_calls], list(WORK_IDS))
        self.assertEqual([call[1] for call in library.analyze_calls], list(WORK_IDS))
        self.assertEqual(len(library.completion_receipts), 1)
        self.assertEqual(library.completion_receipts[0]["range_job_count"], 6)
        self.assertEqual(library.completion_receipts[0]["work_synthesis_count"], 2)

        range_jobs = [job for job in semantic.jobs if _contract_id(job) == "corpus.range_observe"]
        self.assertEqual(len(range_jobs), 6)
        per_work = Counter(
            library.range_to_work[_payload(job)["range_id"]] for job in range_jobs
        )
        self.assertEqual(per_work, Counter({work_id: 3 for work_id in WORK_IDS}))
        for job in range_jobs:
            payload = _payload(job)
            self.assertIn(PASSAGE_SENTINEL, payload["passage"])
            self.assertLessEqual(len(payload["passage"]), 4_000)
            self.assertEqual(payload["research_axes"], list(DEFAULT_RESEARCH_AXES))
            self.assertNotIn("source_fingerprint", payload)

        work_jobs = [job for job in semantic.jobs if _contract_id(job) == "learning.work_synthesize"]
        benchmark_jobs = [
            job for job in semantic.jobs if _contract_id(job) == "learning.benchmark_synthesize"
        ]
        self.assertEqual(len(work_jobs), 2)
        self.assertEqual(len(benchmark_jobs), 1)
        for job in work_jobs:
            payload = _payload(job)
            self.assertFalse(_contains_key(payload, {"passage", "source_fingerprint"}))
            self.assertEqual(len(payload["window_observations"]), 3)
            self.assertTrue(
                all(wrapper["profile"] == "general" for wrapper in payload["window_observations"])
            )
        benchmark_payload = _payload(benchmark_jobs[0])
        self.assertFalse(
            _contains_key(benchmark_payload, {"passage", "source_fingerprint", "passage_fingerprint"})
        )
        self.assertTrue(
            all(wrapper["profile"] == "general" for wrapper in benchmark_payload["work_observations"])
        )

        bundle = completed["candidate_bundle"]
        self.assertFalse(bundle["ingest_ready"])
        self.assertEqual(
            set(bundle["missing_gates"]),
            {
                "standing_policy_authorization_check",
                "semantic_independent_validation",
                "contradiction_gate",
            },
        )
        self.assertTrue(
            all(
                candidate["activation"]
                == "standing_policy_after_semantic_independent_contradiction_gates"
                and candidate["activation_performed"] is False
                for candidate in bundle["private_user_taste_candidates"]
            )
        )
        self.assertTrue(bundle["general_craft_candidate_bundle"]["benchmarks"])
        self.assertEqual(bundle["adult_explicit_candidate_bundle"]["benchmarks"], [])
        self._assert_runner_sqlite_has_no_private_material()

    def test_callback_failure_resumes_without_rerunning_completed_range(self) -> None:
        runner, library, run_id = self._prepared()
        first_attempt = RaiseOnSecondSemantic(profile="general")

        failed = runner.execute(run_id, first_attempt)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "semantic_callback_failed")
        self.assertEqual(len(library.complete_calls), 1)
        completed_range_id = library.complete_calls[0][0]
        self._assert_runner_sqlite_has_no_private_material()

        resumed_semantic = RecordingSemantic(profile="general")
        completed = runner.resume(run_id, resumed_semantic)

        self.assertEqual(completed["status"], "completed")
        all_jobs = first_attempt.jobs + resumed_semantic.jobs
        range_ids = [
            _payload(job)["range_id"]
            for job in all_jobs
            if _contract_id(job) == "corpus.range_observe"
        ]
        self.assertEqual(range_ids.count(completed_range_id), 1)
        self.assertEqual(Counter(range_id for range_id, _judgment in library.complete_calls),
                         Counter({range_id: 1 for range_id in library.range_to_work}))
        self.assertEqual(len(library.analyze_calls), 2)
        self._assert_runner_sqlite_has_no_private_material()

    def test_receipt_failure_never_claims_completed_and_resume_reuses_benchmark(self) -> None:
        runner, library, run_id = self._prepared()
        original_recorder = library.record_semantic_completion
        calls = 0

        def fail_once(**receipt: object) -> dict:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError(f"must not persist {PASSAGE_SENTINEL}")
            return original_recorder(**receipt)

        library.record_semantic_completion = fail_once  # type: ignore[method-assign]
        first_semantic = RecordingSemantic(profile="general")
        failed = runner.execute(run_id, first_semantic)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["benchmark_status"], "complete")
        self.assertEqual(failed["error_code"], "semantic_completion_receipt_failed")
        self.assertNotIn("completion_receipt_fingerprint", failed)

        resumed_semantic = RecordingSemantic(profile="general")
        completed = runner.resume(run_id, resumed_semantic)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(resumed_semantic.jobs, [])
        self.assertEqual(calls, 2)
        self.assertEqual(len(library.completion_receipts), 1)
        self._assert_runner_sqlite_has_no_private_material()

    def test_invalid_semantic_result_fails_closed_before_range_completion(self) -> None:
        runner, library, run_id = self._prepared()
        jobs: list[dict] = []

        def invalid_semantic(job: dict) -> dict:
            jobs.append(copy.deepcopy(job))
            return _semantic_result(
                job,
                {
                    "confidence": 0.9,
                    "range_id": _payload(job)["range_id"],
                    # Required observations/counterexamples/uncertainties are absent.
                },
            )

        failed = runner.execute(run_id, invalid_semantic)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "semantic_result_validation_failed")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(library.complete_calls, [])
        self.assertEqual(library.analyze_calls, [])
        self._assert_runner_sqlite_has_no_private_material()

    def test_adult_explicit_bundle_is_independent_and_never_mixed_into_general(self) -> None:
        runner, _library, run_id = self._prepared(profile="adult_explicit")
        semantic = RecordingSemantic(profile="adult_explicit")

        completed = runner.execute(run_id, semantic)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["profile"], "adult_explicit")
        benchmark_job = next(
            job for job in semantic.jobs if _contract_id(job) == "learning.benchmark_synthesize"
        )
        self.assertTrue(
            all(
                wrapper["profile"] == "adult_explicit"
                for wrapper in _payload(benchmark_job)["work_observations"]
            )
        )
        bundle = completed["candidate_bundle"]
        general = bundle["general_craft_candidate_bundle"]
        adult = bundle["adult_explicit_candidate_bundle"]
        self.assertEqual(general["benchmarks"], [])
        self.assertTrue(adult["benchmarks"])
        self.assertTrue(adult["independent_profile"])
        self.assertFalse(adult["inherits_general_aggregate"])
        self.assertTrue(
            all(benchmark["profiles"] == ["adult_explicit"] for benchmark in adult["benchmarks"])
        )
        self.assertTrue(
            all("general" not in benchmark["profiles"] for benchmark in adult["benchmarks"])
        )
        self.assertTrue(
            all(
                candidate["profile"] == "adult_explicit"
                for candidate in bundle["private_user_taste_candidates"]
            )
        )
        self._assert_runner_sqlite_has_no_private_material()

    def test_adult_explicit_benchmark_rejects_general_profile_mixing(self) -> None:
        runner, _library, run_id = self._prepared(profile="adult_explicit")

        def mixed_profile_semantic(job: dict) -> dict:
            result = _valid_semantic_result(job, profile="adult_explicit")
            if _contract_id(job) == "learning.benchmark_synthesize":
                result["judgment"]["benchmarks"][0]["profiles"] = [
                    "adult_explicit",
                    "general",
                ]
            return result

        failed = runner.execute(run_id, mixed_profile_semantic)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "benchmark_profile_mixing_rejected")
        self.assertNotIn("candidate_bundle", failed)
        self._assert_runner_sqlite_has_no_private_material()

    def test_cancel_updates_runner_and_delegates_to_library(self) -> None:
        runner, library, run_id = self._prepared()

        cancelled = runner.cancel(run_id)

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(library.cancel_calls, [library.study_id])
        self.assertEqual(runner.status(run_id)["status"], "cancelled")

    def test_real_library_runner_receipt_unlocks_preview_validation_and_release(self) -> None:
        sources = self.root / "owned-sources"
        sources.mkdir()
        for index in range(2):
            (sources / f"owned-{index}.txt").write_text(
                f"work {index} opens with a decision.\n\npressure changes in the middle.\n\nthe ending resolves a consequence.",
                encoding="utf-8",
            )
        public_root = self.root / "public"
        shared_db = self.root / "real-corpus.sqlite"
        with (
            patch("corpus.library.STUDY_SIZE", 2),
            patch("corpus.library.GENERAL_MIN_CHARS", 1),
            patch("corpus.study_runner.STUDY_SIZE", 2),
        ):
            library = CorpusLibrary(shared_db, public_root=public_root)
            scan = library.scan_collection(
                sources,
                collection_id="COL-REAL",
                rights_basis="unit-test sources owned by caller",
            )
            bypass_proposed = library.propose_selection(
                "STUDY-BYPASS",
                collection_id=scan["collection_id"],
                seed="fixed",
                profile="general",
            )
            bypass_confirmed = library.confirm_selection(
                bypass_proposed["study_id"],
                expected_hash=bypass_proposed["proposal_hash"],
            )
            with self.assertRaises(CorpusLibraryError) as bypass:
                for work in bypass_confirmed["works"]:
                    library.mark_studied(
                        bypass_confirmed["study_id"],
                        work["public_work_id"],
                        metrics={
                            "sampled_chars": 100,
                            "paragraph_count": 3,
                            "sentence_count": 3,
                            "mean_sentence_chars_milli": 33_333,
                            "dialogue_char_ratio_ppm": 0,
                            "unique_char_ratio_ppm": 500_000,
                            "punctuation_ratio_ppm": 30_000,
                        },
                    )
                library.preview_public(bypass_confirmed["study_id"])
            self.assertEqual(bypass.exception.code, "semantic_completion_receipt_missing")

            proposed = library.propose_selection(
                "STUDY-REAL",
                collection_id=scan["collection_id"],
                seed="fixed",
                profile="general",
            )
            confirmed = library.confirm_selection(
                proposed["study_id"], expected_hash=proposed["proposal_hash"]
            )
            runner = StudyRunner(shared_db, library)
            prepared = runner.prepare(confirmed["study_id"], run_id="RUN-REAL")
            completed = runner.execute(
                prepared["run_id"], RecordingSemantic(profile="general")
            )
            self.assertEqual(completed["status"], "completed")
            self.assertRegex(
                completed["completion_receipt_fingerprint"], r"^sha256:[0-9a-f]{64}$"
            )
            preview = library.preview_public(confirmed["study_id"])
            decision = library.validate_public(preview, study_id=confirmed["study_id"])
            self.assertTrue(decision["valid"], decision["errors"])
            released = library.release_public(
                confirmed["study_id"],
                preview_token=preview["preview_token"],
                manifest_fingerprint=preview["manifest_fingerprint"],
            )
            self.assertEqual(released["status"], "released")
            with closing(sqlite3.connect(shared_db)) as connection:
                connection.execute(
                    "UPDATE study_runs SET completion_receipt_fingerprint=? WHERE run_id=?",
                    ("sha256:" + "0" * 64, prepared["run_id"]),
                )
                connection.commit()
            invalid = library.validate_public(preview, study_id=confirmed["study_id"])
            self.assertFalse(invalid["valid"])
            self.assertIn("semantic_completion_receipt_invalid", invalid["errors"])
            with self.assertRaises(CorpusLibraryError) as tampered_release:
                library.release_public(
                    confirmed["study_id"],
                    preview_token=preview["preview_token"],
                    manifest_fingerprint=preview["manifest_fingerprint"],
                )
            self.assertEqual(
                tampered_release.exception.code, "semantic_completion_receipt_invalid"
            )


if __name__ == "__main__":
    unittest.main()
