"""Typed CH001 generation contracts used by the Quillframe 1.0 workflow."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .workflow import CHAPTER_SCOPE, WorkflowError


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError("invalid_generation_contract", f"{field} must be non-empty")
    return value.strip()


def _chapter(value: str) -> str:
    if value != CHAPTER_SCOPE:
        raise WorkflowError(
            "chapter_scope_violation",
            f"Quillframe 1.0 acceptance is limited to {CHAPTER_SCOPE}",
        )
    return value


def _fingerprint_value(value: Any, field: str) -> str:
    value = _text(value, field)
    if len(value) != 71 or not value.startswith("sha256:"):
        raise WorkflowError("invalid_generation_contract", f"{field} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise WorkflowError("invalid_generation_contract", f"{field} must be sha256:<64 hex>") from exc
    return value


def _items(values: tuple[str, ...], field: str, *, nonempty: bool = False) -> tuple[str, ...]:
    cleaned = tuple(_text(value, field) for value in values)
    if nonempty and not cleaned:
        raise WorkflowError("invalid_generation_contract", f"{field} must not be empty")
    if len(set(cleaned)) != len(cleaned):
        raise WorkflowError("invalid_generation_contract", f"{field} must be unique")
    return cleaned


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SceneIntent:
    project_id: str
    chapter_id: str
    scene_id: str
    purpose: str
    desired_change: str
    constraints: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "chapter_id", _chapter(self.chapter_id))
        object.__setattr__(self, "scene_id", _text(self.scene_id, "scene_id"))
        object.__setattr__(self, "purpose", _text(self.purpose, "purpose"))
        object.__setattr__(self, "desired_change", _text(self.desired_change, "desired_change"))
        object.__setattr__(self, "constraints", _items(tuple(self.constraints), "constraints"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_scene_intent_v1",
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "scene_id": self.scene_id,
            "purpose": self.purpose,
            "desired_change": self.desired_change,
            "constraints": list(self.constraints),
        }


@dataclass(frozen=True)
class CharacterIntent:
    project_id: str
    chapter_id: str
    scene_id: str
    character_id: str
    private_goal: str
    perceived_state: Mapping[str, Any]
    action_candidates: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "chapter_id", _chapter(self.chapter_id))
        object.__setattr__(self, "scene_id", _text(self.scene_id, "scene_id"))
        object.__setattr__(self, "character_id", _text(self.character_id, "character_id"))
        object.__setattr__(self, "private_goal", _text(self.private_goal, "private_goal"))
        if not isinstance(self.perceived_state, Mapping):
            raise WorkflowError("invalid_generation_contract", "perceived_state must be object")
        object.__setattr__(
            self,
            "action_candidates",
            _items(tuple(self.action_candidates), "action_candidates", nonempty=True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_character_intent_v1",
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "scene_id": self.scene_id,
            "character_id": self.character_id,
            "private_goal": self.private_goal,
            "perceived_state": dict(self.perceived_state),
            "action_candidates": list(self.action_candidates),
        }


@dataclass(frozen=True)
class TransitionConstraints:
    project_id: str
    chapter_id: str
    from_state_fingerprint: str
    allowed_changes: tuple[str, ...]
    forbidden_changes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "chapter_id", _chapter(self.chapter_id))
        object.__setattr__(
            self,
            "from_state_fingerprint",
            _fingerprint_value(self.from_state_fingerprint, "from_state_fingerprint"),
        )
        allowed = _items(tuple(self.allowed_changes), "allowed_changes")
        forbidden = _items(tuple(self.forbidden_changes), "forbidden_changes")
        if set(allowed).intersection(forbidden):
            raise WorkflowError("invalid_generation_contract", "allowed and forbidden changes overlap")
        object.__setattr__(self, "allowed_changes", allowed)
        object.__setattr__(self, "forbidden_changes", forbidden)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_transition_constraints_v1",
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "from_state_fingerprint": self.from_state_fingerprint,
            "allowed_changes": list(self.allowed_changes),
            "forbidden_changes": list(self.forbidden_changes),
        }


@dataclass(frozen=True)
class RiskSignal:
    code: str
    severity: str
    owner: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "code"))
        if self.severity not in {"info", "warning", "blocking"}:
            raise WorkflowError("invalid_generation_contract", "severity is invalid")
        if self.owner not in {"story", "plan", "character", "context", "surface", "continuity", "runtime"}:
            raise WorkflowError("invalid_generation_contract", "owner is invalid")
        object.__setattr__(self, "evidence_refs", _items(tuple(self.evidence_refs), "evidence_refs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "owner": self.owner,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class RiskSignals:
    project_id: str
    chapter_id: str
    candidate_fingerprint: str
    signals: tuple[RiskSignal, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "chapter_id", _chapter(self.chapter_id))
        object.__setattr__(
            self,
            "candidate_fingerprint",
            _fingerprint_value(self.candidate_fingerprint, "candidate_fingerprint"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_risk_signals_v1",
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "candidate_fingerprint": self.candidate_fingerprint,
            "signals": [signal.to_dict() for signal in self.signals],
        }


@dataclass(frozen=True)
class RepairPlan:
    project_id: str
    chapter_id: str
    candidate_fingerprint: str
    mode: str
    owner: str
    actions: tuple[str, ...]
    preserve_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "chapter_id", _chapter(self.chapter_id))
        object.__setattr__(
            self,
            "candidate_fingerprint",
            _fingerprint_value(self.candidate_fingerprint, "candidate_fingerprint"),
        )
        if self.mode not in {"local_rewrite", "scene_regenerate", "upstream_replan"}:
            raise WorkflowError("invalid_generation_contract", "repair mode is invalid")
        if self.owner not in {"story", "plan", "character", "context", "surface", "continuity"}:
            raise WorkflowError("invalid_generation_contract", "repair owner is invalid")
        object.__setattr__(self, "actions", _items(tuple(self.actions), "actions", nonempty=True))
        object.__setattr__(self, "preserve_refs", _items(tuple(self.preserve_refs), "preserve_refs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_repair_plan_v1",
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "candidate_fingerprint": self.candidate_fingerprint,
            "mode": self.mode,
            "owner": self.owner,
            "actions": list(self.actions),
            "preserve_refs": list(self.preserve_refs),
        }


@dataclass(frozen=True)
class GenerationPacket:
    project_id: str
    run_id: str
    chapter_id: str
    context_freeze_fingerprint: str
    scene_intents: tuple[SceneIntent, ...]
    character_intents: tuple[CharacterIntent, ...]
    transition_constraints: TransitionConstraints
    task_profile_id: str
    packet_fingerprint: str

    @classmethod
    def build(
        cls,
        *,
        project_id: str,
        run_id: str,
        chapter_id: str,
        context_freeze_fingerprint: str,
        scene_intents: tuple[SceneIntent, ...],
        character_intents: tuple[CharacterIntent, ...],
        transition_constraints: TransitionConstraints,
        task_profile_id: str,
    ) -> "GenerationPacket":
        project_id = _text(project_id, "project_id")
        run_id = _text(run_id, "run_id")
        chapter_id = _chapter(chapter_id)
        context_freeze_fingerprint = _fingerprint_value(
            context_freeze_fingerprint,
            "context_freeze_fingerprint",
        )
        task_profile_id = _text(task_profile_id, "task_profile_id")
        if not scene_intents:
            raise WorkflowError("invalid_generation_contract", "scene_intents must not be empty")
        if not character_intents:
            raise WorkflowError("invalid_generation_contract", "character_intents must not be empty")
        members = (*scene_intents, *character_intents, transition_constraints)
        if any(member.project_id != project_id or member.chapter_id != chapter_id for member in members):
            raise WorkflowError("generation_packet_identity_mismatch", "packet members must share project/chapter")
        unsigned = {
            "schema": "quillframe_generation_packet_v1",
            "project_id": project_id,
            "run_id": run_id,
            "chapter_id": chapter_id,
            "context_freeze_fingerprint": context_freeze_fingerprint,
            "scene_intents": [item.to_dict() for item in scene_intents],
            "character_intents": [item.to_dict() for item in character_intents],
            "transition_constraints": transition_constraints.to_dict(),
            "task_profile_id": task_profile_id,
        }
        return cls(
            project_id=project_id,
            run_id=run_id,
            chapter_id=chapter_id,
            context_freeze_fingerprint=context_freeze_fingerprint,
            scene_intents=scene_intents,
            character_intents=character_intents,
            transition_constraints=transition_constraints,
            task_profile_id=task_profile_id,
            packet_fingerprint=_fingerprint(unsigned),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_generation_packet_v1",
            "project_id": self.project_id,
            "run_id": self.run_id,
            "chapter_id": self.chapter_id,
            "context_freeze_fingerprint": self.context_freeze_fingerprint,
            "scene_intents": [item.to_dict() for item in self.scene_intents],
            "character_intents": [item.to_dict() for item in self.character_intents],
            "transition_constraints": self.transition_constraints.to_dict(),
            "task_profile_id": self.task_profile_id,
            "packet_fingerprint": self.packet_fingerprint,
        }
