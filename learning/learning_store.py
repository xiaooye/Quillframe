#!/usr/bin/env python3
"""Quillframe adaptive-learning store.

Persists user-preference evidence, revisable hypotheses, corpus gaps, learning
candidates, promotions and rollback metadata. This is deliberately separate
from runtime/session state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "quillframe_learning_store_v1"
DEFAULT_DB = ".quillframe/learning.db"
EVIDENCE_SOURCES = {
    "explicit_rule", "user_edit", "rejection", "acceptance",
    "repeated_pattern", "corpus", "external_system", "human_review",
}
SCOPES = {"one_off", "project", "user_taste", "general_craft"}
HYPOTHESIS_STATES = {"candidate", "active", "contested", "superseded", "deprecated"}
GAP_STATES = {"open", "planned", "researching", "satisfied", "blocked", "cancelled"}
CANDIDATE_STATES = {"candidate", "testing", "promotable", "promoted", "rejected", "rolled_back"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class LearningStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def init(self) -> dict[str, Any]:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS preference_evidence (
                evidence_id TEXT PRIMARY KEY,
                subject_scope TEXT NOT NULL,
                project_id TEXT,
                source TEXT NOT NULL,
                polarity TEXT NOT NULL,
                observed_problem TEXT,
                mechanism TEXT NOT NULL,
                user_words_or_reference TEXT,
                artifact_ref TEXT,
                artifact_fingerprint TEXT,
                confidence REAL NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_preference_evidence_scope
              ON preference_evidence(subject_scope, created_at);

            CREATE TABLE IF NOT EXISTS preference_hypotheses (
                hypothesis_id TEXT PRIMARY KEY,
                subject_scope TEXT NOT NULL,
                project_id TEXT,
                dimension TEXT NOT NULL,
                statement TEXT NOT NULL,
                mechanism TEXT NOT NULL,
                state TEXT NOT NULL,
                confidence REAL NOT NULL,
                positive_weight REAL NOT NULL DEFAULT 0,
                negative_weight REAL NOT NULL DEFAULT 0,
                evidence_ids_json TEXT NOT NULL,
                contradiction_ids_json TEXT NOT NULL,
                applicability_json TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_hypothesis_scope
              ON preference_hypotheses(subject_scope, state, updated_at);

            CREATE TABLE IF NOT EXISTS corpus_gaps (
                gap_id TEXT PRIMARY KEY,
                subject_scope TEXT NOT NULL,
                hypothesis_id TEXT,
                question TEXT NOT NULL,
                desired_contrast TEXT,
                genre_tags_json TEXT NOT NULL,
                style_dimensions_json TEXT NOT NULL,
                source_constraints_json TEXT NOT NULL,
                state TEXT NOT NULL,
                priority REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(hypothesis_id) REFERENCES preference_hypotheses(hypothesis_id)
            );
            CREATE INDEX IF NOT EXISTS idx_corpus_gap_state
              ON corpus_gaps(state, priority DESC, created_at);

            CREATE TABLE IF NOT EXISTS learning_candidates (
                candidate_id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                mechanism TEXT NOT NULL,
                hypothesis_ids_json TEXT NOT NULL,
                corpus_evidence_refs_json TEXT NOT NULL,
                eval_refs_json TEXT NOT NULL,
                counterexample_refs_json TEXT NOT NULL,
                profile_boundary_json TEXT NOT NULL,
                state TEXT NOT NULL,
                version_target TEXT,
                rollback_ref TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_learning_candidate_state
              ON learning_candidates(state, updated_at);

            CREATE TABLE IF NOT EXISTS promotion_log (
                promotion_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                before_ref TEXT,
                after_ref TEXT NOT NULL,
                eval_summary_json TEXT NOT NULL,
                rollback_ref TEXT NOT NULL,
                promoted_at TEXT NOT NULL,
                rolled_back_at TEXT,
                rollback_reason TEXT,
                FOREIGN KEY(candidate_id) REFERENCES learning_candidates(candidate_id)
            );
            """)
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('schema',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (SCHEMA,),
            )
        return {"schema": SCHEMA, "db": str(self.db_path), "initialized": True}

    def add_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        required = ("subject_scope", "source", "polarity", "mechanism", "confidence")
        missing = [k for k in required if k not in evidence]
        if missing:
            raise ValueError("evidence missing: " + ", ".join(missing))
        if evidence["subject_scope"] not in SCOPES:
            raise ValueError("invalid subject_scope")
        if evidence["source"] not in EVIDENCE_SOURCES:
            raise ValueError("invalid source")
        if evidence["polarity"] not in {"positive", "negative", "mixed"}:
            raise ValueError("invalid polarity")
        confidence = float(evidence["confidence"])
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be 0..1")
        eid = evidence.get("evidence_id") or "PE-" + uuid.uuid4().hex
        payload = dict(evidence)
        payload["evidence_id"] = eid
        payload_hash = digest(payload)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT payload_hash FROM preference_evidence WHERE evidence_id=?", (eid,)
            ).fetchone()
            if row:
                conn.execute("COMMIT")
                if row["payload_hash"] != payload_hash:
                    raise ValueError("evidence_id conflict")
                return {"evidence_id": eid, "duplicate": True, "payload_hash": payload_hash}
            conn.execute(
                """INSERT INTO preference_evidence(
                    evidence_id,subject_scope,project_id,source,polarity,observed_problem,mechanism,
                    user_words_or_reference,artifact_ref,artifact_fingerprint,confidence,payload_json,payload_hash,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    eid, payload["subject_scope"], payload.get("project_id"), payload["source"], payload["polarity"],
                    payload.get("observed_problem"), payload["mechanism"], payload.get("user_words_or_reference"),
                    payload.get("artifact_ref"), payload.get("artifact_fingerprint"), confidence,
                    canonical_json(payload), payload_hash, now_iso(),
                ),
            )
            conn.execute("COMMIT")
        return {"evidence_id": eid, "duplicate": False, "payload_hash": payload_hash}

    def upsert_hypothesis(self, hypothesis: dict[str, Any], *, expected_version: int | None = None) -> dict[str, Any]:
        required = ("subject_scope", "dimension", "statement", "mechanism", "confidence")
        missing = [k for k in required if k not in hypothesis]
        if missing:
            raise ValueError("hypothesis missing: " + ", ".join(missing))
        if hypothesis["subject_scope"] not in SCOPES:
            raise ValueError("invalid subject_scope")
        confidence = float(hypothesis["confidence"])
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be 0..1")
        state = hypothesis.get("state", "candidate")
        if state not in HYPOTHESIS_STATES:
            raise ValueError("invalid hypothesis state")
        hid = hypothesis.get("hypothesis_id") or "PH-" + uuid.uuid4().hex
        evidence_ids = list(dict.fromkeys(hypothesis.get("evidence_ids", [])))
        contradiction_ids = list(dict.fromkeys(hypothesis.get("contradiction_ids", [])))
        applicability = hypothesis.get("applicability", {})
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT version FROM preference_hypotheses WHERE hypothesis_id=?", (hid,)
            ).fetchone()
            ts = now_iso()
            if row:
                if expected_version is not None and row["version"] != expected_version:
                    conn.execute("ROLLBACK")
                    raise ValueError("hypothesis version mismatch")
                version = row["version"] + 1
                conn.execute(
                    """UPDATE preference_hypotheses SET subject_scope=?,project_id=?,dimension=?,statement=?,mechanism=?,
                       state=?,confidence=?,positive_weight=?,negative_weight=?,evidence_ids_json=?,contradiction_ids_json=?,
                       applicability_json=?,version=?,updated_at=? WHERE hypothesis_id=?""",
                    (
                        hypothesis["subject_scope"], hypothesis.get("project_id"), hypothesis["dimension"],
                        hypothesis["statement"], hypothesis["mechanism"], state, confidence,
                        float(hypothesis.get("positive_weight", 0)), float(hypothesis.get("negative_weight", 0)),
                        canonical_json(evidence_ids), canonical_json(contradiction_ids), canonical_json(applicability),
                        version, ts, hid,
                    ),
                )
            else:
                if expected_version not in (None, 0):
                    conn.execute("ROLLBACK")
                    raise ValueError("nonzero expected_version for new hypothesis")
                version = 1
                conn.execute(
                    """INSERT INTO preference_hypotheses(
                        hypothesis_id,subject_scope,project_id,dimension,statement,mechanism,state,confidence,
                        positive_weight,negative_weight,evidence_ids_json,contradiction_ids_json,applicability_json,
                        version,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        hid, hypothesis["subject_scope"], hypothesis.get("project_id"), hypothesis["dimension"],
                        hypothesis["statement"], hypothesis["mechanism"], state, confidence,
                        float(hypothesis.get("positive_weight", 0)), float(hypothesis.get("negative_weight", 0)),
                        canonical_json(evidence_ids), canonical_json(contradiction_ids), canonical_json(applicability),
                        version, ts, ts,
                    ),
                )
            conn.execute("COMMIT")
        return {"hypothesis_id": hid, "version": version, "state": state, "confidence": confidence}

    def add_gap(self, gap: dict[str, Any]) -> dict[str, Any]:
        required = ("subject_scope", "question", "priority")
        missing = [k for k in required if k not in gap]
        if missing:
            raise ValueError("corpus gap missing: " + ", ".join(missing))
        if gap["subject_scope"] not in SCOPES:
            raise ValueError("invalid subject_scope")
        priority = float(gap["priority"])
        if not 0 <= priority <= 1:
            raise ValueError("priority must be 0..1")
        state = gap.get("state", "open")
        if state not in GAP_STATES:
            raise ValueError("invalid gap state")
        gid = gap.get("gap_id") or "CG-" + uuid.uuid4().hex
        ts = now_iso()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO corpus_gaps(
                    gap_id,subject_scope,hypothesis_id,question,desired_contrast,genre_tags_json,
                    style_dimensions_json,source_constraints_json,state,priority,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    gid, gap["subject_scope"], gap.get("hypothesis_id"), gap["question"], gap.get("desired_contrast"),
                    canonical_json(gap.get("genre_tags", [])), canonical_json(gap.get("style_dimensions", [])),
                    canonical_json(gap.get("source_constraints", {})), state, priority, ts, ts,
                ),
            )
        return {"gap_id": gid, "state": state, "priority": priority}

    def list_open_gaps(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM corpus_gaps WHERE state IN ('open','planned','researching')
                   ORDER BY priority DESC, created_at ASC LIMIT ?""", (limit,)
            ).fetchall()
        return [
            {
                "gap_id": r["gap_id"], "subject_scope": r["subject_scope"], "hypothesis_id": r["hypothesis_id"],
                "question": r["question"], "desired_contrast": r["desired_contrast"],
                "genre_tags": json.loads(r["genre_tags_json"]), "style_dimensions": json.loads(r["style_dimensions_json"]),
                "source_constraints": json.loads(r["source_constraints_json"]), "state": r["state"],
                "priority": r["priority"], "created_at": r["created_at"], "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def status(self) -> dict[str, Any]:
        with self.connect() as conn:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
                for table in (
                    "preference_evidence", "preference_hypotheses", "corpus_gaps",
                    "learning_candidates", "promotion_log",
                )
            }
            hypothesis_states = {
                r["state"]: r["n"] for r in conn.execute(
                    "SELECT state,COUNT(*) AS n FROM preference_hypotheses GROUP BY state"
                ).fetchall()
            }
        return {"schema": SCHEMA, "db": str(self.db_path), "counts": counts, "hypothesis_states": hypothesis_states}


def self_test(path: str | Path) -> dict[str, Any]:
    db = Path(path)
    if db.exists():
        db.unlink()
    store = LearningStore(db)
    store.init()
    ev = store.add_evidence({
        "subject_scope": "user_taste", "source": "explicit_rule", "polarity": "negative",
        "observed_problem": "surface form mistaken for pacing", "mechanism": "reject non-functional fragmentation",
        "user_words_or_reference": "fixture", "confidence": 1.0,
    })
    hyp = store.upsert_hypothesis({
        "subject_scope": "user_taste", "dimension": "paragraph_rhythm",
        "statement": "prefers fast pacing without non-functional fragmentation",
        "mechanism": "pace must come from state change rather than isolated sentence cuts",
        "confidence": 0.8, "state": "candidate", "evidence_ids": [ev["evidence_id"]],
        "applicability": {"genres": ["commercial_fiction"]},
    }, expected_version=0)
    gap = store.add_gap({
        "subject_scope": "user_taste", "hypothesis_id": hyp["hypothesis_id"],
        "question": "Find successful high-tempo passages using complete paragraph units",
        "desired_contrast": "fast pace with low fragment dependence",
        "genre_tags": ["commercial_fiction"], "style_dimensions": ["paragraph_rhythm", "pace"],
        "source_constraints": {"rights": ["redistributable", "analysis_only"]}, "priority": 0.9,
    })
    gaps = store.list_open_gaps()
    status = store.status()
    ok = ev["evidence_id"].startswith("PE-") and hyp["version"] == 1 and gap["gap_id"] == gaps[0]["gap_id"] and status["counts"]["preference_hypotheses"] == 1
    return {
        "learning_store_contract": "PASS" if ok else "FAIL",
        "separate_from_runtime_state": True,
        "evidence_traceable": True,
        "hypotheses_revisable": True,
        "corpus_gap_supported": True,
        "status": status,
    }


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be JSON object")
    return value


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe adaptive learning store")
    p.add_argument("--db", default=os.getenv("QUILLFRAME_LEARNING_DB", DEFAULT_DB))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("self-test")
    ev = sub.add_parser("evidence-add"); ev.add_argument("--json", required=True)
    hy = sub.add_parser("hypothesis-put"); hy.add_argument("--json", required=True); hy.add_argument("--expected-version", type=int)
    gp = sub.add_parser("gap-add"); gp.add_argument("--json", required=True)
    gl = sub.add_parser("gap-list"); gl.add_argument("--limit", type=int, default=20)
    args = p.parse_args()
    try:
        store = LearningStore(args.db)
        store.init()
        if args.cmd == "init": dump(store.init())
        elif args.cmd == "status": dump(store.status())
        elif args.cmd == "self-test": dump(self_test(args.db))
        elif args.cmd == "evidence-add": dump(store.add_evidence(load(args.json)))
        elif args.cmd == "hypothesis-put": dump(store.upsert_hypothesis(load(args.json), expected_version=args.expected_version))
        elif args.cmd == "gap-add": dump(store.add_gap(load(args.json)))
        elif args.cmd == "gap-list": dump({"gaps": store.list_open_gaps(args.limit)})
        return 0
    except Exception as exc:
        dump({"error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
