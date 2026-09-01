from __future__ import annotations

import uuid
from typing import Any

from .contracts import (
    CapabilityEvidence, DiscoveredModel, ModelServiceSnapshot, ModelTurn,
    model_version_fingerprint, now_iso,
)
from .deadlines import DEFAULT_REQUEST_TIMEOUT_SECONDS, validate_request_timeout
from .endpoint import EndpointPolicy, normalize_endpoint
from .fiction_audition import selected_identity, validate_confirmation
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

    def _request_json(self, method: str, url: str, *, token: str, auth_style: str,
                      body: dict[str, Any] | None = None, timeout: float,
                      request_key: str | None = None) -> TransportResponse:
        try:
            return self.transport.request_json(
                method, url, token=token, auth_style=auth_style, body=body,
                timeout=timeout, request_key=request_key,
            )
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
        for model in snapshot.models:
            if "fiction_writing" in model.capabilities and not self._fiction_receipt_valid(
                snapshot.service_id, model
            ):
                model.capabilities.pop("fiction_writing", None)
                model.metadata.pop("quillframe_fiction_audition", None)
        snapshot.snapshot_fingerprint = ""
        snapshot.__post_init__()
        self._snapshots[snapshot.service_id] = snapshot
        return snapshot

    @staticmethod
    def _fiction_receipt_valid(service_id: str, model: DiscoveredModel) -> bool:
        if (
            not model.protocol
            or model.capability_state("text") != "verified"
            or model.capability_state("fiction_writing") != "verified"
        ):
            return False
        evidence = model.capabilities.get("fiction_writing")
        receipt = model.metadata.get("quillframe_fiction_audition")
        try:
            validated = validate_confirmation(receipt)
            selected_service, selected_model, selected_version = selected_identity(validated)
        except (KeyError, TypeError, ValueError):
            return False
        return (
            selected_service == service_id
            and selected_model == model.model_id
            and selected_version == model_version_fingerprint(service_id, model)
            and evidence is not None
            and evidence.evidence_ref == validated["confirmation_fingerprint"]
        )

    def _model_meets(self, service_id: str, model: DiscoveredModel, requirements: set[str]) -> bool:
        if not model.protocol or not all(model.capability_state(req) == "verified" for req in requirements):
            return False
        return "fiction_writing" not in requirements or self._fiction_receipt_valid(service_id, model)

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
            if self._model_meets(service_id, model, requirements):
                return model
        if allow_probe:
            for model in ordered:
                try:
                    self.probe_model(service_id, model.model_id, verify_tools="tool_calling" in requirements)
                except ModelRuntimeError:
                    continue
                if self._model_meets(service_id, model, requirements):
                    return model
        raise ModelRuntimeError("no_eligible_model", "No discovered model has verified evidence for the required capabilities", detail={"requirements": sorted(requirements), "models": [m.model_id for m in ordered]})

    def invoke(self, service_id: str, model_id: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], *,
               max_output_tokens: int = 2048, timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
               output_schema: dict[str, Any] | None = None, request_key: str | None = None,
               expected_model_version_fingerprint: str | None = None) -> ModelTurn:
        try:
            timeout_seconds = validate_request_timeout(timeout_seconds)
        except ValueError as exc:
            raise ModelRuntimeError("invalid_request_timeout", str(exc)) from exc
        snapshot = self.snapshot(service_id)
        model = next((m for m in snapshot.models if m.model_id == model_id), None)
        if not model:
            raise ModelRuntimeError("unknown_model", model_id)
        if (
            expected_model_version_fingerprint is not None
            and model_version_fingerprint(service_id, model) != expected_model_version_fingerprint
        ):
            raise ModelRuntimeError(
                "model_selection_changed",
                "selected model descriptor changed before dispatch",
            )
        if not model.protocol:
            if expected_model_version_fingerprint is not None:
                raise ModelRuntimeError(
                    "model_protocol_unresolved",
                    "a fingerprint-bound request cannot implicitly probe an unresolved protocol",
                )
            if output_schema is not None:
                raise ModelRuntimeError("model_protocol_unresolved", "native output_schema requires an already resolved protocol; no implicit probe")
            model = self.probe_model(service_id, model_id, verify_tools=bool(tools))
        selected_model_id = model.model_id
        selected_protocol = model.protocol
        codec = CODECS[selected_protocol]
        token = self._token(snapshot)
        layout = normalize_endpoint(snapshot.endpoint, self.endpoint_policy)
        try:
            if output_schema is not None and tools:
                raise ValueError("native output_schema is supported only for tool-free requests")
            body = codec.request_body(selected_model_id, history, tools, max_output_tokens, **({"output_schema": output_schema} if output_schema is not None else {}))
        except (ValueError, TypeError, RecursionError) as exc:
            raise ModelRuntimeError("model_output_schema_unsupported", str(exc)) from exc
        auth_style = model.auth_style or snapshot.auth_style or codec.auth_style
        response = self._request_json(
            "POST", layout.url_for(codec.surface), token=token, auth_style=auth_style,
            body=body, timeout=float(timeout_seconds), request_key=request_key,
        )
        if (response.status == 202 and isinstance(response.body, dict)
                and response.body.get("status") == "model_pending"
                and isinstance(response.body.get("request_id"), str)):
            raise ModelRuntimeError(
                "model_pending", "model worker is still running",
                detail={"request_id": response.body["request_id"], "automatic_retry": False},
            )
        if (isinstance(response.body, dict)
                and response.body.get("status") == "model_failed"
                and isinstance(response.body.get("request_id"), str)):
            raise ModelRuntimeError(
                "model_worker_failed", "durable model worker reached a terminal failure",
                detail={
                    "request_id": response.body["request_id"],
                    "failure_code": response.body.get("failure_code"),
                    "automatic_retry": False,
                },
            )
        if not (200 <= response.status < 300) or not isinstance(response.body, dict):
            raise ModelRuntimeError("model_request_failed", f"model request failed with HTTP {response.status}")
        try:
            return codec.normalize(selected_model_id, response.body)
        except (ValueError, TypeError, KeyError) as exc:
            raise ModelRuntimeError("model_response_invalid", str(exc)) from exc
