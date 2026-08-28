from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import project_resolution
from harness.session_runtime import resume_preflight
from studio import project_hub_projection


ROOT = Path(__file__).resolve().parents[1]


def write_native_manifest(root: Path, project_id: str = "PROJECT-SLICE-B") -> None:
    (root / "quillframe.toml").write_text(
        "schema = \"quillframe_project_v1_0\"\n"
        f"id = \"{project_id}\"\n"
        "title = \"Slice B fixture\"\n"
        "language = \"en\"\n",
        encoding="utf-8",
    )


class ProjectContractSliceBTests(unittest.TestCase):
    def test_project_sdk_is_removed_from_runtime_and_packaging_surfaces(self):
        self.assertFalse((ROOT / "project_sdk.py").exists())
        forbidden = {
            "pyproject.toml": ["project_sdk"],
            "Dockerfile": ["project_sdk.py"],
            "release/build_framework_bundle.py": ["project_sdk.py"],
            ".github/workflows/quillframe-ci.yml": ["project_sdk.py", "project-sdk-self-test"],
            "quillframe.py": ["PROJECT_SDK", "project-sdk"],
            "quillframe/cli.py": ["project_sdk.py"],
            "scripts/version_identity.py": ["PROJECT_SDK", "project_sdk.py", "SDK_VERSION_RE"],
            "scripts/framework_hygiene.py": ["project_sdk: project_sdk.py"],
            "evals/cases/infra_framework_contract.json": ["project_sdk.py"],
        }
        for relative, markers in forbidden.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            for marker in markers:
                self.assertNotIn(marker, text, f"{relative} still exposes {marker}")

    def test_project_resolution_has_no_build_api_or_cli(self):
        self.assertFalse(hasattr(project_resolution, "build"))
        with tempfile.TemporaryDirectory(prefix="qf-slice-b-resolver-") as tmp:
            root = Path(tmp)
            write_native_manifest(root)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "project_resolution.py"), "build", str(root)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)

    def test_launch_has_an_executable_native_contract_self_test(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "quillframe" / "launch.py"), "self-test"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["launch_contract"], "PASS")
        self.assertEqual(result["project_schema"], "quillframe_project_v1_0")
        self.assertEqual(result["scope"], "novel")

    def test_manifest_machine_contract_is_native_and_has_no_consumer_lock(self):
        manifest = (ROOT / "HARNESS_MANIFEST.yaml").read_text(encoding="utf-8")
        self.assertIn("supported_project_contract: quillframe_project_v1_0", manifest)
        self.assertIn("launch: quillframe/launch.py", manifest)
        self.assertIn("data_root: .quillframe/data", manifest)
        self.assertNotIn("project_sdk: project_sdk.py", manifest)
        self.assertNotIn("lockfile: quillframe.lock.json", manifest)
        self.assertNotIn("caller_must_pin_exact_framework_commit: true", manifest)
        self.assertNotIn("project-sdk-self-test", manifest)

    def test_current_project_identity_uses_native_manifest_without_lock_or_attestation(self):
        with tempfile.TemporaryDirectory(prefix="qf-slice-b-identity-") as tmp:
            root = Path(tmp)
            write_native_manifest(root, "PROJECT-IDENTITY")
            identity, blockers = resume_preflight.current_project_identity(root)
        self.assertEqual(blockers, [])
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity["project_id"], "PROJECT-IDENTITY")
        self.assertEqual(identity["scope"], "novel")
        self.assertTrue(identity["project_manifest_fingerprint"].startswith("sha256:"))
        self.assertTrue(identity["data_root"].endswith(".quillframe/data"))
        self.assertNotIn("framework", identity)
        self.assertNotIn("project_authority_fingerprint", identity)

    def test_peer_bridge_binds_native_manifest_and_action_provenance(self):
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location(
            "quillframe_slice_b_peer_bridge",
            ROOT / ".github/actions/project-peer-semantic/bridge.py",
        )
        assert spec is not None and spec.loader is not None
        bridge = module_from_spec(spec)
        spec.loader.exec_module(bridge)
        with tempfile.TemporaryDirectory(prefix="qf-slice-b-peer-") as tmp:
            workspace = Path(tmp)
            project = workspace / "project"
            project.mkdir()
            write_native_manifest(project, "PROJECT-PEER")
            env = {
                "GITHUB_WORKSPACE": str(workspace),
                "QUILLFRAME_PROJECT_CHECKOUT": str(workspace),
                "QUILLFRAME_PROJECT_ROOT": "project",
                "QUILLFRAME_PROJECT_ID": "PROJECT-PEER",
                "QUILLFRAME_ACTION_REPOSITORY": "xiaooye/quillframe",
                "QUILLFRAME_ACTION_REF": "a" * 40,
                "GITHUB_REPOSITORY": "consumer/story",
            }
            with patch.dict(os.environ, env, clear=False):
                binding = bridge.load_project_binding()
        self.assertEqual(binding["project_id"], "PROJECT-PEER")
        self.assertEqual(binding["scope"], "novel")
        self.assertTrue(binding["manifest_fingerprint"].startswith("sha256:"))
        self.assertEqual(binding["framework_repo"], "xiaooye/quillframe")
        self.assertEqual(binding["framework_commit"], "a" * 40)
        self.assertNotIn("lock_path", binding)

    def test_project_projection_consumes_context_v1_and_excludes_old_authority(self):
        source = {
            "context_schema": "quillframe_project_context_v1_0",
            "manifest": {
                "schema": "quillframe_project_v1_0",
                "id": "PROJECT-PROJECTION",
                "title": "Projection fixture",
                "language": "en",
            },
            "manifest_fingerprint": project_hub_projection.fingerprint({
                "schema": "quillframe_project_v1_0", "id": "PROJECT-PROJECTION", "title": "Projection fixture", "language": "en",
            }),
            "project_id": "PROJECT-PROJECTION",
            "project_title": "Projection fixture",
            "language": "en",
            "scope": "novel",
            "project_root": "/private/project",
            "data_root": "/private/project/.quillframe/data",
        }
        projection = project_hub_projection.build_projection(source, "cloud_ui")
        self.assertEqual(projection["source_schema"], "quillframe_project_context_v1_0")
        self.assertEqual(projection["project"]["id"], "PROJECT-PROJECTION")
        self.assertEqual(projection["project"]["scope"], "novel")
        self.assertEqual(projection["project"]["manifest_fingerprint"], source["manifest_fingerprint"])
        self.assertNotIn("framework_lock", projection)
        self.assertNotIn("framework_attestation", projection)
        self.assertNotIn("layout", projection["project"])
        self.assertNotIn("project_version", projection["project"])
        self.assertNotIn("project_root", json.dumps(projection))
        self.assertNotIn("data_root", json.dumps(projection))

    def test_project_hub_rejects_manifest_fingerprint_mutation(self):
        with self.assertRaises(ValueError):
            project_hub_projection.build_projection({
                "context_schema": "quillframe_project_context_v1_0",
                "manifest": {"schema": "quillframe_project_v1_0", "id": "P", "title": "Novel", "language": "en"},
                "manifest_fingerprint": "sha256:" + "a" * 64,
                "project_id": "P", "project_title": "Novel", "language": "en", "scope": "novel",
            })

    def test_project_hub_rejects_native_field_mutations_and_normalizes_text(self):
        base = {"context_schema": "quillframe_project_context_v1_0", "manifest": {"schema": "quillframe_project_v1_0", "id": "P", "title": " Novel ", "language": " en-US "}, "manifest_fingerprint": project_hub_projection.fingerprint({"schema": "quillframe_project_v1_0", "id": "P", "title": "Novel", "language": "en-US"}), "project_id": "P", "project_title": "Novel", "language": "en-US", "scope": "novel"}
        projection = project_hub_projection.build_projection(base)
        self.assertEqual(projection["project"]["title"], "Novel")
        for field, value in (("id", 7), ("id", "../escape"), ("title", " "), ("language", 9)):
            mutated = dict(base, manifest=dict(base["manifest"], **{field: value}))
            with self.assertRaises(ValueError):
                project_hub_projection.build_projection(mutated)

    def test_resolver_and_projection_share_one_context_fingerprint(self):
        with tempfile.TemporaryDirectory(prefix="qf-slice-b-agreement-") as tmp:
            root = Path(tmp)
            write_native_manifest(root, "PROJECT-AGREEMENT")
            context = project_resolution.resolve_contract(root)
            projection = project_hub_projection.build_projection(context, "local_app")
        self.assertEqual(projection["source_schema"], context["context_schema"])
        self.assertEqual(projection["project"]["id"], context["project_id"])
        self.assertEqual(projection["project"]["manifest_fingerprint"], context["manifest_fingerprint"])
        self.assertEqual(projection["project"]["scope"], "novel")

    def test_projection_fixture_is_native_or_absent(self):
        fixture = ROOT / "studio/fixtures/project-context.synthetic.json"
        if not fixture.exists():
            return
        value = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(value.get("context_schema"), "quillframe_project_context_v1_0")
        serialized = json.dumps(value)
        for marker in ("framework_lock", "framework_attestation", "layout", "project_version", "project_root"):
            self.assertNotIn(marker, serialized)

    def test_runtime_self_tests_do_not_construct_legacy_project_contract(self):
        paths = (
            "harness/session_runtime/resume_preflight.py",
            "harness/session_runtime/runtime_command_executor.py",
            "harness/session_runtime/terminate_preflight.py",
            "harness/session_runtime/terminate_executor.py",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn('quillframe_lock_v1', text, relative)
            self.assertNotIn('framework.attestation.json', text, relative)
            self.assertNotIn('[quillframe]', text, relative)


if __name__ == "__main__":
    unittest.main()
