from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from harness.control_plane.control_plane import ControlPlane
from harness.session_runtime.session_runtime import checkpoint as session_checkpoint
from model_runtime.contracts import ToolCall, fingerprint

from .contracts import AgentJob
from .tools import ToolSpec


class AgentExecutionHooks(Protocol):
    def before_side_effect(self, job: AgentJob, call: ToolCall, spec: ToolSpec, idempotency_key: str | None) -> str: ...
    def after_side_effect(self, job: AgentJob, call: ToolCall, checkpoint_ref: str, receipt: dict) -> None: ...


@dataclass
class ControlPlaneExecutionHooks:
    """Bind Agent side effects to the existing Session Runtime + Control Plane.

    The pre-effect checkpoint is stored with CAS before the handler is called.
    The post-effect checkpoint and consume-once receipt hash are recorded after
    a successful handler result. This records exact operational evidence but
    does not grant Project/Canon/Framework authority.
    """

    control_plane: ControlPlane

    def __post_init__(self) -> None:
        self.control_plane.init()

    def _session(self, job: AgentJob) -> tuple[dict, int]:
        current = self.control_plane.get_session(job.session_id)
        if current is None:
            raise ValueError(f"agent session is not persisted: {job.session_id}")
        session = current["session"]
        if not any(run.get("run_id") == job.run_id and run.get("status") == "running" for run in session.get("runs", []) if isinstance(run, dict)):
            raise ValueError(f"agent run is not active in session: {job.run_id}")
        return session, int(current["version"])

    def before_side_effect(self, job: AgentJob, call: ToolCall, spec: ToolSpec, idempotency_key: str | None) -> str:
        if not spec.side_effect:
            raise ValueError("before_side_effect called for read-only tool")
        if spec.idempotency_required and not idempotency_key:
            raise ValueError("side-effect tool requires an idempotency key")
        session, version = self._session(job)
        args_fp = fingerprint(call.arguments)
        updated = session_checkpoint(
            session,
            job.run_id,
            f"agent.tool.before:{call.name}:{call.call_id}",
            [job.input_fingerprint, args_fp],
            pending_gate=f"agent_tool:{call.call_id}",
        )
        result = self.control_plane.put_session(updated, expected_version=version)
        checkpoint_ref = updated["checkpoints"][-1]["checkpoint_id"]
        if not result.get("payload_hash"):
            raise ValueError("failed to persist pre-effect checkpoint")
        return checkpoint_ref

    def after_side_effect(self, job: AgentJob, call: ToolCall, checkpoint_ref: str, receipt: dict) -> None:
        if not checkpoint_ref:
            raise ValueError("checkpoint_ref required")
        output_fp = str(receipt.get("output_fingerprint") or "")
        if not output_fp:
            raise ValueError("tool receipt missing output_fingerprint")
        source_id = f"{job.run_id}:{call.call_id}"
        self.control_plane.consume_once("agent_tool", source_id, "agent_runtime", output_fp)
        session, version = self._session(job)
        updated = session_checkpoint(
            session,
            job.run_id,
            f"agent.tool.completed:{call.name}:{call.call_id}",
            [job.input_fingerprint, str(receipt.get("arguments_fingerprint") or ""), output_fp],
            pending_gate=None,
        )
        self.control_plane.put_session(updated, expected_version=version)
