#!/usr/bin/env python3
"""NovelForge repository hygiene / release-boundary checks."""
from __future__ import annotations

import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Construct known consumer identifiers at runtime so the checker itself does
# not commit those complete identifiers into the generic framework tree.
FORBIDDEN_CONSUMER_TOKENS = {
    "xiaooye/" + "frost" + "loom",
    "china" + "boy_webnovel",
    "《从唐" + "人街到白宫》",
    "周" + "叙",
    "陈" + "承",
}
TEXT_EXTS = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}
STABLE_ROUTERS = {
    pathlib.Path("README.md"), pathlib.Path("SKILL.md"), pathlib.Path("AGENTS.md"), pathlib.Path("CLAUDE.md"),
    pathlib.Path("harness/HARNESS_AGENT.md"), pathlib.Path("harness/ORCHESTRATION_PROTOCOL.md"),
    pathlib.Path("harness/SELF_IMPROVEMENT_PROTOCOL.md"), pathlib.Path("harness/CONTINUOUS_MAINTENANCE.md"),
    pathlib.Path("harness/control_plane/CONTROL_PLANE.md"),
    pathlib.Path("harness/session_runtime/SESSION_RUNTIME.md"), pathlib.Path("harness/session_runtime/RUNTIME_ROUTING.md"),
    pathlib.Path("harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.md"),
    pathlib.Path("harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md"),
}


def relative(path: pathlib.Path) -> pathlib.Path:
    return path.relative_to(ROOT)


def leakage_errors() -> list[str]:
    errors: list[str] = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT_EXTS or ".git" in p.parts:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN_CONSUMER_TOKENS:
            if token in text:
                errors.append(f"consumer-project leakage: {relative(p)} contains a forbidden consumer identifier")
    return errors


def bilingual_errors() -> list[str]:
    errors: list[str] = []
    for p in ROOT.rglob("*.md"):
        if ".git" in p.parts:
            continue
        rel = relative(p)
        name = p.name
        if name.endswith(".en.md"):
            peer = p.with_name(name[:-6] + ".zh-CN.md")
            if not peer.exists(): errors.append(f"missing zh-CN pair: {rel}")
        elif name.endswith(".zh-CN.md"):
            peer = p.with_name(name[:-9] + ".en.md")
            if not peer.exists(): errors.append(f"missing en pair: {rel}")
        elif rel not in STABLE_ROUTERS:
            errors.append(f"unpaired human Markdown: {rel}")
    for router in STABLE_ROUTERS:
        path = ROOT / router
        if not path.exists():
            errors.append(f"missing stable router: {router}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not ("English" in text and ("中文" in text or "简体中文" in text)):
            errors.append(f"stable router is not bilingual: {router}")
    return errors


def link_errors() -> list[str]:
    errors: list[str] = []
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for p in ROOT.rglob("*.md"):
        if ".git" in p.parts:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for raw in pattern.findall(text):
            target = raw.strip().split()[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = urllib.parse.unquote(target.split("#", 1)[0])
            if not target: continue
            resolved = (p.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"link escapes repository: {relative(p)} -> {raw}")
                continue
            if not resolved.exists():
                errors.append(f"missing relative link: {relative(p)} -> {raw}")
    return errors


def release_version_errors(manifest: str) -> list[str]:
    errors: list[str] = []
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    manifest_match = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", manifest)
    skill_match = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", skill)
    if not manifest_match:
        errors.append("HARNESS_MANIFEST.yaml missing semantic version")
    if not skill_match:
        errors.append("SKILL.md frontmatter missing semantic version")
    if manifest_match and skill_match and manifest_match.group(1) != skill_match.group(1):
        errors.append(
            f"release version drift: manifest={manifest_match.group(1)} skill={skill_match.group(1)}"
        )
    return errors


def contract_errors() -> list[str]:
    errors: list[str] = []
    manifest = (ROOT / "HARNESS_MANIFEST.yaml").read_text(encoding="utf-8")
    errors.extend(release_version_errors(manifest))
    required = [
        "name: novelforge", "project_agnostic: true",
        "built_in_novel_or_canon: false", "dependency_direction: project-to-framework-only",
        "human_facing_pair_required: true", "project_sdk: project_sdk.py",
        "durable_store: learning/learning_store.py", "scout: corpus/corpus_scout.py",
    ]
    for needle in required:
        if needle not in manifest: errors.append(f"manifest missing {needle!r}")
    surface = (ROOT / "surface/FUNDAMENTALS.en.md").read_text(encoding="utf-8")
    reader = (ROOT / "surface/READER_ENGAGEMENT.en.md").read_text(encoding="utf-8")
    if not ("HF-01" in surface and "HF-29" in surface): errors.append("Surface HF range incomplete")
    if not ("RG-01" in reader and "RG-15" in reader and "SAFE-BUT-FLAT" in reader): errors.append("Reader RG range incomplete")
    for p in (ROOT / "docs/project-sdk.en.md", ROOT / "docs/project-sdk.zh-CN.md"):
        text = p.read_text(encoding="utf-8")
        if "novelforge.toml" not in text: errors.append(f"{relative(p)} missing novelforge.toml")
        if "project.yaml" in text: errors.append(f"{relative(p)} contains stale project.yaml")
    return errors


def main() -> int:
    groups = {
        "project_leakage": leakage_errors(),
        "bilingual_docs": bilingual_errors(),
        "relative_links": link_errors(),
        "release_contract": contract_errors(),
    }
    failed = False
    for name, errors in groups.items():
        if errors:
            failed = True
            print(f"[{name}] FAIL", file=sys.stderr)
            for error in errors: print(f"- {error}", file=sys.stderr)
        else:
            print(f"[{name}] PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
