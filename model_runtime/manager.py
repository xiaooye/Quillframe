from __future__ import annotations

import json
from typing import Any, Protocol

from .contracts import (
    CapabilityEvidence, ModelServiceSnapshot, model_version_fingerprint, now_iso,
)
from .endpoint import normalize_endpoint
from .fiction_audition import selected_identity, validate_confirmation
from .runtime import ModelRuntime
from .secrets import SecretStore


class ModelServiceRepository(Protocol):
    def save_snapshot(self, snapshot: Any) -> dict[str, Any]: ...
    def find_service_by_endpoint(self, endpoint: str) -> dict[str, Any] | None: ...
    def get_internal(self, service_id: str) -> dict[str, Any]: ...
    def get_service(self, service_id: str) -> dict[str, Any]: ...
    def delete_service(self, service_id: str) -> None: ...
    def list_services(self) -> list[dict[str, Any]]: ...


class ModelServiceManager:
    """Durable Model Service lifecycle with exactly endpoint + token as user setup input."""

    def __init__(self, runtime: ModelRuntime, repository: ModelServiceRepository, secrets: SecretStore) -> None:
        self.runtime = runtime
        self.repository = repository
        self.secrets = secrets

    def connect(self, endpoint: str, access_token: str) -> dict[str, Any]:
        normalized = normalize_endpoint(endpoint, self.runtime.endpoint_policy).configured_endpoint
        existing = self.repository.find_service_by_endpoint(normalized)
        service_id = existing["service_id"] if existing else None
        old_ref = existing.get("credential_ref") if existing else None
        if access_token == "" and old_ref:
            return self.refresh(service_id)
        snapshot = self.runtime.connect(normalized, access_token, service_id=service_id)
        self.repository.save_snapshot(snapshot)
        if old_ref and old_ref != snapshot.credential_ref:
            self.secrets.delete(old_ref)
        return self.repository.get_service(snapshot.service_id)

    def hydrate(self, service_id: str) -> ModelServiceSnapshot:
        """Restore a fingerprint-bound snapshot after process restart without model execution."""
        current = self.repository.get_internal(service_id)
        raw = current.get("snapshot_json")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"Model Service {service_id} has no durable snapshot")
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("service_id") != service_id:
            raise ValueError(f"Model Service {service_id} snapshot identity mismatch")
        snapshot = ModelServiceSnapshot.from_dict(value)
        return self.runtime.restore_snapshot(snapshot)

    def hydrate_all(self) -> dict[str, Any]:
        restored: list[str] = []
        stale: list[dict[str, str]] = []
        for public in self.repository.list_services():
            if public.get("enabled") not in {1, True}:
                continue
            service_id = str(public["service_id"])
            try:
                self.hydrate(service_id)
                restored.append(service_id)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                stale.append({"service_id": service_id, "error": str(exc)})
        return {"restored": restored, "stale": stale, "model_execution": False}

    def refresh(self, service_id: str) -> dict[str, Any]:
        current = self.repository.get_internal(service_id)
        credential_ref = current.get("credential_ref")
        token = self.secrets.resolve(credential_ref) if credential_ref else ""
        snapshot = self.runtime.connect(current["endpoint"], token, service_id=service_id, credential_ref=credential_ref)
        self.repository.save_snapshot(snapshot)
        return self.repository.get_service(service_id)

    def replace_token(self, service_id: str, access_token: str) -> dict[str, Any]:
        current = self.repository.get_internal(service_id)
        old_ref = current.get("credential_ref")
        snapshot = self.runtime.connect(current["endpoint"], access_token, service_id=service_id)
        self.repository.save_snapshot(snapshot)
        if old_ref and old_ref != snapshot.credential_ref:
            self.secrets.delete(old_ref)
        return self.repository.get_service(service_id)

    def remove_token(self, service_id: str) -> dict[str, Any]:
        current = self.repository.get_internal(service_id)
        old_ref = current.get("credential_ref")
        try:
            snapshot = self.runtime.snapshot(service_id)
        except Exception:
            snapshot = self.hydrate(service_id)
        snapshot.credential_ref = None
        snapshot.secret_present = False
        snapshot.snapshot_fingerprint = ""
        snapshot.__post_init__()
        self.repository.save_snapshot(snapshot)
        if old_ref:
            self.secrets.delete(old_ref)
        return self.repository.get_service(service_id)

    def delete(self, service_id: str) -> None:
        current = self.repository.get_internal(service_id)
        credential_ref = current.get("credential_ref")
        self.repository.delete_service(service_id)
        self.runtime.forget(service_id)
        if credential_ref:
            self.secrets.delete(credential_ref)

    def list(self) -> list[dict[str, Any]]:
        return self.repository.list_services()

    def get(self, service_id: str) -> dict[str, Any]:
        return self.repository.get_service(service_id)

    def confirm_fiction_writing(self, confirmation: dict[str, Any]) -> dict[str, Any]:
        receipt = validate_confirmation(confirmation)
        service_id, model_id, selected_version = selected_identity(receipt)
        snapshots: dict[str, ModelServiceSnapshot] = {}
        for candidate in receipt["plan"]["candidate_models"]:
            candidate_service = candidate["service_id"]
            snapshot = snapshots.get(candidate_service)
            if snapshot is None:
                try:
                    snapshot = self.runtime.snapshot(candidate_service)
                except Exception:
                    snapshot = self.hydrate(candidate_service)
                snapshots[candidate_service] = snapshot
            current_model = next(
                (item for item in snapshot.models if item.model_id == candidate["model_id"]),
                None,
            )
            if current_model is None:
                raise ValueError("fiction audition candidate is not in the current Model Service snapshot")
            if (
                not current_model.protocol
                or current_model.capability_state("text") != "verified"
            ):
                raise ValueError(
                    "fiction audition candidates require resolved protocol and verified text capability"
                )
            if model_version_fingerprint(candidate_service, current_model) != candidate["model_version_fingerprint"]:
                raise ValueError("fiction audition candidate version no longer matches the current snapshot")
        snapshot = snapshots[service_id]
        model = next((item for item in snapshot.models if item.model_id == model_id), None)
        if model is None or model_version_fingerprint(service_id, model) != selected_version:
            raise ValueError("selected fiction audition model version no longer matches")
        model.metadata["quillframe_fiction_audition"] = receipt
        model.capabilities["fiction_writing"] = CapabilityEvidence(
            "fiction_writing", "verified", "manual_override", now_iso(),
            detail="Author selected this provider-visible model version in a blinded fiction audition.",
            evidence_ref=receipt["confirmation_fingerprint"],
        )
        snapshot.snapshot_fingerprint = ""
        snapshot.__post_init__()
        self.repository.save_snapshot(snapshot)
        return self.repository.get_service(service_id)

    def revoke_fiction_writing(self, service_id: str, model_id: str) -> dict[str, Any]:
        try:
            snapshot = self.runtime.snapshot(service_id)
        except Exception:
            snapshot = self.hydrate(service_id)
        model = next((item for item in snapshot.models if item.model_id == model_id), None)
        if model is None:
            raise ValueError("fiction model is not in the current Model Service snapshot")
        model.capabilities.pop("fiction_writing", None)
        model.metadata.pop("quillframe_fiction_audition", None)
        snapshot.snapshot_fingerprint = ""
        snapshot.__post_init__()
        self.repository.save_snapshot(snapshot)
        return self.repository.get_service(service_id)
