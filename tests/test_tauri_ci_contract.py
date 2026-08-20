"""Behavioral contract for the single authoritative Studio/Tauri CI path."""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEDICATED = ROOT / ".github/workflows/studio-tauri-ci.yml"
CORE = ROOT / ".github/workflows/quillframe-ci.yml"


def load_workflow(path: Path) -> dict:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    # PyYAML's YAML 1.1 resolver reads the unquoted GitHub `on` key as True.
    if True in parsed and "on" not in parsed:
        parsed["on"] = parsed.pop(True)
    return parsed


def event_paths(workflow: dict, event: str) -> list[str]:
    return workflow["on"][event]["paths"]


def workflow_text(workflow: dict) -> str:
    return json.dumps(workflow, ensure_ascii=False, sort_keys=True)


class TauriCiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dedicated = load_workflow(DEDICATED)
        cls.core = load_workflow(CORE)
        cls.steps = cls.dedicated["jobs"]["linux-desktop-host"]["steps"]
        cls.step_text = json.dumps(cls.steps, ensure_ascii=False, sort_keys=True)
        cls.commands = [step.get("run", "") for step in cls.steps]

    def test_single_authoritative_tauri_job(self) -> None:
        self.assertIn("linux-desktop-host", self.dedicated["jobs"])
        self.assertNotIn("tauri", self.core.get("jobs", {}))
        self.assertEqual(
            [name for name in self.dedicated["jobs"] if "tauri" in name.lower() or "desktop" in name.lower()],
            ["linux-desktop-host"],
        )

    def test_both_workflows_have_complete_path_filters(self) -> None:
        required = {
            "package.json",
            "pnpm-workspace.yaml",
            "pnpm-lock.yaml",
            "site/**",
            "studio/app/package.json",
            "studio/app/src/**",
            "studio/app/public/**",
            "studio/app/scripts/**",
            "studio/app/tests/**",
            "studio/app/vite.config.ts",
            "studio/app/tsconfig.json",
            "studio/app/index.html",
            "studio/app/src-tauri/**",
            "studio/tauri_core_sidecar.py",
            "studio/scripts/build_tauri_sidecar.py",
            "studio/host_bridge.py",
            "studio/host_bridge_protocol.py",
            "studio/host_bridge_contract.json",
            "model_runtime/**",
            "persistence/**",
            "agent_runtime/**",
            "core_operations.py",
            "production_runtime/**",
            "publication/**",
            "project_resolution.py",
            "harness/**",
            "quality/**",
            "schemas/**",
            "VERSION",
            "pyproject.toml",
            ".github/workflows/studio-tauri-ci.yml",
            ".github/workflows/quillframe-ci.yml",
        }
        for event in ("push", "pull_request"):
            self.assertTrue(required.issubset(set(event_paths(self.dedicated, event))), (event, sorted(set(required) - set(event_paths(self.dedicated, event)))))

    def test_native_dependency_changes_trigger_both_dedicated_events(self) -> None:
        paths = set(event_paths(self.dedicated, "push"))
        self.assertEqual(paths, set(event_paths(self.dedicated, "pull_request")))
        for expected in ("studio/app/tests/**", "studio/app/vite.config.ts", "studio/app/tsconfig.json", "studio/app/index.html", "agent_runtime/**", "publication/**", "schemas/**", "pyproject.toml"):
            self.assertIn(expected, paths, expected)

    def test_root_lock_and_frozen_install_only(self) -> None:
        text = self.step_text
        setup_node = next(step for step in self.steps if step.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual(setup_node["with"]["cache-dependency-path"], "pnpm-lock.yaml")
        self.assertIn("pnpm install --frozen-lockfile", text)
        self.assertNotIn("studio/app/pnpm-lock.yaml", text)
        self.assertNotRegex(text, r"(?:cd studio/app|working-directory:\s*studio/app).*pnpm install")
        self.assertEqual((ROOT / "pnpm-lock.yaml").is_file(), True)
        self.assertEqual((ROOT / "studio/app/pnpm-lock.yaml").exists(), False)

    def test_rust_toolchain_and_linux_dependencies_are_pinned(self) -> None:
        rust_setup = next(step for step in self.steps if step.get("uses", "").startswith("dtolnay/rust-toolchain@"))
        self.assertEqual(rust_setup["uses"], "dtolnay/rust-toolchain@1.90.0")
        self.assertNotRegex(self.step_text, r"rust-toolchain@(stable|latest|1\.88(?:\.\d+)?)")
        self.assertEqual(rust_setup["with"]["components"], "rustfmt, clippy")
        for package in (
            "libwebkit2gtk-4.1-dev", "build-essential", "curl", "wget", "file",
            "libxdo-dev", "libssl-dev", "libayatana-appindicator3-dev",
            "librsvg2-dev", "patchelf", "pkg-config", "dbus-x11", "gnome-keyring",
        ):
            self.assertIn(package, self.step_text, package)

    def test_ordered_frontend_sidecar_cargo_and_tauri_gates(self) -> None:
        ordered = [
            "build:assets", "playwright-core install", "browser:smoke", "browser:launch",
            "build:finalize", "pyinstaller", "tauri_core_sidecar.py self-test",
            "build_tauri_sidecar.py", "quillframe-core-", "cargo fmt", "cargo metadata", "cargo clippy",
            "cargo test", "cargo check", "dbus-run-session", "cargo install tauri-cli",
            "cargo tauri build --debug --no-bundle --config src-tauri/tauri.conf.json -- --locked",
        ]
        positions = []
        for needle in ordered:
            positions.append(self.step_text.index(needle))
        self.assertEqual(positions, sorted(positions))

    def test_all_cargo_project_gates_are_locked_and_root_explicit(self) -> None:
        cargo_commands = [command for command in self.commands if "cargo " in command]
        self.assertGreaterEqual(len(cargo_commands), 5)
        for command in cargo_commands:
            if "cargo install" not in command and "cargo fmt" not in command:
                self.assertIn("--locked", command, command)
        self.assertIn("cargo fmt --manifest-path studio/app/src-tauri/Cargo.toml -- --check", self.step_text)
        self.assertIn("cargo metadata --locked --no-deps --manifest-path studio/app/src-tauri/Cargo.toml", self.step_text)
        self.assertIn("--manifest-path studio/app/src-tauri/Cargo.toml", self.step_text)
        tauri_step = next(step for step in self.steps if "cargo tauri build" in step.get("run", ""))
        self.assertEqual(tauri_step["working-directory"], "studio/app")
        self.assertIn("--config src-tauri/tauri.conf.json", self.step_text)
        self.assertNotIn("manifest-path studio/app/src-tauri/Cargo.toml --config", self.step_text)

    def test_secret_service_step_is_scrubbed_and_normal_ci_has_no_live_model(self) -> None:
        self.assertIn("dbus-run-session", self.step_text)
        self.assertNotIn("cat /tmp/qf-keyring.env", self.step_text)
        self.assertNotIn("--nocapture", self.step_text)
        self.assertNotIn("QUILLFRAME_MODEL_API_TOKEN", self.step_text)
        self.assertNotIn("WORKOS", self.step_text)
        self_test = next(step for step in self.steps if step.get("name") == "Sidecar source self-test")
        self.assertIn('assert report["model_execution"] is False', self_test["run"])
        self.assertIn('assert report["authority"] is False', self_test["run"])

    def test_sidecar_self_test_has_strict_explicit_truth_fields(self) -> None:
        output = subprocess.check_output(["python", str(ROOT / "studio/tauri_core_sidecar.py"), "self-test"], text=True)
        report = json.loads(output)
        self.assertIs(report["model_execution"], False)
        self.assertIs(report["authority"], False)
        self.assertIs(report["secret_values_exposed"], False)
        for mutated in ({key: value for key, value in report.items() if key != "model_execution"}, {**report, "model_execution": True}):
            with self.assertRaises((KeyError, AssertionError)):
                self.assertIs(mutated["model_execution"], False)

    def test_tauri_config_resolves_generated_frontend_and_sidecar(self) -> None:
        config = json.loads((ROOT / "studio/app/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
        self.assertEqual(config["build"]["frontendDist"], "../dist")
        self.assertEqual(config["bundle"]["externalBin"], ["binaries/quillframe-core"])
        self.assertIn("target", self.step_text)

    def test_no_unsafe_mutable_or_secret_output_patterns(self) -> None:
        self.assertNotRegex(self.step_text, r"\bpnpm install(?! --frozen-lockfile)")
        self.assertNotIn("env |", self.step_text)
        self.assertNotIn("printenv", self.step_text)
        self.assertNotIn("echo $", self.step_text)

    def test_cargo_minimum_is_not_above_workflow_toolchain(self) -> None:
        cargo = (ROOT / "studio/app/src-tauri/Cargo.toml").read_text(encoding="utf-8")
        minimum = tuple(map(int, re.search(r'rust-version\s*=\s*"(\d+)\.(\d+)"', cargo).groups()))
        toolchain = tuple(map(int, re.search(r"rust-toolchain@(\d+)\.(\d+)\.\d+", self.step_text).groups()))
        self.assertLessEqual(minimum, toolchain)


if __name__ == "__main__":
    unittest.main()
