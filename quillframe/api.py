from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_runtime import AgentJob, AgentResult, CancellationToken, QuillframeAgentRuntime, ToolSpec
from agent_runtime.hooks import AgentExecutionHooks
from model_runtime import EndpointPolicy, ModelTransport, SecretStore
from persistence.quillframe_sqlite import QuillframeStore


class Quillframe:
    """Embeddable Quillframe Core façade.

    Hosts own secret storage and host capabilities. Ordinary users still connect
    model inference with exactly two product inputs: API Endpoint + Access Token.
    Quillframe owns discovery, model selection, agent/tool execution and runtime
    invariants behind this façade.
    """

    def __init__(
        self,
        *,
        secret_store: SecretStore,
        data_root: str | Path | None = None,
        transport: ModelTransport | None = None,
        endpoint_policy: EndpointPolicy | None = None,
        host_capabilities: set[str] | None = None,
        execution_hooks: AgentExecutionHooks | None = None,
    ) -> None:
        store = QuillframeStore(Path(data_root).expanduser()) if data_root is not None else None
        self._runtime = QuillframeAgentRuntime(
            secret_store=secret_store,
            transport=transport,
            endpoint_policy=endpoint_policy,
            host_capabilities=host_capabilities,
            store=store,
            execution_hooks=execution_hooks,
        )

    @property
    def hydrate_report(self) -> dict[str, Any]:
        return dict(self._runtime.hydrate_report)

    def connect(self, endpoint: str, access_token: str) -> dict[str, Any]:
        """Connect one Model Service using exactly endpoint + access token."""
        return self._runtime.connect(endpoint, access_token)

    def list_model_services(self) -> dict[str, Any]:
        return self._runtime.list_model_services()

    def inspect_model_service(self, service_id: str) -> dict[str, Any]:
        return self._runtime.get_model_service(service_id)

    def refresh_model_service(self, service_id: str) -> dict[str, Any]:
        return self._runtime.refresh_model_service(service_id)

    def replace_access_token(self, service_id: str, access_token: str) -> dict[str, Any]:
        return self._runtime.replace_access_token(service_id, access_token)

    def remove_access_token(self, service_id: str) -> dict[str, Any]:
        return self._runtime.remove_access_token(service_id)

    def delete_model_service(self, service_id: str) -> dict[str, Any]:
        return self._runtime.delete_model_service(service_id)

    def register_tool(self, spec: ToolSpec) -> None:
        self._runtime.register_tool(spec)

    def run(self, job: AgentJob, *, cancellation: CancellationToken | None = None) -> AgentResult:
        """Run one frozen, bounded AgentJob through Quillframe's own agent loop."""
        return self._runtime.run(job, cancellation=cancellation)
