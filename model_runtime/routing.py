"""Deterministic, secret-free model route planning for Quillframe 1.0."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable


PROFILE_SCHEMA = "quillframe_model_task_profile_v1"
RECEIPT_SCHEMA = "quillframe_model_route_receipt_v1"
_QUALITY = {"standard": 1, "high": 2, "highest": 3}
_ROLES = {
    "writer",
    "reader_critic",
    "continuity_critic",
    "style_critic",
    "repair_editor",
    "independent_reviewer",
    "researcher",
}


class RouteError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RouteError("invalid_model_task_profile", f"{field} must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class ModelTaskProfile:
    profile_id: str
    role: str
    required_capabilities: tuple[str, ...]
    context_budget_tokens: int
    max_cost_micros: int
    quality_floor: str
    independence: str
    privacy: str
    latency_preference: str

    def __post_init__(self) -> None:
        _nonempty(self.profile_id, "profile_id")
        if self.role not in _ROLES:
            raise RouteError("invalid_model_task_profile", "role is not supported")
        if not self.required_capabilities or any(not str(item).strip() for item in self.required_capabilities):
            raise RouteError("invalid_model_task_profile", "required_capabilities must be non-empty")
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise RouteError("invalid_model_task_profile", "required_capabilities must be unique")
        if not isinstance(self.context_budget_tokens, int) or self.context_budget_tokens <= 0:
            raise RouteError("invalid_model_task_profile", "context_budget_tokens must be positive")
        if not isinstance(self.max_cost_micros, int) or self.max_cost_micros < 0:
            raise RouteError("invalid_model_task_profile", "max_cost_micros must be non-negative")
        if self.quality_floor not in _QUALITY:
            raise RouteError("invalid_model_task_profile", "quality_floor is invalid")
        if self.independence not in {"none", "required"}:
            raise RouteError("invalid_model_task_profile", "independence is invalid")
        if self.privacy not in {"project", "public"}:
            raise RouteError("invalid_model_task_profile", "privacy is invalid")
        if self.latency_preference not in {"interactive", "balanced", "quality_first"}:
            raise RouteError("invalid_model_task_profile", "latency_preference is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PROFILE_SCHEMA,
            "profile_id": self.profile_id,
            "role": self.role,
            "required_capabilities": sorted(self.required_capabilities),
            "context_budget_tokens": self.context_budget_tokens,
            "max_cost_micros": self.max_cost_micros,
            "quality_floor": self.quality_floor,
            "independence": self.independence,
            "privacy": self.privacy,
            "latency_preference": self.latency_preference,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelTaskProfile":
        if not isinstance(value, dict) or value.get("schema") != PROFILE_SCHEMA:
            raise RouteError("invalid_model_task_profile", f"schema must be {PROFILE_SCHEMA}")
        return cls(
            profile_id=value.get("profile_id"),
            role=value.get("role"),
            required_capabilities=tuple(value.get("required_capabilities") or ()),
            context_budget_tokens=value.get("context_budget_tokens"),
            max_cost_micros=value.get("max_cost_micros"),
            quality_floor=value.get("quality_floor"),
            independence=value.get("independence"),
            privacy=value.get("privacy"),
            latency_preference=value.get("latency_preference"),
        )


@dataclass(frozen=True)
class ModelRoute:
    route_id: str
    capabilities: frozenset[str]
    context_limit_tokens: int
    estimated_cost_micros: int
    quality_rank: int
    privacy_levels: frozenset[str]
    invocation_id: str
    independent_eligible: bool

    def __post_init__(self) -> None:
        _nonempty(self.route_id, "route_id")
        _nonempty(self.invocation_id, "invocation_id")
        if self.context_limit_tokens <= 0 or self.estimated_cost_micros < 0:
            raise RouteError("invalid_model_route", "route budgets are invalid")
        if self.quality_rank not in {1, 2, 3}:
            raise RouteError("invalid_model_route", "quality_rank must be 1..3")
        if not self.privacy_levels <= {"project", "public"}:
            raise RouteError("invalid_model_route", "privacy_levels are invalid")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelRoute":
        if not isinstance(value, dict):
            raise RouteError("invalid_model_route", "route must be object")
        forbidden = {"access_token", "api_key", "secret", "password", "token"}
        if forbidden.intersection(str(key).lower().replace("-", "_") for key in value):
            raise RouteError("secret_boundary_violation", "route descriptor cannot contain credentials")
        return cls(
            route_id=value.get("route_id"),
            capabilities=frozenset(value.get("capabilities") or ()),
            context_limit_tokens=value.get("context_limit_tokens"),
            estimated_cost_micros=value.get("estimated_cost_micros"),
            quality_rank=value.get("quality_rank"),
            privacy_levels=frozenset(value.get("privacy_levels") or ()),
            invocation_id=value.get("invocation_id"),
            independent_eligible=value.get("independent_eligible") is True,
        )


def _eligible(
    profile: ModelTaskProfile,
    route: ModelRoute,
    manager_invocation_id: str,
) -> bool:
    if not set(profile.required_capabilities) <= route.capabilities:
        return False
    if route.context_limit_tokens < profile.context_budget_tokens:
        return False
    if route.estimated_cost_micros > profile.max_cost_micros:
        return False
    if route.quality_rank < _QUALITY[profile.quality_floor]:
        return False
    if profile.privacy not in route.privacy_levels:
        return False
    if profile.independence == "required" and (
        not route.independent_eligible or route.invocation_id == manager_invocation_id
    ):
        return False
    return True


def preview_route(
    *,
    project_id: str,
    profile: ModelTaskProfile,
    routes: Iterable[ModelRoute],
    manager_invocation_id: str,
) -> dict[str, Any]:
    project_id = _nonempty(project_id, "project_id")
    manager_invocation_id = _nonempty(manager_invocation_id, "manager_invocation_id")
    eligible = [
        route
        for route in routes
        if _eligible(profile, route, manager_invocation_id)
    ]
    if not eligible:
        raise RouteError(
            "no_eligible_model_route",
            "no route satisfies capability, budget, quality, privacy, and independence constraints",
        )
    if profile.latency_preference == "interactive":
        eligible.sort(key=lambda route: (route.estimated_cost_micros, -route.quality_rank, route.route_id))
    else:
        eligible.sort(key=lambda route: (-route.quality_rank, route.estimated_cost_micros, route.route_id))
    selected = eligible[0]
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "project_id": project_id,
        "profile_id": profile.profile_id,
        "selected_route_id": selected.route_id,
        "selection_reasons": [
            "required_capabilities_satisfied",
            "hard_budget_satisfied",
            "quality_floor_satisfied",
            "privacy_boundary_satisfied",
            "independence_boundary_satisfied",
        ],
        "budget": {
            "context_tokens": profile.context_budget_tokens,
            "max_cost_micros": profile.max_cost_micros,
        },
        "fallback": {"used": False, "from_route_id": None, "reason_code": None},
        "authority": False,
    }
    receipt["route_fingerprint"] = _fingerprint(receipt)
    return receipt


def explicit_fallback(
    *,
    prior_receipt: dict[str, Any],
    failed_route_id: str,
    reason_code: str,
    profile: ModelTaskProfile,
    routes: Iterable[ModelRoute],
    manager_invocation_id: str,
) -> dict[str, Any]:
    if (
        not isinstance(prior_receipt, dict)
        or prior_receipt.get("schema") != RECEIPT_SCHEMA
        or prior_receipt.get("profile_id") != profile.profile_id
    ):
        raise RouteError("invalid_fallback_receipt", "prior route receipt is not bound to this profile")
    failed_route_id = _nonempty(failed_route_id, "failed_route_id")
    reason_code = _nonempty(reason_code, "reason_code")
    if prior_receipt.get("selected_route_id") != failed_route_id:
        raise RouteError("invalid_fallback_receipt", "failed route does not match prior selected route")
    candidates = [route for route in routes if route.route_id != failed_route_id]
    receipt = preview_route(
        project_id=prior_receipt.get("project_id"),
        profile=profile,
        routes=candidates,
        manager_invocation_id=manager_invocation_id,
    )
    receipt["fallback"] = {
        "used": True,
        "from_route_id": failed_route_id,
        "reason_code": reason_code,
    }
    receipt["route_fingerprint"] = _fingerprint(
        {key: value for key, value in receipt.items() if key != "route_fingerprint"}
    )
    return receipt
