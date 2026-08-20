#!/usr/bin/env python3
"""Native Quillframe 1.0 acceptance contract.

The module is deliberately boring and explicit. It validates evidence produced by
fixed commands and independently-owned browser/external receipts, it never runs a
caller-supplied command and it does not promise multi-file atomicity.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "1.0.0-dev.0"
REPORT_SCHEMA = "quillframe_release_acceptance_report_v1"
EVIDENCE_SCHEMA = "quillframe_acceptance_evidence_v1"
T605_SCHEMA = "quillframe_browser_acceptance_v1"
T310_SCHEMA = "quillframe_local_browser_acceptance_v1"
T608_PROVISIONAL = "~"
T608_FINAL = "x"
JSON_SELF_HASH_POLICY = "excluded_by_contract"
SHA64 = re.compile(r"^[0-9a-f]{64}$")
SHA_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
SECRET_KEY = re.compile(r"(?:token|secret|password|credential|private[_-]?key|api[_-]?key|authorization|cookie)", re.I)
SAFE_METADATA_KEYS = frozenset({"credentials_used"})
SECRET_VALUE = re.compile(r"(?:Bearer\s+(?!\[REDACTED(?:_[A-Z]+)?\])\S+|-----BEGIN [^-]+-----|(?<![A-Za-z0-9])(?:sk[-_][A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_-]{8,}|xox[-_][A-Za-z0-9_-]{8,}|AIza[A-Za-z0-9_-]{16,}|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)|(?:authorization|cookie|x-api-key)\s*[:=]\s*(?!\[REDACTED(?:_[A-Z]+)?\])\S+)", re.I)
ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/home/|/var/|/tmp/|/private/|/workspace/|/opt/|[A-Za-z]:[\\/]|\\\\)")
DIAGNOSTIC_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/[^\s]+|[A-Za-z]:[\\/][^\s]+|\\\\[^\s]+)")

REPORT_KEYS = {
    "schema", "framework_version", "generated_at", "acceptance_subject",
    "evidence_fingerprint", "status", "release_promotion_authorized",
    "deployment_performed", "model_execution_performed", "gates",
    "local_evidence", "blocking_evidence", "environment_limited_checks",
    "task_ledger", "rendered_artifacts",
}
EVIDENCE_KEYS = {
    "schema", "framework_version", "generated_at", "acceptance_subject",
    "evidence_fingerprint", "commands", "browser_manifests",
    "external_evidence", "environment_limited_checks",
}
MARKDOWN_NAMES = (
    f"{VERSION}.en.md",
    f"{VERSION}.zh-CN.md",
    f"{VERSION}.tasks.en.md",
    f"{VERSION}.tasks.zh-CN.md",
)
CANONICAL_OUTPUT_NAMES = frozenset((*MARKDOWN_NAMES, f"{VERSION}.json"))
DERIVED_OUTPUT_RELATIVE = frozenset(f"release/acceptance/{name}" for name in CANONICAL_OUTPUT_NAMES)
BUILD_INPUT_RELATIVE = ("package.json", "pnpm-lock.yaml", "site/package.json", "studio/app/package.json", "cloud/package.json")


class AcceptanceError(ValueError):
    """A fail-closed contract or evidence error."""


@dataclasses.dataclass(frozen=True)
class GateSpec:
    gate_id: str
    kind: str
    command_name: str | None
    argv: tuple[str, ...]
    cwd: str
    timeout_ms: int
    predicate: str


@dataclasses.dataclass(frozen=True)
class RunnerCommand:
    name: str
    argv: tuple[str, ...]
    timeout_ms: int
    gate_ids: tuple[str, ...]


def _task_ids() -> tuple[str, ...]:
    return tuple(
        [f"T{i:03d}" for i in range(5)]
        + [f"T{i:03d}" for i in range(100, 109)]
        + [f"T{i:03d}" for i in range(200, 209)]
        + [f"T{i:03d}" for i in range(300, 311)]
        + [f"T{i:03d}" for i in range(400, 410)]
        + [f"T{i:03d}" for i in range(500, 504)]
        + [f"T{i:03d}" for i in range(600, 609)]
    )


CANONICAL_TASK_IDS = _task_ids()
EXTERNAL_TASKS = frozenset({"T409", "T606", "T607"})
DERIVED_GATES = frozenset({"T607.derived", "T608.final_readback"})


def _runner_commands() -> tuple[RunnerCommand, ...]:
    return (
        RunnerCommand("version_consistency", ("python", "scripts/version_consistency.py"), 180_000, ("G6.version_consistency",)),
        RunnerCommand("identity", ("python", "scripts/version_identity.py"), 180_000, ("G0.scope",)),
        RunnerCommand("docs", ("python", "scripts/docs_quality.py"), 300_000, ("G0.spec", "G0.research", "G3.docs")),
        RunnerCommand("hygiene", ("python", "quality/clean_break.py"), 300_000, ("G1.reject", "G5.clean_break", "G5.no_compat")),
        RunnerCommand("peer_contract", ("python", "scripts/peer_bridge_contract.py"), 300_000, ("G1.bridge",)),
        RunnerCommand("namespace", ("python", "scripts/namespace_hygiene.py"), 180_000, ("G0.yaml",)),
        RunnerCommand("machine_namespace", ("python", "scripts/machine_namespace_hygiene.py"), 180_000, ("G6.machine_namespace",)),
        RunnerCommand("framework_hygiene", ("python", "scripts/framework_hygiene.py"), 300_000, ("G6.framework_hygiene",)),
        RunnerCommand("quillframe_docs_quality", ("python", "scripts/quillframe_docs_quality.py"), 300_000, ("G6.quillframe_docs_quality",)),
        RunnerCommand("design_system_quality", ("python", "scripts/design_system_quality.py"), 300_000, ("G6.design_system_quality",)),
        RunnerCommand("semantic_reference_integrity", ("python", "scripts/semantic_reference_integrity.py"), 300_000, ("G6.semantic_reference_integrity",)),
        RunnerCommand("python_compile", ("python", "-m", "compileall", "-q", "agent_runtime", "corpus", "evals", "harness", "learning", "model_runtime", "persistence", "production_runtime", "publication", "quality", "quillframe", "release", "studio", "core_operations.py", "project_resolution.py", "quillframe.py"), 600_000, ("G0.plan", "G1.schema", "G2.types", "G6.python_compile")),
        RunnerCommand(
            "python_full",
            ("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"),
            1_200_000,
            (
                "G1.resume", "G1.subscription", "G1.mcp", "G1.launch",
                "G2.workflow", "G2.replay", "G2.pause", "G2.invalidation",
                "G2.budget", "G2.model", "G2.fallback", "G4.cloud_tests",
                "G5.fixture", "G6.python_full",
            ),
        ),
        RunnerCommand("framework_selftest", ("python", "quillframe.py", "self-test"), 1_200_000, ("G2.bridge", "G6.selftest")),
        RunnerCommand("bundle_build", ("python", "release/build_framework_bundle.py", "build", "--root", ".", "--output", "{OUTPUT}/framework-bundle.tar", "--report", "{OUTPUT}/bundle-build.json"), 600_000, ("G6.bundle_build",)),
        RunnerCommand("bundle_verify", ("python", "release/build_framework_bundle.py", "verify", "--bundle", "{OUTPUT}/framework-bundle.tar", "--report", "{OUTPUT}/bundle-verify.json"), 600_000, ("G6.bundle_verify",)),
        RunnerCommand("pnpm_frozen", ("corepack", "pnpm", "install", "--frozen-lockfile", "--store-dir", "{OUTPUT}/pnpm-store"), 1_800_000, ("G1.workspace", "G6.pnpm")),
        RunnerCommand("quality", ("corepack", "pnpm", "run", "quality"), 1_200_000, ("G1.tooling", "G5.quality", "G6.quality")),
        RunnerCommand("test", ("corepack", "pnpm", "run", "test"), 1_200_000, ("G3.fixture", "G3.states", "G6.node_test")),
        RunnerCommand("typecheck", ("corepack", "pnpm", "run", "typecheck"), 1_200_000, ("G6.typecheck",)),
        RunnerCommand("build", ("corepack", "pnpm", "run", "build"), 1_800_000, ("G3.studio", "G3.homepage", "G3.demo", "G6.build")),
        RunnerCommand("wheel_build", ("python", "-m", "pip", "wheel", ".", "--no-deps", "--wheel-dir", "{OUTPUT}/wheel"), 900_000, ("G6.wheel_build",)),
        RunnerCommand("wheel_install_smoke", ("python", "-m", "pip", "install", "--no-deps", "--target", "{OUTPUT}/wheel-smoke", "{WHEEL}"), 900_000, ("G6.wheel_smoke",)),
        RunnerCommand("wheel_import_smoke", ("python", "-c", "import sys\nsys.path.insert(0, '{OUTPUT}/wheel-smoke')\nimport quillframe\nprint(quillframe.__name__)"), 300_000, ("G6.wheel_import",)),
        RunnerCommand("t603_site_smoke", ("corepack", "pnpm", "--filter", "@quillframe/product-site", "browser:smoke"), 1_800_000, ("R.t603.site_smoke",)),
        RunnerCommand("t603_studio_smoke", ("corepack", "pnpm", "--filter", "@quillframe/studio-app", "browser:smoke"), 1_800_000, ("R.t603.studio_smoke",)),
        RunnerCommand("t603_local_launch", ("corepack", "pnpm", "--filter", "@quillframe/studio-app", "browser:launch"), 1_800_000, ("G3.launch", "G3.project", "G3.loopback", "G3.cloud_opt_in", "R.t603.launch_smoke")),
        RunnerCommand("cloud_security", ("corepack", "pnpm", "--filter", "@quillframe/cloud", "test"), 900_000, ("G4.bff", "G4.auth", "G4.security", "G4.coordinator", "G4.vault", "G4.persistence", "G4.container", "G4.endpoint", "G4.redaction", "G6.cloud")),
        RunnerCommand("t605_browser", ("corepack", "pnpm", "--filter", "@quillframe/product-site", "browser:acceptance:t605"), 1_800_000, ("G6.t605_invoke",)),
    )


RUNNER_COMMANDS = _runner_commands()
COMMAND_RECORD_KEYS = frozenset({"id", "gate_id", "subject", "subject_after", "started_at", "finished_at", "result", "artifacts", "argv", "cwd", "timeout_ms", "exit_code", "predicate"})


def _gate(gate_id: str, kind: str = "command", command_name: str | None = None, predicate: str | None = None) -> GateSpec:
    command = next((item for item in RUNNER_COMMANDS if item.name == command_name), None)
    if kind == "command":
        if command is None:
            raise RuntimeError(f"unknown runner command: {command_name}")
        argv = command.argv
        timeout = command.timeout_ms
    else:
        argv = ()
        timeout = 0
    return GateSpec(gate_id, kind, command_name, argv, "repo", timeout, predicate or gate_id)


def _build_gates() -> dict[str, GateSpec]:
    pairs = {
        "G0.scope": "identity", "G0.spec": "docs", "G0.plan": "python_compile", "G0.research": "docs", "G0.yaml": "namespace",
        "G1.workspace": "pnpm_frozen", "G1.tooling": "quality", "G1.schema": "python_compile", "G1.bridge": "peer_contract", "G1.resume": "python_full", "G1.subscription": "python_full", "G1.mcp": "python_full", "G1.reject": "hygiene", "G1.launch": "python_full",
        "G2.workflow": "python_full", "G2.types": "python_compile", "G2.replay": "python_full", "G2.pause": "python_full", "G2.invalidation": "python_full", "G2.budget": "python_full", "G2.model": "python_full", "G2.fallback": "python_full", "G2.bridge": "framework_selftest",
        "G3.launch": "t603_local_launch", "G3.project": "t603_local_launch", "G3.loopback": "t603_local_launch", "G3.cloud_opt_in": "t603_local_launch", "G3.studio": "build", "G3.homepage": "build", "G3.demo": "build", "G3.fixture": "test", "G3.docs": "docs", "G3.states": "test",
        "G4.bff": "cloud_security", "G4.auth": "cloud_security", "G4.security": "cloud_security", "G4.coordinator": "cloud_security", "G4.vault": "cloud_security", "G4.persistence": "cloud_security", "G4.container": "cloud_security", "G4.endpoint": "cloud_security", "G4.redaction": "cloud_security",
        "G5.clean_break": "hygiene", "G5.fixture": "python_full", "G5.quality": "quality", "G5.no_compat": "hygiene",
        "G6.version_consistency": "version_consistency", "G6.machine_namespace": "machine_namespace", "G6.framework_hygiene": "framework_hygiene", "G6.quillframe_docs_quality": "quillframe_docs_quality", "G6.design_system_quality": "design_system_quality", "G6.semantic_reference_integrity": "semantic_reference_integrity",
        "G6.python_compile": "python_compile", "G6.python_full": "python_full", "G6.selftest": "framework_selftest", "G6.bundle_build": "bundle_build", "G6.bundle_verify": "bundle_verify", "G6.pnpm": "pnpm_frozen", "G6.quality": "quality", "G6.node_test": "test", "G6.typecheck": "typecheck", "G6.build": "build", "G6.wheel_build": "wheel_build", "G6.wheel_smoke": "wheel_install_smoke", "G6.wheel_import": "wheel_import_smoke", "G6.cloud": "cloud_security", "G6.t605_invoke": "t605_browser",
        "R.t603.site_smoke": "t603_site_smoke", "R.t603.studio_smoke": "t603_studio_smoke", "R.t603.launch_smoke": "t603_local_launch",
    }
    result = {gate_id: _gate(gate_id, command_name=command_name) for gate_id, command_name in pairs.items()}
    result["T310.browser.local"] = _gate("T310.browser.local", "browser_manifest")
    result["T605.browser.full"] = _gate("T605.browser.full", "browser_manifest")
    result["T409.external"] = _gate("T409.external", "external")
    result["T606.external"] = _gate("T606.external", "external")
    result["T607.approval"] = _gate("T607.approval", "external")
    result["T607.derived"] = _gate("T607.derived", "derived")
    result["T608.final_readback"] = _gate("T608.final_readback", "derived")
    return result


GATES = _build_gates()
GATES["T102.schema.catalog"] = _gate("T102.schema.catalog", command_name="python_compile", predicate="canonical schema catalog and validator")
GATES["G4.cloud_tests"] = _gate("G4.cloud_tests", command_name="python_full", predicate="hosted deterministic cloud contract tests")


def _requirements() -> dict[str, tuple[str, ...]]:
    values = {
        "T000": ("G0.scope",), "T001": ("G0.spec",), "T002": ("G0.plan",), "T003": ("G0.research",), "T004": ("G0.yaml",),
        "T100": ("G1.workspace",), "T101": ("G1.tooling",), "T102": ("G1.schema",), "T103": ("G1.bridge",), "T104": ("G1.resume",), "T105": ("G1.subscription",), "T106": ("G1.mcp",), "T107": ("G1.reject",), "T108": ("G1.launch",),
        "T200": ("G2.workflow",), "T201": ("G2.types",), "T202": ("G2.replay",), "T203": ("G2.pause",), "T204": ("G2.invalidation",), "T205": ("G2.budget",), "T206": ("G2.model",), "T207": ("G2.fallback",), "T208": ("G2.bridge",),
        "T300": ("G3.launch",), "T301": ("G3.project",), "T302": ("G3.loopback",), "T303": ("G3.cloud_opt_in",), "T304": ("G3.studio",), "T305": ("G3.homepage",), "T306": ("G3.demo",), "T307": ("G3.fixture",), "T308": ("G3.docs",), "T309": ("G3.states",), "T310": ("T310.browser.local",),
        "T400": ("G4.bff",), "T401": ("G4.auth",), "T402": ("G4.security",), "T403": ("G4.coordinator",), "T404": ("G4.vault",), "T405": ("G4.persistence",), "T406": ("G4.container",), "T407": ("G4.endpoint",), "T408": ("G4.redaction",), "T409": ("T409.external",),
        "T500": ("G5.clean_break",), "T501": ("G5.fixture",), "T502": ("G5.quality",), "T503": ("G5.no_compat",),
        "T600": ("G6.python_compile", "G6.python_full", "G6.selftest"), "T601": ("G6.pnpm", "G6.node_test", "G6.typecheck", "G6.build", "G6.wheel_build", "G6.wheel_smoke", "G6.wheel_import"), "T602": ("G5.clean_break", "G1.reject", "G6.version_consistency", "G6.machine_namespace", "G6.framework_hygiene", "G6.quillframe_docs_quality", "G6.design_system_quality", "G6.semantic_reference_integrity"), "T603": ("T310.browser.local", "G3.demo", "G3.loopback"), "T604": ("G6.cloud",), "T605": ("T605.browser.full",), "T606": ("T606.external",), "T607": ("T409.external", "T606.external", "T607.approval", "T607.derived"), "T608": ("T608.final_readback",),
    }
    if tuple(values) != CANONICAL_TASK_IDS:
        raise RuntimeError("task mapping drift")
    return values


TASK_REQUIREMENTS = _requirements()


def parse_json(text: str) -> Any:
    def object_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise AcceptanceError("duplicate JSON key")
            value[key] = item
        return value

    try:
        return json.loads(text, object_pairs_hook=object_pairs, parse_constant=lambda _: (_ for _ in ()).throw(AcceptanceError("non-finite JSON")))
    except AcceptanceError:
        raise
    except Exception as exc:
        raise AcceptanceError("invalid JSON") from exc


def exact(value: Any, keys: set[str], where: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise AcceptanceError(f"{where}: exact keys")


def _relative_parts(value: Any) -> tuple[str, ...]:
    if type(value) is not str or not value or "\x00" in value or "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise AcceptanceError("relative path")
    parts = tuple(value.split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        raise AcceptanceError("relative path component")
    return parts


def _safe_root(root: Path) -> Path:
    try:
        fd = _open_directory_chain(root.absolute(), create=False)
    except (OSError, AcceptanceError) as exc:
        raise AcceptanceError("evidence root") from exc
    os.close(fd)
    return root


def _open_directory_chain(path: Path, create: bool) -> int:
    """Open every directory component with O_NOFOLLOW, optionally creating it."""
    absolute = path.absolute()
    if not absolute.is_absolute():
        raise AcceptanceError("directory path")
    current = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in absolute.parts[1:]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=current)
                except FileExistsError:
                    pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = child
        return current
    except Exception:
        os.close(current)
        raise


def _open_relative(root: Path, relative: str, flags: int = os.O_RDONLY) -> int:
    _safe_root(root)
    parts = _relative_parts(relative)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    current = root_fd
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            if current != root_fd:
                os.close(current)
            current = child
        final_fd = os.open(parts[-1], flags | os.O_NOFOLLOW, dir_fd=current)
        if current != root_fd:
            os.close(current)
        os.close(root_fd)
        return final_fd
    except Exception:
        if current != root_fd:
            os.close(current)
        os.close(root_fd)
        raise


def _signature(value: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _descriptor_digest(value: str) -> str:
    if SHA64.fullmatch(value):
        return value
    if SHA_PREFIXED.fullmatch(value):
        return value[7:]
    raise AcceptanceError("sha256 descriptor")


def read_descriptor(descriptor: dict[str, Any], root: Path) -> bytes:
    exact(descriptor, {"path", "size", "sha256", "role"}, "artifact")
    if type(descriptor["size"]) is not int or isinstance(descriptor["size"], bool) or descriptor["size"] < 0 or descriptor["size"] > 64 * 1024 * 1024 or type(descriptor["role"]) is not str:
        raise AcceptanceError("artifact types")
    expected_hash = _descriptor_digest(descriptor["sha256"])
    try:
        fd = _open_relative(root, descriptor["path"])
    except (OSError, AcceptanceError) as exc:
        raise AcceptanceError("artifact open") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise AcceptanceError("artifact regular singleton")
        first = os.pread(fd, before.st_size, 0)
        middle = os.fstat(fd)
        second = os.pread(fd, middle.st_size, 0)
        after = os.fstat(fd)
        if _signature(before) != _signature(middle) or _signature(middle) != _signature(after) or first != second:
            raise AcceptanceError("artifact changed during read")
        if len(second) != descriptor["size"] or hashlib.sha256(second).hexdigest() != expected_hash:
            raise AcceptanceError("artifact digest")
        return second
    finally:
        os.close(fd)


def read_owned(path: Path, require_single_link: bool = True) -> dict[str, Any]:
    parent = path.parent
    fd = _open_relative(parent, path.name)
    try:
        value = os.fstat(fd)
        if not stat.S_ISREG(value.st_mode) or (require_single_link and value.st_nlink != 1):
            raise AcceptanceError("owned target not regular")
        data = os.pread(fd, value.st_size, 0)
        return {"dev": value.st_dev, "ino": value.st_ino, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    finally:
        os.close(fd)


def safe_text(value: str) -> str:
    if SECRET_VALUE.search(value):
        raise AcceptanceError("secret in evidence")
    if ABSOLUTE_PATH.search(value):
        raise AcceptanceError("absolute path in evidence")
    return value


def redact_text(value: str, secret_values: Iterable[str] = ()) -> str:
    for secret in sorted({item for item in secret_values if type(item) is str and len(item) >= 4}, key=len, reverse=True):
        value = value.replace(secret, "[REDACTED_ENV]")
    value = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", value, flags=re.I)
    value = re.sub(r"((?:^|[?&\s])(?:token|secret|code|state|password)=)[^&\s]+", r"\1[REDACTED]", value, flags=re.I)
    value = re.sub(r"((?:authorization|proxy-authorization|cookie|set-cookie|x-api-key)\s*[:=])[^\r\n]+", r"\1 [REDACTED]", value, flags=re.I)
    value = re.sub(r"(https?://)([^/\s:@]+)(?::[^/\s@]*)?@", r"\1[REDACTED]@", value, flags=re.I)
    value = re.sub(r"\b(?:sk[-_][A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_-]{8,}|xox[-_][A-Za-z0-9_-]{8,}|AIza[A-Za-z0-9_-]{16,})\b", "[REDACTED_TOKEN]", value, flags=re.I)
    value = re.sub(r"\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[REDACTED_JWT]", value)
    value = re.sub(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", "[REDACTED_KEY]", value, flags=re.I | re.S)
    value = re.sub(r"(?<!\S)/(?:[^\s]+)", "[REDACTED_PATH]", value)
    value = re.sub(r"(?<!\S)(?:[A-Za-z]:[\\/]|\\\\)[^\s]+", "[REDACTED_PATH]", value)
    return value


def _scan_safe(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str or (SECRET_KEY.search(key) and key not in SAFE_METADATA_KEYS):
                raise AcceptanceError("secret key")
            _scan_safe(item)
    elif isinstance(value, list):
        for item in value:
            _scan_safe(item)
    elif isinstance(value, str):
        safe_text(value)


def read_json_descriptor(root: Path, relative: str) -> Any:
    raw = read_file_bytes(root, relative, 8 * 1024 * 1024, require_single_link=True)
    try:
        parsed = parse_json(raw.decode("utf-8"))
        _scan_safe(parsed)
        return parsed
    except UnicodeDecodeError as exc:
        raise AcceptanceError("JSON encoding") from exc


def read_file_bytes(root: Path, relative: str, limit: int = 64 * 1024 * 1024, require_single_link: bool = True) -> bytes:
    try:
        fd = _open_relative(root, relative)
    except (OSError, AcceptanceError) as exc:
        raise AcceptanceError("file open") from exc
    try:
        value = os.fstat(fd)
        if not stat.S_ISREG(value.st_mode) or (require_single_link and value.st_nlink != 1):
            raise AcceptanceError("file regular singleton")
        if value.st_size > limit:
            raise AcceptanceError("file too large")
        first = os.pread(fd, value.st_size, 0)
        middle = os.fstat(fd)
        second = os.pread(fd, middle.st_size, 0)
        after = os.fstat(fd)
        if _signature(value) != _signature(middle) or _signature(middle) != _signature(after) or first != second:
            raise AcceptanceError("file changed during read")
        return first
    finally:
        os.close(fd)


def validate_subject(value: Any) -> None:
    exact(value, {"kind", "base_commit", "current_commit", "chapter_scope", "version", "dirty", "working_tree_fingerprint", "build_fingerprint", "untracked_paths", "project_id", "candidate_id"}, "subject")
    if value["kind"] not in {"clean_checkout", "uncommitted_working_tree"} or not SHA40.fullmatch(value["base_commit"]) or not SHA40.fullmatch(value["current_commit"]) or value["chapter_scope"] != "CH001" or value["version"] != VERSION or type(value["dirty"]) is not bool or not SHA64.fullmatch(value["working_tree_fingerprint"]) or not SHA64.fullmatch(value["build_fingerprint"]):
        raise AcceptanceError("subject identity")
    if type(value["untracked_paths"]) is not list or any(type(item) is not str or not item for item in value["untracked_paths"]):
        raise AcceptanceError("subject untracked paths")
    if type(value["project_id"]) is not str or type(value["candidate_id"]) is not str:
        raise AcceptanceError("subject project identity")


def _tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode() + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _normalized_source_commit(repo: Path) -> tuple[str, str]:
    """Return ``(attestation-normalized HEAD, merge-base)``.

    A generated acceptance artifact commit is allowed to attest the source
    commit immediately before it, but only when its complete diff is exactly
    the five canonical derived outputs.  This is deliberately one hop: a
    source change or a second chained attestation remains the literal HEAD.
    """
    head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=repo, text=True).strip()
    parents = subprocess.check_output(("git", "rev-list", "--parents", "-n", "1", "HEAD"), cwd=repo, text=True).strip().split()
    if len(parents) != 2:
        return head, head
    changed = subprocess.check_output(("git", "diff-tree", "--no-commit-id", "--name-only", "-r", parents[1], head), cwd=repo, text=True).splitlines()
    if set(changed) == DERIVED_OUTPUT_RELATIVE and len(changed) == len(DERIVED_OUTPUT_RELATIVE):
        return parents[1], parents[1]
    return head, head


def build_input_fingerprint(repo: Path, commit: str) -> str:
    digest = hashlib.sha256()
    version = (repo / "VERSION").read_text().strip()
    digest.update(commit.encode() + b"\0" + version.encode() + b"\0")
    for relative in BUILD_INPUT_RELATIVE:
        path = repo / relative
        if path.is_file() and not path.is_symlink():
            digest.update(relative.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def compute_subject(repo: Path) -> dict[str, Any]:
    commit, base_commit = _normalized_source_commit(repo)
    pathspecs = (".", *(f":(exclude){relative}" for relative in sorted(DERIVED_OUTPUT_RELATIVE)))
    status = subprocess.check_output(("git", "status", "--porcelain=v1", "--untracked-files=all", "--null", "--", *pathspecs), cwd=repo)
    paths = subprocess.check_output(("git", "ls-files", "--others", "--exclude-standard", "-z", "--", *pathspecs), cwd=repo).decode().split("\0")
    untracked = sorted(item for item in paths if item)
    digest = hashlib.sha256()
    listed = subprocess.check_output(("git", "ls-files", "-co", "--exclude-standard", "-z", "--", *pathspecs), cwd=repo).decode().split("\0")
    for relative in sorted(item for item in listed if item):
        if relative in DERIVED_OUTPUT_RELATIVE:
            continue
        path = repo / relative
        digest.update(relative.encode() + b"\0")
        if path.is_symlink():
            raise AcceptanceError("git subject symlink")
        elif not path.exists():
            digest.update(b"[DELETED]\0")
        elif not path.is_file():
            raise AcceptanceError("git subject nonregular")
        else:
            digest.update(path.read_bytes() + b"\0")
    version = (repo / "VERSION").read_text().strip()
    return {
        "kind": "uncommitted_working_tree" if status.strip(b"\0") else "clean_checkout",
        "base_commit": base_commit,
        "current_commit": commit,
        "chapter_scope": "CH001",
        "version": version,
        "dirty": bool(status.strip(b"\0")),
        "working_tree_fingerprint": digest.hexdigest(),
        "build_fingerprint": build_input_fingerprint(repo, commit),
        "untracked_paths": untracked,
        "project_id": "quillframe",
        "candidate_id": "CH001",
    }


def evidence_fingerprint(evidence: dict[str, Any]) -> str:
    body = {key: evidence[key] for key in ("schema", "framework_version", "generated_at", "acceptance_subject", "commands", "browser_manifests", "external_evidence", "environment_limited_checks")}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _timestamp(value: Any) -> None:
    if type(value) is not str or not TIMESTAMP.fullmatch(value):
        raise AcceptanceError("timestamp")


def _artifact_list(value: Any, root: Path, allow_empty: bool = False) -> None:
    if type(value) is not list or (not allow_empty and not value):
        raise AcceptanceError("artifact list")
    paths: set[str] = set()
    for item in value:
        if type(item) is not dict or type(item.get("path")) is not str or item.get("path") in paths:
            raise AcceptanceError("duplicate artifact")
        paths.add(item.get("path"))
        data = read_descriptor(item, root)
        if item.get("role") in {"stdout", "stderr", "diagnostic"}:
            try:
                public = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise AcceptanceError("diagnostic encoding") from exc
            if SECRET_VALUE.search(public) or DIAGNOSTIC_ABSOLUTE_PATH.search(public) or re.search(r"(?:https?://[^\s/@:]+:[^\s/@]+@|(?:authorization|cookie|x-api-key)\s*[:=]\s*(?!\[REDACTED(?:_[A-Z]+)?\])\S+)", public, re.I):
                raise AcceptanceError("secret in diagnostic artifact")


def _validate_record_shape(record: Any, bucket: str) -> None:
    common = {"id", "gate_id", "subject", "subject_after", "started_at", "finished_at", "result", "artifacts"}
    if bucket == "commands":
        expected = common | {"argv", "cwd", "timeout_ms", "exit_code", "predicate"}
    elif bucket == "browser_manifests":
        expected = common | {"manifest"}
    elif bucket == "external_evidence":
        expected = common | {"project_id", "candidate_id", "candidate_fingerprint", "receipt_fingerprint", "target_identity", "approval", "proof"}
    else:
        expected = {"id", "status", "reason", "owner"}
    exact(record, expected, bucket)


def validate_record(record: dict[str, Any], bucket: str, subject: dict[str, Any], root: Path) -> None:
    _validate_record_shape(record, bucket)
    if bucket == "environment_limited_checks":
        if type(record["id"]) is not str or record["status"] not in {"not_run", "blocked"} or type(record["reason"]) is not str or type(record["owner"]) is not str:
            raise AcceptanceError("environment record")
        return
    if type(record["id"]) is not str or not record["id"] or record["subject"] != subject or record["subject_after"] != subject:
        raise AcceptanceError("record identity/subject")
    if record["result"] not in {"pass", "failed", "blocked", "awaiting"}:
        raise AcceptanceError("record result")
    _timestamp(record["started_at"])
    _timestamp(record["finished_at"])
    _artifact_list(record["artifacts"], root, allow_empty=record["result"] != "pass")
    gate_id = record["gate_id"]
    if type(gate_id) is not str or gate_id not in GATES:
        raise AcceptanceError("unknown gate")
    spec = GATES[gate_id]
    if bucket == "commands":
        if spec.kind != "command" or type(record["argv"]) is not list or tuple(record["argv"]) != spec.argv or record["cwd"] != spec.cwd or record["timeout_ms"] != spec.timeout_ms or type(record["exit_code"]) is not int or record["predicate"] != spec.predicate:
            raise AcceptanceError("fixed command gate")
        if record["result"] == "pass" and record["exit_code"] != 0:
            raise AcceptanceError("pass exit")
    elif bucket == "browser_manifests":
        if spec.kind != "browser_manifest" or record["result"] != "pass":
            raise AcceptanceError("browser gate bucket")
        if gate_id == "T605.browser.full":
            validate_t605_manifest(record["manifest"], subject, root)
        elif gate_id == "T310.browser.local":
            validate_local_browser_manifest(record["manifest"], subject, root)
        else:
            raise AcceptanceError("unknown browser gate")
    elif bucket == "external_evidence":
        if spec.kind != "external" or record["result"] != "pass":
            raise AcceptanceError("external gate bucket")
        _validate_external_record(record, subject, root)


def validate_evidence(evidence: Any, root: Path) -> dict[str, Any]:
    exact(evidence, EVIDENCE_KEYS, "evidence")
    if evidence["schema"] != EVIDENCE_SCHEMA or evidence["framework_version"] != VERSION:
        raise AcceptanceError("evidence schema/version")
    _timestamp(evidence["generated_at"])
    validate_subject(evidence["acceptance_subject"])
    if type(evidence["evidence_fingerprint"]) is not str or not SHA64.fullmatch(evidence["evidence_fingerprint"]):
        raise AcceptanceError("evidence fingerprint type")
    _scan_safe(evidence)
    seen: set[str] = set()
    seen_gates: set[str] = set()
    for bucket in ("commands", "browser_manifests", "external_evidence", "environment_limited_checks"):
        if type(evidence[bucket]) is not list:
            raise AcceptanceError("evidence bucket")
        for record in evidence[bucket]:
            if type(record) is not dict or type(record.get("id")) is not str or record["id"] in seen:
                raise AcceptanceError("duplicate record")
            seen.add(record["id"])
            validate_record(record, bucket, evidence["acceptance_subject"], root)
            if bucket != "environment_limited_checks":
                gate_id = record["gate_id"]
                if gate_id in seen_gates:
                    raise AcceptanceError("duplicate gate record")
                seen_gates.add(gate_id)
    if evidence["evidence_fingerprint"] != evidence_fingerprint(evidence):
        raise AcceptanceError("evidence fingerprint mismatch")
    return evidence


def _matrix_items() -> tuple[dict[str, Any], ...]:
    viewports = (
        ("wide", 1440, 1000), ("laptop", 1024, 900), ("tablet", 768, 900), ("phone", 430, 844), ("small", 375, 812),
    )
    modes = (("light", "light", "no-preference", "none"), ("dark", "dark", "no-preference", "none"), ("reduced", "light", "reduce", "none"), ("forced", "light", "no-preference", "active"))
    return tuple({"id": f"{viewport}-{mode}", "viewport": viewport, "width": width, "height": height, "mode": mode, "color_scheme": scheme, "reduced_motion": reduced, "forced_colors": forced, "screenshot": f"{viewport}-{mode}.png" if viewport in {"wide", "tablet", "small"} else None} for viewport, width, height in viewports for mode, scheme, reduced, forced in modes)


def t605_schema_adapter() -> dict[str, Any]:
    """One isolated consumer seam for the canonical T605 v1 manifest."""
    return {
        "schema": T605_SCHEMA,
        "manifest_keys": {"artifacts", "artifacts_root", "browser", "build", "chapter_scope", "errors", "gate", "generated_at", "global_checks", "matrix_count", "schema", "status", "subject", "surfaces", "task"},
        "subject_keys": {"commit", "dirty", "working_tree_fingerprint"},
        "build_keys": {"start_fingerprint", "end_fingerprint", "input_fingerprint", "site_finalizer_fingerprint", "stable"},
        "browser_keys": {"name", "version", "fingerprint"},
        "matrix_count": 40,
        "surface_names": ("site", "studio"),
        "matrix": _matrix_items(),
        "global_check_ids": ("quick_demo_truth", "machine_contracts", "keyboard", "dialog", "offline", "wcag", "cwv", "local_launch"),
        "required_matrix_checks": ("shell", "media_state", "wcag", "cwv", "keyboard", "dialog"),
    }


def _check_index(checks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for check in checks:
        if type(check) is not dict or set(check) - {"id", "status", "route", "observed", "reason"} or type(check.get("id")) is not str or check.get("status") not in {"pass", "fail"} or type(check.get("observed")) is not dict:
            raise AcceptanceError("browser check shape")
        index.setdefault(check["id"], []).append(check)
    return index


def _validate_t605_check(value: Any, where: str) -> None:
    if type(value) is not dict or set(value) not in ({"family", "id", "observed", "route", "status"}, {"family", "id", "observed", "reason", "route", "status"}):
        raise AcceptanceError(f"{where}: check keys")
    if any(type(value[key]) is not str for key in ("family", "id", "route", "status")) or value["status"] != "pass" or type(value["observed"]) is not dict:
        raise AcceptanceError(f"{where}: check types")
    if "reason" in value and type(value["reason"]) is not str:
        raise AcceptanceError(f"{where}: check reason")
    _scan_safe(value)


def _validate_t605_identity(manifest: dict[str, Any], subject: dict[str, Any], adapter: dict[str, Any]) -> None:
    exact(manifest, adapter["manifest_keys"], "T605 manifest")
    if manifest["schema"] != adapter["schema"] or manifest["status"] != "pass" or manifest["task"] != "T605" or manifest["gate"] != "T605_BROWSER_ACCEPTANCE" or manifest["chapter_scope"] != "CH001" or manifest["artifacts_root"] != "." or manifest["matrix_count"] != adapter["matrix_count"]:
        raise AcceptanceError("T605 identity/status")
    _timestamp(manifest["generated_at"])
    exact(manifest["subject"], {"start", "end", "stable"}, "T605 subject")
    for name in ("start", "end"):
        exact(manifest["subject"][name], adapter["subject_keys"], f"T605 subject {name}")
        if type(manifest["subject"][name]["commit"]) is not str or not SHA40.fullmatch(manifest["subject"][name]["commit"]) or type(manifest["subject"][name]["dirty"]) is not bool or type(manifest["subject"][name]["working_tree_fingerprint"]) is not str or not SHA_PREFIXED.fullmatch(manifest["subject"][name]["working_tree_fingerprint"]):
            raise AcceptanceError("T605 subject shape")
    if manifest["subject"]["stable"] is not True or manifest["subject"]["start"] != manifest["subject"]["end"]:
        raise AcceptanceError("T605 subject unstable")
    expected_subject = {"commit": subject["current_commit"], "dirty": subject["dirty"], "working_tree_fingerprint": "sha256:" + subject["working_tree_fingerprint"]}
    if manifest["subject"]["start"] != expected_subject:
        raise AcceptanceError("T605 subject mismatch")
    exact(manifest["build"], adapter["build_keys"], "T605 build")
    if any(type(manifest["build"][key]) is not str or not SHA_PREFIXED.fullmatch(manifest["build"][key]) for key in ("start_fingerprint", "end_fingerprint", "input_fingerprint", "site_finalizer_fingerprint")) or manifest["build"]["stable"] is not True or manifest["build"]["start_fingerprint"] != manifest["build"]["end_fingerprint"] or manifest["build"]["input_fingerprint"] != "sha256:" + subject["build_fingerprint"]:
        raise AcceptanceError("T605 build identity")
    exact(manifest["browser"], adapter["browser_keys"], "T605 browser")
    if manifest["browser"]["name"] != "chromium" or type(manifest["browser"]["version"]) is not str or not manifest["browser"]["version"] or type(manifest["browser"]["fingerprint"]) is not str or not SHA_PREFIXED.fullmatch(manifest["browser"]["fingerprint"]):
        raise AcceptanceError("T605 browser fingerprint")
    if type(manifest["errors"]) is not list or manifest["errors"]:
        raise AcceptanceError("T605 errors")


def validate_t605_manifest(manifest: Any, subject: dict[str, Any], root: Path) -> None:
    adapter = t605_schema_adapter()
    if type(manifest) is not dict:
        raise AcceptanceError("T605 manifest type")
    _validate_t605_identity(manifest, subject, adapter)
    global_checks = manifest["global_checks"]
    if type(global_checks) is not list or [item.get("id") if type(item) is dict else None for item in global_checks] != list(adapter["global_check_ids"]):
        raise AcceptanceError("T605 global checks")
    for check in global_checks:
        _validate_t605_check(check, "T605 global check")
    artifacts = manifest["artifacts"]
    if type(artifacts) is not list:
        raise AcceptanceError("T605 artifacts")
    artifacts_by_path: dict[str, dict[str, Any]] = {}
    screenshot_artifacts: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        exact(artifact, {"id", "kind", "matrix", "path", "sha256", "size", "surface"}, "T605 artifact")
        if type(artifact["id"]) is not str or not artifact["id"] or type(artifact["kind"]) is not str or (type(artifact["surface"]) is not str and artifact["surface"] is not None) or (type(artifact["matrix"]) is not str and artifact["matrix"] is not None) or type(artifact["path"]) is not str or type(artifact["size"]) is not int or isinstance(artifact["size"], bool) or artifact["size"] < 1 or type(artifact["sha256"]) is not str or not SHA_PREFIXED.fullmatch(artifact["sha256"]):
            raise AcceptanceError("T605 artifact types")
        if artifact["path"] in artifacts_by_path:
            raise AcceptanceError("T605 duplicate artifact")
        artifacts_by_path[artifact["path"]] = artifact
        if artifact["kind"] == "screenshot":
            screenshot_artifacts[artifact["path"]] = artifact
        read_descriptor({"path": artifact["path"], "size": artifact["size"], "sha256": artifact["sha256"], "role": "browser-screenshot"}, root)
    if len(screenshot_artifacts) != 24:
        raise AcceptanceError("T605 screenshot count")
    surfaces = manifest["surfaces"]
    if type(surfaces) is not list or len(surfaces) != 2 or [item.get("surface") if type(item) is dict else None for item in surfaces] != list(adapter["surface_names"]):
        raise AcceptanceError("T605 surfaces")
    expected_matrix = [item["id"] for item in adapter["matrix"]]
    for surface in surfaces:
        exact(surface, {"checks", "errors", "matrix_count", "status", "surface", "viewports"}, "T605 surface")
        if surface["status"] != "pass" or surface["matrix_count"] != 20 or type(surface["viewports"]) is not list or len(surface["viewports"]) != 20 or type(surface["checks"]) is not list or type(surface["errors"]) is not list or surface["errors"]:
            raise AcceptanceError("T605 surface status/matrix")
        if [item.get("id") if type(item) is dict else None for item in surface["viewports"]] != expected_matrix:
            raise AcceptanceError("T605 exact matrix")
        seen_check_keys: set[tuple[str, str | None]] = set()
        for item, expected in zip(surface["viewports"], adapter["matrix"]):
            exact(item, {"checks", "height", "id", "mode", "route", "screenshot", "width"}, "T605 viewport")
            if item["width"] != expected["width"] or item["height"] != expected["height"] or item["route"] != ("/" if surface["surface"] == "site" else "/manuscript"):
                raise AcceptanceError("T605 viewport identity")
            exact(item["mode"], {"id", "color_scheme", "reduced_motion", "forced_colors"}, "T605 mode")
            if item["mode"] != {"id": expected["mode"], "color_scheme": expected["color_scheme"], "reduced_motion": expected["reduced_motion"], "forced_colors": expected["forced_colors"]}:
                raise AcceptanceError("T605 mode identity")
            expected_screenshot = f"{surface['surface']}/screenshots/{expected['screenshot']}" if expected["screenshot"] else None
            if expected_screenshot is None:
                if item["screenshot"] is not None:
                    raise AcceptanceError("T605 unexpected screenshot")
            else:
                exact(item["screenshot"], {"path"}, "T605 screenshot reference")
                if item["screenshot"]["path"] != expected_screenshot or expected_screenshot not in screenshot_artifacts:
                    raise AcceptanceError("T605 screenshot mapping")
                artifact = screenshot_artifacts[expected_screenshot]
                if artifact["surface"] != surface["surface"] or artifact["matrix"] != item["id"]:
                    raise AcceptanceError("T605 screenshot binding")
            if type(item["checks"]) is not list:
                raise AcceptanceError("T605 viewport checks")
            check_ids: set[str] = set()
            for check in item["checks"]:
                _validate_t605_check(check, "T605 matrix check")
                if check["id"] in check_ids or type(check["observed"].get("matrix")) is not str or check["observed"].get("matrix") != item["id"]:
                    raise AcceptanceError("T605 matrix check identity")
                check_ids.add(check["id"])
                seen_check_keys.add((check["id"], check["observed"].get("matrix")))
            if not set(adapter["required_matrix_checks"]).issubset(check_ids):
                raise AcceptanceError("T605 required matrix check")
        for check in surface["checks"]:
            _validate_t605_check(check, "T605 surface check")
        if len(seen_check_keys) < 120:
            raise AcceptanceError("T605 matrix check coverage")
    expected_screenshots = {f"{surface}/screenshots/{item['screenshot']}" for surface in adapter["surface_names"] for item in adapter["matrix"] if item["screenshot"]}
    if set(screenshot_artifacts) != expected_screenshots:
        raise AcceptanceError("T605 screenshot set")


def synthetic_t605_manifest(subject: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Test fixture helper. It is intentionally not used by the production runner."""
    adapter = t605_schema_adapter()
    artifacts: list[dict[str, Any]] = []
    surfaces: list[dict[str, Any]] = []
    subject_canonical = {"commit": subject["current_commit"], "dirty": subject["dirty"], "working_tree_fingerprint": "sha256:" + subject["working_tree_fingerprint"]}
    build_canonical = {"start_fingerprint": "sha256:" + "b" * 64, "end_fingerprint": "sha256:" + "b" * 64, "input_fingerprint": "sha256:" + subject["build_fingerprint"], "site_finalizer_fingerprint": "sha256:" + "e" * 64, "stable": True}
    global_checks = [{"id": item, "family": item, "status": "pass", "route": "matrix", "observed": {"value": True}} for item in adapter["global_check_ids"]]
    for surface_name in adapter["surface_names"]:
        viewport_items: list[dict[str, Any]] = []
        for matrix_item in adapter["matrix"]:
            checks = [{"id": item, "family": item, "status": "pass", "route": "/" if surface_name == "site" else "/manuscript", "observed": {"matrix": matrix_item["id"], "value": True}} for item in adapter["required_matrix_checks"]]
            screenshot = {"path": f"{surface_name}/screenshots/{matrix_item['screenshot']}"} if matrix_item["screenshot"] else None
            viewport_items.append({"id": matrix_item["id"], "width": matrix_item["width"], "height": matrix_item["height"], "mode": {"id": matrix_item["mode"], "color_scheme": matrix_item["color_scheme"], "reduced_motion": matrix_item["reduced_motion"], "forced_colors": matrix_item["forced_colors"]}, "route": "/" if surface_name == "site" else "/manuscript", "checks": checks, "screenshot": screenshot})
        surface_checks = [{"id": item, "family": item, "status": "pass", "route": "/" if surface_name == "site" else "/manuscript", "observed": {"value": True}} for item in adapter["required_matrix_checks"]]
        for matrix_item in adapter["matrix"]:
            if not matrix_item["screenshot"]:
                continue
            path = f"{surface_name}/screenshots/{matrix_item['screenshot']}"
            if root is not None:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"png-fixture")
                data = target.read_bytes()
                artifacts.append({"id": f"{surface_name}:{matrix_item['id']}:screenshot", "kind": "screenshot", "surface": surface_name, "matrix": matrix_item["id"], "path": path, "size": len(data), "sha256": "sha256:" + hashlib.sha256(data).hexdigest()})
        surfaces.append({"surface": surface_name, "status": "pass", "matrix_count": 20, "viewports": viewport_items, "checks": surface_checks, "errors": []})
    return {"schema": T605_SCHEMA, "status": "pass", "task": "T605", "gate": "T605_BROWSER_ACCEPTANCE", "chapter_scope": "CH001", "subject": {"start": subject_canonical, "end": dict(subject_canonical), "stable": True}, "build": build_canonical, "browser": {"name": "chromium", "version": "fixture", "fingerprint": "sha256:" + "a" * 64}, "matrix_count": 40, "surfaces": surfaces, "global_checks": global_checks, "artifacts": artifacts, "errors": [], "generated_at": "2026-08-20T00:00:00Z", "artifacts_root": "."}


def validate_local_browser_manifest(manifest: Any, subject: dict[str, Any], root: Path) -> None:
    exact(manifest, {"artifacts", "chapter_scope", "errors", "generated_at", "gate", "launch", "quick_demo", "schema", "status", "subject", "task"}, "T310 manifest")
    if manifest["schema"] != T310_SCHEMA or manifest["status"] != "pass" or manifest["task"] != "T310" or manifest["gate"] != "T310_BROWSER_LOCAL" or manifest["chapter_scope"] != "CH001":
        raise AcceptanceError("T310 identity")
    _timestamp(manifest["generated_at"])
    if type(manifest["errors"]) is not list or manifest["errors"]:
        raise AcceptanceError("T310 errors")
    exact(manifest["subject"], {"start", "end", "stable"}, "T310 subject")
    if manifest["subject"]["stable"] is not True or manifest["subject"]["start"] != subject or manifest["subject"]["end"] != subject:
        raise AcceptanceError("T310 subject identity")
    validate_subject(manifest["subject"]["start"])
    exact(manifest["quick_demo"], {"status", "receipt_schema", "chapter_scope", "authority", "model_execution_performed", "uploads", "canon_mutation"}, "T310 quick demo")
    if manifest["quick_demo"] != {"status": "pass", "receipt_schema": "quillframe_ch001_quick_demo_receipt_v1", "chapter_scope": "CH001", "authority": False, "model_execution_performed": False, "uploads": 0, "canon_mutation": False}:
        raise AcceptanceError("T310 demo truth")
    exact(manifest["launch"], {"status", "profile", "loopback", "core_bound", "cloud_upload_started"}, "T310 launch")
    if manifest["launch"] != {"status": "pass", "profile": "local", "loopback": True, "core_bound": True, "cloud_upload_started": False}:
        raise AcceptanceError("T310 launch truth")
    artifacts = manifest["artifacts"]
    _artifact_list(artifacts, root)
    required = {
        "t603-site-smoke/home-desktop.png",
        "t603-studio-smoke/studio-desktop.png",
        "t603-local-launch/local-launch-bound.png",
    }
    paths = {item["path"] for item in artifacts}
    if not required <= paths:
        raise AcceptanceError("T310 independent smoke artifacts")
    for item in artifacts:
        if item["role"] != "browser-screenshot":
            raise AcceptanceError("T310 artifact role")


def synthetic_local_browser_manifest(subject: dict[str, Any], root: Path) -> dict[str, Any]:
    """Test-only T310 fixture. Production runner never uses this helper."""
    artifacts = []
    for relative in ("t603-site-smoke/home-desktop.png", "t603-studio-smoke/studio-desktop.png", "t603-local-launch/local-launch-bound.png"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png-fixture")
        data = path.read_bytes()
        artifacts.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "role": "browser-screenshot"})
    return {
        "schema": T310_SCHEMA,
        "status": "pass",
        "task": "T310",
        "gate": "T310_BROWSER_LOCAL",
        "chapter_scope": "CH001",
        "subject": {"start": subject, "end": subject, "stable": True},
        "quick_demo": {"status": "pass", "receipt_schema": "quillframe_ch001_quick_demo_receipt_v1", "chapter_scope": "CH001", "authority": False, "model_execution_performed": False, "uploads": 0, "canon_mutation": False},
        "launch": {"status": "pass", "profile": "local", "loopback": True, "core_bound": True, "cloud_upload_started": False},
        "artifacts": artifacts,
        "errors": [],
        "generated_at": "2026-08-20T00:00:00Z",
    }


def _validate_external_record(record: dict[str, Any], subject: dict[str, Any], root: Path) -> None:
    if type(record["project_id"]) is not str or type(record["candidate_id"]) is not str or not SHA64.fullmatch(record["candidate_fingerprint"]) or not SHA64.fullmatch(record["receipt_fingerprint"]):
        raise AcceptanceError("external identity types")
    if record["subject"] != subject or record["project_id"] != subject["project_id"] or record["candidate_id"] != subject["candidate_id"]:
        raise AcceptanceError("external subject identity")
    expected_target = {"environment": "production", "version": VERSION, "project_id": subject["project_id"], "candidate_id": subject["candidate_id"]}
    if record["target_identity"] != expected_target:
        raise AcceptanceError("external target identity")
    proof_descriptors = [item for item in record["artifacts"] if item.get("role") == "external-proof"]
    if len(proof_descriptors) != 1:
        raise AcceptanceError("external proof artifact")
    proof_payload = parse_json(read_descriptor(proof_descriptors[0], root).decode("utf-8"))
    exact(proof_payload, {"schema", "gate_id", "project_id", "candidate_id", "candidate_fingerprint", "receipt_fingerprint", "target_identity", "proof"}, "external proof artifact")
    if proof_payload["schema"] != "quillframe_external_acceptance_proof_v1" or proof_payload["gate_id"] != record["gate_id"] or proof_payload["project_id"] != record["project_id"] or proof_payload["candidate_id"] != record["candidate_id"] or proof_payload["candidate_fingerprint"] != record["candidate_fingerprint"] or proof_payload["receipt_fingerprint"] != record["receipt_fingerprint"] or proof_payload["target_identity"] != record["target_identity"] or proof_payload["proof"] != record["proof"]:
        raise AcceptanceError("external proof binding")
    if record["gate_id"] == "T409.external":
        exact(record["approval"], {"actor", "status"}, "T409 approval")
        exact(record["proof"], {"kind", "deployment_id", "deployment_receipt_fingerprint", "credentials_used", "deployed"}, "T409 proof")
        if record["approval"] != {"actor": "authorized_human", "status": "verified"} or record["proof"]["kind"] != "workos_cloudflare_deployment" or type(record["proof"]["deployment_id"]) is not str or not SHA64.fullmatch(record["proof"]["deployment_receipt_fingerprint"]) or record["proof"]["credentials_used"] is not True or record["proof"]["deployed"] is not True:
            raise AcceptanceError("T409 proof")
    elif record["gate_id"] == "T606.external":
        exact(record["approval"], {"actor", "status"}, "T606 approval")
        exact(record["proof"], {"kind", "independent_reviewer_id", "model_invocation_id", "model_execution_performed", "chain", "receipt_schema", "candidate_artifact_fingerprint", "acceptance_receipt_fingerprint", "settlement_receipt_fingerprint", "publication_receipt_fingerprint"}, "T606 proof")
        if record["proof"]["kind"] != "real_ch001_author_chain" or type(record["proof"]["independent_reviewer_id"]) is not str or not record["proof"]["independent_reviewer_id"] or type(record["proof"]["model_invocation_id"]) is not str or not record["proof"]["model_invocation_id"] or record["proof"]["model_execution_performed"] is not True or record["proof"]["chain"] != ["candidate_visible", "accept", "settle", "publish"] or record["proof"]["receipt_schema"] != "quillframe_host_bridge_result_v11" or record["proof"]["candidate_artifact_fingerprint"] != record["candidate_fingerprint"] or any(not SHA64.fullmatch(record["proof"][key]) for key in ("acceptance_receipt_fingerprint", "settlement_receipt_fingerprint", "publication_receipt_fingerprint")):
            raise AcceptanceError("T606 proof")
    elif record["gate_id"] == "T607.approval":
        exact(record["approval"], {"actor", "status"}, "T607 approval")
        exact(record["proof"], {"kind", "target_identity", "approved", "depends_on"}, "T607 proof")
        if record["approval"] != {"actor": "authorized_human", "status": "approved"} or record["proof"] != {"kind": "promotion_approval", "target_identity": expected_target, "approved": True, "depends_on": ["T409.external", "T606.external"]}:
            raise AcceptanceError("T607 proof")
    else:
        raise AcceptanceError("external gate")


def validate_external_cross_binding(records: list[dict[str, Any]], subject: dict[str, Any]) -> None:
    if type(records) is not list or type(subject) is not dict:
        raise AcceptanceError("external records type")
    by_gate: dict[str, dict[str, Any]] = {}
    for record in records:
        if type(record) is not dict or type(record.get("gate_id")) is not str:
            raise AcceptanceError("external record shape")
        if record.get("result") == "pass":
            if record["gate_id"] in by_gate:
                raise AcceptanceError("duplicate external gate")
            by_gate[record["gate_id"]] = record
    required = ("T409.external", "T606.external", "T607.approval")
    if any(gate not in by_gate for gate in required):
        raise AcceptanceError("external dependency missing")
    try:
        validate_subject(subject)
    except (AcceptanceError, TypeError) as exc:
        raise AcceptanceError("external subject shape") from exc
    try:
        identity = (subject["project_id"], subject["candidate_id"], by_gate["T409.external"]["candidate_fingerprint"], by_gate["T409.external"]["receipt_fingerprint"], by_gate["T409.external"]["target_identity"])
        for gate in required:
            item = by_gate[gate]
            current = (item["project_id"], item["candidate_id"], item["candidate_fingerprint"], item["receipt_fingerprint"], item["target_identity"])
            if current != identity:
                raise AcceptanceError("external cross-binding")
    except (KeyError, TypeError) as exc:
        raise AcceptanceError("external cross-binding shape") from exc


def derive_tasks(evidence: dict[str, Any], t608_final: bool, source_status: dict[str, str] | None = None) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for bucket in ("commands", "browser_manifests", "external_evidence"):
        for record in evidence[bucket]:
            gate_id = record.get("gate_id") if type(record) is dict else None
            if type(gate_id) is not str:
                raise AcceptanceError("gate record shape")
            if gate_id in records:
                raise AcceptanceError("duplicate gate record")
            records[gate_id] = record
    result: list[dict[str, Any]] = []
    for task_id in CANONICAL_TASK_IDS:
        requirements = TASK_REQUIREMENTS[task_id]
        statuses: list[bool] = []
        for gate_id in requirements:
            if gate_id == "T607.derived":
                statuses.append(all(records.get(item, {}).get("result") == "pass" for item in ("T409.external", "T606.external", "T607.approval")))
            elif gate_id == "T608.final_readback":
                statuses.append(t608_final)
            else:
                statuses.append(records.get(gate_id, {}).get("result") == "pass")
        passed = all(statuses)
        status = "x" if passed else "!" if task_id in EXTERNAL_TASKS else "~"
        result.append({"id": task_id, "requirements": list(requirements), "status": status, "source_status": (source_status or {}).get(task_id)})
    return result


def all_local_tasks_pass(tasks: list[dict[str, Any]]) -> bool:
    return all(item.get("status") == "x" for item in tasks)


def final_gate_ready(gates: dict[str, Any]) -> bool:
    return gates.get("t608_phase") == T608_FINAL


def release_ready(evidence: dict[str, Any], tasks: list[dict[str, Any]], external_bound: bool) -> bool:
    return not evidence["acceptance_subject"]["dirty"] and all_local_tasks_pass(tasks) and final_gate_ready(evidence.get("gates", {})) and external_bound


def render_markdown(report: dict[str, Any], tasks: list[dict[str, Any]], language: str, overview: bool) -> str:
    if language == "en":
        title = "Release acceptance overview" if overview else "Complete task ledger"
        intro = "Implementation evidence is bound to CH001 and the exact acceptance subject." if overview else "Generator-owned task ledger. Source checkboxes never grant evidence or authority."
    else:
        title = "发布验收概览" if overview else "完整任务账本"
        intro = "实现证据绑定到 CH001 与精确验收主体。" if overview else "由生成器拥有的任务账本。源文件复选框不会授予证据或权限。"
    lines = [f"# {title}", "", intro, "", f"Framework version: `{VERSION}`", "Chapter scope: `CH001`", f"Status: `{report['status']}`", f"T608 phase: `{report['gates']['t608_phase']}`", f"Evidence fingerprint: `{report['evidence_fingerprint']}`", ""]
    if overview:
        lines.extend(["## Gate summary", "", f"Release promotion authorized: `{report.get('release_promotion_authorized', False)}`", f"Blocking tasks: `{len(report.get('blocking_evidence', []))}`", "", "## Task status", ""])
    else:
        lines.extend(["## Tasks", ""])
    lines.extend(f"- [{item['status']}] {item['id']} requires {', '.join(item['requirements'])}" for item in tasks)
    return "\n".join(lines) + "\n"


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError("short publisher write")
        offset += written


def _safe_output(output: Path) -> Path:
    try:
        fd = _open_directory_chain(output.absolute(), create=True)
    except (OSError, AcceptanceError) as exc:
        raise AcceptanceError("output boundary") from exc
    os.close(fd)
    return output


def _journal_write(path: Path, value: dict[str, Any]) -> None:
    """Write a journal through a descriptor-relative, owned replacement.

    The temporary name is intentionally unpredictable and is created with
    O_EXCL|O_NOFOLLOW.  The old implementation used a fixed ``.tmp`` name,
    which made a pre-created symlink or a concurrent temp swap actionable.
    The journal target is also checked before and after replacement. A
    competitor is never silently accepted as an owned journal.
    """
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    parent = _safe_root(path.parent)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary_name = None
    temporary_metadata = None
    try:
        for _attempt in range(32):
            candidate = f".{path.name}.{os.urandom(16).hex()}.tmp"
            try:
                fd = os.open(candidate, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
                temporary_name = candidate
                break
            except FileExistsError:
                continue
        else:
            raise AcceptanceError("journal temporary name exhausted")
        try:
            _write_all(fd, payload)
            os.fsync(fd)
            stat_value = os.fstat(fd)
            if not stat.S_ISREG(stat_value.st_mode) or stat_value.st_nlink != 1 or stat_value.st_size != len(payload):
                raise AcceptanceError("journal temporary ownership")
            check = os.pread(fd, stat_value.st_size, 0)
            if check != payload or hashlib.sha256(check).hexdigest() != hashlib.sha256(payload).hexdigest():
                raise AcceptanceError("journal temporary digest")
            temporary_metadata = {
                "dev": stat_value.st_dev,
                "ino": stat_value.st_ino,
                "size": len(check),
                "sha256": hashlib.sha256(check).hexdigest(),
            }
        finally:
            os.close(fd)

        target_stat = None
        try:
            target_stat = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        if target_stat is not None:
            if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISREG(target_stat.st_mode) or target_stat.st_nlink != 1:
                raise AcceptanceError("journal target ownership")
            target_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                target_value = os.fstat(target_fd)
                old_bytes = os.pread(target_fd, target_value.st_size, 0)
                try:
                    old_journal = parse_json(old_bytes.decode("utf-8"))
                except (UnicodeDecodeError, AcceptanceError):
                    raise AcceptanceError("journal target ownership")
                if type(old_journal) is not dict or old_journal.get("token") != value.get("token"):
                    raise AcceptanceError("journal target ownership")
            finally:
                os.close(target_fd)

        if target_stat is None:
            try:
                os.link(temporary_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
            except FileExistsError as exc:
                raise AcceptanceError("journal target appeared") from exc
            linked_fd = os.open(temporary_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                linked_value = os.fstat(linked_fd)
                if linked_value.st_dev != temporary_metadata["dev"] or linked_value.st_ino != temporary_metadata["ino"] or linked_value.st_nlink != 2:
                    raise AcceptanceError("journal temporary link ownership")
            finally:
                os.close(linked_fd)
            os.unlink(temporary_name, dir_fd=parent_fd)
            temporary_name = None
        else:
            os.replace(temporary_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            temporary_name = None
        target_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            target_value = os.fstat(target_fd)
            if not stat.S_ISREG(target_value.st_mode) or target_value.st_nlink != 1:
                raise AcceptanceError("journal replacement ownership")
            installed = os.pread(target_fd, target_value.st_size, 0)
            installed_metadata = {
                "dev": target_value.st_dev,
                "ino": target_value.st_ino,
                "size": len(installed),
                "sha256": hashlib.sha256(installed).hexdigest(),
            }
            if installed_metadata != temporary_metadata or installed != payload:
                raise AcceptanceError("journal replacement changed")
        finally:
            os.close(target_fd)
        _fsync_directory(parent)
    finally:
        if temporary_name is not None:
            try:
                temp_stat = os.stat(temporary_name, dir_fd=parent_fd, follow_symlinks=False)
                if stat.S_ISREG(temp_stat.st_mode) and temp_stat.st_nlink == 1 and temporary_metadata is not None and temp_stat.st_ino == temporary_metadata["ino"] and temp_stat.st_dev == temporary_metadata["dev"]:
                    os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)


def _owned_metadata(value: Any, where: str) -> dict[str, Any]:
    exact(value, {"dev", "ino", "size", "sha256"}, where)
    if any(type(value[key]) is not int or isinstance(value[key], bool) or value[key] < 0 for key in ("dev", "ino", "size")) or not SHA64.fullmatch(value["sha256"]):
        raise AcceptanceError(f"{where}: metadata")
    return value


def _validate_publisher_journal(journal: dict[str, Any]) -> None:
    exact(journal, {"schema", "token", "phase", "entries", "names"}, "publisher journal")
    if journal["schema"] != "quillframe_acceptance_publish_v1" or type(journal["token"]) is not str or not re.fullmatch(r"[0-9a-f]{32}", journal["token"]) or journal["phase"] not in {"BACKUP", "INSTALL", "READBACK", "CLEANUP"} or type(journal["names"]) is not list or any(type(name) is not str for name in journal["names"]):
        raise AcceptanceError("publisher journal identity")
    if type(journal["entries"]) is not list or sorted(journal["names"]) != sorted(entry.get("name") for entry in journal["entries"]):
        raise AcceptanceError("publisher journal entries")
    for entry in journal["entries"]:
        exact(entry, {"name", "old", "planned_install", "installed"}, "publisher journal entry")
        if type(entry["name"]) is not str or not entry["name"] or entry["name"] in {".", ".."} or "/" in entry["name"] or "\\" in entry["name"]:
            raise AcceptanceError("publisher journal name")
        for key in ("old", "planned_install", "installed"):
            if entry[key] is not None:
                _owned_metadata(entry[key], f"publisher journal {key}")


def _read_lock_token(output: Path, token: str, required: bool) -> None:
    lock = output / ".acceptance.lock"
    if not lock.exists() and not lock.is_symlink():
        if required:
            raise AcceptanceError("publisher lock missing")
        return
    raw = read_file_bytes(output, lock.name, 1024, require_single_link=True)
    if raw.decode("ascii", errors="replace") != token:
        raise AcceptanceError("publisher lock ownership")


def _unlink_owned(path: Path, expected: dict[str, Any]) -> None:
    actual = read_owned(path, require_single_link=False)
    if actual != expected:
        raise AcceptanceError("publisher unlink ownership")
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            current = os.fstat(fd)
            data = os.pread(fd, current.st_size, 0)
            check = {"dev": current.st_dev, "ino": current.st_ino, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            if check != expected:
                raise AcceptanceError("publisher unlink race")
            os.unlink(path.name, dir_fd=parent_fd)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)
    if path.exists() and not path.is_symlink():
        raise AcceptanceError("publisher unlink postcondition")


def _validate_backup_directory(backup: Path, entries: list[dict[str, Any]]) -> None:
    if not backup.exists():
        return
    if backup.is_symlink() or not backup.is_dir():
        raise AcceptanceError("publisher backup boundary")
    expected_names = {entry["name"] for entry in entries if entry.get("old") is not None}
    actual_names = {item.name for item in backup.iterdir()}
    if actual_names != expected_names:
        raise AcceptanceError("publisher backup names")
    for entry in entries:
        if entry.get("old") is not None and not _entry_matches(backup / entry["name"], entry["old"]):
            raise AcceptanceError("publisher backup ownership")


def _remove_empty_backup(backup: Path) -> None:
    try:
        parent_fd = os.open(backup.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise AcceptanceError("publisher backup boundary") from exc
    try:
        try:
            backup_fd = os.open(backup.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            raise AcceptanceError("publisher backup boundary") from exc
        try:
            backup_identity = os.fstat(backup_fd)
            if not stat.S_ISDIR(backup_identity.st_mode):
                raise AcceptanceError("publisher backup boundary")
            if os.listdir(backup_fd):
                raise AcceptanceError("publisher backup residue")
            current = os.stat(backup.name, dir_fd=parent_fd, follow_symlinks=False)
            if current.st_dev != backup_identity.st_dev or current.st_ino != backup_identity.st_ino:
                raise AcceptanceError("publisher backup race")
            os.rmdir(backup.name, dir_fd=parent_fd)
        finally:
            os.close(backup_fd)
    finally:
        os.close(parent_fd)
    if backup.exists() or backup.is_symlink():
        raise AcceptanceError("publisher backup removal postcondition")


def _remove_owned_backup(backup: Path, entries: list[dict[str, Any]]) -> None:
    _validate_backup_directory(backup, entries)
    for entry in entries:
        if entry.get("old") is not None:
            _unlink_owned(backup / entry["name"], entry["old"])
    _remove_empty_backup(backup)


def rename_owned(source: Path, target: Path) -> None:
    metadata = read_owned(source, require_single_link=True)
    if source.is_symlink() or metadata["size"] < 0:
        raise AcceptanceError("rename source ownership")
    if target.exists() or target.is_symlink():
        raise AcceptanceError("rename target exists")
    source_parent_fd = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    target_parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.link(source.name, target.name, src_dir_fd=source_parent_fd, dst_dir_fd=target_parent_fd, follow_symlinks=False)
        except FileExistsError as exc:
            raise AcceptanceError("rename target appeared") from exc
        target_link_fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=target_parent_fd)
        try:
            target_link = os.fstat(target_link_fd)
            if target_link.st_dev != metadata["dev"] or target_link.st_ino != metadata["ino"] or target_link.st_nlink != 2:
                raise AcceptanceError("rename link ownership")
        finally:
            os.close(target_link_fd)
    finally:
        os.close(source_parent_fd)
        os.close(target_parent_fd)
    _unlink_owned(source, metadata)
    if not _entry_matches(target, metadata):
        raise AcceptanceError("rename ownership postcondition")


def link_owned(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file() or target.exists() or target.is_symlink():
        raise AcceptanceError("link ownership")
    source_metadata = read_owned(source, require_single_link=True)
    if source_metadata["dev"] != target.parent.stat().st_dev:
        raise AcceptanceError("stage filesystem")
    os.link(source, target, follow_symlinks=False)
    if not _entry_matches(target, source_metadata):
        raise AcceptanceError("link ownership postcondition")


def _entry_matches(path: Path, expected: dict[str, Any] | None) -> bool:
    if expected is None or not path.exists() or path.is_symlink():
        return False
    actual = read_owned(path, require_single_link=False)
    return actual["dev"] == expected["dev"] and actual["ino"] == expected["ino"] and actual["sha256"] == expected["sha256"]


def recover(output: Path) -> bool:
    output = _safe_output(output)
    journal_path = output / ".acceptance.journal"
    if not journal_path.exists() and not journal_path.is_symlink():
        return False
    journal = parse_json(read_file_bytes(output, ".acceptance.journal", 8 * 1024 * 1024, require_single_link=True).decode("utf-8"))
    if type(journal) is not dict:
        raise AcceptanceError("publisher journal type")
    _validate_publisher_journal(journal)
    backup = output / f".backup-{journal['token']}"
    _read_lock_token(output, journal["token"], journal["phase"] != "CLEANUP")
    if journal["phase"] == "CLEANUP":
        for entry in journal["entries"]:
            if entry.get("installed") is None or not _entry_matches(output / entry["name"], entry["installed"]):
                raise AcceptanceError("cleanup competitor")
        if backup.exists() or backup.is_symlink():
            _remove_empty_backup(backup)
        journal_metadata = read_owned(journal_path, require_single_link=True)
        _unlink_owned(journal_path, journal_metadata)
        lock = output / ".acceptance.lock"
        if lock.exists() or lock.is_symlink():
            _unlink_owned(lock, read_owned(lock, require_single_link=True))
        _fsync_directory(output)
        return True
    for entry in journal["entries"]:
        target = output / entry["name"]
        installed = entry.get("installed") or entry.get("planned_install")
        if target.exists() or target.is_symlink():
            if entry.get("old") and _entry_matches(target, entry["old"]):
                continue
            if installed and _entry_matches(target, installed):
                _unlink_owned(target, installed)
            else:
                raise AcceptanceError("publisher competitor target")
    for entry in journal["entries"]:
        old = backup / entry["name"]
        target = output / entry["name"]
        expected_old = entry.get("old")
        if expected_old:
            if _entry_matches(target, expected_old):
                if old.exists() or old.is_symlink():
                    raise AcceptanceError("publisher duplicate old ownership")
                continue
            if old.is_symlink() or not old.exists() or not _entry_matches(old, expected_old) or target.exists() or target.is_symlink():
                raise AcceptanceError("publisher backup ownership")
            rename_owned(old, target)
        elif old.exists():
            raise AcceptanceError("unexpected publisher backup")
    if backup.exists():
        _remove_empty_backup(backup)
    journal_metadata = read_owned(journal_path, require_single_link=True)
    _unlink_owned(journal_path, journal_metadata)
    lock = output / ".acceptance.lock"
    if lock.exists() or lock.is_symlink():
        _unlink_owned(lock, read_owned(lock, require_single_link=True))
    _fsync_directory(output)
    return True


def publish(staged: dict[str, Path], output: Path, expected_names: set[str] | frozenset[str] | None = None) -> None:
    output = _safe_output(output)
    names = set(expected_names or CANONICAL_OUTPUT_NAMES)
    if set(staged) != names or any("/" in name or "\\" in name or name in {".", ".."} for name in staged):
        raise AcceptanceError("publisher canonical names")
    if (output / ".acceptance.lock").exists() or (output / ".acceptance.journal").exists():
        raise AcceptanceError("publisher recovery required")
    stage_parents = {source.parent.absolute() for source in staged.values()}
    if len(stage_parents) != 1:
        raise AcceptanceError("publisher stage root")
    stage_root = next(iter(stage_parents))
    _safe_root(stage_root)
    if stage_root == output.absolute() or not stage_root.is_dir() or stage_root.is_symlink():
        raise AcceptanceError("publisher stage root")
    for name, source in staged.items():
        if source.parent.absolute() != stage_root:
            raise AcceptanceError("publisher stage root")
        if source.is_symlink() or not source.is_file() or source.stat().st_dev != output.stat().st_dev:
            raise AcceptanceError("publisher stage boundary")
        read_owned(source, require_single_link=True)
    token = os.urandom(16).hex()
    lock = output / ".acceptance.lock"
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        _write_all(fd, token.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    backup = output / f".backup-{token}"
    try:
        backup.mkdir()
    except Exception:
        try:
            _unlink_owned(lock, read_owned(lock, require_single_link=True))
            _fsync_directory(output)
        finally:
            raise
    entries = [{"name": name, "old": None, "planned_install": read_owned(source), "installed": None} for name, source in sorted(staged.items())]
    journal_path = output / ".acceptance.journal"
    journal = {"schema": "quillframe_acceptance_publish_v1", "token": token, "phase": "BACKUP", "names": sorted(names), "entries": entries}
    try:
        _journal_write(journal_path, journal)
    except Exception:
        if not journal_path.exists() and not journal_path.is_symlink():
            try:
                _remove_empty_backup(backup)
                _unlink_owned(lock, read_owned(lock, require_single_link=True))
                _fsync_directory(output)
            finally:
                raise
        raise
    try:
        for entry in entries:
            target = output / entry["name"]
            if target.exists() or target.is_symlink():
                if target.is_symlink():
                    raise AcceptanceError("publisher target symlink")
                entry["old"] = read_owned(target, require_single_link=True)
                _journal_write(journal_path, journal)
                rename_owned(target, backup / entry["name"])
                _journal_write(journal_path, journal)
        journal["phase"] = "INSTALL"
        _journal_write(journal_path, journal)
        for entry in entries:
            target = output / entry["name"]
            _journal_write(journal_path, journal)
            link_owned(staged[entry["name"]], target)
            entry["installed"] = read_owned(target, require_single_link=False)
            _journal_write(journal_path, journal)
        _fsync_directory(output)
        journal["phase"] = "READBACK"
        _journal_write(journal_path, journal)
        for entry in entries:
            if not _entry_matches(output / entry["name"], entry["installed"]):
                raise AcceptanceError("publisher final readback")
        journal["phase"] = "CLEANUP"
        _journal_write(journal_path, journal)
        _remove_owned_backup(backup, entries)
        _fsync_directory(output)
        _unlink_owned(lock, read_owned(lock, require_single_link=True))
        _fsync_directory(output)
        _unlink_owned(journal_path, read_owned(journal_path, require_single_link=True))
        _fsync_directory(output)
    except Exception:
        raise


def _source_ledgers(repo: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    def read(name: str) -> list[dict[str, Any]]:
        result = []
        path = repo / "specs" / "024-quillframe-all-in-one-1-0" / name
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^- \[([ x~!])\] (T\d{3}) (.+)$", line)
            if match:
                result.append({"id": match.group(2), "description": match.group(3), "source_status": match.group(1)})
        if [item["id"] for item in result] != list(CANONICAL_TASK_IDS):
            raise AcceptanceError("canonical task ledger")
        return result
    return read("tasks.en.md"), read("tasks.zh-CN.md")


def _artifact_descriptor(path: Path, relative: str, role: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "role": role}


def _report_base(evidence: dict[str, Any], tasks: list[dict[str, Any]], tasks_en: list[dict[str, Any]], tasks_zh: list[dict[str, Any]], phase: str, external_bound: bool) -> dict[str, Any]:
    local_ids = [record["id"] for bucket in ("commands", "browser_manifests") for record in evidence[bucket] if record["result"] == "pass"]
    blocking = [item["id"] for item in tasks if item["status"] != "x"]
    def localized(source: list[dict[str, Any]]) -> list[dict[str, Any]]:
        source_by_id = {item["id"]: item for item in source}
        return [{**source_by_id[item["id"]], "status": item["status"], "requirements": item["requirements"]} for item in tasks]

    report = {
        "schema": REPORT_SCHEMA,
        "framework_version": VERSION,
        "generated_at": evidence["generated_at"],
        "acceptance_subject": evidence["acceptance_subject"],
        "evidence_fingerprint": evidence["evidence_fingerprint"],
        "status": "acceptance_incomplete",
        "release_promotion_authorized": False,
        "deployment_performed": any(item["gate_id"] == "T409.external" and item["result"] == "pass" for item in evidence["external_evidence"]),
        "model_execution_performed": any(item["gate_id"] == "T606.external" and item["result"] == "pass" for item in evidence["external_evidence"]),
        "gates": {"chapter_scope": "CH001", "local_gates_pass": all_local_tasks_pass([item for item in tasks if item["id"] not in EXTERNAL_TASKS]), "external_cross_binding": external_bound, "t608_phase": phase, "json_self_hash": JSON_SELF_HASH_POLICY},
        "local_evidence": local_ids,
        "blocking_evidence": blocking,
        "environment_limited_checks": evidence["environment_limited_checks"],
        "task_ledger": {"ordered_ids": list(CANONICAL_TASK_IDS), "tasks_en": localized(tasks_en), "tasks_zh": localized(tasks_zh)},
        "rendered_artifacts": [],
    }
    local_tasks = [item for item in tasks if item["id"] not in EXTERNAL_TASKS]
    if all_local_tasks_pass(local_tasks):
        report["status"] = "implementation_verified_release_blocked"
    if release_ready({**evidence, "gates": report["gates"]}, tasks, external_bound):
        report["status"] = "release_ready"
        report["release_promotion_authorized"] = True
    return report


def _write_stage(stage: Path, report: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Path]:
    rendered = {
        f"{VERSION}.en.md": render_markdown(report, tasks, "en", True),
        f"{VERSION}.zh-CN.md": render_markdown(report, tasks, "zh-CN", True),
        f"{VERSION}.tasks.en.md": render_markdown(report, tasks, "en", False),
        f"{VERSION}.tasks.zh-CN.md": render_markdown(report, tasks, "zh-CN", False),
    }
    report["rendered_artifacts"] = []
    for name, content in rendered.items():
        path = stage / name
        path.write_text(content, encoding="utf-8")
        report["rendered_artifacts"].append(_artifact_descriptor(path, name, "rendered-markdown"))
        report["rendered_artifacts"][-1].pop("role")
    json_path = stage / f"{VERSION}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {path.name: path for path in stage.iterdir()}


def _reread_published(output: Path, expected_report: dict[str, Any]) -> None:
    names = sorted(CANONICAL_OUTPUT_NAMES)
    for name in names:
        read_file_bytes(output, name, 64 * 1024 * 1024)
    report = read_json_descriptor(output, f"{VERSION}.json")
    exact(report, REPORT_KEYS, "published report")
    if report != expected_report:
        raise AcceptanceError("published report parity")
    for descriptor in report["rendered_artifacts"]:
        data = read_descriptor({**descriptor, "role": "rendered-markdown"}, output)
        if len(data) != descriptor["size"] or hashlib.sha256(data).hexdigest() != descriptor["sha256"]:
            raise AcceptanceError("published markdown parity")
    en = read_file_bytes(output, f"{VERSION}.en.md").decode("utf-8")
    zh = read_file_bytes(output, f"{VERSION}.zh-CN.md").decode("utf-8")
    tasks_en = read_file_bytes(output, f"{VERSION}.tasks.en.md").decode("utf-8")
    tasks_zh = read_file_bytes(output, f"{VERSION}.tasks.zh-CN.md").decode("utf-8")
    if en == zh or en == tasks_en or zh == tasks_zh:
        raise AcceptanceError("bilingual artifact parity collision")


def generate(repo: Path, evidence_path: Path, output: Path) -> dict[str, Any]:
    output = _safe_output(output)
    if (output / ".acceptance.journal").exists() or (output / ".acceptance.journal").is_symlink():
        recover(output)
    evidence_root = evidence_path.parent
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise AcceptanceError("evidence path")
    relative = evidence_path.name
    evidence = read_json_descriptor(evidence_root, relative)
    validate_evidence(evidence, evidence_root)
    if (repo / "VERSION").read_text().strip() != VERSION:
        raise AcceptanceError("version mismatch")
    tasks_en, tasks_zh = _source_ledgers(repo)
    source_status = {item["id"]: item["source_status"] for item in tasks_en}
    tasks_provisional = derive_tasks(evidence, False, source_status)
    external_bound = False
    external_records = [record for record in evidence["external_evidence"] if record["result"] == "pass"]
    if len(external_records) == 3:
        try:
            validate_external_cross_binding(external_records, evidence["acceptance_subject"])
            external_bound = True
        except AcceptanceError:
            external_bound = False
    provisional = _report_base(evidence, tasks_provisional, tasks_en, tasks_zh, T608_PROVISIONAL, external_bound)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        stage = Path(directory)
        staged = _write_stage(stage, provisional, tasks_provisional)
        publish(staged, output, CANONICAL_OUTPUT_NAMES)
    _reread_published(output, provisional)
    tasks_final = derive_tasks(evidence, True, source_status)
    final = _report_base(evidence, tasks_final, tasks_en, tasks_zh, T608_FINAL, external_bound)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        stage = Path(directory)
        staged = _write_stage(stage, final, tasks_final)
        publish(staged, output, CANONICAL_OUTPUT_NAMES)
    _reread_published(output, final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe native acceptance generator")
    parser.add_argument("--repo-root")
    parser.add_argument("--evidence")
    parser.add_argument("--output", required=True)
    parser.add_argument("--recover", action="store_true", help="recover a publisher journal in --output and stop")
    args = parser.parse_args()
    if args.recover:
        recover(Path(args.output))
        return 0
    if not args.repo_root or not args.evidence:
        parser.error("--repo-root and --evidence are required unless --recover is used")
    report = generate(Path(args.repo_root), Path(args.evidence), Path(args.output))
    print(report["status"])
    return 0 if report["status"] in {"release_ready", "implementation_verified_release_blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
