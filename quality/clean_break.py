#!/usr/bin/env python3
"""History-aware Quillframe 1.0 clean-break audit.

Historical specifications and changelogs may describe superseded contracts.
Current product, runtime, persistence, and task documentation may only expose
the native novel contract: four manifest keys and top-level scope ``novel``.
CH001 remains valid as an initial chapter or a historical acceptance fixture.
The scanner is intentionally based on exact behavioral
markers rather than a broad word ban, so rejection tests and platform terms
such as Cloudflare's ``compatibility_date`` remain valid evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_clean_break_audit_v1"
HISTORICAL_ROOTS = ["CHANGELOG.en.md", "CHANGELOG.zh-CN.md", "specs"]

REMOVED_PATHS = (
    ".codex/hooks.json",
    ".claude/settings.json",
    "docs/project-adapters.en.md",
    "docs/project-adapters.zh-CN.md",
    "harness/PROJECT_ADAPTER_PROTOCOL.en.md",
    "harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md",
    "harness/integrations/claude_hook.py",
    "harness/integrations/codex_hook.py",
    "harness/integrations/host_bootstrap.py",
    "harness/integrations/host_scaffold.py",
    "harness/project_projection.py",
    "harness/semantic_workers/adapters/openai_responses_adapter.py",
    "persistence/migrations",
    "project_adapter.py",
    "site/src/appearance-v5.ts",
    "studio/app/pnpm-lock.yaml",
    "studio/app/src/productProjection.ts",
    "studio/app/src/routes/Control.tsx",
    "studio/app/src/routes/Inspector.tsx",
    "studio/app/src/routes/InspectorRoute.tsx",
    "studio/app/src/styles/visual-fixes.css",
    "tests/test_quillframe_mapped_projection.py",
    "tests/test_quillframe_bootstrap_host.py",
    "tests/test_quillframe_unified_host_bootstrap.py",
    "project_sdk.py",
    "docs/project-sdk.en.md",
    "docs/project-sdk.zh-CN.md",
    "docs/brand_migration.json",
    "studio/fixtures/project-adapter-resolution.synthetic.json",
)

FORBIDDEN_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "native five-key",
        "CH001 context",
        "fixes the acceptance scope to CH001",
        "required by its lock",
        "quillframe init",
        "quillframe validate",
        "project-local bootstrap",
        "npm install --no-audit --no-fund",
        "python studio/local_server.py",
    ),
    "README.en.md": (
        "native five-key",
        "CH001 context",
        "fixes the acceptance scope to CH001",
        "required by its lock",
        "quillframe init",
        "quillframe validate",
        "project-local bootstrap",
        "npm install --no-audit --no-fund",
        "python studio/local_server.py",
    ),
    "README.zh-CN.md": (
        "native 五键",
        "CH001 context",
        "验收范围固定为 CH001",
        "按照自己的 lock 固定 exact Framework",
        "quillframe init",
        "quillframe validate",
        "项目级 bootstrap",
        "npm install --no-audit --no-fund",
        "python studio/local_server.py",
    ),
    "ROADMAP.md": ("required by their project lock", "native five-key manifest", "CH001 context"),
    "CLAUDE.en.md": ("five-key native manifest", "CH001 context"),
    "CLAUDE.zh-CN.md": ("五键 native manifest", "CH001 context"),
    "core/CANON_STATE.en.md": ("five-key manifest/context",),
    "core/CANON_STATE.zh-CN.md": ("五键 manifest/context",),
    ".github/ISSUE_TEMPLATE/architecture_proposal.yml": ("        - Project SDK",),
    "quillframe/cli.py": (
        'sub.add_parser("init"',
        'sub.add_parser("pin"',
        'sub.add_parser("validate"',
        'sub.add_parser("build"',
        'sub.add_parser("host-install"',
        'sub.add_parser("host-run"',
        'sub.add_parser("claude-hook"',
        'sub.add_parser("codex-hook"',
        "project_sdk.py",
    ),
    "HARNESS_MANIFEST.yaml": (
        "supported_project_contract: quillframe_project_v1\n",
        "project_sdk: project_sdk.py",
        "lockfile: quillframe.lock.json",
        "caller_must_pin_exact_framework_commit: true",
        "project-sdk-self-test",
    ),
    "quillframe.py": (
        '"chapter_scope":resolution.get',
        '"chapter_scope":"CH001"',
        "PROJECT_SDK",
        "project_sdk.py",
        "--no-build",
        '["build", str(project_root)]',
    ),
    "harness/session_runtime/resume_preflight.py": (
        "quillframe.lock.json",
        "framework.attestation.json",
        "project_authority_fingerprint",
        "framework_identity_matches",
        "project_authority_matches",
    ),
    "harness/session_runtime/resume_command.py": (
        '    "project_chapter_scope_matches",\n',
        "project_authority_fingerprint",
        "framework_identity_matches",
        "project_authority_matches",
    ),
    "harness/session_runtime/runtime_command_authorization.py": (
        "project_authority_fingerprint",
        '"framework":',
    ),
    "harness/session_runtime/runtime_command_executor.py": (
        "quillframe.lock.json",
        "framework.attestation.json",
        "project_authority_fingerprint",
        "FRAMEWORK_KEYS",
    ),
    "harness/session_runtime/terminate_preflight.py": (
        "quillframe.lock.json",
        "framework.attestation.json",
    ),
    "harness/session_runtime/terminate_executor.py": (
        "quillframe.lock.json",
        "framework.attestation.json",
    ),
    ".github/actions/project-peer-semantic/bridge.py": (
        "quillframe.lock.json",
        "framework.attestation.json",
        "manifest.get(\"project\")",
    ),
    ".github/actions/project-peer-semantic/action.yml": (
        "v1 remains replay-readable",
    ),
    "studio/project_hub_projection.py": (
        "quillframe_project_resolution_v1",
        "framework_lock",
        "framework_attestation",
        "project_version",
        '"layout"',
    ),
    "harness/context_assembly.py": (
        "LEGACY_SCHEMA",
        "schema not in {None",
    ),
    "harness/context_runtime.py": (
        "Compatibility stage vocabulary",
        '"writer_pre_draft"',
        '"post_draft_critic"',
    ),
    "quality/production_readiness.py": (
        "receipt = independence_receipt if",
        "binding.get(\"bridge_receipt\")",
    ),
    "persistence/independent_review_repository.py": (
        "DEPRECATED_PROVIDER_ALIASES",
        ".get(provider, provider)",
    ),
    "persistence/quillframe_sqlite.py": (
        '"chapter_scope": PROJECT_SCOPE',
        '"chapter_scope": "CH001"',
        "_LEGACY_MIGRATION_CHECKSUMS",
        "apply_migrations",
        ' / "migrations"',
        "migrated_unverified",
    ),
    "production_runtime/runtime.py": (
        "_bind_completed_legacy_submission",
        "released-v9",
        "LEGACY_SCHEMA",
    ),
    "learning/feedback_intake.py": (
        "LEGACY_STEERING_SCHEMA",
        "legacy_author_steering",
    ),
    "learning/author_model.py": (
        'value.get("capture_decision", "capture")',
        '"acceptance": "acceptance"',
    ),
    "site/src/ProductApp.tsx": (
        "five-key Project manifest",
        "五键 Project manifest",
        '<Route path="/start"',
        "<Navigate",
        "legacyProjection",
        "quillframe.lock.json",
        "framework.attestation.json",
        "quillframe_project_resolution_v1",
        "manifest, lock, and attestation",
        "manifest、lock 与 attestation",
    ),
    "site/src/main.tsx": (
        '"/start"',
        "appearance-migrated",
        "appearance-v5",
    ),
    "studio/app/src/studio.tsx": (
        "legacyProjection",
        "projectRoot",
    ),
    "docs/integrations.en.md": (
        "quillframe host-install",
        "quillframe host-run",
        "project-local .codex/hooks.json",
    ),
    "docs/integrations.zh-CN.md": (
        "quillframe host-install",
        "quillframe host-run",
        "project-local .codex/hooks.json",
    ),
    "SKILL.md": (
        "five-key native manifest",
        "CH001 context",
        "Project SDK",
        "exact locked Framework",
    ),
    "docs/DOCUMENTATION_STANDARD.en.md": ("quillframe.lock.json",),
    "docs/DOCUMENTATION_STANDARD.zh-CN.md": ("quillframe.lock.json",),
    "agent-skills/quillframe/SKILL.md": (
        "quillframe_host_bridge_description_v1`",
        "quillframe_studio_host_bridge_request_v1",
        "quillframe_studio_host_bridge_result_v1",
        "session.resume",
        "session.terminate",
    ),
    "agent-skills/quillframe/scripts/quillframe_bridge.py": (
        "quillframe_studio_host_bridge_description_v1",
        "quillframe_studio_host_bridge_request_v1",
        "supported_operations",
        "session.resume",
        "session.terminate",
    ),
    "studio/portable_product_contract.json": (
        "quillframe_studio_portable_product_contract_v1\"",
        "quillframe_studio_host_bridge_request_v1",
        "quillframe_studio_host_bridge_result_v1",
        "session_resume_exposed",
    ),
    "studio/README.en.md": (
        "quillframe_studio_host_bridge_request_v1",
        "quillframe_studio_host_bridge_result_v1",
        "semantic.catalog",
        "python studio/local_server.py",
    ),
    "studio/README.zh-CN.md": (
        "quillframe_studio_host_bridge_request_v1",
        "quillframe_studio_host_bridge_result_v1",
        "semantic.catalog",
        "python studio/local_server.py",
    ),
    "studio/fixtures/host-bridge-request.synthetic.json": (
        "quillframe_studio_host_bridge_request_v1",
        "semantic.catalog",
    ),
    "site/scripts/agent-integration-quality.mjs": (
        "quillframe_studio_host_bridge_contract_v1",
        "host_bridge_v1: true",
        "session.resume",
        "session.terminate",
    ),
    "core_operations.py": (
        "quillframe_host_bridge_description_v1",
        "def bridge_description(",
    ),
    "site/src/ProjectInspector.tsx": (
        "five-key manifest",
        "五键 manifest",
        "quillframe.lock.json",
        "framework.attestation.json",
        "Mapped adapters may intentionally use a different physical layout",
    ),
    "site/scripts/project-inspector-quality.mjs": (
        "quillframe.lock.json",
        "framework.attestation.json",
        "python project_sdk.py init",
    ),
    "studio/app/src/routes/Agents.tsx": (
        "quillframe.lock.json",
        "framework.attestation.json",
    ),
    "studio/app/src/locales/en-US.ts": (
        "framework-lock",
        "attestation consistency",
    ),
    "studio/app/src/locales/zh-CN.ts": (
        "Framework lock",
        "attestation",
    ),
    "SKILL.en.md": (
        "exactly five native keys",
        "CH001 context",
        "manifest/context/fingerprint/CH001/data-boundary",
        "quillframe.lock.json",
        "Project SDK contracts",
        "exact locked Framework",
        "migration-safe",
    ),
    "SKILL.zh-CN.md": (
        "五个 native key",
        "CH001 context",
        "manifest/context/fingerprint/CH001/data-boundary",
        "quillframe.lock.json",
        "Project SDK contract",
        "exact locked Framework",
        "构建、迁移和 rollback",
    ),
    "release/FRAMEWORK_BUNDLE.en.md": (
        "native five-key",
        "exact five-key Project identity",
        "quillframe.lock.json",
        "exact lock resolution",
        "bundle attestation metadata",
    ),
    "release/FRAMEWORK_BUNDLE.zh-CN.md": (
        "native five-key",
        "native 五键",
        "consumer `quillframe.lock.json`",
        "Bundle attestation",
        "exact lock resolution",
    ),
    "docs/project-contract.en.md": (
        "native five-key",
        "CH001 context",
        "1.0 acceptance executes CH001 only.",
        "project_sdk.py",
        "quillframe_project_resolution_v1",
        "quillframe init",
        "quillframe pin",
        "quillframe host-install",
    ),
    "docs/project-contract.zh-CN.md": (
        "五键 `quillframe.toml`",
        "CH001 context",
        "1.0 验收只执行 CH001。",
        "project_sdk.py",
        "quillframe_project_resolution_v1",
        "quillframe init",
        "quillframe pin",
        "quillframe host-install",
    ),
    "site/docs-site/src/components/DocsLanding.astro": (
        "exact framework lock",
        "lock and attestation",
        "Project SDK",
        "精确框架锁定",
        "框架证明",
    ),
    "site/scripts/architecture-explorer-quality.mjs": (
        "quillframe_project_resolution_v1",
    ),
    "studio/app/src/authoring/contracts.ts": (
        "project_schema_version",
    ),
    "studio/PRODUCT_ARCHITECTURE.en.md": (
        "native five-key manifest",
        "quillframe_project_resolution_v1",
    ),
    "studio/PRODUCT_ARCHITECTURE.zh-CN.md": (
        "native 五键 manifest",
        "quillframe_project_resolution_v1",
    ),
    "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.en.md": (
        "project_adapter.py",
        "production_runtime/project_projection.py",
        "persistence/migrations/project/004_",
        "project_sdk_self_test",
        "lock/attestation update",
    ),
    "AGENTS.en.md": ("Project SDK principle",),
    "AGENTS.zh-CN.md": ("Project SDK 原则",),
    "evals/README.en.md": ("Project SDK/Framework hygiene",),
    "evals/README.zh-CN.md": ("Project SDK / Framework hygiene",),
    "docs/architecture.en.md": ("the Project SDK",),
    "assets/DESIGN_SYSTEM.en.md": ("Project SDK",),
    "assets/DESIGN_SYSTEM.zh-CN.md": ("Project SDK",),
    "harness/CONTINUOUS_MAINTENANCE.en.md": ("Project SDK / Adapter self-tests",),
    "harness/CONTINUOUS_MAINTENANCE.zh-CN.md": ("Project SDK / Adapter self-test",),
    "knowledge/AGENT_FRAMEWORK_ADOPTION.en.md": ("Quillframe Project SDK", "migrations and exact locks", "exact-lock dependency migrations"),
    "knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md": ("Quillframe Project SDK", "migration、exact lock", "exact-lock dependency migration"),
    "studio/prototypes/project-hub-scene.html": (
        "CH-012",
        "SCN-012",
        "RUN-SYNTHETIC-012",
        "Quillframe lock visible",
        "manuscripts · dir",
        "novel_bible",
    ),
    "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.zh-CN.md": (
        "project_adapter.py",
        "project_sdk_self_test",
        "lock/attestation update",
    ),
    "harness/ORCHESTRATION_PROTOCOL.en.md": ("exact lock/fingerprint", "Framework/Project compatibility"),
    "harness/ORCHESTRATION_PROTOCOL.zh-CN.md": ("exact lock/fingerprint", "Framework/Project compatibility"),
    "harness/HARNESS_AGENT.en.md": ("exact lock/fingerprint", "exact locked Git identity", "Framework/Project compatibility"),
    "harness/HARNESS_AGENT.zh-CN.md": ("exact lock/fingerprint", "exact locked Git identity", "Framework/Project compatibility"),
    "harness/session_runtime/SESSION_RUNTIME.en.md": ("exact lock/bundle", "Framework / Project compatibility"),
    "harness/session_runtime/SESSION_RUNTIME.zh-CN.md": ("exact lock / bundle", "Framework / Project compatibility"),
    "project_resolution.py": (
        'MANIFEST_KEYS = {"schema", "id", "title", "language", "chapter_scope"}',
        'CHAPTER_SCOPE = "CH001"',
        '"chapter_scope":',
    ),
    "quillframe/launch.py": ('CHAPTER_SCOPE = "CH001"', '"exact_five_key_manifest"'),
    "production_runtime/workflow.py": ("def require_ch001(",),
    "production_runtime/types.py": ("require_ch001",),
    "site/src/project-inspector-contract.ts": ('chapter_scope: "CH001"', '"chapter_scope"'),
    "cloud/src/core-provenance.ts": ('chapter_scope:', '"chapter_scope",', '.chapter_scope'),
    "cloud/src/core-container.ts": ("claims.chapter_scope",),
    "cloud/src/index.ts": ('chapter_scope:', 'verification.chapter_scope'),
    "cloud/src/project-store.ts": ('chapter_scope:', '"chapter_scope",', 'receipt.chapter_scope'),
    "quillframe/cloud_core.py": ('claims["chapter_scope"]', 'manifest.get("chapter_scope")', '"chapter_scope": "CH001"'),
}

REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": ("native four-key", 'scope: "novel"', "initial chapter", ".quillframe/data", "Framework commit/bundle provenance"),
    "README.en.md": ("native four-key", 'scope: "novel"', "initial chapter", ".quillframe/data", "Framework commit/bundle provenance"),
    "README.zh-CN.md": ("原生四键", 'scope: "novel"', "初始章节", ".quillframe/data", "Framework commit / bundle provenance"),
    "ROADMAP.md": ("native four-key manifest", 'scope: "novel"', ".quillframe/data", "no consumer-owned Project lock"),
    ".github/ISSUE_TEMPLATE/architecture_proposal.yml": ("Native Project contract",),
    "SKILL.md": ("native Project manifest/context", "four-key native manifest", 'scope: "novel"', "initial chapter", ".quillframe/data"),
    "SKILL.en.md": ("native Project manifest/context", "exactly four native keys", 'scope: "novel"', "initial chapter", ".quillframe/data", "native-contract-validatable"),
    "SKILL.zh-CN.md": ("native Project manifest/context", "四个原生键", 'scope: "novel"', "初始章节", ".quillframe/data", "按 native contract 验证"),
    "docs/project-contract.en.md": ("native four-key", 'schema = "quillframe_project_v1_0"', 'scope: "novel"', "only the initial chapter", "project:1.0", "manifest_fingerprint"),
    "docs/project-contract.zh-CN.md": ("原生四键", 'schema = "quillframe_project_v1_0"', 'scope: "novel"', "只是初始章节", "project:1.0", "manifest_fingerprint"),
    "CLAUDE.en.md": ("four-key native manifest", 'scope: "novel"'),
    "CLAUDE.zh-CN.md": ("四键原生 manifest", 'scope: "novel"'),
    "knowledge/AGENT_FRAMEWORK_ADOPTION.en.md": ("Framework/Host provenance", "not Project authority or a consumer lock"),
    "knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md": ("Framework / Host provenance", "不是 Project authority 或 consumer lock"),
    "studio/prototypes/project-hub-scene.html": ("CH001", "quillframe_project_v1_0", "manifest_fingerprint", ".quillframe/data", "authority=false"),
    "site/src/ProductApp.tsx": ("four-key Project manifest, context v1_0, and .quillframe/data", "四键 Project manifest、context v1_0 与 .quillframe/data", "scope=novel"),
    "harness/ORCHESTRATION_PROTOCOL.en.md": ("Framework provenance, native Project identity and contract",),
    "harness/ORCHESTRATION_PROTOCOL.zh-CN.md": ("Framework provenance、native Project identity 与 contract",),
    "harness/HARNESS_AGENT.en.md": ("Framework provenance, native Project identity and contract",),
    "harness/HARNESS_AGENT.zh-CN.md": ("Framework provenance、native Project identity 与 contract",),
    "harness/session_runtime/SESSION_RUNTIME.en.md": ("Framework provenance and native Project identity/contract",),
    "harness/session_runtime/SESSION_RUNTIME.zh-CN.md": ("Framework provenance 与 native Project identity / contract",),
    "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.en.md": ("Superseded pre-1.0 endurance plan", "native 1.0"),
    "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.zh-CN.md": ("已被取代", "native 1.0"),
    "quillframe/launch.py": (
        'PROJECT_SCHEMA = "quillframe_project_v1_0"',
        'PROJECT_SCOPE = "novel"',
        "store.create_native_project(",
        "legacy metadata",
    ),
    "studio/host_bridge_protocol.py": (
        'BRIDGE_VERSION = "11"',
        'REQUEST_SCHEMA = "quillframe_host_bridge_request_v11"',
        'RESULT_SCHEMA = "quillframe_host_bridge_result_v11"',
        "def fingerprint(",
    ),
    "studio/host_bridge.py": (
        '"schema": "quillframe_host_bridge_description_v11"',
        '"operation_contracts": operation_contracts',
        "agent_package only permits query operations",
    ),
    "agent-skills/quillframe/scripts/quillframe_bridge.py": (
        'EXPECTED_DESCRIPTION = "quillframe_host_bridge_description_v11"',
        'REQUEST_SCHEMA = "quillframe_host_bridge_request_v11"',
        "def preflight(",
        "metadata.get(\"kind\") != \"query\"",
    ),
    "studio/portable_product_contract.json": (
        '"schema": "quillframe_studio_portable_product_contract_v11"',
        '"request_schema": "quillframe_host_bridge_request_v11"',
        '"result_schema": "quillframe_host_bridge_result_v11"',
        '"agent_package_query_only": true',
    ),
    "harness/control_plane/mcp_stdio.py": (
        'PROTOCOL_VERSION = "2026-07-28"',
    ),
    "persistence/quillframe_sqlite.py": (
        'SCHEMA_RELEASE = "1.0"',
        "def create_native_project(",
        '"scope": PROJECT_SCOPE',
        "Pre10StateRejectedError",
        ' / "schema"',
    ),
    "project_resolution.py": (
        'PROJECT_SCHEMA = "quillframe_project_v1_0"',
        'PROJECT_SCOPE = "novel"',
        'MANIFEST_KEYS = {"schema", "id", "title", "language"}',
        '"scope": PROJECT_SCOPE',
        'DATA_RELATIVE = Path(".quillframe") / "data"',
        "_reject_legacy_metadata",
    ),
    "production_runtime/workflow.py": ("def validate_chapter_id(",),
    "production_runtime/types.py": ("return validate_chapter_id(value)",),
    "harness/session_runtime/resume_command.py": ('    "project_scope_matches",\n',),
    "site/src/project-inspector-contract.ts": ('scope: "novel"', "four-key"),
    "cloud/src/core-provenance.ts": ('scope: "novel"', 'value.scope !== "novel"'),
    "cloud/src/core-container.ts": ('claims.scope !== "novel"',),
    "cloud/src/index.ts": ('scope: "novel"', 'verification.scope !== "novel"'),
    "cloud/src/project-store.ts": ('scope: "novel"', 'receipt.scope !== "novel"'),
    "quillframe/cloud_core.py": ('claims["scope"] != "novel"', 'manifest.get("scope") != "novel"', '"scope": "novel"'),
    "schemas/1.0/catalog.json": (
        '"compatibility": false',
    ),
}


def _text(root: Path, relative: str) -> str | None:
    path = root / relative
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _locks(root: Path) -> list[str]:
    ignored = {".git", "node_modules", "dist", ".quillframe", "__pycache__"}
    found: list[str] = []
    for path in root.rglob("pnpm-lock.yaml"):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        found.append(relative.as_posix())
    return sorted(found)


def audit_clean_break(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    violations: list[dict[str, str]] = []

    for relative in REMOVED_PATHS:
        if (root / relative).exists():
            violations.append({"code": "removed_path_present", "path": relative, "marker": relative})

    for relative, markers in FORBIDDEN_MARKERS.items():
        content = _text(root, relative)
        if content is None:
            violations.append({"code": "current_surface_missing", "path": relative, "marker": "required scan target"})
            continue
        for marker in markers:
            if marker in content:
                violations.append({"code": "pre_1_0_surface_present", "path": relative, "marker": marker})

    for relative, markers in REQUIRED_MARKERS.items():
        content = _text(root, relative)
        if content is None:
            violations.append({"code": "current_surface_missing", "path": relative, "marker": "required contract"})
            continue
        for marker in markers:
            if marker not in content:
                violations.append({"code": "native_1_0_marker_missing", "path": relative, "marker": marker})

    locks = _locks(root)
    if locks != ["pnpm-lock.yaml"]:
        violations.append({"code": "workspace_lockfile_drift", "path": ".", "marker": json.dumps(locks)})

    violations.sort(key=lambda item: (item["path"], item["code"], item["marker"]))
    return {
        "schema": SCHEMA,
        "status": "pass" if not violations else "fail",
        "historical_roots": list(HISTORICAL_ROOTS),
        "compatibility_layer_permitted": False,
        "pre_1_0_state_migration_permitted": False,
        "route_redirect_permitted": False,
        "protocol_negotiation_permitted": False,
        "cli_alias_permitted": False,
        "workspace_lockfiles": locks,
        "removed_path_count": len(REMOVED_PATHS),
        "scanned_current_surface_count": len(FORBIDDEN_MARKERS) + len(REQUIRED_MARKERS),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Quillframe 1.0 clean break")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = audit_clean_break(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
