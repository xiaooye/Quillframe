from __future__ import annotations

from contextlib import closing
import json
import sqlite3
import uuid
from typing import Any

from persistence.quillframe_sqlite import QuillframeStore, _connect_readonly, canonical_json, now_iso
from .contracts import ModelServiceSnapshot, fingerprint


class SQLiteModelServiceRepository:
    """Durable Model Service metadata. Secret values never enter SQLite."""

    def __init__(self, store: QuillframeStore | None = None) -> None:
        self.store = store or QuillframeStore()

    def _connect(self) -> sqlite3.Connection:
        self.store.initialize_global()
        if self.store.read_only:
            return _connect_readonly(self.store.global_db)
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(self.store.global_db, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            return conn
        except Exception:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            raise

    def save_snapshot(self, snapshot: ModelServiceSnapshot) -> dict[str, Any]:
        data = snapshot.to_dict()
        serialized = canonical_json(data)
        lowered = serialized.lower()
        for forbidden in ("authorization", "api_key", "access_token", "password"):
            if f'"{forbidden}"' in lowered:
                raise ValueError(f"snapshot contains forbidden secret field: {forbidden}")
        stamp = now_iso()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT created_at FROM model_services WHERE service_id=?", (snapshot.service_id,)).fetchone()
            created_at = existing["created_at"] if existing else stamp
            conn.execute(
                """INSERT INTO model_services(
                    service_id,endpoint,credential_ref,enabled,auth_style,discovery_state,
                    snapshot_fingerprint,snapshot_json,last_checked_at,created_at,updated_at
                ) VALUES(?,?,?,1,?,'connected',?,?,?,?,?)
                ON CONFLICT(service_id) DO UPDATE SET
                    endpoint=excluded.endpoint,credential_ref=excluded.credential_ref,enabled=1,
                    auth_style=excluded.auth_style,discovery_state='connected',
                    snapshot_fingerprint=excluded.snapshot_fingerprint,snapshot_json=excluded.snapshot_json,
                    last_checked_at=excluded.last_checked_at,updated_at=excluded.updated_at""",
                (
                    snapshot.service_id, snapshot.endpoint, snapshot.credential_ref, snapshot.auth_style,
                    snapshot.snapshot_fingerprint, serialized, snapshot.discovered_at, created_at, stamp,
                ),
            )
            conn.execute("DELETE FROM discovered_models WHERE service_id=?", (snapshot.service_id,))
            for model in snapshot.models:
                cap_json = canonical_json({k: v.to_dict() for k, v in sorted(model.capabilities.items())})
                context_window = model.metadata.get("context_window")
                if not isinstance(context_window, int) or isinstance(context_window, bool):
                    context_window = None
                cost_metadata = model.metadata.get("cost") if isinstance(model.metadata.get("cost"), dict) else {}
                conn.execute(
                    """INSERT INTO discovered_models(
                        service_id,model_id,display_name,protocol_family,auth_style,enabled,context_window,
                        metadata_json,cost_metadata_json,capability_snapshot_json,discovered_at,updated_at
                    ) VALUES(?,?,?,?,?,1,?,?,?,?,?,?)""",
                    (
                        snapshot.service_id, model.model_id, model.display_name or model.model_id, model.protocol, model.auth_style,
                        context_window, canonical_json(model.metadata), canonical_json(cost_metadata), cap_json, snapshot.discovered_at, stamp,
                    ),
                )
                for evidence in model.capabilities.values():
                    payload = {"service_id": snapshot.service_id, "model_id": model.model_id, "protocol_family": model.protocol, **evidence.to_dict()}
                    conn.execute(
                        """INSERT INTO model_capability_evidence(
                            evidence_id,service_id,model_id,capability,state,provenance,protocol_family,
                            detail,evidence_ref,evidence_fingerprint,observed_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            "modelev_" + uuid.uuid4().hex, snapshot.service_id, model.model_id,
                            evidence.capability, evidence.state, evidence.provenance, model.protocol,
                            evidence.detail, evidence.evidence_ref, fingerprint(payload), evidence.observed_at,
                        ),
                    )
            conn.commit()
        return {"service_id": snapshot.service_id, "snapshot_fingerprint": snapshot.snapshot_fingerprint, "models": len(snapshot.models)}

    def list_services(self) -> list[dict[str, Any]]:
        if self.store.read_only and not self.store.global_db.exists():
            return []
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT service_id,endpoint,enabled,auth_style,discovery_state,snapshot_fingerprint,last_checked_at,created_at,updated_at,credential_ref IS NOT NULL AS credential_present FROM model_services ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_service(self, service_id: str) -> dict[str, Any]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT service_id,endpoint,enabled,auth_style,discovery_state,snapshot_fingerprint,last_checked_at,created_at,updated_at,credential_ref IS NOT NULL AS credential_present FROM model_services WHERE service_id=?",
                (service_id,),
            ).fetchone()
            if not row:
                raise KeyError(service_id)
            raw_models = [dict(r) for r in conn.execute(
                "SELECT model_id,display_name,protocol_family,auth_style,enabled,context_window,metadata_json,cost_metadata_json,capability_snapshot_json,discovered_at,updated_at FROM discovered_models WHERE service_id=? ORDER BY display_name,model_id",
                (service_id,),
            )]
        models: list[dict[str, Any]] = []
        for model in raw_models:
            model["metadata"] = json.loads(model.pop("metadata_json") or "{}")
            model["cost_metadata"] = json.loads(model.pop("cost_metadata_json") or "{}")
            model["capabilities"] = json.loads(model.pop("capability_snapshot_json") or "{}")
            models.append(model)
        return {**dict(row), "models": models, "authority": False}

    def get_internal(self, service_id: str) -> dict[str, Any]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT service_id,endpoint,credential_ref,enabled,auth_style,discovery_state,snapshot_fingerprint,snapshot_json,last_checked_at,created_at,updated_at FROM model_services WHERE service_id=?",
                (service_id,),
            ).fetchone()
        if not row:
            raise KeyError(service_id)
        return dict(row)

    def find_service_by_endpoint(self, endpoint: str) -> dict[str, Any] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT service_id,endpoint,credential_ref FROM model_services WHERE endpoint=?", (endpoint,)).fetchone()
        return dict(row) if row else None

    def set_credential_ref(self, service_id: str, credential_ref: str | None) -> None:
        with closing(self._connect()) as conn:
            cur = conn.execute("UPDATE model_services SET credential_ref=?,updated_at=? WHERE service_id=?", (credential_ref, now_iso(), service_id))
            if cur.rowcount != 1:
                raise KeyError(service_id)
            conn.commit()

    def delete_service(self, service_id: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM model_services WHERE service_id=?", (service_id,))
            conn.commit()
