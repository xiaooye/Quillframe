#!/usr/bin/env python3
"""Project-hosted peer semantic bridge.

Runs inside a consuming repository through a NovelForge composite action. The
consumer owns the Issue/runtime trace. This module only supplies the generic
relay/validation mechanism from the exact Framework revision pinned by the
consumer lockfile.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, NoReturn
import tomllib

PACKET_MARKER = "<!-- novelforge-peer-packet-v1 -->"
RESULT_MARKER = "<!-- novelforge-peer-result-v1 -->"
VALIDATION_MARKER = "<!-- novelforge-peer-validation-v1 -->"
RECEIPT_MARKER = "<!-- novelforge-peer-validation-receipt-v1 -->"


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def run(cmd: list[str], *, capture: bool = False) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=capture, check=False)
    if proc.returncode != 0:
        fail((proc.stderr or proc.stdout or "command failed").strip())
    return proc.stdout if capture else ""


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def canonical_repo(value: str) -> str:
    return value.strip().lower()


def parse_fenced(body: str, marker: str) -> dict[str, Any]:
    if marker not in body:
        fail(f"marker missing: {marker}")
    tail = body.split(marker, 1)[1]
    if "```json" in tail:
        tail = tail.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in tail:
        tail = tail.split("```", 1)[1].split("```", 1)[0]
    value = json.loads(tail.strip())
    if not isinstance(value, dict):
        fail("marked payload must be a JSON object")
    return value


def load_project_binding() -> dict[str, Any]:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    project_root = (workspace / os.environ["NOVELFORGE_PROJECT_ROOT"]).resolve()
    if workspace not in project_root.parents and project_root != workspace:
        fail("project root escapes caller workspace")

    manifest_path = project_root / "novelforge.toml"
    lock_path = project_root / "novelforge.lock.json"
    if not manifest_path.exists() or not lock_path.exists():
        fail("consumer must contain novelforge.toml and novelforge.lock.json")

    with manifest_path.open("rb") as f:
        manifest = tomllib.load(f)
    lock = read_json(lock_path)

    expected_project_id = os.environ["NOVELFORGE_PROJECT_ID"]
    actual_project_id = str((manifest.get("project") or {}).get("id") or "")
    if actual_project_id != expected_project_id:
        fail(f"project id mismatch: expected {expected_project_id}, got {actual_project_id}")

    framework = lock.get("framework") or {}
    locked_repo = canonical_repo(str(framework.get("source_repo") or ""))
    locked_commit = str(framework.get("commit") or "")
    action_repo = canonical_repo(os.environ.get("NOVELFORGE_ACTION_REPOSITORY", ""))
    action_ref = str(os.environ.get("NOVELFORGE_ACTION_REF") or "")
    caller_repo = canonical_repo(os.environ.get("GITHUB_REPOSITORY", ""))

    if not locked_repo or not locked_commit:
        fail("framework lock must contain source_repo and exact commit")
    if locked_repo != action_repo:
        fail(f"framework repository mismatch: lock={locked_repo}, action={action_repo}")
    if locked_commit != action_ref:
        fail(f"framework commit mismatch: lock={locked_commit}, action_ref={action_ref}")
    if caller_repo == action_repo:
        fail("consumer peer bridge may not run with Framework repository as caller")

    return {
        "workspace": workspace,
        "project_root": project_root,
        "project_id": actual_project_id,
        "framework_repo": locked_repo,
        "framework_commit": locked_commit,
        "caller_repo": caller_repo,
    }


def common_event(binding: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    event = read_json(Path(os.environ["GITHUB_EVENT_PATH"]))
    issue = event.get("issue")
    if not isinstance(issue, dict):
        fail("peer bridge requires an issue-scoped event")
    issue_number = int(issue.get("number") or 0)
    if issue_number <= 0:
        fail("invalid issue number")

    actor = os.environ.get("GITHUB_ACTOR", "")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    if actor != owner:
        fail("only repository owner may trigger the default peer bridge")
    prefix = f"[novelforge-peer][{binding['project_id']}] "
    title = str(issue.get("title") or "")
    if not title.startswith(prefix):
        fail(f"issue title must start with {prefix!r}")
    return event, issue, issue_number


def framework_paths() -> tuple[Path, Path, Path, Path]:
    action_path = Path(os.environ["NOVELFORGE_ACTION_PATH"]).resolve()
    framework_root = action_path.parents[2]
    router = framework_root / "harness" / "semantic_workers" / "semantic_worker_router.py"
    relay = framework_root / "harness" / "semantic_workers" / "peer_chat_relay.py"
    registered = framework_root / "harness" / "semantic_workers" / "registered_contract_binding.py"
    receipt = framework_root / "harness" / "semantic_workers" / "peer_bridge_receipt.py"
    for path in (router, relay, registered, receipt):
        if not path.exists():
            fail(f"Framework semantic runtime file missing: {path.name}")
    return router, relay, registered, receipt


def verify_job_provenance(job: dict[str, Any], binding: dict[str, Any]) -> None:
    provenance = job.get("provenance")
    if not isinstance(provenance, dict):
        fail("semantic job provenance must be an object")
    checks = {
        "project_repo": binding["caller_repo"],
        "framework_repo": binding["framework_repo"],
        "framework_commit": binding["framework_commit"],
    }
    for key, expected in checks.items():
        actual = canonical_repo(str(provenance.get(key) or "")) if key.endswith("repo") else str(provenance.get(key) or "")
        if actual != expected:
            fail(f"job provenance mismatch for {key}: expected {expected}, got {actual}")
    project_id = provenance.get("project_id")
    if project_id is not None and str(project_id) != binding["project_id"]:
        fail("job provenance project_id mismatch")


def validate_registered_contract_job(job_path: Path, registered: Path) -> None:
    job = read_json(job_path)
    input_obj = job.get("input")
    if isinstance(input_obj, dict) and input_obj.get("model_contract_id") is not None:
        run(["python", str(registered), "validate-job", "--job", str(job_path)])


def prepare(binding: dict[str, Any]) -> None:
    _event, issue, issue_number = common_event(binding)
    body = str(issue.get("body") or "")
    job = json.loads(body)
    if not isinstance(job, dict):
        fail("issue body must be one semantic job JSON object")

    prefix = f"[novelforge-peer][{binding['project_id']}] "
    expected_job_id = str(issue.get("title") or "")[len(prefix):].strip()
    if job.get("job_id") != expected_job_id:
        fail("issue body job_id must match title suffix")
    verify_job_provenance(job, binding)

    router, relay, registered, _receipt = framework_paths()
    with tempfile.TemporaryDirectory(prefix="novelforge-peer-") as tmp:
        tmpdir = Path(tmp)
        job_path = tmpdir / "job.json"
        jobs_path = tmpdir / "jobs.json"
        packet_path = tmpdir / "packet.json"
        job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        jobs_path.write_text(json.dumps({"jobs": [job]}, ensure_ascii=False), encoding="utf-8")
        run(["python", str(router), "validate-jobs", "--jobs", str(jobs_path)])
        validate_registered_contract_job(job_path, registered)
        run(["python", str(relay), "build", "--job", str(job_path), "--output", str(packet_path)])
        packet = packet_path.read_text(encoding="utf-8").strip()

    comment = "\n".join([
        PACKET_MARKER,
        "`semantic_status: awaiting_user`",
        "",
        "This runtime trace is owned by the consuming Project repository. Use a genuinely separate reviewer session and return only the typed result in a new comment prefixed with `<!-- novelforge-peer-result-v1 -->`.",
        "",
        "```json",
        packet,
        "```",
    ])
    run(["gh", "issue", "comment", str(issue_number), "--repo", binding["caller_repo"], "--body", comment])


def validate_result(binding: dict[str, Any]) -> dict[str, Any]:
    event, _issue, issue_number = common_event(binding)
    comment = event.get("comment")
    if not isinstance(comment, dict) or RESULT_MARKER not in str(comment.get("body") or ""):
        fail("validate-result requires a marked peer result comment")

    comments_raw = run([
        "gh", "api", f"repos/{binding['caller_repo']}/issues/{issue_number}/comments?per_page=100"
    ], capture=True)
    comments = json.loads(comments_raw)
    if not isinstance(comments, list):
        fail("GitHub comments response must be a list")
    packets = [c for c in comments if PACKET_MARKER in str((c or {}).get("body") or "")]
    if not packets:
        fail("no peer packet found in Project issue")

    packet = parse_fenced(str(packets[-1].get("body") or ""), PACKET_MARKER)
    result = parse_fenced(str(comment.get("body") or ""), RESULT_MARKER)
    job = packet.get("job") or {}
    if not isinstance(job, dict):
        fail("packet job must be object")
    verify_job_provenance(job, binding)

    _router, relay, registered, receipt_tool = framework_paths()
    with tempfile.TemporaryDirectory(prefix="novelforge-peer-result-") as tmp:
        tmpdir = Path(tmp)
        packet_path = tmpdir / "packet.json"
        result_path = tmpdir / "result.json"
        job_path = tmpdir / "job.json"
        receipt_path = tmpdir / "validation-receipt.json"
        packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
        result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        run(["python", str(relay), "validate-result", "--packet", str(packet_path), "--result", str(result_path)])
        validate_registered_contract_job(job_path, registered)
        run([
            "python", str(receipt_tool), "build",
            "--packet", str(packet_path),
            "--result", str(result_path),
            "--project-id", binding["project_id"],
            "--project-repo", binding["caller_repo"],
            "--framework-repo", binding["framework_repo"],
            "--framework-commit", binding["framework_commit"],
            "--issue-number", str(issue_number),
            "--output", str(receipt_path),
        ])
        receipt = read_json(receipt_path)

    ready = "\n".join([
        VALIDATION_MARKER,
        RECEIPT_MARKER,
        "`semantic_status: validated_result_ready`",
        "",
        f"Project-owned peer result binding passed against NovelForge `{binding['framework_commit']}`. The manager may consume this logical result once after revalidating Project authority.",
        "",
        "```json",
        json.dumps(receipt, ensure_ascii=False, indent=2),
        "```",
    ])
    run(["gh", "issue", "comment", str(issue_number), "--repo", binding["caller_repo"], "--body", ready])
    run(["gh", "issue", "close", str(issue_number), "--repo", binding["caller_repo"], "--reason", "completed"])
    return receipt


def write_action_output(receipt: dict[str, Any]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write("validation-receipt<<NOVELFORGE_RECEIPT\n")
        handle.write(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.write("NOVELFORGE_RECEIPT\n")


def main() -> int:
    mode = os.environ.get("NOVELFORGE_BRIDGE_MODE", "")
    if mode not in {"prepare", "validate-result"}:
        fail("NOVELFORGE_BRIDGE_MODE must be prepare or validate-result")
    binding = load_project_binding()
    if mode == "prepare":
        prepare(binding)
        output = {
            "schema": "novelforge_project_peer_bridge_receipt_v1",
            "mode": mode,
            "project_id": binding["project_id"],
            "project_repo": binding["caller_repo"],
            "framework_repo": binding["framework_repo"],
            "framework_commit": binding["framework_commit"],
            "project_hosted": True,
            "authority": False,
        }
    else:
        output = validate_result(binding)
        write_action_output(output)
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
