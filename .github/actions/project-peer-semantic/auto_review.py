#!/usr/bin/env python3
"""Project-owned independent semantic review through GitHub Copilot CLI.

Runs only inside a consuming Project GitHub Actions workflow. The reviewer sees
only the bounded peer packet, never the writer conversation or Project checkout.
The script deterministically wraps the model's judgment with exact job/
fingerprint/nonce provenance, validates it through Quillframe's peer contracts,
builds the Project-owned receipt, and posts the auditable result back to the
Project issue.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ACTION = Path(__file__).resolve().parent
if str(ACTION) not in sys.path:
    sys.path.insert(0, str(ACTION))

import bridge  # noqa: E402

DEFAULT_MODEL = "claude-sonnet-4.6"


def _semantic_modules():
    action_path = Path(os.environ["QUILLFRAME_ACTION_PATH"]).resolve()
    framework_root = action_path.parents[2]
    semantic = framework_root / "harness" / "semantic_workers"
    if str(semantic) not in sys.path:
        sys.path.insert(0, str(semantic))
    from peer_bridge_receipt import build_receipt, validate_receipt
    from peer_chat_relay import build as build_packet, validate_peer_result
    from registered_contract_binding import validate_registered_job
    from semantic_worker_router import validate_dispatchable_job
    return build_receipt, validate_receipt, build_packet, validate_peer_result, validate_registered_job, validate_dispatchable_job


def _parse_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```json"):
        value = value[len("```json"):]
    elif value.startswith("```"):
        value = value[3:]
    if value.endswith("```"):
        value = value[:-3]
    value = value.strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Copilot reviewer did not return a JSON object")
        parsed = json.loads(value[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Copilot reviewer judgment must be a JSON object")
    return parsed


def _copilot_judgment(packet: dict[str, Any], model: str) -> dict[str, Any]:
    if not (os.environ.get("COPILOT_GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        raise ValueError("Copilot authentication token is required for independent peer review")
    job = packet["job"]
    prompt = "\n".join([
        "You are the genuinely separate independent semantic reviewer for one frozen Quillframe job.",
        "Judge ONLY the bounded job supplied below. Do not use repository files, web access, tools, persistent memory, hidden expected labels, or the writer conversation.",
        "Return ONLY the JSON object required by job.output_contract for result.judgment.",
        "Do not return the outer semantic-result envelope, markdown, commentary, or chain-of-thought. The deterministic Quillframe bridge owns IDs, fingerprints, worker provenance, and nonce binding.",
        "",
        json.dumps({
            "reviewer_instruction": packet.get("reviewer_instruction"),
            "job": job,
        }, ensure_ascii=False, indent=2),
    ])
    with tempfile.TemporaryDirectory(prefix="quillframe-copilot-review-") as tmp:
        root = Path(tmp)
        home = root / "copilot-home"
        home.mkdir()
        env = os.environ.copy()
        env["COPILOT_HOME"] = str(home)
        command = [
            "copilot",
            "-s",
            "--no-ask-user",
            "--model",
            model,
            "--deny-tool=shell",
            "--deny-tool=write",
            "--deny-tool=read",
            "--deny-tool=url",
            "--deny-tool=memory",
        ]
        proc = subprocess.run(
            command,
            text=True,
            input=prompt,
            capture_output=True,
            cwd=root,
            env=env,
            check=False,
            timeout=180,
        )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "Copilot CLI failed").strip()[:1600]
        raise RuntimeError(f"Copilot CLI independent review failed: {detail}")
    if not proc.stdout.strip():
        raise ValueError("Copilot reviewer response content missing")
    return _parse_json_object(proc.stdout)


def _post_comment(repo: str, issue_number: int, body: str) -> int:
    raw = bridge.run([
        "gh", "api", "--method", "POST",
        f"repos/{repo}/issues/{issue_number}/comments",
        "-f", f"body={body}",
        "--jq", ".id",
    ], capture=True).strip()
    try:
        comment_id = int(raw)
    except ValueError as exc:
        raise ValueError("GitHub result comment id missing") from exc
    if comment_id <= 0:
        raise ValueError("GitHub result comment id invalid")
    return comment_id


def _write_output(name: str, value: dict[str, Any]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    marker = "QUILLFRAME_" + name.upper().replace("-", "_")
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}<<{marker}\n")
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.write(marker + "\n")


def main() -> int:
    binding = bridge.load_project_binding()
    _event, issue, issue_number = bridge.common_event(binding)
    body = str(issue.get("body") or "")
    job = json.loads(body)
    if not isinstance(job, dict):
        bridge.fail("issue body must be one semantic job JSON object")
    prefix = f"[quillframe-peer][{binding['project_id']}] "
    expected_job_id = str(issue.get("title") or "")[len(prefix):].strip()
    if job.get("job_id") != expected_job_id:
        bridge.fail("issue body job_id must match title suffix")
    bridge.verify_job_provenance(job, binding)

    build_receipt, validate_receipt, build_packet, validate_peer_result, validate_registered_job, validate_dispatchable_job = _semantic_modules()
    dispatch_errors = validate_dispatchable_job(job)
    if dispatch_errors:
        bridge.fail("invalid dispatchable peer job: " + "; ".join(dispatch_errors))
    registered_errors = validate_registered_job(job)
    if registered_errors:
        bridge.fail("invalid registered peer job: " + "; ".join(registered_errors))
    packet = build_packet(job)

    packet_comment = "\n".join([
        bridge.PACKET_MARKER,
        "`semantic_status: independent_model_running`",
        "",
        "Project-owned GitHub Actions is dispatching this exact bounded packet to a separate GitHub Copilot CLI invocation.",
        "",
        "```json",
        json.dumps(packet, ensure_ascii=False, indent=2),
        "```",
    ])
    _post_comment(binding["caller_repo"], issue_number, packet_comment)

    model = os.environ.get("QUILLFRAME_REVIEW_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    judgment = _copilot_judgment(packet, model)
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "github_copilot_actions",
            "model_or_reviewer": f"github-copilot-cli:{model}",
            "run_reference": packet["relay_nonce"],
        },
        "judgment": judgment,
        "proposals": [],
        "errors": [],
        "execution": {
            "run_reference": packet["relay_nonce"],
            "transport": "github_copilot_actions",
            "github_run_id": bridge.positive_env_int("GITHUB_RUN_ID"),
            "github_run_attempt": bridge.positive_env_int("GITHUB_RUN_ATTEMPT"),
            "workflow_name": os.environ.get("GITHUB_WORKFLOW", ""),
            "model_requested": model,
        },
    }
    peer_errors = validate_peer_result(packet, result)
    if peer_errors:
        bridge.fail("Copilot peer result failed Quillframe validation: " + "; ".join(peer_errors))

    result_comment = "\n".join([
        bridge.RESULT_MARKER,
        "`semantic_status: completed_by_github_copilot_actions`",
        "",
        f"Independent provider: `github_copilot_actions` · model: `{model}`",
        "",
        "```json",
        json.dumps(result, ensure_ascii=False, indent=2),
        "```",
    ])
    result_comment_id = _post_comment(binding["caller_repo"], issue_number, result_comment)
    runtime_trace = {
        "source": "project_owned_github_actions_bridge",
        "github_run_id": bridge.positive_env_int("GITHUB_RUN_ID"),
        "github_run_attempt": bridge.positive_env_int("GITHUB_RUN_ATTEMPT"),
        "github_event_name": os.environ.get("GITHUB_EVENT_NAME", ""),
        "result_comment_id": result_comment_id,
        "workflow_name": os.environ.get("GITHUB_WORKFLOW", ""),
        "framework_action_ref": os.environ.get("QUILLFRAME_ACTION_REF", ""),
    }
    receipt = build_receipt(
        packet,
        result,
        project_id=binding["project_id"],
        project_repo=binding["caller_repo"],
        framework_repo=binding["framework_repo"],
        framework_commit=binding["framework_commit"],
        issue_number=issue_number,
        runtime_trace=runtime_trace,
    )
    receipt_errors = validate_receipt(receipt, packet, result)
    if receipt_errors:
        bridge.fail("Project peer receipt failed post-build validation: " + "; ".join(receipt_errors))

    validation_comment = "\n".join([
        bridge.VALIDATION_MARKER,
        bridge.RECEIPT_MARKER,
        "`semantic_status: validated_result_ready`",
        "",
        f"Project-owned GitHub Copilot result passed exact Quillframe `{binding['framework_commit']}` binding.",
        "",
        "```json",
        json.dumps(receipt, ensure_ascii=False, indent=2),
        "```",
    ])
    _post_comment(binding["caller_repo"], issue_number, validation_comment)
    bridge.run(["gh", "issue", "close", str(issue_number), "--repo", binding["caller_repo"], "--reason", "completed"])
    _write_output("peer-result", result)
    _write_output("validation-receipt", receipt)
    print(json.dumps({
        "schema": "quillframe_project_github_copilot_peer_review_v1",
        "project_id": binding["project_id"],
        "issue_number": issue_number,
        "worker_provider": "github_copilot_actions",
        "model_or_reviewer": f"github-copilot-cli:{model}",
        "result": judgment.get("result"),
        "result_fingerprint": receipt["result_fingerprint"],
        "validation_receipt": receipt,
        "authority": False,
        "model_execution": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
