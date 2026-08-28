from __future__ import annotations

import json
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pathlib import Path

from harness.settlement_runtime import TX_SCHEMA, apply_authority, connect, prepare
from harness.property_write_policy import policy_from_project
from persistence.quillframe_sqlite import QuillframeStore
from quillframe import launch as launch_module
from project_resolution import resolve_contract
from quillframe.launch import LaunchError, launch_project


def write_manifest(root: Path, **overrides: str) -> None:
    values = {
        "schema": "quillframe_project_v1_0",
        "id": "PROJECT-TEST",
        "title": "Fixture",
        "language": "en",
    }
    values.update(overrides)
    lines = []
    for key, value in values.items():
        lines.append(f"{key} = {json.dumps(value)}")
    (root / "quillframe.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_existing_with_ch001(data: Path, project_id: str, title: str, language: str) -> None:
    """Construct a valid existing Project through the raw store plus explicit CH001 seed."""
    store = QuillframeStore(data)
    store.create_project(project_id, title, language)
    with store.open_project(project_id) as conn:
        conn.execute(
            """INSERT INTO story_nodes(
            node_id,parent_id,kind,ordinal,title,pov_character_id,location_id,metadata_json
            ) VALUES(?,NULL,'chapter',1,?,NULL,NULL,'{}')""",
            ("CH001", title),
        )
        conn.execute(
            """INSERT INTO documents(
            document_id,story_node_id,document_kind,title,created_at
            ) VALUES(?,?,?, ?,?)""",
            ("DOC-CH001", "CH001", "manuscript", title, "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()


def business_rows(data: Path, project_id: str) -> tuple[tuple[object, ...], tuple[object, ...]]:
    with QuillframeStore(data, read_only=True).open_project(project_id) as conn:
        nodes = tuple(tuple(row) for row in conn.execute(
            "SELECT node_id,parent_id,kind,ordinal,title,pov_character_id,location_id,metadata_json "
            "FROM story_nodes ORDER BY node_id"
        ).fetchall())
        documents = tuple(tuple(row) for row in conn.execute(
            "SELECT document_id,story_node_id,document_kind,title FROM documents ORDER BY document_id"
        ).fetchall())
    return nodes, documents


class ProjectContractSliceATests(unittest.TestCase):
    def test_flat_manifest_accepts_exact_four_keys(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-flat-") as td:
            root = Path(td)
            write_manifest(root)

            context = resolve_contract(root)

            self.assertEqual(
                set(context["manifest"]),
                {"schema", "id", "title", "language"},
            )
            self.assertEqual(context["manifest"]["schema"], "quillframe_project_v1_0")
            self.assertEqual(context["scope"], "novel")
            self.assertEqual(Path(context["project_root"]), root.resolve())
            self.assertEqual(Path(context["data_root"]), root.resolve() / ".quillframe" / "data")

    def test_flat_manifest_rejects_extra_key(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-extra-") as td:
            root = Path(td)
            write_manifest(root, extra="forbidden")

            with self.assertRaises(ValueError):
                resolve_contract(root)

    def test_flat_manifest_rejects_missing_key(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-missing-") as td:
            root = Path(td)
            write_manifest(root)
            manifest = (root / "quillframe.toml").read_text(encoding="utf-8")
            (root / "quillframe.toml").write_text(
                manifest.replace('language = "en"\n', ""),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                resolve_contract(root)

    def test_flat_manifest_rejects_nested_v1_tables(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-nested-") as td:
            root = Path(td)
            (root / "quillframe.toml").write_text(
                '[quillframe]\nschema = "quillframe_project_v1"\n'
                '[project]\nid = "PROJECT-TEST"\ntitle = "Fixture"\n'
                'language = "en"\nchapter_scope = "CH001"\n',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                resolve_contract(root)

    def test_flat_manifest_rejects_old_schema_and_legacy_scope(self):
        for overrides in (
            {"schema": "quillframe_project_v1"},
            {"chapter_scope": "CH002"},
        ):
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory(prefix="qf-contract-old-") as td:
                root = Path(td)
                write_manifest(root, **overrides)

                with self.assertRaises(ValueError):
                    resolve_contract(root)

    def test_project_id_validator_rejects_path_dot_whitespace_and_control_values(self):
        invalid_ids = (".", "..", "A/B", "A\\B", "A B", "A\nB", "A\tB", "", "é", "A" * 65)
        for invalid_id in invalid_ids:
            with self.subTest(invalid_id=repr(invalid_id)), tempfile.TemporaryDirectory(prefix="qf-contract-id-") as td:
                root = Path(td)
                write_manifest(root, id=invalid_id)

                with self.assertRaises(ValueError):
                    resolve_contract(root)
                with self.assertRaises(ValueError):
                    QuillframeStore(root / ".quillframe" / "data").location(invalid_id)

    def test_project_id_grammar_is_identical_across_manifest_and_persistence(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-id-agreement-") as td:
            root = Path(td)
            write_manifest(root, id="a..b")
            context = resolve_contract(root)
            data = root / ".quillframe" / "data"
            store = QuillframeStore(data)

            location = store.create_project(context["project_id"], context["project_title"], context["language"])

            self.assertEqual(location.project_id, "a..b")
            self.assertEqual(location.directory, data / "projects" / "a..b")
            with store.open_project("a..b") as conn:
                self.assertEqual(conn.execute("SELECT project_id FROM project_identity").fetchone()[0], "a..b")

    def test_new_rejects_existing_manifest_or_nonempty_directory_without_writes(self):
        for existing_kind in ("manifest", "nonempty"):
            with self.subTest(existing_kind=existing_kind), tempfile.TemporaryDirectory(prefix="qf-contract-new-existing-") as td:
                root = Path(td) / "novel"
                root.mkdir()
                if existing_kind == "manifest":
                    write_manifest(root, id="OLD", title="Old", language="en")
                else:
                    (root / "old.txt").write_bytes(b"old")
                data = root / ".quillframe" / "data"
                data.mkdir(parents=True)
                database = data / "projects" / "OLD" / "project.sqlite"
                database.parent.mkdir(parents=True)
                database.write_bytes(b"sqlite-before")
                before = {
                    path.relative_to(root).as_posix(): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                }

                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="NEW",
                        title="New",
                        language="zh-CN",
                        port=0,
                        no_browser=True,
                        serve=False,
                    )

                self.assertEqual(rejected.exception.code, "project_directory_not_empty")
                after = {
                    path.relative_to(root).as_posix(): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)

    def test_new_rejects_control_or_whitespace_id_before_directory_creation(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-new-id-") as td:
            root = Path(td) / "novel"
            with self.assertRaises(LaunchError) as rejected:
                launch_project(
                    project=root,
                    new=True,
                    profile="cloud",
                    project_id="A\nB",
                    title="New",
                    language="en",
                    port=0,
                    no_browser=True,
                    serve=False,
                )
            self.assertEqual(rejected.exception.code, "invalid_launch_args")
            self.assertFalse(root.exists())

    def test_concurrent_new_has_one_winner_and_no_loser_partial_project(self):
        for attempt in range(50):
            with self.subTest(attempt=attempt), tempfile.TemporaryDirectory(prefix="qf-contract-race-") as td:
                root = Path(td) / "novel"
                barrier = threading.Barrier(2)

                def worker(project_id: str):
                    barrier.wait()
                    try:
                        product = launch_project(
                            project=root,
                            new=True,
                            profile="cloud",
                            project_id=project_id,
                            title=project_id,
                            language="en",
                            port=0,
                            no_browser=True,
                            serve=False,
                        )
                        product.close()
                        return "success", project_id
                    except LaunchError as exc:
                        return exc.code, project_id

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(worker, ("RACE-A", "RACE-B")))

                self.assertEqual(sum(result[0] == "success" for result in results), 1, results)
                self.assertEqual(sum(result[0] == "project_directory_not_empty" for result in results), 1, results)
                context = resolve_contract(root)
                self.assertIn(context["project_id"], {"RACE-A", "RACE-B"})
                self.assertFalse((root / ".quillframe-new.lock").exists())
                self.assertEqual(
                    len(list((root / ".quillframe" / "data").rglob("project.sqlite"))),
                    1,
                )

    def test_existing_project_database_identity_is_read_only_checked_before_writes(self):
        cases = (
            ("wrong-id", "TARGET", "Stored", "en"),
            ("wrong-title", "SOURCE", "Different", "en"),
            ("wrong-language", "SOURCE", "Stored", "zh-CN"),
        )
        for case, manifest_id, manifest_title, manifest_language in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="qf-contract-db-identity-") as td:
                base = Path(td)
                source_root = base / "source"
                source_data = source_root / ".quillframe" / "data"
                QuillframeStore(source_data).create_project("SOURCE", "Stored", "en")
                source_db = source_data / "projects" / "SOURCE" / "project.sqlite"

                target = base / "target"
                target.mkdir()
                write_manifest(target, id=manifest_id, title=manifest_title, language=manifest_language)
                target_db = target / ".quillframe" / "data" / "projects" / manifest_id / "project.sqlite"
                target_db.parent.mkdir(parents=True)
                shutil.copy2(source_db, target_db)
                before = {
                    path.relative_to(target).as_posix(): path.read_bytes()
                    for path in target.rglob("*")
                    if path.is_file()
                }

                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=target,
                        new=False,
                        profile="cloud",
                        project_id=None,
                        title=None,
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

                self.assertEqual(rejected.exception.code, "project_state_identity_mismatch")
                after = {
                    path.relative_to(target).as_posix(): path.read_bytes()
                    for path in target.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)

    def test_existing_seeded_project_launches_without_business_mutation(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-existing-valid-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            create_existing_with_ch001(data, "P", "Title", "en")
            before = business_rows(data, "P")

            launched = launch_project(
                project=root,
                new=False,
                profile="cloud",
                project_id=None,
                title=None,
                language="en",
                port=0,
                no_browser=True,
                serve=False,
                interactive=False,
            )
            launched.close()

            self.assertEqual(business_rows(data, "P"), before)

    def test_existing_identity_recheck_is_transaction_bound_and_apply_schema_free(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-toctou-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            create_existing_with_ch001(data, "P", "Title", "en")

            def mutate_identity(conn):
                conn.execute("UPDATE project_identity SET title='EVIL'")

            with patch.object(launch_module, "_after_existing_identity_check", side_effect=mutate_identity), \
                patch("persistence.quillframe_sqlite.apply_schema", side_effect=AssertionError("existing path applied schema")):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=False,
                        profile="cloud",
                        project_id=None,
                        title=None,
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_state_identity_mismatch")
            with QuillframeStore(data, read_only=True).open_project("P") as conn:
                identity = conn.execute("SELECT project_id,title,language FROM project_identity").fetchone()
                self.assertEqual(tuple(identity), ("P", "Title", "en"))
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM story_nodes").fetchone()[0], 1)

    def test_project_database_symlink_is_rejected_before_external_bytes_change(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-db-symlink-") as td:
            base = Path(td)
            external_data = base / "external" / ".quillframe" / "data"
            create_existing_with_ch001(external_data, "P", "Title", "en")
            external_db = external_data / "projects" / "P" / "project.sqlite"
            external_before = external_db.read_bytes()

            root = base / "target"
            root.mkdir()
            write_manifest(root, id="P", title="Title", language="en")
            target_db = root / ".quillframe" / "data" / "projects" / "P" / "project.sqlite"
            target_db.parent.mkdir(parents=True)
            target_db.symlink_to(external_db)

            with self.assertRaises(LaunchError) as rejected:
                launch_project(
                    project=root,
                    new=False,
                    profile="cloud",
                    project_id=None,
                    title=None,
                    language="en",
                    port=0,
                    no_browser=True,
                    serve=False,
                    interactive=False,
                )

            self.assertEqual(rejected.exception.code, "project_state_path_invalid")
            self.assertEqual(external_db.read_bytes(), external_before)
            with QuillframeStore(external_data, read_only=True).open_project("P") as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)

    def test_partial_manifest_failure_cleans_target_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-partial-manifest-") as td:
            root = Path(td) / "novel"

            original_fsync = launch_module.os.fsync
            fsync_calls = 0

            def fail_manifest_fsync(fd):
                nonlocal fsync_calls
                fsync_calls += 1
                if fsync_calls == 2:  # reservation first, manifest temp second
                    raise OSError("injected manifest write failure")
                return original_fsync(fd)

            with patch.object(launch_module.os, "fsync", side_effect=fail_manifest_fsync):
                with self.assertRaises(OSError):
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                    )

            self.assertFalse((root / "quillframe.toml").exists())
            self.assertFalse((root / launch_module.NEW_RESERVATION_NAME).exists())
            self.assertFalse(root.exists())
            launched = launch_project(
                project=root,
                new=True,
                profile="cloud",
                project_id="P",
                title="Title",
                language="en",
                port=0,
                no_browser=True,
                serve=False,
            )
            launched.close()

    def test_reservation_open_failure_cleans_only_our_empty_root(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-reservation-failure-") as td:
            root = Path(td) / "novel"
            original_open = launch_module.os.open

            def fail_lock(path, flags, mode=0o777, *args):
                if str(path).endswith(launch_module.NEW_RESERVATION_NAME):
                    raise OSError("injected reservation failure")
                return original_open(path, flags, mode, *args)

            with patch.object(launch_module.os, "open", side_effect=fail_lock):
                with self.assertRaises(OSError):
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                    )

            self.assertFalse(root.exists())

    def test_manifest_competitor_is_preserved_when_publication_fails(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-manifest-owner-") as td:
            root = Path(td) / "novel"
            competitor = (
                'schema = "quillframe_project_v1_0"\n'
                'id = "COMPETITOR"\n'
                'title = "Competitor"\n'
                'language = "en"\n'
            ).encode("utf-8")

            def competitor_then_fail(path, content):
                path.write_bytes(competitor)
                raise OSError("injected publication failure")

            with patch.object(launch_module, "_write_new_manifest", side_effect=competitor_then_fail):
                with self.assertRaises(OSError):
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                    )

            manifest_path = root / "quillframe.toml"
            self.assertEqual(manifest_path.read_bytes(), competitor)
            self.assertTrue(root.exists())
            self.assertFalse((root / launch_module.NEW_RESERVATION_NAME).exists())

    def test_competitor_reservation_replacement_is_preserved_on_failure(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-lock-owner-") as td:
            root = Path(td) / "novel"
            lock_path = root / launch_module.NEW_RESERVATION_NAME
            competitor = b"competitor-lock\n"

            def replace_lock_then_fail(_fd):
                lock_path.unlink()
                lock_path.write_bytes(competitor)
                raise OSError("injected reservation close failure")

            with patch.object(launch_module.os, "fsync", side_effect=replace_lock_then_fail):
                with self.assertRaises(OSError):
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                    )

            self.assertEqual(lock_path.read_bytes(), competitor)
            self.assertTrue(root.exists())

    def test_database_swap_after_safety_check_rejects_external_target(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-db-swap-") as td:
            base = Path(td)
            external_data = base / "external" / ".quillframe" / "data"
            create_existing_with_ch001(external_data, "P", "Title", "en")
            external_db = external_data / "projects" / "P" / "project.sqlite"
            external_before = external_db.read_bytes()

            root = base / "target"
            root.mkdir()
            write_manifest(root, id="P", title="Title", language="en")
            target_db = root / ".quillframe" / "data" / "projects" / "P" / "project.sqlite"
            target_db.parent.mkdir(parents=True)
            shutil.copy2(external_db, target_db)
            original_check = launch_module._assert_safe_project_database_path

            def check_then_swap(data, database):
                result = original_check(data, database)
                target_db.unlink()
                target_db.symlink_to(external_db)
                return result

            with patch.object(launch_module, "_assert_safe_project_database_path", side_effect=check_then_swap):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=False,
                        profile="cloud",
                        project_id=None,
                        title=None,
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_state_path_invalid")
            self.assertEqual(external_db.read_bytes(), external_before)
            with QuillframeStore(external_data, read_only=True).open_project("P") as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)

    def test_manifest_replacement_between_parse_and_core_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-manifest-race-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            create_existing_with_ch001(data, "P", "Title", "en")
            before = business_rows(data, "P")
            original_ensure = launch_module._ensure_local_core

            def replace_then_ensure(project_root, context, **kwargs):
                write_manifest(project_root, id="P", title="EVIL", language="en")
                return original_ensure(project_root, context, **kwargs)

            with patch.object(launch_module, "_ensure_local_core", side_effect=replace_then_ensure):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=False,
                        profile="cloud",
                        project_id=None,
                        title=None,
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_manifest_changed")
            with QuillframeStore(data, read_only=True).open_project("P") as conn:
                identity = conn.execute("SELECT project_id,title,language FROM project_identity").fetchone()
                self.assertEqual(tuple(identity), ("P", "Title", "en"))
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)

    def test_same_value_manifest_replacement_with_different_raw_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-manifest-raw-identity-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            create_existing_with_ch001(data, "P", "Title", "en")
            before = business_rows(data, "P")

            def rewrite_same_values(project_root, _context):
                (project_root / "quillframe.toml").write_text(
                    'language = "en"\n'
                    'title = "Title"\nid = "P"\nschema = "quillframe_project_v1_0"\n',
                    encoding="utf-8",
                )

            with patch.object(launch_module, "_before_ensure_local_core", side_effect=rewrite_same_values):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=False,
                        profile="cloud",
                        project_id=None,
                        title=None,
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_manifest_changed")
            self.assertEqual(business_rows(data, "P"), before)

    def test_manifest_replacement_after_existing_precommit_check_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-manifest-commit-race-existing-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            create_existing_with_ch001(data, "P", "Title", "en")
            before = business_rows(data, "P")

            def replace_after_last_check():
                write_manifest(root, id="P", title="EVIL", language="en")

            with patch.object(launch_module, "_before_existing_commit", side_effect=lambda _conn: replace_after_last_check()):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=False,
                        profile="cloud",
                        project_id=None,
                        title=None,
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_manifest_changed")
            self.assertIn('title = "EVIL"', (root / "quillframe.toml").read_text(encoding="utf-8"))
            self.assertEqual(business_rows(data, "P"), before)

    def test_existing_project_without_canonical_ch001_is_rejected_without_repair(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-existing-missing-seed-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            QuillframeStore(data).create_project("P", "Title", "en")

            with self.assertRaises(LaunchError) as rejected:
                launch_project(
                    project=root,
                    new=False,
                    profile="cloud",
                    project_id=None,
                    title=None,
                    language="en",
                    port=0,
                    no_browser=True,
                    serve=False,
                    interactive=False,
                )

            self.assertEqual(rejected.exception.code, "project_state_invalid")
            with QuillframeStore(data, read_only=True).open_project("P") as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM story_nodes").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 0)

    def test_manifest_replacement_after_new_precommit_check_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-manifest-commit-race-new-") as td:
            root = Path(td) / "novel"

            def replace_after_last_check():
                write_manifest(root, id="P", title="EVIL", language="en")

            with patch.object(launch_module, "_before_new_commit", side_effect=lambda _conn: replace_after_last_check()):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_manifest_changed")
            self.assertIn('title = "EVIL"', (root / "quillframe.toml").read_text(encoding="utf-8"))
            self.assertFalse((root / ".quillframe" / "data" / "projects").exists())

    def test_new_reservation_replacement_after_final_check_is_rejected_and_competitor_survives(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-reservation-commit-race-") as td:
            root = Path(td) / "novel"
            lock_path = root / launch_module.NEW_RESERVATION_NAME
            competitor = b"competitor-reservation\n"

            def replace_after_last_check(_conn):
                lock_path.unlink()
                lock_path.write_bytes(competitor)
                write_manifest(root, id="P", title="COMPETITOR", language="en")

            with patch.object(launch_module, "_before_new_commit", side_effect=replace_after_last_check):
                with self.assertRaises(LaunchError) as rejected:
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(rejected.exception.code, "project_reservation_lost")
            self.assertEqual(lock_path.read_bytes(), competitor)
            self.assertTrue((root / "quillframe.toml").exists())
            self.assertFalse((root / ".quillframe").exists())

    def test_new_reservation_replacement_with_reused_inode_token_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-reservation-inode-reuse-") as td:
            root = Path(td) / "novel"
            lock_path = root / launch_module.NEW_RESERVATION_NAME
            competitor = b"competitor-reused-reservation\n"
            original_lstat_token = launch_module._lstat_token
            reservation_token = None
            replacement_complete = False

            def emulate_reused_token(path):
                nonlocal reservation_token
                current = original_lstat_token(path)
                if Path(path) == lock_path:
                    if reservation_token is None:
                        reservation_token = current
                    elif replacement_complete:
                        return reservation_token
                return current

            def replace_after_last_check(_conn):
                nonlocal replacement_complete
                lock_path.unlink()
                lock_path.write_bytes(competitor)
                write_manifest(root, id="P", title="COMPETITOR", language="en")
                replacement_complete = True

            with patch.object(launch_module, "_lstat_token", side_effect=emulate_reused_token):
                with patch.object(launch_module, "_before_new_commit", side_effect=replace_after_last_check):
                    with self.assertRaises(LaunchError) as rejected:
                        launch_project(
                            project=root,
                            new=True,
                            profile="cloud",
                            project_id="P",
                            title="Title",
                            language="en",
                            port=0,
                            no_browser=True,
                            serve=False,
                            interactive=False,
                        )

            self.assertEqual(rejected.exception.code, "project_reservation_lost")
            self.assertEqual(lock_path.read_bytes(), competitor)
            self.assertIn('title = "COMPETITOR"', (root / "quillframe.toml").read_text(encoding="utf-8"))
            self.assertFalse((root / ".quillframe").exists())

    def test_new_core_failure_cleans_owned_state_but_preserves_competitor(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-core-failure-cleanup-") as td:
            root = Path(td) / "novel"
            competitor = root / "competitor.txt"
            original_create = launch_module.QuillframeStore.create_native_project

            def create_then_fail(store, project_id, title, language, **kwargs):
                result = original_create(store, project_id, title, language, **kwargs)
                competitor.write_bytes(b"competitor")
                raise OSError("injected failure after core initialization")

            with patch.object(launch_module.QuillframeStore, "create_native_project", new=create_then_fail):
                with self.assertRaises(LaunchError):
                    launch_project(
                        project=root,
                        new=True,
                        profile="cloud",
                        project_id="P",
                        title="Title",
                        language="en",
                        port=0,
                        no_browser=True,
                        serve=False,
                        interactive=False,
                    )

            self.assertEqual(competitor.read_bytes(), b"competitor")
            self.assertFalse((root / "quillframe.toml").exists())
            self.assertFalse((root / ".quillframe" / "data" / "projects").exists())
            self.assertFalse((root / ".quillframe").exists())

    def test_existing_database_fails_closed_without_descriptor_capabilities(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-db-capability-") as td:
            root = Path(td)
            write_manifest(root, id="P", title="Title", language="en")
            data = root / ".quillframe" / "data"
            create_existing_with_ch001(data, "P", "Title", "en")

            original_open = launch_module.os.open
            database = data / "projects" / "P" / "project.sqlite"

            def reject_database_open(path, *args):
                if Path(path) == database:
                    raise AssertionError("ordinary path open")
                return original_open(path, *args)

            original_is_dir = Path.is_dir

            def procfs_missing(path):
                if path == Path("/proc/self/fd"):
                    return False
                return original_is_dir(path)

            capability_patches = (
                patch.object(launch_module.os, "O_NOFOLLOW", None, create=True),
                patch.object(launch_module.os, "O_CLOEXEC", None, create=True),
                patch.object(Path, "is_dir", new=procfs_missing),
            )
            for capability_patch in capability_patches:
                with self.subTest(capability=repr(capability_patch)):
                    with capability_patch, patch.object(launch_module.os, "open", side_effect=reject_database_open):
                        with self.assertRaises(LaunchError) as rejected:
                            launch_project(
                                project=root,
                                new=False,
                                profile="cloud",
                                project_id=None,
                                title=None,
                                language="en",
                                port=0,
                                no_browser=True,
                                serve=False,
                                interactive=False,
                            )
                    self.assertEqual(rejected.exception.code, "project_state_path_invalid")

    def test_flat_manifest_rejects_lock_or_attestation_metadata(self):
        for name in ("quillframe.lock.json", "framework.attestation.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="qf-contract-legacy-") as td:
                root = Path(td)
                write_manifest(root)
                (root / name).write_text("{}\n", encoding="utf-8")

                with self.assertRaises(ValueError):
                    resolve_contract(root)

    def test_rejection_happens_before_data_boundary_is_modified(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-before-data-") as td:
            root = Path(td)
            write_manifest(root)
            data = root / ".quillframe" / "data"
            data.mkdir(parents=True)
            marker = data / "marker"
            marker.write_bytes(b"unchanged")
            (root / "framework.attestation.json").write_text("{}\n", encoding="utf-8")

            with self.assertRaises(LaunchError) as rejected:
                launch_project(
                    project=root,
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

            self.assertEqual(rejected.exception.code, "project_legacy_metadata_rejected")
            self.assertEqual(marker.read_bytes(), b"unchanged")
            self.assertFalse((data / "projects").exists())

    def test_launch_and_bootstrap_use_the_same_resolver(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-bootstrap-") as td:
            root = Path(td) / "novel"
            launched = launch_project(
                project=root,
                new=True,
                profile="cloud",
                project_id="PROJECT-TEST",
                title="Fixture",
                language="en",
                port=0,
                no_browser=True,
                serve=False,
            )
            try:
                context = resolve_contract(root)
                process = subprocess.run(
                    [sys.executable, "quillframe.py", "bootstrap", "--project-root", str(root), "--task-mode", "PLAN-CHAPTER"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                projection = json.loads(process.stdout)
            finally:
                launched.close()

            self.assertEqual(process.returncode, 0)
            self.assertTrue(projection["ready"])
            self.assertEqual(projection["project_id"], context["manifest"]["id"])
            self.assertEqual(Path(projection["data_root"]), Path(context["data_root"]))
            self.assertNotIn("framework_lock", projection)
            self.assertNotIn("project_layout", projection)
            self.assertFalse((root / "dist" / "project.bundle.json").exists())

    def test_launch_created_project_resolves_and_reaches_settlement(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-settle-") as td:
            root = Path(td) / "novel"
            launched = launch_project(
                project=root,
                new=True,
                profile="cloud",
                project_id="PROJECT-TEST",
                title="Fixture",
                language="en",
                port=0,
                no_browser=True,
                serve=False,
            )
            try:
                target = root / "state" / "canon" / "TEST.json"
                target.parent.mkdir(parents=True)
                target.write_text('{"value":"before"}\n', encoding="utf-8")
                before = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
                intent = {
                    "schema": TX_SCHEMA,
                    "tx_id": "SETTLE-SLICE-A",
                    "project_id": "PROJECT-TEST",
                    "accepted_artifact": {"ref": "manuscripts/accepted/CH001.md", "fingerprint": "sha256:" + "a" * 64},
                    "acceptance": {"status": "accepted", "actor": "user", "evidence_ref": "session:acceptance"},
                    "checkpoint_ref": "checkpoint:before-settle",
                    "write_authorization_ref": "authorization:settle",
                    "writes": [{
                        "path": "state/canon/TEST.json",
                        "operation": "update",
                        "before_fingerprint": before,
                        "after_text": '{"value":"after"}\n',
                    }],
                    "projections": [],
                }
                conn = connect(Path(td) / "settlement.db")
                try:
                    prepared = prepare(conn, root, intent)
                    applied = apply_authority(conn, prepared["tx_id"])
                finally:
                    conn.close()
            finally:
                launched.close()

            self.assertEqual(applied["status"], "authority_applied")
            self.assertEqual(target.read_text(encoding="utf-8"), '{"value":"after"}\n')

    def test_flat_project_policy_loads_from_fixed_state_path(self):
        policy = {
            "schema": "quillframe_property_write_policy_v1",
            "default": {"mutation_class": "proposal_only"},
            "object_types": {},
        }
        with tempfile.TemporaryDirectory(prefix="qf-contract-policy-") as td:
            root = Path(td)
            write_manifest(root)
            policy_path = root / "state" / "property-write-policy.json"
            policy_path.parent.mkdir()
            policy_path.write_text(json.dumps(policy), encoding="utf-8")

            loaded = policy_from_project(root)

            self.assertEqual(loaded["schema"], "quillframe_property_write_policy_v1")
            self.assertEqual(Path(loaded["policy_ref"]), policy_path)

    def test_missing_policy_fails_closed_and_unsafe_policy_paths_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qf-contract-policy-safe-") as td:
            root = Path(td)
            write_manifest(root)
            self.assertIsNone(policy_from_project(root))

            policy_path = root / "state" / "property-write-policy.json"
            policy_path.parent.mkdir()
            outside = Path(td) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            os.symlink(outside, policy_path)
            with self.assertRaises(ValueError):
                policy_from_project(root)


class NativeNovelStorageTests(unittest.TestCase):
    def test_native_create_never_follows_a_registry_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "store"
            root.mkdir()
            outside = Path(td) / "outside.sqlite"
            sentinel = b"do not touch this file"
            outside.write_bytes(sentinel)
            (root / "quillframe.sqlite").symlink_to(outside)
            with self.assertRaises(OSError):
                QuillframeStore(root).create_native_project("P", "Novel")
            self.assertEqual(outside.read_bytes(), sentinel)
            self.assertFalse((root / "projects" / "P").exists())

    def test_open_rejects_incomplete_schema_without_recreating_missing_tables(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_manifest(root, id="P", title="Novel", language="en")
            store = QuillframeStore(root / ".quillframe" / "data")
            loc = store.create_native_project("P", "Novel", "en")
            with store.open_project("P") as conn:
                conn.execute("DROP TABLE publication_collection_requests")
                conn.commit()
            with self.assertRaises(LaunchError) as rejected:
                launch_project(project=root, new=False, profile="cloud", project_id=None, title=None, language="en", port=0, no_browser=True, serve=False, interactive=False)
            self.assertEqual(rejected.exception.code, "project_state_invalid")
            conn = sqlite3.connect(loc.database)
            try:
                self.assertIsNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='publication_collection_requests'").fetchone())
            finally:
                conn.close()

    def test_native_create_is_exclusive_and_seed_is_atomic(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            observed = []

            def inspect(conn):
                observed.append((conn.in_transaction, conn.execute("SELECT COUNT(*) FROM project_identity").fetchone()[0], conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]))

            store.create_native_project("P", "First", "zh-CN", before_commit=inspect)
            self.assertEqual(observed, [(True, 1, 1)])
            before = business_rows(Path(td), "P")
            with self.assertRaises(FileExistsError):
                store.create_native_project("P", "Overwritten", "en")
            self.assertEqual(business_rows(Path(td), "P"), before)
            with store.open_project("P") as conn:
                self.assertEqual(tuple(conn.execute("SELECT title,language FROM project_identity").fetchone()), ("First", "zh-CN"))

    def test_failed_native_seed_rolls_back_identity_and_manuscript(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))

            def fail(_conn):
                raise RuntimeError("before commit")

            with self.assertRaisesRegex(RuntimeError, "before commit"):
                store.create_native_project("P", "Fixture", before_commit=fail)
            with store.open_project("P") as conn:
                for table in ("project_identity", "story_nodes", "documents"):
                    self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
            self.assertEqual(store.list_projects(), [])
            # An incomplete creation is preserved and cannot become an upsert.
            with self.assertRaises(FileExistsError):
                store.create_native_project("P", "Retry")

    def test_open_accepts_current_multichapter_titles_and_never_reseeds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_manifest(root, id="P", title="Novel", language="en")
            data = root / ".quillframe" / "data"
            store = QuillframeStore(data)
            store.create_native_project("P", "Novel", "en")
            with store.open_project("P") as conn:
                conn.execute("UPDATE story_nodes SET title='A revised chapter title',metadata_json='{}' WHERE node_id='CH001'")
                conn.execute("UPDATE documents SET title='Chapter one' WHERE document_id='DOC-CH001'")
                conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH002','chapter',2,'Next','{}')")
                conn.execute("INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES('DOC-CH002','CH002','manuscript','Next','2026-01-01T00:00:00+00:00')")
                conn.commit()
            before = business_rows(data, "P")
            product = launch_project(project=root, new=False, profile="cloud", project_id=None, title=None, language="en", port=0, no_browser=True, serve=False, interactive=False)
            product.close()
            self.assertEqual(business_rows(data, "P"), before)
            bundle = store.backup_project("P")
            self.assertTrue(store.verify_backup(bundle)["valid"])
            restored = QuillframeStore(Path(td) / "restored")
            restored.restore_project(bundle)
            self.assertEqual(business_rows(restored.root, "P"), before)

    def test_manuscript_creation_validates_chapter_and_rolls_back_index_failure(self):
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            store.create_native_project("P", "Novel")
            for target in (None, "missing"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    store.create_document("P", "INVALID", "Invalid", story_node_id=target)
            with store.open_project("P") as conn:
                conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH002','chapter',2,'Next','{}')")
                conn.commit()
            with patch.object(store, "index_search", side_effect=RuntimeError("index failed")):
                with self.assertRaisesRegex(RuntimeError, "index failed"):
                    store.create_document("P", "DOC-CH002", "Next", story_node_id="CH002")
            with store.open_project("P") as conn:
                self.assertIsNone(conn.execute("SELECT 1 FROM documents WHERE document_id='DOC-CH002'").fetchone())


if __name__ == "__main__":
    unittest.main()
