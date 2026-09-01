"""Fail-closed orchestrator for evaluating an existing native production run."""
from __future__ import annotations

import hashlib
from typing import Any

from core_operations import CoreOperations
from production_runtime import ProductionRunExecutor


class NativeStyleRunnerError(RuntimeError):
    """A native run cannot safely expose an evaluation candidate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class NativeStyleRunner:
    """Execute or resume a Core-created run and release only its visible candidate."""

    _PROSE_KEYS = {"candidate_text", "content", "manuscript", "prose", "text", "final_text", "draft_text"}
    _STATUS_KEYS = {
        "schema", "project_id", "run_id", "task_mode", "target_ref", "status",
        "result_fingerprint", "events", "candidate", "authority", "execution_journal",
        "repair_source", "awaiting", "pending", "pending_mechanism",
        "failed_mechanism", "candidate_visible", "raw_draft_visible",
        "automatic_model_retry", "new_context_fingerprint_required", "validation",
        "context_bundle_fingerprint", "freeze_fingerprint", "stage_receipts",
        "qualification", "production_readiness", "production_release",
        "same_request_poll_only",
    }

    def __init__(self, executor: ProductionRunExecutor, operations: CoreOperations) -> None:
        self._executor = executor
        self._operations = operations

    @classmethod
    def _guard_runtime_result(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise NativeStyleRunnerError("native_runtime_result_invalid", "native runtime must return a typed status object")

        unexpected = set(value) - cls._STATUS_KEYS
        if unexpected:
            code = (
                "native_runtime_prose_forbidden"
                if unexpected.intersection(cls._PROSE_KEYS)
                else "native_runtime_result_invalid"
            )
            raise NativeStyleRunnerError(
                code,
                "native runtime returned fields outside the closed text-free status projection",
            )
        status = value.get("status")
        if not isinstance(status, str) or not status:
            raise NativeStyleRunnerError(
                "native_runtime_result_invalid", "native runtime status is missing",
            )
        candidate = value.get("candidate")
        if candidate is not None and not isinstance(candidate, dict):
            raise NativeStyleRunnerError(
                "native_runtime_prose_forbidden",
                "runtime candidate payload must remain metadata-only",
            )
        safe_candidate = None
        if isinstance(candidate, dict):
            candidate_id = candidate.get("candidate_id")
            candidate_fingerprint = (
                candidate.get("candidate_fingerprint")
                or candidate.get("content_fingerprint")
            )
            if not isinstance(candidate_id, str) or not isinstance(candidate_fingerprint, str):
                raise NativeStyleRunnerError(
                    "native_runtime_result_invalid",
                    "runtime candidate metadata is incomplete",
                )
            safe_candidate = {
                "candidate_id": candidate_id,
                "candidate_fingerprint": candidate_fingerprint,
                "status": candidate.get("status"),
            }
        journal = value.get("execution_journal")
        safe_journal = None
        if isinstance(journal, dict):
            safe_journal = {key: journal.get(key) for key in (
                "active_executor", "dispatched_call_count", "confirmed_call_count",
                "unconfirmed_call_ids", "hard_unconfirmed_call_ids", "pending_call_ids",
                "safe_to_poll_pending", "request_fingerprint",
            ) if key in journal}
        return {
            "schema": "quillframe_native_style_runner_status_v1",
            "project_id": value.get("project_id"), "run_id": value.get("run_id"),
            "status": status, "awaiting": value.get("awaiting"),
            "pending": value.get("pending"),
            "pending_mechanism": value.get("pending_mechanism"),
            "failed_mechanism": value.get("failed_mechanism"),
            "same_request_poll_only": value.get("same_request_poll_only", False),
            "candidate_visible": value.get("candidate_visible", False),
            "raw_draft_visible": False, "candidate": safe_candidate,
            "execution_journal": safe_journal, "authority": False,
        }

    def _status(self, project_id: str, run_id: str) -> dict[str, Any]:
        return self._guard_runtime_result(self._executor.status(project_id, run_id))

    def status(self, project_id: str, run_id: str) -> dict[str, Any]:
        """Return the guarded native status without manuscript text."""
        return self._status(project_id, run_id)

    def _completed_candidate(self, project_id: str, run_id: str) -> dict[str, Any]:
        state = self._status(project_id, run_id)
        if state.get("status") != "completed":
            raise NativeStyleRunnerError("native_run_not_completed", "candidate remains hidden until the native run is completed")
        candidate = state.get("candidate")
        candidate_id = candidate.get("candidate_id") if isinstance(candidate, dict) else None
        if not isinstance(candidate_id, str) or not candidate_id:
            raise NativeStyleRunnerError("native_candidate_missing", "completed native run has no released candidate identity")
        visible = self._operations.candidate_visible_get(project_id, candidate_id=candidate_id)
        content = visible.get("content") if isinstance(visible, dict) else None
        expected_fingerprint = candidate.get("candidate_fingerprint")
        actual_fingerprint = (
            "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
            if isinstance(content, str) else None
        )
        if (
            not isinstance(visible, dict)
            or not isinstance(content, str)
            or visible.get("candidate_id") != candidate_id
            or not isinstance(expected_fingerprint, str)
            or visible.get("candidate_fingerprint") != expected_fingerprint
            or actual_fingerprint != expected_fingerprint
            or visible.get("content_access") != "production_release_only"
            or visible.get("accepted") is not False
            or visible.get("settled") is not False
        ):
            raise NativeStyleRunnerError(
                "native_candidate_not_visible",
                "Core did not return the exact released, unaccepted candidate",
            )
        return {
            "schema": "quillframe_native_style_runner_result_v1",
            "project_id": project_id,
            "run_id": run_id,
            "status": "completed",
            "candidate": visible,
            "authority": False,
        }

    def visible_candidate(self, project_id: str, run_id: str) -> dict[str, Any]:
        """Read prose only after the native release boundary is complete."""
        return self._completed_candidate(project_id, run_id)

    def execute(self, project_id: str, run_id: str, **execution: Any) -> dict[str, Any]:
        """Execute the complete graph for an already registered native run."""
        self._status(project_id, run_id)
        raw = self._executor.execute(project_id, run_id, **execution)
        # The native handoff may contain the frozen reviewer packet and prose.
        # Never return or persist it through the evaluation runner; re-project
        # the durable text-free status instead.
        result = (
            self._status(project_id, run_id)
            if isinstance(raw, dict) and raw.get("status") == "awaiting_external"
            else self._guard_runtime_result(raw)
        )
        if result.get("status") == "completed":
            return self._completed_candidate(project_id, run_id)
        return result

    def resume(self, project_id: str, run_id: str) -> dict[str, Any]:
        """Resume the immutable graph for an already registered native run."""
        state = self._status(project_id, run_id)
        if state.get("status") == "completed":
            return self._completed_candidate(project_id, run_id)
        raw = self._executor.resume_execution(project_id, run_id)
        result = (
            self._status(project_id, run_id)
            if isinstance(raw, dict) and raw.get("status") == "awaiting_external"
            else self._guard_runtime_result(raw)
        )
        if result.get("status") == "completed":
            return self._completed_candidate(project_id, run_id)
        return result
