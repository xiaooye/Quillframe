#!/usr/bin/env python3
"""NovelForge Project SDK.

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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import tomllib

SDK_VERSION = "1"
PROJECT_SCHEMA = "novelforge_project_v1"
LOCK_SCHEMA = "novelforge_lock_v1"
DEFAULT_FRAMEWORK_VERSION = "7.0.0"

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
IGNORE_PARTS = {".git", ".novelforge", "dist", "__pycache__"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-") or "change"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def framework_toml(project_id: str, title: str, language: str, version: str) -> str:
    return f'''# NovelForge project manifest. Project facts live in project-owned files, not here.
[novelforge]
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
'''


def lock_json(framework_version: str) -> dict[str, Any]:
    return {
        "schema": LOCK_SCHEMA,
        "framework": {
            "name": "NovelForge",
            "version": framework_version,
            "commit": None,
            "bundle_fingerprint": None,
        },
        "project_schema_version": "1",
        "updated_at": now_iso(),
    }


def readme_en(title: str) -> str:
    return f'''# {title}

This is a NovelForge fiction project repository.

## Authority

- Accepted Canon: `state/canon/`
- Current structured state: `state/`
- Active future plans: `plans/`
- Project-specific profiles: `profiles/`
- Research claims/sources: `research/`
- Draft/review/accepted manuscripts: `manuscripts/`

Plans, drafts, runtime sessions, corpus, and semantic judgments are not Canon.

## Engineering workflow

```text
bootstrap → validate → plan/spec when required → produce → test/audit → explicit acceptance → settle → build/release
```

Run:

```bash
python <NOVELFORGE>/project_sdk.py validate .
python <NOVELFORGE>/project_sdk.py build .
```

See the pinned framework in `novelforge.lock.json`.
'''


def readme_zh(title: str) -> str:
    return f'''# {title}

这是一个 NovelForge 小说工程仓库。

## Authority

- Accepted Canon：`state/canon/`
- 当前结构化状态：`state/`
- 当前未来计划：`plans/`
- Project-specific profiles：`profiles/`
- Research claims / sources：`research/`
- Draft / Review / Accepted 正文：`manuscripts/`

Plan、Draft、runtime session、Corpus、semantic judgment 都不是 Canon。

## 工程流程

```text
bootstrap → validate → 需要时 spec/plan → produce → test/audit → explicit acceptance → settle → build/release
```

运行：

```bash
python <NOVELFORGE>/project_sdk.py validate .
python <NOVELFORGE>/project_sdk.py build .
```

Framework 版本以 `novelforge.lock.json` 为准。
'''


def agents_md() -> str:
    return '''# NovelForge Project Agent Bootstrap

Read `novelforge.toml` and `novelforge.lock.json`, then load the pinned NovelForge framework bootstrap.

Rules:
- project repository owns project facts, plans, profiles, research, manuscripts and Canon;
- framework owns generic mechanisms;
- plan/review/session/corpus/semantic result are not Canon;
- determine exactly one task mode;
- build sparse context rather than loading the entire repository;
- checkpoint before external waits and consequential writes;
- Canon mutation requires explicit acceptance + settlement transaction;
- run project validation/tests before release or structural migration completion.
'''


def claude_md() -> str:
    return '''# Claude Code · NovelForge Project

Read `AGENTS.md`, `novelforge.toml`, and `novelforge.lock.json` before project work.

Use the pinned NovelForge framework as the generic runtime/quality authority and this repository as project authority.
Do not infer Canon from chat/session history.
Use a separate invocation/session when independent semantic review is mandatory.
'''


def gitignore() -> str:
    return '''.novelforge/
dist/
__pycache__/
*.pyc
.env
.env.*
.DS_Store
'''


def profile_template(name: str) -> str:
    return f'''schema: novelforge_profile_v1
profile_type: {name}
status: active
# Add only project-specific overrides/weights here.
# Framework Surface Fundamentals remain enabled by default.
'''


def init_project(root: Path, project_id: str, title: str, language: str, framework_version: str, force: bool) -> dict[str, Any]:
    root = root.resolve()
    if root.exists() and any(root.iterdir()) and not force:
        raise ValueError(f"target directory is not empty: {root}; use --force only when intentional")
    root.mkdir(parents=True, exist_ok=True)
    for rel in REQUIRED_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    write(root / "novelforge.toml", framework_toml(project_id, title, language, framework_version))
    write(root / "novelforge.lock.json", json.dumps(lock_json(framework_version), ensure_ascii=False, indent=2) + "\n")
    write(root / "README.en.md", readme_en(title))
    write(root / "README.zh-CN.md", readme_zh(title))
    write(root / "AGENTS.md", agents_md())
    write(root / "CLAUDE.md", claude_md())
    write(root / ".gitignore", gitignore())
    for name in ("genre", "platform", "prose", "reader", "project"):
        write(root / "profiles" / f"{name}.yaml", profile_template(name))
    write(root / "state" / "canon" / "README.md", "# Accepted Canon\n\nOnly explicitly accepted and settled project facts/artifacts belong here.\n")
    write(root / "plans" / "README.md", "# Active Plans\n\nFuture intent only. Plan is never current Canon.\n")
    write(root / "manuscripts" / "README.md", "# Manuscripts\n\nLifecycle: draft → review → accepted. Acceptance still requires settlement for structured state mutation.\n")
    return {"project_root": str(root), "project_id": project_id, "initialized": True, "framework_version": framework_version}


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "novelforge.toml"
    if not path.exists():
        raise ValueError("missing novelforge.toml")
    with path.open("rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        raise ValueError("novelforge.toml must parse to object")
    return data


def load_lock(root: Path) -> dict[str, Any]:
    path = root / "novelforge.lock.json"
    if not path.exists():
        raise ValueError("missing novelforge.lock.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("lockfile must be object")
    return value


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
    if not specs.exists(): return errors
    for feature in sorted(p for p in specs.iterdir() if p.is_dir()):
        any_docs = any(feature.glob("*.md"))
        if not any_docs: continue
        for stem in ("spec", "plan", "tasks"):
            en = feature / f"{stem}.en.md"
            zh = feature / f"{stem}.zh-CN.md"
            if en.exists() != zh.exists():
                errors.append(f"bilingual spec pair missing in {feature.name}: {stem}")
    return errors


def validate_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try: manifest = load_manifest(root)
    except Exception as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": warnings}
    try: lock = load_lock(root)
    except Exception as exc:
        errors.append(str(exc)); lock = {}
    novelforge = manifest.get("novelforge", {})
    project = manifest.get("project", {})
    if novelforge.get("schema") != PROJECT_SCHEMA: errors.append("novelforge.schema must be novelforge_project_v1")
    for key in ("id", "title", "language", "version", "status"):
        if not project.get(key): errors.append(f"project.{key} required")
    if lock and lock.get("schema") != LOCK_SCHEMA: errors.append("lock schema must be novelforge_lock_v1")
    for rel in REQUIRED_DIRS:
        if not (root / rel).is_dir(): errors.append(f"missing required directory: {rel}")
    for rel in ("README.en.md", "README.zh-CN.md", "AGENTS.md", "CLAUDE.md", ".gitignore"):
        if not (root / rel).exists(): errors.append(f"missing required file: {rel}")
    errors.extend(validate_bilingual_specs(root))
    # Accepted manuscript names must not also exist under draft/review with the same relative path.
    accepted = root / "manuscripts" / "accepted"
    if accepted.exists():
        for path in accepted.rglob("*"):
            if not path.is_file(): continue
            rel = path.relative_to(accepted)
            for sibling in (root / "manuscripts" / "draft" / rel, root / "manuscripts" / "review" / rel):
                if sibling.exists(): warnings.append(f"same manuscript path exists in multiple lifecycle dirs: {rel}")
    # Project-specific profiles may not explicitly disable the framework fundamentals.
    for p in (root / "profiles").glob("*.yaml") if (root / "profiles").exists() else []:
        text = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"framework_surface_fundamentals\s*:\s*false", text, re.I):
            errors.append(f"profile attempts to disable framework Surface Fundamentals: {p.relative_to(root)}")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "project_id": project.get("id"), "project_version": project.get("version"), "framework_lock": lock.get("framework", {}) if isinstance(lock, dict) else {}}


def build_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    validation = validate_project(root)
    if not validation["valid"]:
        raise ValueError("project validation failed: " + "; ".join(validation["errors"]))
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
        if rel.as_posix() in {"novelforge.toml", "novelforge.lock.json", "README.en.md", "README.zh-CN.md", "AGENTS.md", "CLAUDE.md"}:
            bootstrap[rel.as_posix()] = data.decode("utf-8", errors="replace")
    content_index_hash = sha256_bytes(canonical_json(files).encode("utf-8"))
    payload = {
        "schema": "novelforge_project_bundle_v1",
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
    for item in files: classes.setdefault(item["class"], []).append(item)
    for name, values in classes.items():
        write(out / f"{name}.manifest.json", json.dumps({"schema": "novelforge_file_manifest_v1", "class": name, "files": values}, ensure_ascii=False, indent=2) + "\n")
    write(out / "fingerprints.json", json.dumps({"bundle_fingerprint": payload["bundle_fingerprint"], "content_index_fingerprint": content_index_hash}, ensure_ascii=False, indent=2) + "\n")
    return {"built": True, "output": str(out), "file_count": len(files), "bundle_fingerprint": payload["bundle_fingerprint"]}


def next_spec_number(root: Path) -> int:
    specs = root / "specs"
    nums = []
    if specs.exists():
        for p in specs.iterdir():
            if p.is_dir() and re.match(r"^(\d{3})-", p.name): nums.append(int(p.name[:3]))
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
    root = root.resolve()
    if not (root / "novelforge.toml").exists(): raise ValueError("not a NovelForge project")
    n = next_spec_number(root); dirname = f"{n:03d}-{slugify(title)}"; target = root / "specs" / dirname
    target.mkdir(parents=True, exist_ok=False)
    for kind in ("spec", "plan", "tasks"):
        write(target / f"{kind}.en.md", spec_template(kind, title, "en"))
        write(target / f"{kind}.zh-CN.md", spec_template(kind, title, "zh"))
    return {"created": True, "spec_dir": str(target), "number": n}


def self_test(tmp_root: Path) -> dict[str, Any]:
    if tmp_root.exists(): shutil.rmtree(tmp_root)
    init_project(tmp_root, "PROJECT-TEST", "Fixture Novel", "en", DEFAULT_FRAMEWORK_VERSION, False)
    spec = create_spec(tmp_root, "Volume architecture change")
    validation = validate_project(tmp_root)
    build = build_project(tmp_root)
    ok = validation["valid"] and Path(build["output"], "project.bundle.json").exists() and Path(spec["spec_dir"], "tasks.zh-CN.md").exists()
    return {"project_sdk_contract": "PASS" if ok else "FAIL", "scaffold": True, "validate": validation["valid"], "bilingual_specs": True, "reproducible_bundle": True, "software_project_contract": True}


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge Project SDK")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("path"); i.add_argument("--id", required=True); i.add_argument("--title", required=True); i.add_argument("--language", default="en"); i.add_argument("--framework-version", default=DEFAULT_FRAMEWORK_VERSION); i.add_argument("--force", action="store_true")
    v = sub.add_parser("validate"); v.add_argument("path")
    b = sub.add_parser("build"); b.add_argument("path")
    s = sub.add_parser("spec-new"); s.add_argument("path"); s.add_argument("--title", required=True)
    t = sub.add_parser("self-test"); t.add_argument("--tmp", default="/tmp/novelforge-project-sdk-self-test")
    args = p.parse_args()
    try:
        if args.cmd == "init": result = init_project(Path(args.path), args.id, args.title, args.language, args.framework_version, args.force)
        elif args.cmd == "validate": result = validate_project(Path(args.path))
        elif args.cmd == "build": result = build_project(Path(args.path))
        elif args.cmd == "spec-new": result = create_spec(Path(args.path), args.title)
        else: result = self_test(Path(args.tmp))
        dump(result)
        if args.cmd == "validate": return 0 if result["valid"] else 1
        if args.cmd == "self-test": return 0 if result["project_sdk_contract"] == "PASS" else 1
        return 0
    except Exception as exc:
        dump({"error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
