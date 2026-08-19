#!/usr/bin/env python3
"""Project-hosted peer semantic bridge.

Runs inside a consuming repository through a Quillframe composite action. The
consumer owns the Issue/runtime trace. This module only supplies the generic
relay/validation mechanism from the exact Framework revision pinned by the
consumer lockfile.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Any, NoReturn
import tomllib

PACKET_REFERENCE_MARKER = "<!-- quillframe-peer-packet-reference-v1 -->"
RESULT_MARKER = "<!-- quillframe-peer-result-v1 -->"
RESULT_REFERENCE_MARKER = "<!-- quillframe-peer-result-reference-v1 -->"
VALIDATION_MARKER = "<!-- quillframe-peer-validation-v1 -->"
RECEIPT_MARKER = "<!-- quillframe-peer-validation-receipt-v1 -->"
ISSUE_TOMBSTONE_SCHEMA = "quillframe_peer_issue_tombstone_v1"
PACKET_REFERENCE_SCHEMA = "quillframe_peer_packet_reference_v1"
RESULT_REFERENCE_SCHEMA = "quillframe_peer_result_reference_v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def caller_checkout(workspace: Path) -> Path:
    """Resolve the credentials-free caller checkout without allowing escape."""
    reference = os.environ.get("QUILLFRAME_PROJECT_CHECKOUT", "").strip()
    checkout = Path(reference) if reference else workspace
    if not checkout.is_absolute():
        checkout = workspace / checkout
    checkout = checkout.resolve()
    if workspace not in checkout.parents and checkout != workspace:
        fail("caller Project checkout escapes GitHub workspace")
    return checkout


def frozen_packet_checkout(workspace: Path) -> Path:
    """Resolve the bounded packet-transfer root inside the Actions workspace."""
    reference = os.environ.get("QUILLFRAME_FROZEN_PACKET_CHECKOUT", "").strip()
    if not reference:
        return caller_checkout(workspace)
    checkout = Path(reference)
    if not checkout.is_absolute():
        checkout = workspace / checkout
    checkout = checkout.resolve()
    if workspace not in checkout.parents and checkout != workspace:
        fail("frozen packet checkout escapes GitHub workspace")
    return checkout


def checkout_member(checkout: Path, reference: str, label: str) -> Path:
    path = Path(reference)
    path = path if path.is_absolute() else checkout / path
    path = path.resolve()
    if checkout not in path.parents and path != checkout:
        fail(f"{label} escapes caller Project checkout")
    return path


def positive_env_int(name: str) -> int:
    raw = os.environ.get(name, "")
    try:
        value = int(raw)
    except ValueError:
        fail(f"{name} must be a positive integer")
    if value <= 0:
        fail(f"{name} must be a positive integer")
    return value


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
    checkout = caller_checkout(workspace)
    project_root = checkout_member(checkout, os.environ["QUILLFRAME_PROJECT_ROOT"], "project root")

    manifest_path = project_root / "quillframe.toml"
    lock_path = project_root / "quillframe.lock.json"
    if not manifest_path.exists() or not lock_path.exists():
        fail("consumer must contain quillframe.toml and quillframe.lock.json")

    with manifest_path.open("rb") as f:
        manifest = tomllib.load(f)
    lock = read_json(lock_path)

    expected_project_id = os.environ["QUILLFRAME_PROJECT_ID"]
    actual_project_id = str((manifest.get("project") or {}).get("id") or "")
    if actual_project_id != expected_project_id:
        fail(f"project id mismatch: expected {expected_project_id}, got {actual_project_id}")

    framework = lock.get("framework") or {}
    locked_repo = canonical_repo(str(framework.get("source_repo") or ""))
    locked_commit = str(framework.get("commit") or "")
    action_repo = canonical_repo(os.environ.get("QUILLFRAME_ACTION_REPOSITORY", ""))
    action_ref = str(os.environ.get("QUILLFRAME_ACTION_REF") or "")
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
        "project_checkout": checkout,
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
    prefix = f"[quillframe-peer][{binding['project_id']}] "
    title = str(issue.get("title") or "")
    if not title.startswith(prefix):
        fail(f"issue title must start with {prefix!r}")
    return event, issue, issue_number


def validate_issue_tombstone(
    issue: dict[str, Any],
    binding: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, str]:
    """Require a manuscript-free Issue body bound to the exact frozen packet."""
    job = packet.get("job")
    if not isinstance(job, dict):
        fail("Core-frozen packet job must be an object")
    prefix = f"[quillframe-peer][{binding['project_id']}] "
    expected_title = prefix + str(job.get("job_id") or "")
    if str(issue.get("title") or "") != expected_title:
        fail("issue title must exactly bind the Core-frozen packet job_id")
    try:
        tombstone = json.loads(str(issue.get("body") or ""))
    except json.JSONDecodeError as exc:
        fail(f"issue body must be one {ISSUE_TOMBSTONE_SCHEMA} JSON object: {exc}")
    if not isinstance(tombstone, dict):
        fail(f"issue body must be one {ISSUE_TOMBSTONE_SCHEMA} JSON object")
    allowed = {"schema", "job_id", "input_fingerprint", "status"}
    if set(tombstone) != allowed:
        fail("peer issue tombstone fields must be exactly schema/job_id/input_fingerprint/status")
    expected = {
        "schema": ISSUE_TOMBSTONE_SCHEMA,
        "job_id": job.get("job_id"),
        "input_fingerprint": packet.get("input_fingerprint"),
        "status": "awaiting_external",
    }
    if tombstone != expected:
        fail("peer issue tombstone differs from the Core-frozen packet binding")
    return tombstone


def packet_reference(packet: dict[str, Any], packet_bytes: bytes, *, status: str) -> dict[str, Any]:
    job = packet.get("job")
    if not isinstance(job, dict):
        fail("Core-frozen packet job must be an object")
    relay_nonce = str(packet.get("relay_nonce") or "")
    if not relay_nonce:
        fail("Core-frozen packet relay nonce is required")
    return {
        "schema": PACKET_REFERENCE_SCHEMA,
        "job_id": job.get("job_id"),
        "input_fingerprint": packet.get("input_fingerprint"),
        "packet_fingerprint": "sha256:" + hashlib.sha256(packet_bytes).hexdigest(),
        "relay_nonce_fingerprint": "sha256:" + hashlib.sha256(relay_nonce.encode("utf-8")).hexdigest(),
        "status": status,
        "manuscript_published": False,
        "authority": False,
    }


def packet_reference_comment(packet: dict[str, Any], packet_bytes: bytes, *, status: str) -> str:
    reference = packet_reference(packet, packet_bytes, status=status)
    return "\n".join([
        PACKET_REFERENCE_MARKER,
        f"`semantic_status: {status}`",
        "",
        "The consuming Project retained the exact Core-frozen packet in the workflow artifact. This Issue stores only its non-authoritative fingerprint binding; manuscript bytes are not published here.",
        "",
        "```json",
        json.dumps(reference, ensure_ascii=False, indent=2),
        "```",
    ])


def result_reference_comment(result: dict[str, Any], *, status: str) -> str:
    worker = result.get("worker")
    if not isinstance(worker, dict):
        fail("peer result worker must be an object")
    reference = {
        "schema": RESULT_REFERENCE_SCHEMA,
        "job_id": result.get("job_id"),
        "input_fingerprint": result.get("input_fingerprint"),
        "result_fingerprint": "sha256:" + hashlib.sha256(canonical_json(result).encode("utf-8")).hexdigest(),
        "worker_provider": worker.get("provider"),
        "model_or_reviewer": worker.get("model_or_reviewer"),
        "status": status,
        "manuscript_published": False,
        "authority": False,
    }
    return "\n".join([
        RESULT_REFERENCE_MARKER,
        f"`semantic_status: {status}`",
        "",
        "The independent result remains in the workflow output. This Issue stores only its fingerprint and provider binding; judgment text and manuscript bytes are not published here.",
        "",
        "```json",
        json.dumps(reference, ensure_ascii=False, indent=2),
        "```",
    ])


def framework_paths() -> tuple[Path, Path, Path, Path]:
    action_path = Path(os.environ["QUILLFRAME_ACTION_PATH"]).resolve()
    framework_root = action_path.parents[2]
    router = framework_root / "harness" / "semantic_workers" / "semantic_worker_router.py"
    relay = framework_root / "harness" / "semantic_workers" / "peer_chat_relay.py"
    registered = framework_root / "harness" / "semantic_workers" / "registered_contract_binding.py"
    receipt = framework_root / "harness" / "semantic_workers" / "peer_bridge_receipt.py"
    for path in (router, relay, registered, receipt):
        if not path.exists():
            fail(f"Framework semantic runtime file missing: {path.name}")
    return router, relay, registered, receipt


def load_frozen_packet() -> tuple[dict[str, Any], bytes]:
    """Load the exact Core packet; absence or reserialization fails closed."""
    reference = os.environ.get("QUILLFRAME_FROZEN_PACKET", "").strip()
    if not reference:
        fail("QUILLFRAME_FROZEN_PACKET is required; packet creation belongs to Core")
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
    path = checkout_member(frozen_packet_checkout(workspace), reference, "frozen packet")
    if not path.is_file():
        fail(f"Core-frozen packet file not found: {path}")
    raw = path.read_bytes()
    expected_sha256 = os.environ.get("QUILLFRAME_FROZEN_PACKET_SHA256", "").strip()
    if (
        not expected_sha256.startswith("sha256:")
        or len(expected_sha256) != 71
        or any(ch not in "0123456789abcdef" for ch in expected_sha256[7:])
    ):
        fail("QUILLFRAME_FROZEN_PACKET_SHA256 must be one exact sha256:<64 lowercase hex> fingerprint")
    actual_sha256 = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        fail("Core-frozen packet SHA-256 differs from the caller-supplied Core fingerprint")
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"Core-frozen packet is invalid JSON: {exc}")
    if not isinstance(packet, dict):
        fail("Core-frozen packet must be a JSON object")
    _router, relay, _registered, _receipt = framework_paths()
    if str(relay.parent) not in sys.path:
        sys.path.insert(0, str(relay.parent))
    with tempfile.TemporaryDirectory(prefix="quillframe-frozen-packet-") as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_bytes(raw)
        module_path = relay
        spec = importlib.util.spec_from_file_location("qf_frozen_relay", module_path)
        if spec is None or spec.loader is None:
            fail("unable to load packet validator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        errors = module.validate_packet(packet)
    if errors:
        fail("Core-frozen packet rejected: " + "; ".join(errors))
    if raw != canonical_json(packet).encode("utf-8"):
        fail("Core-frozen packet bytes are not canonical; rebuild is forbidden")
    binding = packet.get("return_binding") or {}
    if binding.get("run_reference") != packet.get("relay_nonce"):
        fail("Core-frozen packet nonce binding is invalid")
    return packet, raw


def verify_job_provenance(job: dict[str, Any], binding: dict[str, Any]) -> None:
    provenance = job.get("provenance")
    if not isinstance(provenance, dict):
        fail("semantic job provenance must be an object")
    checks = {
        "project_id": binding["project_id"],
        "project_repo": binding["caller_repo"],
        "framework_repo": binding["framework_repo"],
        "framework_commit": binding["framework_commit"],
    }
    for key, expected in checks.items():
        actual = canonical_repo(str(provenance.get(key) or "")) if key.endswith("repo") else str(provenance.get(key) or "")
        if actual != expected:
            fail(f"job provenance mismatch for {key}: expected {expected}, got {actual}")


def validate_registered_contract_job(job_path: Path, registered: Path) -> None:
    job = read_json(job_path)
    input_obj = job.get("input")
    if isinstance(input_obj, dict) and input_obj.get("model_contract_id") is not None:
        run(["python", str(registered), "validate-job", "--job", str(job_path)])


def prepare(binding: dict[str, Any]) -> None:
    _event, issue, issue_number = common_event(binding)
    packet, packet_bytes = load_frozen_packet()
    job = packet.get("job")
    if not isinstance(job, dict):
        fail("Core-frozen packet job must be an object")
    validate_issue_tombstone(issue, binding, packet)
    verify_job_provenance(job, binding)

    router, _relay, registered, _receipt = framework_paths()
    with tempfile.TemporaryDirectory(prefix="quillframe-peer-") as tmp:
        tmpdir = Path(tmp)
        job_path = tmpdir / "job.json"
        jobs_path = tmpdir / "jobs.json"
        job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        jobs_path.write_text(json.dumps({"jobs": [job]}, ensure_ascii=False), encoding="utf-8")
        run(["python", str(router), "validate-jobs", "--jobs", str(jobs_path)])
        validate_registered_contract_job(job_path, registered)

    comment = packet_reference_comment(packet, packet_bytes, status="awaiting_user")
    run(["gh", "issue", "comment", str(issue_number), "--repo", binding["caller_repo"], "--body", comment])


def validate_result(binding: dict[str, Any]) -> dict[str, Any]:
    event, issue, issue_number = common_event(binding)
    comment = event.get("comment")
    if not isinstance(comment, dict) or RESULT_MARKER not in str(comment.get("body") or ""):
        fail("validate-result requires a marked peer result comment")
    result_comment_id = int(comment.get("id") or 0)
    if result_comment_id <= 0:
        fail("result comment id required")

    packet, packet_bytes = load_frozen_packet()
    validate_issue_tombstone(issue, binding, packet)
    result = parse_fenced(str(comment.get("body") or ""), RESULT_MARKER)
    job = packet.get("job") or {}
    if not isinstance(job, dict):
        fail("packet job must be object")
    verify_job_provenance(job, binding)

    runtime_trace = {
        "github_run_id": positive_env_int("GITHUB_RUN_ID"),
        "github_run_attempt": positive_env_int("GITHUB_RUN_ATTEMPT"),
        "github_event_name": os.environ.get("GITHUB_EVENT_NAME", ""),
        "result_comment_id": result_comment_id,
        "workflow_name": os.environ.get("GITHUB_WORKFLOW", ""),
        "framework_action_ref": os.environ.get("QUILLFRAME_ACTION_REF", ""),
    }

    _router, relay, registered, receipt_tool = framework_paths()
    with tempfile.TemporaryDirectory(prefix="quillframe-peer-result-") as tmp:
        tmpdir = Path(tmp)
        packet_path = tmpdir / "packet.json"
        result_path = tmpdir / "result.json"
        job_path = tmpdir / "job.json"
        runtime_trace_path = tmpdir / "runtime-trace.json"
        receipt_path = tmpdir / "validation-receipt.json"
        packet_path.write_bytes(packet_bytes)
        result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        runtime_trace_path.write_text(json.dumps(runtime_trace, ensure_ascii=False), encoding="utf-8")
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
            "--runtime-trace", str(runtime_trace_path),
            "--output", str(receipt_path),
        ])
        receipt = read_json(receipt_path)

    ready = "\n".join([
        VALIDATION_MARKER,
        RECEIPT_MARKER,
        "`semantic_status: validated_result_ready`",
        "",
        f"Project-owned peer result binding passed against Quillframe `{binding['framework_commit']}`. The manager may consume this logical result once after revalidating Project authority.",
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
        handle.write("validation-receipt<<QUILLFRAME_RECEIPT\n")
        handle.write(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.write("QUILLFRAME_RECEIPT\n")


def main() -> int:
    mode = os.environ.get("QUILLFRAME_BRIDGE_MODE", "")
    if mode not in {"prepare", "validate-result"}:
        fail("QUILLFRAME_BRIDGE_MODE must be prepare or validate-result")
    binding = load_project_binding()
    if mode == "prepare":
        prepare(binding)
        output = {
            "schema": "quillframe_project_peer_bridge_receipt_v1",
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
