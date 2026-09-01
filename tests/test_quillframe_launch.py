from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quillframe import cli
from quillframe.launch import (
    LaunchError,
    _assert_manifest_guard_current,
    _open_manifest_guard,
    launch_project,
    resolve_project_root,
)
from project_resolution import resolve_contract


class LaunchTests(unittest.TestCase):
    def test_manifest_descriptor_read_has_windows_fallback(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-fd-") as td:
            path = Path(td) / "quillframe.toml"
            payload = b'schema = "quillframe_project_v1_0"\r\nid = "novel"\r\n'
            path.write_bytes(payload)
            expected = "sha256:" + hashlib.sha256(payload).hexdigest()
            guard = None
            try:
                with patch.object(os, "pread", None, create=True):
                    guard = _open_manifest_guard(Path(td), expected)
                    _assert_manifest_guard_current(guard)
            finally:
                if guard is not None:
                    os.close(guard.fd)

    def test_launch_keeps_user_corpus_outside_project_data_root(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-corpus-") as td, patch.dict(
            os.environ,
            {
                "QUILLFRAME_DATA_DIR": str(Path(td) / "user-data"),
                "QUILLFRAME_LAUNCH_STATE": str(Path(td) / "launch-state.json"),
            },
        ):
            os.environ.pop("QUILLFRAME_CORPUS_DIR", None)
            root = Path(td) / "novel"
            launched = launch_project(
                project=root,
                new=True,
                profile="local",
                project_id="novel",
                title="Novel",
                language="en",
                port=0,
                no_browser=True,
                serve=False,
            )
            self.assertEqual(
                Path(os.environ["QUILLFRAME_DATA_DIR"]),
                root / ".quillframe" / "data",
            )
            self.assertEqual(
                Path(os.environ["QUILLFRAME_CORPUS_DIR"]),
                Path(td) / "user-data" / "corpus",
            )
            launched.close()
            self.assertEqual(
                Path(os.environ["QUILLFRAME_DATA_DIR"]), Path(td) / "user-data"
            )
            self.assertNotIn("QUILLFRAME_CORPUS_DIR", os.environ)

    def test_new_local_project_is_project_local_and_receipt_is_secret_free(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-") as td:
            root = Path(td) / "novel"
            dist = Path(td) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text(
                '<meta name="quillframe-studio-token" content="__QUILLFRAME_STUDIO_TOKEN__">',
                encoding="utf-8",
            )
            launched = launch_project(
                project=root,
                new=True,
                profile="local",
                project_id="novel",
                title="Novel",
                language="en",
                port=0,
                no_browser=True,
                dist=dist,
                serve=False,
            )
            receipt = launched.receipt
            self.assertEqual(receipt["schema"], "quillframe_launch_receipt_v1")
            self.assertEqual(receipt["profile"], "local")
            self.assertEqual(receipt["storage_boundary"], "project_local_sqlite")
            self.assertTrue(receipt["url"].startswith("http://127.0.0.1:"))
            self.assertFalse(receipt["browser_opened"])
            self.assertFalse(receipt["cloud_upload_started"])
            self.assertTrue((root / "quillframe.toml").is_file())
            self.assertTrue(any((root / ".quillframe" / "data").rglob("project.sqlite")))
            serialized = json.dumps(receipt).lower()
            self.assertNotIn("token", serialized)
            self.assertNotIn("secret", serialized)
            launched.close()

    def test_current_project_resolution_walks_parents_without_legacy_import(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-resolve-") as td:
            root = Path(td) / "novel"
            child = root / "notes" / "today"
            child.mkdir(parents=True)
            (root / "quillframe.toml").write_text(
                'schema = "quillframe_project_v1_0"\nid = "novel"\ntitle = "Novel"\nlanguage = "en"\n',
                encoding="utf-8",
            )
            self.assertEqual(resolve_project_root(child), root)
            self.assertEqual(resolve_contract(root)["scope"], "novel")
            self.assertFalse((root / ".quillframe" / "imports").exists())

    def test_cloud_profile_never_uploads_implicitly(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-cloud-") as td:
            root = Path(td) / "novel"
            launched = launch_project(
                project=root,
                new=True,
                profile="cloud",
                project_id="novel",
                title="Novel",
                language="en",
                port=0,
                no_browser=True,
                serve=False,
            )
            self.assertEqual(launched.receipt["profile"], "cloud")
            self.assertEqual(launched.receipt["status"], "awaiting_authentication")
            self.assertFalse(launched.receipt["cloud_upload_started"])
            self.assertFalse(any(root.rglob("uploaded*")))
            launched.close()

    def test_no_argument_launch_uses_last_explicitly_opened_project(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-last-") as td:
            root = Path(td) / "novel"
            dist = Path(td) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text(
                '<meta name="quillframe-studio-token" content="__QUILLFRAME_STUDIO_TOKEN__">',
                encoding="utf-8",
            )
            previous = os.environ.get("QUILLFRAME_LAUNCH_STATE")
            os.environ["QUILLFRAME_LAUNCH_STATE"] = str(Path(td) / "launch-state.json")
            try:
                first = launch_project(
                    project=root,
                    new=True,
                    profile="local",
                    project_id="novel",
                    title="Novel",
                    language="en",
                    port=0,
                    no_browser=True,
                    dist=dist,
                    serve=False,
                )
                first.close()
                second = launch_project(
                    project=None,
                    new=False,
                    profile="local",
                    project_id=None,
                    title=None,
                    language="en",
                    port=0,
                    no_browser=True,
                    dist=dist,
                    serve=False,
                    interactive=False,
                )
                self.assertEqual(Path(second.receipt["project_root"]), root)
                second.close()
            finally:
                if previous is None:
                    os.environ.pop("QUILLFRAME_LAUNCH_STATE", None)
                else:
                    os.environ["QUILLFRAME_LAUNCH_STATE"] = previous

    def test_noninteractive_unresolved_launch_fails_typed(self):
        with tempfile.TemporaryDirectory(prefix="qf-launch-none-") as td:
            with self.assertRaises(LaunchError) as blocked:
                launch_project(
                    project=Path(td),
                    new=False,
                    profile="local",
                    project_id=None,
                    title=None,
                    language="en",
                    port=0,
                    no_browser=True,
                    serve=False,
                    interactive=False,
                )
            self.assertEqual(blocked.exception.code, "project_resolution_required")

    def test_cli_launch_declares_the_all_in_one_flags_and_emits_receipt(self):
        class FakeLaunch:
            receipt = {
                "schema": "quillframe_launch_receipt_v1",
                "status": "ready",
                "profile": "local",
            }

            def serve_forever(self):
                return None

        with tempfile.TemporaryDirectory(prefix="qf-launch-cli-") as td, patch.object(
            cli,
            "launch_project",
            return_value=FakeLaunch(),
            create=True,
        ) as invoked, patch("builtins.print") as printed:
            code = cli.main(
                [
                    "launch",
                    str(Path(td) / "novel"),
                    "--new",
                    "--profile",
                    "local",
                    "--id",
                    "novel",
                    "--title",
                    "Novel",
                    "--language",
                    "en",
                    "--port",
                    "43111",
                    "--no-browser",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(invoked.call_args.kwargs["profile"], "local")
        self.assertTrue(invoked.call_args.kwargs["new"])
        self.assertTrue(invoked.call_args.kwargs["no_browser"])
        self.assertEqual(invoked.call_args.kwargs["port"], 43111)
        payload = json.loads(printed.call_args.args[0])
        self.assertEqual(payload["schema"], "quillframe_launch_receipt_v1")

    def test_pre_1_0_cli_commands_are_not_registered(self):
        for old_command in ("init", "pin", "validate", "build", "host-install", "host-run", "claude-hook", "codex-hook"):
            with self.subTest(old_command=old_command), patch("builtins.print"):
                with self.assertRaises(SystemExit) as rejected:
                    cli.main([old_command])
                self.assertEqual(rejected.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
