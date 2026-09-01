"""Fixed offline regression runner for Framework checkpoint migrations."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from harness.context_runtime import fingerprint
from persistence.production_stage_repository import ProductionStageRepository

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGRESSION_MODULES = (
    "tests.test_quillframe_production_checkpoints",
    "tests.test_quillframe_writer_context",
    "tests.test_quillframe_persistence_c1",
)
MAX_CAPTURE_BYTES = 2 * 1024 * 1024


def run_and_record_build_regression(
    repository: ProductionStageRepository,
    project_id: str,
    run_id: str,
    *,
    new_framework_build: dict[str, Any],
    timeout_seconds: int = 20 * 60,
) -> dict[str, Any]:
    """Run the repository-owned suite and persist a non-caller-asserted receipt."""

    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    command = [sys.executable, "-m", "unittest", "-q", *DEFAULT_REGRESSION_MODULES]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    stdout = completed.stdout[-MAX_CAPTURE_BYTES:]
    stderr = completed.stderr[-MAX_CAPTURE_BYTES:]
    command_evidence = {
        "schema": "quillframe_offline_regression_command_v1",
        "argv": command[1:],
        "modules": list(DEFAULT_REGRESSION_MODULES),
        "cwd_fingerprint": fingerprint(str(ROOT.resolve())),
        "authority": False,
    }
    output_evidence = {
        "schema": "quillframe_offline_regression_output_v1",
        "returncode": completed.returncode,
        "stdout_fingerprint": fingerprint(stdout),
        "stderr_fingerprint": fingerprint(stderr),
        "stdout_truncated": len(completed.stdout) > MAX_CAPTURE_BYTES,
        "stderr_truncated": len(completed.stderr) > MAX_CAPTURE_BYTES,
        "authority": False,
    }
    if completed.returncode != 0:
        raise RuntimeError(
            "Framework migration regression failed; no migration receipt was recorded"
        )
    command_fp = fingerprint(command_evidence)
    output_fp = fingerprint(output_evidence)
    return repository._record_offline_regression_receipt(
        project_id,
        run_id,
        new_framework_build=new_framework_build,
        test_command_fingerprint=command_fp,
        test_output_fingerprint=output_fp,
        test_evidence_fingerprints=[command_fp, output_fp],
    )
