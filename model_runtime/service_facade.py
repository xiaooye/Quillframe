from __future__ import annotations

from typing import Any

from agent_runtime.runtime import QuillframeAgentRuntime


class ModelServiceFacade:
    """Stable Core-facing Model Service API over the existing Generic Model Runtime.

    User setup remains Endpoint + Access Token. Provider names/protocol dialects
    are runtime evidence, not product authority or a required setup choice.
    """

    def __init__(self, runtime: QuillframeAgentRuntime) -> None:
        self.runtime = runtime

    @staticmethod
    def _capability_projection(model: dict[str, Any]) -> dict[str, Any]:
        return {
            "model_id": model.get("model_id"),
            "display_name": model.get("display_name") or model.get("model_id"),
            "protocol": model.get("protocol") or model.get("protocol_family"),
            "context_window": model.get("context_window") or (model.get("metadata") or {}).get("context_window"),
            "capabilities": model.get("capabilities") or {},
            "authority": False,
        }

    def connect(self, endpoint: str, access_token: str) -> dict[str, Any]:
        return self.runtime.connect(endpoint, access_token)

    def list(self) -> dict[str, Any]:
        return self.runtime.list_model_services()

    def get(self, service_id: str) -> dict[str, Any]:
        return self.runtime.get_model_service(service_id)

    def discover(self, service_id: str) -> dict[str, Any]:
        """Refresh discovery from the configured endpoint using the host secret reference."""
        return self.runtime.refresh_model_service(service_id)

    def test(self, service_id: str, *, model_id: str | None = None, verify_tools: bool = False) -> dict[str, Any]:
        self.runtime._ensure_loaded(service_id)
        snapshot = self.runtime.model_runtime.snapshot(service_id)
        selected = model_id or (snapshot.models[0].model_id if snapshot.models else None)
        if not selected:
            raise ValueError("Model Service has no discovered models")
        model = self.runtime.model_runtime.probe_model(service_id, selected, verify_tools=verify_tools)
        # Persist fresh capability evidence if the service is durable. Only the
        # credential reference already in the snapshot is serialized; never the secret value.
        if self.runtime.repository is not None:
            self.runtime.repository.save_snapshot(snapshot)
        return {
            "schema": "quillframe_model_service_test_result_v1",
            "service_id": service_id,
            "model": self._capability_projection(model.to_dict()),
            "verify_tools": bool(verify_tools),
            "status": "verified",
            "authority": False,
            "canon_authority": False,
            "settlement_authority": False,
        }

    def capabilities(self, service_id: str) -> dict[str, Any]:
        service = self.get(service_id)
        models = [self._capability_projection(model) for model in service.get("models", [])]
        return {
            "schema": "quillframe_model_capability_matrix_v1",
            "service_id": service_id,
            "endpoint": service.get("endpoint"),
            "credential_present": bool(service.get("credential_present")),
            "models": models,
            "unknown_is_not_supported": False,
            "capability_grants_authority": False,
            "authority": False,
            "canon_authority": False,
            "settlement_authority": False,
        }

    def confirm_fiction_writing(self, confirmation: dict[str, Any]) -> dict[str, Any]:
        """Persist an explicit author-blind-audition result; never runs a model."""
        return self.runtime.confirm_fiction_writing(confirmation)

    def revoke_fiction_writing(self, service_id: str, model_id: str) -> dict[str, Any]:
        return self.runtime.revoke_fiction_writing(service_id, model_id)
