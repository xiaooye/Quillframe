from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NamespaceHygieneTests(unittest.TestCase):
    def test_generated_and_dependency_outputs_do_not_change_source_hygiene_result(self):
        forbidden = "Novel" + "Forge"
        with tempfile.TemporaryDirectory(prefix="qf-namespace-") as td:
            sandbox = Path(td)
            (sandbox / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts" / "namespace_hygiene.py", sandbox / "scripts" / "namespace_hygiene.py")
            for relative in (
                "site/dist/generated/leak.json",
                "site/public/generated/leak.json",
                "site/docs-site/node_modules/leak.js",
                "studio/app/node_modules/leak.js",
            ):
                target = sandbox / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(forbidden, encoding="utf-8")
            active = sandbox / "active.py"
            active.write_text("print('quillframe')\n", encoding="utf-8")

            clean = subprocess.run(
                [sys.executable, "scripts/namespace_hygiene.py"],
                cwd=sandbox,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

            active.write_text(f"# {forbidden}\n", encoding="utf-8")
            dirty = subprocess.run(
                [sys.executable, "scripts/namespace_hygiene.py"],
                cwd=sandbox,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(dirty.returncode, 1)
            self.assertIn("active.py", dirty.stdout)

    def test_machine_namespace_ignores_generated_and_dependency_outputs(self):
        forbidden = "NOVEL" + "_OS_"
        with tempfile.TemporaryDirectory(prefix="qf-machine-namespace-") as td:
            sandbox = Path(td)
            (sandbox / "scripts").mkdir()
            shutil.copy2(
                ROOT / "scripts" / "machine_namespace_hygiene.py",
                sandbox / "scripts" / "machine_namespace_hygiene.py",
            )
            for relative in (
                "site/dist/generated/leak.json",
                "site/public/generated/leak.json",
                "site/docs-site/node_modules/.astro/leak.json",
                "studio/app/node_modules/leak.json",
            ):
                target = sandbox / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(forbidden, encoding="utf-8")
            active = sandbox / "active.py"
            active.write_text("print('quillframe')\n", encoding="utf-8")

            clean = subprocess.run(
                [sys.executable, "scripts/machine_namespace_hygiene.py"],
                cwd=sandbox,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

            active.write_text(f"# {forbidden}\n", encoding="utf-8")
            dirty = subprocess.run(
                [sys.executable, "scripts/machine_namespace_hygiene.py"],
                cwd=sandbox,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(dirty.returncode, 1)
            self.assertIn("active.py", dirty.stdout)


if __name__ == "__main__":
    unittest.main()
