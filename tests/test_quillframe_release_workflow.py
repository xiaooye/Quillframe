from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quillframe-release-bundle.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "quillframe-ci.yml"
DOCKERFILE = ROOT / "Dockerfile"


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_development_bundle_is_manual_deterministic_and_non_releasing(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("1.0.0-dev.0", text)
        self.assertNotIn("gh release create", text)
        self.assertNotIn("push:\n    tags:", text)
        self.assertNotIn("tags: ['v*']", text)
        self.assertNotIn("RELEASE_TAG", text)
        self.assertIn("python scripts/version_consistency.py", text)
        self.assertIn("python scripts/version_identity.py", text)
        self.assertIn("python quality/clean_break.py", text)
        self.assertIn('cmp "acceptance-out/${BUNDLE_NAME}" "acceptance-out/quillframe-framework-${COMMIT}.second.tar"', text)
        self.assertIn('python release/build_framework_bundle.py verify --bundle "acceptance-out/${BUNDLE_NAME}"', text)
        self.assertIn('rm "acceptance-out/quillframe-framework-${COMMIT}.second.tar"', text)
        self.assertNotIn("acceptance-out/quillframe-framework-*.tar", text)
        self.assertIn('"release_promotion_performed": False', text)
        self.assertIn('"hosted_deployment": "awaiting_external"', text)
        self.assertIn('"model_execution": False', text)
        self.assertIn('uses: actions/upload-artifact@v4', text)


class DistributionWorkflowContractTests(unittest.TestCase):
    def test_dependency_updates_use_the_shared_workspace_lockfile_root(self):
        workspace_path = ROOT / "pnpm-workspace.yaml"
        workspace = yaml.safe_load(workspace_path.read_text(encoding="utf-8"))
        lockfile = yaml.safe_load((workspace_path.parent / "pnpm-lock.yaml").read_text(encoding="utf-8"))
        dependabot = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
        update_roots = [
            (ROOT / directory.lstrip("/")).resolve()
            for update in dependabot["updates"]
            if update["package-ecosystem"] == "npm"
            for directory in (
                update["directories"] if "directories" in update else [update["directory"]]
            )
        ]

        self.assertEqual(
            update_roots,
            [workspace_path.parent],
            "Dependency updates must run once from the shared lockfile root, not individual packages.",
        )
        for package in workspace["packages"]:
            with self.subTest(package=package):
                self.assertTrue((update_roots[0] / package / "package.json").is_file())
                self.assertIn(package, lockfile["importers"])

    def test_installed_wheel_smoke_follows_studio_build_in_product_job(self):
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        product = text.split("\n  product:\n", 1)[1]

        self.assertIn("uses: actions/setup-python@v7", product)
        self.assertIn("python-version: '3.13'", product)
        studio_build = product.index("name: Build Site, Docs, Studio and Cloud")
        wheel_smoke = product.index("name: Build and test the installed wheel")
        self.assertLess(studio_build, wheel_smoke)
        self.assertNotIn("pip wheel .", text.split("\n  product:\n", 1)[0])

        for fragment in (
            "python -m pip wheel . --no-deps -w /tmp/quillframe-wheel",
            "python -m pip install --no-deps --target /tmp/quillframe-install",
            "cd /tmp",
            "import quillframe.cli",
            "import quillframe.cloud_core",
            "import production_runtime.semantic",
            'resolve_contract_registry("reader.reaction")',
            'files("studio").joinpath("app/dist/index.html").is_file()',
            'files("studio").joinpath("app/dist/.well-known/quillframe-studio-footprint.json").is_file()',
            'files("studio").joinpath("app/dist/.well-known/quillframe-host.json").is_file()',
            'files("studio").joinpath("app/dist/.well-known/security.txt").is_file()',
            'main(["--help"])',
        ):
            self.assertIn(fragment, product)

    def test_docker_smoke_cannot_import_from_wheel_build_checkout(self):
        text = DOCKERFILE.read_text(encoding="utf-8")

        self.assertIn("WORKDIR /srv/quillframe", text)
        self.assertNotIn("WORKDIR /app", text)
        self.assertIn("/tmp/quillframe-build/pyproject.toml", text)
        self.assertIn("python -m pip wheel", text)
        self.assertNotIn("COPY pyproject.toml /app/pyproject.toml", text)

    def test_docker_build_context_copies_every_declared_runtime_package(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        includes = config["tool"]["setuptools"]["packages"]["find"]["include"]

        for pattern in includes:
            package = pattern.removesuffix("*")
            self.assertIn(
                f"COPY {package} /tmp/quillframe-build/{package}",
                text,
                package,
            )


if __name__ == "__main__":
    unittest.main()
