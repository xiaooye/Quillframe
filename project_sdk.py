#!/usr/bin/env python3
"""Quillframe Project SDK.

Stdlib-only project scaffold / validate / build / spec tooling.
It treats a fiction project as a reproducible software project without making
artistic judgment or mutating Canon automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import tomllib

SDK_VERSION = "1"
PROJECT_SCHEMA = "quillframe_project_v1"
LOCK_SCHEMA = "quillframe_lock_v1"
ATTESTATION_SCHEMA = "quillframe_framework_attestation_v1"
DEFAULT_FRAMEWORK_VERSION = "0.9.0"
FRAMEWORK_ROOT = Path(__file__).resolve().parent

REQUIRED_DIRS = [
    "specs",
    "profiles",
    "bible/book",
    "bible/characters",
    "bible/relationships",
    "bible/world",
    "state/canon",
    "state/ledgers",
    "state/dependencies",
    "state/migrations",
    "plans/book",
    "plans/volumes",
    "plans/units",
    "plans/chapters",
    "plans/scene-cards",
    "manuscripts/draft",
    "manuscripts/review",
    "manuscripts/accepted",
    "evals/capability",
    "evals/regression",
    "evals/fixtures",
    "tests/continuity",
    "tests/state",
    "tests/release",
    "research/sources",
    "research/claims",
    "research/notes",
    "corpus/refs",
    "corpus/project-benchmarks",
    "assets",
    "scripts",
]

TEXT_EXTS = {".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".csv"}
IGNORE_PARTS = {".git", ".quillframe", "dist", "__pycache__"}
COMMIT_RE = re.compile(r"[0-9a-f]{40,64}")
FINGERPRINT_RE = re.compile(r"sha256:[0-9a-f]{64}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(path: Path, text: str) -> None:
    """Atomically replace one UTF-8 text file within its directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-") or "change"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", value.strip())
    if not match:
        raise ValueError(f"unsupported framework version format: {value}")
    major, minor, patch = match.groups()
    return int(major), int(minor or 0), int(patch or 0)


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"unable to inspect Framework git checkout: {type(exc).__name__}") from exc
    return result.stdout.strip()


def _framework_root(framework_root: Path | None = None) -> Path:
    root = (framework_root or FRAMEWORK_ROOT).expanduser().resolve()
    for rel in ("HARNESS_MANIFEST.yaml", "VERSION", "release/build_framework_bundle.py"):
        if not (root / rel).is_file():
            raise ValueError(f"not a complete Quillframe Framework checkout: missing {rel}")
    return root


def _require_project_outside_framework(project_root: Path, framework_root: Path) -> None:
    root = project_root.resolve()
    fw = framework_root.resolve()
    if root == fw or fw in root.parents:
        raise ValueError("fiction Project must live outside the generic Quillframe Framework checkout")


def framework_checkout_identity(framework_root: Path | None = None, *, require_clean: bool = True) -> dict[str, Any]:
    """Return exact identity for a materialized Quillframe source checkout."""
    root = _framework_root(framework_root)
    status = _git(root, "status", "--porcelain", "--untracked-files=normal")
    if require_clean and status:
        raise ValueError("Framework checkout is dirty; commit or stash changes before exact pinning")
    commit = _git(root, "rev-parse", "HEAD")
    if not COMMIT_RE.fullmatch(commit):
        raise ValueError("Framework git HEAD is not a supported exact commit id")
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError("Framework VERSION is empty")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from release.build_framework_bundle import build as build_framework_bundle
    except ImportError as exc:
        raise ValueError("unable to load deterministic Framework bundle builder") from exc
    with tempfile.TemporaryDirectory(prefix="quillframe-pin-") as td:
        report = build_framework_bundle(root, Path(td) / "framework.tar")
    fingerprint = report.get("bundle_fingerprint")
    content_index = report.get("content_index_fingerprint")
    if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
        raise ValueError("Framework bundle builder returned an invalid fingerprint")
    return {
        "name": "Quillframe",
        "version": version,
        "commit": commit,
        "bundle_fingerprint": fingerprint,
        "content_index_fingerprint": content_index,
    }


def framework_toml(project_id: str, title: str, language: str, version: str) -> str:
    return f'''# Quillframe project manifest. Project facts live in project-owned files, not here.
[quillframe]
schema = {toml_string(PROJECT_SCHEMA)}
project_schema_version = "1"
minimum_framework_version = {toml_string(version)}

[project]
id = {toml_string(project_id)}
title = {toml_string(title)}
language = {toml_string(language)}
version = "0.1.0"
status = "active"

[authority]
accepted_canon = "state/canon"
current_state = "state"
active_plans = "plans"
project_profiles = "profiles"
research = "research"
regressions = "evals/regression"

[paths]
bible = "bible"
state = "state"
plans = "plans"
manuscripts = "manuscripts"
profiles = "profiles"
evals = "evals"
tests = "tests"
research = "research"
corpus = "corpus"
specs = "specs"
assets = "assets"

[build]
output = "dist"
include_text_index = true
include_bootstrap_files = true

[quality]
framework_surface_fundamentals = true
framework_reader_engagement = true
independent_semantic_gate_supported = true
reader_simulation_supported = true
quality_evolution_supported = true
author_context_memory_controls_supported = true
'''


def lock_json(framework_version: str, commit: str | None = None, bundle_fingerprint: str | None = None) -> dict[str, Any]:
    return {
        "schema": LOCK_SCHEMA,
        "framework": {
            "name": "Quillframe",
            "version": framework_version,
            "commit": commit,
            "bundle_fingerprint": bundle_fingerprint,
        },
        "project_schema_version": "1",
        "updated_at": now_iso(),
    }


def attestation_json(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": ATTESTATION_SCHEMA,
        "framework": {key: identity.get(key) for key in ("name", "version", "commit", "bundle_fingerprint")},
        "content_index_fingerprint": identity.get("content_index_fingerprint"),
        "source": {"kind": "clean_git_checkout"},
        "attested_at": now_iso(),
    }


def readme_en(title: str) -> str:
    return f'''# {title}

This is a Quillframe fiction project repository.

## Authority

- Accepted Canon: `state/canon/`
- Current structured state: `state/`
- Active future plans: `plans/`
- Project-specific profiles: `profiles/`
- Research claims/sources: `research/`
- Draft/review/accepted manuscripts: `manuscripts/`
- Exact Framework identity: `quillframe.lock.json` + `framework.attestation.json`

Plans, drafts, runtime sessions, corpus, memory overlays, reader panels, revision reports, and semantic judgments are not Canon.

## Engineering workflow

```text
bootstrap → validate → plan/spec when required → produce → test/audit → explicit acceptance → settle → build/release
```

Run:

```bash
quillframe validate .
quillframe build .
```

Use `quillframe pin .` only for an explicit Framework repin. A normal authoring run must not silently replace the lock with a newer Framework checkout.
'''


def readme_zh(title: str) -> str:
    return f'''# {title}

这是一个 Quillframe 小说工程仓库。

## 权威

- Accepted Canon：`state/canon/`
- 当前结构化状态：`state/`
- 当前未来计划：`plans/`
- 项目专属 profiles：`profiles/`
- Research claims / sources：`research/`
- Draft / Review / Accepted 正文：`manuscripts/`
- 精确 Framework identity：`quillframe.lock.json` + `framework.attestation.json`

Plan、Draft、runtime session、Corpus、memory overlay、Reader Panel、revision report、semantic judgment 都不是 Canon。

## 工程流程

```text
bootstrap → validate → 需要时 spec/plan → produce → test/audit → explicit acceptance → settle → build/release
```

运行：

```bash
quillframe validate .
quillframe build .
```

只有显式升级 Framework 时才运行 `quillframe pin .`。普通创作 run 不得静默把 Project lock 换成更新的 Framework checkout。
'''


def agents_md() -> str:
    return '''# Quillframe Project Agent Bootstrap

Read `quillframe.toml`, `quillframe.lock.json`, and `framework.attestation.json` before project work, then load the exact pinned Quillframe Framework bootstrap.

Rules:
- project repository owns project facts, plans, profiles, research, manuscripts and Canon;
- framework owns generic mechanisms;
- plan/review/session/corpus/memory overlay/reader-panel/revision-report/semantic result are not Canon;
- determine exactly one task mode;
- build sparse context rather than loading the entire repository;
- author-visible memory/context controls affect retrieval or proposals, never silently mutate Canon;
- checkpoint before external waits and consequential writes;
- Canon mutation requires explicit acceptance + settlement transaction;
- do not silently repin the Framework during ordinary production;
- run project validation/tests before release or structural migration completion.
'''


def claude_md() -> str:
    return '''# Claude Code · Quillframe Project Host

@AGENTS.md

The project-local Claude hook verifies the exact Framework lock/attestation and injects current bootstrap state at session start. Claude Code is a host, not the source of Project or Framework authority.
'''


def independent_reviewer_instruction() -> str:
    return '''You are Quillframe's native independent reviewer for exactly one frozen packet.

Use ONLY the frozen packet injected by the trusted lifecycle hook. Do not inspect or infer from the Project, filesystem, shell, network, memory, host conversation, or any write-capable tool. Do not call tools.

Return ONLY one JSON object matching the packet's judgment output contract. Do not return markdown, commentary, chain-of-thought, an outer semantic-result envelope, candidate text, or Project paths. The trusted hook owns lifecycle identity, provider identity, the frozen nonce, deterministic result wrapping, and submission.
'''


def codex_independent_reviewer_toml() -> str:
    instruction = independent_reviewer_instruction().replace('"""', '\\"\\"\\"')
    return f'''name = "quillframe-independent-reviewer"
description = "Review one exact frozen Quillframe packet in a separate native context without tools."
developer_instructions = """{instruction}"""
'''


def claude_independent_reviewer_md() -> str:
    return f'''---
name: quillframe-independent-reviewer
description: Review one exact frozen Quillframe packet in a separate native context.
tools: []
permissionMode: plan
---

{independent_reviewer_instruction()}'''


def codex_hooks_json() -> str:
    command = "quillframe codex-hook"
    hook = {"type": "command", "command": command, "timeout": 30}
    context_hook = {**hook, "additionalContextLimit": 6000}
    value = {
        "description": "Quillframe Project bootstrap, native reviewer lifecycle, and execution guard. Review/trust with /hooks before use.",
        "hooks": {
            "SessionStart": [
                {"matcher": "startup|resume|clear|compact", "hooks": [context_hook]},
            ],
            "UserPromptSubmit": [{"hooks": [context_hook]}],
            "SubagentStart": [
                {"matcher": "quillframe-independent-reviewer", "hooks": [context_hook]},
            ],
            "SubagentStop": [
                {"matcher": "quillframe-independent-reviewer", "hooks": [context_hook]},
            ],
            "PreToolUse": [
                {"matcher": "Bash|apply_patch|Edit|Write", "hooks": [context_hook]},
                {"matcher": ".*", "hooks": [context_hook]},
            ],
            "PostToolUse": [
                {"matcher": "Bash|apply_patch|Edit|Write", "hooks": [context_hook]},
            ],
            "SessionEnd": [{"hooks": [hook]}],
        },
    }
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def claude_settings_json() -> str:
    return json.dumps(
        {
            "permissions": {"ask": ["Skill"]},
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup|resume|clear|compact",
                        "hooks": [{"type": "command", "command": "quillframe claude-hook"}],
                    }
                ],
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": "quillframe claude-hook"}]}
                ],
                "SubagentStart": [
                    {
                        "matcher": "quillframe-independent-reviewer",
                        "hooks": [{"type": "command", "command": "quillframe claude-hook"}],
                    }
                ],
                "SubagentStop": [
                    {
                        "matcher": "quillframe-independent-reviewer",
                        "hooks": [{"type": "command", "command": "quillframe claude-hook"}],
                    }
                ],
                "PreToolUse": [
                    {
                        "matcher": "Write|Edit|Bash|Skill",
                        "hooks": [{"type": "command", "command": "quillframe claude-hook"}],
                    },
                    {
                        "matcher": ".*",
                        "hooks": [{"type": "command", "command": "quillframe claude-hook"}],
                    },
                ],
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write|Bash",
                        "hooks": [{"type": "command", "command": "quillframe claude-hook"}],
                    }
                ],
                "SessionEnd": [
                    {"hooks": [{"type": "command", "command": "quillframe claude-hook"}]}
                ],
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def gitignore() -> str:
    return '''.quillframe/
dist/
__pycache__/
*.pyc
.env
.env.*
.DS_Store
'''


def profile_template(name: str) -> str:
    return f'''schema: quillframe_profile_v1
profile_type: {name}
status: active
# Add only project-specific overrides/weights here.
# Framework Surface Fundamentals remain enabled by default.
'''


def _pin_payload(framework_root: Path | None, minimum_version: str) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = framework_checkout_identity(framework_root)
    if _version_tuple(identity["version"]) < _version_tuple(minimum_version):
        raise ValueError(f"Framework {identity['version']} is below project minimum {minimum_version}")
    return (
        lock_json(identity["version"], identity["commit"], identity["bundle_fingerprint"]),
        attestation_json(identity),
    )


def init_project(
    root: Path,
    project_id: str,
    title: str,
    language: str,
    framework_version: str,
    force: bool,
    framework_root: Path | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    fw_root = _framework_root(framework_root)
    _require_project_outside_framework(root, fw_root)
    if root.exists() and any(root.iterdir()) and not force:
        raise ValueError(f"target directory is not empty: {root}; use --force only when intentional")
    lock, attestation = _pin_payload(fw_root, framework_version)
    root.mkdir(parents=True, exist_ok=True)
    for rel in REQUIRED_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    write(root / "quillframe.toml", framework_toml(project_id, title, language, framework_version))
    write(root / "framework.attestation.json", json.dumps(attestation, ensure_ascii=False, indent=2) + "\n")
    # Lock is written after evidence so a partial failure cannot advertise a new
    # Project authority without its matching attestation.
    write(root / "quillframe.lock.json", json.dumps(lock, ensure_ascii=False, indent=2) + "\n")
    write(root / "README.en.md", readme_en(title))
    write(root / "README.zh-CN.md", readme_zh(title))
    write(root / "AGENTS.md", agents_md())
    write(root / "CLAUDE.md", claude_md())
    write(root / ".claude" / "settings.json", claude_settings_json())
    write(root / ".claude" / "agents" / "quillframe-independent-reviewer.md", claude_independent_reviewer_md())
    write(root / ".codex" / "hooks.json", codex_hooks_json())
    write(root / ".codex" / "agents" / "quillframe-independent-reviewer.toml", codex_independent_reviewer_toml())
    write(root / ".gitignore", gitignore())
    for name in ("genre", "platform", "prose", "reader", "project"):
        write(root / "profiles" / f"{name}.yaml", profile_template(name))
    write(root / "state" / "canon" / "README.md", "# Accepted Canon\n\nOnly explicitly accepted and settled project facts/artifacts belong here.\n")
    write(root / "plans" / "README.md", "# Active Plans\n\nFuture intent only. Plan is never current Canon.\n")
    write(root / "manuscripts" / "README.md", "# Manuscripts\n\nLifecycle: draft → review → accepted. Acceptance still requires settlement for structured state mutation.\n")
    return {
        "project_root": str(root),
        "project_id": project_id,
        "initialized": True,
        "framework_pin": lock["framework"],
        "authority_ready": True,
    }


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "quillframe.toml"
    if not path.exists():
        raise ValueError("missing quillframe.toml")
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if not isinstance(data, dict):
        raise ValueError("quillframe.toml must parse to object")
    return data


def load_lock(root: Path) -> dict[str, Any]:
    path = root / "quillframe.lock.json"
    if not path.exists():
        raise ValueError("missing quillframe.lock.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("lockfile must be object")
    return value


def load_attestation(root: Path) -> dict[str, Any]:
    path = root / "framework.attestation.json"
    if not path.exists():
        raise ValueError("missing framework.attestation.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("framework attestation must be object")
    return value


def _exact_framework_fields(framework: Any) -> tuple[bool, list[str]]:
    problems: list[str] = []
    if not isinstance(framework, dict):
        return False, ["framework lock must be object"]
    if framework.get("name") != "Quillframe":
        problems.append("framework.name must be Quillframe")
    if not framework.get("version"):
        problems.append("framework.version required")
    commit = framework.get("commit")
    if commit is None:
        problems.append("framework.commit is not pinned")
    elif not COMMIT_RE.fullmatch(str(commit)):
        problems.append("framework.commit must be an exact lowercase git commit id")
    fingerprint = framework.get("bundle_fingerprint")
    if fingerprint is None:
        problems.append("framework.bundle_fingerprint is not pinned")
    elif not FINGERPRINT_RE.fullmatch(str(fingerprint)):
        problems.append("framework.bundle_fingerprint must be sha256:<64 lowercase hex>")
    return not problems, problems


def project_authority_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    try:
        lock = load_lock(root)
    except Exception as exc:
        return {
            "authority_ready": False,
            "errors": [str(exc)],
            "framework_lock": None,
            "framework_attestation": None,
        }
    framework = lock.get("framework", {}) if isinstance(lock, dict) else {}
    exact, exact_problems = _exact_framework_fields(framework)
    errors.extend(exact_problems)
    attestation: dict[str, Any] | None = None
    try:
        attestation = load_attestation(root)
    except Exception as exc:
        errors.append(str(exc))
    if attestation is not None:
        if attestation.get("schema") != ATTESTATION_SCHEMA:
            errors.append("framework attestation schema must be quillframe_framework_attestation_v1")
        att_framework = attestation.get("framework")
        if not isinstance(att_framework, dict):
            errors.append("framework attestation framework must be object")
        else:
            for key in ("name", "version", "commit", "bundle_fingerprint"):
                if att_framework.get(key) != framework.get(key):
                    errors.append(f"framework attestation mismatch: {key}")
    return {
        "authority_ready": exact and not errors,
        "errors": errors,
        "framework_lock": framework,
        "framework_attestation": attestation,
    }


def verify_materialized_framework(root: Path, framework_root: Path | None = None) -> dict[str, Any]:
    """Verify a Project's exact lock/attestation against local Framework bytes."""
    local = project_authority_status(root)
    errors = list(local["errors"])
    actual: dict[str, Any] | None = None
    if local["authority_ready"]:
        try:
            actual = framework_checkout_identity(framework_root)
        except Exception as exc:
            errors.append(str(exc))
    if actual is not None:
        expected = local["framework_lock"]
        for key in ("name", "version", "commit", "bundle_fingerprint"):
            if actual.get(key) != expected.get(key):
                errors.append(f"materialized Framework mismatch: {key}")
    return {
        **local,
        "errors": errors,
        "materialized_authority_verified": actual is not None and not errors,
        "materialized_framework": actual,
    }


def pin_project(root: Path, framework_root: Path | None = None) -> dict[str, Any]:
    root = root.expanduser().resolve()
    fw_root = _framework_root(framework_root)
    _require_project_outside_framework(root, fw_root)
    manifest = load_manifest(root)
    lock_path = root / "quillframe.lock.json"
    attestation_path = root / "framework.attestation.json"
    old_lock_text = lock_path.read_text(encoding="utf-8")
    old_lock = json.loads(old_lock_text)
    old_attestation_text = attestation_path.read_text(encoding="utf-8") if attestation_path.exists() else None
    minimum = str(manifest.get("quillframe", {}).get("minimum_framework_version") or DEFAULT_FRAMEWORK_VERSION)
    new_lock, new_attestation = _pin_payload(fw_root, minimum)
    try:
        write(attestation_path, json.dumps(new_attestation, ensure_ascii=False, indent=2) + "\n")
        write(lock_path, json.dumps(new_lock, ensure_ascii=False, indent=2) + "\n")
        status = project_authority_status(root)
        if not status["authority_ready"]:
            raise ValueError("post-pin authority verification failed: " + "; ".join(status["errors"]))
    except Exception:
        write(lock_path, old_lock_text)
        if old_attestation_text is None:
            attestation_path.unlink(missing_ok=True)
        else:
            write(attestation_path, old_attestation_text)
        raise
    return {
        "pinned": True,
        "project_root": str(root),
        "previous_framework": old_lock.get("framework", {}),
        "framework": new_lock["framework"],
        "authority_ready": True,
    }


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORE_PARTS for part in rel.parts):
            continue
        yield path, rel


def classify(rel: Path) -> str:
    first = rel.parts[0] if rel.parts else ""
    if first == "state": return "authority_state"
    if first == "bible": return "authority_bible"
    if first == "profiles": return "authority_profile"
    if first == "research": return "authority_research"
    if first == "plans": return "plan"
    if first == "manuscripts":
        if len(rel.parts) > 1 and rel.parts[1] == "accepted": return "accepted_manuscript"
        return "generated_manuscript"
    if first == "evals": return "eval"
    if first == "specs": return "engineering_spec"
    if first == "corpus": return "corpus_reference"
    if first == "tests": return "test"
    if first == "assets": return "asset"
    return "project_meta"


def validate_bilingual_specs(root: Path) -> list[str]:
    errors: list[str] = []
    specs = root / "specs"
    if not specs.exists():
        return errors
    for feature in sorted(p for p in specs.iterdir() if p.is_dir()):
        if not any(feature.glob("*.md")):
            continue
        for stem in ("spec", "plan", "tasks"):
            en = feature / f"{stem}.en.md"
            zh = feature / f"{stem}.zh-CN.md"
            if en.exists() != zh.exists():
                errors.append(f"bilingual spec pair missing in {feature.name}: {stem}")
    return errors


def _structural_framework_errors(framework: Any) -> list[str]:
    """Malformed explicit values are structural errors; missing legacy pins are warnings."""
    errors: list[str] = []
    if not isinstance(framework, dict):
        return ["framework lock must be object"]
    if framework.get("name") not in (None, "Quillframe"):
        errors.append("framework.name must be Quillframe")
    if not framework.get("version"):
        errors.append("framework.version required")
    commit = framework.get("commit")
    if commit is not None and not COMMIT_RE.fullmatch(str(commit)):
        errors.append("framework.commit must be an exact lowercase git commit id when present")
    fingerprint = framework.get("bundle_fingerprint")
    if fingerprint is not None and not FINGERPRINT_RE.fullmatch(str(fingerprint)):
        errors.append("framework.bundle_fingerprint must be sha256:<64 lowercase hex> when present")
    return errors


def validate_project(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_manifest(root)
    except Exception as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": warnings, "authority_ready": False}
    try:
        lock = load_lock(root)
    except Exception as exc:
        errors.append(str(exc))
        lock = {}
    quillframe = manifest.get("quillframe", {})
    project = manifest.get("project", {})
    if quillframe.get("schema") != PROJECT_SCHEMA:
        errors.append("quillframe.schema must be quillframe_project_v1")
    for key in ("id", "title", "language", "version", "status"):
        if not project.get(key):
            errors.append(f"project.{key} required")
    if lock and lock.get("schema") != LOCK_SCHEMA:
        errors.append("lock schema must be quillframe_lock_v1")
    framework_lock = lock.get("framework", {}) if isinstance(lock, dict) else {}
    errors.extend(_structural_framework_errors(framework_lock))

    authority = project_authority_status(root) if lock else {
        "authority_ready": False,
        "errors": ["missing exact Framework authority"],
        "framework_lock": framework_lock,
        "framework_attestation": None,
    }
    if not authority["authority_ready"]:
        warnings.extend(f"authority: {problem}" for problem in authority["errors"])

    for rel in REQUIRED_DIRS:
        if not (root / rel).is_dir():
            errors.append(f"missing required directory: {rel}")
    for rel in ("README.en.md", "README.zh-CN.md", "AGENTS.md", "CLAUDE.md", ".gitignore"):
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")
    errors.extend(validate_bilingual_specs(root))

    accepted = root / "manuscripts" / "accepted"
    if accepted.exists():
        for path in accepted.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(accepted)
            for sibling in (root / "manuscripts" / "draft" / rel, root / "manuscripts" / "review" / rel):
                if sibling.exists():
                    warnings.append(f"same manuscript path exists in multiple lifecycle dirs: {rel}")
    profiles = root / "profiles"
    for profile in profiles.glob("*.yaml") if profiles.exists() else []:
        text = profile.read_text(encoding="utf-8", errors="replace")
        if re.search(r"framework_surface_fundamentals\s*:\s*false", text, re.I):
            errors.append(f"profile attempts to disable framework Surface Fundamentals: {profile.relative_to(root)}")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "project_id": project.get("id"),
        "project_version": project.get("version"),
        "framework_lock": framework_lock,
        "framework_attestation": authority.get("framework_attestation"),
        "authority_ready": authority["authority_ready"],
        "authority_errors": authority["errors"],
    }


def build_project(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    validation = validate_project(root)
    if not validation["valid"]:
        raise ValueError("project validation failed: " + "; ".join(validation["errors"]))
    if not validation["authority_ready"]:
        raise ValueError(
            "project exact Framework authority is not ready; run an explicit `quillframe pin` after reviewing the dependency change"
        )
    manifest = load_manifest(root)
    lock = load_lock(root)
    files = []
    bootstrap: dict[str, str] = {}
    for path, rel in iter_files(root):
        data = path.read_bytes()
        item = {
            "path": rel.as_posix(),
            "class": classify(rel),
            "size": len(data),
            "fingerprint": sha256_bytes(data),
        }
        files.append(item)
        if rel.as_posix() in {
            "quillframe.toml",
            "quillframe.lock.json",
            "framework.attestation.json",
            "README.en.md",
            "README.zh-CN.md",
            "AGENTS.md",
            "CLAUDE.md",
            ".claude/settings.json",
        }:
            bootstrap[rel.as_posix()] = data.decode("utf-8", errors="replace")
    content_index_hash = sha256_bytes(canonical_json(files).encode("utf-8"))
    payload = {
        "schema": "quillframe_project_bundle_v1",
        "sdk_version": SDK_VERSION,
        "built_at": now_iso(),
        "project": manifest.get("project", {}),
        "framework_lock": lock.get("framework", {}),
        "authority": manifest.get("authority", {}),
        "paths": manifest.get("paths", {}),
        "bootstrap": bootstrap,
        "content_index": files,
        "content_index_fingerprint": content_index_hash,
    }
    payload["bundle_fingerprint"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    out = root / "dist"
    out.mkdir(parents=True, exist_ok=True)
    write(out / "project.bundle.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    classes: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        classes.setdefault(item["class"], []).append(item)
    for name, values in classes.items():
        write(
            out / f"{name}.manifest.json",
            json.dumps({"schema": "quillframe_file_manifest_v1", "class": name, "files": values}, ensure_ascii=False, indent=2) + "\n",
        )
    write(
        out / "fingerprints.json",
        json.dumps(
            {"bundle_fingerprint": payload["bundle_fingerprint"], "content_index_fingerprint": content_index_hash},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )
    return {
        "built": True,
        "output": str(out),
        "file_count": len(files),
        "bundle_fingerprint": payload["bundle_fingerprint"],
    }


def next_spec_number(root: Path) -> int:
    specs = root / "specs"
    nums = []
    if specs.exists():
        for path in specs.iterdir():
            if path.is_dir() and re.match(r"^(\d{3})-", path.name):
                nums.append(int(path.name[:3]))
    return max(nums, default=0) + 1


def spec_template(kind: str, title: str, lang: str) -> str:
    if lang == "en":
        if kind == "spec":
            return f'''# Specification · {title}\n\nStatus: Draft\n\n## Problem / Context\n\n## Current-state Audit\n\n## User / Editorial Value\n\n## Requirements\n\n## Non-goals\n\n## Authority / Canon Impact\n\n## Reader / Prose Impact\n\n## Compatibility Constraints\n\n## Acceptance Scenarios\n\n## Risks\n'''
        if kind == "plan":
            return f'''# Implementation Plan · {title}\n\n## Chosen Architecture\n\n## Alternatives Considered\n\n## Affected Objects / Paths\n\n## Dependency Graph\n\n## Migration Strategy\n\n## Test / Eval Strategy\n\n## Phases / Checkpoints\n\n## Rollback\n'''
        return f'''# Tasks · {title}\n\nFormat: `[ID] [P?] [Phase/Story] exact target + completion criterion`\n\n## Phase 1 · Foundation\n\n- [ ] T001 Define exact targets and before-state.\n\n### Checkpoint\n- [ ] Validation passes before next phase.\n'''
    if kind == "spec":
        return f'''# 规格说明 · {title}\n\n状态：Draft\n\n## 问题 / 背景\n\n## 当前状态审计\n\n## 用户 / 编辑价值\n\n## Requirements\n\n## Non-goals\n\n## Authority / Canon 影响\n\n## Reader / Prose 影响\n\n## 兼容性约束\n\n## 验收场景\n\n## 风险\n'''
    if kind == "plan":
        return f'''# 实施计划 · {title}\n\n## 选定架构\n\n## 备选方案\n\n## 影响对象 / 路径\n\n## Dependency Graph\n\n## Migration Strategy\n\n## Test / Eval Strategy\n\n## Phases / Checkpoints\n\n## Rollback\n'''
    return f'''# 任务 · {title}\n\n格式：`[ID] [P?] [Phase/Story] 精确 target + 完成标准`\n\n## Phase 1 · Foundation\n\n- [ ] T001 定义 exact targets 与 before-state。\n\n### Checkpoint\n- [ ] 进入下一阶段前 validation 必须通过。\n'''


def create_spec(root: Path, title: str) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not (root / "quillframe.toml").exists():
        raise ValueError("not a Quillframe project")
    number = next_spec_number(root)
    target = root / "specs" / f"{number:03d}-{slugify(title)}"
    target.mkdir(parents=True, exist_ok=False)
    for kind in ("spec", "plan", "tasks"):
        write(target / f"{kind}.en.md", spec_template(kind, title, "en"))
        write(target / f"{kind}.zh-CN.md", spec_template(kind, title, "zh"))
    return {"created": True, "spec_dir": str(target), "number": number}


def projection_preview(root: Path) -> dict[str, Any]:
    """Compile an optional mapped runtime manifest without mutating SQLite."""
    from harness.project_projection import preview
    return preview(root)


def projection_apply(root: Path, data_dir: Path | None = None, expected_projection_fingerprint: str | None = None) -> dict[str, Any]:
    from harness.project_projection import apply
    return apply(root, data_dir=data_dir, expected_projection_fingerprint=expected_projection_fingerprint)


def projection_status(root: Path, data_dir: Path | None = None) -> dict[str, Any]:
    from harness.project_projection import status
    return status(root, data_dir=data_dir)


def projection_preflight(root: Path, target_id: str, stage: str, data_dir: Path | None = None) -> dict[str, Any]:
    from harness.project_projection import preflight
    return preflight(root, target_id, stage, data_dir=data_dir)


def self_test(tmp_root: Path) -> dict[str, Any]:
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    init_project(tmp_root, "PROJECT-TEST", "Fixture Novel", "en", DEFAULT_FRAMEWORK_VERSION, False)
    spec = create_spec(tmp_root, "Volume architecture change")
    validation = validate_project(tmp_root)
    build = build_project(tmp_root)
    manifest = load_manifest(tmp_root)
    quality = manifest.get("quality", {})
    ok = (
        validation["valid"]
        and validation["authority_ready"]
        and (tmp_root / "framework.attestation.json").exists()
        and (tmp_root / ".claude" / "settings.json").exists()
        and Path(build["output"], "project.bundle.json").exists()
        and Path(spec["spec_dir"], "tasks.zh-CN.md").exists()
        and quality.get("reader_simulation_supported") is True
        and quality.get("quality_evolution_supported") is True
        and quality.get("author_context_memory_controls_supported") is True
    )
    return {
        "project_sdk_contract": "PASS" if ok else "FAIL",
        "framework_default": DEFAULT_FRAMEWORK_VERSION,
        "scaffold": True,
        "validate": validation["valid"],
        "authority_ready": validation["authority_ready"],
        "exact_framework_pin": True,
        "bilingual_specs": True,
        "reproducible_bundle": True,
        "software_project_contract": True,
        "quality_control_scaffold": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe Project SDK")
    sub = parser.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init")
    init.add_argument("path")
    init.add_argument("--id", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--language", default="en")
    init.add_argument("--framework-version", default=DEFAULT_FRAMEWORK_VERSION)
    init.add_argument("--framework-root")
    init.add_argument("--force", action="store_true")
    validate = sub.add_parser("validate")
    validate.add_argument("path")
    build = sub.add_parser("build")
    build.add_argument("path")
    pin = sub.add_parser("pin")
    pin.add_argument("path")
    pin.add_argument("--framework-root")
    spec = sub.add_parser("spec-new")
    spec.add_argument("path")
    spec.add_argument("--title", required=True)
    test = sub.add_parser("self-test")
    test.add_argument("--tmp", default="/tmp/quillframe-project-sdk-self-test")
    args = parser.parse_args()
    try:
        if args.cmd == "init":
            result = init_project(
                Path(args.path),
                args.id,
                args.title,
                args.language,
                args.framework_version,
                args.force,
                Path(args.framework_root) if args.framework_root else None,
            )
        elif args.cmd == "validate":
            result = validate_project(Path(args.path))
        elif args.cmd == "build":
            result = build_project(Path(args.path))
        elif args.cmd == "pin":
            result = pin_project(Path(args.path), Path(args.framework_root) if args.framework_root else None)
        elif args.cmd == "spec-new":
            result = create_spec(Path(args.path), args.title)
        else:
            result = self_test(Path(args.tmp))
        dump(result)
        if args.cmd == "validate":
            return 0 if result["valid"] else 1
        if args.cmd == "self-test":
            return 0 if result["project_sdk_contract"] == "PASS" else 1
        return 0
    except Exception as exc:
        dump({"error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
