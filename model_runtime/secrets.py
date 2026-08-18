from __future__ import annotations

import os
import uuid
from typing import Protocol


class SecretStore(Protocol):
    def put(self, secret: str) -> str: ...
    def resolve(self, secret_ref: str) -> str: ...
    def delete(self, secret_ref: str) -> None: ...
    def present(self, secret_ref: str | None) -> bool: ...


class MemorySecretStore:
    """Test/embedding secret store. It never serializes secret values."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def put(self, secret: str) -> str:
        ref = "memory:qf-secret-" + uuid.uuid4().hex
        self._values[ref] = secret
        return ref

    def resolve(self, secret_ref: str) -> str:
        try:
            return self._values[secret_ref]
        except KeyError as exc:
            raise KeyError("secret reference is unavailable") from exc

    def delete(self, secret_ref: str) -> None:
        self._values.pop(secret_ref, None)

    def present(self, secret_ref: str | None) -> bool:
        return bool(secret_ref and secret_ref in self._values)


class EnvSecretStore:
    """Read-only resolver for env:NAME references."""

    def put(self, secret: str) -> str:
        raise RuntimeError("EnvSecretStore cannot persist new secrets")

    def resolve(self, secret_ref: str) -> str:
        if not secret_ref.startswith("env:"):
            raise ValueError("EnvSecretStore only resolves env: references")
        name = secret_ref.split(":", 1)[1]
        value = os.getenv(name)
        if value is None:
            raise KeyError("environment secret is unavailable")
        return value

    def delete(self, secret_ref: str) -> None:
        raise RuntimeError("EnvSecretStore cannot delete environment secrets")

    def present(self, secret_ref: str | None) -> bool:
        return bool(secret_ref and secret_ref.startswith("env:") and os.getenv(secret_ref.split(":", 1)[1]) is not None)
