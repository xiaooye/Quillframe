from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

PROTOCOLS = {"openai_chat_completions", "openai_responses", "anthropic_messages"}
CAPABILITY_STATES = {"verified", "detected", "manually_configured", "unavailable", "unknown"}
CAPABILITIES = {
    "text", "streaming", "tool_calling", "parallel_tool_calling", "structured_output",
    "json_schema", "vision", "reasoning_control", "context_window",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilityEvidence:
    capability: str
    state: str
    provenance: str
    observed_at: str
    detail: str | None = None
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if self.capability not in CAPABILITIES:
            raise ValueError(f"unknown model capability: {self.capability}")
        if self.state not in CAPABILITY_STATES:
            raise ValueError(f"invalid capability state: {self.state}")
        if self.provenance not in {"declared", "probed", "verified", "manual_override", "unknown"}:
            raise ValueError(f"invalid capability provenance: {self.provenance}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "state": self.state,
            "provenance": self.provenance,
            "observed_at": self.observed_at,
            "detail": self.detail,
            "evidence_ref": self.evidence_ref,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CapabilityEvidence":
        return cls(
            capability=str(value["capability"]), state=str(value["state"]), provenance=str(value["provenance"]),
            observed_at=str(value["observed_at"]), detail=str(value["detail"]) if value.get("detail") is not None else None,
            evidence_ref=str(value["evidence_ref"]) if value.get("evidence_ref") is not None else None,
        )


@dataclass
class DiscoveredModel:
    model_id: str
    display_name: str | None = None
    protocol: str | None = None
    auth_style: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, CapabilityEvidence] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        if self.protocol is not None and self.protocol not in PROTOCOLS:
            raise ValueError(f"invalid protocol: {self.protocol}")
        if self.auth_style is not None and self.auth_style not in {"bearer", "x_api_key", "none"}:
            raise ValueError(f"invalid auth style: {self.auth_style}")

    def capability_state(self, name: str) -> str:
        evidence = self.capabilities.get(name)
        return evidence.state if evidence else "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name or self.model_id,
            "protocol": self.protocol,
            "auth_style": self.auth_style,
            "metadata": self.metadata,
            "capabilities": {k: v.to_dict() for k, v in sorted(self.capabilities.items())},
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DiscoveredModel":
        raw_caps = value.get("capabilities") or {}
        capabilities = {str(name): CapabilityEvidence.from_dict(dict(item)) for name, item in raw_caps.items() if isinstance(item, dict)}
        return cls(
            model_id=str(value["model_id"]), display_name=str(value["display_name"]) if value.get("display_name") is not None else None,
            protocol=str(value["protocol"]) if value.get("protocol") is not None else None,
            auth_style=str(value["auth_style"]) if value.get("auth_style") is not None else None,
            metadata=dict(value.get("metadata") or {}), capabilities=capabilities,
        )


@dataclass
class ModelServiceSnapshot:
    service_id: str
    endpoint: str
    credential_ref: str | None
    discovered_at: str
    auth_style: str
    models: list[DiscoveredModel]
    api_surfaces: dict[str, str] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    secret_present: bool = False
    snapshot_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_fingerprint:
            self.snapshot_fingerprint = fingerprint(self.fingerprint_payload())

    def fingerprint_payload(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id, "endpoint": self.endpoint, "credential_ref": self.credential_ref,
            "discovered_at": self.discovered_at, "auth_style": self.auth_style,
            "models": [m.to_dict() for m in self.models], "api_surfaces": self.api_surfaces,
            "diagnostics": self.diagnostics, "secret_present": self.secret_present,
        }

    def to_dict(self) -> dict[str, Any]:
        value = self.fingerprint_payload()
        value.update({"schema": "quillframe_model_service_snapshot_v1", "snapshot_fingerprint": self.snapshot_fingerprint})
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelServiceSnapshot":
        if value.get("schema") not in {None, "quillframe_model_service_snapshot_v1"}:
            raise ValueError("unsupported model service snapshot schema")
        claimed = str(value.get("snapshot_fingerprint") or "")
        snapshot = cls(
            service_id=str(value["service_id"]), endpoint=str(value["endpoint"]),
            credential_ref=str(value["credential_ref"]) if value.get("credential_ref") is not None else None,
            discovered_at=str(value["discovered_at"]), auth_style=str(value.get("auth_style") or "unknown"),
            models=[DiscoveredModel.from_dict(dict(item)) for item in value.get("models") or [] if isinstance(item, dict)],
            api_surfaces={str(k): str(v) for k, v in dict(value.get("api_surfaces") or {}).items()},
            diagnostics=[dict(item) for item in value.get("diagnostics") or [] if isinstance(item, dict)],
            secret_present=bool(value.get("secret_present", False)), snapshot_fingerprint="",
        )
        actual = fingerprint(snapshot.fingerprint_payload())
        if claimed and claimed != actual:
            raise ValueError(f"model service snapshot fingerprint mismatch: {claimed} != {actual}")
        snapshot.snapshot_fingerprint = actual
        return snapshot


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"call_id": self.call_id, "name": self.name, "arguments": self.arguments}


@dataclass
class ModelTurn:
    protocol: str
    model_id: str
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    response_id: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    opaque_continuation: Any = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol, "model_id": self.model_id, "text": self.text,
            "tool_calls": [c.to_dict() for c in self.tool_calls], "finish_reason": self.finish_reason,
            "usage": self.usage, "response_id": self.response_id, "raw_metadata": self.raw_metadata,
            "opaque_continuation_present": self.opaque_continuation is not None,
        }
