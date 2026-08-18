"""Typed SQLite persistence for Quillframe semantic Context Runtime.

This module persists derived semantic metadata and runtime receipts. It never
creates Project authority, Canon, acceptance, or settlement state.
"""
from __future__ import annotations

import json
from typing import Any

from harness.context_runtime import (
    FREEZE_SCHEMA,
    GREENLIGHT_SCHEMA,
    PROFILE_SCHEMA,
    PROFILE_OVERRIDE_SCHEMA,
    build_inspector_projection,
    canonical_json,
    fingerprint,
    now_iso,
)
from persistence.quillframe_sqlite import QuillframeStore


class ContextRepository:
    def __init__(self, store: QuillframeStore) -> None:
        self.store = store

    def save_profile(self, project_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        if profile.get("schema") != PROFILE_SCHEMA or profile.get("authority") is not False:
            raise ValueError("valid non-authoritative semantic profile required")
        source_id = str(profile.get("source_object_id") or "").strip()
        if not source_id:
            raise ValueError("source_object_id required")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """UPDATE semantic_context_profiles
                   SET status='stale', stale_reason='source_fingerprint_changed', updated_at=?
                   WHERE source_object_id=? AND status='current' AND source_fingerprint<>?""",
                (now_iso(), source_id, profile["source_fingerprint"]),
            )
            conn.execute(
                """INSERT INTO semantic_context_profiles(
                   profile_id,source_object_id,source_object_type,source_fingerprint,profile_fingerprint,
                   description,trigger_when,estimated_tokens,semantic_tags_json,stage_affinities_json,
                   generator_provenance_json,manual_override_fingerprint,status,stale_reason,generated_at,updated_at,authority)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                   ON CONFLICT(profile_id) DO UPDATE SET
                     profile_fingerprint=excluded.profile_fingerprint,
                     description=excluded.description,trigger_when=excluded.trigger_when,
                     estimated_tokens=excluded.estimated_tokens,semantic_tags_json=excluded.semantic_tags_json,
                     stage_affinities_json=excluded.stage_affinities_json,
                     generator_provenance_json=excluded.generator_provenance_json,
                     manual_override_fingerprint=excluded.manual_override_fingerprint,
                     status=excluded.status,stale_reason=excluded.stale_reason,
                     generated_at=excluded.generated_at,updated_at=excluded.updated_at""",
                (
                    profile["profile_id"], source_id, profile["source_object_type"], profile["source_fingerprint"],
                    profile["profile_fingerprint"], profile.get("description", ""), profile.get("trigger_when", ""),
                    int(profile.get("estimated_tokens") or 0), canonical_json(profile.get("semantic_tags", [])),
                    canonical_json(profile.get("stage_affinities", [])), canonical_json(profile.get("generator_provenance", {})),
                    (profile.get("manual_override") or {}).get("override_fingerprint"), profile.get("status") or "current",
                    profile.get("stale_reason"), profile["generated_at"], now_iso(),
                ),
            )
            conn.commit()
        return {"profile_id": profile["profile_id"], "profile_fingerprint": profile["profile_fingerprint"], "persisted": True, "authority": False}

    def save_override(self, project_id: str, override: dict[str, Any]) -> dict[str, Any]:
        if override.get("schema") != PROFILE_OVERRIDE_SCHEMA or override.get("authority") is not False:
            raise ValueError("valid non-authoritative profile override required")
        with self.store.open_project(project_id) as conn:
            conn.execute(
                """INSERT INTO context_profile_overrides(source_object_id,override_id,override_fingerprint,fields_json,updated_by,updated_at,authority)
                   VALUES(?,?,?,?,?,?,0)
                   ON CONFLICT(source_object_id) DO UPDATE SET
                     override_id=excluded.override_id,override_fingerprint=excluded.override_fingerprint,
                     fields_json=excluded.fields_json,updated_by=excluded.updated_by,updated_at=excluded.updated_at""",
                (override["source_object_id"], override["override_id"], override["override_fingerprint"],
                 canonical_json(override["fields"]), override["updated_by"], override["updated_at"]),
            )
            conn.commit()
        return {"source_object_id": override["source_object_id"], "override_fingerprint": override["override_fingerprint"], "persisted": True, "authority": False}

    def get_override(self, project_id: str, source_object_id: str) -> dict[str, Any] | None:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("SELECT * FROM context_profile_overrides WHERE source_object_id=?", (source_object_id,)).fetchone()
        if not row:
            return None
        return {
            "schema": PROFILE_OVERRIDE_SCHEMA,
            "override_id": row["override_id"], "source_object_id": row["source_object_id"],
            "fields": json.loads(row["fields_json"]), "updated_by": row["updated_by"],
            "updated_at": row["updated_at"], "override_fingerprint": row["override_fingerprint"],
            "authority": False,
        }

    def list_profiles(self, project_id: str, source_object_id: str | None = None) -> list[dict[str, Any]]:
        with self.store.open_project(project_id) as conn:
            if source_object_id:
                rows = conn.execute("SELECT * FROM semantic_context_profiles WHERE source_object_id=? ORDER BY updated_at DESC", (source_object_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM semantic_context_profiles ORDER BY updated_at DESC").fetchall()
        return [self._profile_row(row) for row in rows]

    @staticmethod
    def _profile_row(row: Any) -> dict[str, Any]:
        return {
            "schema": PROFILE_SCHEMA, "profile_id": row["profile_id"], "source_object_id": row["source_object_id"],
            "source_object_type": row["source_object_type"], "source_fingerprint": row["source_fingerprint"],
            "profile_fingerprint": row["profile_fingerprint"], "description": row["description"], "trigger_when": row["trigger_when"],
            "estimated_tokens": row["estimated_tokens"], "semantic_tags": json.loads(row["semantic_tags_json"]),
            "stage_affinities": json.loads(row["stage_affinities_json"]), "generator_provenance": json.loads(row["generator_provenance_json"]),
            "status": row["status"], "stale_reason": row["stale_reason"], "generated_at": row["generated_at"], "authority": False,
        }

    def save_stage_selection(self, project_id: str, pool: dict[str, Any], greenlight: dict[str, Any]) -> dict[str, Any]:
        if greenlight.get("schema") != GREENLIGHT_SCHEMA or greenlight.get("authority") is not False:
            raise ValueError("valid stage greenlight required")
        if pool.get("candidate_universe_fingerprint") != greenlight.get("candidate_universe_fingerprint"):
            raise ValueError("pool/greenlight fingerprint mismatch")
        selection_id = "CTXS-" + greenlight["selection_fingerprint"][7:23]
        with self.store.open_project(project_id) as conn:
            conn.execute(
                """INSERT OR IGNORE INTO context_stage_selections(
                   selection_id,run_id,stage_id,candidate_universe_fingerprint,selection_fingerprint,pool_json,greenlight_json,status,created_at,authority)
                   VALUES(?,?,?,?,?,?,?,?,?,0)""",
                (selection_id, greenlight["run_id"], greenlight["stage_id"], greenlight["candidate_universe_fingerprint"],
                 greenlight["selection_fingerprint"], canonical_json(pool), canonical_json(greenlight), greenlight["status"], now_iso()),
            )
            conn.commit()
        return {"selection_id": selection_id, "selection_fingerprint": greenlight["selection_fingerprint"], "persisted": True, "authority": False}

    def save_freeze(self, project_id: str, freeze: dict[str, Any]) -> dict[str, Any]:
        if freeze.get("schema") != FREEZE_SCHEMA or freeze.get("authority") is not False:
            raise ValueError("valid non-authoritative context freeze required")
        selected = {stage: value.get("selected_object_ids", []) for stage, value in freeze.get("stage_greenlights", {}).items()}
        loaded = {stage: value.get("loaded_object_ids", value.get("selected_object_ids", [])) for stage, value in freeze.get("stage_greenlights", {}).items()}
        dropped = {stage: [x.get("object_id") for x in value.get("dropped_due_budget", [])] for stage, value in freeze.get("stage_greenlights", {}).items()}
        budget = {stage: {"hard_budget": value.get("hard_budget"), "estimated_tokens": value.get("estimated_tokens"), "status": value.get("status")} for stage, value in freeze.get("stage_greenlights", {}).items()}
        manifest_id = "CTX-" + freeze["freeze_fingerprint"][7:23]
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT OR IGNORE INTO context_freezes(freeze_id,run_id,task_mode,freeze_fingerprint,snapshot_json,status,supersedes_freeze_id,created_at,authority)
                   VALUES(?,?,?,?,?,?,?,?,0)""",
                (freeze["freeze_id"], freeze["run_id"], freeze["task_mode"], freeze["freeze_fingerprint"], canonical_json(freeze),
                 freeze.get("status") or "frozen", freeze.get("supersedes_freeze_id"), freeze.get("created_at") or now_iso()),
            )
            conn.execute(
                """INSERT OR IGNORE INTO context_manifests(
                   manifest_id,run_id,task_mode,selected_json,loaded_json,dropped_json,visibility_excluded_json,budget_json,content_fingerprint,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (manifest_id, freeze["run_id"], freeze["task_mode"], canonical_json(selected), canonical_json(loaded), canonical_json(dropped),
                 canonical_json({"source": "context_stage_selections"}), canonical_json(budget), freeze["freeze_fingerprint"], freeze.get("created_at") or now_iso()),
            )
            conn.commit()
        return {"freeze_id": freeze["freeze_id"], "manifest_id": manifest_id, "freeze_fingerprint": freeze["freeze_fingerprint"], "persisted": True, "authority": False}

    def get_freeze(self, project_id: str, *, freeze_id: str | None = None, run_id: str | None = None) -> dict[str, Any] | None:
        if not freeze_id and not run_id:
            raise ValueError("freeze_id or run_id required")
        with self.store.open_project(project_id) as conn:
            if freeze_id:
                row = conn.execute("SELECT snapshot_json FROM context_freezes WHERE freeze_id=?", (freeze_id,)).fetchone()
            else:
                row = conn.execute("SELECT snapshot_json FROM context_freezes WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run_id,)).fetchone()
        return json.loads(row["snapshot_json"]) if row else None

    def inspector_projection(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            rows = conn.execute("SELECT pool_json,greenlight_json FROM context_stage_selections WHERE run_id=? ORDER BY created_at,stage_id", (run_id,)).fetchall()
            freeze_row = conn.execute("SELECT snapshot_json FROM context_freezes WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run_id,)).fetchone()
        pools = [json.loads(row["pool_json"]) for row in rows]
        greenlights = [json.loads(row["greenlight_json"]) for row in rows]
        freeze = json.loads(freeze_row["snapshot_json"]) if freeze_row else None
        return build_inspector_projection(run_id=run_id, pools=pools, greenlights=greenlights, freeze=freeze)
