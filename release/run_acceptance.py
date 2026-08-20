#!/usr/bin/env python3
"""Run only the generator-owned deterministic command set.

There is no command passthrough. Browser manifests and external receipts are
separate evidence channels and are never synthesized from a shell exit code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from acceptance import (
    AcceptanceError,
    EVIDENCE_SCHEMA,
    GATES,
    T310_SCHEMA,
    VERSION,
    RUNNER_COMMANDS,
    compute_subject,
    evidence_fingerprint,
    read_json_descriptor,
    read_file_bytes,
    redact_text,
    _relative_parts,
    _safe_output,
    validate_local_browser_manifest,
    validate_t605_manifest,
)

SECRET_ENV_NAME = re.compile(r"(?:TOKEN|SECRET|PASSWORD|PASSWD|COOKIE|AUTH|CREDENTIAL|PRIVATE|API[_-]?KEY|ACCESS[_-]?KEY|SESSION)", re.I)
SAFE_ENV_NAMES = frozenset({"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "CI", "TERM", "TMPDIR", "TMP", "TEMP", "CHROME_BIN", "PYTHON", "NODE", "COREPACK_ENABLE_PROJECT_SPEC", "GITHUB_ACTIONS", "GITHUB_WORKFLOW"})


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bounded_output(data: bytes, limit: int = 64 * 1024, secret_values: tuple[str, ...] = ()) -> bytes:
    return redact_text(data[:limit].decode("utf-8", errors="replace"), secret_values).encode("utf-8")


def write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError("short artifact write")
        offset += written


def child_environment(base: dict[str, str], overrides: dict[str, str] | None = None) -> dict[str, str]:
    result = {}
    for key, value in base.items():
        if SECRET_ENV_NAME.search(key):
            continue
        if key in SAFE_ENV_NAMES or key.startswith("LC_") or key.startswith("COREPACK_"):
            result[key] = value
    result.update(overrides or {})
    return result


def substitute(argv: tuple[str, ...], output: Path, wheel: Path | None = None) -> tuple[str, ...]:
    values = {"{OUTPUT}": str(output), "{WHEEL}": str(wheel) if wheel is not None else str(output / "wheel" / "MISSING.whl")}
    return tuple(item.replace("{OUTPUT}", values["{OUTPUT}"]).replace("{WHEEL}", values["{WHEEL}"]) for item in argv)


def run_process(argv: tuple[str, ...], cwd: Path, timeout_ms: int, environment: dict[str, str] | None = None) -> tuple[int, bytes, bytes, str, str]:
    started = timestamp()
    try:
        child = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    except OSError as exc:
        return 127, b"", str(exc).encode(), started, timestamp()
    try:
        stdout, stderr = child.communicate(timeout=timeout_ms / 1000)
        return child.returncode, stdout, stderr, started, timestamp()
    except subprocess.TimeoutExpired as first_timeout:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = child.communicate(timeout=5)
            return 124, stdout, stderr, started, timestamp()
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = child.communicate()
            return 137, stdout, stderr, started, timestamp()


def command_environment(command_name: str, original_environment: dict[str, str], output: Path, repo: Path) -> dict[str, str]:
    """Build the fixed child environment for one generator-owned command."""
    overrides: dict[str, str] = {}
    if command_name == "t605_browser":
        overrides["QF_BROWSER_EVIDENCE_DIR"] = str(output)
        overrides["QF_REPO_ROOT"] = str(repo)
        overrides["QF_START_PREVIEWS"] = "1"
    if command_name == "t603_site_smoke":
        overrides["QF_BROWSER_EVIDENCE_DIR"] = str(_safe_output(output / "t603-site-smoke"))
    if command_name == "t603_studio_smoke":
        overrides["QF_BROWSER_EVIDENCE_DIR"] = str(_safe_output(output / "t603-studio-smoke"))
    if command_name == "t603_local_launch":
        overrides["QF_BROWSER_EVIDENCE_DIR"] = str(_safe_output(output / "t603-local-launch"))
    return child_environment(original_environment, overrides)


def write_artifact(output: Path, name: str, data: bytes, role: str) -> dict:
    parts = _relative_parts(name)
    parent = output.joinpath(*parts[:-1]) if len(parts) > 1 else output
    _safe_output(parent)
    path = parent / parts[-1]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "role": role}


def write_t310_blocked_manifest(output: Path, subject: dict, reason: str) -> Path:
    path = output / "t310-local-browser.json"
    payload = {
        "schema": T310_SCHEMA,
        "status": "blocked",
        "task": "T310",
        "gate": "T310_BROWSER_LOCAL",
        "chapter_scope": "CH001",
        "subject": {"start": subject, "end": subject, "stable": True},
        "quick_demo": {"status": "blocked", "receipt_schema": "quillframe_ch001_quick_demo_receipt_v1", "chapter_scope": "CH001", "authority": False, "model_execution_performed": False, "uploads": 0, "canon_mutation": False},
        "launch": {"status": "blocked", "profile": "local", "loopback": False, "core_bound": False, "cloud_upload_started": False},
        "artifacts": [],
        "errors": [{"id": "runner", "code": "T310_BLOCKED", "reason": reason}],
        "generated_at": timestamp(),
    }
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def compose_t310_manifest(output: Path, subject_start: dict, subject_end: dict, command_results: dict[str, dict]) -> Path:
    """Compose T310 only from three fixed browser smoke outputs and real files."""
    required_commands = ("t603_site_smoke", "t603_studio_smoke", "t603_local_launch")
    reasons = []
    for name in required_commands:
        record = command_results.get(name)
        if record is None or record["result"] != "pass" or record["exit_code"] != 0:
            reasons.append(f"{name} did not pass its fixed predicate")
    if subject_start != subject_end:
        reasons.append("subject changed across T603 smoke")
    site_stdout = output / "commands" / "t603_site_smoke.stdout.txt"
    studio_stdout = output / "commands" / "t603_studio_smoke.stdout.txt"
    launch_stdout = output / "commands" / "t603_local_launch.stdout.txt"
    try:
        site_text = read_file_bytes(output, "commands/t603_site_smoke.stdout.txt", 64 * 1024).decode("utf-8")
        studio_text = read_file_bytes(output, "commands/t603_studio_smoke.stdout.txt", 64 * 1024).decode("utf-8")
        launch_text = read_file_bytes(output, "commands/t603_local_launch.stdout.txt", 64 * 1024).decode("utf-8")
    except (AcceptanceError, UnicodeError) as exc:
        reasons.append("T603 output readback failed: " + str(exc))
        site_text = studio_text = launch_text = ""
    if "browser_smoke=PASS" not in site_text:
        reasons.append("site smoke did not emit its pass receipt")
    if "browser_smoke=PASS" not in studio_text:
        reasons.append("studio smoke did not emit its pass receipt")
    launch_markers = ("local_launch_smoke=PASS", "local_launch_profile=local", "local_launch_core_bound=true", "local_launch_cloud_upload_started=false")
    for marker in launch_markers:
        if marker not in launch_text:
            reasons.append("local launch marker missing: " + marker)
    artifact_paths = (
        "t603-site-smoke/home-desktop.png",
        "t603-site-smoke/home-demo-complete.png",
        "t603-site-smoke/home-phone.png",
        "t603-site-smoke/docs-desktop.png",
        "t603-studio-smoke/studio-desktop.png",
        "t603-studio-smoke/studio-phone.png",
        "t603-studio-smoke/studio-dark.png",
        "t603-local-launch/local-launch-bound.png",
    )
    artifacts = []
    for relative in artifact_paths:
        try:
            data = read_file_bytes(output, relative)
            if not data:
                raise AcceptanceError("empty browser artifact")
            artifacts.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "role": "browser-screenshot"})
        except (AcceptanceError, OSError) as exc:
            reasons.append(f"browser artifact unavailable: {relative}: {exc}")
    if reasons:
        return write_t310_blocked_manifest(output, subject_start, ", ".join(reasons))
    payload = {
        "schema": T310_SCHEMA,
        "status": "pass",
        "task": "T310",
        "gate": "T310_BROWSER_LOCAL",
        "chapter_scope": "CH001",
        "subject": {"start": subject_start, "end": subject_end, "stable": True},
        "quick_demo": {"status": "pass", "receipt_schema": "quillframe_ch001_quick_demo_receipt_v1", "chapter_scope": "CH001", "authority": False, "model_execution_performed": False, "uploads": 0, "canon_mutation": False},
        "launch": {"status": "pass", "profile": "local", "loopback": True, "core_bound": True, "cloud_upload_started": False},
        "artifacts": artifacts,
        "errors": [],
        "generated_at": timestamp(),
    }
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path = output / "t310-local-browser.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def consume_t605_manifest(output: Path, subject: dict, redaction_values: tuple[str, ...] = (), subject_after: dict | None = None) -> tuple[list[dict], list[str]]:
    """Consume only the fixed root T605 manifest for this runner invocation."""
    browser_manifests: list[dict] = []
    blocks: list[str] = []
    path = output / "browser-acceptance-v1.json"
    if path.is_file() and not path.is_symlink():
        try:
            manifest = read_json_descriptor(output, path.name)
            validate_t605_manifest(manifest, subject, output)
            manifest_bytes = read_file_bytes(output, path.name)
            manifest_artifact = {"path": path.name, "size": len(manifest_bytes), "sha256": hashlib.sha256(manifest_bytes).hexdigest(), "role": "browser-manifest"}
            after = subject_after or subject
            browser_manifests.append({"id": "runner-t605-browser-manifest", "gate_id": "T605.browser.full", "subject": subject, "subject_after": after, "started_at": timestamp(), "finished_at": timestamp(), "result": "pass", "artifacts": [manifest_artifact], "manifest": manifest})
        except (AcceptanceError, OSError, UnicodeError) as exc:
            blocks.append("T605 manifest rejected: " + redact_text(str(exc), redaction_values))
    else:
        blocks.append("T605 browser manifest missing")
    return browser_manifests, blocks


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe fixed acceptance runner")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    output = _safe_output(Path(args.output).absolute())
    version = (repo / "VERSION").read_text(encoding="utf-8").strip()
    if version != VERSION:
        raise SystemExit("VERSION_MISMATCH")
    before = compute_subject(repo)
    original_environment = dict(os.environ)
    redaction_values = tuple(value for key, value in original_environment.items() if SECRET_ENV_NAME.search(key) and len(value) >= 4)
    records = []
    command_results: dict[str, dict] = {}
    for command in RUNNER_COMMANDS:
        wheels = sorted((output / "wheel").glob("*.whl"))
        argv = substitute(command.argv, output, wheels[0] if wheels else None)
        environment = command_environment(command.name, original_environment, output, repo)
        code, stdout, stderr, started, finished = run_process(argv, repo, command.timeout_ms, environment)
        result = "pass" if code == 0 else "blocked" if code in {124, 137, 127} else "failed"
        artifacts = [
            write_artifact(output, f"commands/{command.name}.stdout.txt", bounded_output(stdout, secret_values=redaction_values), "stdout"),
            write_artifact(output, f"commands/{command.name}.stderr.txt", bounded_output(stderr, secret_values=redaction_values), "stderr"),
        ]
        after = compute_subject(repo)
        if after != before:
            result = "failed"
        command_results[command.name] = {"result": result, "exit_code": code}
        for gate_id in command.gate_ids:
            records.append({
                "id": f"runner-{command.name}-{gate_id}",
                "gate_id": gate_id,
                "subject": before,
                "subject_after": after,
                "started_at": started,
                "finished_at": finished,
                "result": result,
                "artifacts": artifacts,
                "argv": list(command.argv),
                "cwd": "repo",
                "timeout_ms": command.timeout_ms,
                "exit_code": code,
                "predicate": GATES[gate_id].predicate,
            })
    subject_end = compute_subject(repo)
    t310_path = output / "t310-local-browser.json"
    if not t310_path.exists() and not t310_path.is_symlink():
        compose_t310_manifest(output, before, subject_end, command_results)
    browser_manifests, browser_manifest_blocks = consume_t605_manifest(output, before, redaction_values)
    final_subject = compute_subject(repo)
    for record in browser_manifests:
        record["subject_after"] = final_subject
    local_manifest_path = output / "t310-local-browser.json"
    if local_manifest_path.is_file() and not local_manifest_path.is_symlink():
        try:
            manifest = read_json_descriptor(output, local_manifest_path.name)
            if manifest.get("status") != "pass":
                errors = manifest.get("errors")
                if type(errors) is list:
                    reason = " | ".join(str(item.get("reason", item.get("code", "blocked"))) for item in errors if type(item) is dict)
                else:
                    reason = "blocked manifest"
                browser_manifest_blocks.append("T310 manifest blocked: " + (reason or "blocked manifest"))
                manifest = None
            else:
                validate_local_browser_manifest(manifest, before, output)
            if manifest is not None:
                manifest_bytes = read_file_bytes(output, local_manifest_path.name)
                manifest_artifact = {"path": local_manifest_path.name, "size": len(manifest_bytes), "sha256": hashlib.sha256(manifest_bytes).hexdigest(), "role": "browser-manifest"}
                after = compute_subject(repo)
                browser_manifests.append({"id": "runner-t310-browser-manifest", "gate_id": "T310.browser.local", "subject": before, "subject_after": after, "started_at": timestamp(), "finished_at": timestamp(), "result": "pass", "artifacts": [manifest_artifact], "manifest": manifest})
        except (AcceptanceError, OSError, UnicodeError) as exc:
            browser_manifest_blocks.append("T310 manifest rejected: " + redact_text(str(exc), redaction_values))
    else:
        write_t310_blocked_manifest(output, before, "T310 local browser manifest missing, command exit cannot authorize T310")
        browser_manifest_blocks.append("T310 local browser manifest missing, command exit cannot authorize T310")
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "framework_version": VERSION,
        "generated_at": timestamp(),
        "acceptance_subject": before,
        "evidence_fingerprint": "0" * 64,
        "commands": records,
        "browser_manifests": browser_manifests,
        "external_evidence": [],
        "environment_limited_checks": [{"id": "browser-manifest", "status": "blocked", "reason": ", ".join(browser_manifest_blocks), "owner": "T310/T605 browser runner"}] if browser_manifest_blocks else [],
    }
    evidence["evidence_fingerprint"] = evidence_fingerprint(evidence)
    evidence_data = (json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    evidence_fd = os.open(output / "evidence.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(evidence_fd, evidence_data)
        os.fsync(evidence_fd)
    finally:
        os.close(evidence_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
