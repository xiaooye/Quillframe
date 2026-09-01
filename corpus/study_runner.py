#!/usr/bin/env python3
"""Recoverable semantic orchestration for a confirmed Corpus study.

The runner persists only opaque identifiers, fingerprints, state, rubrics and
validated derived judgments.  A range passage exists only in the local stack
frame that builds and dispatches ``corpus.range_observe``; neither the semantic
job containing it nor callback error text is written to SQLite.
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
from typing import Any, Callable, Iterable, Mapping
import unicodedata
import uuid

from corpus.library import MAX_WINDOW_CHARS, STUDY_SIZE
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import make_contract_job, validate_result


DEFAULT_RESEARCH_AXES = (
    "scene_entry",
    "causal_progression",
    "dialogue_voice",
    "interiority_distance",
    "information_timing",
    "paragraph_rhythm",
    "relationship_movement",
    "chapter_forward_pull",
)

_SCOPE_TO_ROLE = {
    "opening": "opening",
    "middle": "representative_middle",
    "closing": "chapter_ending",
}
_RAW_OR_IDENTITY_KEYS = {
    "passage",
    "excerpt",
    "quote",
    "full_text",
    "raw_text",
    "source_text",
    "source",
    "source_id",
    "source_name",
    "source_title",
    "title",
    "book_title",
    "creator",
    "author",
    "display_label",
    "relative_locator",
    "local_path",
    "source_path",
    "file_path",
    "filepath",
    "filename",
}
_PATH_RE = re.compile(
    r"(?:^[A-Za-z]:|[\\/]|file:|~[\\/]|(?:^|[^A-Za-z])users[\\/]|\.\.[\\/])",
    re.IGNORECASE,
)
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class StudyRunnerError(ValueError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class _StepFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str, kind: str) -> str:
    value = str(value or "").strip()
    if not _MACHINE_ID_RE.fullmatch(value):
        raise StudyRunnerError(f"invalid_{kind}")
    return value


def _contains_key(value: Any, names: set[str]) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in names or _contains_key(child, names):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_key(child, names) for child in value)
    return False


class StudyRunner:
    """Checkpointed 3-window → work → cross-work semantic runner."""

    def __init__(self, db_path: str | Path, library: Any) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.library = library
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
                CREATE TABLE IF NOT EXISTS study_runs (
                    run_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL UNIQUE,
                    public_study_id TEXT NOT NULL,
                    profile TEXT NOT NULL CHECK(profile IN ('general','adult_explicit')),
                    checklist_hash TEXT NOT NULL,
                    research_axes_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('prepared','running','failed','completed','cancelled')),
                    benchmark_state TEXT NOT NULL CHECK(benchmark_state IN ('pending','running','failed','complete')),
                    benchmark_job_fingerprint TEXT,
                    benchmark_result_fingerprint TEXT,
                    benchmark_judgment_json TEXT,
                    candidate_bundle_json TEXT,
                    completion_receipt_fingerprint TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS study_work_steps (
                    run_id TEXT NOT NULL REFERENCES study_runs(run_id) ON DELETE CASCADE,
                    public_work_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','ranges_ready','ranges_complete','semantic_complete','complete','failed')),
                    semantic_job_fingerprint TEXT,
                    semantic_result_fingerprint TEXT,
                    work_judgment_json TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    failure_stage TEXT,
                    error_code TEXT,
                    PRIMARY KEY(run_id,public_work_id),
                    UNIQUE(run_id,ordinal)
                );
                CREATE TABLE IF NOT EXISTS study_range_steps (
                    range_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES study_runs(run_id) ON DELETE CASCADE,
                    public_work_id TEXT NOT NULL,
                    range_ordinal INTEGER NOT NULL CHECK(range_ordinal BETWEEN 1 AND 3),
                    window_role TEXT NOT NULL CHECK(window_role IN ('opening','representative_middle','chapter_ending')),
                    state TEXT NOT NULL CHECK(state IN ('pending','running','failed','complete')),
                    source_fingerprint TEXT NOT NULL,
                    passage_fingerprint TEXT NOT NULL,
                    job_fingerprint TEXT,
                    semantic_result_fingerprint TEXT,
                    judgment_json TEXT,
                    judgment_fingerprint TEXT,
                    rubric_json TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    UNIQUE(run_id,public_work_id,range_ordinal)
                );
                CREATE INDEX IF NOT EXISTS runner_work_state_idx
                    ON study_work_steps(run_id,state,ordinal);
                CREATE INDEX IF NOT EXISTS runner_range_state_idx
                    ON study_range_steps(run_id,public_work_id,state,range_ordinal);
                """
            )
            run_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(study_runs)")
            }
            if "completion_receipt_fingerprint" not in run_columns:
                connection.execute(
                    "ALTER TABLE study_runs ADD COLUMN completion_receipt_fingerprint TEXT"
                )

    # ---------------------------------------------------------------
    # Durable-data guards
    # ---------------------------------------------------------------
    @classmethod
    def _assert_safe_derived(
        cls,
        value: Any,
        *,
        forbid_fingerprints: bool = False,
        context: str = "derived",
    ) -> None:
        node_count = 0

        def visit(node: Any, depth: int) -> None:
            nonlocal node_count
            node_count += 1
            if node_count > 20_000 or depth > 20:
                raise _StepFailure(f"{context}_size_limit")
            if node is None or isinstance(node, bool):
                return
            if isinstance(node, (int, float)) and not isinstance(node, bool):
                if not math.isfinite(node):
                    raise _StepFailure(f"{context}_non_finite_number")
                return
            if isinstance(node, str):
                if len(node) > 20_000 or _PATH_RE.search(node):
                    raise _StepFailure(f"{context}_path_or_size_rejected")
                if forbid_fingerprints and _HASH_RE.fullmatch(node):
                    raise _StepFailure(f"{context}_fingerprint_rejected")
                return
            if isinstance(node, Mapping):
                for raw_key, child in node.items():
                    key = str(raw_key).casefold().replace("-", "_")
                    if key in _RAW_OR_IDENTITY_KEYS or key.endswith("_path"):
                        raise _StepFailure(f"{context}_forbidden_field")
                    if forbid_fingerprints and "fingerprint" in key:
                        raise _StepFailure(f"{context}_fingerprint_rejected")
                    visit(child, depth + 1)
                return
            if isinstance(node, (list, tuple)):
                for child in node:
                    visit(child, depth + 1)
                return
            raise _StepFailure(f"{context}_non_json_value")

        visit(value, 0)
        try:
            size = len(_canonical_bytes(value))
        except (TypeError, ValueError) as exc:
            raise _StepFailure(f"{context}_non_json_value") from exc
        if size > 8 * 1024 * 1024:
            raise _StepFailure(f"{context}_size_limit")

    @staticmethod
    def _json(value: Any) -> str:
        return _canonical_bytes(value).decode("utf-8")

    @classmethod
    def _normalize_derived(cls, value: Any) -> Any:
        """Match the library's safe derived-string canonicalization."""

        if isinstance(value, str):
            normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
            characters: list[str] = []
            for character in normalized:
                category = unicodedata.category(character)
                if character in {"\n", "\t"} or category not in {"Cc", "Cf", "Cs"}:
                    characters.append(character)
            normalized = "".join(characters)
            normalized = re.sub(r"[ \t]+", " ", normalized)
            normalized = re.sub(r" *\n *", "\n", normalized)
            normalized = re.sub(r"\n{4,}", "\n\n\n", normalized)
            return normalized.strip()
        if isinstance(value, Mapping):
            return {str(key): cls._normalize_derived(child) for key, child in value.items()}
        if isinstance(value, list):
            return [cls._normalize_derived(child) for child in value]
        return value

    # ---------------------------------------------------------------
    # Run lifecycle
    # ---------------------------------------------------------------
    def prepare(
        self,
        study_id: str,
        *,
        research_axes: Iterable[str] = DEFAULT_RESEARCH_AXES,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        study_id = _safe_id(study_id, "study_id")
        axes = tuple(research_axes)
        if len(axes) != len(DEFAULT_RESEARCH_AXES) or set(axes) != set(DEFAULT_RESEARCH_AXES):
            raise StudyRunnerError("research_axes_must_be_exact_eight")
        axes = DEFAULT_RESEARCH_AXES
        status = self.library.study_status(study_id, include_works=True)
        study_id = _safe_id(status.get("study_id"), "study_id")
        if status.get("status") not in {"confirmed", "running"}:
            raise StudyRunnerError("study_not_confirmed_or_running")
        profile = status.get("profile")
        if profile not in {"general", "adult_explicit"}:
            raise StudyRunnerError("study_profile_invalid")
        checklist_hash = status.get("checklist_hash")
        if not isinstance(checklist_hash, str) or not _HASH_RE.fullmatch(checklist_hash):
            raise StudyRunnerError("study_checklist_not_frozen")
        works = status.get("works")
        if not isinstance(works, list) or len(works) != STUDY_SIZE:
            raise StudyRunnerError("study_cardinality_invalid")
        work_ids = [work.get("public_work_id") for work in works if isinstance(work, dict)]
        if len(work_ids) != STUDY_SIZE or len(set(work_ids)) != STUDY_SIZE:
            raise StudyRunnerError("study_membership_invalid")
        public_study_id = str(status.get("public_study_id") or "")
        if not public_study_id:
            raise StudyRunnerError("public_study_id_missing")
        run_id = _safe_id(run_id, "run_id") if run_id else f"CRUN-{uuid.uuid4().hex}"
        now = _utc_now()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT run_id,study_id FROM study_runs WHERE run_id=? OR study_id=?",
                (run_id, study_id),
            ).fetchone()
            if existing is not None:
                if existing["study_id"] != study_id:
                    raise StudyRunnerError("run_identity_conflict")
                return self._status(connection, existing["run_id"])
            connection.execute(
                "INSERT INTO study_runs(run_id,study_id,public_study_id,profile,checklist_hash,"
                "research_axes_json,status,benchmark_state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,'prepared','pending',?,?)",
                (
                    run_id,
                    study_id,
                    public_study_id,
                    profile,
                    checklist_hash,
                    self._json(list(axes)),
                    now,
                    now,
                ),
            )
            connection.executemany(
                "INSERT INTO study_work_steps(run_id,public_work_id,ordinal,state) "
                "VALUES(?,?,?,'pending')",
                [
                    (run_id, public_work_id, index)
                    for index, public_work_id in enumerate(work_ids, 1)
                ],
            )
            return self._status(connection, run_id)

    def _status(self, connection: sqlite3.Connection, run_id: str) -> dict[str, Any]:
        run = connection.execute(
            "SELECT * FROM study_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run is None:
            raise StudyRunnerError("run_not_found")
        work_counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM study_work_steps WHERE run_id=? GROUP BY state",
                (run_id,),
            )
        }
        range_counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM study_range_steps WHERE run_id=? GROUP BY state",
                (run_id,),
            )
        }
        receipt_fingerprint = (
            run["completion_receipt_fingerprint"]
            if "completion_receipt_fingerprint" in run.keys()
            else None
        )
        projected_status = run["status"]
        projected_error = run["error_code"]
        if projected_status == "completed" and not _HASH_RE.fullmatch(
            str(receipt_fingerprint or "")
        ):
            projected_status = "failed"
            projected_error = "semantic_completion_receipt_missing"
        result: dict[str, Any] = {
            "schema": "quillframe_corpus_study_runner_status_v1",
            "run_id": run["run_id"],
            "study_id": run["study_id"],
            "public_study_id": run["public_study_id"],
            "profile": run["profile"],
            "status": projected_status,
            "benchmark_status": run["benchmark_state"],
            "work_count": sum(work_counts.values()),
            "work_states": dict(sorted(work_counts.items())),
            "range_states": dict(sorted(range_counts.items())),
            "semantic_attempts": run["attempt_count"],
            "raw_passage_persisted": False,
            "authority": {
                "canon_write": False,
                "framework_behavior_write": False,
                "automatic_activation": False,
                "automatic_promotion": False,
            },
        }
        if projected_error:
            result["error_code"] = projected_error
        if run["candidate_bundle_json"]:
            result["candidate_bundle"] = json.loads(run["candidate_bundle_json"])
        if receipt_fingerprint:
            result["completion_receipt_fingerprint"] = receipt_fingerprint
        return result

    def status(self, run_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            return self._status(connection, _safe_id(run_id, "run_id"))

    def status_for_study(self, study_id: str) -> dict[str, Any] | None:
        study_id = _safe_id(study_id, "study_id")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT run_id FROM study_runs WHERE study_id=?", (study_id,)
            ).fetchone()
            return self._status(connection, row["run_id"]) if row is not None else None

    @classmethod
    def inspect_for_study(
        cls, db_path: str | Path, study_id: str
    ) -> dict[str, Any] | None:
        """Read an existing runner projection without creating runner state."""

        study_id = _safe_id(study_id, "study_id")
        path = Path(db_path).expanduser().resolve()
        if not path.is_file():
            return None
        connection = sqlite3.connect(path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='study_runs'"
            ).fetchone()
            if table is None:
                return None
            row = connection.execute(
                "SELECT run_id FROM study_runs WHERE study_id=?", (study_id,)
            ).fetchone()
            if row is None:
                return None
            instance = cls.__new__(cls)
            instance.db_path = path
            instance.library = None
            return instance._status(connection, row["run_id"])
        finally:
            connection.close()

    def cancel(self, run_id: str) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run_id")
        with self._connection() as connection:
            run = connection.execute(
                "SELECT * FROM study_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise StudyRunnerError("run_not_found")
            if run["status"] == "completed":
                raise StudyRunnerError("completed_run_not_cancelable")
            if run["status"] == "cancelled":
                return self._status(connection, run_id)
            study_id = run["study_id"]
        cancel_study = getattr(self.library, "cancel_study", None)
        if callable(cancel_study):
            cancel_study(study_id)
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_runs SET status='cancelled',error_code='cancelled_by_caller',updated_at=? "
                "WHERE run_id=?",
                (_utc_now(), run_id),
            )
            return self._status(connection, run_id)

    # ---------------------------------------------------------------
    # Semantic dispatch
    # ---------------------------------------------------------------
    def _semantic_call(
        self,
        *,
        contract_id: str,
        subject_id: str,
        payload: dict[str, Any],
        run_id: str,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
        allow_raw_passage: bool,
    ) -> tuple[dict[str, Any], str, str]:
        if not allow_raw_passage:
            self._assert_safe_derived(
                payload,
                forbid_fingerprints=contract_id == "learning.benchmark_synthesize",
                context="semantic_input",
            )
        try:
            job = make_contract_job(
                contract_id,
                subject_id,
                payload,
                source_session_id=run_id,
            )
        except (TypeError, ValueError) as exc:
            raise _StepFailure("contract_job_creation_failed") from exc
        if validate_registered_job(job):
            raise _StepFailure("registered_job_validation_failed")
        try:
            result = run_semantic(job)
        except Exception as exc:
            # Never persist callback exception text: it may echo the passage.
            raise _StepFailure("semantic_callback_failed") from exc
        if validate_registered_job(job):
            raise _StepFailure("registered_job_mutated")
        if not isinstance(result, dict):
            raise _StepFailure("semantic_result_not_object")
        errors = validate_result(job, result)
        if errors or result.get("status") != "completed":
            raise _StepFailure("semantic_result_validation_failed")
        judgment = result.get("judgment")
        if not isinstance(judgment, dict):
            raise _StepFailure("semantic_judgment_missing")
        judgment = self._normalize_derived(judgment)
        self._assert_safe_derived(
            judgment,
            forbid_fingerprints=contract_id != "corpus.range_observe",
            context="semantic_judgment",
        )
        return (
            json.loads(self._json(judgment)),
            job["input_fingerprint"],
            _fingerprint(result),
        )

    def _run_row(self, run_id: str) -> sqlite3.Row:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM study_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if row is None:
                raise StudyRunnerError("run_not_found")
            return row

    def _set_run_failed(
        self,
        run_id: str,
        code: str,
        *,
        public_work_id: str | None = None,
        range_id: str | None = None,
        stage: str | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_runs SET status='failed',error_code=?,updated_at=? WHERE run_id=?",
                (code, _utc_now(), run_id),
            )
            if public_work_id is not None:
                connection.execute(
                    "UPDATE study_work_steps SET state='failed',failure_stage=?,error_code=? "
                    "WHERE run_id=? AND public_work_id=?",
                    (stage, code, run_id, public_work_id),
                )
            if range_id is not None:
                connection.execute(
                    "UPDATE study_range_steps SET state='failed',error_code=? WHERE range_id=?",
                    (code, range_id),
                )

    def _prepare_work_ranges(self, run: sqlite3.Row, work: sqlite3.Row) -> None:
        try:
            batch = self.library.prepare_ranges(
                run["study_id"],
                work["public_work_id"],
                rubric={
                    "rubric_id": "corpus_range_observe_v1",
                    "research_axes": list(DEFAULT_RESEARCH_AXES),
                },
                max_chars=MAX_WINDOW_CHARS,
            )
        except Exception as exc:
            raise _StepFailure("range_preparation_failed") from exc
        ranges = batch.get("ranges") if isinstance(batch, dict) else None
        if not isinstance(ranges, list) or len(ranges) != 3:
            raise _StepFailure("range_cardinality_invalid")
        scopes = [item.get("scope") for item in ranges if isinstance(item, dict)]
        if len(scopes) != 3 or set(scopes) != set(_SCOPE_TO_ROLE):
            raise _StepFailure("range_roles_invalid")
        ordered = sorted(ranges, key=lambda item: ("opening", "middle", "closing").index(item["scope"]))
        rows: list[tuple[Any, ...]] = []
        for ordinal, receipt in enumerate(ordered, 1):
            if _contains_key(receipt, {"passage", "text", "excerpt", "full_text", "raw_text"}):
                raise _StepFailure("range_receipt_contains_raw_text")
            range_id = _safe_id(receipt.get("range_id"), "range_id")
            source_fp = str(receipt.get("source_fingerprint") or "")
            passage_fp = str(receipt.get("passage_fingerprint") or "")
            if not _HASH_RE.fullmatch(source_fp) or not _HASH_RE.fullmatch(passage_fp):
                raise _StepFailure("range_fingerprint_invalid")
            rubric = receipt.get("rubric")
            self._assert_safe_derived(rubric, context="range_rubric")
            rows.append(
                (
                    range_id,
                    run["run_id"],
                    work["public_work_id"],
                    ordinal,
                    _SCOPE_TO_ROLE[receipt["scope"]],
                    source_fp,
                    passage_fp,
                    self._json(rubric),
                )
            )
        with self._connection() as connection:
            for row in rows:
                existing = connection.execute(
                    "SELECT run_id,public_work_id,range_ordinal,source_fingerprint,passage_fingerprint "
                    "FROM study_range_steps WHERE range_id=?",
                    (row[0],),
                ).fetchone()
                identity = (row[1], row[2], row[3], row[5], row[6])
                if existing is not None:
                    current = tuple(existing[key] for key in (
                        "run_id", "public_work_id", "range_ordinal",
                        "source_fingerprint", "passage_fingerprint",
                    ))
                    if current != identity:
                        raise _StepFailure("range_identity_conflict")
                    continue
                connection.execute(
                    "INSERT INTO study_range_steps(range_id,run_id,public_work_id,range_ordinal,"
                    "window_role,state,source_fingerprint,passage_fingerprint,rubric_json) "
                    "VALUES(?,?,?,?,?,'pending',?,?,?)",
                    row,
                )
            connection.execute(
                "UPDATE study_work_steps SET state='ranges_ready',failure_stage=NULL,error_code=NULL "
                "WHERE run_id=? AND public_work_id=?",
                (run["run_id"], work["public_work_id"]),
            )

    def _execute_range(
        self,
        run: sqlite3.Row,
        work: sqlite3.Row,
        range_row: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_range_steps SET state='running',attempt_count=attempt_count+1,error_code=NULL "
                "WHERE range_id=?",
                (range_row["range_id"],),
            )
            connection.execute(
                "UPDATE study_work_steps SET attempt_count=attempt_count+1 WHERE run_id=? AND public_work_id=?",
                (run["run_id"], work["public_work_id"]),
            )
            connection.execute(
                "UPDATE study_runs SET attempt_count=attempt_count+1,updated_at=? WHERE run_id=?",
                (_utc_now(), run["run_id"]),
            )
        try:
            ephemeral = self.library.materialize_range(range_row["range_id"])
            passage = ephemeral.get("passage") if isinstance(ephemeral, dict) else None
            if not isinstance(passage, str) or not passage or len(passage) > MAX_WINDOW_CHARS:
                raise _StepFailure("materialized_passage_invalid")
            if ephemeral.get("range_id") != range_row["range_id"]:
                raise _StepFailure("materialized_range_binding_mismatch")
            if ephemeral.get("passage_fingerprint") != range_row["passage_fingerprint"]:
                raise _StepFailure("materialized_passage_fingerprint_mismatch")
            payload = {
                "range_id": range_row["range_id"],
                "window_role": range_row["window_role"],
                "passage": passage,
                "research_axes": list(DEFAULT_RESEARCH_AXES),
                "passage_fingerprint": range_row["passage_fingerprint"],
            }
            judgment, job_fp, result_fp = self._semantic_call(
                contract_id="corpus.range_observe",
                subject_id=range_row["range_id"],
                payload=payload,
                run_id=run["run_id"],
                run_semantic=run_semantic,
                allow_raw_passage=True,
            )
            if judgment.get("range_id") != range_row["range_id"]:
                raise _StepFailure("range_judgment_binding_mismatch")
            try:
                completion = self.library.complete_range(range_row["range_id"], judgment)
            except Exception as exc:
                raise _StepFailure("range_judgment_leak_or_binding_rejected") from exc
            expected_judgment_fingerprint = _fingerprint(judgment)
            if (
                not isinstance(completion, dict)
                or completion.get("status") != "complete"
                or completion.get("judgment_fingerprint") != expected_judgment_fingerprint
            ):
                raise _StepFailure("range_completion_receipt_invalid")
        except _StepFailure:
            raise
        except Exception as exc:
            raise _StepFailure("range_materialization_failed") from exc
        finally:
            # Locals are deliberately not returned or captured by a checkpoint.
            ephemeral = None
            payload = None
            passage = None
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_range_steps SET state='complete',job_fingerprint=?,"
                "semantic_result_fingerprint=?,judgment_json=?,judgment_fingerprint=?,error_code=NULL "
                "WHERE range_id=?",
                (
                    job_fp,
                    result_fp,
                    self._json(judgment),
                    expected_judgment_fingerprint,
                    range_row["range_id"],
                ),
            )
            incomplete = connection.execute(
                "SELECT COUNT(*) FROM study_range_steps WHERE run_id=? AND public_work_id=? AND state!='complete'",
                (run["run_id"], work["public_work_id"]),
            ).fetchone()[0]
            if incomplete == 0:
                connection.execute(
                    "UPDATE study_work_steps SET state='ranges_complete',failure_stage=NULL,error_code=NULL "
                    "WHERE run_id=? AND public_work_id=?",
                    (run["run_id"], work["public_work_id"]),
                )

    def _execute_work_synthesis(
        self,
        run: sqlite3.Row,
        work: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        with self._connection() as connection:
            ranges = connection.execute(
                "SELECT * FROM study_range_steps WHERE run_id=? AND public_work_id=? "
                "ORDER BY range_ordinal",
                (run["run_id"], work["public_work_id"]),
            ).fetchall()
        if len(ranges) != 3 or any(row["state"] != "complete" or not row["judgment_json"] for row in ranges):
            raise _StepFailure("work_ranges_incomplete")
        observations = [
            {
                "profile": run["profile"],
                "window_role": row["window_role"],
                "observation": json.loads(row["judgment_json"]),
            }
            for row in ranges
        ]
        payload = {
            "public_work_id": work["public_work_id"],
            "window_observations": observations,
            "research_axes": list(DEFAULT_RESEARCH_AXES),
        }
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_work_steps SET attempt_count=attempt_count+1 WHERE run_id=? AND public_work_id=?",
                (run["run_id"], work["public_work_id"]),
            )
            connection.execute(
                "UPDATE study_runs SET attempt_count=attempt_count+1,updated_at=? WHERE run_id=?",
                (_utc_now(), run["run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="learning.work_synthesize",
            subject_id=work["public_work_id"],
            payload=payload,
            run_id=run["run_id"],
            run_semantic=run_semantic,
            allow_raw_passage=False,
        )
        if judgment.get("public_work_id") != work["public_work_id"]:
            raise _StepFailure("work_judgment_binding_mismatch")
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_work_steps SET state='semantic_complete',semantic_job_fingerprint=?,"
                "semantic_result_fingerprint=?,work_judgment_json=?,failure_stage=NULL,error_code=NULL "
                "WHERE run_id=? AND public_work_id=?",
                (
                    job_fp,
                    result_fp,
                    self._json(judgment),
                    run["run_id"],
                    work["public_work_id"],
                ),
            )

    def _finalize_work(self, run: sqlite3.Row, work: sqlite3.Row) -> None:
        analyze = getattr(self.library, "analyze_work", None)
        if callable(analyze):
            try:
                analyze(run["study_id"], work["public_work_id"])
            except Exception as exc:
                raise _StepFailure("library_work_finalize_failed") from exc
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_work_steps SET state='complete',failure_stage=NULL,error_code=NULL "
                "WHERE run_id=? AND public_work_id=?",
                (run["run_id"], work["public_work_id"]),
            )

    @staticmethod
    def _validate_benchmark_judgment(
        judgment: dict[str, Any], *, profile: str, work_ids: set[str]
    ) -> None:
        benchmarks = judgment.get("benchmarks")
        if not isinstance(benchmarks, list):
            raise _StepFailure("benchmark_list_invalid")
        for benchmark in benchmarks:
            if not isinstance(benchmark, dict):
                raise _StepFailure("benchmark_item_invalid")
            support = benchmark.get("supporting_work_ids")
            counter = benchmark.get("counterexample_work_ids")
            if not isinstance(support, list) or not set(support).issubset(work_ids):
                raise _StepFailure("benchmark_support_binding_invalid")
            if not isinstance(counter, list) or not set(counter).issubset(work_ids):
                raise _StepFailure("benchmark_counterexample_binding_invalid")
            profiles = benchmark.get("profiles")
            if not isinstance(profiles, list) or any(not isinstance(item, str) for item in profiles):
                raise _StepFailure("benchmark_profiles_invalid")
            if profile == "general" and "adult_explicit" in profiles:
                raise _StepFailure("benchmark_profile_mixing_rejected")
            if profile == "adult_explicit":
                if "adult_explicit" not in profiles:
                    raise _StepFailure("adult_explicit_profile_binding_required")
                if "general" in profiles:
                    raise _StepFailure("benchmark_profile_mixing_rejected")

    @staticmethod
    def _candidate_bundle(run: sqlite3.Row, judgment: dict[str, Any]) -> dict[str, Any]:
        benchmarks = judgment.get("benchmarks", [])
        user_candidates = []
        for index, benchmark in enumerate(benchmarks, 1):
            material = {
                "run_id": run["run_id"],
                "profile": run["profile"],
                "ordinal": index,
                "benchmark": benchmark,
            }
            user_candidates.append(
                {
                    "candidate_id": "UTC-" + hashlib.sha256(_canonical_bytes(material)).hexdigest()[:24],
                    "scope": "private_user_taste",
                    "profile": run["profile"],
                    "state": "candidate",
                    "activation": "standing_policy_after_semantic_independent_contradiction_gates",
                    "activation_performed": False,
                    "mechanism": benchmark["mechanism"],
                    "writer_guidance": benchmark["writer_guidance"],
                    "failure_boundary": benchmark["failure_boundary"],
                    "supporting_work_ids": benchmark["supporting_work_ids"],
                    "counterexample_work_ids": benchmark["counterexample_work_ids"],
                }
            )
        general_benchmarks = benchmarks if run["profile"] == "general" else []
        adult_benchmarks = benchmarks if run["profile"] == "adult_explicit" else []
        bundle: dict[str, Any] = {
            "schema": "quillframe_corpus_study_candidate_bundle_v1",
            "run_id": run["run_id"],
            "public_study_id": run["public_study_id"],
            "profile": run["profile"],
            "ingest_ready": False,
            "missing_gates": [
                "standing_policy_authorization_check",
                "semantic_independent_validation",
                "contradiction_gate",
            ],
            "private_user_taste_candidates": user_candidates,
            "general_craft_candidate_bundle": {
                "profile": "general",
                "state": "candidate",
                "review_mode": "manual_only",
                "benchmarks": general_benchmarks,
                "promotion_performed": False,
                "activation_performed": False,
            },
            "adult_explicit_candidate_bundle": {
                "profile": "adult_explicit",
                "independent_profile": True,
                "inherits_general_aggregate": False,
                "state": "candidate",
                "review_mode": "manual_only",
                "benchmarks": adult_benchmarks,
                "promotion_performed": False,
                "activation_performed": False,
            },
            "authority": {
                "canon_write": False,
                "framework_behavior_write": False,
                "durable_user_taste_write": False,
                "automatic_activation": False,
                "automatic_promotion": False,
            },
        }
        bundle["bundle_fingerprint"] = _fingerprint(bundle)
        return bundle

    def _finalize_completion_receipt(self, run_id: str) -> None:
        """Bind the durable semantic graph before the runner may say completed."""

        run = self._run_row(run_id)
        if run["benchmark_state"] != "complete":
            raise _StepFailure("semantic_completion_benchmark_incomplete")
        try:
            bundle = json.loads(run["candidate_bundle_json"] or "")
        except (TypeError, json.JSONDecodeError) as exc:
            raise _StepFailure("semantic_completion_bundle_invalid") from exc
        if not isinstance(bundle, dict):
            raise _StepFailure("semantic_completion_bundle_invalid")
        bundle_fingerprint = str(bundle.get("bundle_fingerprint") or "")
        fingerprint_input = dict(bundle)
        fingerprint_input.pop("bundle_fingerprint", None)
        if not _HASH_RE.fullmatch(bundle_fingerprint) or _fingerprint(fingerprint_input) != bundle_fingerprint:
            raise _StepFailure("semantic_completion_bundle_invalid")
        with self._connection() as connection:
            range_job_count = connection.execute(
                "SELECT COUNT(*) FROM study_range_steps WHERE run_id=? AND state='complete'",
                (run_id,),
            ).fetchone()[0]
            work_synthesis_count = connection.execute(
                "SELECT COUNT(*) FROM study_work_steps WHERE run_id=? AND state='complete' "
                "AND semantic_job_fingerprint IS NOT NULL AND semantic_result_fingerprint IS NOT NULL "
                "AND work_judgment_json IS NOT NULL",
                (run_id,),
            ).fetchone()[0]
        recorder = getattr(self.library, "record_semantic_completion", None)
        if not callable(recorder):
            raise _StepFailure("semantic_completion_receipt_unavailable")
        try:
            receipt = recorder(
                study_id=run["study_id"],
                run_id=run_id,
                public_study_id=run["public_study_id"],
                profile=run["profile"],
                checklist_hash=run["checklist_hash"],
                range_job_count=range_job_count,
                work_synthesis_count=work_synthesis_count,
                benchmark_job_fingerprint=run["benchmark_job_fingerprint"],
                benchmark_result_fingerprint=run["benchmark_result_fingerprint"],
                candidate_bundle_fingerprint=bundle_fingerprint,
            )
        except Exception as exc:
            # Never persist exception text; a downstream implementation could
            # accidentally include semantic material in it.
            raise _StepFailure("semantic_completion_receipt_failed") from exc
        receipt_fingerprint = (
            receipt.get("receipt_fingerprint") if isinstance(receipt, dict) else None
        )
        if (
            not isinstance(receipt, dict)
            or receipt.get("status") != "complete"
            or not _HASH_RE.fullmatch(str(receipt_fingerprint or ""))
        ):
            raise _StepFailure("semantic_completion_receipt_invalid")
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_runs SET status='completed',completion_receipt_fingerprint=?,"
                "error_code=NULL,updated_at=? WHERE run_id=? AND benchmark_state='complete'",
                (receipt_fingerprint, _utc_now(), run_id),
            )

    def _execute_benchmark(
        self,
        run: sqlite3.Row,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        with self._connection() as connection:
            works = connection.execute(
                "SELECT public_work_id,work_judgment_json FROM study_work_steps "
                "WHERE run_id=? ORDER BY ordinal",
                (run["run_id"],),
            ).fetchall()
        if len(works) != STUDY_SIZE or any(not row["work_judgment_json"] for row in works):
            raise _StepFailure("benchmark_work_set_incomplete")
        work_observations = [
            {
                "profile": run["profile"],
                "observation": json.loads(row["work_judgment_json"]),
            }
            for row in works
        ]
        payload = {
            "corpus_version": run["public_study_id"],
            "work_observations": work_observations,
            "research_axes": list(DEFAULT_RESEARCH_AXES),
        }
        self._assert_safe_derived(
            payload, forbid_fingerprints=True, context="benchmark_input"
        )
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_runs SET benchmark_state='running',attempt_count=attempt_count+1,"
                "updated_at=? WHERE run_id=?",
                (_utc_now(), run["run_id"]),
            )
        judgment, job_fp, result_fp = self._semantic_call(
            contract_id="learning.benchmark_synthesize",
            subject_id=run["public_study_id"],
            payload=payload,
            run_id=run["run_id"],
            run_semantic=run_semantic,
            allow_raw_passage=False,
        )
        self._validate_benchmark_judgment(
            judgment,
            profile=run["profile"],
            work_ids={row["public_work_id"] for row in works},
        )
        bundle = self._candidate_bundle(run, judgment)
        self._assert_safe_derived(
            bundle, forbid_fingerprints=False, context="candidate_bundle"
        )
        with self._connection() as connection:
            connection.execute(
                "UPDATE study_runs SET status='running',benchmark_state='complete',"
                "benchmark_job_fingerprint=?,benchmark_result_fingerprint=?,"
                "benchmark_judgment_json=?,candidate_bundle_json=?,error_code=NULL,updated_at=? "
                "WHERE run_id=?",
                (
                    job_fp,
                    result_fp,
                    self._json(judgment),
                    self._json(bundle),
                    _utc_now(),
                    run["run_id"],
                ),
            )
        self._finalize_completion_receipt(run["run_id"])

    def execute(
        self,
        run_id: str,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        max_jobs: int | None = None,
    ) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run_id")
        if not callable(run_semantic):
            raise StudyRunnerError("run_semantic_not_callable")
        if max_jobs is not None and (
            isinstance(max_jobs, bool) or not isinstance(max_jobs, int) or max_jobs < 1
        ):
            raise StudyRunnerError("max_jobs_invalid")
        run = self._run_row(run_id)
        if run["status"] == "cancelled":
            return self.status(run_id)
        if run["status"] == "completed":
            if _HASH_RE.fullmatch(str(run["completion_receipt_fingerprint"] or "")):
                return self.status(run_id)
            # A pre-receipt runner database may contain semantically complete
            # steps but must not retain the old completed claim.  Re-enter the
            # receipt finalization path without rerunning semantic work.
            with self._connection() as connection:
                connection.execute(
                    "UPDATE study_runs SET status='running',error_code=NULL,updated_at=? "
                    "WHERE run_id=?",
                    (_utc_now(), run_id),
                )
            run = self._run_row(run_id)
        if run["status"] == "failed":
            raise StudyRunnerError("failed_run_requires_resume")
        if run["status"] == "prepared":
            starter = getattr(self.library, "start_study", None)
            if callable(starter):
                starter(run["study_id"])
            with self._connection() as connection:
                connection.execute(
                    "UPDATE study_runs SET status='running',updated_at=? WHERE run_id=?",
                    (_utc_now(), run_id),
                )
        semantic_calls = 0
        while True:
            run = self._run_row(run_id)
            with self._connection() as connection:
                work = connection.execute(
                    "SELECT * FROM study_work_steps WHERE run_id=? AND state!='complete' ORDER BY ordinal LIMIT 1",
                    (run_id,),
                ).fetchone()
            if work is None:
                if run["benchmark_state"] == "complete":
                    try:
                        self._finalize_completion_receipt(run_id)
                    except _StepFailure as exc:
                        with self._connection() as connection:
                            connection.execute(
                                "UPDATE study_runs SET status='failed',error_code=?,updated_at=? "
                                "WHERE run_id=?",
                                (exc.code, _utc_now(), run_id),
                            )
                    return self.status(run_id)
                if max_jobs is not None and semantic_calls >= max_jobs:
                    return self.status(run_id)
                try:
                    self._execute_benchmark(run, run_semantic)
                    semantic_calls += 1
                except _StepFailure as exc:
                    with self._connection() as connection:
                        connection.execute(
                            "UPDATE study_runs SET status='failed',"
                            "benchmark_state=CASE WHEN benchmark_state='complete' THEN 'complete' ELSE 'failed' END,"
                            "error_code=?,updated_at=? WHERE run_id=?",
                            (exc.code, _utc_now(), run_id),
                        )
                    return self.status(run_id)
                return self.status(run_id)
            if work["state"] == "failed":
                raise StudyRunnerError("failed_run_requires_resume")
            try:
                if work["state"] == "pending":
                    self._prepare_work_ranges(run, work)
                    continue
                if work["state"] == "ranges_ready":
                    with self._connection() as connection:
                        range_row = connection.execute(
                            "SELECT * FROM study_range_steps WHERE run_id=? AND public_work_id=? "
                            "AND state!='complete' ORDER BY range_ordinal LIMIT 1",
                            (run_id, work["public_work_id"]),
                        ).fetchone()
                    if range_row is None:
                        with self._connection() as connection:
                            connection.execute(
                                "UPDATE study_work_steps SET state='ranges_complete' "
                                "WHERE run_id=? AND public_work_id=?",
                                (run_id, work["public_work_id"]),
                            )
                        continue
                    if range_row["state"] in {"failed", "running"}:
                        raise StudyRunnerError("interrupted_range_requires_resume")
                    if max_jobs is not None and semantic_calls >= max_jobs:
                        return self.status(run_id)
                    self._execute_range(run, work, range_row, run_semantic)
                    semantic_calls += 1
                    continue
                if work["state"] == "ranges_complete":
                    if max_jobs is not None and semantic_calls >= max_jobs:
                        return self.status(run_id)
                    self._execute_work_synthesis(run, work, run_semantic)
                    semantic_calls += 1
                    continue
                if work["state"] == "semantic_complete":
                    self._finalize_work(run, work)
                    continue
                raise _StepFailure("work_state_invalid")
            except _StepFailure as exc:
                current_range_id = (
                    range_row["range_id"]
                    if "range_row" in locals() and range_row is not None and work["state"] == "ranges_ready"
                    else None
                )
                self._set_run_failed(
                    run_id,
                    exc.code,
                    public_work_id=work["public_work_id"],
                    range_id=current_range_id,
                    stage=("range" if current_range_id else work["state"]),
                )
                return self.status(run_id)

    def resume(
        self,
        run_id: str,
        run_semantic: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        max_jobs: int | None = None,
    ) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run_id")
        with self._connection() as connection:
            run = connection.execute(
                "SELECT * FROM study_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise StudyRunnerError("run_not_found")
            if run["status"] == "cancelled":
                return self._status(connection, run_id)
            if run["status"] == "completed" and _HASH_RE.fullmatch(
                str(run["completion_receipt_fingerprint"] or "")
            ):
                return self._status(connection, run_id)
            connection.execute(
                "UPDATE study_range_steps SET state='pending',error_code=NULL "
                "WHERE run_id=? AND state IN ('failed','running')",
                (run_id,),
            )
            failed_works = connection.execute(
                "SELECT * FROM study_work_steps WHERE run_id=? AND state='failed'",
                (run_id,),
            ).fetchall()
            for work in failed_works:
                if work["work_judgment_json"]:
                    state = "semantic_complete"
                else:
                    range_count = connection.execute(
                        "SELECT COUNT(*) FROM study_range_steps WHERE run_id=? AND public_work_id=?",
                        (run_id, work["public_work_id"]),
                    ).fetchone()[0]
                    incomplete = connection.execute(
                        "SELECT COUNT(*) FROM study_range_steps WHERE run_id=? AND public_work_id=? AND state!='complete'",
                        (run_id, work["public_work_id"]),
                    ).fetchone()[0]
                    state = "pending" if range_count == 0 else (
                        "ranges_ready" if incomplete else "ranges_complete"
                    )
                connection.execute(
                    "UPDATE study_work_steps SET state=?,failure_stage=NULL,error_code=NULL "
                    "WHERE run_id=? AND public_work_id=?",
                    (state, run_id, work["public_work_id"]),
                )
            benchmark_state = "pending" if run["benchmark_state"] in {"failed", "running"} else run["benchmark_state"]
            connection.execute(
                "UPDATE study_runs SET status='running',benchmark_state=?,error_code=NULL,updated_at=? "
                "WHERE run_id=?",
                (benchmark_state, _utc_now(), run_id),
            )
        return self.execute(run_id, run_semantic, max_jobs=max_jobs)


__all__ = [
    "StudyRunner",
    "StudyRunnerError",
    "DEFAULT_RESEARCH_AXES",
]
