"""Deterministic identity for the code and contracts that execute production runs."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOTS = (
    "agent_runtime",
    "model_runtime",
    "production_runtime",
    "quality",
    "persistence",
    "harness",
    "learning",
    "corpus",
    "surface",
    "quillframe",
)
ROOT_FILES = (
    "VERSION",
    "HARNESS_MANIFEST.yaml",
    "pyproject.toml",
    "core_operations.py",
    "project_resolution.py",
)
INCLUDED_SUFFIXES = {".py", ".json", ".sql", ".md", ".yaml", ".yml"}


def framework_build_identity(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    paths: list[Path] = []
    for relative in ROOT_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"framework build input unavailable: {relative}")
        paths.append(path)
    for relative in BUILD_ROOTS:
        base = root / relative
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"framework build root unavailable: {relative}")
        paths.extend(
            path for path in base.rglob("*")
            if path.is_file() and not path.is_symlink()
            and path.suffix in INCLUDED_SUFFIXES
            and "__pycache__" not in path.parts
        )
    relative_paths = sorted({path.relative_to(root).as_posix(): path for path in paths}.items())
    digest = hashlib.sha256()
    for relative, path in relative_paths:
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return {
        "schema": "quillframe_framework_build_identity_v1",
        "version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "input_file_count": len(relative_paths),
        "build_fingerprint": "sha256:" + digest.hexdigest(),
        "authority": False,
    }
