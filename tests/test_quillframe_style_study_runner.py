"""Synthetic-only tests for :mod:`corpus.style_study_runner`.

The fake library keeps its generated passages in memory.  No test reads a
real corpus work, and the runner database is checked for prose leakage after
both successful and interrupted execution.
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

from corpus.style_contract import STYLE_AXES
from corpus.style_sampling import STYLE_SAMPLE_ROLES, fingerprint_source_text, sample_style_windows
from corpus.style_study_runner import (
    DEFAULT_AXIS_BATCH_SIZE,
    STYLE_CONTRACT_IDS,
    StyleStudyRunner,
    StyleStudyRunnerError,
)


PASSAGE_SENTINEL = "SYNTHETIC_STYLE_PASSAGE_SENTINEL"
APPEARANCE_SENTINEL = "巨乳"
FORBIDDEN_SOURCE_KEYS = {
    "passage",
    "excerpt",
    "quote",
    "raw",
    "raw_text",
    "source_text",
    "source_prose",
    "full_text",
    "source_title",
    "work_title",
    "book_title",
    "creator",
    "author",
    "local_path",
    "source_path",
    "file_path",
    "filepath",
    "filename",
    "relative_path",
    "relative_locator",
}


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _synthetic_work_text(work_id: str) -> str:
    """Return deliberately artificial prose unique to one opaque work ID."""

    return f"""第一章 合成开端
{PASSAGE_SENTINEL}-{work_id} 她在镜前整理长发，外套掩住丰满身材与{APPEARANCE_SENTINEL}。
***
“现在出发。”朋友说，“我仍然信任你。”
***
随后，她转身冲下楼梯，推开测试用的蓝色门。
***
她想起多年前的约定，也意识到自己仍有疑问。
***
雨水敲着空房间的窗，冷风掠过无人的街道。
尾声
合成人物回到原处，本段只用于确定性单元测试。
"""


def _synthetic_checklist_hash(
    profile: str, work_ids: tuple[str, ...], texts: dict[str, str]
) -> str:
    material = {
        "profile": profile,
        "works": [
            {
                "public_work_id": work_id,
                "source_version": 1,
                "source_fingerprint": fingerprint_source_text(texts[work_id]),
            }
            for work_id in work_ids
        ],
    }
    encoded = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _semantic_result(job: dict, judgment: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "deterministic_fixture",
            "model_or_reviewer": "synthetic-unit-test",
        },
        "judgment": judgment,
        "proposals": [],
        "errors": [],
    }


def _contract_id(job: dict) -> str:
    return job["input"]["model_contract_id"]


def _payload(job: dict) -> dict:
    return job["input"]["payload"]


def _contains_key(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold().replace("-", "_") in forbidden
            or _contains_key(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key(child, forbidden) for child in value)
    return False


class FakeStyleLibrary:
    """Minimum style-study surface with all private prose kept in memory."""

    def __init__(self, *, work_count: int = 6, profile: str = "general") -> None:
        self.study_id = "STUDY-STYLE-UNIT"
        self.public_study_id = "PS-" + "4" * 32
        self.profile = profile
        self.state = "confirmed"
        self.work_ids = tuple(f"PW-{index:032x}" for index in range(1, work_count + 1))
        self._texts = {
            work_id: _synthetic_work_text(work_id) for work_id in self.work_ids
        }
        self.checklist_hash = _synthetic_checklist_hash(
            self.profile, self.work_ids, self._texts
        )
        self.start_calls: list[str] = []
        self.cancel_calls: list[str] = []
        self.sample_calls: list[dict] = []
        self.materialize_calls: list[dict] = []
        self.leakage_calls: list[str] = []
        self.verify_calls: list[str] = []
        self.completion_receipts: list[dict] = []

    def study_status(self, study_id: str, *, include_works: bool = True) -> dict:
        self._require_study(study_id)
        result = {
            "schema": "quillframe_corpus_study_status_v1",
            "study_id": self.study_id,
            "public_study_id": self.public_study_id,
            "profile": self.profile,
            "status": self.state,
            "checklist_hash": self.checklist_hash,
            "work_count": len(self.work_ids),
        }
        if include_works:
            result["works"] = [
                {"public_work_id": work_id, "study_ordinal": ordinal}
                for ordinal, work_id in enumerate(self.work_ids, 1)
            ]
        return result

    def start_study(self, study_id: str) -> dict:
        self._require_study(study_id)
        self.start_calls.append(study_id)
        self.state = "running"
        return self.study_status(study_id)

    def cancel_study(self, study_id: str) -> dict:  # pragma: no cover - must never run
        self._require_study(study_id)
        self.cancel_calls.append(study_id)
        self.state = "invalidated"
        return self.study_status(study_id)

    def sample_style_work(
        self,
        study_id: str,
        public_work_id: str,
        *,
        requested_roles: list[str],
        max_windows: int,
        prior_manifest: dict | None,
    ) -> dict:
        self._require_work(study_id, public_work_id)
        text = self._texts[public_work_id]
        self.sample_calls.append(
            {
                "public_work_id": public_work_id,
                "requested_roles": list(requested_roles),
                "max_windows": max_windows,
                "prior_manifest_fingerprint": None
                if prior_manifest is None
                else prior_manifest["manifest_fingerprint"],
            }
        )
        result = sample_style_windows(
            text,
            source_fingerprint=fingerprint_source_text(text),
            requested_roles=requested_roles,
            max_windows=max_windows,
            target_window_chars=64,
            max_window_chars=96,
            max_overlap_ratio=0.1,
            prior_manifest=prior_manifest,
        )
        return {
            **result,
            "upstream_source_fingerprint": _hash_text(
                "upstream-fixture:" + public_work_id
            ),
        }

    def materialize_style_window(
        self, study_id: str, public_work_id: str, descriptor: dict
    ) -> dict:
        self._require_work(study_id, public_work_id)
        text = self._texts[public_work_id]
        start, end = descriptor["span"]["start"], descriptor["span"]["end"]
        passage = text[start:end]
        self.materialize_calls.append(
            {
                "public_work_id": public_work_id,
                "window_id": descriptor["window_id"],
                "passage_fingerprint": descriptor["passage_fingerprint"],
            }
        )
        if descriptor["source_fingerprint"] != fingerprint_source_text(text):
            raise AssertionError("style source binding changed")
        if descriptor["passage_fingerprint"] != fingerprint_source_text(passage):
            raise AssertionError("style passage binding changed")
        return {
            "schema": "quillframe_corpus_ephemeral_style_window_v1",
            "passage": passage,
            "source_fingerprint": descriptor["source_fingerprint"],
            "passage_fingerprint": descriptor["passage_fingerprint"],
            "paragraph_spans": [
                {
                    "span_ref": "SPAN-" + descriptor["window_id"].removeprefix(
                        "style-window-"
                    ),
                    "start": 0,
                    "end": len(passage),
                }
            ],
            "persisted": False,
        }

    def style_leakage_reference_batches(
        self, study_id: str, *, public_work_ids: list[str]
    ) -> list[dict[str, str]]:
        self._require_study(study_id)
        self.leakage_calls.append(study_id)
        if not public_work_ids or not set(public_work_ids).issubset(self.work_ids):
            raise AssertionError("invalid used cohort")
        return [
            {
                "REF-SYNTHETIC-1": (
                    "这是一段只用于泄漏校验的独立占位材料，词汇与所有候选机制完全不同。"
                )
                * 3
            }
        ]

    def record_style_completion(self, **receipt: object) -> dict:
        self._require_study(str(receipt.get("study_id")))
        self.completion_receipts.append(copy.deepcopy(receipt))
        return {
            "schema": "quillframe_corpus_style_completion_receipt_v1",
            **receipt,
        }

    def verify_style_source_dependency(
        self,
        study_id: str,
        public_work_id: str,
        *,
        version_id: str,
        source_sha256: str,
    ) -> dict:
        self._require_work(study_id, public_work_id)
        self.verify_calls.append(public_work_id)
        actual = hashlib.sha256(self._texts[public_work_id].encode("utf-8")).hexdigest()
        if source_sha256 != actual:
            raise ValueError("synthetic_source_dependency_drift")
        return {
            "schema": "quillframe_corpus_style_source_dependency_receipt_v1",
            "public_work_id": public_work_id,
            "version_id": version_id,
            "source_fingerprint": "sha256:" + actual,
            "dependency_fingerprint": _hash_text(
                public_work_id + "\0" + version_id + "\0" + actual
            ),
            "source_prose_included": False,
            "authority": False,
        }

    def _require_study(self, study_id: str) -> None:
        if study_id != self.study_id:
            raise AssertionError(f"unexpected study: {study_id}")

    def _require_work(self, study_id: str, public_work_id: str) -> None:
        self._require_study(study_id)
        if public_work_id not in self._texts:
            raise AssertionError(f"unexpected work: {public_work_id}")


class RecordingStyleSemantic:
    """Registered-contract fixture that emits source-free deterministic results."""

    def __init__(
        self,
        *,
        profile: str = "general",
        continue_first_round: bool = False,
        continue_coverage_gaps: list[str] | None = None,
        emit_claims: bool = True,
        reconcile_convergence: str = "converged",
        reconcile_work_id_override: str | None = None,
        reconcile_scene_functions_by_axis: dict[str, list[str]] | None = None,
        fail_on_call: int | None = None,
    ) -> None:
        self.profile = profile
        self.continue_first_round = continue_first_round
        self.continue_coverage_gaps = (
            ["body_appearance"]
            if continue_coverage_gaps is None
            else list(continue_coverage_gaps)
        )
        self.emit_claims = emit_claims
        self.reconcile_convergence = reconcile_convergence
        self.reconcile_work_id_override = reconcile_work_id_override
        self.reconcile_scene_functions_by_axis = reconcile_scene_functions_by_axis or {}
        self.fail_on_call = fail_on_call
        self.jobs: list[dict] = []

    def __call__(self, job: dict) -> dict:
        self.jobs.append(copy.deepcopy(job))
        if self.fail_on_call == len(self.jobs):
            raise RuntimeError("synthetic callback interruption")
        contract_id = _contract_id(job)
        payload = _payload(job)

        if contract_id == "corpus.style_observe":
            span_ref = payload["paragraph_spans"][0]["span_ref"]
            axis = (
                "body_appearance"
                if payload["retrieval_scene_function_hint"] == "opening"
                else "syntax_rhythm"
            )
            judgment = {
                "confidence": 0.83,
                "style_range_id": payload["style_range_id"],
                # Deliberately disagree with the retrieval hint.  Downstream
                # synthesis must consume this model classification.
                "observed_scene_functions": ["relationship"],
                "observations": [
                    {
                        "axis": axis,
                        "level": "paragraph",
                        "operation": "Select concrete viewpoint-owned detail",
                        "observed_effect": "Keeps description attached to current attention",
                        "applies_when": ["A viewpoint notices a meaningful visible trait"],
                        "avoid_when": ["The detail would erase deliberate narrative distance"],
                        "failure_boundary": "A neutral inventory may intentionally stay distant",
                        "content_zone": self.profile,
                        "evidence_span_refs": [span_ref],
                        "confidence": 0.8,
                    }
                ],
                "counterexamples": ["Deliberate summary can omit local sensory detail"],
                "coverage": {"axes_observed": [axis]},
                "uncertainties": [],
            }
        elif contract_id == "learning.style_work_synthesize":
            continue_round = self.continue_first_round and payload["analysis_round"] == 1
            judgment = {
                "confidence": 0.79,
                "public_work_id": payload["public_work_id"],
                "stable_patterns": [
                    {
                        "axis": "body_appearance",
                        "operation": "Tie selected visible detail to viewpoint attention",
                    }
                ],
                "local_variants": [
                    {"scene_function": payload["observed_scene_functions"][0]}
                ],
                "counterexamples": [
                    {"boundary": "Distant summary can legitimately compress description"}
                ],
                "coverage_gaps": list(self.continue_coverage_gaps) if continue_round else [],
                "saturation": {
                    "state": "continue" if continue_round else "saturated",
                    "reason": "One more distinct scene function is useful"
                    if continue_round
                    else "Available functional evidence no longer changes the profile",
                },
                "uncertainties": [],
            }
        elif contract_id == "learning.style_axis_synthesize":
            work_ids = [
                row["public_work_id"] for row in payload["discovery_work_profiles"]
            ]
            claims = []
            if self.emit_claims:
                if len(work_ids) < 3:
                    raise AssertionError("claim fixture requires three discovery works")
                claims.append(
                    {
                        "operation": "Vary surface realization by scene function",
                        "desired_effect": "Preserve a coherent voice without uniform texture",
                        "applies_when": ["The current scene function is known"],
                        "avoid_when": ["Variation would obscure causal or viewpoint clarity"],
                        "failure_boundary": "Intentional monotony can embody constrained attention",
                        "scene_functions": ["opening", "dialogue"],
                        "content_zones": [self.profile],
                        "supporting_work_ids": work_ids[:2],
                        "counterexample_work_ids": [work_ids[2]],
                        "confidence": 0.76,
                    }
                )
            judgment = {
                "confidence": 0.78,
                "axis": payload["axis"],
                "claims": claims,
                "contested_questions": [
                    "Whether the same operation helps every scene function"
                ],
            }
        elif contract_id == "learning.style_axis_reconcile":
            candidate_claims = [
                claim
                for batch in payload["batch_syntheses"]
                for claim in batch["claims"]
            ]
            claims = []
            if self.emit_claims and candidate_claims:
                supports = list(dict.fromkeys(
                    work_id
                    for claim in candidate_claims
                    for work_id in claim["supporting_work_ids"]
                ))
                counters = [
                    work_id
                    for work_id in dict.fromkeys(
                        work_id
                        for claim in candidate_claims
                        for work_id in claim["counterexample_work_ids"]
                    )
                    if work_id not in supports
                ]
                reconciled = copy.deepcopy(candidate_claims[0])
                reconciled["operation"] = "Reconciled scene-conditioned surface realization"
                reconciled["supporting_work_ids"] = supports
                reconciled["counterexample_work_ids"] = counters
                claims = [reconciled]
            requested_ids = payload["eligible_discovery_work_ids"][:1]
            if self.reconcile_work_id_override is not None:
                requested_ids = [self.reconcile_work_id_override]
            runtime_convergence = self.reconcile_convergence
            if runtime_convergence == "continue":
                cycle = int(payload["reconciliation_id"].rsplit(":", 1)[-1])
                runtime_convergence = (
                    "continue" if cycle == 1 and requested_ids else
                    "converged" if cycle > 1 else "insufficient_evidence"
                )
            judgment = {
                "confidence": 0.77,
                "axis": payload["axis"],
                "reconciliation_id": payload["reconciliation_id"],
                "claims": claims,
                "resolved_conflicts": [
                    "Equivalent batch claims were merged under one conditional boundary"
                ] if claims else [],
                "unresolved_questions": [],
                "convergence": {
                    "state": runtime_convergence,
                    "rationale": (
                        "Bounded batch claims no longer expose an unresolved axis conflict"
                        if runtime_convergence == "converged"
                        else "Another source-free evidence slice could resolve the remaining boundary"
                    ),
                    "remaining_gaps": [] if runtime_convergence == "converged" else [
                        "Scene-function boundary remains unresolved"
                    ],
                },
                "next_evidence_requests": [] if runtime_convergence != "continue" else [
                    {
                        "request_id": f"REQ-{payload['axis']}",
                        "axis": payload["axis"],
                        "public_work_ids": requested_ids,
                        "scene_functions": self.reconcile_scene_functions_by_axis.get(
                            payload["axis"], ["transition"]
                        ),
                        "question": "Does the boundary persist in a transition scene?",
                    }
                ],
            }
        elif contract_id == "learning.style_claim_verify":
            holdout_ids = [
                row["public_work_id"] for row in payload["holdout_work_profiles"]
            ]
            judgment = {
                "confidence": 0.74,
                "claim_id": payload["claim_id"],
                "verdict": "promote",
                "verified_operation": "Vary realization according to scene function",
                "verified_boundary": "Retain causal clarity and the established viewpoint",
                "supporting_holdout_work_ids": holdout_ids[:1],
                "counterexample_holdout_work_ids": [],
                "content_disentanglement": {"passed": True, "risks": []},
                "report": "Held-out profiles support a conditional, source-independent operation.",
            }
        else:  # pragma: no cover - every registered contract needs a fixture
            raise AssertionError(f"unexpected style contract: {contract_id}")
        return _semantic_result(job, judgment)


class StyleStudyRunnerTests(unittest.TestCase):
    def test_axis_claims_keep_open_semantic_scene_functions(self) -> None:
        """Claim labels are semantic; only retrieval requests use fixed roles."""

        work_ids = {"WORK-A", "WORK-B", "WORK-C"}
        judgment = {
            "axis": STYLE_AXES[0],
            "claims": [
                {
                    "operation": "Change sentence pressure at a social reversal",
                    "desired_effect": "Make the shift legible without exposition",
                    "applies_when": ["A scene pivots on a change in social leverage"],
                    "avoid_when": ["The viewpoint cannot perceive the reversal"],
                    "failure_boundary": "A hidden reversal may require delayed recognition",
                    "scene_functions": ["social_leverage_reversal"],
                    "content_zones": ["general"],
                    "supporting_work_ids": ["WORK-A", "WORK-B"],
                    "counterexample_work_ids": ["WORK-C"],
                    "confidence": 0.7,
                }
            ],
            "contested_questions": [],
        }

        StyleStudyRunner._validate_axis_judgment(
            judgment,
            axis=STYLE_AXES[0],
            work_ids=work_ids,
            profile="general",
        )

        invalid = copy.deepcopy(judgment)
        invalid["claims"][0]["scene_functions"] = ["x" * 81]
        with self.assertRaisesRegex(Exception, "style_axis_scene_function_invalid"):
            StyleStudyRunner._validate_axis_judgment(
                invalid,
                axis=STYLE_AXES[0],
                work_ids=work_ids,
                profile="general",
            )

    def test_safe_derived_accepts_profile_labels_but_still_rejects_paths_and_size(self) -> None:
        """The path guard must not find ``file:`` inside a literary profile label."""

        StyleStudyRunner._assert_safe_derived(
            {
                "stable_patterns": [
                    {"source_free_analysis": "Style profile: scene-conditioned restraint"}
                ],
                "local_variants": [
                    {"source_free_analysis": "Scene profile: pressure rises through syntax"}
                ],
                "saturation": {
                    "state": "saturated",
                    "reason": "The profile: no longer changes with another bounded sample",
                },
                "uncertainties": ["Profile: evidence remains source-free"],
            },
            context="semantic_judgment",
        )

        rejected = (
            "file:///private/example",
            r"file:C:\private\example",
            "file:relative/example",
            r"C:\private\example",
            "~/private/example",
            "../private/example",
            "/Users/example/private",
            "/home/example/private",
            "x" * 4_001,
        )
        for value in rejected:
            with self.subTest(value=value[:24]):
                with self.assertRaisesRegex(
                    Exception, "semantic_judgment_string_rejected"
                ):
                    StyleStudyRunner._assert_safe_derived(
                        {"source_free_analysis": value},
                        context="semantic_judgment",
                    )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _runner(
        self, *, work_count: int = 6, profile: str = "general", name: str = "runner.sqlite"
    ) -> tuple[StyleStudyRunner, FakeStyleLibrary]:
        library = FakeStyleLibrary(work_count=work_count, profile=profile)
        return StyleStudyRunner(self.root / name, library), library

    def _single_window_runner(
        self, *, work_count: int = 3, name: str = "single-window.sqlite"
    ) -> tuple[StyleStudyRunner, FakeStyleLibrary]:
        library = FakeStyleLibrary(work_count=work_count)
        library._texts = {
            work_id: (
                f"第一章 合成\n{PASSAGE_SENTINEL}-{work_id} "
                "单一窗口只用于测试自适应证据不足，不包含任何真实来源。"
            )
            for work_id in library.work_ids
        }
        library.checklist_hash = _synthetic_checklist_hash(
            library.profile, library.work_ids, library._texts
        )
        return StyleStudyRunner(self.root / name, library), library

    def _assert_database_has_no_synthetic_prose(self, database: Path) -> None:
        files = [path for path in database.parent.glob(database.name + "*") if path.is_file()]
        self.assertTrue(files)
        durable = b"".join(path.read_bytes() for path in files)
        self.assertNotIn(PASSAGE_SENTINEL.encode("utf-8"), durable)
        self.assertNotIn(APPEARANCE_SENTINEL.encode("utf-8"), durable)
        self.assertNotIn("现在出发".encode("utf-8"), durable)

    def _install_trusted_publication_ledger(
        self, runner: StyleStudyRunner, library: FakeStyleLibrary
    ) -> None:
        receipt = library.completion_receipts[-1]
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE studies (
                    study_id TEXT PRIMARY KEY, public_study_id TEXT, profile TEXT,
                    state TEXT, checklist_hash TEXT, invalidation_reason TEXT
                );
                CREATE TABLE logical_works (
                    work_id TEXT PRIMARY KEY, public_work_id TEXT, active_version_id TEXT
                );
                CREATE TABLE source_versions (
                    version_id TEXT PRIMARY KEY, version_number INTEGER, sha256 TEXT,
                    available INTEGER, parse_state TEXT, private_metadata_json TEXT
                );
                CREATE TABLE source_files (
                    file_id TEXT PRIMARY KEY, work_id TEXT, version_id TEXT, available INTEGER,
                    relative_path TEXT
                );
                CREATE TABLE study_works (
                    study_id TEXT, work_id TEXT, version_id TEXT, ordinal INTEGER, state TEXT
                );
                CREATE TABLE style_completion_receipts (
                    receipt_id TEXT PRIMARY KEY, style_run_id TEXT, study_id TEXT,
                    public_study_id TEXT, profile TEXT, checklist_hash TEXT,
                    protocol_fingerprint TEXT, sampling_config_fingerprint TEXT,
                    semantic_config_fingerprint TEXT, semantic_evidence_fingerprint TEXT,
                    used_source_set_fingerprint TEXT,
                    candidate_bundle_fingerprint TEXT, candidate_artifact_fingerprint TEXT,
                    craft_pack_fingerprint TEXT, receipt_fingerprint TEXT, state TEXT
                );
                CREATE TRIGGER immutable_style_completion_receipt
                BEFORE UPDATE OF receipt_id,style_run_id,study_id,public_study_id,profile,
                    checklist_hash,protocol_fingerprint,sampling_config_fingerprint,
                    semantic_config_fingerprint,semantic_evidence_fingerprint,
                    used_source_set_fingerprint,
                    candidate_bundle_fingerprint,candidate_artifact_fingerprint,
                    craft_pack_fingerprint,receipt_fingerprint
                ON style_completion_receipts
                BEGIN SELECT RAISE(ABORT, 'style_completion_receipt_immutable'); END;
                """
            )
            connection.execute(
                "INSERT INTO studies VALUES(?,?,?,?,?,NULL)",
                (
                    library.study_id, library.public_study_id, library.profile,
                    "complete", library.checklist_hash,
                ),
            )
            for ordinal, public_work_id in enumerate(library.work_ids, 1):
                work_id = f"WORK-{ordinal:03d}"
                version_id = f"VERSION-{ordinal:03d}"
                connection.execute(
                    "INSERT INTO logical_works VALUES(?,?,?)",
                    (work_id, public_work_id, version_id),
                )
                connection.execute(
                    "INSERT INTO source_versions VALUES(?,1,?,1,'ok',?)",
                    (
                        version_id,
                        hashlib.sha256(library._texts[public_work_id].encode("utf-8")).hexdigest(),
                        json.dumps({"title": f"Synthetic work {ordinal:03d}"}),
                    ),
                )
                connection.execute(
                    "INSERT INTO source_files VALUES(?,?,?,1,?)",
                    (f"FILE-{ordinal:03d}", work_id, version_id, f"shelf/work-{ordinal:03d}.txt"),
                )
                activated = connection.execute(
                    "SELECT activation_cycle FROM style_work_steps WHERE style_run_id=? "
                    "AND public_work_id=?",
                    (receipt["style_run_id"], public_work_id),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO study_works VALUES(?,?,?,?, ?)",
                    (
                        library.study_id, work_id, version_id, ordinal,
                        "studied" if activated is not None else "selected",
                    ),
                )
            connection.execute(
                "INSERT INTO style_completion_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'complete')",
                (
                    "STYLE-RECEIPT-UNIT",
                    receipt["style_run_id"], receipt["study_id"], receipt["public_study_id"],
                    receipt["profile"], receipt["checklist_hash"], receipt["protocol_fingerprint"],
                    receipt["sampling_config_fingerprint"], receipt["semantic_config_fingerprint"],
                    receipt["semantic_evidence_fingerprint"], receipt["used_source_set_fingerprint"],
                    receipt["candidate_bundle_fingerprint"],
                    receipt["candidate_artifact_fingerprint"], receipt["craft_pack_fingerprint"],
                    receipt["receipt_fingerprint"],
                ),
            )
            connection.commit()

    def test_registered_reconciliation_contract_is_current_and_v5_is_archived(self) -> None:
        root = Path(__file__).resolve().parents[1]
        current_path = root / "harness/semantic_workers/contracts/learning.json"
        archive_path = root / "harness/semantic_workers/contracts/history/learning.v5.json"
        index_path = root / "harness/semantic_workers/contracts/history/index.json"
        catalog_path = root / "harness/semantic_workers/model_contract_catalog.json"
        current = json.loads(current_path.read_text(encoding="utf-8"))
        archive = json.loads(archive_path.read_text(encoding="utf-8"))
        index = json.loads(index_path.read_text(encoding="utf-8"))
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

        self.assertEqual(current["version"], "6")
        self.assertEqual(archive["version"], "5")
        self.assertIn("learning.style_axis_reconcile", current["contracts"])
        self.assertFalse(current["contracts"]["learning.style_claim_verify"]["independent_gate"])
        self.assertTrue(any(
            "disjoint" in rule
            for rule in current["contracts"]["learning.style_axis_synthesize"]["rubric"]
        ))
        self.assertTrue(any(
            "disjoint" in rule
            for rule in current["contracts"]["learning.style_claim_verify"]["rubric"]
        ))
        observe = current["contracts"]["corpus.style_observe"]
        self.assertIn(
            "retrieval_scene_function_hint", observe["input_contract"]["required"]
        )
        self.assertNotIn("scene_function", observe["input_contract"]["properties"])
        self.assertIn(
            "observed_scene_functions", observe["output_contract"]["required"]
        )
        reconcile = current["contracts"]["learning.style_axis_reconcile"]
        self.assertIn(
            "eligible_discovery_work_ids", reconcile["input_contract"]["required"]
        )
        for contract_id in (
            "learning.style_axis_synthesize",
            "learning.style_axis_reconcile",
        ):
            claim_scene_schema = current["contracts"][contract_id]["output_contract"][
                "properties"
            ]["claims"]["items"]["properties"]["scene_functions"]["items"]
            self.assertEqual(claim_scene_schema["type"], "string")
            self.assertNotIn("enum", claim_scene_schema)
        request_schema = reconcile["output_contract"]["properties"][
            "next_evidence_requests"
        ]["items"]
        self.assertIn("public_work_ids", request_schema["required"])
        self.assertEqual(
            request_schema["properties"]["scene_functions"]["items"]["enum"],
            list(STYLE_SAMPLE_ROLES),
        )
        learning_pack = next(row for row in catalog["packs"] if row["id"] == "learning")
        self.assertIn("learning.style_axis_reconcile", learning_pack["contracts"])
        history = next(
            row for row in index["entries"]
            if row["pack_id"] == "learning" and row["version"] == "5"
        )
        self.assertEqual(history["path"], "learning.v5.json")
        self.assertEqual(history["sha256"], hashlib.sha256(archive_path.read_bytes()).hexdigest())

    def test_discovery_holdout_split_is_deterministic_and_order_independent(self) -> None:
        library = FakeStyleLibrary(work_count=21)
        first = StyleStudyRunner._split_work_ids(
            library.public_study_id, library.work_ids
        )
        second = StyleStudyRunner._split_work_ids(
            library.public_study_id, tuple(reversed(library.work_ids))
        )
        self.assertEqual(first, second)
        self.assertGreaterEqual(Counter(first.values())["discovery"], 2)
        self.assertGreaterEqual(Counter(first.values())["holdout"], 1)

        runner = StyleStudyRunner(self.root / "split.sqlite", library)
        one = runner.prepare(library.study_id, style_run_id="SRUN-SPLIT-ONE")
        two = runner.prepare(library.study_id, style_run_id="SRUN-SPLIT-TWO")
        self.assertEqual(one["work_count"], 21)
        self.assertEqual(two["work_count"], 21)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            rows = connection.execute(
                "SELECT style_run_id,public_work_id,split FROM style_work_steps "
                "ORDER BY style_run_id,public_work_id"
            ).fetchall()
        projections: dict[str, dict[str, str]] = {}
        for style_run_id, work_id, split in rows:
            projections.setdefault(style_run_id, {})[work_id] = split
        self.assertEqual(projections["SRUN-SPLIT-ONE"], projections["SRUN-SPLIT-TWO"])

    def test_axis_batches_cover_only_activated_discovery_and_never_exceed_sixteen(self) -> None:
        runner, library = self._runner(work_count=21, name="axis-batch.sqlite")
        runner.prepare(
            library.study_id,
            style_run_id="SRUN-AXIS-BATCH",
            axis_batch_size=DEFAULT_AXIS_BATCH_SIZE,
        )
        runner._activate_seed_cohort(runner._run_row("SRUN-AXIS-BATCH"))
        with closing(sqlite3.connect(runner.db_path)) as connection:
            rows = connection.execute(
                "SELECT public_work_id,split FROM style_work_steps WHERE style_run_id=? "
                "AND activation_cycle IS NOT NULL",
                ("SRUN-AXIS-BATCH",),
            ).fetchall()
            for work_id, _split in rows:
                profile = {
                    "confidence": 0.5,
                    "public_work_id": work_id,
                    "stable_patterns": [],
                    "local_variants": [],
                    "counterexamples": [],
                    "coverage_gaps": [],
                    "saturation": {"state": "saturated", "reason": "synthetic fixture"},
                    "uncertainties": [],
                }
                connection.execute(
                    "UPDATE style_work_steps SET state='complete',work_profile_json=? "
                    "WHERE style_run_id=? AND public_work_id=?",
                    (json.dumps(profile, sort_keys=True), "SRUN-AXIS-BATCH", work_id),
                )
            connection.commit()

        runner._prepare_axis_steps(runner._run_row("SRUN-AXIS-BATCH"))
        with closing(sqlite3.connect(runner.db_path)) as connection:
            steps = connection.execute(
                "SELECT axis,batch_ordinal,discovery_work_ids_json FROM style_axis_steps "
                "WHERE style_run_id=? ORDER BY axis,batch_ordinal",
                ("SRUN-AXIS-BATCH",),
            ).fetchall()
            discovery_ids = {
                row[0]
                for row in connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                    "AND split='discovery' AND activation_cycle IS NOT NULL",
                    ("SRUN-AXIS-BATCH",),
                )
            }
        self.assertEqual({axis for axis, _ordinal, _ids in steps}, set(STYLE_AXES))
        by_axis: dict[str, list[str]] = {axis: [] for axis in STYLE_AXES}
        for axis, _ordinal, encoded in steps:
            batch = json.loads(encoded)
            self.assertGreaterEqual(len(batch), 2)
            self.assertLessEqual(len(batch), 16)
            by_axis[axis].extend(batch)
        for axis in STYLE_AXES:
            self.assertEqual(set(by_axis[axis]), discovery_ids)
            self.assertEqual(len(by_axis[axis]), len(set(by_axis[axis])))

    def test_empty_continuation_preserves_last_profile_without_semantic_resynthesis(self) -> None:
        runner, library = self._single_window_runner(name="empty-continuation.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-EMPTY-CONTINUATION",
            windows_per_round=6,
        )
        semantic = RecordingStyleSemantic(
            continue_first_round=True,
            continue_coverage_gaps=["opening"],
            emit_claims=False,
        )

        completed = runner.execute(prepared["style_run_id"], semantic)

        self.assertEqual(completed["status"], "completed")
        with closing(sqlite3.connect(runner.db_path)) as connection:
            work_rows = connection.execute(
                "SELECT public_work_id,current_round,state,saturation_state,work_profile_json "
                "FROM style_work_steps WHERE style_run_id=? AND activation_cycle IS NOT NULL "
                "ORDER BY ordinal",
                (prepared["style_run_id"],),
            ).fetchall()
            round_rows = connection.execute(
                "SELECT public_work_id,round_number,new_window_count,"
                "work_semantic_job_fingerprint,work_semantic_result_fingerprint "
                "FROM style_work_rounds WHERE style_run_id=? ORDER BY public_work_id,round_number",
                (prepared["style_run_id"],),
            ).fetchall()
            sample_rounds = connection.execute(
                "SELECT DISTINCT round_number FROM style_sample_steps WHERE style_run_id=?",
                (prepared["style_run_id"],),
            ).fetchall()

        self.assertTrue(work_rows)
        self.assertTrue(all(row[1:4] == (1, "complete", "insufficient_available_evidence") for row in work_rows))
        self.assertTrue(all(json.loads(row[4])["saturation"]["state"] == "continue" for row in work_rows))
        self.assertEqual({row[1] for row in round_rows}, {1})
        self.assertTrue(all(row[2] == 1 and row[3] and row[4] for row in round_rows))
        self.assertEqual(sample_rounds, [(1,)])

        synthesis_counts = Counter(
            job["subject_id"]
            for job in semantic.jobs
            if _contract_id(job) == "learning.style_work_synthesize"
        )
        self.assertTrue(all(synthesis_counts[row[0]] == 1 for row in work_rows))
        self.assertTrue(all(
            sum(call["public_work_id"] == row[0] for call in library.sample_calls) == 2
            for row in work_rows
        ))

        axis_jobs = [
            job for job in semantic.jobs
            if _contract_id(job) == "learning.style_axis_synthesize"
        ]
        self.assertTrue(axis_jobs)
        for job in axis_jobs:
            for item in _payload(job)["discovery_work_profiles"]:
                self.assertEqual(item["profile"]["saturation"]["state"], "continue")
                self.assertEqual(item["runtime_evidence"], {
                    "state": "insufficient_available_evidence",
                    "last_semantic_round": 1,
                    "profile_saturation_state": "continue",
                })
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_resume_retries_failed_adaptive_synthesis_in_current_round(self) -> None:
        runner, library = self._runner(work_count=3, name="resume-adaptive-round.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-RESUME-ADAPTIVE-ROUND",
            windows_per_round=1,
        )

        class FailAdaptiveSynthesis:
            def __init__(self) -> None:
                self.base = RecordingStyleSemantic(
                    continue_first_round=True,
                    continue_coverage_gaps=["ending"],
                    emit_claims=False,
                )
                self.jobs: list[dict] = []

            def __call__(self, job: dict) -> dict:
                self.jobs.append(copy.deepcopy(job))
                if (
                    _contract_id(job) == "learning.style_work_synthesize"
                    and _payload(job)["analysis_round"] == 2
                ):
                    raise RuntimeError("synthetic adaptive synthesis interruption")
                return self.base(job)

        interrupted_semantic = FailAdaptiveSynthesis()
        failed = runner.execute(prepared["style_run_id"], interrupted_semantic)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "semantic_callback_failed")
        self.assertEqual(_contract_id(interrupted_semantic.jobs[-1]), "learning.style_work_synthesize")
        self.assertEqual(_payload(interrupted_semantic.jobs[-1])["analysis_round"], 2)

        resumed_semantic = RecordingStyleSemantic(emit_claims=False)
        resumed = runner.resume(
            prepared["style_run_id"], resumed_semantic, max_jobs=1
        )

        self.assertEqual(resumed["status"], "running")
        self.assertEqual(len(resumed_semantic.jobs), 1)
        self.assertEqual(_contract_id(resumed_semantic.jobs[0]), "learning.style_work_synthesize")
        self.assertEqual(_payload(resumed_semantic.jobs[0])["analysis_round"], 2)
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_protocol_fingerprint_drift_blocks_execute_and_resume_without_mutation(self) -> None:
        runner, library = self._runner(work_count=3, name="protocol-drift.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-PROTOCOL-DRIFT",
        )
        marker = StyleStudyRunner._protocol_material()[
            "adaptive_sampling_evidence_semantics"
        ]
        self.assertEqual(marker["empty_continuation_runtime_state"], "insufficient_available_evidence")
        self.assertFalse(marker["empty_continuation_semantic_resynthesis"])
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE style_analysis_runs SET protocol_fingerprint=? WHERE style_run_id=?",
                ("sha256:" + "0" * 64, prepared["style_run_id"]),
            )
            connection.commit()

        semantic = RecordingStyleSemantic(emit_claims=False)
        with self.assertRaisesRegex(
            StyleStudyRunnerError, "style_protocol_fingerprint_mismatch"
        ):
            runner.execute(prepared["style_run_id"], semantic)
        with self.assertRaisesRegex(
            StyleStudyRunnerError, "style_protocol_fingerprint_mismatch"
        ):
            runner.resume(prepared["style_run_id"], semantic)

        with closing(sqlite3.connect(runner.db_path)) as connection:
            run = connection.execute(
                "SELECT status,phase,attempt_count,error_code FROM style_analysis_runs "
                "WHERE style_run_id=?",
                (prepared["style_run_id"],),
            ).fetchone()
            work_states = connection.execute(
                "SELECT DISTINCT state FROM style_work_steps WHERE style_run_id=?",
                (prepared["style_run_id"],),
            ).fetchall()
        self.assertEqual(run, ("prepared", "work_profiles", 0, None))
        self.assertEqual(work_states, [("pending",)])
        self.assertEqual(semantic.jobs, [])

    def test_full_pipeline_uses_five_contracts_multiround_sampling_and_heldout_verification(self) -> None:
        runner, library = self._runner(name="complete.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-COMPLETE",
            windows_per_round=1,
        )
        semantic = RecordingStyleSemantic(
            continue_first_round=True,
            continue_coverage_gaps=["ending", "opening"],
        )

        completed = runner.execute(prepared["style_run_id"], semantic)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["result_state"], "candidate")
        self.assertEqual({_contract_id(job) for job in semantic.jobs}, set(STYLE_CONTRACT_IDS))
        self.assertTrue(all(count == 2 for count in Counter(
            call["public_work_id"] for call in library.sample_calls
        ).values()))
        self.assertTrue(all(call["prior_manifest_fingerprint"] is None for call in library.sample_calls[::2]))
        self.assertTrue(all(call["prior_manifest_fingerprint"] is not None for call in library.sample_calls[1::2]))
        self.assertTrue(all(
            call["requested_roles"] == list(STYLE_SAMPLE_ROLES)
            for call in library.sample_calls[::2]
        ))
        self.assertTrue(all(
            call["requested_roles"] == ["opening", "ending"]
            for call in library.sample_calls[1::2]
        ))
        self.assertEqual(
            StyleStudyRunner._ordered_requested_roles(
                ["ending", "opening", "ending", "opening"]
            ),
            ["opening", "ending"],
        )

        observe_jobs = [job for job in semantic.jobs if _contract_id(job) == "corpus.style_observe"]
        self.assertTrue(observe_jobs)
        self.assertTrue(all(_payload(job)["content_profile"] == "general" for job in observe_jobs))
        self.assertTrue(all(
            "retrieval_scene_function_hint" in _payload(job)
            and "scene_function" not in _payload(job)
            for job in observe_jobs
        ))
        work_jobs = [
            job for job in semantic.jobs
            if _contract_id(job) == "learning.style_work_synthesize"
        ]
        self.assertTrue(work_jobs)
        self.assertTrue(all(
            _payload(job)["observed_scene_functions"] == ["relationship"]
            and all(
                set(window) == {"style_range_id", "observation"}
                for window in _payload(job)["window_observations"]
            )
            for job in work_jobs
        ))

        with closing(sqlite3.connect(runner.db_path)) as connection:
            holdout_ids = {
                row[0]
                for row in connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? AND split='holdout'",
                    ("SRUN-COMPLETE",),
                )
            }
            source_free_observations = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT judgment_json FROM style_sample_steps WHERE style_run_id=? AND state='complete'",
                    ("SRUN-COMPLETE",),
                )
            ]
            heldout_verifications = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT verification_json FROM style_claim_steps WHERE style_run_id=? AND state='complete'",
                    ("SRUN-COMPLETE",),
                )
            ]
            reconciled_claims = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT candidate_claim_json FROM style_claim_steps WHERE style_run_id=? "
                    "AND batch_ordinal<0 ORDER BY axis,claim_id",
                    ("SRUN-COMPLETE",),
                )
            ]
        self.assertTrue(any(
            observation["axis"] == "body_appearance"
            for judgment in source_free_observations
            for observation in judgment["observations"]
        ))
        verify_jobs = [
            job for job in semantic.jobs if _contract_id(job) == "learning.style_claim_verify"
        ]
        self.assertTrue(verify_jobs)
        self.assertTrue(all(job["provenance"]["independent_gate"] is False for job in verify_jobs))
        for job in verify_jobs:
            supplied = {
                row["public_work_id"] for row in _payload(job)["holdout_work_profiles"]
            }
            self.assertEqual(supplied, holdout_ids)
        self.assertTrue(heldout_verifications)
        self.assertTrue(reconciled_claims)
        self.assertTrue(all(
            claim["operation"] == "Reconciled scene-conditioned surface realization"
            for claim in reconciled_claims
        ))
        self.assertTrue(all(
            set(verification["supporting_holdout_work_ids"]).issubset(holdout_ids)
            and set(verification["counterexample_holdout_work_ids"]).issubset(holdout_ids)
            for verification in heldout_verifications
        ))

        for job in semantic.jobs:
            if _contract_id(job) != "corpus.style_observe":
                self.assertFalse(_contains_key(_payload(job), FORBIDDEN_SOURCE_KEYS))

        reconcile_jobs = [
            job for job in semantic.jobs
            if _contract_id(job) == "learning.style_axis_reconcile"
        ]
        self.assertEqual(len(reconcile_jobs), len(STYLE_AXES))
        for job in reconcile_jobs:
            payload = _payload(job)
            self.assertEqual(
                set(payload),
                {"axis", "reconciliation_id", "content_profile", "batch_syntheses", "eligible_discovery_work_ids"},
            )
            self.assertTrue(payload["batch_syntheses"])
            self.assertTrue(all(
                set(batch) == {"batch_id", "claims", "contested_questions"}
                for batch in payload["batch_syntheses"]
            ))

        bundle = completed["candidate_bundle"]
        contract = bundle["style_contract"]
        writer = bundle["writer_projection"]
        self.assertIsNotNone(contract)
        self.assertIsNotNone(writer)
        self.assertFalse(_contains_key(contract, FORBIDDEN_SOURCE_KEYS | {"work_id", "evidence_id"}))
        self.assertFalse(_contains_key(writer, FORBIDDEN_SOURCE_KEYS | {"work_id", "evidence_id"}))
        self.assertEqual(writer["content_zone"], "general")
        self.assertTrue(any(
            candidate["axis"] == "body_appearance"
            for candidate in writer["craft_candidates"]
        ))
        self.assertEqual(len(library.completion_receipts), 1)
        receipt = library.completion_receipts[0]
        self.assertEqual(receipt["semantic_config_fingerprint"], prepared["semantic_config_fingerprint"])
        self.assertEqual(
            receipt["semantic_evidence_fingerprint"],
            completed["semantic_evidence_fingerprint"],
        )
        self.assertEqual(
            receipt["semantic_evidence_fingerprint"],
            runner._semantic_evidence_fingerprint(completed["style_run_id"]),
        )
        self.assertEqual(
            receipt["used_source_set_fingerprint"],
            completed["used_source_set_fingerprint"],
        )
        self.assertEqual(library.materialize_calls, [])
        self.assertEqual(library.cancel_calls, [])
        self._install_trusted_publication_ledger(runner, library)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "INSERT INTO source_files VALUES(?,?,?,?,?)",
                ("FILE-ALIAS", "WORK-001", "VERSION-001", 1, "Private Alias Title.txt"),
            )
            connection.commit()
        trusted = runner.trusted_publication_material_for_study(library.study_id)
        self.assertEqual(
            trusted["candidate_bundle"]["bundle_fingerprint"],
            bundle["bundle_fingerprint"],
        )
        self.assertTrue(trusted["source_dependencies_current"])
        self.assertIn("synthetic work 001", trusted["forbidden_identity_terms"])
        self.assertIn("private alias title", trusted["forbidden_identity_terms"])
        completion_fingerprint = trusted["completion_receipt"]["receipt_fingerprint"]
        by_receipt = runner.trusted_publication_material_for_receipt(completion_fingerprint)
        self.assertEqual(
            by_receipt["candidate_bundle"]["bundle_fingerprint"],
            bundle["bundle_fingerprint"],
        )
        forged_fingerprint = "sha256:" + "f" * 64
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "INSERT INTO style_completion_receipts "
                "SELECT 'RECEIPT-FORGED','STYLE-RUN-FORGED',study_id,public_study_id,profile,"
                "checklist_hash,protocol_fingerprint,sampling_config_fingerprint,"
                "semantic_config_fingerprint,semantic_evidence_fingerprint,"
                "used_source_set_fingerprint,"
                "candidate_bundle_fingerprint,candidate_artifact_fingerprint,"
                "craft_pack_fingerprint,?,'complete' FROM style_completion_receipts "
                "WHERE style_run_id=?",
                (forged_fingerprint, completed["style_run_id"]),
            )
            connection.commit()
        with self.assertRaisesRegex(ValueError, "style_completion_receipt_lookup_invalid"):
            runner.trusted_publication_material_for_receipt(forged_fingerprint)

        original_bundle = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        tampered_bundle = copy.deepcopy(bundle)
        tampered_bundle["writer_projection"]["craft_candidates"][0]["effect"] = "tampered"
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE style_analysis_runs SET candidate_bundle_json=? WHERE style_run_id=?",
                (json.dumps(tampered_bundle), completed["style_run_id"]),
            )
            connection.commit()
        with self.assertRaisesRegex(ValueError, "style_publication_material_invalid"):
            runner.trusted_publication_material_for_study(library.study_id)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE style_analysis_runs SET candidate_bundle_json=? WHERE style_run_id=?",
                (original_bundle, completed["style_run_id"]),
            )
            connection.commit()

        with closing(sqlite3.connect(runner.db_path)) as connection:
            original_result_fingerprint = connection.execute(
                "SELECT semantic_result_fingerprint FROM style_sample_steps WHERE style_run_id=? "
                "ORDER BY public_work_id,round_number,style_range_id LIMIT 1",
                (completed["style_run_id"],),
            ).fetchone()[0]
            connection.execute(
                "UPDATE style_sample_steps SET semantic_result_fingerprint=? WHERE style_range_id=("
                "SELECT style_range_id FROM style_sample_steps WHERE style_run_id=? "
                "ORDER BY public_work_id,round_number,style_range_id LIMIT 1)",
                ("sha256:" + "e" * 64, completed["style_run_id"]),
            )
            connection.commit()
        with self.assertRaisesRegex(ValueError, "style_publication_material_invalid"):
            runner.trusted_publication_material_for_study(library.study_id)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE style_sample_steps SET semantic_result_fingerprint=? WHERE style_range_id=("
                "SELECT style_range_id FROM style_sample_steps WHERE style_run_id=? "
                "ORDER BY public_work_id,round_number,style_range_id LIMIT 1)",
                (original_result_fingerprint, completed["style_run_id"]),
            )
            connection.commit()

        original_source = library._texts[library.work_ids[0]]
        library._texts[library.work_ids[0]] += "\npost-scan drift"
        with self.assertRaisesRegex(ValueError, "style_publication_source_dependency_invalid"):
            runner.trusted_publication_material_for_receipt(completion_fingerprint)
        library._texts[library.work_ids[0]] = original_source

        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE logical_works SET active_version_id=NULL WHERE public_work_id=?",
                (library.work_ids[0],),
            )
            connection.commit()
        with self.assertRaisesRegex(ValueError, "style_publication_source_dependency_invalid"):
            runner.trusted_publication_material_for_study(library.study_id)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE logical_works SET active_version_id=? WHERE public_work_id=?",
                ("VERSION-001", library.work_ids[0]),
            )
            connection.execute("DROP TRIGGER immutable_style_completion_receipt")
            connection.execute(
                "CREATE TRIGGER immutable_style_completion_receipt BEFORE UPDATE OF "
                "receipt_id,style_run_id,study_id,public_study_id,profile,checklist_hash,"
                "protocol_fingerprint,sampling_config_fingerprint,semantic_config_fingerprint,"
                "semantic_evidence_fingerprint,used_source_set_fingerprint,candidate_bundle_fingerprint,"
                "candidate_artifact_fingerprint,craft_pack_fingerprint,receipt_fingerprint "
                "ON style_completion_receipts WHEN 0 "
                "BEGIN SELECT RAISE(ABORT, 'style_completion_receipt_immutable'); END"
            )
            connection.commit()
        with self.assertRaisesRegex(ValueError, "style_completion_receipt_not_immutable"):
            runner.trusted_publication_material_for_study(library.study_id)
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_reconcile_continue_activates_exact_model_work_and_stops_large_pool_early(self) -> None:
        runner, library = self._runner(work_count=21, name="reconcile-continue.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-RECONCILE-CONTINUE",
            windows_per_round=1,
        )
        semantic = RecordingStyleSemantic(
            reconcile_convergence="continue",
            reconcile_scene_functions_by_axis={
                STYLE_AXES[0]: ["action"],
                STYLE_AXES[1]: ["transition"],
            },
        )

        completed = runner.execute(prepared["style_run_id"], semantic)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["result_state"], "candidate")
        self.assertEqual(set(completed["axis_reconciliation"]), set(STYLE_AXES))
        self.assertEqual(
            completed["axis_reconciliation_execution"],
            {
                "work_pool": "dynamic_source_free_cohort",
                "dynamic_work_cohort_implemented": True,
                "early_stop_performed": True,
            },
        )
        self.assertTrue(all(
            item["convergence"]["state"] == "converged"
            for item in completed["axis_reconciliation"].values()
        ))
        first_cycle = [
            _payload(job) for job in semantic.jobs
            if _contract_id(job) == "learning.style_axis_reconcile"
            and _payload(job)["reconciliation_id"].endswith(":1")
        ]
        self.assertEqual(len(first_cycle), len(STYLE_AXES))
        selected_ids = {payload["eligible_discovery_work_ids"][0] for payload in first_cycle}
        self.assertEqual(len(selected_ids), 1)
        selected_id = next(iter(selected_ids))
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            adaptive = connection.execute(
                "SELECT public_work_id,requested_roles_json FROM style_work_steps "
                "WHERE style_run_id=? AND activation_kind='adaptive'",
                (completed["style_run_id"],),
            ).fetchall()
            untouched = connection.execute(
                "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                "AND split='discovery' AND activation_cycle IS NULL AND state='pending' "
                "AND current_round=0",
                (completed["style_run_id"],),
            ).fetchone()[0]
        self.assertEqual([row["public_work_id"] for row in adaptive], [selected_id])
        self.assertEqual(json.loads(adaptive[0]["requested_roles_json"]), [])
        adaptive_sample_call = next(
            call for call in library.sample_calls
            if call["public_work_id"] == selected_id
        )
        self.assertEqual(adaptive_sample_call["requested_roles"], ["action", "transition"])
        self.assertGreater(untouched, 0)
        touched = {call["public_work_id"] for call in library.sample_calls}
        self.assertEqual(library.materialize_calls, [])
        self.assertTrue(set(library.work_ids) - touched)
        self._install_trusted_publication_ledger(runner, library)
        trusted = runner.trusted_publication_material_for_study(library.study_id)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            used_ids = {
                row[0] for row in connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                    "AND activation_cycle IS NOT NULL",
                    (completed["style_run_id"],),
                )
            }
            remaining_states = {
                row[0] for row in connection.execute(
                    "SELECT sw.state FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                    "JOIN style_work_steps steps ON steps.public_work_id=w.public_work_id "
                    "WHERE steps.style_run_id=? AND steps.activation_cycle IS NULL",
                    (completed["style_run_id"],),
                )
            }
        self.assertEqual(set(library.verify_calls), used_ids)
        self.assertEqual(
            len(trusted["source_dependency_fingerprints"]), len(used_ids)
        )
        self.assertEqual(remaining_states, {"selected"})
        self.assertFalse(completed["authority"]["automatic_activation"])
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_trusted_publication_recomputes_unused_checklist_version_binding(self) -> None:
        runner, library = self._runner(
            work_count=21, name="checklist-version-drift.sqlite"
        )
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-CHECKLIST-VERSION-DRIFT",
            windows_per_round=1,
        )
        completed = runner.execute(
            prepared["style_run_id"], RecordingStyleSemantic()
        )
        self.assertEqual(completed["status"], "completed")
        self._install_trusted_publication_ledger(runner, library)

        with closing(sqlite3.connect(runner.db_path)) as connection:
            unused = connection.execute(
                "SELECT sw.work_id,sw.version_id,v.sha256 FROM study_works sw "
                "JOIN logical_works w ON w.work_id=sw.work_id "
                "JOIN source_versions v ON v.version_id=sw.version_id "
                "JOIN style_work_steps steps ON steps.public_work_id=w.public_work_id "
                "AND steps.style_run_id=? "
                "WHERE sw.study_id=? AND steps.activation_cycle IS NULL "
                "ORDER BY sw.ordinal LIMIT 1",
                (completed["style_run_id"], library.study_id),
            ).fetchone()
            self.assertIsNotNone(unused)
            forged_version_id = unused[1] + "-FORGED"
            connection.execute(
                "INSERT INTO source_versions "
                "(version_id,version_number,sha256,available,parse_state,private_metadata_json) "
                "VALUES(?,2,?,1,'ok','{}')",
                (forged_version_id, unused[2]),
            )
            connection.execute(
                "UPDATE study_works SET version_id=? WHERE study_id=? AND work_id=?",
                (forged_version_id, library.study_id, unused[0]),
            )
            connection.commit()

        with self.assertRaisesRegex(
            ValueError, "style_publication_study_binding_invalid"
        ):
            runner.trusted_publication_material_for_study(library.study_id)
        self.assertEqual(library.verify_calls, [])

    def test_reconciliation_requests_are_iff_continue_and_advance_filters_axes(self) -> None:
        runner, library = self._runner(
            work_count=6, name="reconciliation-request-binding.sqlite"
        )
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-RECONCILIATION-REQUEST-BINDING",
            windows_per_round=1,
        )
        with closing(sqlite3.connect(runner.db_path)) as connection:
            discovery_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                    "AND split='discovery' ORDER BY ordinal LIMIT 2",
                    (prepared["style_run_id"],),
                )
            ]
        self.assertEqual(len(discovery_ids), 2)

        def request(axis: str, work_id: str, scene_function: str) -> dict:
            return {
                "request_id": f"REQ-{axis}",
                "axis": axis,
                "public_work_ids": [work_id],
                "scene_functions": [scene_function],
                "question": "Synthetic evidence request",
            }

        def judgment(
            axis: str,
            state: str,
            *,
            gaps: list[str],
            requests: list[dict],
        ) -> dict:
            return {
                "confidence": 0.5,
                "axis": axis,
                "reconciliation_id": "RECONCILE-UNIT",
                "claims": [],
                "resolved_conflicts": [],
                "unresolved_questions": [],
                "convergence": {
                    "state": state,
                    "rationale": "Synthetic reconciliation boundary",
                    "remaining_gaps": gaps,
                },
                "next_evidence_requests": requests,
            }

        invalid_cases = (
            judgment(
                STYLE_AXES[0],
                "continue",
                gaps=[],
                requests=[request(STYLE_AXES[0], discovery_ids[0], "action")],
            ),
            judgment(
                STYLE_AXES[0],
                "insufficient_evidence",
                gaps=["No eligible evidence can resolve the boundary"],
                requests=[request(STYLE_AXES[0], discovery_ids[0], "action")],
            ),
        )
        for invalid in invalid_cases:
            with self.subTest(state=invalid["convergence"]["state"]):
                with self.assertRaisesRegex(
                    Exception, "style_axis_reconcile_convergence_invalid"
                ):
                    StyleStudyRunner._validate_axis_reconciliation(
                        invalid,
                        axis=STYLE_AXES[0],
                        reconciliation_id="RECONCILE-UNIT",
                        work_ids=set(),
                        eligible_work_ids=set(discovery_ids),
                        profile=library.profile,
                    )

        persisted: dict[str, dict] = {}
        for index, axis in enumerate(STYLE_AXES):
            if index == 0:
                persisted[axis] = judgment(
                    axis,
                    "continue",
                    gaps=["Action boundary remains unresolved"],
                    requests=[request(axis, discovery_ids[0], "action")],
                )
            elif index == 1:
                persisted[axis] = judgment(
                    axis,
                    "insufficient_evidence",
                    gaps=["No eligible evidence can resolve the transition boundary"],
                    requests=[request(axis, discovery_ids[1], "transition")],
                )
            else:
                persisted[axis] = judgment(
                    axis, "converged", gaps=[], requests=[]
                )
        with closing(sqlite3.connect(runner.db_path)) as connection:
            connection.execute(
                "UPDATE style_analysis_runs SET cohort_cycle=1 WHERE style_run_id=?",
                (prepared["style_run_id"],),
            )
            connection.executemany(
                "INSERT INTO style_axis_steps "
                "(style_run_id,axis,batch_ordinal,cohort_cycle,discovery_work_ids_json,"
                "state,judgment_json) VALUES(?,?,-1,1,'[]','complete',?)",
                [
                    (
                        prepared["style_run_id"],
                        axis,
                        json.dumps(persisted[axis], sort_keys=True),
                    )
                    for axis in STYLE_AXES
                ],
            )
            connection.commit()

        runner._advance_after_reconciliation(
            runner._run_row(prepared["style_run_id"])
        )

        with closing(sqlite3.connect(runner.db_path)) as connection:
            activated = connection.execute(
                "SELECT public_work_id,requested_roles_json FROM style_work_steps "
                "WHERE style_run_id=? AND activation_kind='adaptive' ORDER BY ordinal",
                (prepared["style_run_id"],),
            ).fetchall()
            ignored_cycle = connection.execute(
                "SELECT activation_cycle FROM style_work_steps WHERE style_run_id=? "
                "AND public_work_id=?",
                (prepared["style_run_id"], discovery_ids[1]),
            ).fetchone()[0]
        self.assertEqual(
            activated,
            [(discovery_ids[0], json.dumps(["action"], separators=(",", ":")))],
        )
        self.assertIsNone(ignored_cycle)

    def test_reconcile_holdout_id_fails_closed_and_resume_does_not_repeat_seed(self) -> None:
        runner, library = self._runner(work_count=21, name="illegal-holdout.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-ILLEGAL-HOLDOUT",
            windows_per_round=1,
        )
        with closing(sqlite3.connect(runner.db_path)) as connection:
            holdout_id = connection.execute(
                "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                "AND split='holdout' ORDER BY ordinal LIMIT 1",
                (prepared["style_run_id"],),
            ).fetchone()[0]
        invalid = RecordingStyleSemantic(
            reconcile_convergence="continue",
            reconcile_work_id_override=holdout_id,
        )

        failed = runner.execute(prepared["style_run_id"], invalid)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "style_axis_reconcile_request_invalid")
        seed_calls = Counter(call["public_work_id"] for call in library.sample_calls)
        with closing(sqlite3.connect(runner.db_path)) as connection:
            self.assertIsNone(connection.execute(
                "SELECT activation_cycle FROM style_work_steps WHERE style_run_id=? "
                "AND public_work_id=?",
                (prepared["style_run_id"], holdout_id),
            ).fetchone()[0])
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                "AND activation_kind='adaptive'",
                (prepared["style_run_id"],),
            ).fetchone()[0], 0)

        resumed = runner.resume(
            prepared["style_run_id"],
            RecordingStyleSemantic(reconcile_convergence="continue"),
        )

        self.assertEqual(resumed["status"], "completed")
        final_calls = Counter(call["public_work_id"] for call in library.sample_calls)
        for work_id, count in seed_calls.items():
            self.assertEqual(final_calls[work_id], count)
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_semantic_job_budget_pause_keeps_one_seed_activation_and_no_resample(self) -> None:
        runner, library = self._runner(work_count=21, name="budget-pause.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-BUDGET-PAUSE",
            windows_per_round=1,
        )
        semantic = RecordingStyleSemantic(emit_claims=False)

        first = runner.execute(prepared["style_run_id"], semantic, max_jobs=1)
        first_subject = semantic.jobs[0]["subject_id"]
        second = runner.execute(prepared["style_run_id"], semantic, max_jobs=1)

        self.assertEqual(first["status"], "running")
        self.assertEqual(second["status"], "running")
        self.assertEqual(len(semantic.jobs), 2)
        self.assertNotEqual(semantic.jobs[1]["subject_id"], first_subject)
        sampled = Counter(call["public_work_id"] for call in library.sample_calls)
        self.assertEqual(len(sampled), 2)
        self.assertTrue(all(count == 1 for count in sampled.values()))
        with closing(sqlite3.connect(runner.db_path)) as connection:
            active = connection.execute(
                "SELECT COUNT(*),COUNT(DISTINCT activation_fingerprint) "
                "FROM style_work_steps WHERE style_run_id=? AND activation_kind='seed'",
                (prepared["style_run_id"],),
            ).fetchone()
        self.assertEqual(active, (8, 8))
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_no_axis_claims_finishes_as_insufficient_without_false_artifacts(self) -> None:
        runner, library = self._runner(work_count=3, name="insufficient.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-INSUFFICIENT",
            windows_per_round=1,
        )
        semantic = RecordingStyleSemantic(emit_claims=False)

        completed = runner.execute(prepared["style_run_id"], semantic)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["result_state"], "insufficient_verified_claims")
        bundle = completed["candidate_bundle"]
        self.assertIsNone(bundle["style_contract"])
        self.assertIsNone(bundle["writer_projection"])
        self.assertIsNone(bundle["candidate_artifact_fingerprint"])
        self.assertIsNone(bundle["craft_pack_fingerprint"])
        self.assertEqual(bundle["promotion_state"], "blocked")
        self.assertEqual(bundle["missing_gates"], ["heldout_verified_claims"])
        self.assertFalse(bundle["activation_performed"])
        self.assertFalse(bundle["promotion_performed"])
        self.assertNotIn("learning.style_claim_verify", {_contract_id(job) for job in semantic.jobs})
        self.assertEqual(len(library.completion_receipts), 1)
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_model_continue_without_retrieval_hint_fails_instead_of_assuming_saturation(self) -> None:
        runner, library = self._runner(work_count=3, name="missing-next-role.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-MISSING-NEXT-ROLE",
            windows_per_round=1,
        )
        semantic = RecordingStyleSemantic(
            continue_first_round=True,
            continue_coverage_gaps=[],
        )

        failed = runner.execute(prepared["style_run_id"], semantic)

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "style_work_continuation_roles_missing")
        self.assertEqual(len(library.sample_calls), 1)
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_resume_retries_failed_sample_without_rerunning_completed_sample(self) -> None:
        runner, library = self._runner(work_count=3, name="resume.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-RESUME",
            windows_per_round=2,
        )
        first_semantic = RecordingStyleSemantic(
            emit_claims=False,
            fail_on_call=2,
        )

        failed = runner.execute(prepared["style_run_id"], first_semantic)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "semantic_callback_failed")
        first_completed_subject = first_semantic.jobs[0]["subject_id"]

        resumed_semantic = RecordingStyleSemantic(emit_claims=False)
        resumed = runner.resume(
            prepared["style_run_id"], resumed_semantic, max_jobs=1
        )

        self.assertEqual(resumed["status"], "running")
        self.assertEqual(len(resumed_semantic.jobs), 1)
        self.assertNotEqual(resumed_semantic.jobs[0]["subject_id"], first_completed_subject)
        combined_subjects = [job["subject_id"] for job in first_semantic.jobs + resumed_semantic.jobs]
        self.assertEqual(combined_subjects.count(first_completed_subject), 1)
        self.assertEqual(resumed["sample_states"], {"complete": 2})
        self._assert_database_has_no_synthetic_prose(runner.db_path)

    def test_cancel_affects_only_style_run_and_never_calls_library_cancel(self) -> None:
        runner, library = self._runner(work_count=3, name="cancel.sqlite")
        prepared = runner.prepare(
            library.study_id,
            style_run_id="SRUN-CANCEL",
            windows_per_round=1,
        )
        semantic = RecordingStyleSemantic(emit_claims=False)
        running = runner.execute(prepared["style_run_id"], semantic, max_jobs=1)
        self.assertEqual(running["status"], "running")

        cancelled = runner.cancel(prepared["style_run_id"])

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(library.start_calls, [library.study_id])
        self.assertEqual(library.cancel_calls, [])
        self.assertEqual(library.state, "running")
        self.assertEqual(runner.execute(prepared["style_run_id"], semantic)["status"], "cancelled")
        self._assert_database_has_no_synthetic_prose(runner.db_path)


if __name__ == "__main__":
    unittest.main()
