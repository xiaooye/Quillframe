from __future__ import annotations

import uuid
from typing import Any

from .contracts import CapabilityEvidence, DiscoveredModel, ModelServiceSnapshot, ModelTurn, now_iso
from .endpoint import EndpointPolicy, normalize_endpoint
from .protocols import CODECS
from .secrets import SecretStore
from .transport import ModelTransport, TransportError, TransportResponse, UrllibTransport


class ModelRuntimeError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


_SECRET_METADATA_KEYS = {"token", "access_token", "api_key", "apikey", "password", "secret", "authorization", "credential"}


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_metadata(child)
            for key, child in value.items()
            if str(key).lower().replace("-", "_") not in _SECRET_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    return value


def _extract_models(payload: Any) -> list[DiscoveredModel]:
    if not isinstance(payload, dict):
        raise ValueError("models response must be an object")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("models response must contain a data array")
    models: list[DiscoveredModel] = []
    for item in data:
        if isinstance(item, str):
            models.append(DiscoveredModel(item)); continue
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or item.get("model") or "").strip()
        if not model_id:
            continue
        display = item.get("display_name") or item.get("name") or model_id
        protocol = None
        explicit = str(item.get("protocol") or item.get("api_protocol") or "").strip()
        if explicit in CODECS:
            protocol = explicit
        endpoint_hint = str(item.get("endpoint") or "")
        if not protocol:
            if endpoint_hint.endswith("/chat/completions"):
                protocol = "openai_chat_completions"
            elif endpoint_hint.endswith("/responses"):
                protocol = "openai_responses"
            elif endpoint_hint.endswith("/messages"):
                protocol = "anthropic_messages"
        models.append(DiscoveredModel(model_id, str(display), protocol=protocol, metadata=_sanitize_metadata(item)))
    return models


class ModelRuntime:
    def __init__(self, secret_store: SecretStore, transport: ModelTransport | None = None, endpoint_policy: EndpointPolicy | None = None) -> None:
        self.secret_store = secret_store
        self.endpoint_policy = endpoint_policy or EndpointPolicy()
        self.transport = transport or UrllibTransport(
            allow_loopback=self.endpoint_policy.allow_loopback,
            allow_private_network=self.endpoint_policy.allow_private_network,
        )
        self._snapshots: dict[str, ModelServiceSnapshot] = {}

    def _request_json(self, method: str, url: str, *, token: str, auth_style: str, body: dict[str, Any] | None = None, timeout: float) -> TransportResponse:
        try:
            return self.transport.request_json(method, url, token=token, auth_style=auth_style, body=body, timeout=timeout)
        except TransportError as exc:
            raise ModelRuntimeError(exc.code, str(exc)) from exc

    def connect(self, endpoint: str, access_token: str, *, service_id: str | None = None, credential_ref: str | None = None) -> ModelServiceSnapshot:
        layout = normalize_endpoint(endpoint, self.endpoint_policy)
        created_secret = credential_ref is None and bool(access_token)
        if credential_ref is not None and access_token and not self.secret_store.present(credential_ref):
            raise ModelRuntimeError("credential_ref_missing", "The supplied credential reference is not present in the secret store")
        credential_ref = credential_ref if credential_ref is not None else (self.secret_store.put(access_token) if access_token else None)
        token = access_token
        diagnostics: list[dict[str, Any]] = []
        exact = layout.exact_surface
        auth_order = ["x_api_key", "bearer", "none"] if exact == "anthropic_messages" else (["bearer", "x_api_key"] if token else ["none"])
        if token and "none" not in auth_order:
            auth_order.append("none")
        models: list[DiscoveredModel] = []
        selected_auth = "none" if not token else auth_order[0]
        models_url = layout.url_for("models")
        try:
            for auth_style in auth_order:
                response = self._request_json("GET", models_url, token=token, auth_style=auth_style, timeout=20.0)
                diagnostics.append({"stage": "model_discovery", "surface": "models", "auth_style": auth_style, "status": response.status})
                if 200 <= response.status < 300:
                    try:
                        models = _extract_models(response.body)
                    except ValueError as exc:
                        diagnostics.append({"stage": "model_discovery", "status": "invalid_payload", "message": str(exc)})
                        continue
                    selected_auth = auth_style
                    break
                if response.status not in {401, 403, 404, 405}:
                    break
        except ModelRuntimeError:
            if created_secret and credential_ref:
                self.secret_store.delete(credential_ref)
            raise
        if not models:
            if created_secret and credential_ref:
                self.secret_store.delete(credential_ref)
            raise ModelRuntimeError("model_discovery_failed", "Endpoint was reachable but no discoverable models were returned", detail=diagnostics)

        if exact in CODECS:
            for model in models:
                if model.protocol is None:
                    model.protocol = exact
        service_id = service_id or ("modelsvc_" + uuid.uuid4().hex)
        snapshot = ModelServiceSnapshot(
            service_id=service_id,
            endpoint=layout.configured_endpoint,
            credential_ref=credential_ref,
            discovered_at=now_iso(),
            auth_style=selected_auth,
            models=models,
            api_surfaces={"models": "verified", **({exact: "detected_from_endpoint"} if exact in CODECS else {})},
            diagnostics=diagnostics,
            secret_present=bool(credential_ref and self.secret_store.present(credential_ref)),
        )
        self._snapshots[service_id] = snapshot
        return snapshot

    def restore_snapshot(self, value: ModelServiceSnapshot | dict[str, Any]) -> ModelServiceSnapshot:
        """Hydrate verified durable Model Service metadata without re-probing or exposing secrets."""
        snapshot = value if isinstance(value, ModelServiceSnapshot) else ModelServiceSnapshot.from_dict(value)
        normalize_endpoint(snapshot.endpoint, self.endpoint_policy)
        self._snapshots[snapshot.service_id] = snapshot
        return snapshot

    def disconnect(self, service_id: str) -> None:
        snapshot = self._snapshots.pop(service_id, None)
        if snapshot and snapshot.credential_ref:
            self.secret_store.delete(snapshot.credential_ref)

    def forget(self, service_id: str) -> None:
        """Forget only in-memory execution state; durable secret ownership is managed elsewhere."""
        self._snapshots.pop(service_id, None)

    def snapshot(self, service_id: str) -> ModelServiceSnapshot:
        try:
            return self._snapshots[service_id]
        except KeyError as exc:
            raise ModelRuntimeError("unknown_model_service", service_id) from exc

    def list_services(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._snapshots.values()]

    def _token(self, snapshot: ModelServiceSnapshot) -> str:
        if not snapshot.credential_ref:
            return ""
        try:
            return self.secret_store.resolve(snapshot.credential_ref)
        except KeyError as exc:
            raise ModelRuntimeError("credential_unavailable", "Model Service credential reference cannot be resolved") from exc

    def probe_model(self, service_id: str, model_id: str, *, verify_tools: bool = False) -> DiscoveredModel:
        snapshot = self.snapshot(service_id)
        model = next((m for m in snapshot.models if m.model_id == model_id), None)
        if not model:
            raise ModelRuntimeError("unknown_model", model_id)
        layout = normalize_endpoint(snapshot.endpoint, self.endpoint_policy)
        token = self._token(snapshot)
        protocol_order = [model.protocol] if model.protocol else []
        if layout.exact_surface in CODECS and layout.exact_surface not in protocol_order:
            protocol_order.append(layout.exact_surface)
        for protocol in ("openai_chat_completions", "openai_responses", "anthropic_messages"):
            if protocol not in protocol_order:
                protocol_order.append(protocol)

        last_errors: list[dict[str, Any]] = []
        for protocol in protocol_order:
            codec = CODECS[protocol]
            auth_styles = [snapshot.auth_style]
            if codec.auth_style not in auth_styles:
                auth_styles.append(codec.auth_style)
            for auth_style in auth_styles:
                body = codec.request_body(model.model_id, [{"role": "user", "content": "Reply with exactly OK."}], [], 8)
                response = self._request_json("POST", layout.url_for(codec.surface), token=token, auth_style=auth_style, body=body, timeout=30.0)
                if not (200 <= response.status < 300) or not isinstance(response.body, dict):
                    last_errors.append({"protocol": protocol, "auth_style": auth_style, "status": response.status})
                    continue
                try:
                    codec.normalize(model.model_id, response.body)
                except (ValueError, TypeError) as exc:
                    last_errors.append({"protocol": protocol, "auth_style": auth_style, "status": "invalid_payload", "error": str(exc)})
                    continue
                model.protocol = protocol
                model.auth_style = auth_style
                stamp = now_iso()
                model.capabilities["text"] = CapabilityEvidence("text", "verified", "verified", stamp, evidence_ref=f"probe:{snapshot.service_id}:{model.model_id}:{protocol}:text")
                snapshot.api_surfaces[protocol] = "verified"
                if verify_tools:
                    self._probe_tools(snapshot, model, codec, auth_style)
                snapshot.snapshot_fingerprint = ""
                snapshot.__post_init__()
                return model
        raise ModelRuntimeError("model_protocol_unresolved", "No supported protocol produced a valid response for this model", detail=last_errors)

    def _probe_tools(self, snapshot: ModelServiceSnapshot, model: DiscoveredModel, codec: Any, auth_style: str) -> None:
        layout = normalize_endpoint(snapshot.endpoint, self.endpoint_policy)
        token = self._token(snapshot)
        tool = {"name": "quillframe_capability_probe", "description": "Return the supplied value through a tool call.", "input_schema": {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": {"type": "string"}}}}
        history = [{"role": "user", "content": "Call quillframe_capability_probe with value set to ok. Do not answer normally."}]
        body = codec.request_body(model.model_id, history, [tool], 32)
        response = self._request_json("POST", layout.url_for(codec.surface), token=token, auth_style=auth_style, body=body, timeout=30.0)
        stamp = now_iso()
        if 200 <= response.status < 300 and isinstance(response.body, dict):
            try:
                turn = codec.normalize(model.model_id, response.body)
            except (ValueError, TypeError):
                turn = ModelTurn(codec.protocol, model.model_id)
            if any(c.name == "quillframe_capability_probe" for c in turn.tool_calls):
                model.capabilities["tool_calling"] = CapabilityEvidence("tool_calling", "verified", "verified", stamp, evidence_ref=f"probe:{snapshot.service_id}:{model.model_id}:{codec.protocol}:tool")
                return
        model.capabilities["tool_calling"] = CapabilityEvidence("tool_calling", "unavailable", "probed", stamp, detail="bounded tool-call probe did not produce a valid tool call")

    def select_model(self, service_id: str, requirements: set[str], *, preference: str | None = None, allow_probe: bool = True) -> DiscoveredModel:
        snapshot = self.snapshot(service_id)
        ordered = list(snapshot.models)
        if preference:
            ordered.sort(key=lambda m: 0 if m.model_id == preference else 1)
        for model in ordered:
            if all(model.capability_state(req) == "verified" for req in requirements):
                return model
        if allow_probe:
            for model in ordered:
                try:
                    self.probe_model(service_id, model.model_id, verify_tools="tool_calling" in requirements)
                except ModelRuntimeError:
                    continue
                if all(model.capability_state(req) == "verified" for req in requirements):
                    return model
        raise ModelRuntimeError("no_eligible_model", "No discovered model has verified evidence for the required capabilities", detail={"requirements": sorted(requirements), "models": [m.model_id for m in ordered]})

    def invoke(self, service_id: str, model_id: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], *, max_output_tokens: int = 2048) -> ModelTurn:
        snapshot = self.snapshot(service_id)
        model = next((m for m in snapshot.models if m.model_id == model_id), None)
        if not model:
            raise ModelRuntimeError("unknown_model", model_id)
        if not model.protocol:
            model = self.probe_model(service_id, model_id, verify_tools=bool(tools))
        codec = CODECS[model.protocol]
        token = self._token(snapshot)
        layout = normalize_endpoint(snapshot.endpoint, self.endpoint_policy)
        body = codec.request_body(model.model_id, history, tools, max_output_tokens)
        auth_style = model.auth_style or snapshot.auth_style or codec.auth_style
        response = self._request_json("POST", layout.url_for(codec.surface), token=token, auth_style=auth_style, body=body, timeout=120.0)
        if not (200 <= response.status < 300) or not isinstance(response.body, dict):
            raise ModelRuntimeError("model_request_failed", f"model request failed with HTTP {response.status}")
        try:
            return codec.normalize(model.model_id, response.body)
        except (ValueError, TypeError, KeyError) as exc:
            raise ModelRuntimeError("model_response_invalid", str(exc)) from exc
