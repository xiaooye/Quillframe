"""Typed, resumable chapter workflow state machine for Quillframe 1.0."""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


CHAPTER_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
EVENT_SCHEMA = "quillframe_author_run_event_v1"
BATCH_SCHEMA = "quillframe_author_run_event_batch_v1"
SNAPSHOT_SCHEMA = "quillframe_novel_workflow_snapshot_v1"
WORKFLOW_STAGES = (
    "intent",
    "story_canon",
    "planning_horizon",
    "character_intent",
    "event_plan",
    "context_freeze",
    "raw_draft",
    "deterministic_checks",
    "critics",
    "local_repair",
    "candidate_freeze",
    "pre_independent_qualification",
    "independent_review",
    "human_review",
    "accept",
    "settlement",
    "publish",
)
_SECRET_KEYS = {"access_token", "api_key", "apikey", "password", "secret", "token"}


class WorkflowError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def validate_chapter_id(value: Any) -> str:
    """Validate identifier syntax; Core must also prove chapter ownership."""
    if not isinstance(value, str) or not CHAPTER_ID_PATTERN.fullmatch(value):
        raise WorkflowError("invalid_chapter_id", "chapter_id must be a bounded native identifier")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError("invalid_workflow_input", f"{field} must be non-empty")
    return value.strip()


def _require_fingerprint(value: Any, field: str) -> str:
    value = _require_text(value, field)
    if len(value) != 71 or not value.startswith("sha256:"):
        raise WorkflowError("invalid_workflow_input", f"{field} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise WorkflowError("invalid_workflow_input", f"{field} must be sha256:<64 hex>") from exc
    return value


def _assert_secret_free(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _SECRET_KEYS or "credential" in normalized:
                raise WorkflowError(
                    "secret_boundary_violation",
                    f"workflow event payload cannot contain {key}",
                )
            _assert_secret_free(child)
    elif isinstance(value, list):
        for child in value:
            _assert_secret_free(child)


class NovelWorkflowEngine:
    def __init__(
        self,
        *,
        project_id: str,
        run_id: str,
        chapter_id: str,
        author_profile: str,
        stage: str,
        status: str,
        events: list[dict[str, Any]],
        idempotency: dict[str, int] | None = None,
        candidate_fingerprint: str | None = None,
        active_reviews: list[dict[str, Any]] | None = None,
        action_receipts: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.project_id = _require_text(project_id, "project_id")
        self.run_id = _require_text(run_id, "run_id")
        validate_chapter_id(chapter_id)
        if author_profile not in {"guided", "expert"}:
            raise WorkflowError("invalid_workflow_input", "author_profile must be guided|expert")
        if stage not in WORKFLOW_STAGES:
            raise WorkflowError("invalid_workflow_input", "unknown workflow stage")
        if status not in {"running", "paused", "awaiting_user", "cancelled", "completed", "failed"}:
            raise WorkflowError("invalid_workflow_input", "unknown workflow status")
        self.chapter_id = chapter_id
        self.author_profile = author_profile
        self.stage = stage
        self.status = status
        self._events = deepcopy(events)
        self._idempotency = dict(idempotency or {})
        self.candidate_fingerprint = candidate_fingerprint
        self._active_reviews = deepcopy(active_reviews or [])
        self._action_receipts = deepcopy(action_receipts or {})
        self._validate_events()

    @classmethod
    def start(
        cls,
        *,
        project_id: str,
        run_id: str,
        chapter_id: str,
        author_profile: str = "guided",
    ) -> "NovelWorkflowEngine":
        validate_chapter_id(chapter_id)
        engine = cls(
            project_id=project_id,
            run_id=run_id,
            chapter_id=chapter_id,
            author_profile=author_profile,
            stage=WORKFLOW_STAGES[0],
            status="running",
            events=[],
        )
        engine._append("run_started", {"author_profile": author_profile})
        return engine

    @property
    def cursor(self) -> int:
        return self._events[-1]["cursor"] if self._events else -1

    @property
    def active_reviews(self) -> list[dict[str, Any]]:
        return deepcopy(self._active_reviews)

    def _validate_events(self) -> None:
        for expected, event in enumerate(self._events):
            if event.get("schema") != EVENT_SCHEMA or event.get("cursor") != expected:
                raise WorkflowError("workflow_snapshot_invalid", "event cursor or schema is invalid")
            if (
                event.get("project_id") != self.project_id
                or event.get("run_id") != self.run_id
                or event.get("chapter_id") != self.chapter_id
                or event.get("authority") is not False
            ):
                raise WorkflowError("workflow_snapshot_invalid", "event identity is invalid")
            _assert_secret_free(event.get("payload"))

    def _append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise WorkflowError("invalid_workflow_input", "event payload must be object")
        _assert_secret_free(payload)
        event = {
            "schema": EVENT_SCHEMA,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "chapter_id": self.chapter_id,
            "cursor": self.cursor + 1,
            "event_type": event_type,
            "stage": self.stage,
            "payload": deepcopy(payload),
            "created_at": _now(),
            "authority": False,
        }
        self._events.append(event)
        return deepcopy(event)

    def _require_active(self) -> None:
        if self.status not in {"running"}:
            raise WorkflowError("workflow_not_running", f"run status is {self.status}")

    def advance(self, *, stage: str, evidence: dict[str, Any]) -> dict[str, Any]:
        self._require_active()
        if stage != self.stage:
            raise WorkflowError(
                "invalid_stage_transition",
                f"expected stage {self.stage}, received {stage}",
            )
        if self.stage in {"human_review", "accept", "settlement"}:
            raise WorkflowError(
                "explicit_author_action_required",
                f"{self.stage} requires a dedicated explicit author action",
            )
        if self.stage == "independent_review":
            review = self._current_independent_review()
            if review is None:
                raise WorkflowError(
                    "independent_review_required",
                    "independent review must be bound to the current candidate",
                )
            if review["result"] == "reject":
                routed = self._append(
                    "repair_required",
                    {
                        "reason": "independent_review_reject",
                        "candidate_fingerprint": self.candidate_fingerprint,
                        "review_fingerprint": review["review_fingerprint"],
                    },
                )
                self.stage = "local_repair"
                self._append("stage_entered", {"routed_from": "independent_review"})
                return routed
        completed = self._append("stage_completed", evidence)
        index = WORKFLOW_STAGES.index(self.stage)
        if index == len(WORKFLOW_STAGES) - 1:
            self.status = "completed"
            self._append("completed", {"final_stage": self.stage})
            return completed
        self.stage = WORKFLOW_STAGES[index + 1]
        if self.stage == "human_review":
            self.status = "awaiting_user"
            self._append("human_action_required", {"action": "review_candidate"})
        else:
            self._append("stage_entered", {})
        return completed

    def pause(self, *, reason: str, idempotency_key: str) -> dict[str, Any]:
        key = _require_text(idempotency_key, "idempotency_key")
        if key in self._idempotency:
            return deepcopy(self._events[self._idempotency[key]])
        self._require_active()
        self.status = "paused"
        event = self._append("paused", {"reason": _require_text(reason, "reason")})
        self._idempotency[key] = event["cursor"]
        return event

    def resume(self, *, expected_cursor: int, idempotency_key: str) -> dict[str, Any]:
        key = _require_text(idempotency_key, "idempotency_key")
        if key in self._idempotency:
            return deepcopy(self._events[self._idempotency[key]])
        if self.status != "paused":
            raise WorkflowError("workflow_not_paused", f"run status is {self.status}")
        if expected_cursor != self.cursor:
            raise WorkflowError("cursor_conflict", "resume cursor does not match current event cursor")
        self.status = "running"
        event = self._append("resumed", {"resumed_from_cursor": expected_cursor})
        self._idempotency[key] = event["cursor"]
        return event

    def cancel(
        self,
        *,
        expected_cursor: int,
        idempotency_key: str,
        user_authorized: bool,
    ) -> dict[str, Any]:
        key = _require_text(idempotency_key, "idempotency_key")
        if key in self._idempotency:
            return deepcopy(self._events[self._idempotency[key]])
        if user_authorized is not True:
            raise WorkflowError("authorization_required", "cancel requires explicit user action")
        if self.status in {"cancelled", "completed", "failed"}:
            raise WorkflowError("workflow_terminal", f"run status is {self.status}")
        if expected_cursor != self.cursor:
            raise WorkflowError("cursor_conflict", "cancel cursor does not match current event cursor")
        self.status = "cancelled"
        event = self._append("cancelled", {"cancelled_from_cursor": expected_cursor})
        self._idempotency[key] = event["cursor"]
        return event

    def bind_candidate(self, candidate_fingerprint: str) -> dict[str, Any]:
        value = _require_fingerprint(candidate_fingerprint, "candidate_fingerprint")
        self.candidate_fingerprint = value
        self._active_reviews = []
        return self._append("stage_completed", {"candidate_fingerprint": value, "binding": "candidate"})

    def bind_review(
        self,
        *,
        candidate_fingerprint: str,
        review_fingerprint: str,
        independent: bool,
        result: str,
    ) -> dict[str, Any]:
        candidate = _require_fingerprint(candidate_fingerprint, "candidate_fingerprint")
        review = _require_fingerprint(review_fingerprint, "review_fingerprint")
        if candidate != self.candidate_fingerprint:
            raise WorkflowError("candidate_fingerprint_mismatch", "review is not bound to current candidate")
        if independent is not True:
            raise WorkflowError("independent_review_required", "production review must be independent")
        if self.stage != "independent_review" or self.status != "running":
            raise WorkflowError(
                "invalid_stage_transition",
                "independent review can only bind at independent_review",
            )
        if result not in {"pass", "reject"}:
            raise WorkflowError("invalid_workflow_input", "review result must be pass|reject")
        if self._current_independent_review() is not None:
            raise WorkflowError(
                "independent_attempt_already_bound",
                "current candidate already has an independent result",
            )
        binding = {
            "candidate_fingerprint": candidate,
            "review_fingerprint": review,
            "independent": True,
            "result": result,
        }
        self._active_reviews.append(binding)
        return self._append("stage_completed", {"review": binding})

    def _current_independent_review(self) -> dict[str, Any] | None:
        for review in reversed(self._active_reviews):
            if (
                review.get("candidate_fingerprint") == self.candidate_fingerprint
                and review.get("independent") is True
                and review.get("result") in {"pass", "reject"}
            ):
                return review
        return None

    def replace_candidate(self, candidate_fingerprint: str, *, reason: str) -> dict[str, Any]:
        value = _require_fingerprint(candidate_fingerprint, "candidate_fingerprint")
        _require_text(reason, "reason")
        if value == self.candidate_fingerprint:
            raise WorkflowError("candidate_unchanged", "replacement candidate fingerprint is unchanged")
        invalidated = len(self._active_reviews)
        previous = self.candidate_fingerprint
        self.candidate_fingerprint = value
        self._active_reviews = []
        self._append(
            "stage_completed",
            {
                "binding": "candidate_replacement",
                "previous_candidate_fingerprint": previous,
                "candidate_fingerprint": value,
                "invalidated_review_count": invalidated,
                "reason": reason,
            },
        )
        return {
            "schema": "quillframe_candidate_replacement_receipt_v1",
            "candidate_fingerprint": value,
            "invalidated_review_count": invalidated,
            "authority": False,
        }

    def accept(
        self,
        *,
        candidate_fingerprint: str,
        authorized_by: str,
        idempotency_key: str,
        user_authorized: bool,
    ) -> dict[str, Any]:
        key = _require_text(idempotency_key, "idempotency_key")
        if key in self._action_receipts:
            return deepcopy(self._action_receipts[key])
        if user_authorized is not True:
            raise WorkflowError("authorization_required", "accept requires explicit user action")
        if self.stage != "human_review" or self.status != "awaiting_user":
            raise WorkflowError("invalid_stage_transition", "accept requires human_review")
        candidate = _require_fingerprint(candidate_fingerprint, "candidate_fingerprint")
        if candidate != self.candidate_fingerprint:
            raise WorkflowError("candidate_fingerprint_mismatch", "acceptance is not bound to current candidate")
        review = self._current_independent_review()
        if review is None or review["result"] != "pass":
            raise WorkflowError(
                "independent_review_required",
                "accept requires a passing independent review bound to the current candidate",
            )
        authorized_by = _require_text(authorized_by, "authorized_by")
        acceptance_id = "accept_" + _fingerprint(
            {"run_id": self.run_id, "candidate": candidate, "key": key}
        )[7:31]
        self.stage = "accept"
        self.status = "awaiting_user"
        self._append(
            "stage_completed",
            {
                "action": "accept",
                "acceptance_id": acceptance_id,
                "candidate_fingerprint": candidate,
                "authorized_by": authorized_by,
            },
        )
        receipt = {
            "schema": "quillframe_workflow_author_action_receipt_v1",
            "action": "accept",
            "acceptance_id": acceptance_id,
            "candidate_fingerprint": candidate,
            "canon_mutated": False,
            "authority": False,
        }
        self._action_receipts[key] = receipt
        return deepcopy(receipt)

    def settle(
        self,
        *,
        acceptance_id: str,
        idempotency_key: str,
        user_authorized: bool,
    ) -> dict[str, Any]:
        key = _require_text(idempotency_key, "idempotency_key")
        if key in self._action_receipts:
            return deepcopy(self._action_receipts[key])
        if user_authorized is not True:
            raise WorkflowError("authorization_required", "settlement requires explicit user action")
        if self.stage != "accept" or self.status != "awaiting_user":
            raise WorkflowError("invalid_stage_transition", "settlement requires accepted workflow state")
        acceptance_id = _require_text(acceptance_id, "acceptance_id")
        settlement_id = "settle_" + _fingerprint(
            {"run_id": self.run_id, "acceptance_id": acceptance_id, "key": key}
        )[7:31]
        self.stage = "settlement"
        self.status = "awaiting_user"
        self._append(
            "stage_completed",
            {
                "action": "settlement",
                "acceptance_id": acceptance_id,
                "settlement_id": settlement_id,
            },
        )
        receipt = {
            "schema": "quillframe_workflow_author_action_receipt_v1",
            "action": "settlement",
            "acceptance_id": acceptance_id,
            "settlement_id": settlement_id,
            "canon_mutated": False,
            "authority": False,
        }
        self._action_receipts[key] = receipt
        return deepcopy(receipt)

    def publish(
        self,
        *,
        settlement_id: str,
        idempotency_key: str,
        user_authorized: bool,
    ) -> dict[str, Any]:
        key = _require_text(idempotency_key, "idempotency_key")
        if key in self._action_receipts:
            return deepcopy(self._action_receipts[key])
        if user_authorized is not True:
            raise WorkflowError("authorization_required", "publish requires explicit user action")
        if self.stage != "settlement" or self.status != "awaiting_user":
            raise WorkflowError("invalid_stage_transition", "publish requires settled workflow state")
        settlement_id = _require_text(settlement_id, "settlement_id")
        publication_id = "publish_" + _fingerprint(
            {"run_id": self.run_id, "settlement_id": settlement_id, "key": key}
        )[7:31]
        self.stage = "publish"
        self.status = "completed"
        self._append(
            "completed",
            {
                "action": "publish",
                "settlement_id": settlement_id,
                "publication_id": publication_id,
            },
        )
        receipt = {
            "schema": "quillframe_workflow_author_action_receipt_v1",
            "action": "publish",
            "settlement_id": settlement_id,
            "publication_id": publication_id,
            "authority": False,
        }
        self._action_receipts[key] = receipt
        return deepcopy(receipt)

    def events_after(self, cursor: int) -> dict[str, Any]:
        if not isinstance(cursor, int) or cursor < -1:
            raise WorkflowError("invalid_cursor", "cursor must be integer >= -1")
        return {
            "schema": BATCH_SCHEMA,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "events": [deepcopy(event) for event in self._events if event["cursor"] > cursor],
            "next_cursor": self.cursor,
            "authority": False,
        }

    def snapshot(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": SNAPSHOT_SCHEMA,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "chapter_id": self.chapter_id,
            "author_profile": self.author_profile,
            "stage": self.stage,
            "status": self.status,
            "events": deepcopy(self._events),
            "idempotency": dict(sorted(self._idempotency.items())),
            "candidate_fingerprint": self.candidate_fingerprint,
            "active_reviews": deepcopy(self._active_reviews),
            "action_receipts": deepcopy(self._action_receipts),
            "authority": False,
        }
        payload["snapshot_fingerprint"] = _fingerprint(payload)
        return payload

    @classmethod
    def restore(cls, snapshot: dict[str, Any]) -> "NovelWorkflowEngine":
        if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
            raise WorkflowError("workflow_snapshot_invalid", f"schema must be {SNAPSHOT_SCHEMA}")
        supplied = snapshot.get("snapshot_fingerprint")
        unsigned = {key: deepcopy(value) for key, value in snapshot.items() if key != "snapshot_fingerprint"}
        if supplied != _fingerprint(unsigned):
            raise WorkflowError("workflow_snapshot_invalid", "snapshot fingerprint mismatch")
        if snapshot.get("authority") is not False:
            raise WorkflowError("workflow_snapshot_invalid", "snapshot must be non-authoritative")
        return cls(
            project_id=snapshot.get("project_id"),
            run_id=snapshot.get("run_id"),
            chapter_id=snapshot.get("chapter_id"),
            author_profile=snapshot.get("author_profile"),
            stage=snapshot.get("stage"),
            status=snapshot.get("status"),
            events=snapshot.get("events") or [],
            idempotency=snapshot.get("idempotency") or {},
            candidate_fingerprint=snapshot.get("candidate_fingerprint"),
            active_reviews=snapshot.get("active_reviews") or [],
            action_receipts=snapshot.get("action_receipts") or {},
        )
