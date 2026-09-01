from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from model_runtime.contracts import canonical_json, fingerprint
from model_runtime.deadlines import MAX_REQUEST_TIMEOUT_SECONDS
from model_runtime.structured_output import validate_output_schema

_SECRET_KEYS = {"token", "access_token", "api_key", "apikey", "password", "secret", "authorization", "credential"}


def _secret_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            child_path = f"{path}.{key}"
            if normalized in _SECRET_KEYS:
                found.append(child_path)
            found.extend(_secret_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_secret_paths(child, f"{path}[{index}]"))
    return found


@dataclass(frozen=True)
class AgentBudget:
    max_steps: int = 24
    max_model_requests: int = 24
    max_tool_calls: int = 64
    max_parallel_tool_calls: int = 8
    model_context_limit: int = 200_000
    max_output_tokens: int = 4096
    run_cost_budget: int = 10_000_000
    max_elapsed_ms: int = 15 * 60 * 1000
    max_model_request_ms: int | None = None

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_model_request_ms is not None and (
            isinstance(self.max_model_request_ms, bool)
            or self.max_model_request_ms > int(MAX_REQUEST_TIMEOUT_SECONDS * 1000)
        ):
            raise ValueError(
                f"max_model_request_ms must be a positive integer at most {int(MAX_REQUEST_TIMEOUT_SECONDS * 1000)}"
            )

    def to_dict(self) -> dict[str, int]:
        value = {
            "max_steps": self.max_steps,
            "max_model_requests": self.max_model_requests,
            "max_tool_calls": self.max_tool_calls,
            "max_parallel_tool_calls": self.max_parallel_tool_calls,
            "model_context_limit": self.model_context_limit,
            "max_output_tokens": self.max_output_tokens,
            "run_cost_budget": self.run_cost_budget,
            "max_elapsed_ms": self.max_elapsed_ms,
        }
        # Omitting an unset request limit preserves historical job fingerprints.
        if self.max_model_request_ms is not None:
            value["max_model_request_ms"] = self.max_model_request_ms
        return value


@dataclass
class AgentJob:
    job_id: str
    session_id: str
    run_id: str
    task_mode: str
    runtime_role: str
    service_id: str
    instruction: str
    context: list[dict[str, Any]] = field(default_factory=list)
    tool_grants: set[str] = field(default_factory=set)
    model_preference: str | None = None
    required_model_capabilities: set[str] = field(default_factory=lambda: {"text"})
    authority: dict[str, Any] = field(default_factory=dict)
    budgets: AgentBudget = field(default_factory=AgentBudget)
    idempotency_key: str | None = None
    output_schema: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        for name in ("job_id", "session_id", "run_id", "task_mode", "runtime_role", "service_id", "instruction"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.output_schema is not None:
            validate_output_schema(self.output_schema)
            if self.tool_grants:
                raise ValueError("native output_schema is supported only for tool-free jobs")
        payload = self.to_dict(include_fingerprint=False)
        secret_paths = _secret_paths(payload)
        if secret_paths:
            raise ValueError("AgentJob contains forbidden secret-bearing fields: " + ", ".join(secret_paths))

    @property
    def input_fingerprint(self) -> str:
        return fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema": "quillframe_agent_job_v1",
            "job_id": self.job_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "task_mode": self.task_mode,
            "runtime_role": self.runtime_role,
            "service_id": self.service_id,
            "instruction": self.instruction,
            "context": self.context,
            "tool_grants": sorted(self.tool_grants),
            "model_preference": self.model_preference,
            "required_model_capabilities": sorted(self.required_model_capabilities),
            "authority": self.authority,
            "budgets": self.budgets.to_dict(),
            "idempotency_key": self.idempotency_key,
        }
        # Absent constraints must not change existing jobs or their fingerprints.
        if self.output_schema is not None:
            value["output_schema"] = self.output_schema
        if include_fingerprint:
            value["input_fingerprint"] = fingerprint(value)
        return value


@dataclass
class AgentResult:
    job_id: str
    session_id: str
    run_id: str
    status: str
    model_service_id: str
    model_id: str
    protocol: str
    input_fingerprint: str
    model_version_fingerprint: str | None = None
    model_version_identity_strength: str | None = None
    final_text: str = ""
    steps: int = 0
    model_requests: int = 0
    tool_calls: int = 0
    tool_receipts: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any] | str] = field(default_factory=list)

    def __post_init__(self) -> None:
        allowed = {"completed", "cancelled", "budget_exhausted", "model_pending", "model_failed", "tool_failed", "checkpoint_failed", "side_effect_unconfirmed"}
        if self.status not in allowed:
            raise ValueError(f"invalid AgentResult status: {self.status}")
        secret_paths = _secret_paths(self.to_dict())
        if secret_paths:
            raise ValueError("AgentResult contains forbidden secret-bearing fields: " + ", ".join(secret_paths))

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema": "quillframe_agent_result_v1",
            "job_id": self.job_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "status": self.status,
            "final_text": self.final_text,
            "model_service_id": self.model_service_id,
            "model_id": self.model_id,
            "protocol": self.protocol,
            "input_fingerprint": self.input_fingerprint,
            "steps": self.steps,
            "model_requests": self.model_requests,
            "tool_calls": self.tool_calls,
            "tool_receipts": self.tool_receipts,
            "usage": self.usage,
            "errors": self.errors,
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
        }
        if self.model_version_fingerprint is not None:
            value["model_version_fingerprint"] = self.model_version_fingerprint
        if self.model_version_identity_strength is not None:
            value["model_version_identity_strength"] = self.model_version_identity_strength
        return value


def job_fingerprint_payload(value: dict[str, Any]) -> str:
    """Deterministic helper for external typed bridges."""
    return fingerprint(canonical_json(value))
