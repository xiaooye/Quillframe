#!/usr/bin/env python3
"""Project-local host scaffold/repair helpers.

Host integration files are execution adapters only. This module never changes
Project lock/attestation, story state, Canon, plans, manuscripts, or profiles.
Unknown user-authored host files fail safe unless explicit force replacement is
requested.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _load_source_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_sdk() -> ModuleType:
    return _load_source_module("quillframe_project_sdk_scaffold", ROOT / "project_sdk.py")


def project_agents_md() -> str:
    return '''# Quillframe Project Agent Bootstrap

This repository is a **consumer fiction Project**. Project facts, characters, relationships, plans, research, manuscripts, current state, and Canon belong here; generic mechanisms belong to the exact pinned Quillframe Framework.

## Mandatory startup

1. Read `quillframe.toml`, `quillframe.lock.json`, and `framework.attestation.json`.
2. Load the exact pinned Quillframe bootstrap contracts (`HARNESS_MANIFEST.yaml`, `SKILL`, `harness/HARNESS_AGENT`, Project adapter/protocol) through the verified Framework host/runtime.
3. Require a Quillframe host bootstrap context containing `QF_SESSION_ID`. If it is absent, **do not perform consequential Project writes**. In Codex, review/trust the Project hooks with `/hooks` and restart; in Claude Code, repair the Project host files with `quillframe host-install .` and restart.
4. Determine exactly one primary Quillframe `task_mode` from the user task. Do not combine user-visible modes.
5. Execute the exact `quillframe host-run begin --session-id ... --mode ...` command injected by the host bootstrap before consequential work.
6. Confirm the host state becomes `running` with one active manager run, then build sparse Context from current Project authority.
7. For `DRAFT` / `REVISE`, resolve a real Quillframe production runtime before producing manuscript text. If the host lacks a bound runtime, materialize the exact locked Framework in an ephemeral sandbox, verify its Git identity, and invoke the typed production bridge. If runtime/model/independent-review capability is unavailable, return the typed pending/blocked state; **never synthesize a Quillframe manuscript in the host itself**.
8. Surface production manuscript text only through an exact fingerprint-bound production release (`candidate.visible.get` or an equivalent Core-owned released projection). Raw Draft, pending candidates, failed candidates, and host-authored substitutes are not user-visible Review Drafts.

## Authority rules

- `stored != injected`; `relevant != authoritative`.
- `Plan != Canon`; `Review != Accepted`; `Accepted != Settled`.
- Session history, host memory, telemetry, model inference, Corpus, and Research are not Canon.
- Do not silently repin the Framework during ordinary production.
- Canon mutation requires explicit Project acceptance plus the settlement transaction.
- Checkpoint before external waits and consequential writes.
- Mandatory independent semantic review must use a genuinely separate invocation/session when the active mode requires it.

Claude Code and Codex are hosts. Neither host, its skills, its memory, nor its tool permissions replace Quillframe workflow or authority.
'''


def codex_hooks_json() -> str:
    return project_sdk().codex_hooks_json()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.quillframe.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _safe_install_text(
    path: Path,
    desired: str,
    *,
    known_generated: set[str],
    force: bool,
) -> tuple[str, str | None]:
    if not path.exists():
        _atomic_write(path, desired)
        return "created", None
    current = path.read_text(encoding="utf-8")
    if current == desired:
        return "unchanged", None
    if current in known_generated or force:
        _atomic_write(path, desired)
        return "updated", None
    return "manual_merge_required", f"refusing to overwrite unknown user-authored file: {path}"


def install_project_hosts(root: Path, *, force: bool = False) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not (root / "quillframe.toml").is_file():
        raise ValueError("not a Quillframe Project: missing quillframe.toml")
    sdk = project_sdk()

    desired_agents = project_agents_md()
    generated_agents = sdk.agents_md()
    desired_claude = sdk.claude_md()
    desired_claude_settings = sdk.claude_settings_json()
    desired_codex_hooks = sdk.codex_hooks_json()
    desired_codex_reviewer = sdk.codex_independent_reviewer_toml()
    desired_claude_reviewer = sdk.claude_independent_reviewer_md()

    specs = [
        (root / "AGENTS.md", desired_agents, {generated_agents, desired_agents}),
        (root / "CLAUDE.md", desired_claude, {desired_claude}),
        (root / ".claude" / "settings.json", desired_claude_settings, {desired_claude_settings}),
        (root / ".codex" / "hooks.json", desired_codex_hooks, {desired_codex_hooks}),
        (
            root / ".codex" / "agents" / "quillframe-independent-reviewer.toml",
            desired_codex_reviewer,
            {desired_codex_reviewer},
        ),
        (
            root / ".claude" / "agents" / "quillframe-independent-reviewer.md",
            desired_claude_reviewer,
            {desired_claude_reviewer},
        ),
    ]
    results: dict[str, str] = {}
    warnings: list[str] = []
    for path, desired, known in specs:
        status, warning = _safe_install_text(path, desired, known_generated=known, force=force)
        results[path.relative_to(root).as_posix()] = status
        if warning:
            warnings.append(warning)

    changed = sorted(path for path, status in results.items() if status in {"created", "updated"})
    manual = sorted(path for path, status in results.items() if status == "manual_merge_required")
    return {
        "schema": "quillframe_host_install_v1",
        "project_root": str(root),
        "installed": not manual,
        "changed": changed,
        "manual_merge_required": manual,
        "files": results,
        "warnings": warnings,
        "framework_repin": False,
        "canon_mutation": False,
    }
