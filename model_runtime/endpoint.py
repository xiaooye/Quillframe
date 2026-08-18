from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

KNOWN_SUFFIXES = ("/chat/completions", "/responses", "/messages", "/models")


@dataclass(frozen=True)
class EndpointPolicy:
    allow_loopback: bool = True
    allow_private_network: bool = False
    require_https_for_remote: bool = True


@dataclass(frozen=True)
class EndpointLayout:
    configured_endpoint: str
    base_url: str
    exact_surface: str | None

    def url_for(self, surface: str) -> str:
        suffixes = {
            "models": "/models",
            "openai_chat_completions": "/chat/completions",
            "openai_responses": "/responses",
            "anthropic_messages": "/messages",
        }
        if surface not in suffixes:
            raise ValueError(f"unsupported API surface: {surface}")
        return self.base_url.rstrip("/") + suffixes[surface]


def _classify_literal_host(host: str) -> str:
    if host.lower() == "localhost":
        return "loopback"
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return "hostname"
    if ip.is_loopback:
        return "loopback"
    if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
        return "private"
    return "public"


def normalize_endpoint(endpoint: str, policy: EndpointPolicy | None = None) -> EndpointLayout:
    policy = policy or EndpointPolicy()
    raw = endpoint.strip()
    if not raw:
        raise ValueError("API endpoint is required")
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"}:
        raise ValueError("API endpoint must use http or https")
    if not parts.hostname:
        raise ValueError("API endpoint must include a hostname")
    if parts.username or parts.password:
        raise ValueError("credentials must not be embedded in the API endpoint URL")
    if parts.query or parts.fragment:
        raise ValueError("API endpoint must not contain query or fragment components")

    host_class = _classify_literal_host(parts.hostname)
    if host_class == "loopback" and not policy.allow_loopback:
        raise ValueError("loopback endpoint is not allowed by network policy")
    if host_class == "private" and not policy.allow_private_network:
        raise ValueError("private/link-local endpoint is not allowed by network policy")
    if host_class in {"public", "hostname"} and policy.require_https_for_remote and parts.scheme != "https":
        raise ValueError("remote API endpoint must use https")

    path = (parts.path or "").rstrip("/")
    exact_surface = None
    base_path = path
    for suffix, surface in (
        ("/chat/completions", "openai_chat_completions"),
        ("/responses", "openai_responses"),
        ("/messages", "anthropic_messages"),
        ("/models", "models"),
    ):
        if path.endswith(suffix):
            base_path = path[: -len(suffix)]
            exact_surface = surface
            break
    if not base_path:
        base_path = ""
    normalized = urlunsplit((parts.scheme, parts.netloc, path or "", "", ""))
    base = urlunsplit((parts.scheme, parts.netloc, base_path, "", ""))
    return EndpointLayout(configured_endpoint=normalized.rstrip("/"), base_url=base.rstrip("/"), exact_surface=exact_surface)
