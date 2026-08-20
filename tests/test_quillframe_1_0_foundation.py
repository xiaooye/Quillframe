from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from fnmatch import fnmatch
from pathlib import Path

from evals.validate_semantic_acceptance import framework_version
from harness.control_plane.mcp_stdio import MCPServer
from studio import host_bridge


ROOT = Path(__file__).resolve().parents[1]


def version_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split("-", 1)[0].split("."))  # type: ignore[return-value]


class CleanBreakFoundationTests(unittest.TestCase):
    def test_canonical_schema_catalog_is_complete_and_ch001_bounded(self):
        root = ROOT / "schemas" / "1.0"
        catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
        expected = {
            "quillframe_scene_intent_v1",
            "quillframe_character_intent_v1",
            "quillframe_transition_constraints_v1",
            "quillframe_risk_signals_v1",
            "quillframe_repair_plan_v1",
            "quillframe_generation_packet_v1",
            "quillframe_author_run_event_v1",
            "quillframe_model_task_profile_v1",
            "quillframe_model_route_receipt_v1",
            "quillframe_cloud_project_manifest_v1",
            "quillframe_secret_lease_receipt_v1",
            "quillframe_launch_receipt_v1",
        }
        self.assertEqual(set(catalog["schemas"]), expected)
        for schema_id, relative in catalog["schemas"].items():
            schema = json.loads((root / relative).read_text(encoding="utf-8"))
            self.assertEqual(schema["properties"]["schema"]["const"], schema_id)
            self.assertFalse(schema["additionalProperties"])
            if "chapter_id" in schema["properties"]:
                self.assertEqual(schema["properties"]["chapter_id"], {"const": "CH001"})

    def test_host_bridge_is_v11_only(self):
        contract = host_bridge.contract()
        self.assertEqual(contract["schema"], "quillframe_host_bridge_contract_v11")
        self.assertEqual(contract["version"], "11")
        self.assertNotIn("deprecated_input_aliases", json.dumps(contract))
        self.assertNotIn("legacy", json.dumps(contract).lower())
        for operation in (
            "author.run.resume",
            "author.run.cancel",
            "author.run.events",
            "model.route.preview",
        ):
            self.assertIn(operation, contract["operations"])

    def test_bridge_rejects_old_and_missing_version_envelopes(self):
        base = {
            "schema": host_bridge.REQUEST_SCHEMA,
            "request_id": "foundation",
            "operation": "bridge.describe",
            "surface": "local_app",
            "args": {},
            "authority": False,
        }
        for request in (
            {**base, "schema": "quillframe_studio_host_bridge_request_v1", "bridge_version": "10"},
            {**base, "bridge_version": "10"},
            base,
        ):
            with self.subTest(request=request):
                response = host_bridge.invoke(request)
                self.assertEqual(response["status"], "invalid")
                self.assertFalse(response["error"]["mutation_performed"])

        current = host_bridge.invoke({**base, "bridge_version": "11"})
        self.assertEqual(current["status"], "ok")
        self.assertEqual(current["data"]["contract_version"], "11")

    def test_mcp_requires_exact_2026_07_28_initialize(self):
        server = MCPServer(":memory:")
        for version in (None, "2025-06-18", "2026-03-26"):
            params = {} if version is None else {"protocolVersion": version}
            response = server.handle(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": params}
            )
            self.assertEqual(response["error"]["code"], -32602)
            server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
            blocked = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            self.assertEqual(blocked["error"]["code"], -32002)

        accepted = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "initialize",
                "params": {"protocolVersion": "2026-07-28"},
            }
        )
        self.assertEqual(accepted["result"]["protocolVersion"], "2026-07-28")

    def test_root_declares_one_pnpm_workspace(self):
        workspace = (ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8")
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertIn("site", workspace)
        self.assertIn("studio/app", workspace)
        self.assertIn("cloud", workspace)
        self.assertEqual(package["packageManager"], "pnpm@10.33.0")
        self.assertTrue((ROOT / "pnpm-lock.yaml").is_file())
        nested_locks = [
            path
            for path in ROOT.rglob("pnpm-lock.yaml")
            if path != ROOT / "pnpm-lock.yaml"
        ]
        self.assertEqual(nested_locks, [])

    def test_development_semver_is_a_first_class_framework_identity(self):
        self.assertEqual(version_tuple("1.0.0-dev.0"), (1, 0, 0))
        self.assertEqual(framework_version(), "1.0.0-dev.0")

    def test_declared_wheel_layout_imports_every_public_runtime_surface(self):
        """Dropping a runtime package from pyproject must break this smoke test."""
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        setuptools = config["tool"]["setuptools"]
        includes = setuptools["packages"]["find"]["include"]
        modules = setuptools.get("py-modules", [])

        with tempfile.TemporaryDirectory() as directory:
            install_root = Path(directory)
            for candidate in ROOT.iterdir():
                if not candidate.is_dir() or not any(candidate.rglob("*.py")):
                    continue
                if any(fnmatch(candidate.name, pattern.removesuffix("*")) for pattern in includes):
                    shutil.copytree(
                        candidate,
                        install_root / candidate.name,
                        ignore=shutil.ignore_patterns("node_modules", "dist", "__pycache__"),
                    )
            for module in modules:
                shutil.copy2(ROOT / f"{module}.py", install_root / f"{module}.py")

            env = {**os.environ, "PYTHONPATH": str(install_root), "PYTHONDONTWRITEBYTECODE": "1"}
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import quillframe.cli; import quillframe.cloud_core; "
                        "import production_runtime.semantic; "
                        "from studio import host_bridge; "
                        "assert host_bridge.contract()['version'] == '11'"
                    ),
                ],
                cwd=install_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_studio_well_known_manifests_are_explicit_wheel_data(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_data = config["tool"]["setuptools"]["package-data"]["studio"]
        expected = {
            "app/dist/.well-known/quillframe-studio-footprint.json",
            "app/dist/.well-known/quillframe-host.json",
            "app/dist/.well-known/security.txt",
        }
        self.assertTrue(expected.issubset(set(package_data)))


if __name__ == "__main__":
    unittest.main()
