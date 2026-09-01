#!/usr/bin/env python3
"""User-owned standing policy and writer-safe user-taste projection.

The policy is the durable authority. Semantic review may establish that a
candidate is suitable for ``user_taste`` scope, but it can never enable the
policy or activate itself.  This module deliberately stores no corpus text,
source paths, author names, or evidence payloads in run-time projections.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

from harness.context_runtime import fingerprint
from learning.learning_store import LearningStore, canonical_json, now_iso
from learning.promotion_gate import evaluate as evaluate_promotion_candidate


POLICY_SCHEMA = "quillframe_user_taste_auto_activation_policy_v1"
SNAPSHOT_SCHEMA = "quillframe_user_taste_snapshot_v1"
WRITER_SCHEMA = "quillframe_writer_user_taste_v1"
RECEIPT_SCHEMA = "quillframe_user_taste_activation_receipt_v1"
SOURCE_KINDS = {"corpus", "feedback", "user_edit"}
PREFERENCE_STATES = {"candidate", "active", "contested", "superseded", "deprecated"}
_SAFE_APPLICABILITY_KEYS = {
    "scene_types", "genres", "languages", "content_zones", "desired_behavior",
    "avoid_behavior", "exceptions", "applies_when", "avoid_when",
}


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    out = [_text(item, name) for item in value]
    if len(out) != len(set(out)):
        raise ValueError(f"{name} must contain unique values")
    return out


class UserTasteService:
    """Deterministic policy, activation, suspension and projection service."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        LearningStore(self.db_path).init()
        self._ensure_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
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

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_taste_policy (
                policy_id TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL,
                policy_version INTEGER NOT NULL,
                source_kinds_json TEXT NOT NULL,
                authorization_ref TEXT,
                authorized_at TEXT,
                revoked_at TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_taste_activation_receipts (
                receipt_id TEXT PRIMARY KEY,
                hypothesis_id TEXT NOT NULL,
                action TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                policy_version INTEGER NOT NULL,
                before_version INTEGER NOT NULL,
                after_version INTEGER NOT NULL,
                candidate_id TEXT,
                reason TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(hypothesis_id, action, before_version, after_version)
            );
            """)
            conn.execute(
                """INSERT OR IGNORE INTO user_taste_policy(
                       policy_id,enabled,policy_version,source_kinds_json,
                       authorization_ref,authorized_at,revoked_at,updated_at
                   ) VALUES('default',0,0,?,NULL,NULL,NULL,?)""",
                (canonical_json(sorted(SOURCE_KINDS)), now_iso()),
            )

    @staticmethod
    def _policy(row: sqlite3.Row) -> dict[str, Any]:
        value = {
            "schema": POLICY_SCHEMA,
            "policy_id": row["policy_id"],
            "enabled": bool(row["enabled"]),
            "policy_version": row["policy_version"],
            "source_kinds": json.loads(row["source_kinds_json"]),
            "authorization_ref": row["authorization_ref"],
            "authorized_at": row["authorized_at"],
            "revoked_at": row["revoked_at"],
            "authority_scope": "user_taste_only",
            "framework_write": False,
            "canon_write": False,
        }
        value["fingerprint"] = fingerprint(value)
        return value

    @staticmethod
    def _default_policy() -> dict[str, Any]:
        value = {
            "schema": POLICY_SCHEMA,
            "policy_id": "default",
            "enabled": False,
            "policy_version": 0,
            "source_kinds": sorted(SOURCE_KINDS),
            "authorization_ref": None,
            "authorized_at": None,
            "revoked_at": None,
            "authority_scope": "user_taste_only",
            "framework_write": False,
            "canon_write": False,
        }
        value["fingerprint"] = fingerprint(value)
        return value

    @staticmethod
    def _snapshot_value(policy: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        value = {
            "schema": SNAPSHOT_SCHEMA,
            "policy": policy,
            "priority": "below_current_request_above_project_profile",
            "candidates": candidates,
            "authority": False,
        }
        value["candidate_fingerprint"] = fingerprint(candidates)
        value["snapshot_fingerprint"] = fingerprint(value)
        return value

    @classmethod
    def snapshot_readonly(cls, db_path: str | Path) -> dict[str, Any]:
        """Project a snapshot without creating or migrating storage.

        Empty/new projects must remain side-effect free when merely inspected.
        The mutating service constructor is reserved for explicit policy or
        preference operations.
        """

        path = Path(db_path)
        if not path.is_file():
            return cls._snapshot_value(cls._default_policy(), [])
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                    "('user_taste_policy','preference_hypotheses')"
                )
            }
            if "user_taste_policy" not in tables:
                return cls._snapshot_value(cls._default_policy(), [])
            row = connection.execute(
                "SELECT * FROM user_taste_policy WHERE policy_id='default'"
            ).fetchone()
            policy = cls._policy(row) if row is not None else cls._default_policy()
            candidates: list[dict[str, Any]] = []
            if policy["enabled"] and "preference_hypotheses" in tables:
                rows = connection.execute(
                    "SELECT * FROM preference_hypotheses "
                    "WHERE subject_scope='user_taste' AND state='active' "
                    "ORDER BY updated_at DESC,hypothesis_id ASC"
                ).fetchall()
                for item in rows:
                    applicability_source = json.loads(item["applicability_json"])
                    applicability = {
                        key: deepcopy(value) for key, value in applicability_source.items()
                        if key in _SAFE_APPLICABILITY_KEYS
                    }
                    candidates.append({
                        "hypothesis_id": item["hypothesis_id"],
                        "dimension": item["dimension"],
                        "mechanism": item["mechanism"],
                        "applicability": applicability,
                        "version": item["version"],
                    })
            return cls._snapshot_value(policy, candidates)
        finally:
            connection.close()

    def get_policy(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM user_taste_policy WHERE policy_id='default'").fetchone()
        assert row is not None
        return self._policy(row)

    def set_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("policy payload must be an object")
        enabled = payload.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        source_kinds = _string_list(payload.get("source_kinds", sorted(SOURCE_KINDS)), "source_kinds")
        if not set(source_kinds).issubset(SOURCE_KINDS) or not source_kinds:
            raise ValueError("source_kinds contains an unsupported source")
        authorization_ref = payload.get("authorization_ref")
        if enabled:
            authorization_ref = _text(authorization_ref, "authorization_ref")
        elif authorization_ref is not None:
            authorization_ref = _text(authorization_ref, "authorization_ref")
        expected = payload.get("expected_version")
        if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool) or expected < 0):
            raise ValueError("expected_version must be a non-negative integer")
        stamp = now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM user_taste_policy WHERE policy_id='default'").fetchone()
            assert row is not None
            if expected is not None and row["policy_version"] != expected:
                conn.execute("ROLLBACK")
                raise ValueError("policy version mismatch")
            version = row["policy_version"] + 1
            authorized_at = stamp if enabled else row["authorized_at"]
            revoked_at = None if enabled else stamp
            conn.execute(
                """UPDATE user_taste_policy SET enabled=?,policy_version=?,source_kinds_json=?,
                   authorization_ref=?,authorized_at=?,revoked_at=?,updated_at=? WHERE policy_id='default'""",
                (int(enabled), version, canonical_json(sorted(source_kinds)), authorization_ref,
                 authorized_at, revoked_at, stamp),
            )
            conn.execute("COMMIT")
        return self.get_policy()

    @staticmethod
    def _preference(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "hypothesis_id": row["hypothesis_id"],
            "scope": row["subject_scope"],
            "project_id": row["project_id"],
            "dimension": row["dimension"],
            "statement": row["statement"],
            "mechanism": row["mechanism"],
            "state": row["state"],
            "confidence": row["confidence"],
            "applicability": json.loads(row["applicability_json"]),
            "evidence_ids": json.loads(row["evidence_ids_json"]),
            "contradiction_ids": json.loads(row["contradiction_ids_json"]),
            "version": row["version"],
        }

    def list_preferences(self, state: str | None = None) -> list[dict[str, Any]]:
        if state is not None and state not in PREFERENCE_STATES:
            raise ValueError("invalid preference state")
        sql = "SELECT * FROM preference_hypotheses WHERE subject_scope='user_taste'"
        args: tuple[Any, ...] = ()
        if state is not None:
            sql += " AND state=?"
            args = (state,)
        sql += " ORDER BY updated_at DESC,hypothesis_id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [self._preference(row) for row in rows]

    def get_preference(self, hypothesis_id: str) -> dict[str, Any]:
        hypothesis_id = _text(hypothesis_id, "hypothesis_id")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM preference_hypotheses WHERE hypothesis_id=? AND subject_scope='user_taste'",
                (hypothesis_id,),
            ).fetchone()
        if row is None:
            raise ValueError("unknown user_taste preference")
        return self._preference(row)

    def _transition(self, *, hypothesis_id: str, expected_version: int, state: str,
                    action: str, source_kind: str, reason: str,
                    candidate_id: str | None = None,
                    allowed_from: set[str] | None = None) -> dict[str, Any]:
        if source_kind not in SOURCE_KINDS:
            raise ValueError("invalid source_kind")
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError("expected_version must be a positive integer")
        if state not in PREFERENCE_STATES:
            raise ValueError("invalid preference target state")
        reason = _text(reason, "reason")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM preference_hypotheses WHERE hypothesis_id=? AND subject_scope='user_taste'",
                (hypothesis_id,),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                raise ValueError("unknown user_taste preference")
            if row["version"] != expected_version:
                conn.execute("ROLLBACK")
                raise ValueError("preference version mismatch")
            if allowed_from is not None and row["state"] not in allowed_from:
                conn.execute("ROLLBACK")
                raise ValueError("invalid preference state transition")
            after_version = expected_version + 1
            conn.execute(
                "UPDATE preference_hypotheses SET state=?,version=?,updated_at=? WHERE hypothesis_id=?",
                (state, after_version, now_iso(), hypothesis_id),
            )
            policy = conn.execute("SELECT * FROM user_taste_policy WHERE policy_id='default'").fetchone()
            assert policy is not None
            receipt = {
                "schema": RECEIPT_SCHEMA,
                "receipt_id": "UTR-" + uuid.uuid4().hex,
                "hypothesis_id": hypothesis_id,
                "action": action,
                "source_kind": source_kind,
                "policy_version": policy["policy_version"],
                "before_version": expected_version,
                "after_version": after_version,
                "candidate_id": candidate_id,
                "reason": reason,
                "authority": False,
            }
            conn.execute(
                """INSERT INTO user_taste_activation_receipts(
                       receipt_id,hypothesis_id,action,source_kind,policy_version,before_version,
                       after_version,candidate_id,reason,payload_json,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (receipt["receipt_id"], hypothesis_id, action, source_kind,
                 receipt["policy_version"], expected_version, after_version, candidate_id,
                 reason, canonical_json(receipt), now_iso()),
            )
            conn.execute("COMMIT")
        return {"preference": self.get_preference(hypothesis_id), "receipt": receipt}

    def activate(self, *, hypothesis_id: str, expected_version: int,
                 candidate: dict[str, Any], source_kind: str) -> dict[str, Any]:
        policy = self.get_policy()
        if not policy["enabled"] or source_kind not in policy["source_kinds"]:
            raise ValueError("standing user_taste policy does not authorize this source")
        preference = self.get_preference(hypothesis_id)
        if preference["state"] not in {"candidate", "contested"}:
            raise ValueError("preference is not an activatable candidate")
        if preference["contradiction_ids"]:
            raise ValueError("unresolved contradiction blocks automatic activation")
        report = evaluate_promotion_candidate(candidate)
        if report.get("status") != "ready_for_activation":
            raise ValueError("promotion review does not support user_taste activation")
        if report.get("scope") != "user_taste" or report.get("mechanism") != preference["mechanism"]:
            raise ValueError("promotion candidate does not bind the preference")
        return self._transition(
            hypothesis_id=hypothesis_id, expected_version=expected_version, state="active",
            action="activate", source_kind=source_kind,
            reason="standing policy plus bound promotion and contradiction gates",
            candidate_id=report.get("candidate_id"),
            allowed_from={"candidate", "contested"},
        )

    def ingest_corpus_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist one source-free corpus mechanism and apply standing policy.

        The semantic promotion candidate must bind the exact opaque Corpus
        evidence refs supplied here. No work title, source path or excerpt is
        accepted by this bridge.
        """
        if not isinstance(payload, dict):
            raise ValueError("corpus candidate must be an object")
        forbidden = {"source_title", "creator", "author", "local_path", "source_path", "excerpt", "raw_text", "source_text", "full_text"}
        if forbidden.intersection(payload):
            raise ValueError("corpus candidate contains source-identifying or raw fields")
        dimension = _text(payload.get("dimension"), "dimension")
        statement = _text(payload.get("statement"), "statement")
        mechanism = _text(payload.get("mechanism"), "mechanism")
        evidence_refs = _string_list(payload.get("corpus_evidence_refs"), "corpus_evidence_refs")
        if not evidence_refs:
            raise ValueError("corpus_evidence_refs must not be empty")
        applicability = payload.get("applicability", {})
        if not isinstance(applicability, dict) or set(applicability).difference(_SAFE_APPLICABILITY_KEYS):
            raise ValueError("corpus candidate applicability is not writer-safe")
        promotion_candidate = payload.get("promotion_candidate")
        if not isinstance(promotion_candidate, dict):
            raise ValueError("promotion_candidate is required")
        promoted_refs = (promotion_candidate.get("evidence") or {}).get("evidence_refs")
        if promoted_refs != evidence_refs:
            raise ValueError("promotion candidate must bind exact corpus_evidence_refs")
        artifact_ref = _text(payload.get("artifact_ref"), "artifact_ref")
        artifact_fingerprint = _text(payload.get("artifact_fingerprint"), "artifact_fingerprint")
        identity = fingerprint({
            "dimension": dimension, "statement": statement, "mechanism": mechanism,
            "evidence_refs": evidence_refs, "artifact_ref": artifact_ref,
            "artifact_fingerprint": artifact_fingerprint,
        })
        evidence_id = "PE-CORPUS-" + identity[7:31]
        store = LearningStore(self.db_path)
        evidence = store.add_evidence({
            "evidence_id": evidence_id,
            "subject_scope": "user_taste",
            "source": "corpus",
            "polarity": "positive",
            "mechanism": mechanism,
            "artifact_ref": artifact_ref,
            "artifact_fingerprint": artifact_fingerprint,
            "confidence": float(payload.get("confidence", 0.8)),
            "corpus_evidence_refs": evidence_refs,
        })
        with store.connect() as conn:
            rows = conn.execute("SELECT * FROM preference_hypotheses ORDER BY hypothesis_id").fetchall()
        existing = None
        for row in rows:
            refs = json.loads(row["evidence_ids_json"])
            if evidence_id in refs:
                existing = self._preference(row)
                break
        if existing is None:
            created = store.upsert_hypothesis({
                "subject_scope": "user_taste",
                "project_id": None,
                "dimension": dimension,
                "statement": statement,
                "mechanism": mechanism,
                "state": "candidate",
                "confidence": float(payload.get("confidence", 0.8)),
                "positive_weight": 1,
                "negative_weight": 0,
                "evidence_ids": [evidence_id],
                "contradiction_ids": [],
                "applicability": applicability,
            }, expected_version=0)
            preference = self.get_preference(created["hypothesis_id"])
        else:
            preference = existing
        result: dict[str, Any] = {
            "preference": preference,
            "evidence_id": evidence_id,
            "evidence_duplicate": evidence["duplicate"],
            "auto_activation": {"status": "not_attempted", "authority": False},
            "authority": False,
        }
        policy = self.get_policy()
        if policy["enabled"] and "corpus" in policy["source_kinds"] and preference["state"] == "candidate":
            try:
                activated = self.activate(
                    hypothesis_id=preference["hypothesis_id"], expected_version=preference["version"],
                    candidate=promotion_candidate, source_kind="corpus",
                )
            except ValueError as exc:
                result["auto_activation"] = {"status": "blocked", "reason": str(exc), "authority": False}
            else:
                result["preference"] = activated["preference"]
                result["auto_activation"] = {"status": "activated", "receipt": activated["receipt"], "authority": False}
        return result

    def pause(self, *, hypothesis_id: str, expected_version: int, reason: str) -> dict[str, Any]:
        return self._transition(
            hypothesis_id=hypothesis_id, expected_version=expected_version, state="contested",
            action="pause", source_kind="feedback", reason=reason,
            allowed_from={"active"},
        )

    def withdraw(self, *, hypothesis_id: str, expected_version: int, reason: str) -> dict[str, Any]:
        return self._transition(
            hypothesis_id=hypothesis_id, expected_version=expected_version, state="deprecated",
            action="withdraw", source_kind="feedback", reason=reason,
            allowed_from={"candidate", "active", "contested"},
        )

    def suspend_invalidated(self, evidence_ids: list[str], *, reason: str) -> dict[str, Any]:
        evidence_ids = _string_list(evidence_ids, "evidence_ids")
        suspended: list[str] = []
        for preference in self.list_preferences("active"):
            if set(preference["evidence_ids"]).intersection(evidence_ids):
                self.pause(
                    hypothesis_id=preference["hypothesis_id"], expected_version=preference["version"],
                    reason=reason,
                )
                suspended.append(preference["hypothesis_id"])
        return {"suspended_hypothesis_ids": suspended, "authority": False}

    def snapshot(self) -> dict[str, Any]:
        policy = self.get_policy()
        candidates = []
        if policy["enabled"]:
            for row in self.list_preferences("active"):
                applicability = {
                    key: deepcopy(value) for key, value in row["applicability"].items()
                    if key in _SAFE_APPLICABILITY_KEYS
                }
                candidates.append({
                    "hypothesis_id": row["hypothesis_id"],
                    "dimension": row["dimension"],
                    "mechanism": row["mechanism"],
                    "applicability": applicability,
                    "version": row["version"],
                })
        return self._snapshot_value(policy, candidates)


def validate_snapshot(snapshot: Any) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("invalid user_taste snapshot")
    expected = fingerprint({key: value for key, value in snapshot.items() if key != "snapshot_fingerprint"})
    if snapshot.get("snapshot_fingerprint") != expected:
        raise ValueError("user_taste snapshot fingerprint changed")
    policy = snapshot.get("policy")
    policy_keys = {
        "schema", "policy_id", "enabled", "policy_version", "source_kinds",
        "authorization_ref", "authorized_at", "revoked_at", "authority_scope",
        "framework_write", "canon_write", "fingerprint",
    }
    if not isinstance(policy, dict) or set(policy) != policy_keys or policy.get("schema") != POLICY_SCHEMA:
        raise ValueError("invalid user_taste policy snapshot")
    policy_expected = fingerprint({key: value for key, value in policy.items() if key != "fingerprint"})
    if policy.get("fingerprint") != policy_expected:
        raise ValueError("user_taste policy fingerprint changed")
    if (
        not isinstance(policy.get("enabled"), bool)
        or isinstance(policy.get("policy_version"), bool)
        or not isinstance(policy.get("policy_version"), int)
        or policy["policy_version"] < 0
        or not isinstance(policy.get("source_kinds"), list)
        or not set(policy["source_kinds"]).issubset(SOURCE_KINDS)
        or len(policy["source_kinds"]) != len(set(policy["source_kinds"]))
        or policy.get("authority_scope") != "user_taste_only"
        or policy.get("framework_write") is not False
        or policy.get("canon_write") is not False
    ):
        raise ValueError("invalid user_taste policy authority boundary")
    if policy["enabled"] and not str(policy.get("authorization_ref") or "").strip():
        raise ValueError("enabled user_taste policy lacks user authorization")
    candidates = snapshot.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 100:
        raise ValueError("invalid user_taste candidate inventory")
    if snapshot.get("candidate_fingerprint") != fingerprint(candidates):
        raise ValueError("user_taste candidate inventory changed")
    seen: set[str] = set()
    for row in candidates:
        if not isinstance(row, dict) or set(row) != {
            "hypothesis_id", "dimension", "mechanism", "applicability", "version",
        }:
            raise ValueError("invalid user_taste candidate")
        identity = _text(row["hypothesis_id"], "hypothesis_id")
        if identity in seen:
            raise ValueError("duplicate user_taste candidate")
        seen.add(identity)
        _text(row["dimension"], "dimension")
        _text(row["mechanism"], "mechanism")
        if not isinstance(row["applicability"], dict):
            raise ValueError("invalid user_taste applicability")
        if not isinstance(row["version"], int) or isinstance(row["version"], bool) or row["version"] < 1:
            raise ValueError("invalid user_taste version")


def selection_payload(snapshot: dict[str, Any], *, request: str,
                      scene_context: dict[str, Any]) -> dict[str, Any] | None:
    validate_snapshot(snapshot)
    if not snapshot["policy"]["enabled"] or not snapshot["candidates"]:
        return None
    return {
        "request": _text(request, "request"),
        "scene_context": deepcopy(scene_context),
        "policy_fingerprint": snapshot["policy"]["fingerprint"],
        "candidate_fingerprint": snapshot["candidate_fingerprint"],
        "candidates": deepcopy(snapshot["candidates"]),
    }


def materialize_selection(snapshot: dict[str, Any], selection: Any, *,
                          binding_fingerprint: str) -> dict[str, Any] | None:
    validate_snapshot(snapshot)
    if not isinstance(selection, list):
        raise ValueError("user_taste selection must be an array")
    if not snapshot["policy"]["enabled"]:
        if selection:
            raise ValueError("disabled user_taste policy cannot select preferences")
        return None
    by_id = {row["hypothesis_id"]: row for row in snapshot["candidates"]}
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in selection:
        if not isinstance(item, dict) or set(item) != {"hypothesis_id", "reason"}:
            raise ValueError("invalid user_taste selection entry")
        identity = _text(item["hypothesis_id"], "hypothesis_id")
        if identity in seen or identity not in by_id:
            raise ValueError("unknown or repeated user_taste selection")
        seen.add(identity)
        reason = _text(item["reason"], "reason")
        if len(reason) > 800:
            raise ValueError("user_taste selection reason is too long")
        row = by_id[identity]
        applicability = row["applicability"]
        chosen.append({
            "hypothesis_id": identity,
            "version": row["version"],
            "mechanism": row["mechanism"],
            "applies_when": deepcopy(applicability.get("applies_when", applicability.get("scene_types", []))),
            "avoid_when": deepcopy(applicability.get("avoid_when", applicability.get("exceptions", []))),
        })
    if not chosen:
        return None
    value = {
        "schema": WRITER_SCHEMA,
        "policy_fingerprint": snapshot["policy"]["fingerprint"],
        "snapshot_fingerprint": snapshot["snapshot_fingerprint"],
        "selection_binding_fingerprint": _text(binding_fingerprint, "binding_fingerprint"),
        "preferences": chosen,
        "authority": False,
    }
    value["guidance_fingerprint"] = fingerprint(value)
    return value
