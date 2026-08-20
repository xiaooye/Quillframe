#!/usr/bin/env python3
"""Quillframe repository hygiene / release-boundary checks."""
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
IGNORED_TREE_PARTS = {
    ".astro",
    ".git",
    ".venv",
    "coverage",
    "dist",
    "node_modules",
    "target",
}
IGNORED_TREE_PREFIXES = {
    ".superpowers/sdd/",
    "release/acceptance/",
    "site/docs-site/public/repo-assets/",
    "site/docs-site/src/content/docs/",
}
# GitHub/community metadata, machine-served Markdown assets, and archived
# implementation records intentionally keep their conventional singleton names.
# Product, contract, and maintained guidance documents remain pair-required.
INTENTIONALLY_SINGLETON_MARKDOWN = {
    pathlib.Path(".github/pull_request_template.md"),
    pathlib.Path("CODE_OF_CONDUCT.md"),
    pathlib.Path("CONTRIBUTING.md"),
    pathlib.Path("ROADMAP.md"),
    pathlib.Path("SECURITY.md"),
    pathlib.Path("site/public/auth.md"),
    pathlib.Path("site/public/sitemap.md"),
    pathlib.Path("specs/021-production-visibility-enforcement/verification.md"),
    pathlib.Path("studio/app/CORE_CONSUMER_HANDOFF.md"),
    pathlib.Path("agent-skills/quillframe/SKILL.md"),
}
INTENTIONALLY_SINGLETON_PREFIXES = {
    "docs/superpowers/plans/",
    "docs/superpowers/reports/",
}
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


def ignored(path: pathlib.Path) -> bool:
    rel = relative(path)
    rel_text = rel.as_posix()
    return (
        any(part in IGNORED_TREE_PARTS for part in rel.parts)
        or any(rel_text.startswith(prefix) for prefix in IGNORED_TREE_PREFIXES)
    )


def singleton_markdown(rel: pathlib.Path) -> bool:
    rel_text = rel.as_posix()
    return rel in INTENTIONALLY_SINGLETON_MARKDOWN or any(
        rel_text.startswith(prefix) for prefix in INTENTIONALLY_SINGLETON_PREFIXES
    )


def gitignore_errors() -> list[str]:
    path = ROOT / ".gitignore"
    if not path.is_file():
        return ["missing .gitignore"]
    entries = [
        line.strip().lstrip("/")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    rules = {entry for entry in entries if not entry.startswith("!")}
    errors: list[str] = []
    if ".superpowers/sdd/" not in rules:
        errors.append(".gitignore must contain exact operational boundary .superpowers/sdd/")
    for entry in sorted(set(entries)):
        candidate = entry.removeprefix("!").lstrip("/").replace("\\", "")
        related = any(token in candidate.lower() for token in ("superpowers", "sdd", "tasks.en"))
        if related and entry != ".superpowers/sdd/":
            errors.append(f".gitignore contains conflicting operational rule: {entry}")
    return errors


def leakage_errors() -> list[str]:
    errors: list[str] = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT_EXTS or ignored(p):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN_CONSUMER_TOKENS:
            if token in text:
                errors.append(f"consumer-project leakage: {relative(p)} contains a forbidden consumer identifier")
    return errors


def bilingual_errors() -> list[str]:
    errors: list[str] = []
    for p in ROOT.rglob("*.md"):
        if ignored(p):
            continue
        rel = relative(p)
        name = p.name
        if name.endswith(".en.md"):
            peer = p.with_name(name[:-6] + ".zh-CN.md")
            if not peer.exists(): errors.append(f"missing zh-CN pair: {rel}")
        elif name.endswith(".zh-CN.md"):
            peer = p.with_name(name[:-9] + ".en.md")
            if not peer.exists(): errors.append(f"missing en pair: {rel}")
        elif rel not in STABLE_ROUTERS and not singleton_markdown(rel):
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
        if ignored(p):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for raw in pattern.findall(text):
            target = raw.strip().split()[0].strip("<>")
            if not target or target.startswith(("#", "/", "http://", "https://", "mailto:")):
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
    semver = r"([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)"
    manifest_match = re.search(rf"(?m)^version:\s*{semver}\s*$", manifest)
    skill_match = re.search(rf"(?m)^version:\s*{semver}\s*$", skill)
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
        "name: quillframe", "project_agnostic: true",
        "built_in_novel_or_canon: false", "dependency_direction: project-to-framework-only",
        "human_facing_pair_required: true", "supported_project_contract: quillframe_project_v1_0",
        "durable_store: learning/learning_store.py", "scout: corpus/corpus_scout.py",
    ]
    for needle in required:
        if needle not in manifest: errors.append(f"manifest missing {needle!r}")
    surface = (ROOT / "surface/FUNDAMENTALS.en.md").read_text(encoding="utf-8")
    reader = (ROOT / "surface/READER_ENGAGEMENT.en.md").read_text(encoding="utf-8")
    if not ("HF-01" in surface and "HF-29" in surface): errors.append("Surface HF range incomplete")
    if not ("RG-01" in reader and "RG-15" in reader and "SAFE-BUT-FLAT" in reader): errors.append("Reader RG range incomplete")
    for p in (ROOT / "docs/project-contract.en.md", ROOT / "docs/project-contract.zh-CN.md"):
        text = p.read_text(encoding="utf-8")
        if "quillframe.toml" not in text: errors.append(f"{relative(p)} missing quillframe.toml")
        if "project.yaml" in text: errors.append(f"{relative(p)} contains stale project.yaml")
    return errors


def main() -> int:
    groups = {
        "gitignore_boundary": gitignore_errors(),
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
