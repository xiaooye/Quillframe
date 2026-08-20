from __future__ import annotations

import ast
import shutil
import tempfile
import unittest
from pathlib import Path

from quality.clean_break import audit_clean_break


ROOT = Path(__file__).resolve().parents[1]


class CleanBreakAuditTests(unittest.TestCase):
    def _forbidden_marker_entries(self):
        tree = ast.parse(
            (ROOT / "quality" / "clean_break.py").read_text(encoding="utf-8"),
            filename="quality/clean_break.py",
        )
        assignment = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "FORBIDDEN_MARKERS"
        )
        self.assertIsInstance(assignment.value, ast.Dict)
        entries = []
        for key, value in zip(assignment.value.keys, assignment.value.values):
            self.assertIsInstance(key, ast.Constant)
            self.assertIsInstance(key.value, str)
            self.assertIsInstance(value, ast.Tuple)
            markers = []
            for marker in value.elts:
                self.assertIsInstance(marker, ast.Constant)
                self.assertIsInstance(marker.value, str)
                markers.append(marker.value)
            entries.append((key.value, tuple(markers)))
        return entries

    def test_forbidden_marker_literal_keys_are_unique(self):
        entries = self._forbidden_marker_entries()
        keys = [key for key, _ in entries]
        self.assertEqual(len(keys), len(set(keys)), "FORBIDDEN_MARKERS has duplicate literal keys")

    def test_merged_forbidden_marker_tuples_retain_all_duplicate_key_markers(self):
        entries = dict(self._forbidden_marker_entries())
        expected_markers = {
            "quillframe/cli.py": {
                'sub.add_parser("init"',
                'sub.add_parser("pin"',
                'sub.add_parser("validate"',
                'sub.add_parser("build"',
                'sub.add_parser("host-install"',
                'sub.add_parser("host-run"',
                'sub.add_parser("claude-hook"',
                'sub.add_parser("codex-hook"',
                "project_sdk.py",
            },
            "site/src/ProductApp.tsx": {
                '<Route path="/start"',
                "<Navigate",
                "legacyProjection",
                "quillframe.lock.json",
                "framework.attestation.json",
                "quillframe_project_resolution_v1",
                "manifest, lock, and attestation",
                "manifest、lock 与 attestation",
            },
            "README.md": {
                "required by its lock",
                "quillframe init",
                "quillframe validate",
                "project-local bootstrap",
                "npm install --no-audit --no-fund",
                "python studio/local_server.py",
            },
            "README.en.md": {
                "required by its lock",
                "quillframe init",
                "quillframe validate",
                "project-local bootstrap",
                "npm install --no-audit --no-fund",
                "python studio/local_server.py",
            },
            "README.zh-CN.md": {
                "按照自己的 lock 固定 exact Framework",
                "quillframe init",
                "quillframe validate",
                "项目级 bootstrap",
                "npm install --no-audit --no-fund",
                "python studio/local_server.py",
            },
            "ROADMAP.md": {"required by their project lock"},
            ".github/ISSUE_TEMPLATE/architecture_proposal.yml": {"        - Project SDK"},
            ".github/actions/project-peer-semantic/action.yml": {"v1 remains replay-readable"},
            "SKILL.md": {"Project SDK", "exact locked Framework"},
            "SKILL.en.md": {"Project SDK contracts", "exact locked Framework", "migration-safe"},
            "SKILL.zh-CN.md": {"Project SDK contract", "exact locked Framework", "构建、迁移和 rollback"},
            "release/FRAMEWORK_BUNDLE.en.md": {"exact lock resolution", "bundle attestation metadata"},
            "release/FRAMEWORK_BUNDLE.zh-CN.md": {"Bundle attestation", "exact lock resolution"},
            "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.en.md": {"project_adapter.py", "production_runtime/project_projection.py", "persistence/migrations/project/004_", "project_sdk_self_test", "lock/attestation update"},
            "docs/project-contract.en.md": {"project_sdk.py", "quillframe_project_resolution_v1", "quillframe init", "quillframe pin", "quillframe host-install"},
            "docs/project-contract.zh-CN.md": {"project_sdk.py", "quillframe_project_resolution_v1", "quillframe init", "quillframe pin", "quillframe host-install"},
            "AGENTS.en.md": {"Project SDK principle"},
            "AGENTS.zh-CN.md": {"Project SDK 原则"},
            "evals/README.en.md": {"Project SDK/Framework hygiene"},
            "evals/README.zh-CN.md": {"Project SDK / Framework hygiene"},
            "docs/architecture.en.md": {"the Project SDK"},
            "assets/DESIGN_SYSTEM.en.md": {"Project SDK"},
            "assets/DESIGN_SYSTEM.zh-CN.md": {"Project SDK"},
            "harness/CONTINUOUS_MAINTENANCE.en.md": {"Project SDK / Adapter self-tests"},
            "harness/CONTINUOUS_MAINTENANCE.zh-CN.md": {"Project SDK / Adapter self-test"},
            "site/docs-site/src/components/DocsLanding.astro": {"Project SDK", "精确框架锁定", "框架证明"},
            "knowledge/AGENT_FRAMEWORK_ADOPTION.en.md": {"Quillframe Project SDK", "migrations and exact locks", "exact-lock dependency migrations"},
            "knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md": {"Quillframe Project SDK", "migration、exact lock", "exact-lock dependency migration"},
            "studio/prototypes/project-hub-scene.html": {"CH-012", "SCN-012", "RUN-SYNTHETIC-012", "Quillframe lock visible", "manuscripts · dir", "novel_bible"},
            "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.zh-CN.md": {"project_adapter.py", "project_sdk_self_test", "lock/attestation update"},
            "harness/ORCHESTRATION_PROTOCOL.en.md": {"exact lock/fingerprint", "Framework/Project compatibility"},
            "harness/ORCHESTRATION_PROTOCOL.zh-CN.md": {"exact lock/fingerprint", "Framework/Project compatibility"},
            "harness/HARNESS_AGENT.en.md": {"exact lock/fingerprint", "exact locked Git identity", "Framework/Project compatibility"},
            "harness/HARNESS_AGENT.zh-CN.md": {"exact lock/fingerprint", "exact locked Git identity", "Framework/Project compatibility"},
            "harness/session_runtime/SESSION_RUNTIME.en.md": {"exact lock/bundle", "Framework / Project compatibility"},
            "harness/session_runtime/SESSION_RUNTIME.zh-CN.md": {"exact lock / bundle", "Framework / Project compatibility"},
            "studio/README.en.md": {"python studio/local_server.py"},
            "studio/README.zh-CN.md": {"python studio/local_server.py"},
            "docs/DOCUMENTATION_STANDARD.en.md": {"quillframe.lock.json"},
            "docs/DOCUMENTATION_STANDARD.zh-CN.md": {"quillframe.lock.json"},
        }
        for path, required in expected_markers.items():
            self.assertIn(path, entries)
            self.assertTrue(required <= set(entries[path]), (path, entries[path]))

    def test_current_machine_surface_has_no_pre_1_0_compatibility_surface(self):
        report = audit_clean_break(ROOT)
        self.assertEqual(report["schema"], "quillframe_clean_break_audit_v1")
        self.assertEqual(report["historical_roots"], ["CHANGELOG.en.md", "CHANGELOG.zh-CN.md", "specs"])
        self.assertEqual(report["violations"], [], report)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["compatibility_layer_permitted"] is False)
        self.assertTrue(report["pre_1_0_state_migration_permitted"] is False)

    def test_readme_quick_start_uses_only_the_native_launch_flow(self):
        for relative in ("README.md", "README.en.md", "README.zh-CN.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("quillframe launch ../my-novel", text, relative)
            self.assertIn("--new", text, relative)
            self.assertIn("corepack pnpm install --frozen-lockfile", text, relative)
            self.assertIn("corepack pnpm run quality", text, relative)
            for removed in (
                "quillframe init",
                "quillframe validate",
                "project-local bootstrap",
                "项目级 bootstrap",
                "npm install --no-audit --no-fund",
                "python studio/local_server.py",
            ):
                self.assertNotIn(removed, text, (relative, removed))

    def test_studio_docs_expose_launch_not_the_internal_server_entrypoint(self):
        for relative in ("studio/README.en.md", "studio/README.zh-CN.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("quillframe launch PROJECT", text, relative)
            self.assertNotIn("python studio/local_server.py", text, relative)

    def test_current_docs_mutation_is_detected_without_global_allowlist(self):
        with tempfile.TemporaryDirectory(prefix="qf-clean-break-mutation-") as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "__pycache__"))
            target = copy / "SKILL.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nProject SDK\n", encoding="utf-8")
            report = audit_clean_break(copy)
        self.assertIn({"code": "pre_1_0_surface_present", "path": "SKILL.md", "marker": "Project SDK"}, report["violations"])

    def test_residual_current_surface_mutations_are_detected(self):
        cases = (
            ("README.en.md", "required by its lock"),
            ("README.en.md", "quillframe init"),
            ("README.en.md", "npm install --no-audit --no-fund"),
            ("README.zh-CN.md", "按照自己的 lock 固定 exact Framework"),
            ("README.zh-CN.md", "quillframe validate"),
            ("README.zh-CN.md", "python studio/local_server.py"),
            ("ROADMAP.md", "required by their project lock"),
            ("site/src/ProductApp.tsx", "manifest, lock, and attestation"),
            ("SKILL.en.md", "migration-safe"),
            ("knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md", "exact-lock dependency migration"),
            (".github/ISSUE_TEMPLATE/architecture_proposal.yml", "        - Project SDK"),
            (".github/actions/project-peer-semantic/action.yml", "v1 remains replay-readable"),
            ("studio/prototypes/project-hub-scene.html", "CH-012"),
            ("studio/prototypes/project-hub-scene.html", "RUN-SYNTHETIC-012"),
            ("harness/HARNESS_AGENT.en.md", "Framework/Project compatibility"),
        )
        with tempfile.TemporaryDirectory(prefix="qf-clean-break-residual-") as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "__pycache__"))
            for relative, marker in cases:
                target = copy / relative
                original = target.read_text(encoding="utf-8")
                target.write_text(original + f"\n{marker}\n", encoding="utf-8")
                report = audit_clean_break(copy)
                self.assertIn(
                    {"code": "pre_1_0_surface_present", "path": relative, "marker": marker},
                    report["violations"],
                    relative,
                )
                target.write_text(original, encoding="utf-8")

    def test_superseded_plan_mutation_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="qf-clean-break-plan-") as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "__pycache__"))
            target = copy / "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.en.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nproject_adapter.py\n", encoding="utf-8")
            report = audit_clean_break(copy)
        self.assertIn({"code": "pre_1_0_surface_present", "path": "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.en.md", "marker": "project_adapter.py"}, report["violations"])

    def test_superseded_plan_chinese_mutation_is_detected_and_bilingual_copy_is_native(self):
        with tempfile.TemporaryDirectory(prefix="qf-clean-break-plan-zh-") as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "__pycache__"))
            target = copy / "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.zh-CN.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nproject_adapter.py\n", encoding="utf-8")
            report = audit_clean_break(copy)
        self.assertIn({"code": "pre_1_0_surface_present", "path": "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.zh-CN.md", "marker": "project_adapter.py"}, report["violations"])
        for relative, required in {
            "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.en.md": ("Superseded pre-1.0", "native 1.0", "CH001", ".quillframe/data"),
            "docs/superpowers/plans/2026-08-19-quillframe-v091-endurance-run.zh-CN.md": ("已被取代", "native 1.0", "CH001", ".quillframe/data"),
        }.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            for marker in required:
                self.assertIn(marker, text, relative)

    def test_removed_product_files_do_not_return(self):
        forbidden = (
            "harness/integrations/claude_hook.py",
            "harness/integrations/codex_hook.py",
            "harness/integrations/host_bootstrap.py",
            "harness/integrations/host_scaffold.py",
            "harness/project_projection.py",
            "harness/semantic_workers/adapters/openai_responses_adapter.py",
            "persistence/migrations",
            "project_adapter.py",
            "site/src/appearance-v5.ts",
            "studio/app/src/productProjection.ts",
            "studio/app/src/styles/visual-fixes.css",
        )
        self.assertEqual([path for path in forbidden if (ROOT / path).exists()], [])


if __name__ == "__main__":
    unittest.main()
