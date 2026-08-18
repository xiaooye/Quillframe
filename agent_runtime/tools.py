from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from model_runtime.contracts import fingerprint


class ToolRuntimeError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def _fingerprint_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return [f"{path} must be object"]
        for key in schema.get("required") or []:
            if key not in value:
                errors.append(f"{path}.{key} is required")
        if schema.get("additionalProperties") is False:
            allowed = set((schema.get("properties") or {}).keys())
            for key in value:
                if key not in allowed:
                    errors.append(f"{path}.{key} is not allowed")
        for key, child_schema in (schema.get("properties") or {}).items():
            if key in value and isinstance(child_schema, dict):
                errors.extend(_validate_schema(value[key], child_schema, f"{path}.{key}"))
    elif kind == "array":
        if not isinstance(value, list):
            return [f"{path} must be array"]
        item_schema = schema.get("items") or {}
        for i, item in enumerate(value):
            errors.extend(_validate_schema(item, item_schema, f"{path}[{i}]"))
    elif kind == "string" and not isinstance(value, str):
        errors.append(f"{path} must be string")
    elif kind == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"{path} must be integer")
    elif kind == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        errors.append(f"{path} must be number")
    elif kind == "boolean" and not isinstance(value, bool):
        errors.append(f"{path} must be boolean")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} must be one of {schema['enum']}")
    return errors


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    required_host_capability: str
    required_authority: str | None = None
    side_effect: bool = False
    idempotency_required: bool = False
    parallel_safe: bool = False

    def model_view(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


@dataclass
class ToolRuntime:
    host_capabilities: set[str] = field(default_factory=set)
    _tools: dict[str, ToolSpec] = field(default_factory=dict)
    _receipts: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def spec(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolRuntimeError("tool_unknown", name) from exc

    def model_tools(self, grants: set[str]) -> list[dict[str, Any]]:
        return [self._tools[name].model_view() for name in sorted(grants) if name in self._tools]

    def execute(self, call_id: str, name: str, arguments: dict[str, Any], *, grants: set[str], authority: dict[str, Any], idempotency_key: str | None = None) -> dict[str, Any]:
        if not call_id:
            raise ToolRuntimeError("tool_call_id_required", "tool call id is required")
        spec = self.spec(name)
        if name not in grants:
            raise ToolRuntimeError("tool_not_granted", name)
        if spec.required_host_capability not in self.host_capabilities:
            raise ToolRuntimeError("host_capability_missing", spec.required_host_capability)
        if spec.required_authority and authority.get(spec.required_authority) is not True:
            raise ToolRuntimeError("tool_authority_denied", spec.required_authority)
        errors = _validate_schema(arguments, spec.input_schema)
        if errors:
            raise ToolRuntimeError("tool_arguments_invalid", "; ".join(errors))
        args_fp = fingerprint(arguments)
        prior = self._receipts.get(call_id)
        if prior:
            if prior["tool"] != name or prior["arguments_fingerprint"] != args_fp:
                raise ToolRuntimeError("tool_call_replay_conflict", "same call id arrived with different tool or arguments")
            return prior
        if spec.idempotency_required and not idempotency_key:
            raise ToolRuntimeError("tool_idempotency_required", name)
        try:
            output = spec.handler(arguments)
        except ToolRuntimeError:
            raise
        except Exception as exc:
            raise ToolRuntimeError("tool_execution_failed", f"{type(exc).__name__}: {exc}") from exc
        receipt = {
            "schema": "quillframe_tool_receipt_v1",
            "tool_call_id": call_id,
            "tool": name,
            "arguments_fingerprint": args_fp,
            "idempotency_key": idempotency_key,
            "side_effect": spec.side_effect,
            "output": output,
            "output_fingerprint": fingerprint(output),
            "authority": False,
        }
        self._receipts[call_id] = receipt
        return receipt


class RepositoryToolset:
    DEFAULT_SENSITIVE_NAMES = {".env", "credentials.json", "service-account.json"}
    DEFAULT_SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}

    def __init__(self, root: Path, *, allow_sensitive_paths: bool = False) -> None:
        self.root = root.expanduser().resolve()
        self.allow_sensitive_paths = allow_sensitive_paths
        if not self.root.is_dir():
            raise ValueError("repository root must be a directory")

    def _is_sensitive(self, path: Path) -> bool:
        if self.allow_sensitive_paths:
            return False
        relative = path.relative_to(self.root)
        name = relative.name.lower()
        return (
            ".git" in relative.parts
            or name in self.DEFAULT_SENSITIVE_NAMES
            or name.startswith(".env.")
            or relative.suffix.lower() in self.DEFAULT_SENSITIVE_SUFFIXES
        )

    def _path(self, relative: str) -> Path:
        if not relative or Path(relative).is_absolute():
            raise ToolRuntimeError("repo_path_invalid", "path must be a non-empty relative path")
        target = (self.root / relative).resolve()
        if target != self.root and self.root not in target.parents:
            raise ToolRuntimeError("repo_path_escape", relative)
        if self._is_sensitive(target):
            raise ToolRuntimeError("repo_sensitive_path_denied", relative)
        return target

    def read_spec(self) -> ToolSpec:
        def read(args: dict[str, Any]) -> dict[str, Any]:
            path = self._path(args["path"])
            if not path.is_file():
                raise ToolRuntimeError("repo_file_not_found", args["path"])
            data = path.read_bytes()
            return {"path": path.relative_to(self.root).as_posix(), "content": data.decode("utf-8"), "fingerprint": _fingerprint_bytes(data)}
        return ToolSpec(
            "repo.read", "Read one UTF-8 repository file. Secret-bearing paths are excluded by host policy.",
            {"type": "object", "additionalProperties": False, "required": ["path"], "properties": {"path": {"type": "string"}}},
            read, "filesystem_read",
        )

    def search_spec(self) -> ToolSpec:
        def search(args: dict[str, Any]) -> dict[str, Any]:
            query = args["query"]
            if not query:
                return {"query": query, "matches": []}
            max_matches = min(max(int(args.get("max_matches", 40)), 1), 200)
            matches: list[dict[str, Any]] = []
            for path in sorted(self.root.rglob("*")):
                if len(matches) >= max_matches:
                    break
                if not path.is_file() or self._is_sensitive(path.resolve()):
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if query in line:
                        matches.append({"path": path.relative_to(self.root).as_posix(), "line": lineno, "text": line[:1000]})
                        if len(matches) >= max_matches:
                            break
            return {"query": query, "matches": matches}
        return ToolSpec(
            "repo.search", "Search non-sensitive UTF-8 repository files for a literal string.",
            {"type": "object", "additionalProperties": False, "required": ["query"], "properties": {"query": {"type": "string"}, "max_matches": {"type": "integer"}}},
            search, "filesystem_read",
        )

    def write_spec(self) -> ToolSpec:
        def write(args: dict[str, Any]) -> dict[str, Any]:
            path = self._path(args["path"])
            before = "absent" if not path.exists() else _fingerprint_bytes(path.read_bytes())
            if before != args["expected_before_fingerprint"]:
                raise ToolRuntimeError("repo_before_state_mismatch", f"expected {args['expected_before_fingerprint']}, got {before}")
            if path.exists() and not path.is_file():
                raise ToolRuntimeError("repo_target_not_file", args["path"])
            content = args["content"].encode("utf-8")
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=".qf-write-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            after = _fingerprint_bytes(content)
            if _fingerprint_bytes(path.read_bytes()) != after:
                raise ToolRuntimeError("repo_postcondition_failed", args["path"])
            return {"path": path.relative_to(self.root).as_posix(), "before_fingerprint": before, "after_fingerprint": after}
        return ToolSpec(
            "repo.write", "Replace one non-sensitive UTF-8 repository file with exact before-state validation.",
            {"type": "object", "additionalProperties": False, "required": ["path", "content", "expected_before_fingerprint"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "expected_before_fingerprint": {"type": "string"}}},
            write, "filesystem_write", required_authority="filesystem_write", side_effect=True, idempotency_required=True,
        )

    def register(self, runtime: ToolRuntime, *, include_write: bool = False) -> None:
        runtime.register(self.read_spec())
        runtime.register(self.search_spec())
        if include_write:
            runtime.register(self.write_spec())


class SubprocessToolset:
    DEFAULT_ENV_ALLOWLIST = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP"}

    def __init__(self, root: Path, allowed_executables: set[str], *, env_allowlist: set[str] | None = None) -> None:
        self.root = root.expanduser().resolve()
        self.allowed_executables = set(allowed_executables)
        self.env_allowlist = set(env_allowlist or self.DEFAULT_ENV_ALLOWLIST)

    def run_spec(self) -> ToolSpec:
        def run(args: dict[str, Any]) -> dict[str, Any]:
            argv = args["argv"]
            if not argv or argv[0] not in self.allowed_executables:
                raise ToolRuntimeError("process_executable_denied", argv[0] if argv else "")
            cwd = (self.root / args.get("cwd", ".")).resolve()
            if cwd != self.root and self.root not in cwd.parents:
                raise ToolRuntimeError("process_cwd_escape", str(cwd))
            timeout = min(max(int(args.get("timeout_seconds", 60)), 1), 300)
            safe_env = {name: os.environ[name] for name in self.env_allowlist if name in os.environ}
            proc = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False, shell=False, env=safe_env)
            return {"argv": argv, "cwd": cwd.relative_to(self.root).as_posix() or ".", "returncode": proc.returncode, "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:]}
        return ToolSpec(
            "process.run", "Run a host-allowlisted argv command without a shell or inherited secret environment.",
            {"type": "object", "additionalProperties": False, "required": ["argv"], "properties": {"argv": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}, "timeout_seconds": {"type": "integer"}}},
            run, "subprocess", required_authority="subprocess_execute", side_effect=True, idempotency_required=True,
        )

    def register(self, runtime: ToolRuntime) -> None:
        runtime.register(self.run_spec())
