#!/usr/bin/env python3
"""Opt-in, one-process-per-request Codex transport for the loopback relay.

This is manager transport, never an independent-review receipt. It preserves
the original message values and the CLI's final UTF-8 bytes. CLI configuration
and event rejection bound context/tool use; they do not attest OS isolation or
prove the provider's internal retry count. No model runs on import or in CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from harness.integrations.chat_host_relay import SCHEMA as RELAY_SCHEMA

SCHEMA = "quillframe_codex_cli_relay_v1"
MANAGER_CALL_LIMIT = 63  # One further invocation is reserved for independent review.
RELAY_LIFETIME_SECONDS = 170.0
MAX_WORKER_SECONDS = 150.0
PUBLISH_RESERVE_SECONDS = 5.0
COUNTED_EVENTS = {"spawned", "spawn_failed", "cli_started"}
REQUEST_ID = re.compile(r"req_[0-9a-f]{32}\Z")
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "shell_snapshot", "code_mode_host",
    "multi_agent", "apps", "plugins", "remote_plugin", "browser_use",
    "browser_use_external", "computer_use", "in_app_browser",
    "image_generation", "view_image", "workspace_dependencies", "skill_search",
    "skill_mcp_dependency_install", "hooks", "goals", "memories", "tool_suggest",
    "unbounded_connection_retries",
)
CLI_CONFIG = (
    "project_doc_max_bytes=0", "project_doc_fallback_filenames=[]",
    'web_search="disabled"', "tools.view_image=false",
    "hide_agent_reasoning=true", "show_raw_agent_reasoning=false",
    'model_reasoning_summary="none"', 'history.persistence="none"',
)
ENVIRONMENT_KEYS = {
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "HOME",
    "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
    "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "USER", "USERNAME",
    "CODEX_HOME", "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTP_PROXY", "HTTPS_PROXY",
    "ALL_PROXY", "NO_PROXY",
}
TRANSPORT_INSTRUCTION = (
    "Execute the supplied original message sequence as one bounded request. "
    "Use only this packet; do not use tools, read files, or consult other context. "
    "Return only the assistant response content requested by that sequence. "
    "The following JSON array preserves every original role and content value.\n"
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


class RelayError(RuntimeError):
    """A metadata-only error; never include prompt, output, stderr or reasoning."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def _load_json(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)


def read_ledger(queue: Path) -> list[dict[str, Any]]:
    path = queue / "calls.jsonl"
    if not path.exists():
        return []
    try:
        rows = [_load_json(line) for line in path.read_bytes().splitlines() if line.strip()]
    except (UnicodeError, ValueError, OSError) as exc:
        raise RelayError("invalid_ledger") from exc
    if any(
        not isinstance(row, dict) or not isinstance(row.get("event"), str)
        or (row.get("request_id") is not None and not isinstance(row["request_id"], str))
        for row in rows
    ):
        raise RelayError("invalid_ledger")
    return rows


def used_calls(rows: list[dict[str, Any]]) -> int:
    # Failed launches count, even when a host never returned a thread identity.
    return sum(row["event"] in COUNTED_EVENTS for row in rows)


def _append(queue: Path, row: dict[str, Any]) -> None:
    with (queue / "calls.jsonl").open("ab") as stream:
        stream.write(json_bytes(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def _exclusive_write(path: Path, raw: bytes) -> None:
    # The relay retries incomplete JSON while this exclusive publication finishes.
    # Unlike replace(), this cannot overwrite another publisher on Windows/UNC.
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def driver_lock(queue: Path) -> Iterator[None]:
    path = queue / ".codex-cli-driver.lock"
    try:
        _exclusive_write(path, json_bytes({"pid": os.getpid(), "created_at_unix": time.time()}))
    except FileExistsError as exc:
        raise RelayError("driver_lock_exists_no_automatic_recovery") from exc
    try:
        yield
    finally:
        path.unlink()


@dataclass(frozen=True)
class DriverConfig:
    queue: Path
    cli_binary: str
    run_id: str
    source_snapshot_sha256: str
    model: str
    reasoning_effort: str = "xhigh"
    allow_model_execution: bool = False
    manager_limit: int = MANAGER_CALL_LIMIT
    worker_seconds: float = MAX_WORKER_SECONDS

    def validate(self) -> None:
        if not self.allow_model_execution:
            raise RelayError("explicit_model_execution_opt_in_required")
        if not self.cli_binary or not self.model or not self.run_id:
            raise RelayError("missing_explicit_host_or_run_identity")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_snapshot_sha256):
            raise RelayError("invalid_source_snapshot_sha256")
        if not 1 <= self.manager_limit <= MANAGER_CALL_LIMIT:
            raise RelayError("manager_limit_exceeds_reserved_review_budget")
        if not math.isfinite(self.worker_seconds) or not 0 < self.worker_seconds <= MAX_WORKER_SECONDS:
            raise RelayError("invalid_worker_timeout")


def cli_command(config: DriverConfig, cwd: Path, output: Path) -> list[str]:
    command = [
        config.cli_binary, "--ask-for-approval", "never", "exec", "--json", "--strict-config",
        "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
        "--sandbox", "read-only", "--color", "never", "--cd", str(cwd),
        "--model", config.model, "--output-last-message", str(output),
        "--enable", "skip_host_skill_discovery",
    ]
    for feature in DISABLED_FEATURES:
        command.extend(("--disable", feature))
    for setting in (*CLI_CONFIG, "model_reasoning_effort=" + json.dumps(config.reasoning_effort)):
        command.extend(("--config", setting))
    return command + ["-"]


def child_environment() -> dict[str, str]:
    # Retain signed-in CLI auth discovery, not arbitrary project secrets, API-key
    # provider overrides, parent thread IDs or host-injected context variables.
    return {key: value for key, value in os.environ.items() if key.upper() in ENVIRONMENT_KEYS}


@dataclass
class EventAudit:
    thread_id: str | None = None
    final_message: str | None = field(default=None, repr=False)
    usage: dict[str, int] | None = None
    errors: list[str] = field(default_factory=list)
    forbidden_event_count: int = 0
    safe_lines: list[bytes] = field(default_factory=list, repr=False)

    @property
    def evidence(self) -> bytes:
        return b"".join(line + b"\n" for line in self.safe_lines)


def audit_events(raw: bytes) -> EventAudit:
    """Validate one JSONL turn and retain no message or reasoning text in logs."""
    audit = EventAudit()
    seen: set[bytes] = set()
    item_states: dict[str, tuple[str, str]] = {}
    turn_started = turn_completed = False
    final_count = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        safe: dict[str, Any] = {"event_sha256": sha256(line), "event_bytes": len(line)}
        try:
            event = _load_json(line)
            if not isinstance(event, dict):
                raise ValueError("not_object")
            canonical = json.dumps(event, sort_keys=True, allow_nan=False).encode("utf-8")
        except (ValueError, UnicodeError):
            audit.errors.append("invalid_cli_jsonl")
            audit.safe_lines.append(json_bytes(safe))
            continue
        if canonical in seen:
            audit.errors.append("duplicate_cli_event")
        seen.add(canonical)
        kind = event.get("type")
        safe["type"] = kind if isinstance(kind, str) and re.fullmatch(r"[a-z_.]+", kind) else "invalid"
        if safe["type"] == "invalid":
            audit.errors.append("unknown_cli_event")
            audit.forbidden_event_count += 1
            audit.safe_lines.append(json_bytes(safe))
            continue
        if turn_completed:
            audit.errors.append("event_after_turn_completed")
        if kind == "thread.started":
            identity = event.get("thread_id")
            try:
                valid_uuid = isinstance(identity, str) and str(uuid.UUID(identity)) == identity.lower()
            except ValueError:
                valid_uuid = False
            if not valid_uuid or audit.thread_id is not None or turn_started or set(event) != {"type", "thread_id"}:
                audit.errors.append("invalid_or_duplicate_thread_started")
            else:
                audit.thread_id = identity
            if valid_uuid and set(event) == {"type", "thread_id"}:
                audit.safe_lines.append(line)  # Actual, unmodified host identity event.
                continue
        elif kind == "turn.started":
            if audit.thread_id is None or turn_started or set(event) != {"type"}:
                audit.errors.append("invalid_or_duplicate_turn_started")
            turn_started = True
        elif kind == "turn.completed":
            usage = event.get("usage")
            if not turn_started or turn_completed or final_count != 1:
                audit.errors.append("invalid_or_duplicate_turn_completed")
            if (
                set(event) == {"type", "usage"} and isinstance(usage, dict)
                and {"input_tokens", "output_tokens"}.issubset(usage)
                and set(usage) <= {"input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"}
                and all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0 for k, v in usage.items())
            ):
                audit.usage = dict(usage)
                audit.safe_lines.append(line)  # Token counts only, no reasoning text.
            else:
                audit.errors.append("invalid_turn_usage")
                audit.safe_lines.append(json_bytes(safe))
            turn_completed = True
            continue
        elif kind in {"item.started", "item.updated", "item.completed"}:
            item = event.get("item")
            if not turn_started or not isinstance(item, dict):
                audit.errors.append("invalid_cli_item")
            else:
                item_type, item_id = item.get("type"), item.get("id")
                safe["item_type"] = item_type if isinstance(item_type, str) and re.fullmatch(r"[a-z_]+", item_type) else "invalid"
                try:
                    if isinstance(item_id, str):
                        safe["item_id_sha256"] = sha256(item_id.encode("utf-8"))
                    if isinstance(item.get("text"), str):
                        text_bytes = item["text"].encode("utf-8")
                        safe.update(text_sha256=sha256(text_bytes), text_bytes=len(text_bytes))
                except UnicodeError:
                    audit.errors.append("invalid_cli_item_unicode")
                    audit.safe_lines.append(json_bytes(safe))
                    continue
                if not isinstance(item_type, str) or item_type not in {"agent_message", "reasoning"}:
                    audit.forbidden_event_count += 1
                    audit.errors.append("forbidden_cli_item")
                elif not isinstance(item_id, str) or not item_id:
                    audit.errors.append("missing_cli_item_identity")
                else:
                    previous = item_states.get(item_id)
                    state = kind.removeprefix("item.")
                    if previous and (previous[0] != item_type or previous[1] == "completed" or state == "started"):
                        audit.errors.append("duplicate_or_inconsistent_cli_item")
                    item_states[item_id] = (item_type, state)
                    if item.get("status") not in (None, "in_progress", "completed"):
                        audit.errors.append("failed_cli_item")
                    if item_type == "agent_message" and state == "completed":
                        final_count += 1
                        if not isinstance(item.get("text"), str) or final_count != 1:
                            audit.errors.append("missing_or_duplicate_final_message")
                        else:
                            audit.final_message = item["text"]
        elif kind in {"turn.failed", "error"}:
            audit.errors.append("cli_reported_failure")
        else:
            audit.forbidden_event_count += 1
            audit.errors.append("unknown_cli_event")
        audit.safe_lines.append(json_bytes(safe))
    if audit.thread_id is None or not turn_started or not turn_completed or final_count != 1:
        audit.errors.append("incomplete_cli_lifecycle")
    if any(state != "completed" for _, state in item_states.values()):
        audit.errors.append("incomplete_cli_item")
    audit.errors = sorted(set(audit.errors))
    return audit


class RelayDriver:
    def __init__(self, config: DriverConfig):
        self.config = config
        self.queue = Path(config.queue).expanduser().resolve()
        self.started_at = time.time()
        # A restarted driver never picks up a previous process/run's packets.
        self.existing_requests = {path.name for path in self.queue.glob("req_*.request.json")}

    def _admit(self, path: Path) -> tuple[dict[str, Any], bytes] | None:
        self.config.validate()
        rows = read_ledger(self.queue)
        request_id = path.name.removesuffix(".request.json")
        seen_ids = {row.get("request_id") for row in rows}
        if path.name in self.existing_requests or request_id in seen_ids:
            return None
        if (self.queue / f"{request_id}.response.json").exists():
            return None
        if used_calls(rows) >= self.config.manager_limit:
            raise RelayError("manager_budget_exhausted")
        current_rows = [row for row in rows if row.get("run_id") == self.config.run_id]
        finished_ids = {row.get("request_id") for row in current_rows if row["event"] == "submitted"}
        if any(row["event"] == "cli_started" and row.get("request_id") not in finished_ids for row in current_rows):
            raise RelayError("run_has_failed_or_unconfirmed_attempt")
        if not REQUEST_ID.fullmatch(request_id) or path.parent.resolve() != self.queue or path.is_symlink():
            raise RelayError("invalid_request_path")
        try:
            raw = path.read_bytes()
            packet = _load_json(raw)
        except (OSError, UnicodeError, ValueError) as exc:
            raise RelayError("invalid_request_json") from exc
        if not isinstance(packet, dict) or packet.get("schema") != RELAY_SCHEMA or packet.get("request_id") != request_id:
            raise RelayError("invalid_request_identity")
        if packet.get("manager_transport") is not True or packet.get("independent_review_evidence") is not False or packet.get("authority") is not False:
            raise RelayError("request_is_not_manager_transport")
        created = packet.get("created_at_unix")
        if not isinstance(created, (float, int)) or isinstance(created, bool) or not math.isfinite(created):
            raise RelayError("invalid_request_timestamp")
        if created < self.started_at:
            return None
        if created > time.time() + 5:
            raise RelayError("request_timestamp_in_future")
        if time.time() >= created + RELAY_LIFETIME_SECONDS - PUBLISH_RESERVE_SECONDS:
            raise RelayError("request_deadline_exhausted")
        body = packet.get("request")
        messages = body.get("messages") if isinstance(body, dict) else None
        if not isinstance(messages, list) or not messages or any(
            not isinstance(message, dict)
            or message.get("role") not in {"system", "developer", "user", "assistant"}
            or not isinstance(message.get("content"), str)
            or message.get("tool_calls")
            for message in messages
        ):
            raise RelayError("unsupported_request_messages")
        if body.get("tools") or body.get("functions"):
            raise RelayError("tool_requests_are_not_supported")
        metadata = body.get("metadata")
        declared_runs = [packet.get("run_id")]
        if isinstance(metadata, dict):
            declared_runs.append(metadata.get("run_id"))
        if any(value is not None and value != self.config.run_id for value in declared_runs):
            raise RelayError("request_run_id_mismatch")
        for suffix in ("assistant.txt", "cli-events.jsonl"):
            if (self.queue / "worker-output" / f"{request_id}.{suffix}").exists():
                raise RelayError("request_artifact_already_exists")
        # The fixed wrapper identifies transport intent, not a semantic rubric.
        # Every supplied role/content value remains unchanged inside the array.
        prompt = TRANSPORT_INSTRUCTION.encode("utf-8") + json_bytes(messages)
        return {
            "schema": SCHEMA, "sequence": used_calls(rows) + 1,
            "request_id": request_id, "request_sha256": sha256(raw),
            "request_bytes": len(raw), "request_created_at_unix": created,
            "run_id": self.config.run_id,
            "source_snapshot_sha256": self.config.source_snapshot_sha256,
            "run_binding": "operator_supplied_with_start_fence",
            "host_provider": "codex_cli", "manager_transport_only": True,
            "independent_review_evidence": False, "authority": False,
            "prompt_sha256": sha256(prompt), "prompt_bytes": len(prompt),
        }, prompt

    def _record(self, base: dict[str, Any], event: str, **fields: Any) -> None:
        _append(self.queue, {
            **base, "event": event, "recorded_unix": time.time(), **fields,
        })

    def _execute(self, base: dict[str, Any], prompt: bytes) -> dict[str, Any]:
        request_id = base["request_id"]
        output_relative = f"worker-output/{request_id}.assistant.txt"
        events_relative = f"worker-output/{request_id}.cli-events.jsonl"
        output_path = self.queue / output_relative
        events_path = self.queue / events_relative
        output_path.parent.mkdir(exist_ok=True)
        if output_path.parent.resolve() != self.queue / "worker-output":
            raise RelayError("artifact_directory_is_not_queue_owned")
        failures: list[str] = []
        stdout = stderr = b""
        output: bytes | None = None
        output_preserved = events_preserved = False
        process: Any = None
        response_info: dict[str, Any] = {}
        launched_at = time.time()
        deadline = base["request_created_at_unix"] + RELAY_LIFETIME_SECONDS
        worker_seconds = min(self.config.worker_seconds, deadline - launched_at - PUBLISH_RESERVE_SECONDS)
        if worker_seconds <= 0:
            raise RelayError("request_deadline_exhausted")
        with tempfile.TemporaryDirectory(prefix="quillframe-codex-cli-") as temp:
            cwd = Path(temp).resolve()
            framework_root = Path(__file__).resolve().parents[2]
            if (
                cwd.is_relative_to(self.queue) or cwd.is_relative_to(framework_root)
                or any((parent / ".git").exists() or (parent / "quillframe.toml").exists() for parent in (cwd, *cwd.parents))
            ):
                raise RelayError("temporary_cwd_is_not_project_free")
            temporary_output = cwd / "assistant.txt"
            command = cli_command(self.config, cwd, temporary_output)
            self._record(
                base, "cli_started", status="attempted", counts_against_budget=True,
                budget_count_after_start=base["sequence"], cli_binary=self.config.cli_binary,
                model=self.config.model, reasoning_effort=self.config.reasoning_effort,
                command_sha256=sha256(json_bytes(command)),
                output_file=output_relative, events_file=events_relative,
                worker_timeout_seconds=worker_seconds, started_unix=launched_at,
                fresh_process=True, project_free_cwd=True, os_isolation_attested=False,
            )
            monotonic_deadline = time.monotonic() + worker_seconds
            try:
                process = subprocess.Popen(
                    command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=str(cwd), env=child_environment(), shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
                )
                stdout, stderr = process.communicate(
                    input=prompt, timeout=max(0.001, monotonic_deadline - time.monotonic()),
                )
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                failures.append("cli_timeout" if isinstance(exc, subprocess.TimeoutExpired) else "cli_interrupted")
                if process is not None:
                    process.kill()
                    try:
                        stdout, stderr = process.communicate(timeout=2.0)
                    except subprocess.TimeoutExpired as drain:
                        stdout, stderr = drain.output or b"", drain.stderr or b""
                        failures.append("cli_termination_unconfirmed")
            except OSError:
                failures.append("cli_launch_or_io_failed")
            if process is not None and process.returncode != 0:
                failures.append("cli_nonzero_exit")
            audit = audit_events(stdout)
            failures.extend(audit.errors)
            if temporary_output.is_symlink():
                failures.append("cli_output_is_symlink")
            elif temporary_output.is_file():
                try:
                    output = temporary_output.read_bytes()
                    _exclusive_write(output_path, output)
                    output_preserved = True
                except OSError:
                    failures.append("cli_output_preservation_failed")
            else:
                failures.append("cli_output_missing")
            matches = output is not None and audit.final_message is not None and output == audit.final_message.encode("utf-8")
            if not matches:
                failures.append("cli_output_does_not_match_final_message")
            try:
                if output is None or not output.decode("utf-8").strip():
                    failures.append("cli_output_empty")
            except UnicodeError:
                failures.append("cli_output_not_utf8")
            try:
                _exclusive_write(events_path, audit.evidence)
                events_preserved = True
            except OSError:
                failures.append("cli_events_preservation_failed")
            if time.time() >= deadline - PUBLISH_RESERVE_SECONDS:
                failures.append("request_publish_deadline_exhausted")
            request_path = self.queue / f"{request_id}.request.json"
            try:
                if sha256(request_path.read_bytes()) != base["request_sha256"]:
                    failures.append("request_changed_during_execution")
            except OSError:
                failures.append("request_missing_after_execution")
            finished = {
                "status": "failed" if failures else "completed",
                "thread_id": audit.thread_id,
                "pid": process.pid if process is not None else None,
                "returncode": process.returncode if process is not None else None,
                "usage": audit.usage,
                "events_file": events_relative if events_preserved else None,
                "events_sha256": sha256(audit.evidence) if events_preserved else None,
                "stdout_sha256": sha256(stdout), "stdout_bytes": len(stdout),
                "stderr_sha256": sha256(stderr), "stderr_bytes": len(stderr),
                "output_file": output_relative if output_preserved else None,
                "output_sha256": sha256(output) if output is not None else None,
                "output_bytes": len(output) if output is not None else None,
                "output_matches_final_message": matches,
                "forbidden_event_count": audit.forbidden_event_count,
                "failure_codes": sorted(set(failures)),
                "elapsed_since_request_seconds": time.time() - base["request_created_at_unix"],
                "elapsed_worker_seconds": time.time() - launched_at,
            }
            # Durable process identity and sanitized evidence precede the only
            # publication Core can consume. Publication failure is a distinct,
            # uncharged event; it cannot rewrite the process's actual outcome.
            self._record(base, "cli_finished", **finished)
            if not failures and output is not None:
                # Match the relay envelope without read_text's CRLF conversion,
                # semantic JSON reserialization, output trimming or replacement.
                response_path = self.queue / f"{request_id}.response.json"
                raw_response = json_bytes({
                    "schema": RELAY_SCHEMA, "request_id": request_id,
                    "content": output.decode("utf-8"),
                    "usage": audit.usage,
                }) + b"\n"
                try:
                    if time.time() >= deadline - PUBLISH_RESERVE_SECONDS:
                        raise RelayError("request_publish_deadline_exhausted")
                    _exclusive_write(response_path, raw_response)
                    response_bytes = response_path.read_bytes()
                    response = _load_json(response_bytes)
                    exact = response.get("content", "").encode("utf-8") == output
                    if not exact:
                        failures.append("published_response_changed")
                    if time.time() >= deadline:
                        failures.append("response_published_after_deadline")
                    response_info = {
                        "response_file": response_path.name,
                        "response_file_sha256": sha256(response_bytes),
                        "response_content_exact_match": exact,
                        "response_written_unix": response_path.stat().st_mtime,
                        "response_elapsed_seconds": response_path.stat().st_mtime - base["request_created_at_unix"],
                    }
                except RelayError as exc:
                    failures.append(str(exc))
                except (OSError, ValueError, UnicodeError):
                    failures.append("response_publication_failed_or_already_exists")
                if failures:
                    self._record(base, "submission_failed", status="failed", failure_codes=sorted(set(failures)), **response_info)
                else:
                    self._record(
                        base, "submitted", status="submitted", thread_id=audit.thread_id,
                        output_file=output_relative, output_sha256=sha256(output), output_bytes=len(output),
                        elapsed_since_request_seconds=time.time() - base["request_created_at_unix"],
                        **response_info,
                    )
            return {**base, **finished, "status": "failed" if failures else "submitted", "failure_codes": sorted(set(failures))}

    def process_request(self, path: Path) -> dict[str, Any] | None:
        """Execute at most one new packet. Tests replace subprocess.Popen."""
        self.config.validate()
        self.queue.mkdir(parents=True, exist_ok=True)
        with driver_lock(self.queue):
            admitted = self._admit(Path(path))
            return self._execute(*admitted) if admitted is not None else None

    def serve(
        self, *, expected_used: int | None = None, idle_seconds: float = 60.0,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        self.config.validate()
        if not math.isfinite(idle_seconds) or idle_seconds <= 0:
            raise RelayError("invalid_idle_timeout")
        self.queue.mkdir(parents=True, exist_ok=True)
        emit = on_event or (lambda _event: None)
        with driver_lock(self.queue):
            count = used_calls(read_ledger(self.queue))
            if expected_used is not None and expected_used != count:
                raise RelayError("ledger_budget_does_not_match_expected_used")
            emit({"event": "driver_ready", "used_calls": count, "run_id": self.config.run_id, "accept_after_unix": self.started_at})
            idle_until = time.monotonic() + idle_seconds
            while time.monotonic() < idle_until:
                for path in sorted(self.queue.glob("req_*.request.json")):
                    admitted = self._admit(path)
                    if admitted is None:
                        continue
                    result = self._execute(*admitted)
                    emit(result)
                    if result["status"] != "submitted":
                        return result
                    idle_until = time.monotonic() + idle_seconds
                time.sleep(min(0.5, max(0.0, idle_until - time.monotonic())))
            return {"status": "idle_stopped", "used_calls": used_calls(read_ledger(self.queue)), "run_id": self.config.run_id}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="explicitly authorize fresh CLI manager workers")
    serve.add_argument("--queue", type=Path, required=True)
    serve.add_argument("--cli-binary", required=True)
    serve.add_argument("--run-id", required=True)
    serve.add_argument("--source-snapshot-sha256", required=True)
    serve.add_argument("--model", required=True)
    serve.add_argument("--reasoning-effort", choices=("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"), default="xhigh")
    serve.add_argument("--allow-model-execution", action="store_true")
    serve.add_argument("--manager-limit", type=int, default=MANAGER_CALL_LIMIT)
    serve.add_argument("--worker-seconds", type=float, default=MAX_WORKER_SECONDS)
    serve.add_argument("--expected-used", type=int)
    serve.add_argument("--idle-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        driver = RelayDriver(DriverConfig(
            queue=args.queue, cli_binary=args.cli_binary, run_id=args.run_id,
            source_snapshot_sha256=args.source_snapshot_sha256, model=args.model,
            reasoning_effort=args.reasoning_effort, allow_model_execution=args.allow_model_execution,
            manager_limit=args.manager_limit, worker_seconds=args.worker_seconds,
        ))
        result = driver.serve(
            expected_used=args.expected_used, idle_seconds=args.idle_seconds,
            on_event=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True),
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 1 if result["status"] == "failed" else 0
    except (RelayError, OSError) as exc:
        print(json.dumps({"status": "stopped", "error": str(exc) if isinstance(exc, RelayError) else "driver_filesystem_error"}), flush=True)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
