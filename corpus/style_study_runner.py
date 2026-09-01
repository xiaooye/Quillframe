#!/usr/bin/env python3
"""Recoverable, scene-aware prose-style learning for a frozen Corpus study.

This protocol is deliberately separate from the legacy three-window benchmark
runner.  A V5 selection may own several append-only analysis runs without
renaming, invalidating, or silently replacing that selection.  Source prose is
materialized only for one ``corpus.style_observe`` call and is never written to
SQLite.  Durable state contains opaque locators, fingerprints, source-free
model judgments, coverage/saturation evidence, per-axis semantic reconciliation,
and exact candidate bindings.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable, Iterable, Mapping, Sequence
import unicodedata
import uuid

from corpus.style_contract import (
    MAX_CANDIDATES,
    STYLE_AXES,
    StyleContractError,
    check_local_leakage,
    compile_style_contract,
    compile_writer_projection,
    fingerprint as style_fingerprint,
    make_craft_candidate,
    validate_style_contract,
    validate_writer_projection,
)
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import make_contract_job, validate_result

try:
    from corpus.style_sampling import STYLE_SAMPLE_ROLES
except (ImportError, ModuleNotFoundError):  # pragma: no cover - explicit install failure path
    STYLE_SAMPLE_ROLES = (
        "opening", "dialogue", "action", "interiority", "exposition",
        "environment", "body_appearance", "relationship", "transition", "ending",
    )


STYLE_PROTOCOL_ID = "quillframe_corpus_style_learning_v1"
STYLE_PROTOCOL_VERSION = "1"
STYLE_CONTRACT_IDS = (
    "corpus.style_observe",
    "learning.style_work_synthesize",
    "learning.style_axis_synthesize",
    "learning.style_axis_reconcile",
    "learning.style_claim_verify",
)
DEFAULT_MAX_ROUNDS = 4
DEFAULT_WINDOWS_PER_ROUND = 6
DEFAULT_AXIS_BATCH_SIZE = 16
DEFAULT_HOLDOUT_PPM = 200_000
DEFAULT_SEED_DISCOVERY_WORKS = 8
DEFAULT_HOLDOUT_COHORT_WORKS = 8

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$")
_PATH_RE = re.compile(
    r"(?:^[A-Za-z]:[\\/]|(?<![A-Za-z0-9_])file:|"
    r"~[\\/]|\.\.[\\/]|[\\/](?:Users|home)[\\/])",
    re.IGNORECASE,
)
_FORBIDDEN_DERIVED_KEYS = {
    "passage", "excerpt", "excerpts", "quote", "quotes", "raw", "raw_text",
    "source_text", "source_prose", "full_text", "source_title", "work_title",
    "book_title", "creator", "author", "local_path", "source_path", "file_path",
    "filepath", "filename", "relative_path", "relative_locator",
}


class StyleStudyRunnerError(ValueError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class _StepFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: Any, kind: str) -> str:
    normalized = str(value or "").strip()
    if not _ID_RE.fullmatch(normalized):
        raise StyleStudyRunnerError(f"invalid_{kind}")
    return normalized


def _json(value: Any) -> str:
    return _canonical_bytes(value).decode("utf-8")


def _normalized_overlap(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in value if ch.isalnum() or "\u3400" <= ch <= "\u9fff")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _strings(child)


class StyleStudyRunner:
    """Checkpointed functional sampling -> verified StyleContract pipeline."""

    def __init__(self, db_path: str | Path, library: Any) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.library = library
        # Passage text lives only here between sampling and its semantic call.
        # A resumed/new process intentionally falls back to exact re-materialization.
        self._ephemeral_windows: dict[str, dict[str, Any]] = {}
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS style_analysis_runs (
                    style_run_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL,
                    public_study_id TEXT NOT NULL,
                    profile TEXT NOT NULL CHECK(profile IN ('general','adult_explicit')),
                    checklist_hash TEXT NOT NULL,
                    protocol_id TEXT NOT NULL,
                    protocol_version TEXT NOT NULL,
                    protocol_fingerprint TEXT NOT NULL,
                    sampling_config_json TEXT NOT NULL,
                    sampling_config_fingerprint TEXT NOT NULL,
                    semantic_config_fingerprint TEXT NOT NULL,
                    semantic_evidence_fingerprint TEXT,
                    used_source_set_fingerprint TEXT,
                    cohort_cycle INTEGER NOT NULL DEFAULT 0,
                    discovery_converged INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL CHECK(status IN ('prepared','running','failed','completed','cancelled')),
                    phase TEXT NOT NULL CHECK(phase IN ('work_profiles','axis_synthesis','claim_verification','compilation','complete')),
                    result_state TEXT,
                    candidate_bundle_json TEXT,
                    candidate_artifact_fingerprint TEXT,
                    craft_pack_fingerprint TEXT,
                    local_leakage_summary_json TEXT,
                    completion_receipt_fingerprint TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS style_runs_study_idx
                    ON style_analysis_runs(study_id,created_at,style_run_id);

                CREATE TABLE IF NOT EXISTS style_work_steps (
                    style_run_id TEXT NOT NULL REFERENCES style_analysis_runs(style_run_id) ON DELETE CASCADE,
                    public_work_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    split TEXT NOT NULL CHECK(split IN ('discovery','holdout')),
                    state TEXT NOT NULL CHECK(state IN ('pending','sampling_ready','observations_ready','synthesizing','complete','failed')),
                    current_round INTEGER NOT NULL DEFAULT 0,
                    requested_roles_json TEXT NOT NULL,
                    activation_cycle INTEGER,
                    activation_kind TEXT,
                    activation_fingerprint TEXT,
                    work_profile_json TEXT,
                    work_profile_fingerprint TEXT,
                    saturation_state TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    PRIMARY KEY(style_run_id,public_work_id),
                    UNIQUE(style_run_id,ordinal)
                );

                CREATE TABLE IF NOT EXISTS style_work_rounds (
                    style_run_id TEXT NOT NULL,
                    public_work_id TEXT NOT NULL,
                    round_number INTEGER NOT NULL CHECK(round_number BETWEEN 1 AND 4),
                    requested_roles_json TEXT NOT NULL,
                    sampling_manifest_json TEXT NOT NULL,
                    sampling_manifest_fingerprint TEXT NOT NULL,
                    new_window_count INTEGER NOT NULL,
                    work_semantic_job_fingerprint TEXT,
                    work_semantic_result_fingerprint TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(style_run_id,public_work_id,round_number),
                    FOREIGN KEY(style_run_id,public_work_id)
                        REFERENCES style_work_steps(style_run_id,public_work_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS style_sample_steps (
                    style_range_id TEXT PRIMARY KEY,
                    style_run_id TEXT NOT NULL,
                    public_work_id TEXT NOT NULL,
                    round_number INTEGER NOT NULL,
                    scene_function TEXT NOT NULL,
                    descriptor_json TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    source_fingerprint TEXT NOT NULL,
                    passage_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','running','complete','failed')),
                    semantic_job_fingerprint TEXT,
                    semantic_result_fingerprint TEXT,
                    judgment_json TEXT,
                    judgment_fingerprint TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    UNIQUE(style_run_id,public_work_id,style_range_id),
                    FOREIGN KEY(style_run_id,public_work_id)
                        REFERENCES style_work_steps(style_run_id,public_work_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS style_samples_state_idx
                    ON style_sample_steps(style_run_id,public_work_id,state,round_number,style_range_id);

                CREATE TABLE IF NOT EXISTS style_axis_steps (
                    style_run_id TEXT NOT NULL REFERENCES style_analysis_runs(style_run_id) ON DELETE CASCADE,
                    axis TEXT NOT NULL,
                    batch_ordinal INTEGER NOT NULL,
                    cohort_cycle INTEGER NOT NULL DEFAULT 1,
                    discovery_work_ids_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','running','complete','failed')),
                    semantic_job_fingerprint TEXT,
                    semantic_result_fingerprint TEXT,
                    judgment_json TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    PRIMARY KEY(style_run_id,axis,batch_ordinal)
                );

                CREATE TABLE IF NOT EXISTS style_claim_steps (
                    style_run_id TEXT NOT NULL REFERENCES style_analysis_runs(style_run_id) ON DELETE CASCADE,
                    claim_id TEXT NOT NULL,
                    axis TEXT NOT NULL,
                    batch_ordinal INTEGER NOT NULL,
                    candidate_claim_json TEXT NOT NULL,
                    candidate_claim_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','running','complete','failed')),
                    verdict TEXT,
                    semantic_job_fingerprint TEXT,
                    semantic_result_fingerprint TEXT,
                    verification_json TEXT,
                    verification_fingerprint TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    PRIMARY KEY(style_run_id,claim_id)
                );
                CREATE INDEX IF NOT EXISTS style_claim_state_idx
                    ON style_claim_steps(style_run_id,state,axis,claim_id);
                """
            )
            round_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(style_work_rounds)")
            }
            for column in (
                "work_semantic_job_fingerprint",
                "work_semantic_result_fingerprint",
            ):
                if column not in round_columns:
                    connection.execute(
                        f"ALTER TABLE style_work_rounds ADD COLUMN {column} TEXT"
                    )
            run_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(style_analysis_runs)")
            }
            if "semantic_evidence_fingerprint" not in run_columns:
                connection.execute(
                    "ALTER TABLE style_analysis_runs ADD COLUMN semantic_evidence_fingerprint TEXT"
                )
            for column, declaration in (
                ("used_source_set_fingerprint", "TEXT"),
                ("cohort_cycle", "INTEGER NOT NULL DEFAULT 0"),
                ("discovery_converged", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if column not in run_columns:
                    connection.execute(
                        f"ALTER TABLE style_analysis_runs ADD COLUMN {column} {declaration}"
                    )
            work_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(style_work_steps)")
            }
            for column, declaration in (
                ("activation_cycle", "INTEGER"),
                ("activation_kind", "TEXT"),
                ("activation_fingerprint", "TEXT"),
            ):
                if column not in work_columns:
                    connection.execute(
                        f"ALTER TABLE style_work_steps ADD COLUMN {column} {declaration}"
                    )
            axis_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(style_axis_steps)")
            }
            if "cohort_cycle" not in axis_columns:
                connection.execute(
                    "ALTER TABLE style_axis_steps ADD COLUMN cohort_cycle INTEGER NOT NULL DEFAULT 1"
                )

    # ------------------------------------------------------------------
    # Closed derived-state guards
    # ------------------------------------------------------------------
    @classmethod
    def _assert_safe_derived(cls, value: Any, *, context: str) -> None:
        count = 0

        def visit(node: Any, depth: int) -> None:
            nonlocal count
            count += 1
            if count > 30_000 or depth > 24:
                raise _StepFailure(f"{context}_size_limit")
            if node is None or isinstance(node, bool):
                return
            if isinstance(node, (int, float)) and not isinstance(node, bool):
                if not math.isfinite(node):
                    raise _StepFailure(f"{context}_non_finite")
                return
            if isinstance(node, str):
                if len(node) > 4_000 or _PATH_RE.search(node):
                    raise _StepFailure(f"{context}_string_rejected")
                return
            if isinstance(node, Mapping):
                for raw_key, child in node.items():
                    key = str(raw_key).casefold().replace("-", "_")
                    if key in _FORBIDDEN_DERIVED_KEYS or key.endswith("_path"):
                        raise _StepFailure(f"{context}_forbidden_field")
                    visit(child, depth + 1)
                return
            if isinstance(node, (list, tuple)):
                for child in node:
                    visit(child, depth + 1)
                return
            raise _StepFailure(f"{context}_non_json")

        visit(value, 0)
        try:
            if len(_canonical_bytes(value)) > 8 * 1024 * 1024:
                raise _StepFailure(f"{context}_size_limit")
        except (TypeError, ValueError) as exc:
            raise _StepFailure(f"{context}_non_json") from exc

    @staticmethod
    def _assert_no_passage_overlap(passage: str, judgment: Mapping[str, Any]) -> None:
        normalized_source = _normalized_overlap(passage)
        for value in _strings(judgment):
            normalized = _normalized_overlap(value)
            if len(normalized) >= 24 and normalized in normalized_source:
                raise _StepFailure("semantic_judgment_source_overlap")

    # ------------------------------------------------------------------
    # Lifecycle and inspection
    # ------------------------------------------------------------------
    @staticmethod
    def _protocol_material() -> dict[str, Any]:
        return {
            "protocol_id": STYLE_PROTOCOL_ID,
            "protocol_version": STYLE_PROTOCOL_VERSION,
            "contracts": list(STYLE_CONTRACT_IDS),
            "style_axes": list(STYLE_AXES),
            "scene_functions": list(STYLE_SAMPLE_ROLES),
            "cross_work_axis_batch_max": DEFAULT_AXIS_BATCH_SIZE,
            "cross_work_pooling": "dynamic_source_free_cohort",
            "seed_discovery_work_count": DEFAULT_SEED_DISCOVERY_WORKS,
            "holdout_cohort_work_count": DEFAULT_HOLDOUT_COHORT_WORKS,
            "adaptive_sampling_evidence_semantics": {
                "retrieval_hints_are_semantic_coverage": False,
                "continuation_requires_new_window_evidence": True,
                "empty_continuation_runtime_state": "insufficient_available_evidence",
                "empty_continuation_semantic_resynthesis": False,
                "axis_runtime_evidence_state_required": True,
            },
            "source_prose_persistence": "forbidden",
            "promotion": "manual_only",
        }

    @classmethod
    def _assert_protocol_current(cls, run: Mapping[str, Any]) -> None:
        """Fail closed when stored execution semantics differ from this runner.

        Protocol version 1 remains the public contract identity, while the
        fingerprint binds exact execution semantics.  An older in-flight run
        therefore stays inspectable but cannot be silently resumed by newer
        code with materially different adaptive-sampling behavior.
        """

        if (
            run["protocol_id"] != STYLE_PROTOCOL_ID
            or run["protocol_version"] != STYLE_PROTOCOL_VERSION
            or run["protocol_fingerprint"] != _fingerprint(cls._protocol_material())
        ):
            raise StyleStudyRunnerError("style_protocol_fingerprint_mismatch")

    @staticmethod
    def _split_work_ids(public_study_id: str, work_ids: Sequence[str]) -> dict[str, str]:
        if len(work_ids) < 3:
            raise StyleStudyRunnerError("style_study_requires_three_works")
        ranked = sorted(
            work_ids,
            key=lambda value: hashlib.sha256(
                (public_study_id + "\0" + value).encode("utf-8")
            ).digest(),
        )
        holdout_count = max(1, round(len(ranked) * DEFAULT_HOLDOUT_PPM / 1_000_000))
        holdout_count = min(holdout_count, len(ranked) - 2)
        holdout = set(ranked[-holdout_count:])
        return {work_id: ("holdout" if work_id in holdout else "discovery") for work_id in work_ids}

    def prepare(
        self,
        study_id: str,
        *,
        style_run_id: str | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        windows_per_round: int = DEFAULT_WINDOWS_PER_ROUND,
        axis_batch_size: int = DEFAULT_AXIS_BATCH_SIZE,
        seed_discovery_work_count: int = DEFAULT_SEED_DISCOVERY_WORKS,
        holdout_cohort_work_count: int = DEFAULT_HOLDOUT_COHORT_WORKS,
        semantic_config: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        study_id = _safe_id(study_id, "study_id")
        if max_rounds != DEFAULT_MAX_ROUNDS:
            raise StyleStudyRunnerError("max_rounds_must_be_protocol_default")
        if (
            isinstance(windows_per_round, bool)
            or not isinstance(windows_per_round, int)
            or not 1 <= windows_per_round <= 12
        ):
            raise StyleStudyRunnerError("windows_per_round_invalid")
        if (
            isinstance(axis_batch_size, bool)
            or not isinstance(axis_batch_size, int)
            or not 2 <= axis_batch_size <= DEFAULT_AXIS_BATCH_SIZE
        ):
            raise StyleStudyRunnerError("axis_batch_size_invalid")
        if (
            isinstance(seed_discovery_work_count, bool)
            or not isinstance(seed_discovery_work_count, int)
            or not 2 <= seed_discovery_work_count <= DEFAULT_AXIS_BATCH_SIZE
        ):
            raise StyleStudyRunnerError("seed_discovery_work_count_invalid")
        if (
            isinstance(holdout_cohort_work_count, bool)
            or not isinstance(holdout_cohort_work_count, int)
            or not 1 <= holdout_cohort_work_count <= 32
        ):
            raise StyleStudyRunnerError("holdout_cohort_work_count_invalid")
        status = self.library.study_status(study_id, include_works=True)
        if status.get("status") not in {"confirmed", "running", "paused", "complete"}:
            raise StyleStudyRunnerError("study_not_confirmed_or_running")
        profile = status.get("profile")
        if profile not in {"general", "adult_explicit"}:
            raise StyleStudyRunnerError("study_profile_invalid")
        checklist_hash = status.get("checklist_hash")
        if not isinstance(checklist_hash, str) or not _HASH_RE.fullmatch(checklist_hash):
            raise StyleStudyRunnerError("study_checklist_not_frozen")
        works = status.get("works")
        if not isinstance(works, list) or len(works) < 3:
            raise StyleStudyRunnerError("study_membership_invalid")
        work_ids = [row.get("public_work_id") for row in works if isinstance(row, Mapping)]
        if len(work_ids) != len(works) or len(set(work_ids)) != len(work_ids):
            raise StyleStudyRunnerError("study_membership_invalid")
        work_ids = [_safe_id(value, "public_work_id") for value in work_ids]
        public_study_id = _safe_id(status.get("public_study_id"), "public_study_id")
        splits = self._split_work_ids(public_study_id, work_ids)
        protocol = self._protocol_material()
        sampling_config = {
            "max_rounds": max_rounds,
            "windows_per_round": windows_per_round,
            "axis_batch_size": axis_batch_size,
            "holdout_ppm": DEFAULT_HOLDOUT_PPM,
            "initial_requested_roles": list(STYLE_SAMPLE_ROLES),
            "seed_discovery_work_count": seed_discovery_work_count,
            "holdout_cohort_work_count": holdout_cohort_work_count,
        }
        semantic_config = dict(semantic_config or {"executor": "external_registered_contract"})
        self._assert_safe_derived(semantic_config, context="semantic_config")
        style_run_id = _safe_id(style_run_id, "style_run_id") if style_run_id else f"SRUN-{uuid.uuid4().hex}"
        now = _utc_now()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT style_run_id,study_id FROM style_analysis_runs WHERE style_run_id=?",
                (style_run_id,),
            ).fetchone()
            if existing is not None:
                if existing["study_id"] != study_id:
                    raise StyleStudyRunnerError("style_run_identity_conflict")
                return self._status(connection, style_run_id)
            connection.execute(
                "INSERT INTO style_analysis_runs(style_run_id,study_id,public_study_id,profile,"
                "checklist_hash,protocol_id,protocol_version,protocol_fingerprint,sampling_config_json,"
                "sampling_config_fingerprint,semantic_config_fingerprint,status,phase,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,'prepared','work_profiles',?,?)",
                (
                    style_run_id, study_id, public_study_id, profile, checklist_hash,
                    STYLE_PROTOCOL_ID, STYLE_PROTOCOL_VERSION, _fingerprint(protocol),
                    _json(sampling_config), _fingerprint(sampling_config),
                    _fingerprint(semantic_config), now, now,
                ),
            )
            connection.executemany(
                "INSERT INTO style_work_steps(style_run_id,public_work_id,ordinal,split,state,"
                "requested_roles_json) VALUES(?,?,?,?,'pending',?)",
                [
                    (style_run_id, work_id, ordinal, splits[work_id], _json([]))
                    for ordinal, work_id in enumerate(work_ids, 1)
                ],
            )
            return self._status(connection, style_run_id)

    @staticmethod
    def _axis_reconciliation_status(
        connection: sqlite3.Connection, style_run_id: str
    ) -> dict[str, Any]:
        rows: dict[str, sqlite3.Row] = {}
        for row in connection.execute(
            "SELECT axis,state,judgment_json,cohort_cycle FROM style_axis_steps "
            "WHERE style_run_id=? AND batch_ordinal<0 ORDER BY cohort_cycle",
            (style_run_id,),
        ):
            rows[row["axis"]] = row
        result: dict[str, Any] = {}
        for axis in STYLE_AXES:
            row = rows.get(axis)
            if row is None:
                continue
            item: dict[str, Any] = {"step_state": row["state"]}
            item["cohort_cycle"] = row["cohort_cycle"]
            if row["judgment_json"]:
                judgment = json.loads(row["judgment_json"])
                item["convergence"] = judgment["convergence"]
                item["next_evidence_requests"] = judgment["next_evidence_requests"]
            result[axis] = item
        return result

    @staticmethod
    def _activation_fingerprint(
        style_run_id: str, public_work_id: str, cycle: int, kind: str,
        requested_roles: Sequence[str],
    ) -> str:
        return _fingerprint({
            "schema": "quillframe_style_cohort_activation_v1",
            "style_run_id": style_run_id,
            "public_work_id": public_work_id,
            "activation_cycle": cycle,
            "activation_kind": kind,
            "requested_roles": list(requested_roles),
        })

    def _activate_works(
        self,
        connection: sqlite3.Connection,
        run: sqlite3.Row,
        *,
        cycle: int,
        kind: str,
        requests: Mapping[str, Sequence[str]],
    ) -> None:
        if kind not in {"seed", "adaptive", "holdout"} or cycle < 1 or not requests:
            raise _StepFailure("style_cohort_activation_invalid")
        for work_id, raw_roles in requests.items():
            roles = self._ordered_requested_roles(raw_roles)
            if not roles:
                raise _StepFailure("style_cohort_activation_roles_invalid")
            row = connection.execute(
                "SELECT split,activation_cycle FROM style_work_steps WHERE style_run_id=? "
                "AND public_work_id=?",
                (run["style_run_id"], work_id),
            ).fetchone()
            expected_split = "holdout" if kind == "holdout" else "discovery"
            if row is None or row["split"] != expected_split or row["activation_cycle"] is not None:
                raise _StepFailure("style_cohort_activation_binding_invalid")
            activation_fp = self._activation_fingerprint(
                run["style_run_id"], work_id, cycle, kind, roles,
            )
            connection.execute(
                "UPDATE style_work_steps SET activation_cycle=?,activation_kind=?,"
                "activation_fingerprint=?,requested_roles_json=?,state='pending',error_code=NULL "
                "WHERE style_run_id=? AND public_work_id=? AND activation_cycle IS NULL",
                (
                    cycle, kind, activation_fp, _json(roles),
                    run["style_run_id"], work_id,
                ),
            )
        connection.execute(
            "UPDATE style_analysis_runs SET cohort_cycle=?,phase='work_profiles',updated_at=? "
            "WHERE style_run_id=?",
            (cycle, _utc_now(), run["style_run_id"]),
        )

    def _activate_seed_cohort(self, run: sqlite3.Row) -> None:
        config = json.loads(run["sampling_config_json"])
        limit = int(config["seed_discovery_work_count"])
        with self._connection() as connection:
            already_active = connection.execute(
                "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                "AND activation_cycle IS NOT NULL",
                (run["style_run_id"],),
            ).fetchone()[0]
            if already_active:
                return
            rows = connection.execute(
                "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                "AND split='discovery' AND activation_cycle IS NULL ORDER BY ordinal LIMIT ?",
                (run["style_run_id"], limit),
            ).fetchall()
            if len(rows) < 2:
                raise _StepFailure("style_discovery_split_insufficient")
            self._activate_works(
                connection,
                run,
                cycle=1,
                kind="seed",
                requests={row["public_work_id"]: STYLE_SAMPLE_ROLES for row in rows},
            )

    def _status(self, connection: sqlite3.Connection, style_run_id: str) -> dict[str, Any]:
        run = connection.execute(
            "SELECT * FROM style_analysis_runs WHERE style_run_id=?", (style_run_id,)
        ).fetchone()
        if run is None:
            raise StyleStudyRunnerError("style_run_not_found")
        work_counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM style_work_steps WHERE style_run_id=? GROUP BY state",
                (style_run_id,),
            )
        }
        cohort_counts = {
            row["bucket"]: row["amount"]
            for row in connection.execute(
                "SELECT CASE WHEN activation_cycle IS NULL THEN 'available_unanalysed' "
                "WHEN state='complete' THEN 'analysed' ELSE 'activated' END AS bucket,"
                "COUNT(*) AS amount FROM style_work_steps WHERE style_run_id=? GROUP BY bucket",
                (style_run_id,),
            )
        }
        sample_counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM style_sample_steps WHERE style_run_id=? GROUP BY state",
                (style_run_id,),
            )
        }
        axis_counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM style_axis_steps WHERE style_run_id=? GROUP BY state",
                (style_run_id,),
            )
        }
        claim_counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM style_claim_steps WHERE style_run_id=? GROUP BY state",
                (style_run_id,),
            )
        }
        result: dict[str, Any] = {
            "schema": "quillframe_corpus_style_run_status_v1",
            "analysis_protocol_id": run["protocol_id"],
            "analysis_protocol_version": run["protocol_version"],
            "style_run_id": run["style_run_id"],
            "study_id": run["study_id"],
            "public_study_id": run["public_study_id"],
            "profile": run["profile"],
            "status": run["status"],
            "phase": run["phase"],
            "result_state": run["result_state"],
            "work_count": sum(work_counts.values()),
            "work_states": dict(sorted(work_counts.items())),
            "sample_states": dict(sorted(sample_counts.items())),
            "axis_states": dict(sorted(axis_counts.items())),
            "claim_states": dict(sorted(claim_counts.items())),
            "semantic_attempts": run["attempt_count"],
            "semantic_config_fingerprint": run["semantic_config_fingerprint"],
            "cohort_cycle": run["cohort_cycle"],
            "cohort_states": {
                key: cohort_counts.get(key, 0)
                for key in ("available_unanalysed", "activated", "analysed")
            },
            "raw_passage_persisted": False,
            "stop_criteria": [
                "functional_coverage", "semantic_saturation", "cross_work_counterexamples",
                "heldout_replication", "causal_ab_uplift", "non_leakage",
            ],
            "book_count_is_quality_threshold": False,
            "axis_reconciliation_execution": {
                "work_pool": "dynamic_source_free_cohort",
                "dynamic_work_cohort_implemented": True,
                "early_stop_performed": bool(
                    run["discovery_converged"]
                    and connection.execute(
                        "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                        "AND split='discovery' AND activation_cycle IS NULL",
                        (style_run_id,),
                    ).fetchone()[0]
                ),
            },
            "authority": {
                "canon_write": False,
                "framework_behavior_write": False,
                "automatic_activation": False,
                "automatic_promotion": False,
                "public_release": False,
            },
        }
        if run["error_code"]:
            result["error_code"] = run["error_code"]
        if run["candidate_bundle_json"]:
            result["candidate_bundle"] = json.loads(run["candidate_bundle_json"])
        if run["completion_receipt_fingerprint"]:
            result["completion_receipt_fingerprint"] = run["completion_receipt_fingerprint"]
        if run["semantic_evidence_fingerprint"]:
            result["semantic_evidence_fingerprint"] = run["semantic_evidence_fingerprint"]
        if run["used_source_set_fingerprint"]:
            result["used_source_set_fingerprint"] = run["used_source_set_fingerprint"]
        reconciliation = self._axis_reconciliation_status(connection, style_run_id)
        if reconciliation:
            result["axis_reconciliation"] = reconciliation
        return result

    def status(self, style_run_id: str) -> dict[str, Any]:
        style_run_id = _safe_id(style_run_id, "style_run_id")
        with self._connection() as connection:
            return self._status(connection, style_run_id)

    def status_for_study(self, study_id: str) -> dict[str, Any] | None:
        study_id = _safe_id(study_id, "study_id")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT style_run_id FROM style_analysis_runs WHERE study_id=? "
                "ORDER BY created_at DESC,style_run_id DESC LIMIT 1", (study_id,),
            ).fetchone()
            return self._status(connection, row["style_run_id"]) if row else None

    def trusted_publication_material_for_study(self, study_id: str) -> dict[str, Any]:
        """Load the latest publishable candidate from immutable local ledger facts.

        The caller supplies only ``study_id``.  Candidate JSON, completion
        identity and source-dependency facts are reloaded from SQLite and every
        fingerprint is recomputed before any public preview can be built.
        """

        study_id = _safe_id(study_id, "study_id")
        try:
            with self._connection() as connection:
                run = connection.execute(
                    "SELECT * FROM style_analysis_runs WHERE study_id=? AND status='completed' "
                    "AND phase='complete' AND result_state='candidate' "
                    "ORDER BY created_at DESC,style_run_id DESC LIMIT 1",
                    (study_id,),
                ).fetchone()
                if run is None:
                    raise StyleStudyRunnerError("style_publication_candidate_not_ready")
                receipts = connection.execute(
                    "SELECT * FROM style_completion_receipts WHERE style_run_id=?",
                    (run["style_run_id"],),
                ).fetchall()
                study = connection.execute(
                    "SELECT * FROM studies WHERE study_id=?", (study_id,)
                ).fetchone()
                dependencies = connection.execute(
                    "SELECT sw.ordinal,sw.state,sw.work_id,w.public_work_id,w.active_version_id,"
                    "sw.version_id,v.version_number,v.sha256,v.available,v.parse_state,"
                    "v.private_metadata_json,"
                    "(SELECT sf.relative_path FROM source_files sf WHERE sf.version_id=sw.version_id "
                    "AND sf.work_id=sw.work_id AND sf.available=1 ORDER BY sf.relative_path LIMIT 1) "
                    "AS relative_path,"
                    "EXISTS(SELECT 1 FROM source_files sf WHERE sf.version_id=sw.version_id "
                    "AND sf.work_id=sw.work_id AND sf.available=1) AS live_file "
                    "FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                    "JOIN source_versions v ON v.version_id=sw.version_id "
                    "WHERE sw.study_id=? ORDER BY sw.ordinal",
                    (study_id,),
                ).fetchall()
                identity_locators = connection.execute(
                    "SELECT DISTINCT sf.relative_path FROM study_works sw "
                    "JOIN logical_works w ON w.work_id=sw.work_id "
                    "JOIN style_work_steps steps ON steps.public_work_id=w.public_work_id "
                    "AND steps.style_run_id=? AND steps.activation_cycle IS NOT NULL "
                    "JOIN source_files sf ON sf.version_id=sw.version_id AND sf.work_id=sw.work_id "
                    "WHERE sw.study_id=? AND sf.available=1 ORDER BY sf.relative_path",
                    (run["style_run_id"], study_id),
                ).fetchall()
                work_steps = connection.execute(
                    "SELECT ordinal,public_work_id,state,activation_cycle FROM style_work_steps "
                    "WHERE style_run_id=? ORDER BY ordinal",
                    (run["style_run_id"],),
                ).fetchall()
                immutable_trigger = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type='trigger' "
                    "AND name='immutable_style_completion_receipt'",
                ).fetchone()
        except StyleStudyRunnerError:
            raise
        except sqlite3.Error as exc:
            raise StyleStudyRunnerError("style_publication_ledger_unavailable") from exc

        if len(receipts) != 1 or receipts[0]["state"] != "complete":
            raise StyleStudyRunnerError("style_completion_receipt_not_unique")
        receipt = receipts[0]
        trigger_sql = (
            re.sub(r"\s+", " ", str(immutable_trigger["sql"] or "")).casefold()
            if immutable_trigger is not None else ""
        )
        immutable_columns = {
            "receipt_id", "style_run_id", "study_id", "public_study_id", "profile",
            "checklist_hash", "protocol_fingerprint", "sampling_config_fingerprint",
            "semantic_config_fingerprint", "semantic_evidence_fingerprint",
            "used_source_set_fingerprint",
            "candidate_bundle_fingerprint", "candidate_artifact_fingerprint",
            "craft_pack_fingerprint", "receipt_fingerprint",
        }
        trigger_match = re.search(
            r"before update of (.+?) on style_completion_receipts", trigger_sql
        )
        protected_column_list = [
            column.strip().strip('"`[] ')
            for column in trigger_match.group(1).split(",")
        ] if trigger_match else []
        protected_columns = set(protected_column_list)
        immutable_body = re.search(
            r"\bon style_completion_receipts\s+begin\s+select\s+raise\s*\(\s*abort\s*,\s*"
            r"'style_completion_receipt_immutable'\s*\)\s*;\s*end\s*;?\s*$",
            trigger_sql,
        )
        if (
            study is None
            or protected_columns != immutable_columns
            or len(protected_column_list) != len(immutable_columns)
            or immutable_body is None
        ):
            raise StyleStudyRunnerError("style_completion_receipt_not_immutable")
        if (
            study["state"] != "complete"
            or study["invalidation_reason"] is not None
            or study["public_study_id"] != run["public_study_id"]
            or study["profile"] != run["profile"]
            or study["checklist_hash"] != run["checklist_hash"]
        ):
            raise StyleStudyRunnerError("style_publication_study_binding_invalid")
        if not dependencies or len(dependencies) != len(work_steps):
            raise StyleStudyRunnerError("style_publication_source_dependency_invalid")
        expected_ordinals = list(range(1, len(dependencies) + 1))
        if [row["ordinal"] for row in dependencies] != expected_ordinals or [
            row["ordinal"] for row in work_steps
        ] != expected_ordinals:
            raise StyleStudyRunnerError("style_publication_source_dependency_invalid")
        checklist_works = []
        for row in dependencies:
            source_fingerprint = "sha256:" + str(row["sha256"] or "")
            if (
                not isinstance(row["public_work_id"], str)
                or not _ID_RE.fullmatch(row["public_work_id"])
                or isinstance(row["version_number"], bool)
                or not isinstance(row["version_number"], int)
                or row["version_number"] < 1
                or not _HASH_RE.fullmatch(source_fingerprint)
            ):
                raise StyleStudyRunnerError("style_publication_study_binding_invalid")
            checklist_works.append({
                "public_work_id": row["public_work_id"],
                "source_version": row["version_number"],
                "source_fingerprint": source_fingerprint,
            })
        recomputed_checklist_hash = _fingerprint({
            "profile": study["profile"], "works": checklist_works,
        })
        if recomputed_checklist_hash != study["checklist_hash"]:
            raise StyleStudyRunnerError("style_publication_study_binding_invalid")
        used_dependencies: list[sqlite3.Row] = []
        for dependency, work in zip(dependencies, work_steps, strict=True):
            if work["public_work_id"] != dependency["public_work_id"]:
                raise StyleStudyRunnerError("style_publication_source_dependency_invalid")
            if work["activation_cycle"] is None:
                if work["state"] != "pending":
                    raise StyleStudyRunnerError("style_publication_source_dependency_invalid")
                continue
            if (
                dependency["state"] != "studied"
                or dependency["active_version_id"] != dependency["version_id"]
                or dependency["available"] != 1
                or dependency["parse_state"] != "ok"
                or dependency["live_file"] != 1
                or work["state"] != "complete"
            ):
                raise StyleStudyRunnerError("style_publication_source_dependency_invalid")
            used_dependencies.append(dependency)
        if not used_dependencies:
            raise StyleStudyRunnerError("style_publication_source_dependency_invalid")

        source_dependency_fingerprints: list[str] = []
        source_verifier = getattr(self.library, "verify_style_source_dependency", None)
        if not callable(source_verifier):
            raise StyleStudyRunnerError("style_publication_source_verifier_unavailable")
        for dependency in used_dependencies:
            try:
                verified = source_verifier(
                    study_id,
                    dependency["public_work_id"],
                    version_id=dependency["version_id"],
                    source_sha256=dependency["sha256"],
                )
            except Exception as exc:
                raise StyleStudyRunnerError(
                    "style_publication_source_dependency_invalid"
                ) from exc
            dependency_fingerprint = (
                verified.get("dependency_fingerprint")
                if isinstance(verified, Mapping) else None
            )
            if not isinstance(dependency_fingerprint, str) or not _HASH_RE.fullmatch(
                dependency_fingerprint
            ):
                raise StyleStudyRunnerError("style_publication_source_dependency_invalid")
            source_dependency_fingerprints.append(dependency_fingerprint)

        identity_terms: set[str] = set()

        def add_identity_term(value: Any) -> None:
            normalized = "".join(
                character
                for character in unicodedata.normalize("NFKC", str(value)).casefold()
                if unicodedata.category(character) not in {"Cf", "Cc", "Cs", "Co", "Cn"}
            ).strip()
            if 2 <= len(normalized) <= 300:
                identity_terms.add(normalized)

        for locator in identity_locators:
            add_identity_term(Path(str(locator["relative_path"] or "")).stem)
        for dependency in used_dependencies:
            try:
                metadata = json.loads(dependency["private_metadata_json"] or "{}")
            except (TypeError, json.JSONDecodeError) as exc:
                raise StyleStudyRunnerError("style_publication_identity_policy_invalid") from exc
            if not isinstance(metadata, dict):
                raise StyleStudyRunnerError("style_publication_identity_policy_invalid")
            for value in metadata.values():
                add_identity_term(value)
        if not identity_terms:
            raise StyleStudyRunnerError("style_publication_identity_policy_incomplete")

        try:
            protocol = self._protocol_material()
            sampling_config = json.loads(run["sampling_config_json"])
            bundle = json.loads(run["candidate_bundle_json"])
            if not isinstance(sampling_config, dict) or not isinstance(bundle, dict):
                raise ValueError("not an object")
            if run["protocol_id"] != STYLE_PROTOCOL_ID or run["protocol_version"] != STYLE_PROTOCOL_VERSION:
                raise ValueError("protocol identity")
            if run["protocol_fingerprint"] != _fingerprint(protocol):
                raise ValueError("protocol fingerprint")
            if run["sampling_config_fingerprint"] != _fingerprint(sampling_config):
                raise ValueError("sampling fingerprint")
            if set(sampling_config) != {
                "max_rounds", "windows_per_round", "axis_batch_size", "holdout_ppm",
                "initial_requested_roles", "seed_discovery_work_count",
                "holdout_cohort_work_count",
            }:
                raise ValueError("sampling schema")
            if (
                sampling_config["max_rounds"] != DEFAULT_MAX_ROUNDS
                or isinstance(sampling_config["windows_per_round"], bool)
                or not isinstance(sampling_config["windows_per_round"], int)
                or not 1 <= sampling_config["windows_per_round"] <= 12
                or isinstance(sampling_config["axis_batch_size"], bool)
                or not isinstance(sampling_config["axis_batch_size"], int)
                or not 2 <= sampling_config["axis_batch_size"] <= DEFAULT_AXIS_BATCH_SIZE
                or sampling_config["holdout_ppm"] != DEFAULT_HOLDOUT_PPM
                or sampling_config["initial_requested_roles"] != list(STYLE_SAMPLE_ROLES)
                or isinstance(sampling_config["seed_discovery_work_count"], bool)
                or not isinstance(sampling_config["seed_discovery_work_count"], int)
                or not 2 <= sampling_config["seed_discovery_work_count"] <= DEFAULT_AXIS_BATCH_SIZE
                or isinstance(sampling_config["holdout_cohort_work_count"], bool)
                or not isinstance(sampling_config["holdout_cohort_work_count"], int)
                or not 1 <= sampling_config["holdout_cohort_work_count"] <= 32
            ):
                raise ValueError("sampling value")

            bundle_base = {key: value for key, value in bundle.items() if key != "bundle_fingerprint"}
            if bundle.get("bundle_fingerprint") != _fingerprint(bundle_base):
                raise ValueError("bundle fingerprint")
            contract = bundle.get("style_contract")
            projection = bundle.get("writer_projection")
            leakage = bundle.get("local_leakage")
            if not isinstance(contract, dict) or validate_style_contract(contract):
                raise ValueError("style contract")
            if not isinstance(projection, dict) or validate_writer_projection(projection):
                raise ValueError("writer projection")
            if projection != compile_writer_projection(contract):
                raise ValueError("writer projection binding")
            if not isinstance(leakage, dict):
                raise ValueError("local leakage")
            leakage_base = {
                key: value for key, value in leakage.items() if key != "summary_fingerprint"
            }
            if (
                leakage.get("local_status") != "pass"
                or leakage.get("summary_fingerprint") != _fingerprint(leakage_base)
            ):
                raise ValueError("local leakage binding")
            candidate_artifact_fingerprint = _fingerprint(
                {
                    "style_contract": contract,
                    "writer_projection": projection,
                    "local_leakage_summary_fingerprint": leakage["summary_fingerprint"],
                }
            )
            craft_pack_fingerprint = projection["projection_fingerprint"]
            if (
                bundle.get("schema") != "quillframe_corpus_style_candidate_bundle_v1"
                or bundle.get("analysis_protocol_id") != STYLE_PROTOCOL_ID
                or bundle.get("public_study_id") != run["public_study_id"]
                or bundle.get("profile") != run["profile"]
                or bundle.get("result_state") != "candidate"
                or bundle.get("candidate_artifact_fingerprint") != candidate_artifact_fingerprint
                or bundle.get("craft_pack_fingerprint") != craft_pack_fingerprint
                or run["candidate_artifact_fingerprint"] != candidate_artifact_fingerprint
                or run["craft_pack_fingerprint"] != craft_pack_fingerprint
            ):
                raise ValueError("candidate artifact binding")

            receipt_material = {
                "schema": "quillframe_corpus_style_completion_receipt_v1",
                "style_run_id": receipt["style_run_id"],
                "study_id": receipt["study_id"],
                "public_study_id": receipt["public_study_id"],
                "profile": receipt["profile"],
                "checklist_hash": receipt["checklist_hash"],
                "protocol_fingerprint": receipt["protocol_fingerprint"],
                "sampling_config_fingerprint": receipt["sampling_config_fingerprint"],
                "semantic_config_fingerprint": receipt["semantic_config_fingerprint"],
                "semantic_evidence_fingerprint": receipt["semantic_evidence_fingerprint"],
                "used_source_set_fingerprint": receipt["used_source_set_fingerprint"],
                "candidate_bundle_fingerprint": receipt["candidate_bundle_fingerprint"],
                "candidate_artifact_fingerprint": receipt["candidate_artifact_fingerprint"],
                "craft_pack_fingerprint": receipt["craft_pack_fingerprint"],
            }
            if (
                receipt["receipt_fingerprint"] != _fingerprint(receipt_material)
                or run["completion_receipt_fingerprint"] != receipt["receipt_fingerprint"]
                or receipt["style_run_id"] != run["style_run_id"]
                or receipt["study_id"] != run["study_id"]
                or receipt["public_study_id"] != run["public_study_id"]
                or receipt["profile"] != run["profile"]
                or receipt["checklist_hash"] != run["checklist_hash"]
                or receipt["protocol_fingerprint"] != run["protocol_fingerprint"]
                or receipt["sampling_config_fingerprint"] != run["sampling_config_fingerprint"]
                or receipt["semantic_config_fingerprint"] != run["semantic_config_fingerprint"]
                or receipt["semantic_evidence_fingerprint"]
                != run["semantic_evidence_fingerprint"]
                or receipt["semantic_evidence_fingerprint"]
                != self._semantic_evidence_fingerprint(run["style_run_id"])
                or receipt["used_source_set_fingerprint"]
                != run["used_source_set_fingerprint"]
                or receipt["used_source_set_fingerprint"]
                != self._used_source_set_fingerprint(run["style_run_id"])
                or receipt["candidate_bundle_fingerprint"] != bundle["bundle_fingerprint"]
                or receipt["candidate_artifact_fingerprint"] != candidate_artifact_fingerprint
                or receipt["craft_pack_fingerprint"] != craft_pack_fingerprint
            ):
                raise ValueError("completion receipt binding")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, _StepFailure) as exc:
            raise StyleStudyRunnerError("style_publication_material_invalid") from exc

        return {
            "schema": "quillframe_corpus_trusted_style_publication_material_v1",
            "analysis_protocol_id": STYLE_PROTOCOL_ID,
            "style_run_id": run["style_run_id"],
            "study_id": run["study_id"],
            "candidate_bundle": bundle,
            "completion_receipt": {
                **receipt_material,
                "receipt_fingerprint": receipt["receipt_fingerprint"],
            },
            "forbidden_identity_terms": sorted(identity_terms),
            "source_dependency_fingerprints": source_dependency_fingerprints,
            "source_dependencies_current": True,
            "authority": False,
        }

    def trusted_publication_material_for_receipt(
        self, completion_receipt_fingerprint: str
    ) -> dict[str, Any]:
        """Resolve the latest trusted study candidate by its immutable receipt.

        The receipt fingerprint is only a lookup key.  The selected study is
        reloaded through :meth:`trusted_publication_material_for_study`, which
        revalidates the candidate, receipt, checklist and current source bytes.
        Historical or forged receipt rows therefore cannot select a different
        candidate by supplying a study identifier alongside the lookup.
        """

        if not isinstance(completion_receipt_fingerprint, str) or not _HASH_RE.fullmatch(
            completion_receipt_fingerprint
        ):
            raise StyleStudyRunnerError("style_completion_receipt_fingerprint_invalid")
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    "SELECT study_id FROM style_completion_receipts "
                    "WHERE receipt_fingerprint=? AND state='complete'",
                    (completion_receipt_fingerprint,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise StyleStudyRunnerError("style_publication_ledger_unavailable") from exc
        if len(rows) != 1:
            raise StyleStudyRunnerError("style_completion_receipt_lookup_invalid")
        material = self.trusted_publication_material_for_study(rows[0]["study_id"])
        receipt = material.get("completion_receipt") if isinstance(material, Mapping) else None
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("receipt_fingerprint") != completion_receipt_fingerprint
        ):
            raise StyleStudyRunnerError("style_completion_receipt_lookup_invalid")
        return material

    @classmethod
    def inspect_for_study(cls, db_path: str | Path, study_id: str) -> dict[str, Any] | None:
        database = Path(db_path).expanduser().resolve()
        if not database.exists():
            return None
        try:
            with sqlite3.connect(database, timeout=5) as connection:
                connection.row_factory = sqlite3.Row
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='style_analysis_runs'"
                ).fetchone()
                if not exists:
                    return None
                row = connection.execute(
                    "SELECT style_run_id FROM style_analysis_runs WHERE study_id=? "
                    "ORDER BY created_at DESC,style_run_id DESC LIMIT 1", (study_id,),
                ).fetchone()
            if not row:
                return None
            # Read-only inspection cannot construct a CorpusLibrary here; build
            # the same public status projection directly.
            with sqlite3.connect(database, timeout=5) as connection:
                connection.row_factory = sqlite3.Row
                run = connection.execute(
                    "SELECT * FROM style_analysis_runs WHERE style_run_id=?", (row["style_run_id"],)
                ).fetchone()
                work_counts = {r[0]: r[1] for r in connection.execute(
                    "SELECT state,COUNT(*) FROM style_work_steps WHERE style_run_id=? GROUP BY state",
                    (row["style_run_id"],),
                )}
                cohort_counts = {r[0]: r[1] for r in connection.execute(
                    "SELECT CASE WHEN activation_cycle IS NULL THEN 'available_unanalysed' "
                    "WHEN state='complete' THEN 'analysed' ELSE 'activated' END,COUNT(*) "
                    "FROM style_work_steps WHERE style_run_id=? GROUP BY 1",
                    (row["style_run_id"],),
                )}
                sample_counts = {r[0]: r[1] for r in connection.execute(
                    "SELECT state,COUNT(*) FROM style_sample_steps WHERE style_run_id=? GROUP BY state",
                    (row["style_run_id"],),
                )}
                axis_counts = {r[0]: r[1] for r in connection.execute(
                    "SELECT state,COUNT(*) FROM style_axis_steps WHERE style_run_id=? GROUP BY state",
                    (row["style_run_id"],),
                )}
                claim_counts = {r[0]: r[1] for r in connection.execute(
                    "SELECT state,COUNT(*) FROM style_claim_steps WHERE style_run_id=? GROUP BY state",
                    (row["style_run_id"],),
                )}
                result = {
                    "schema": "quillframe_corpus_style_run_status_v1",
                    "analysis_protocol_id": run["protocol_id"],
                    "analysis_protocol_version": run["protocol_version"],
                    "style_run_id": run["style_run_id"], "study_id": run["study_id"],
                    "public_study_id": run["public_study_id"], "profile": run["profile"],
                    "status": run["status"], "phase": run["phase"],
                    "result_state": run["result_state"], "work_count": sum(work_counts.values()),
                    "work_states": dict(sorted(work_counts.items())),
                    "sample_states": dict(sorted(sample_counts.items())),
                    "axis_states": dict(sorted(axis_counts.items())),
                    "claim_states": dict(sorted(claim_counts.items())),
                    "semantic_attempts": run["attempt_count"],
                    "semantic_config_fingerprint": run["semantic_config_fingerprint"],
                    "cohort_cycle": run["cohort_cycle"],
                    "cohort_states": {
                        key: cohort_counts.get(key, 0)
                        for key in ("available_unanalysed", "activated", "analysed")
                    },
                    "raw_passage_persisted": False,
                    "axis_reconciliation_execution": {
                        "work_pool": "dynamic_source_free_cohort",
                        "dynamic_work_cohort_implemented": True,
                        "early_stop_performed": bool(
                            run["discovery_converged"]
                            and connection.execute(
                                "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                                "AND split='discovery' AND activation_cycle IS NULL",
                                (row["style_run_id"],),
                            ).fetchone()[0]
                        ),
                    },
                    "authority": {"canon_write": False, "framework_behavior_write": False,
                                  "automatic_activation": False, "automatic_promotion": False,
                                  "public_release": False},
                    **({"error_code": run["error_code"]} if run["error_code"] else {}),
                }
                if run["candidate_bundle_json"]:
                    result["candidate_bundle"] = json.loads(run["candidate_bundle_json"])
                if run["completion_receipt_fingerprint"]:
                    result["completion_receipt_fingerprint"] = run["completion_receipt_fingerprint"]
                if (
                    "semantic_evidence_fingerprint" in run.keys()
                    and run["semantic_evidence_fingerprint"]
                ):
                    result["semantic_evidence_fingerprint"] = run["semantic_evidence_fingerprint"]
                if (
                    "used_source_set_fingerprint" in run.keys()
                    and run["used_source_set_fingerprint"]
                ):
                    result["used_source_set_fingerprint"] = run["used_source_set_fingerprint"]
                reconciliation = cls._axis_reconciliation_status(
                    connection, row["style_run_id"]
                )
                if reconciliation:
                    result["axis_reconciliation"] = reconciliation
                return result
        except (sqlite3.Error, OSError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Registered semantic calls and validations
    # ------------------------------------------------------------------
    def _semantic_call(
        self,
        *,
        contract_id: str,
        subject_id: str,
        payload: dict[str, Any],
        style_run_id: str,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
        raw_passage: bool = False,
    ) -> tuple[dict[str, Any], str, str]:
        if not raw_passage:
            self._assert_safe_derived(payload, context="semantic_input")
        stable_job_id = "JOB-" + hashlib.sha256(
            _canonical_bytes({"run": style_run_id, "contract": contract_id, "subject": subject_id, "payload": payload})
        ).hexdigest()[:32]
        try:
            job = make_contract_job(
                contract_id, subject_id, payload, job_id=stable_job_id,
                source_session_id=f"SES-{style_run_id}",
                handoff_id=f"{style_run_id}:{contract_id}:{subject_id}",
            )
        except ValueError as exc:
            raise _StepFailure("semantic_job_invalid") from exc
        errors = validate_registered_job(job)
        if errors:
            raise _StepFailure("semantic_job_binding_invalid")
        try:
            result = run_semantic(job)
        except Exception as exc:
            raise _StepFailure("semantic_callback_failed") from exc
        if not isinstance(result, dict):
            raise _StepFailure("semantic_result_not_object")
        if validate_result(job, result):
            raise _StepFailure("semantic_result_validation_failed")
        judgment = result.get("judgment")
        if not isinstance(judgment, dict):
            raise _StepFailure("semantic_judgment_missing")
        self._assert_safe_derived(judgment, context="semantic_judgment")
        return judgment, str(job["input_fingerprint"]), _fingerprint(result)

    @staticmethod
    def _validate_range_judgment(
        judgment: Mapping[str, Any], *, style_range_id: str, span_refs: set[str], profile: str,
    ) -> None:
        if judgment.get("style_range_id") != style_range_id:
            raise _StepFailure("style_range_result_binding_mismatch")
        observations = judgment.get("observations")
        if not isinstance(observations, list):
            raise _StepFailure("style_observations_invalid")
        for row in observations:
            if not isinstance(row, Mapping) or row.get("axis") not in STYLE_AXES:
                raise _StepFailure("style_observation_axis_invalid")
            if row.get("content_zone") not in {profile, "profile_neutral"}:
                raise _StepFailure("style_observation_profile_mismatch")
            refs = row.get("evidence_span_refs")
            if not isinstance(refs, list) or not refs or not set(refs).issubset(span_refs):
                raise _StepFailure("style_observation_span_ref_invalid")
        coverage = judgment.get("coverage")
        axes = coverage.get("axes_observed") if isinstance(coverage, Mapping) else None
        if not isinstance(axes, list) or not set(axes).issubset(set(STYLE_AXES)):
            raise _StepFailure("style_observation_coverage_invalid")
        observed_functions = judgment.get("observed_scene_functions")
        if (
            not isinstance(observed_functions, list)
            or not observed_functions
            or len(observed_functions) != len(set(observed_functions))
            or not set(observed_functions).issubset(set(STYLE_SAMPLE_ROLES))
        ):
            raise _StepFailure("style_observed_scene_functions_invalid")

    @staticmethod
    def _validate_work_profile(judgment: Mapping[str, Any], *, work_id: str) -> None:
        if judgment.get("public_work_id") != work_id:
            raise _StepFailure("style_work_result_binding_mismatch")
        gaps = judgment.get("coverage_gaps")
        if not isinstance(gaps, list) or not set(gaps).issubset(set(STYLE_SAMPLE_ROLES)):
            raise _StepFailure("style_work_coverage_gap_invalid")
        saturation = judgment.get("saturation")
        if not isinstance(saturation, Mapping) or saturation.get("state") not in {
            "continue", "saturated", "insufficient_available_evidence",
        }:
            raise _StepFailure("style_work_saturation_invalid")
        if saturation["state"] == "continue" and not gaps:
            raise _StepFailure("style_work_continuation_roles_missing")

    @staticmethod
    def _ordered_requested_roles(coverage_gaps: Sequence[Any]) -> list[str]:
        """Turn semantic coverage gaps into a stable retrieval hint only."""

        requested = set(coverage_gaps)
        return [role for role in STYLE_SAMPLE_ROLES if role in requested]

    @staticmethod
    def _validate_axis_judgment(
        judgment: Mapping[str, Any], *, axis: str, work_ids: set[str], profile: str,
    ) -> None:
        if judgment.get("axis") != axis:
            raise _StepFailure("style_axis_result_binding_mismatch")
        claims = judgment.get("claims")
        if not isinstance(claims, list):
            raise _StepFailure("style_axis_claims_invalid")
        for claim in claims:
            if not isinstance(claim, Mapping):
                raise _StepFailure("style_axis_claim_invalid")
            supports = claim.get("supporting_work_ids")
            counters = claim.get("counterexample_work_ids")
            if (
                not isinstance(supports, list) or len(set(supports)) < 2
                or not isinstance(counters, list) or len(set(counters)) < 1
                or not set(supports).issubset(work_ids)
                or not set(counters).issubset(work_ids)
                or set(supports) & set(counters)
            ):
                raise _StepFailure("style_axis_evidence_binding_invalid")
            zones = claim.get("content_zones")
            if not isinstance(zones, list) or not zones or not set(zones).issubset(
                {profile, "profile_neutral"}
            ):
                raise _StepFailure("style_axis_profile_mismatch")
            scene_functions = claim.get("scene_functions")
            if (
                not isinstance(scene_functions, list)
                or not scene_functions
                or len(scene_functions) > 10
                or len(set(scene_functions)) != len(scene_functions)
                or any(
                    not isinstance(scene_function, str)
                    or not 1 <= len(scene_function) <= 80
                    for scene_function in scene_functions
                )
            ):
                raise _StepFailure("style_axis_scene_function_invalid")
            for key in ("applies_when", "avoid_when"):
                values = claim.get(key)
                if (
                    not isinstance(values, list)
                    or not values
                    or len(set(values)) != len(values)
                ):
                    raise _StepFailure(f"style_axis_{key}_invalid")

    @classmethod
    def _validate_axis_reconciliation(
        cls,
        judgment: Mapping[str, Any],
        *,
        axis: str,
        reconciliation_id: str,
        work_ids: set[str],
        eligible_work_ids: set[str],
        profile: str,
    ) -> None:
        if judgment.get("reconciliation_id") != reconciliation_id:
            raise _StepFailure("style_axis_reconcile_binding_mismatch")
        cls._validate_axis_judgment(
            judgment, axis=axis, work_ids=work_ids, profile=profile,
        )
        claims = judgment["claims"]
        claim_fingerprints = [_fingerprint(claim) for claim in claims]
        if len(claim_fingerprints) != len(set(claim_fingerprints)):
            raise _StepFailure("style_axis_reconcile_duplicate_claim")
        convergence = judgment.get("convergence")
        requests = judgment.get("next_evidence_requests")
        if (
            not isinstance(convergence, Mapping)
            or convergence.get("state") not in {
                "continue", "converged", "insufficient_evidence",
            }
            or not isinstance(convergence.get("rationale"), str)
            or not convergence["rationale"].strip()
            or not isinstance(convergence.get("remaining_gaps"), list)
            or not isinstance(requests, list)
        ):
            raise _StepFailure("style_axis_reconcile_convergence_invalid")
        for request in requests:
            if not isinstance(request, Mapping):
                raise _StepFailure("style_axis_reconcile_request_invalid")
            scene_functions = request.get("scene_functions")
            requested_ids = request.get("public_work_ids")
            if (
                request.get("axis") != axis
                or not isinstance(scene_functions, list)
                or not scene_functions
                or not set(scene_functions).issubset(set(STYLE_SAMPLE_ROLES))
                or not isinstance(requested_ids, list)
                or not requested_ids
                or len(requested_ids) != len(set(requested_ids))
                or not set(requested_ids).issubset(eligible_work_ids)
            ):
                raise _StepFailure("style_axis_reconcile_request_invalid")
        all_requested = [
            work_id for request in requests for work_id in request["public_work_ids"]
        ]
        if len(all_requested) != len(set(all_requested)):
            raise _StepFailure("style_axis_reconcile_request_duplicate")
        if convergence["state"] == "converged" and convergence["remaining_gaps"]:
            raise _StepFailure("style_axis_reconcile_convergence_invalid")
        if convergence["state"] == "continue":
            if not convergence["remaining_gaps"]:
                raise _StepFailure("style_axis_reconcile_convergence_invalid")
            if not requests:
                raise _StepFailure("style_axis_reconcile_request_missing")
        elif requests:
            raise _StepFailure("style_axis_reconcile_convergence_invalid")

    @staticmethod
    def _validate_claim_verification(
        judgment: Mapping[str, Any], *, claim_id: str, holdout_ids: set[str],
    ) -> None:
        if judgment.get("claim_id") != claim_id:
            raise _StepFailure("style_claim_result_binding_mismatch")
        supports = judgment.get("supporting_holdout_work_ids")
        counters = judgment.get("counterexample_holdout_work_ids")
        if (
            not isinstance(supports, list) or not isinstance(counters, list)
            or not set(supports).issubset(holdout_ids)
            or not set(counters).issubset(holdout_ids)
            or set(supports) & set(counters)
        ):
            raise _StepFailure("style_claim_holdout_binding_invalid")
        verdict = judgment.get("verdict")
        disentanglement = judgment.get("content_disentanglement")
        if verdict in {"promote", "narrow"} and (
            not supports or not isinstance(disentanglement, Mapping)
            or disentanglement.get("passed") is not True
        ):
            raise _StepFailure("style_claim_verification_insufficient")

    # ------------------------------------------------------------------
    # Work sampling and synthesis
    # ------------------------------------------------------------------
    def _run_row(self, style_run_id: str) -> sqlite3.Row:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM style_analysis_runs WHERE style_run_id=?", (style_run_id,)
            ).fetchone()
        if row is None:
            raise StyleStudyRunnerError("style_run_not_found")
        return row

    def _set_failed(
        self, style_run_id: str, code: str, *, work_id: str | None = None,
        range_id: str | None = None, axis: str | None = None, claim_id: str | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_analysis_runs SET status='failed',error_code=?,updated_at=? WHERE style_run_id=?",
                (code, _utc_now(), style_run_id),
            )
            if work_id:
                connection.execute(
                    "UPDATE style_work_steps SET state='failed',error_code=? "
                    "WHERE style_run_id=? AND public_work_id=?", (code, style_run_id, work_id),
                )
            if range_id:
                connection.execute(
                    "UPDATE style_sample_steps SET state='failed',error_code=? WHERE style_range_id=?",
                    (code, range_id),
                )
            if axis:
                connection.execute(
                    "UPDATE style_axis_steps SET state='failed',error_code=? WHERE style_run_id=? AND axis=? AND state!='complete'",
                    (code, style_run_id, axis),
                )
            if claim_id:
                connection.execute(
                    "UPDATE style_claim_steps SET state='failed',error_code=? WHERE style_run_id=? AND claim_id=?",
                    (code, style_run_id, claim_id),
                )

    def _prepare_round(self, run: sqlite3.Row, work: sqlite3.Row) -> None:
        next_round = int(work["current_round"]) + 1
        config = json.loads(run["sampling_config_json"])
        if next_round > int(config["max_rounds"]):
            raise _StepFailure("style_sampling_round_budget_exhausted")
        with self._connection() as connection:
            prior = connection.execute(
                "SELECT round_number,sampling_manifest_json,work_semantic_job_fingerprint,"
                "work_semantic_result_fingerprint FROM style_work_rounds WHERE style_run_id=? "
                "AND public_work_id=? ORDER BY round_number DESC LIMIT 1",
                (run["style_run_id"], work["public_work_id"]),
            ).fetchone()
        prior_manifest = json.loads(prior["sampling_manifest_json"]) if prior else None
        requested_roles = json.loads(work["requested_roles_json"])
        sampler = getattr(self.library, "sample_style_work", None)
        if not callable(sampler):
            raise _StepFailure("style_sampler_unavailable")
        try:
            result = sampler(
                run["study_id"], work["public_work_id"], requested_roles=requested_roles,
                max_windows=int(config["windows_per_round"]), prior_manifest=prior_manifest,
            )
        except Exception as exc:
            raise _StepFailure("style_sampling_failed") from exc
        if not isinstance(result, Mapping):
            raise _StepFailure("style_sampling_result_invalid")
        manifest = result.get("manifest")
        ephemeral = result.get("ephemeral_windows")
        if not isinstance(manifest, Mapping) or not isinstance(ephemeral, list):
            raise _StepFailure("style_sampling_result_invalid")
        # The sampler validator is authoritative for chapter/scene locators.
        try:
            from corpus.style_sampling import validate_sampling_manifest
            validation = validate_sampling_manifest(manifest)
        except Exception as exc:
            raise _StepFailure("style_sampling_manifest_invalid") from exc
        if validation not in (None, [], True):
            raise _StepFailure("style_sampling_manifest_invalid")
        source_binding = manifest.get("source_binding")
        source_fp = source_binding.get("source_fingerprint") if isinstance(source_binding, Mapping) else None
        if not isinstance(source_fp, str) or not _HASH_RE.fullmatch(source_fp):
            raise _StepFailure("style_sampling_source_binding_invalid")
        upstream_fp = result.get("upstream_source_fingerprint")
        if not isinstance(upstream_fp, str) or not _HASH_RE.fullmatch(upstream_fp):
            raise _StepFailure("style_sampling_upstream_binding_invalid")
        windows_by_id = {
            row.get("window_id"): row for row in manifest.get("windows", []) if isinstance(row, Mapping)
        }
        current_ids = manifest.get("current_window_ids")
        if not isinstance(current_ids, list) or len(current_ids) != len(ephemeral):
            raise _StepFailure("style_sampling_current_window_binding_invalid")
        if set(current_ids) != {row.get("window_id") for row in ephemeral if isinstance(row, Mapping)}:
            raise _StepFailure("style_sampling_current_window_binding_invalid")
        if not current_ids:
            # An initial round has no prior semantic evidence to preserve and
            # therefore cannot legally complete without an observation.
            if next_round == 1:
                raise _StepFailure("style_initial_sampling_evidence_missing")

            # A continuation request means the previous model profile found a
            # real evidence gap.  If deterministic retrieval cannot produce a
            # novel window, do not ask the model the same question again with
            # the same observations and a different round number.  Preserve
            # the last real model profile and its receipt, and record only the
            # runtime evidence boundary on the work step.
            profile_json = work["work_profile_json"]
            profile_fingerprint = work["work_profile_fingerprint"]
            try:
                profile = json.loads(profile_json) if isinstance(profile_json, str) else None
            except (TypeError, json.JSONDecodeError) as exc:
                raise _StepFailure("style_continuation_profile_invalid") from exc
            if (
                prior is None
                or int(prior["round_number"]) != int(work["current_round"])
                or not isinstance(profile, Mapping)
                or not isinstance(profile_fingerprint, str)
                or not _HASH_RE.fullmatch(profile_fingerprint)
                or _fingerprint(profile) != profile_fingerprint
                or not isinstance(prior["work_semantic_job_fingerprint"], str)
                or not _HASH_RE.fullmatch(prior["work_semantic_job_fingerprint"])
                or not isinstance(prior["work_semantic_result_fingerprint"], str)
                or not _HASH_RE.fullmatch(prior["work_semantic_result_fingerprint"])
                or work["saturation_state"] != "continue"
            ):
                raise _StepFailure("style_continuation_evidence_binding_invalid")
            self._validate_work_profile(profile, work_id=work["public_work_id"])
            if profile["saturation"]["state"] != "continue":
                raise _StepFailure("style_continuation_profile_state_invalid")
            with self._connection() as connection:
                updated = connection.execute(
                    "UPDATE style_work_steps SET state='complete',requested_roles_json='[]',"
                    "saturation_state='insufficient_available_evidence',error_code=NULL "
                    "WHERE style_run_id=? AND public_work_id=? AND state='pending' AND current_round=?",
                    (
                        run["style_run_id"], work["public_work_id"],
                        work["current_round"],
                    ),
                )
                if updated.rowcount != 1:
                    raise _StepFailure("style_continuation_state_conflict")
                connection.execute(
                    "UPDATE style_analysis_runs SET updated_at=? WHERE style_run_id=?",
                    (_utc_now(), run["style_run_id"]),
                )
            return
        ephemeral_by_id = {
            row.get("window_id"): row for row in ephemeral if isinstance(row, Mapping)
        }
        pending_cache: dict[str, dict[str, Any]] = {}
        now = _utc_now()
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO style_work_rounds(style_run_id,public_work_id,round_number,"
                "requested_roles_json,sampling_manifest_json,sampling_manifest_fingerprint,new_window_count,created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    run["style_run_id"], work["public_work_id"], next_round,
                    _json(requested_roles), _json(manifest), manifest.get("manifest_fingerprint"),
                    len(current_ids), now,
                ),
            )
            for window_id in current_ids:
                descriptor = windows_by_id.get(window_id)
                if not isinstance(descriptor, Mapping):
                    raise _StepFailure("style_sampling_descriptor_missing")
                role = descriptor.get("role")
                passage_fp = descriptor.get("passage_fingerprint")
                if role not in STYLE_SAMPLE_ROLES or not isinstance(passage_fp, str) or not _HASH_RE.fullmatch(passage_fp):
                    raise _StepFailure("style_sampling_descriptor_invalid")
                style_range_id = "STYLE-" + hashlib.sha256(
                    _canonical_bytes({"run": run["style_run_id"], "work": work["public_work_id"], "window": window_id})
                ).hexdigest()[:32]
                ephemeral_row = ephemeral_by_id.get(window_id)
                passage = ephemeral_row.get("text") if isinstance(ephemeral_row, Mapping) else None
                if (
                    not isinstance(passage, str)
                    or not passage
                    or len(passage) > 3000
                    or "sha256:" + hashlib.sha256(passage.encode("utf-8")).hexdigest()
                    != passage_fp
                    or ephemeral_row.get("source_fingerprint") != source_fp
                ):
                    raise _StepFailure("style_sampling_ephemeral_binding_invalid")
                pending_cache[style_range_id] = {
                    "schema": "quillframe_corpus_ephemeral_style_window_v1",
                    "passage": passage,
                    "source_fingerprint": source_fp,
                    "passage_fingerprint": passage_fp,
                    "paragraph_spans": [{
                        "span_ref": "SPAN-" + hashlib.sha256(
                            (style_range_id + ":1").encode("utf-8")
                        ).hexdigest()[:24],
                        "start": 0,
                        "end": len(passage),
                    }],
                    "persisted": False,
                }
                durable = {
                    "window_id": window_id, "span": descriptor.get("span"), "role": role,
                    "candidate_roles": descriptor.get("candidate_roles"),
                    "functional_layers": descriptor.get("functional_layers"),
                    "passage_fingerprint": passage_fp,
                    "unicode_chars": descriptor.get("unicode_chars"),
                    "chapter_ordinal": descriptor.get("chapter_ordinal"),
                    "scene_ordinal": descriptor.get("scene_ordinal"),
                    "paragraph_start_ordinal": descriptor.get("paragraph_start_ordinal"),
                    "paragraph_end_ordinal": descriptor.get("paragraph_end_ordinal"),
                    "source_fingerprint": source_fp,
                    "upstream_source_fingerprint": upstream_fp,
                }
                connection.execute(
                    "INSERT INTO style_sample_steps(style_range_id,style_run_id,public_work_id,"
                    "round_number,scene_function,descriptor_json,descriptor_fingerprint,source_fingerprint,"
                    "passage_fingerprint,state) VALUES(?,?,?,?,?,?,?,?,?,'pending')",
                    (
                        style_range_id, run["style_run_id"], work["public_work_id"], next_round,
                        role, _json(durable), _fingerprint(durable), source_fp, passage_fp,
                    ),
                )
            connection.execute(
                "UPDATE style_work_steps SET current_round=?,state='sampling_ready',error_code=NULL "
                "WHERE style_run_id=? AND public_work_id=?",
                (next_round, run["style_run_id"], work["public_work_id"]),
            )
        self._ephemeral_windows.update(pending_cache)

    def _execute_sample(
        self, run: sqlite3.Row, work: sqlite3.Row, sample: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        descriptor = json.loads(sample["descriptor_json"])
        ephemeral = self._ephemeral_windows.pop(sample["style_range_id"], None)
        if ephemeral is None:
            materializer = getattr(self.library, "materialize_style_window", None)
            if not callable(materializer):
                raise _StepFailure("style_window_materializer_unavailable")
            try:
                ephemeral = materializer(
                    run["study_id"], work["public_work_id"], descriptor
                )
            except Exception as exc:
                raise _StepFailure("style_window_materialization_failed") from exc
        if not isinstance(ephemeral, Mapping):
            raise _StepFailure("style_window_materialization_invalid")
        passage = ephemeral.get("passage")
        spans = ephemeral.get("paragraph_spans")
        if (
            not isinstance(passage, str) or not passage or len(passage) > 3000
            or ephemeral.get("passage_fingerprint") != sample["passage_fingerprint"]
            or ephemeral.get("source_fingerprint") != sample["source_fingerprint"]
            or not isinstance(spans, list) or not spans
        ):
            raise _StepFailure("style_window_materialization_binding_mismatch")
        span_refs = {
            row.get("span_ref") for row in spans if isinstance(row, Mapping) and isinstance(row.get("span_ref"), str)
        }
        if len(span_refs) != len(spans):
            raise _StepFailure("style_window_paragraph_spans_invalid")
        payload = {
            "style_range_id": sample["style_range_id"],
            "retrieval_scene_function_hint": sample["scene_function"],
            "passage": passage,
            "passage_fingerprint": sample["passage_fingerprint"],
            "paragraph_spans": spans,
            "style_axes": list(STYLE_AXES),
            "content_profile": run["profile"],
        }
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_sample_steps SET state='running',attempt_count=attempt_count+1,error_code=NULL "
                "WHERE style_range_id=?", (sample["style_range_id"],),
            )
            connection.execute(
                "UPDATE style_analysis_runs SET attempt_count=attempt_count+1,updated_at=? WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="corpus.style_observe", subject_id=sample["style_range_id"], payload=payload,
            style_run_id=run["style_run_id"], run_semantic=run_semantic, raw_passage=True,
        )
        self._validate_range_judgment(
            judgment, style_range_id=sample["style_range_id"], span_refs=span_refs,
            profile=run["profile"],
        )
        self._assert_no_passage_overlap(passage, judgment)
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_sample_steps SET state='complete',semantic_job_fingerprint=?,"
                "semantic_result_fingerprint=?,judgment_json=?,judgment_fingerprint=?,error_code=NULL "
                "WHERE style_range_id=?",
                (job_fp, result_fp, _json(judgment), _fingerprint(judgment), sample["style_range_id"]),
            )

    def _execute_work_synthesis(
        self, run: sqlite3.Row, work: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT style_range_id,scene_function,judgment_json FROM style_sample_steps "
                "WHERE style_run_id=? AND public_work_id=? AND state='complete' "
                "ORDER BY round_number,style_range_id",
                (run["style_run_id"], work["public_work_id"]),
            ).fetchall()
        if not rows:
            raise _StepFailure("style_work_observations_missing")
        observations = [json.loads(row["judgment_json"]) for row in rows]
        observed_scene_functions = [
            role
            for role in STYLE_SAMPLE_ROLES
            if any(role in judgment["observed_scene_functions"] for judgment in observations)
        ]
        payload = {
            "public_work_id": work["public_work_id"],
            "analysis_round": work["current_round"],
            "style_axes": list(STYLE_AXES),
            "observed_scene_functions": observed_scene_functions,
            "window_observations": [
                {"style_range_id": row["style_range_id"], "observation": judgment}
                for row, judgment in zip(rows, observations, strict=True)
            ],
            "content_profile": run["profile"],
        }
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_work_steps SET state='synthesizing',attempt_count=attempt_count+1,error_code=NULL "
                "WHERE style_run_id=? AND public_work_id=?",
                (run["style_run_id"], work["public_work_id"]),
            )
            connection.execute(
                "UPDATE style_analysis_runs SET attempt_count=attempt_count+1,updated_at=? WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="learning.style_work_synthesize", subject_id=work["public_work_id"],
            payload=payload, style_run_id=run["style_run_id"], run_semantic=run_semantic,
        )
        self._validate_work_profile(judgment, work_id=work["public_work_id"])
        saturation = judgment["saturation"]["state"]
        gaps = judgment["coverage_gaps"]
        requested_roles = self._ordered_requested_roles(gaps)
        config = json.loads(run["sampling_config_json"])
        continue_sampling = (
            saturation == "continue"
            and int(work["current_round"]) < int(config["max_rounds"])
        )
        runtime_saturation = saturation
        if saturation == "continue" and not continue_sampling:
            runtime_saturation = "round_budget_or_available_evidence_exhausted"
        with self._connection() as connection:
            updated_round = connection.execute(
                "UPDATE style_work_rounds SET work_semantic_job_fingerprint=?,"
                "work_semantic_result_fingerprint=? WHERE style_run_id=? AND public_work_id=? "
                "AND round_number=?",
                (
                    job_fp, result_fp, run["style_run_id"], work["public_work_id"],
                    work["current_round"],
                ),
            )
            if updated_round.rowcount != 1:
                raise _StepFailure("style_work_round_binding_missing")
            connection.execute(
                "UPDATE style_work_steps SET state=?,requested_roles_json=?,work_profile_json=?,"
                "work_profile_fingerprint=?,saturation_state=?,error_code=NULL "
                "WHERE style_run_id=? AND public_work_id=?",
                (
                    "pending" if continue_sampling else "complete",
                    _json(requested_roles if continue_sampling else []),
                    _json(judgment), _fingerprint(judgment), runtime_saturation,
                    run["style_run_id"], work["public_work_id"],
                ),
            )

    # ------------------------------------------------------------------
    # Cross-work synthesis, held-out verification and compilation
    # ------------------------------------------------------------------
    def _prepare_axis_steps(self, run: sqlite3.Row) -> None:
        config = json.loads(run["sampling_config_json"])
        batch_size = int(config["axis_batch_size"])
        with self._connection() as connection:
            incomplete = connection.execute(
                "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                "AND activation_cycle IS NOT NULL AND state!='complete'",
                (run["style_run_id"],),
            ).fetchone()[0]
            if incomplete:
                raise _StepFailure("style_work_profiles_incomplete")
            if run["discovery_converged"]:
                self._materialize_reconciled_claims(connection, run)
                connection.execute(
                    "UPDATE style_analysis_runs SET phase='claim_verification',updated_at=? "
                    "WHERE style_run_id=?",
                    (_utc_now(), run["style_run_id"]),
                )
                return
            cycle = int(run["cohort_cycle"])
            if cycle < 1:
                raise _StepFailure("style_cohort_cycle_invalid")
            new_rows = connection.execute(
                "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                "AND split='discovery' AND activation_cycle=? AND state='complete' ORDER BY ordinal",
                (run["style_run_id"], cycle),
            ).fetchall()
            ids = [row["public_work_id"] for row in new_rows]
            if not ids:
                raise _StepFailure("style_discovery_cohort_empty")
            existing = connection.execute(
                "SELECT COUNT(*) FROM style_axis_steps WHERE style_run_id=? "
                "AND cohort_cycle=? AND batch_ordinal>0",
                (run["style_run_id"], cycle),
            ).fetchone()[0]
            if not existing:
                anchors = [
                    row["public_work_id"]
                    for row in connection.execute(
                        "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                        "AND split='discovery' AND activation_cycle<? AND state='complete' ORDER BY ordinal",
                        (run["style_run_id"], cycle),
                    )
                ]
                batches = [ids[index:index + batch_size] for index in range(0, len(ids), batch_size)]
                for batch in batches:
                    for anchor in anchors:
                        if len(batch) >= 3:
                            break
                        if anchor not in batch:
                            batch.append(anchor)
                    if len(batch) < 2 or len(batch) > DEFAULT_AXIS_BATCH_SIZE:
                        raise _StepFailure("style_discovery_cohort_insufficient")
                for axis in STYLE_AXES:
                    next_ordinal = connection.execute(
                        "SELECT COALESCE(MAX(batch_ordinal),0)+1 FROM style_axis_steps "
                        "WHERE style_run_id=? AND axis=? AND batch_ordinal>0",
                        (run["style_run_id"], axis),
                    ).fetchone()[0]
                    for offset, batch in enumerate(batches):
                        connection.execute(
                            "INSERT INTO style_axis_steps(style_run_id,axis,batch_ordinal,"
                            "cohort_cycle,discovery_work_ids_json,state) VALUES(?,?,?,?,?,'pending')",
                            (
                                run["style_run_id"], axis, next_ordinal + offset,
                                cycle, _json(batch),
                            ),
                        )
            connection.execute(
                "UPDATE style_analysis_runs SET phase='axis_synthesis',updated_at=? WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )

    def _execute_axis_step(
        self, run: sqlite3.Row, step: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        work_ids = json.loads(step["discovery_work_ids_json"])
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT public_work_id,work_profile_json,saturation_state,current_round "
                "FROM style_work_steps WHERE style_run_id=? "
                "AND public_work_id IN (%s)" % ",".join("?" for _ in work_ids),
                (run["style_run_id"], *work_ids),
            ).fetchall()
        work_evidence = {row["public_work_id"]: row for row in rows}
        if set(work_evidence) != set(work_ids):
            raise _StepFailure("style_axis_work_profile_binding_missing")
        profiles: dict[str, dict[str, Any]] = {}
        runtime_evidence: dict[str, dict[str, Any]] = {}
        terminal_states = {
            "saturated",
            "insufficient_available_evidence",
            "round_budget_or_available_evidence_exhausted",
        }
        for work_id in work_ids:
            row = work_evidence[work_id]
            try:
                profile = json.loads(row["work_profile_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise _StepFailure("style_axis_work_profile_binding_missing") from exc
            state = row["saturation_state"]
            profile_state = (
                profile.get("saturation", {}).get("state")
                if isinstance(profile, Mapping)
                else None
            )
            if state not in terminal_states or profile_state not in {
                "continue", "saturated", "insufficient_available_evidence",
            }:
                raise _StepFailure("style_axis_work_evidence_state_invalid")
            profiles[work_id] = profile
            runtime_evidence[work_id] = {
                "state": state,
                "last_semantic_round": int(row["current_round"]),
                "profile_saturation_state": profile_state,
            }
        payload = {
            "axis": step["axis"],
            "batch_id": (
                f"{run['style_run_id']}:{step['axis']}:"
                f"{step['cohort_cycle']}:{step['batch_ordinal']}"
            ),
            "content_profile": run["profile"],
            "discovery_work_profiles": [
                {
                    "public_work_id": work_id,
                    "profile": profiles[work_id],
                    "runtime_evidence": runtime_evidence[work_id],
                }
                for work_id in work_ids
            ],
        }
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_axis_steps SET state='running',attempt_count=attempt_count+1,error_code=NULL "
                "WHERE style_run_id=? AND axis=? AND batch_ordinal=?",
                (run["style_run_id"], step["axis"], step["batch_ordinal"]),
            )
            connection.execute(
                "UPDATE style_analysis_runs SET attempt_count=attempt_count+1,updated_at=? WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="learning.style_axis_synthesize",
            subject_id=f"AXIS-{step['axis']}-{step['batch_ordinal']}", payload=payload,
            style_run_id=run["style_run_id"], run_semantic=run_semantic,
        )
        self._validate_axis_judgment(
            judgment, axis=step["axis"], work_ids=set(work_ids), profile=run["profile"],
        )
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_axis_steps SET state='complete',semantic_job_fingerprint=?,"
                "semantic_result_fingerprint=?,judgment_json=?,error_code=NULL WHERE style_run_id=? "
                "AND axis=? AND batch_ordinal=?",
                (job_fp, result_fp, _json(judgment), run["style_run_id"], step["axis"], step["batch_ordinal"]),
            )

    def _prepare_axis_reconcile_steps(self, run: sqlite3.Row) -> None:
        """Checkpoint one source-free reconciliation call for every style axis."""

        with self._connection() as connection:
            cycle = int(run["cohort_cycle"])
            incomplete_batches = connection.execute(
                "SELECT COUNT(*) FROM style_axis_steps WHERE style_run_id=? "
                "AND cohort_cycle=? AND batch_ordinal>0 AND state!='complete'",
                (run["style_run_id"], cycle),
            ).fetchone()[0]
            if incomplete_batches:
                raise _StepFailure("style_axis_batches_incomplete")
            pre_reconcile_claims = connection.execute(
                "SELECT COUNT(*) FROM style_claim_steps WHERE style_run_id=? "
                "AND batch_ordinal!=0",
                (run["style_run_id"],),
            ).fetchone()[0]
            if pre_reconcile_claims:
                raise _StepFailure("style_pre_reconcile_claims_present")
            for axis in STYLE_AXES:
                batch_count = connection.execute(
                    "SELECT COUNT(*) FROM style_axis_steps WHERE style_run_id=? AND axis=? "
                    "AND cohort_cycle=? AND batch_ordinal>0",
                    (run["style_run_id"], axis, cycle),
                ).fetchone()[0]
                if not batch_count:
                    raise _StepFailure("style_axis_batches_missing")
                connection.execute(
                    "INSERT OR IGNORE INTO style_axis_steps(style_run_id,axis,batch_ordinal,"
                    "cohort_cycle,discovery_work_ids_json,state) VALUES(?,?,?,?, '[]','pending')",
                    (run["style_run_id"], axis, -cycle, cycle),
                )

    def _execute_axis_reconcile_step(
        self,
        run: sqlite3.Row,
        step: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        axis = step["axis"]
        cycle = int(step["cohort_cycle"])
        reconciliation_id = f"{run['style_run_id']}:{axis}:reconcile:{cycle}"
        with self._connection() as connection:
            batches = connection.execute(
                "SELECT batch_ordinal,cohort_cycle,judgment_json FROM style_axis_steps "
                "WHERE style_run_id=? AND axis=? AND cohort_cycle<=? AND batch_ordinal>0 "
                "AND state='complete' ORDER BY cohort_cycle,batch_ordinal",
                (run["style_run_id"], axis, cycle),
            ).fetchall()
            eligible_ids = [
                row["public_work_id"]
                for row in connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                    "AND split='discovery' AND activation_cycle IS NULL ORDER BY ordinal",
                    (run["style_run_id"],),
                )
            ]
        if not batches:
            raise _StepFailure("style_axis_batches_missing")
        batch_syntheses: list[dict[str, Any]] = []
        work_ids: set[str] = set()
        for batch in batches:
            judgment = json.loads(batch["judgment_json"])
            claims = judgment["claims"]
            for claim in claims:
                work_ids.update(claim["supporting_work_ids"])
                work_ids.update(claim["counterexample_work_ids"])
            batch_syntheses.append({
                "batch_id": (
                    f"{run['style_run_id']}:{axis}:"
                    f"{batch['cohort_cycle']}:{batch['batch_ordinal']}"
                ),
                "claims": claims,
                "contested_questions": judgment["contested_questions"],
            })
        with self._connection() as connection:
            discovery_ids = {
                row["public_work_id"]
                for row in connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                    "AND split='discovery' AND state='complete'",
                    (run["style_run_id"],),
                )
            }
        if not discovery_ids or not work_ids.issubset(discovery_ids):
            raise _StepFailure("style_axis_reconcile_evidence_binding_invalid")
        payload = {
            "axis": axis,
            "reconciliation_id": reconciliation_id,
            "content_profile": run["profile"],
            "batch_syntheses": batch_syntheses,
            "eligible_discovery_work_ids": eligible_ids,
        }
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_axis_steps SET state='running',attempt_count=attempt_count+1,error_code=NULL "
                "WHERE style_run_id=? AND axis=? AND batch_ordinal=?",
                (run["style_run_id"], axis, -cycle),
            )
            connection.execute(
                "UPDATE style_analysis_runs SET attempt_count=attempt_count+1,updated_at=? "
                "WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="learning.style_axis_reconcile",
            subject_id=f"AXIS-{axis}-RECONCILE",
            payload=payload,
            style_run_id=run["style_run_id"],
            run_semantic=run_semantic,
        )
        self._validate_axis_reconciliation(
            judgment,
            axis=axis,
            reconciliation_id=reconciliation_id,
            work_ids=work_ids,
            eligible_work_ids=set(eligible_ids),
            profile=run["profile"],
        )
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_axis_steps SET state='complete',semantic_job_fingerprint=?,"
                "semantic_result_fingerprint=?,judgment_json=?,error_code=NULL WHERE style_run_id=? "
                "AND axis=? AND batch_ordinal=?",
                (
                    job_fp, result_fp, _json(judgment),
                    run["style_run_id"], axis, -cycle,
                ),
            )

    def _materialize_reconciled_claims(
        self, connection: sqlite3.Connection, run: sqlite3.Row,
    ) -> None:
        cycle = int(run["cohort_cycle"]) - 1
        rows = connection.execute(
            "SELECT axis,judgment_json FROM style_axis_steps WHERE style_run_id=? "
            "AND cohort_cycle=? AND batch_ordinal=? AND state='complete' ORDER BY axis",
            (run["style_run_id"], cycle, -cycle),
        ).fetchall()
        if len(rows) != len(STYLE_AXES):
            raise _StepFailure("style_axis_reconciliations_missing")
        for row in rows:
            judgment = json.loads(row["judgment_json"])
            if judgment["convergence"]["state"] != "converged":
                raise _StepFailure("style_axis_convergence_binding_invalid")
            for claim in judgment["claims"]:
                claim_material = {
                    "axis": row["axis"], "stage": "reconciled",
                    "cohort_cycle": cycle, "claim": claim,
                }
                claim_id = "CLAIM-" + hashlib.sha256(
                    _canonical_bytes(claim_material)
                ).hexdigest()[:32]
                connection.execute(
                    "INSERT OR IGNORE INTO style_claim_steps(style_run_id,claim_id,axis,"
                    "batch_ordinal,candidate_claim_json,candidate_claim_fingerprint,state) "
                    "VALUES(?,?,?,?,?,?,'pending')",
                    (
                        run["style_run_id"], claim_id, row["axis"], -cycle,
                        _json(claim), _fingerprint(claim),
                    ),
                )

    def _advance_after_reconciliation(self, run: sqlite3.Row) -> None:
        cycle = int(run["cohort_cycle"])
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT axis,judgment_json FROM style_axis_steps WHERE style_run_id=? "
                "AND cohort_cycle=? AND batch_ordinal=? AND state='complete'",
                (run["style_run_id"], cycle, -cycle),
            ).fetchall()
            if len(rows) != len(STYLE_AXES):
                raise _StepFailure("style_axis_reconciliations_missing")
            judgments = {row["axis"]: json.loads(row["judgment_json"]) for row in rows}
            states = {
                axis: judgments[axis]["convergence"]["state"] for axis in STYLE_AXES
            }
            if "continue" in states.values():
                requested: dict[str, list[str]] = {}
                for axis in STYLE_AXES:
                    if states[axis] != "continue":
                        continue
                    for request in judgments[axis]["next_evidence_requests"]:
                        for work_id in request["public_work_ids"]:
                            combined = set(requested.get(work_id, []))
                            combined.update(request["scene_functions"])
                            requested[work_id] = self._ordered_requested_roles(combined)
                if not requested:
                    connection.execute(
                        "UPDATE style_analysis_runs SET result_state='insufficient_axis_convergence',"
                        "phase='compilation',updated_at=? WHERE style_run_id=?",
                        (_utc_now(), run["style_run_id"]),
                    )
                    return
                self._activate_works(
                    connection,
                    run,
                    cycle=cycle + 1,
                    kind="adaptive",
                    requests=requested,
                )
                return
            if all(state == "converged" for state in states.values()):
                config = json.loads(run["sampling_config_json"])
                limit = int(config["holdout_cohort_work_count"])
                holdouts = connection.execute(
                    "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                    "AND split='holdout' AND activation_cycle IS NULL ORDER BY ordinal LIMIT ?",
                    (run["style_run_id"], limit),
                ).fetchall()
                if not holdouts:
                    raise _StepFailure("style_holdout_split_invalid")
                connection.execute(
                    "UPDATE style_analysis_runs SET discovery_converged=1 WHERE style_run_id=?",
                    (run["style_run_id"],),
                )
                self._activate_works(
                    connection,
                    run,
                    cycle=cycle + 1,
                    kind="holdout",
                    requests={
                        row["public_work_id"]: STYLE_SAMPLE_ROLES for row in holdouts
                    },
                )
                return
            connection.execute(
                "UPDATE style_analysis_runs SET result_state='insufficient_axis_convergence',"
                "phase='compilation',updated_at=? WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )

    def _execute_claim_step(
        self, run: sqlite3.Row, claim: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT public_work_id,work_profile_json FROM style_work_steps WHERE style_run_id=? "
                "AND split='holdout' AND state='complete' ORDER BY ordinal", (run["style_run_id"],),
            ).fetchall()
        holdout_ids = {row["public_work_id"] for row in rows}
        if not holdout_ids or len(holdout_ids) > 32:
            raise _StepFailure("style_holdout_split_invalid")
        candidate = json.loads(claim["candidate_claim_json"])
        payload = {
            "claim_id": claim["claim_id"], "axis": claim["axis"],
            "content_profile": run["profile"], "candidate_claim": candidate,
            "holdout_work_profiles": [
                {"public_work_id": row["public_work_id"], "profile": json.loads(row["work_profile_json"])}
                for row in rows
            ],
        }
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_claim_steps SET state='running',attempt_count=attempt_count+1,error_code=NULL "
                "WHERE style_run_id=? AND claim_id=?", (run["style_run_id"], claim["claim_id"]),
            )
            connection.execute(
                "UPDATE style_analysis_runs SET attempt_count=attempt_count+1,updated_at=? WHERE style_run_id=?",
                (_utc_now(), run["style_run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="learning.style_claim_verify", subject_id=claim["claim_id"], payload=payload,
            style_run_id=run["style_run_id"], run_semantic=run_semantic,
        )
        self._validate_claim_verification(
            judgment, claim_id=claim["claim_id"], holdout_ids=holdout_ids,
        )
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_claim_steps SET state='complete',verdict=?,semantic_job_fingerprint=?,"
                "semantic_result_fingerprint=?,verification_json=?,verification_fingerprint=?,error_code=NULL "
                "WHERE style_run_id=? AND claim_id=?",
                (judgment["verdict"], job_fp, result_fp, _json(judgment), _fingerprint(judgment),
                 run["style_run_id"], claim["claim_id"]),
            )

    @staticmethod
    def _evidence_ref(claim_id: str, work_id: str, role: str, stage: str) -> dict[str, Any]:
        material = {"claim_id": claim_id, "work_id": work_id, "role": role, "stage": stage}
        return {
            "work_id": work_id,
            "evidence_id": f"{stage}:{claim_id}:{work_id}",
            "role": role,
            "evidence_fingerprint": style_fingerprint(material),
        }

    def _leakage_summary(self, run: sqlite3.Row, candidate_text: str) -> dict[str, Any]:
        batcher = getattr(self.library, "style_leakage_reference_batches", None)
        if not callable(batcher):
            base = {
                "schema": "quillframe_style_leakage_summary_v1", "local_status": "not_performed",
                "release_ready": False, "candidate_text_fingerprint": "sha256:" + hashlib.sha256(
                    candidate_text.encode("utf-8")
                ).hexdigest(), "reference_count": 0, "batch_report_fingerprints": [],
                "semantic_check": "required_external",
            }
            base["summary_fingerprint"] = _fingerprint(base)
            return base
        report_fps: list[str] = []
        reference_count = 0
        blocked = False
        try:
            with self._connection() as connection:
                used_work_ids = [
                    row["public_work_id"]
                    for row in connection.execute(
                        "SELECT public_work_id FROM style_work_steps WHERE style_run_id=? "
                        "AND activation_cycle IS NOT NULL AND state='complete' ORDER BY ordinal",
                        (run["style_run_id"],),
                    )
                ]
            if not used_work_ids:
                raise _StepFailure("style_leakage_used_cohort_missing")
            batches = batcher(run["study_id"], public_work_ids=used_work_ids)
            for batch in batches:
                if not isinstance(batch, Mapping) or not batch:
                    raise _StepFailure("style_leakage_reference_batch_invalid")
                report = check_local_leakage(candidate_text, batch)
                report_fps.append(report["report_fingerprint"])
                reference_count += len(batch)
                blocked = blocked or report["local_status"] == "blocked"
        except _StepFailure:
            raise
        except Exception as exc:
            raise _StepFailure("style_local_leakage_check_failed") from exc
        base = {
            "schema": "quillframe_style_leakage_summary_v1",
            "local_status": "blocked" if blocked else "pass",
            "release_ready": False,
            "candidate_text_fingerprint": "sha256:" + hashlib.sha256(candidate_text.encode("utf-8")).hexdigest(),
            "reference_count": reference_count,
            "batch_report_fingerprints": report_fps,
            "semantic_check": "required_external",
        }
        base["summary_fingerprint"] = _fingerprint(base)
        return base

    def _compile_candidate_bundle(self, run: sqlite3.Row) -> dict[str, Any]:
        with self._connection() as connection:
            reconciliation = self._axis_reconciliation_status(
                connection, run["style_run_id"]
            )
            rows = connection.execute(
                "SELECT * FROM style_claim_steps WHERE style_run_id=? AND state='complete' "
                "ORDER BY axis,claim_id", (run["style_run_id"],),
            ).fetchall()
        axes_converged = (
            set(reconciliation) == set(STYLE_AXES)
            and all(
                item.get("step_state") == "complete"
                and item.get("convergence", {}).get("state") == "converged"
                for item in reconciliation.values()
            )
        )

        def blocked_bundle(result_state: str, missing_gates: list[str]) -> dict[str, Any]:
            bundle: dict[str, Any] = {
                "schema": "quillframe_corpus_style_candidate_bundle_v1",
                "analysis_protocol_id": STYLE_PROTOCOL_ID,
                "public_study_id": run["public_study_id"], "profile": run["profile"],
                "result_state": result_state, "style_contract": None,
                "writer_projection": None, "candidate_artifact_fingerprint": None,
                "craft_pack_fingerprint": None, "local_leakage": None,
                "promotion_state": "blocked", "missing_gates": missing_gates,
                "activation_performed": False, "promotion_performed": False,
                "authority": False,
            }
            bundle["bundle_fingerprint"] = _fingerprint(bundle)
            return bundle

        verified_rows = []
        for row in rows:
            verification = json.loads(row["verification_json"])
            if row["verdict"] not in {"promote", "narrow"}:
                continue
            if verification.get("content_disentanglement", {}).get("passed") is not True:
                continue
            verified_rows.append((row, json.loads(row["candidate_claim_json"]), verification))
        if not verified_rows:
            missing_gates = ["heldout_verified_claims"]
            if not axes_converged:
                missing_gates.insert(0, "axis_semantic_convergence")
            return blocked_bundle(
                "insufficient_verified_claims" if axes_converged
                else "blocked_axis_convergence",
                missing_gates,
            )
        candidates = []
        invalid_candidate = False
        for row, claim, verification in verified_rows:
            evidence_refs = []
            for work_id in claim["supporting_work_ids"]:
                evidence_refs.append(self._evidence_ref(row["claim_id"], work_id, "support", "discovery"))
            for work_id in claim["counterexample_work_ids"]:
                evidence_refs.append(self._evidence_ref(row["claim_id"], work_id, "counterexample", "discovery"))
            for work_id in verification["supporting_holdout_work_ids"]:
                evidence_refs.append(self._evidence_ref(row["claim_id"], work_id, "support", "holdout"))
            for work_id in verification["counterexample_holdout_work_ids"]:
                evidence_refs.append(self._evidence_ref(row["claim_id"], work_id, "counterexample", "holdout"))
            confidence = min(float(claim.get("confidence", 0)), float(verification.get("confidence", 0)))
            applies_when = list(claim["applies_when"])
            applies_when.extend(
                f"scene_function={scene_function}"
                for scene_function in claim["scene_functions"]
                if f"scene_function={scene_function}" not in applies_when
            )
            try:
                candidates.append(make_craft_candidate(
                    record_id=row["claim_id"], axis=row["axis"],
                    operation=verification["verified_operation"], effect=claim["desired_effect"],
                    applies_when=applies_when, avoid_when=claim["avoid_when"],
                    failure_boundary=verification["verified_boundary"], content_zone=run["profile"],
                    evidence_refs=evidence_refs,
                    supports=["cross_work_discovery", "heldout_replication"],
                    counterexamples=["discovery_or_holdout_counterexample"],
                    confidence_ppm=max(0, min(1_000_000, round(confidence * 1_000_000))),
                ))
            except StyleContractError:
                invalid_candidate = True
        compilation_gates = []
        if invalid_candidate:
            compilation_gates.append("candidate_record_contract_validity")
        if len(candidates) > MAX_CANDIDATES:
            compilation_gates.append("candidate_count_within_contract_bounds")
        if compilation_gates:
            return blocked_bundle("blocked_candidate_compilation", compilation_gates)
        contract_id = "STYLE-" + hashlib.sha256(
            (run["style_run_id"] + "\0" + run["checklist_hash"]).encode("utf-8")
        ).hexdigest()[:32]
        contract = compile_style_contract(contract_id, candidates, content_zone=run["profile"])
        writer_projection = compile_writer_projection(contract)
        candidate_text = _json(contract)
        leakage = self._leakage_summary(run, candidate_text)
        craft_pack_fingerprint = writer_projection["projection_fingerprint"]
        candidate_artifact_fingerprint = _fingerprint({
            "style_contract": contract,
            "writer_projection": writer_projection,
            "local_leakage_summary_fingerprint": leakage["summary_fingerprint"],
        })
        missing = [
            "independent_semantic_leakage_review", "baseline_v3_corpus_blind_ab",
            "leave_one_work_out_regression", "green_framework_ci", "human_promotion_review",
        ]
        if not axes_converged:
            missing.insert(0, "axis_semantic_convergence")
        if leakage["local_status"] != "pass":
            missing.insert(0, "local_leakage_pass")
        result_state = "candidate"
        if not axes_converged:
            result_state = "blocked_axis_convergence"
        elif leakage["local_status"] != "pass":
            result_state = "blocked_local_leakage"
        bundle = {
            "schema": "quillframe_corpus_style_candidate_bundle_v1",
            "analysis_protocol_id": STYLE_PROTOCOL_ID,
            "public_study_id": run["public_study_id"], "profile": run["profile"],
            "result_state": result_state,
            "style_contract": contract, "writer_projection": writer_projection,
            "candidate_artifact_fingerprint": candidate_artifact_fingerprint,
            "craft_pack_fingerprint": craft_pack_fingerprint,
            "local_leakage": leakage,
            "promotion_state": "manual_review_required" if axes_converged else "blocked",
            "missing_gates": missing, "activation_performed": False,
            "promotion_performed": False, "authority": False,
        }
        bundle["bundle_fingerprint"] = _fingerprint(bundle)
        return bundle

    def _semantic_evidence_fingerprint(self, style_run_id: str) -> str:
        """Bind every completed semantic job/result pair in protocol order."""

        axis_order = {axis: ordinal for ordinal, axis in enumerate(STYLE_AXES)}
        ordered: list[tuple[tuple[Any, ...], str, str]] = []

        def append_pair(key: tuple[Any, ...], job_fp: Any, result_fp: Any) -> None:
            if (
                not isinstance(job_fp, str) or not _HASH_RE.fullmatch(job_fp)
                or not isinstance(result_fp, str) or not _HASH_RE.fullmatch(result_fp)
            ):
                raise _StepFailure("style_semantic_evidence_incomplete")
            ordered.append((key, job_fp, result_fp))

        with self._connection() as connection:
            work_ordinals = {
                row["public_work_id"]: row["ordinal"]
                for row in connection.execute(
                    "SELECT public_work_id,ordinal FROM style_work_steps WHERE style_run_id=?",
                    (style_run_id,),
                )
            }
            for row in connection.execute(
                "SELECT public_work_id,round_number,style_range_id,semantic_job_fingerprint,"
                "semantic_result_fingerprint FROM style_sample_steps WHERE style_run_id=? "
                "AND state='complete'",
                (style_run_id,),
            ):
                append_pair(
                    (
                        0, work_ordinals[row["public_work_id"]], row["round_number"],
                        0, row["style_range_id"],
                    ),
                    row["semantic_job_fingerprint"],
                    row["semantic_result_fingerprint"],
                )
            for row in connection.execute(
                "SELECT public_work_id,round_number,work_semantic_job_fingerprint,"
                "work_semantic_result_fingerprint FROM style_work_rounds WHERE style_run_id=?",
                (style_run_id,),
            ):
                append_pair(
                    (0, work_ordinals[row["public_work_id"]], row["round_number"], 1, ""),
                    row["work_semantic_job_fingerprint"],
                    row["work_semantic_result_fingerprint"],
                )
            for row in connection.execute(
                "SELECT axis,batch_ordinal,cohort_cycle,semantic_job_fingerprint,semantic_result_fingerprint "
                "FROM style_axis_steps WHERE style_run_id=? AND state='complete'",
                (style_run_id,),
            ):
                stage = 1 if row["batch_ordinal"] > 0 else 2
                append_pair(
                    (
                        stage, row["cohort_cycle"], axis_order[row["axis"]],
                        abs(row["batch_ordinal"]),
                    ),
                    row["semantic_job_fingerprint"],
                    row["semantic_result_fingerprint"],
                )
            for row in connection.execute(
                "SELECT axis,claim_id,semantic_job_fingerprint,semantic_result_fingerprint "
                "FROM style_claim_steps WHERE style_run_id=? AND state='complete'",
                (style_run_id,),
            ):
                append_pair(
                    (3, axis_order[row["axis"]], row["claim_id"]),
                    row["semantic_job_fingerprint"],
                    row["semantic_result_fingerprint"],
                )
        if not ordered:
            raise _StepFailure("style_semantic_evidence_missing")
        material = {
            "schema": "quillframe_ordered_semantic_evidence_v1",
            "ordered_pairs": [
                {"job_fingerprint": job_fp, "result_fingerprint": result_fp}
                for _key, job_fp, result_fp in sorted(ordered, key=lambda row: row[0])
            ],
        }
        return _fingerprint(material)

    def _used_source_set_fingerprint(self, style_run_id: str) -> str:
        with self._connection() as connection:
            works = connection.execute(
                "SELECT public_work_id,ordinal,activation_cycle,activation_kind,state "
                "FROM style_work_steps WHERE style_run_id=? AND activation_cycle IS NOT NULL "
                "ORDER BY ordinal",
                (style_run_id,),
            ).fetchall()
            if not works or any(row["state"] != "complete" for row in works):
                raise _StepFailure("style_used_source_set_incomplete")
            used_sources = []
            for work in works:
                source_fingerprints = [
                    row["source_fingerprint"]
                    for row in connection.execute(
                        "SELECT DISTINCT source_fingerprint FROM style_sample_steps "
                        "WHERE style_run_id=? AND public_work_id=? AND state='complete' "
                        "ORDER BY source_fingerprint",
                        (style_run_id, work["public_work_id"]),
                    )
                ]
                if not source_fingerprints or any(
                    not _HASH_RE.fullmatch(value) for value in source_fingerprints
                ):
                    raise _StepFailure("style_used_source_set_incomplete")
                used_sources.append({
                    "public_work_id": work["public_work_id"],
                    "ordinal": work["ordinal"],
                    "activation_cycle": work["activation_cycle"],
                    "activation_kind": work["activation_kind"],
                    "source_fingerprints": source_fingerprints,
                })
        return _fingerprint({
            "schema": "quillframe_style_used_source_set_v1",
            "style_run_id": style_run_id,
            "used_sources": used_sources,
        })

    def _finalize(self, run: sqlite3.Row) -> None:
        bundle = self._compile_candidate_bundle(run)
        self._assert_safe_derived(bundle, context="style_candidate_bundle")
        semantic_evidence_fingerprint = self._semantic_evidence_fingerprint(
            run["style_run_id"]
        )
        used_source_set_fingerprint = self._used_source_set_fingerprint(
            run["style_run_id"]
        )
        with self._connection() as connection:
            current = connection.execute(
                "SELECT semantic_evidence_fingerprint,used_source_set_fingerprint "
                "FROM style_analysis_runs "
                "WHERE style_run_id=?",
                (run["style_run_id"],),
            ).fetchone()
            if current is None or (
                current["semantic_evidence_fingerprint"] is not None
                and current["semantic_evidence_fingerprint"] != semantic_evidence_fingerprint
            ):
                raise _StepFailure("style_semantic_evidence_binding_conflict")
            if (
                current["used_source_set_fingerprint"] is not None
                and current["used_source_set_fingerprint"] != used_source_set_fingerprint
            ):
                raise _StepFailure("style_used_source_set_binding_conflict")
            connection.execute(
                "UPDATE style_analysis_runs SET semantic_evidence_fingerprint=?,"
                "used_source_set_fingerprint=? "
                "WHERE style_run_id=?",
                (
                    semantic_evidence_fingerprint, used_source_set_fingerprint,
                    run["style_run_id"],
                ),
            )
        receipt_material = {
            "schema": "quillframe_corpus_style_completion_receipt_v1",
            "style_run_id": run["style_run_id"], "study_id": run["study_id"],
            "public_study_id": run["public_study_id"], "profile": run["profile"],
            "checklist_hash": run["checklist_hash"], "protocol_fingerprint": run["protocol_fingerprint"],
            "sampling_config_fingerprint": run["sampling_config_fingerprint"],
            "semantic_config_fingerprint": run["semantic_config_fingerprint"],
            "semantic_evidence_fingerprint": semantic_evidence_fingerprint,
            "used_source_set_fingerprint": used_source_set_fingerprint,
            "candidate_bundle_fingerprint": bundle["bundle_fingerprint"],
            "candidate_artifact_fingerprint": bundle["candidate_artifact_fingerprint"],
            "craft_pack_fingerprint": bundle["craft_pack_fingerprint"],
        }
        receipt_fp = _fingerprint(receipt_material)
        recorder = getattr(self.library, "record_style_completion", None)
        if callable(recorder):
            try:
                receipt = recorder(**receipt_material, receipt_fingerprint=receipt_fp)
            except Exception as exc:
                raise _StepFailure("style_completion_receipt_failed") from exc
            if not isinstance(receipt, Mapping) or receipt.get("receipt_fingerprint") != receipt_fp:
                raise _StepFailure("style_completion_receipt_invalid")
        with self._connection() as connection:
            connection.execute(
                "UPDATE style_analysis_runs SET status='completed',phase='complete',result_state=?,"
                "candidate_bundle_json=?,candidate_artifact_fingerprint=?,craft_pack_fingerprint=?,"
                "local_leakage_summary_json=?,completion_receipt_fingerprint=?,error_code=NULL,updated_at=? "
                "WHERE style_run_id=?",
                (
                    bundle["result_state"], _json(bundle), bundle["candidate_artifact_fingerprint"],
                    bundle["craft_pack_fingerprint"], _json(bundle["local_leakage"]) if bundle["local_leakage"] else None,
                    receipt_fp, _utc_now(), run["style_run_id"],
                ),
            )

    # ------------------------------------------------------------------
    # Public execution controls
    # ------------------------------------------------------------------
    def execute(
        self, style_run_id: str, run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
        *, max_jobs: int | None = None,
    ) -> dict[str, Any]:
        style_run_id = _safe_id(style_run_id, "style_run_id")
        if not callable(run_semantic):
            raise StyleStudyRunnerError("run_semantic_not_callable")
        if max_jobs is not None and (
            isinstance(max_jobs, bool) or not isinstance(max_jobs, int) or max_jobs < 1
        ):
            raise StyleStudyRunnerError("max_jobs_invalid")
        run = self._run_row(style_run_id)
        self._assert_protocol_current(run)
        if run["status"] == "cancelled" or run["status"] == "completed":
            return self.status(style_run_id)
        if run["status"] == "failed":
            raise StyleStudyRunnerError("failed_style_run_requires_resume")
        if run["status"] == "prepared":
            starter = getattr(self.library, "start_study", None)
            if callable(starter):
                starter(run["study_id"])
            with self._connection() as connection:
                connection.execute(
                    "UPDATE style_analysis_runs SET status='running',updated_at=? WHERE style_run_id=?",
                    (_utc_now(), style_run_id),
                )
        run = self._run_row(style_run_id)
        if int(run["cohort_cycle"]) == 0:
            try:
                self._activate_seed_cohort(run)
            except _StepFailure as exc:
                self._set_failed(style_run_id, exc.code)
                return self.status(style_run_id)
        semantic_calls = 0
        while True:
            # Reset step-local identities every iteration so a later failure is
            # never misattributed to a stale row from an earlier phase.
            work = sample = step = claim = None
            run = self._run_row(style_run_id)
            try:
                if run["phase"] == "work_profiles":
                    with self._connection() as connection:
                        work = connection.execute(
                            "SELECT * FROM style_work_steps WHERE style_run_id=? "
                            "AND activation_cycle IS NOT NULL AND state!='complete' "
                            "ORDER BY ordinal LIMIT 1", (style_run_id,),
                        ).fetchone()
                    if work is None:
                        self._prepare_axis_steps(run)
                        continue
                    if work["state"] == "failed":
                        raise StyleStudyRunnerError("failed_style_run_requires_resume")
                    if work["state"] == "pending":
                        self._prepare_round(run, work)
                        continue
                    if work["state"] == "sampling_ready":
                        with self._connection() as connection:
                            sample = connection.execute(
                                "SELECT * FROM style_sample_steps WHERE style_run_id=? AND public_work_id=? "
                                "AND state!='complete' ORDER BY round_number,style_range_id LIMIT 1",
                                (style_run_id, work["public_work_id"]),
                            ).fetchone()
                        if sample is None:
                            with self._connection() as connection:
                                connection.execute(
                                    "UPDATE style_work_steps SET state='observations_ready' WHERE style_run_id=? "
                                    "AND public_work_id=?", (style_run_id, work["public_work_id"]),
                                )
                            continue
                        if max_jobs is not None and semantic_calls >= max_jobs:
                            return self.status(style_run_id)
                        self._execute_sample(run, work, sample, run_semantic)
                        semantic_calls += 1
                        continue
                    if work["state"] == "observations_ready":
                        if max_jobs is not None and semantic_calls >= max_jobs:
                            return self.status(style_run_id)
                        self._execute_work_synthesis(run, work, run_semantic)
                        semantic_calls += 1
                        continue
                    if work["state"] == "synthesizing":
                        raise StyleStudyRunnerError("interrupted_style_work_requires_resume")
                    raise _StepFailure("style_work_state_invalid")

                if run["phase"] == "axis_synthesis":
                    with self._connection() as connection:
                        pending_batches = connection.execute(
                            "SELECT * FROM style_axis_steps WHERE style_run_id=? AND state!='complete' "
                            "AND cohort_cycle=? AND batch_ordinal>0",
                            (style_run_id, run["cohort_cycle"]),
                        ).fetchall()
                    if pending_batches:
                        step = min(
                            pending_batches,
                            key=lambda row: (STYLE_AXES.index(row["axis"]), row["batch_ordinal"]),
                        )
                        if max_jobs is not None and semantic_calls >= max_jobs:
                            return self.status(style_run_id)
                        self._execute_axis_step(run, step, run_semantic)
                        semantic_calls += 1
                        continue

                    self._prepare_axis_reconcile_steps(run)
                    with self._connection() as connection:
                        pending_reconciliations = connection.execute(
                            "SELECT * FROM style_axis_steps WHERE style_run_id=? AND state!='complete' "
                            "AND cohort_cycle=? AND batch_ordinal=?",
                            (style_run_id, run["cohort_cycle"], -int(run["cohort_cycle"])),
                        ).fetchall()
                    if pending_reconciliations:
                        step = min(
                            pending_reconciliations,
                            key=lambda row: STYLE_AXES.index(row["axis"]),
                        )
                        if max_jobs is not None and semantic_calls >= max_jobs:
                            return self.status(style_run_id)
                        self._execute_axis_reconcile_step(run, step, run_semantic)
                        semantic_calls += 1
                        continue

                    self._advance_after_reconciliation(run)
                    continue

                if run["phase"] == "claim_verification":
                    with self._connection() as connection:
                        claim = connection.execute(
                            "SELECT * FROM style_claim_steps WHERE style_run_id=? AND state!='complete' "
                            "ORDER BY axis,claim_id LIMIT 1", (style_run_id,),
                        ).fetchone()
                    if claim is None:
                        with self._connection() as connection:
                            connection.execute(
                                "UPDATE style_analysis_runs SET phase='compilation',updated_at=? WHERE style_run_id=?",
                                (_utc_now(), style_run_id),
                            )
                        continue
                    if max_jobs is not None and semantic_calls >= max_jobs:
                        return self.status(style_run_id)
                    self._execute_claim_step(run, claim, run_semantic)
                    semantic_calls += 1
                    continue

                if run["phase"] == "compilation":
                    self._finalize(run)
                    return self.status(style_run_id)
                if run["phase"] == "complete":
                    return self.status(style_run_id)
                raise _StepFailure("style_run_phase_invalid")
            except StyleStudyRunnerError:
                raise
            except _StepFailure as exc:
                self._set_failed(
                    style_run_id, exc.code,
                    work_id=(work["public_work_id"] if "work" in locals() and work else None),
                    range_id=(sample["style_range_id"] if "sample" in locals() and sample else None),
                    axis=(step["axis"] if "step" in locals() and step else None),
                    claim_id=(claim["claim_id"] if "claim" in locals() and claim else None),
                )
                return self.status(style_run_id)

    def resume(
        self, style_run_id: str, run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
        *, max_jobs: int | None = None,
    ) -> dict[str, Any]:
        style_run_id = _safe_id(style_run_id, "style_run_id")
        with self._connection() as connection:
            run = connection.execute(
                "SELECT * FROM style_analysis_runs WHERE style_run_id=?", (style_run_id,),
            ).fetchone()
            if run is None:
                raise StyleStudyRunnerError("style_run_not_found")
            self._assert_protocol_current(run)
            if run["status"] in {"completed", "cancelled"}:
                return self._status(connection, style_run_id)
            failed_works = connection.execute(
                "SELECT public_work_id,current_round,saturation_state,work_profile_json,"
                "work_profile_fingerprint "
                "FROM style_work_steps WHERE style_run_id=? AND state='failed'",
                (style_run_id,),
            ).fetchall()
            recovery_states: dict[str, str] = {}
            for work in failed_works:
                current_round = int(work["current_round"])
                if current_round == 0:
                    recovery_states[work["public_work_id"]] = "pending"
                    continue
                round_row = connection.execute(
                    "SELECT work_semantic_job_fingerprint,work_semantic_result_fingerprint "
                    "FROM style_work_rounds WHERE style_run_id=? AND public_work_id=? "
                    "AND round_number=?",
                    (style_run_id, work["public_work_id"], current_round),
                ).fetchone()
                if round_row is None:
                    raise StyleStudyRunnerError("style_resume_round_record_missing")
                sample_state = connection.execute(
                    "SELECT COUNT(*) AS amount,"
                    "SUM(CASE WHEN state!='complete' THEN 1 ELSE 0 END) AS incomplete "
                    "FROM style_sample_steps WHERE style_run_id=? AND public_work_id=? "
                    "AND round_number=?",
                    (style_run_id, work["public_work_id"], current_round),
                ).fetchone()
                sample_count = int(sample_state["amount"])
                incomplete = int(sample_state["incomplete"] or 0)
                if incomplete:
                    recovery_states[work["public_work_id"]] = "sampling_ready"
                    continue
                job_fp = round_row["work_semantic_job_fingerprint"]
                result_fp = round_row["work_semantic_result_fingerprint"]
                if job_fp is None and result_fp is None:
                    if sample_count == 0:
                        raise StyleStudyRunnerError("style_resume_round_evidence_missing")
                    recovery_states[work["public_work_id"]] = "observations_ready"
                    continue
                if (
                    not isinstance(job_fp, str) or not _HASH_RE.fullmatch(job_fp)
                    or not isinstance(result_fp, str) or not _HASH_RE.fullmatch(result_fp)
                ):
                    raise StyleStudyRunnerError("style_resume_round_evidence_invalid")
                try:
                    profile = (
                        json.loads(work["work_profile_json"])
                        if isinstance(work["work_profile_json"], str)
                        else None
                    )
                except (TypeError, json.JSONDecodeError) as exc:
                    raise StyleStudyRunnerError("style_resume_work_profile_invalid") from exc
                profile_fp = work["work_profile_fingerprint"]
                if (
                    not isinstance(profile, Mapping)
                    or not isinstance(profile_fp, str)
                    or not _HASH_RE.fullmatch(profile_fp)
                    or _fingerprint(profile) != profile_fp
                ):
                    raise StyleStudyRunnerError("style_resume_work_profile_invalid")
                try:
                    self._validate_work_profile(
                        profile, work_id=work["public_work_id"]
                    )
                except _StepFailure as exc:
                    raise StyleStudyRunnerError("style_resume_work_profile_invalid") from exc
                state = work["saturation_state"]
                profile_state = profile["saturation"]["state"]
                if state == "continue":
                    if profile_state != "continue":
                        raise StyleStudyRunnerError("style_resume_work_evidence_state_invalid")
                    recovery_states[work["public_work_id"]] = "pending"
                elif state in {
                    "saturated",
                    "insufficient_available_evidence",
                    "round_budget_or_available_evidence_exhausted",
                }:
                    if (
                        state == "saturated" and profile_state != "saturated"
                        or state == "insufficient_available_evidence"
                        and profile_state not in {"continue", "insufficient_available_evidence"}
                        or state == "round_budget_or_available_evidence_exhausted"
                        and profile_state != "continue"
                    ):
                        raise StyleStudyRunnerError("style_resume_work_evidence_state_invalid")
                    recovery_states[work["public_work_id"]] = "complete"
                else:
                    raise StyleStudyRunnerError("style_resume_work_evidence_state_invalid")

            connection.execute(
                "UPDATE style_sample_steps SET state='pending',error_code=NULL WHERE style_run_id=? "
                "AND state IN ('running','failed')", (style_run_id,),
            )
            connection.execute(
                "UPDATE style_axis_steps SET state='pending',error_code=NULL WHERE style_run_id=? "
                "AND state IN ('running','failed')", (style_run_id,),
            )
            connection.execute(
                "UPDATE style_claim_steps SET state='pending',error_code=NULL WHERE style_run_id=? "
                "AND state IN ('running','failed')", (style_run_id,),
            )
            for work_id, state in recovery_states.items():
                connection.execute(
                    "UPDATE style_work_steps SET state=?,error_code=NULL WHERE style_run_id=? AND public_work_id=?",
                    (state, style_run_id, work_id),
                )
            connection.execute(
                "UPDATE style_analysis_runs SET status='running',error_code=NULL,updated_at=? WHERE style_run_id=?",
                (_utc_now(), style_run_id),
            )
        return self.execute(style_run_id, run_semantic, max_jobs=max_jobs)

    def cancel(self, style_run_id: str) -> dict[str, Any]:
        """Cancel only this append-only analysis run; never invalidate the V5 selection."""

        style_run_id = _safe_id(style_run_id, "style_run_id")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM style_analysis_runs WHERE style_run_id=?", (style_run_id,),
            ).fetchone()
            if row is None:
                raise StyleStudyRunnerError("style_run_not_found")
            if row["status"] != "completed":
                connection.execute(
                    "UPDATE style_analysis_runs SET status='cancelled',error_code=NULL,updated_at=? WHERE style_run_id=?",
                    (_utc_now(), style_run_id),
                )
            return self._status(connection, style_run_id)


__all__ = [
    "DEFAULT_AXIS_BATCH_SIZE",
    "DEFAULT_MAX_ROUNDS",
    "DEFAULT_WINDOWS_PER_ROUND",
    "STYLE_CONTRACT_IDS",
    "STYLE_PROTOCOL_ID",
    "STYLE_PROTOCOL_VERSION",
    "StyleStudyRunner",
    "StyleStudyRunnerError",
]
