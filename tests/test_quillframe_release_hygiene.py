from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from release import build_framework_bundle
from scripts import docs_quality, framework_hygiene, peer_bridge_contract

ROOT = Path(__file__).resolve().parents[1]


class ReleaseHygieneTests(unittest.TestCase):
    def test_documentation_catalog_does_not_consume_derived_acceptance_reports(self):
        manifest = json.loads((ROOT / "docs" / "documentation_manifest.json").read_text(encoding="utf-8"))
        serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        discovered = docs_quality.discover_bilingual_docs()

        self.assertNotIn("release/acceptance/", serialized)
        self.assertNotIn("release-acceptance-1-0-dev-0", serialized)
        self.assertIn("docs/project-contract.en.md", discovered)
        self.assertFalse(any(path.startswith("release/acceptance/") for path in discovered))
        self.assertIn("release/acceptance/", framework_hygiene.IGNORED_TREE_PREFIXES)
        self.assertNotIn("release/", framework_hygiene.IGNORED_TREE_PREFIXES)

        windows_root = PureWindowsPath("C:/Quillframe")
        with patch.object(docs_quality, "ROOT", windows_root):
            for relative in ("docs/project-contract.en.md", "release/acceptance/1.0.0-dev.0.en.md"):
                with self.subTest(relative=relative):
                    self.assertEqual(relative, docs_quality.rel(windows_root / relative))

    def test_framework_bundle_excludes_derived_release_acceptance_outputs(self):
        with tempfile.TemporaryDirectory(prefix="qf-bundle-acceptance-boundary-") as tmp:
            root = Path(tmp)
            runtime = root / "release" / "runtime.py"
            derived = root / "release" / "acceptance" / "1.0.0-dev.0.json"
            runtime.parent.mkdir(parents=True)
            derived.parent.mkdir(parents=True)
            runtime.write_text("runtime\n", encoding="utf-8")
            derived.write_text("derived acceptance\n", encoding="utf-8")

            included = {relative.as_posix() for _path, relative in build_framework_bundle.iter_files(root)}

            self.assertIn("release/runtime.py", included)
            self.assertNotIn("release/acceptance/1.0.0-dev.0.json", included)

    def test_framework_bundle_includes_native_schema_and_knowledge_contracts(self):
        included = {
            relative.as_posix()
            for _path, relative in build_framework_bundle.iter_files(ROOT)
        }

        self.assertIn("schemas/1.0/catalog.json", included)
        self.assertIn("knowledge/AGENT_FRAMEWORK_ADOPTION.en.md", included)
        self.assertNotIn("knowledge_base", build_framework_bundle.DEFAULT_INCLUDE)

    def test_operational_ignore_and_portable_singleton_are_exact(self):
        with tempfile.TemporaryDirectory(prefix="qf-hygiene-") as tmp:
            root = Path(tmp)
            (root / ".superpowers/sdd/tasks.en").mkdir(parents=True)
            (root / ".superpowers/sdd/tasks.en/progress.md").write_text("operational", encoding="utf-8")
            (root / "agent-skills/quillframe").mkdir(parents=True)
            (root / "agent-skills/quillframe/SKILL.md").write_text("singleton", encoding="utf-8")
            (root / "agent-skills/other").mkdir(parents=True)
            (root / "agent-skills/other/SKILL.md").write_text("other", encoding="utf-8")
            with patch.object(framework_hygiene, "ROOT", root), patch.object(framework_hygiene, "STABLE_ROUTERS", set()):
                self.assertEqual(framework_hygiene.bilingual_errors(), ["unpaired human Markdown: agent-skills/other/SKILL.md"])
                framework_hygiene.IGNORED_TREE_PREFIXES.remove(".superpowers/sdd/")
                try:
                    self.assertIn("unpaired human Markdown: .superpowers/sdd/tasks.en/progress.md", framework_hygiene.bilingual_errors())
                finally:
                    framework_hygiene.IGNORED_TREE_PREFIXES.add(".superpowers/sdd/")
                framework_hygiene.INTENTIONALLY_SINGLETON_MARKDOWN.remove(Path("agent-skills/quillframe/SKILL.md"))
                try:
                    self.assertIn("unpaired human Markdown: agent-skills/quillframe/SKILL.md", framework_hygiene.bilingual_errors())
                finally:
                    framework_hygiene.INTENTIONALLY_SINGLETON_MARKDOWN.add(Path("agent-skills/quillframe/SKILL.md"))

    def test_broad_operational_ignore_is_not_accepted(self):
        self.assertIn(".superpowers/sdd/", framework_hygiene.IGNORED_TREE_PREFIXES)
        self.assertNotIn(".superpowers/", framework_hygiene.IGNORED_TREE_PREFIXES)
        self.assertNotIn("tasks.en/", framework_hygiene.IGNORED_TREE_PREFIXES)
        self.assertNotIn("agent-skills/quillframe/SKILL.md", framework_hygiene.STABLE_ROUTERS)

    def test_gitignore_requires_the_exact_operational_boundary(self):
        with tempfile.TemporaryDirectory(prefix="qf-gitignore-") as tmp:
            root = Path(tmp)
            gitignore = root / ".gitignore"
            with patch.object(framework_hygiene, "ROOT", root):
                gitignore.write_text("node_modules/\n.superpowers/sdd/\n", encoding="utf-8")
                self.assertEqual(framework_hygiene.gitignore_errors(), [])
                for mutation in [
                    "node_modules/\n",
                    "node_modules/\n.superpowers/\n",
                    "node_modules/\ntasks.en/\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/\n",
                    "node_modules/\n.superpowers/sdd/\ntasks.en/\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/sdd/*\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/sdd/**\n",
                    "node_modules/\n.superpowers/sdd/\n!.superpowers/sdd/\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/sdd/**/\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/sdd/**foo\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/sdd/[a]\n",
                    "node_modules/\n.superpowers/sdd/\n.superpowers/sdd\n",
                    "node_modules/\n.superpowers/sdd/\n**/.superpowers/sdd/**\n",
                    "node_modules/\n.superpowers/sdd/\n\\.superpowers/sdd/**\n",
                ]:
                    gitignore.write_text(mutation, encoding="utf-8")
                    self.assertTrue(framework_hygiene.gitignore_errors(), mutation)

        self.assertEqual(framework_hygiene.gitignore_errors(), [])

    def test_bridge_runtime_requires_exact_lowercase_action_commit(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("qf_release_bridge", ROOT / ".github/actions/project-peer-semantic/bridge.py")
        assert spec and spec.loader
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        with tempfile.TemporaryDirectory(prefix="qf-release-project-") as tmp:
            workspace = Path(tmp)
            project = workspace / "project"
            project.mkdir()
            (project / "quillframe.toml").write_text(
                'schema = "quillframe_project_v1_0"\nid = "P"\ntitle = "Project"\nlanguage = "en"\n',
                encoding="utf-8",
            )
            base = {
                "GITHUB_WORKSPACE": str(workspace), "QUILLFRAME_PROJECT_CHECKOUT": str(workspace),
                "QUILLFRAME_PROJECT_ROOT": "project", "QUILLFRAME_PROJECT_ID": "P",
                "QUILLFRAME_ACTION_REPOSITORY": "xiaooye/quillframe", "GITHUB_REPOSITORY": "consumer/story",
            }
            for ref in ["a" * 40]:
                with patch.dict(os.environ, {**base, "QUILLFRAME_ACTION_REF": ref}, clear=False):
                    binding = bridge.load_project_binding()
                self.assertEqual(binding["framework_commit"], ref)
            for ref in ["a" * 39, "a" * 41, "A" * 40, "g" * 40, "", " " + "a" * 40]:
                with self.assertRaises(SystemExit):
                    with patch.dict(os.environ, {**base, "QUILLFRAME_ACTION_REF": ref}, clear=False):
                        bridge.load_project_binding()

    def _checker_copy(self):
        tmp = tempfile.TemporaryDirectory(prefix="qf-peer-contract-")
        root = Path(tmp.name)
        (root / ".github/workflows").mkdir(parents=True)
        (root / ".github/actions/project-peer-semantic").mkdir(parents=True)
        for source, target in [
            (peer_bridge_contract.WORKFLOW, root / ".github/workflows/quillframe-chat-semantic-bridge.yml"),
            (peer_bridge_contract.ACTION, root / ".github/actions/project-peer-semantic/action.yml"),
            (peer_bridge_contract.BRIDGE, root / ".github/actions/project-peer-semantic/bridge.py"),
        ]:
            shutil.copy2(source, target)
        return tmp, root

    def _run_checker(self, root: Path) -> int:
        with patch.object(peer_bridge_contract, "ROOT", root), \
             patch.object(peer_bridge_contract, "WORKFLOW", root / ".github/workflows/quillframe-chat-semantic-bridge.yml"), \
             patch.object(peer_bridge_contract, "ACTION", root / ".github/actions/project-peer-semantic/action.yml"), \
             patch.object(peer_bridge_contract, "BRIDGE", root / ".github/actions/project-peer-semantic/bridge.py"), \
             contextlib.redirect_stdout(io.StringIO()):
            return peer_bridge_contract.main()

    def test_peer_checker_accepts_native_provenance_and_rejects_mutations(self):
        tmp, root = self._checker_copy()
        try:
            self.assertEqual(self._run_checker(root), 0)
            workflow = root / ".github/workflows/quillframe-chat-semantic-bridge.yml"
            bridge = root / ".github/actions/project-peer-semantic/bridge.py"
            original_workflow = workflow.read_text(encoding="utf-8")
            original_bridge = bridge.read_text(encoding="utf-8")
            for old, new in [
                ("^[0-9a-f]{40}$", "^.+$"),
                ('ACTUAL_FRAMEWORK_COMMIT=\"$(git -C .quillframe-framework rev-parse HEAD)\"\n', ""),
                ('test \"$ACTUAL_FRAMEWORK_COMMIT\" = \"$EXPECTED_FRAMEWORK_COMMIT\"\n', ""),
                ("printf 'commit=%s\\n' \"$ACTUAL_FRAMEWORK_COMMIT\" >> \"$GITHUB_OUTPUT\"", ""),
            ]:
                mutated = original_workflow.replace(old, new)
                self.assertNotEqual(mutated, original_workflow, old)
                workflow.write_text(mutated, encoding="utf-8")
                self.assertNotEqual(self._run_checker(root), 0, old)
                workflow.write_text(original_workflow, encoding="utf-8")
            action = root / ".github/actions/project-peer-semantic/action.yml"
            original_action = action.read_text(encoding="utf-8")
            action.write_text(original_action.replace("QUILLFRAME_ACTION_REPOSITORY: ${{ github.action_repository }}", "QUILLFRAME_ACTION_REPOSITORY: ''"), encoding="utf-8")
            self.assertNotEqual(self._run_checker(root), 0)
            action.write_text(original_action, encoding="utf-8")
            bridge.write_text(original_bridge.replace('re.fullmatch(r"[0-9a-f]{40}", action_ref)', 're.match(r"[0-9a-f]{40}", action_ref)'), encoding="utf-8")
            self.assertNotEqual(self._run_checker(root), 0)
            bridge.write_text(original_bridge.replace("if caller_repo == action_repo:\n        fail(\"consumer peer bridge may not run with Framework repository as caller\")", ""), encoding="utf-8")
            self.assertNotEqual(self._run_checker(root), 0)
            bridge.write_text(original_bridge, encoding="utf-8")
            bridge.write_text(original_bridge + "\nlocked_commit = action_ref\n", encoding="utf-8")
            self.assertNotEqual(self._run_checker(root), 0)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
