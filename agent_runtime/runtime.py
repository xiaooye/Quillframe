from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from model_runtime import EndpointPolicy, ModelRuntime, ModelRuntimeError, ModelTransport, SecretStore
from model_runtime.manager import ModelServiceManager
from model_runtime.persistence import SQLiteModelServiceRepository
from persistence.quillframe_sqlite import QuillframeStore

from .contracts import AgentJob, AgentResult
from .hooks import AgentExecutionHooks
from .runner import AgentRunner, CancellationToken
from .tools import ToolRuntime, ToolSpec


class QuillframeAgentRuntime:
    """Embeddable Quillframe-owned Agent Runtime.

    Hosts inject secret storage, operational capabilities, and durable execution
    hooks. When a Quillframe SQLite store is supplied, Model Service metadata is
    durable and hydrated on restart; credential values remain outside SQLite.
    """

    def __init__(
        self,
        *,
        secret_store: SecretStore,
        transport: ModelTransport | None = None,
        endpoint_policy: EndpointPolicy | None = None,
        host_capabilities: set[str] | None = None,
        store: QuillframeStore | None = None,
        execution_hooks: AgentExecutionHooks | None = None,
    ) -> None:
        self.secret_store = secret_store
        self.model_runtime = ModelRuntime(secret_store, transport=transport, endpoint_policy=endpoint_policy)
        self.tool_runtime = ToolRuntime(host_capabilities=set(host_capabilities or set()))
        self.runner = AgentRunner(self.model_runtime, self.tool_runtime, execution_hooks=execution_hooks)
        self.repository = SQLiteModelServiceRepository(store) if store is not None else None
        self.services = ModelServiceManager(self.model_runtime, self.repository, secret_store) if self.repository is not None else None
        self.hydrate_report = self.services.hydrate_all() if self.services is not None else {"restored": [], "stale": [], "model_execution": False}

    @staticmethod
    def _projection(value: dict[str, Any]) -> dict[str, Any]:
        return {"schema": "quillframe_model_service_projection_v1", **value, "authority": False}

    def connect(self, endpoint: str, access_token: str) -> dict[str, Any]:
        """Public model setup boundary: exactly API Endpoint + Access Token."""
        if self.services is not None:
            return self._projection(self.services.connect(endpoint, access_token))
        snapshot = self.model_runtime.connect(endpoint, access_token)
        return self._projection({
            "service_id": snapshot.service_id,
            "endpoint": snapshot.endpoint,
            "credential_present": snapshot.secret_present,
            "discovery_state": "connected",
            "snapshot_fingerprint": snapshot.snapshot_fingerprint,
            "last_checked_at": snapshot.discovered_at,
            "models": [model.to_dict() for model in snapshot.models],
        })

    def list_model_services(self) -> dict[str, Any]:
        items = self.services.list() if self.services is not None else [
            {
                "service_id": snapshot.service_id,
                "endpoint": snapshot.endpoint,
                "credential_present": snapshot.secret_present,
                "discovery_state": "connected",
                "snapshot_fingerprint": snapshot.snapshot_fingerprint,
                "last_checked_at": snapshot.discovered_at,
            }
            for snapshot in self.model_runtime._snapshots.values()
        ]
        return {"schema": "quillframe_model_service_list_v1", "items": items, "authority": False}

    def supports_durable_model_request(
        self, service_id: str, model_preference: str | None = None,
    ) -> bool:
        """Report the exact loopback relay path that consumes request keys."""
        try:
            snapshot = self.model_runtime.snapshot(service_id)
            host = (urlsplit(snapshot.endpoint).hostname or "").lower()
        except (ModelRuntimeError, ValueError):
            return False
        if host not in {"127.0.0.1", "::1", "localhost"}:
            return False
        models = [
            model for model in snapshot.models
            if model.model_id == "quillframe-chat-host-relay"
            and model.protocol == "openai_chat_completions"
        ]
        return bool(models) and model_preference in {None, "quillframe-chat-host-relay"}

    def get_model_service(self, service_id: str) -> dict[str, Any]:
        if self.services is not None:
            return self._projection(self.services.get(service_id))
        snapshot = self.model_runtime.snapshot(service_id)
        return self._projection({
            "service_id": snapshot.service_id,
            "endpoint": snapshot.endpoint,
            "credential_present": snapshot.secret_present,
            "discovery_state": "connected",
            "snapshot_fingerprint": snapshot.snapshot_fingerprint,
            "last_checked_at": snapshot.discovered_at,
            "models": [model.to_dict() for model in snapshot.models],
        })

    def refresh_model_service(self, service_id: str) -> dict[str, Any]:
        if self.services is None:
            raise RuntimeError("refresh requires durable Model Service repository")
        return self._projection(self.services.refresh(service_id))

    def replace_access_token(self, service_id: str, access_token: str) -> dict[str, Any]:
        if self.services is None:
            raise RuntimeError("token replacement requires durable Model Service repository")
        return self._projection(self.services.replace_token(service_id, access_token))

    def remove_access_token(self, service_id: str) -> dict[str, Any]:
        if self.services is None:
            raise RuntimeError("token removal requires durable Model Service repository")
        return self._projection(self.services.remove_token(service_id))

    def delete_model_service(self, service_id: str) -> dict[str, Any]:
        if self.services is not None:
            self.services.delete(service_id)
        else:
            self.model_runtime.disconnect(service_id)
        return {"schema": "quillframe_model_service_delete_result_v1", "service_id": service_id, "deleted": True, "authority": False}

    def confirm_fiction_writing(self, confirmation: dict[str, Any]) -> dict[str, Any]:
        if self.services is None:
            raise RuntimeError("fiction audition confirmation requires durable Model Service storage")
        return self._projection(self.services.confirm_fiction_writing(confirmation))

    def revoke_fiction_writing(self, service_id: str, model_id: str) -> dict[str, Any]:
        if self.services is None:
            raise RuntimeError("fiction capability revocation requires durable Model Service storage")
        return self._projection(self.services.revoke_fiction_writing(service_id, model_id))

    def register_tool(self, spec: ToolSpec) -> None:
        self.tool_runtime.register(spec)

    def _ensure_loaded(self, service_id: str) -> None:
        try:
            self.model_runtime.snapshot(service_id)
            return
        except ModelRuntimeError as exc:
            if exc.code != "unknown_model_service" or self.services is None:
                raise
        self.services.hydrate(service_id)

    def run(self, job: AgentJob, *, cancellation: CancellationToken | None = None) -> AgentResult:
        self._ensure_loaded(job.service_id)
        return self.runner.run(job, cancellation=cancellation)
