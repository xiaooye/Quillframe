from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .contracts import ProductionRunError
from .runtime import ProductionRunExecutor as _ProductionRunExecutor
from .workflow import CHAPTER_SCOPE, WorkflowError
from .workflow_service import NovelWorkflowService

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_ROOT = ROOT / "harness" / "semantic_workers"
if str(SEMANTIC_ROOT) not in sys.path:
    sys.path.insert(0, str(SEMANTIC_ROOT))

from semantic_worker_router import make_contract_job  # noqa: E402


class ProductionRunExecutor(_ProductionRunExecutor):
    """Public production executor with deterministic entry-contract guards.

    Literary judgment remains model-owned. This wrapper only rejects malformed
    registered semantic inputs before an expensive DRAFT/REVISE graph starts.
    """

    @staticmethod
    def validate_rule_material(rule_material: Any, reader_grip: Any) -> None:
        if not isinstance(rule_material, list) or not rule_material:
            raise ProductionRunError(
                "quality_rule_material_required",
                "non-empty authoritative rule_material is required for registered candidate self-audit",
            )
        dummy_fingerprint = "sha256:" + "0" * 64
        try:
            make_contract_job(
                "quality.candidate_self_audit",
                "PRODUCTION-RULE-MATERIAL-PREFLIGHT",
                {
                    "candidate_fingerprint": dummy_fingerprint,
                    "candidate_text": "Preflight placeholder; no literary judgment is executed.",
                    "rule_material": rule_material,
                    "reader_grip": reader_grip,
                },
                source_session_id="deterministic-preflight",
                handoff_id="quality-rule-material-preflight",
            )
        except ValueError as exc:
            raise ProductionRunError("quality_rule_material_invalid", str(exc)) from exc

    def execute(self, project_id: str, run_id: str, **kwargs: Any) -> dict[str, Any]:
        try:
            workflow = NovelWorkflowService(self.store).load(project_id, run_id)
        except WorkflowError as exc:
            raise ProductionRunError(
                "workflow_scope_required",
                "production execution requires a durable Quillframe 1.0 CH001 workflow binding",
            ) from exc
        if workflow.chapter_id != CHAPTER_SCOPE:
            raise ProductionRunError(
                "chapter_scope_violation",
                f"production execution is limited to {CHAPTER_SCOPE}",
            )
        if workflow.status in {"cancelled", "completed", "failed"}:
            raise ProductionRunError(
                "workflow_not_executable",
                f"workflow status is {workflow.status}",
            )
        self.validate_rule_material(kwargs.get("rule_material"), kwargs.get("reader_grip"))
        return super().execute(project_id, run_id, **kwargs)
