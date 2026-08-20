from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "release"))
import acceptance as a
import run_acceptance as runner


def make_subject(dirty: bool = False, project: str = "quillframe", candidate: str = "CH001") -> dict:
    return {
        "kind": "uncommitted_working_tree" if dirty else "clean_checkout",
        "base_commit": "a" * 40,
        "current_commit": "b" * 40,
        "chapter_scope": "CH001",
        "version": a.VERSION,
        "dirty": dirty,
        "working_tree_fingerprint": "c" * 64,
        "build_fingerprint": "d" * 64,
        "untracked_paths": [],
        "project_id": project,
        "candidate_id": candidate,
    }


def write_bytes(root: Path, name: str, data: bytes = b"artifact") -> dict:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "role": "test"}


def command_record(gate_id: str, subject: dict, root: Path, result: str = "pass") -> dict:
    spec = a.GATES[gate_id]
    artifact = write_bytes(root, f"artifacts/{gate_id.replace('.', '_')}.txt")
    return {
        "id": f"record-{gate_id}",
        "gate_id": gate_id,
        "subject": subject,
        "subject_after": subject,
        "started_at": "2026-08-20T00:00:00Z",
        "finished_at": "2026-08-20T00:00:01Z",
        "result": result,
        "artifacts": [artifact] if result == "pass" else [],
        "argv": list(spec.argv),
        "cwd": spec.cwd,
        "timeout_ms": spec.timeout_ms,
        "exit_code": 0 if result == "pass" else 1,
        "predicate": spec.predicate,
    }


def base_evidence(root: Path, subject: dict | None = None) -> dict:
    value = {
        "schema": a.EVIDENCE_SCHEMA,
        "framework_version": a.VERSION,
        "generated_at": "2026-08-20T00:00:00Z",
        "acceptance_subject": subject or make_subject(),
        "evidence_fingerprint": "0" * 64,
        "commands": [],
        "browser_manifests": [],
        "external_evidence": [],
        "environment_limited_checks": [],
    }
    value["evidence_fingerprint"] = a.evidence_fingerprint(value)
    return value


class ContractShapeTests(unittest.TestCase):
    def test_task_requirements_cover_exact_canonical_ids(self):
        self.assertEqual(tuple(a.TASK_REQUIREMENTS), a.CANONICAL_TASK_IDS)
        self.assertEqual(len(a.TASK_REQUIREMENTS), 57)

    def test_task_requirements_are_semantically_named(self):
        self.assertTrue(all("." in gate for gates in a.TASK_REQUIREMENTS.values() for gate in gates))
        self.assertNotIn("source_status", a.TASK_REQUIREMENTS)

    def test_unrelated_tasks_do_not_share_unittest_only_gate(self):
        self.assertNotEqual(a.TASK_REQUIREMENTS["T102"], a.TASK_REQUIREMENTS["T200"])

    def test_all_required_gate_ids_are_generator_owned(self):
        self.assertTrue(all(gate in a.GATES for values in a.TASK_REQUIREMENTS.values() for gate in values if gate not in a.DERIVED_GATES))

    def test_local_browser_evidence_has_one_canonical_gate_without_aliases(self):
        self.assertNotIn("G3.browser_local", a.GATES)
        self.assertNotIn("G3.local_browser", a.GATES)
        self.assertNotIn("G3.local_browser.invoke", a.GATES)
        self.assertIn("T310.browser.local", a.TASK_REQUIREMENTS["T603"])

    def test_report_top_level_is_exact_canonical_set(self):
        self.assertEqual(a.REPORT_KEYS, {"schema", "framework_version", "generated_at", "acceptance_subject", "evidence_fingerprint", "status", "release_promotion_authorized", "deployment_performed", "model_execution_performed", "gates", "local_evidence", "blocking_evidence", "environment_limited_checks", "task_ledger", "rendered_artifacts"})

    def test_schema_versions_remain_native_v1(self):
        self.assertEqual(a.REPORT_SCHEMA, "quillframe_release_acceptance_report_v1")
        self.assertEqual(a.EVIDENCE_SCHEMA, "quillframe_acceptance_evidence_v1")

    def test_parse_rejects_duplicate_keys(self):
        self.assertRaises(a.AcceptanceError, a.parse_json, '{"x": 1, "x": 2}')

    def test_parse_rejects_nonfinite_numbers(self):
        self.assertRaises(a.AcceptanceError, a.parse_json, '{"x": NaN}')

    def test_subject_requires_ch001(self):
        subject = make_subject()
        subject["chapter_scope"] = "CH002"
        self.assertRaises(a.AcceptanceError, a.validate_subject, subject)

    def test_subject_requires_complete_fingerprint_fields(self):
        subject = make_subject()
        del subject["untracked_paths"]
        self.assertRaises(a.AcceptanceError, a.validate_subject, subject)

    def test_subject_rejects_wrong_fingerprint_length(self):
        subject = make_subject()
        subject["working_tree_fingerprint"] = "x"
        self.assertRaises(a.AcceptanceError, a.validate_subject, subject)

    def test_subject_rejects_nonboolean_dirty(self):
        subject = make_subject()
        subject["dirty"] = "false"
        self.assertRaises(a.AcceptanceError, a.validate_subject, subject)

    def test_environment_record_has_exact_shape(self):
        evidence = base_evidence(Path("/tmp"))
        evidence["environment_limited_checks"].append({"id": "cargo", "status": "not_run", "reason": "missing", "owner": "CI"})
        evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
        a.validate_evidence(evidence, Path("/tmp"))

    def test_environment_record_rejects_extra_key(self):
        evidence = base_evidence(Path("/tmp"))
        evidence["environment_limited_checks"].append({"id": "cargo", "status": "not_run", "reason": "missing", "owner": "CI", "extra": 1})
        evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
        self.assertRaises(a.AcceptanceError, a.validate_evidence, evidence, Path("/tmp"))


class SubjectDerivationTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> str:
        result = subprocess.run(("git", *args), cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()

    def _repo(self, root: Path) -> tuple[Path, list[Path]]:
        repo = root / "repo"
        repo.mkdir()
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "acceptance@example.invalid")
        self._git(repo, "config", "user.name", "Acceptance Fixture")
        (repo / "VERSION").write_text(a.VERSION + "\n")
        (repo / "source.txt").write_text("source\n")
        self._git(repo, "add", "VERSION", "source.txt")
        self._git(repo, "commit", "-q", "-m", "source")
        output_dir = repo / "release" / "acceptance"
        output_dir.mkdir(parents=True)
        outputs = []
        for name in sorted(a.CANONICAL_OUTPUT_NAMES):
            path = output_dir / name
            path.write_text(name + "\n")
            outputs.append(path)
        self._git(repo, "add", *(f"release/acceptance/{path.name}" for path in outputs))
        self._git(repo, "commit", "-q", "-m", "acceptance-artifacts")
        return repo, outputs

    def test_exact_five_derived_outputs_are_excluded_from_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, outputs = self._repo(Path(directory))
            normalized = self._git(repo, "rev-parse", "HEAD^")
            subject = a.compute_subject(repo)
            self.assertEqual(subject["current_commit"], normalized)
            self.assertFalse(subject["dirty"])
            baseline = dict(subject)
            outputs[0].write_text("changed output\n")
            self.assertEqual(a.compute_subject(repo), baseline)
            outputs[0].write_text(outputs[0].name + "\n")

    def test_source_change_and_sixth_output_do_not_hide_subject_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, outputs = self._repo(Path(directory))
            baseline = a.compute_subject(repo)
            (repo / "source.txt").write_text("changed source\n")
            changed = a.compute_subject(repo)
            self.assertTrue(changed["dirty"])
            self.assertNotEqual(changed["working_tree_fingerprint"], baseline["working_tree_fingerprint"])
            (repo / "source.txt").write_text("source\n")
            sixth = repo / "release" / "acceptance" / "sixth.md"
            sixth.write_text("not canonical\n")
            with_sixth = a.compute_subject(repo)
            self.assertTrue(with_sixth["dirty"])
            self.assertIn("release/acceptance/sixth.md", with_sixth["untracked_paths"])

    def test_mixed_source_and_output_commit_is_not_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, outputs = self._repo(Path(directory))
            (repo / "source.txt").write_text("mixed source\n")
            for path in outputs:
                path.write_text("mixed output\n")
            self._git(repo, "add", "source.txt", *(f"release/acceptance/{path.name}" for path in outputs))
            self._git(repo, "commit", "-q", "-m", "mixed-change")
            head = self._git(repo, "rev-parse", "HEAD")
            subject = a.compute_subject(repo)
            self.assertEqual(subject["current_commit"], head)
            self.assertNotEqual(subject["current_commit"], self._git(repo, "rev-parse", "HEAD^"))

    def test_python_subject_matches_real_t605_node_git_subject(self):
        node = shutil.which("node")
        script = Path(__file__).resolve().parents[1] / "site" / "scripts" / "browser-acceptance-t605.mjs"
        if node is None:
            self.fail("Node is required for the canonical T605 cross-language contract test")
        if not script.is_file():
            self.fail(f"canonical repo T605 producer is missing: {script}")
        with tempfile.TemporaryDirectory() as directory:
            repo, _outputs = self._repo(Path(directory))
            source = "import { gitSubject } from " + json.dumps(str(script)) + "\nconst value = gitSubject(process.argv[1])\nprocess.stdout.write(JSON.stringify(value))"
            def compare_subjects() -> None:
                result = subprocess.run((node, "--input-type=module", "-e", source, str(repo)), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                node_subject = json.loads(result.stdout)
                python_subject = a.compute_subject(repo)
                self.assertEqual(node_subject, {"commit": python_subject["current_commit"], "dirty": python_subject["dirty"], "working_tree_fingerprint": "sha256:" + python_subject["working_tree_fingerprint"]})

            compare_subjects()
            (repo / "source.txt").unlink()
            compare_subjects()
            (repo / "source.txt").write_text("source restored\n")
            (repo / "ordinary-untracked.txt").write_text("ordinary untracked\n")
            compare_subjects()
            (repo / "source.txt").write_text("modified source\n")
            compare_subjects()

    def test_python_build_input_fingerprint_matches_real_t605_node_exporter(self):
        node = shutil.which("node")
        script = Path(__file__).resolve().parents[1] / "site" / "scripts" / "browser-acceptance-t605.mjs"
        if node is None:
            self.fail("Node is required for the canonical T605 build-input contract test")
        if not script.is_file():
            self.fail(f"canonical repo T605 producer is missing: {script}")
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            self._git(repo, "init", "-q")
            self._git(repo, "config", "user.email", "acceptance@example.invalid")
            self._git(repo, "config", "user.name", "Acceptance Fixture")
            (repo / "VERSION").write_text(a.VERSION + "\n")
            for index, relative in enumerate(a.BUILD_INPUT_RELATIVE):
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"fixture": index, "path": relative}, sort_keys=True) + "\n")
            self._git(repo, "add", "VERSION", *a.BUILD_INPUT_RELATIVE)
            self._git(repo, "commit", "-q", "-m", "build-input-contract")
            commit = self._git(repo, "rev-parse", "HEAD")
            source = "import { acceptanceInputFingerprint } from " + json.dumps(str(script)) + "\nconst value = acceptanceInputFingerprint(process.argv[1], process.argv[2])\nprocess.stdout.write(JSON.stringify(value))"

            def node_fingerprint() -> str:
                result = subprocess.run((node, "--input-type=module", "-e", source, str(repo), commit), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return json.loads(result.stdout)

            python_fingerprint = a.build_input_fingerprint(repo, commit)
            self.assertEqual(node_fingerprint(), "sha256:" + python_fingerprint)
            before = python_fingerprint
            package = repo / "package.json"
            package.write_text('{"fixture":"mutated-package"}\n')
            after = a.build_input_fingerprint(repo, commit)
            self.assertNotEqual(after, before)
            self.assertEqual(node_fingerprint(), "sha256:" + after)

    def test_real_t605_manifest_timestamp_matches_native_seconds_contract(self):
        node = shutil.which("node")
        script = Path(__file__).resolve().parents[1] / "site" / "scripts" / "browser-acceptance-t605.mjs"
        if node is None:
            self.fail("Node is required for the canonical T605 timestamp contract test")
        if not script.is_file():
            self.fail(f"canonical repo T605 producer is missing: {script}")
        with tempfile.TemporaryDirectory() as directory:
            source = "import { writeFailureManifest } from " + json.dumps(str(script)) + "\nwriteFailureManifest({ evidenceRoot: process.argv[1], code: 'CONTRACT_PROBE' })"
            subprocess.run((node, "--input-type=module", "-e", source, directory), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            manifest = json.loads((Path(directory) / "browser-acceptance-v1.json").read_text())
            a._timestamp(manifest["generated_at"])


class ArtifactBoundaryTests(unittest.TestCase):
    def test_descriptor_read_accepts_regular_single_link_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            self.assertEqual(a.read_descriptor(item, root), b"artifact")

    def test_descriptor_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            item["path"] = "/tmp/x.txt"
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_rejects_parent_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            item["path"] = "../x.txt"
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_rejects_final_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "secret"
            target.write_bytes(b"artifact")
            (root / "x").symlink_to(target)
            item = {"path": "x", "size": 8, "sha256": hashlib.sha256(b"artifact").hexdigest(), "role": "test"}
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_rejects_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "secret"
            target.write_bytes(b"artifact")
            (root / "link").symlink_to(Path(outside), target_is_directory=True)
            item = {"path": "link/secret", "size": 8, "sha256": hashlib.sha256(b"artifact").hexdigest(), "role": "test"}
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_rejects_hardlink_nlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.write_bytes(b"artifact")
            os.link(source, root / "x")
            item = {"path": "x", "size": 8, "sha256": hashlib.sha256(b"artifact").hexdigest(), "role": "test"}
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            item["sha256"] = "0" * 64
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_rejects_size_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            item["size"] = 1
            self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_detects_second_read_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            real_pread = os.pread
            calls = [0]

            def mutate(fd: int, size: int, offset: int) -> bytes:
                calls[0] += 1
                data = real_pread(fd, size, offset)
                return b"changed!" if calls[0] == 2 else data

            with mock.patch("os.pread", side_effect=mutate):
                self.assertRaises(a.AcceptanceError, a.read_descriptor, item, root)

    def test_descriptor_detects_same_size_rewrite_after_mtime_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = write_bytes(root, "x.txt")
            path = root / "x.txt"
            real_fstat = os.fstat
            calls = [0]

            def mutate(fd: int) -> os.stat_result:
                calls[0] += 1
                before = real_fstat(fd)
                if calls[0] == 2:
                    path.write_bytes(b"ARTIFACT")
                    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                    return real_fstat(fd)
                return before

            with mock.patch("os.fstat", side_effect=mutate):
                with self.assertRaises(a.AcceptanceError):
                    a.read_descriptor(item, root)

    def test_file_read_detects_same_size_rewrite_after_mtime_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "x.txt"
            path.write_bytes(b"artifact")
            real_fstat = os.fstat
            calls = [0]

            def mutate(fd: int) -> os.stat_result:
                calls[0] += 1
                before = real_fstat(fd)
                if calls[0] == 2:
                    path.write_bytes(b"ARTIFACT")
                    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                    return real_fstat(fd)
                return before

            with mock.patch("os.fstat", side_effect=mutate):
                with self.assertRaises(a.AcceptanceError):
                    a.read_file_bytes(root, "x.txt")

    def test_evidence_file_read_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "evidence.json"
            target.write_text("{}")
            (root / "evidence.json").symlink_to(target)
            self.assertRaises(a.AcceptanceError, a.read_json_descriptor, root, "evidence.json")

    def test_secret_scan_redacts_bearer_and_query(self):
        safe = a.redact_text("Bearer abcdef token=secret-value /home/private/file /opt/private/file")
        self.assertNotIn("abcdef", safe)
        self.assertNotIn("secret-value", safe)
        self.assertNotIn("/home/private/file", safe)
        self.assertNotIn("/opt/private/file", safe)

    def test_secret_scan_rejects_unredactable_secret(self):
        self.assertRaises(a.AcceptanceError, a.safe_text, "-----BEGIN PRIVATE KEY-----")


class GateEvidenceTests(unittest.TestCase):
    def test_command_record_requires_fixed_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["argv"] = ["true"]
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_command_record_requires_fixed_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["cwd"] = "/tmp"
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_command_record_rejects_unknown_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["gate_id"] = "fake.pass"
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_command_record_rejects_extra_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["extra"] = True
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_command_record_rejects_mixed_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["subject"] = make_subject(project="other")
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_command_record_rejects_subject_changed_after_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["subject_after"] = make_subject(dirty=True)
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_command_record_requires_artifact_on_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T102.schema.catalog", subject, root)
            record["artifacts"] = []
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_browser_gate_is_rejected_from_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T605.browser.full", subject, root)
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_local_browser_gate_is_rejected_from_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = command_record("T310.browser.local", subject, root)
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "commands", subject, root)

    def test_duplicate_record_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            evidence = base_evidence(root, subject)
            first = command_record("T102.schema.catalog", subject, root)
            second = command_record("T102.schema.catalog", subject, root)
            second["id"] = first["id"]
            evidence["commands"] = [first, second]
            evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
            self.assertRaises(a.AcceptanceError, a.validate_evidence, evidence, root)

    def test_duplicate_gate_ids_are_rejected_before_a_later_pass_can_mask_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            evidence = base_evidence(root, subject)
            failed = command_record("G6.version_consistency", subject, root, result="failed")
            failed["id"] = "version-consistency-failed"
            passed = command_record("G6.version_consistency", subject, root, result="pass")
            passed["id"] = "version-consistency-pass"
            evidence["commands"] = [failed, passed]
            evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
            self.assertRaises(a.AcceptanceError, a.validate_evidence, evidence, root)
            self.assertRaises(a.AcceptanceError, a.derive_tasks, evidence, False)

    def test_every_t602_gate_failure_blocks_t602_and_distinct_passes_do_not_collide(self):
        requirements = a.TASK_REQUIREMENTS["T602"]
        self.assertEqual(len(requirements), len(set(requirements)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            for failed_gate in requirements:
                evidence = base_evidence(root, subject)
                evidence["commands"] = [
                    command_record(gate_id, subject, root, result="failed" if gate_id == failed_gate else "pass")
                    for gate_id in requirements
                ]
                task = next(item for item in a.derive_tasks(evidence, False) if item["id"] == "T602")
                self.assertEqual(task["status"], "~", failed_gate)
            evidence = base_evidence(root, subject)
            evidence["commands"] = [command_record(gate_id, subject, root) for gate_id in requirements]
            task = next(item for item in a.derive_tasks(evidence, False) if item["id"] == "T602")
            self.assertEqual(task["status"], "x")

    def test_missing_required_task_gate_blocks_task(self):
        evidence = base_evidence(Path("/tmp"))
        tasks = a.derive_tasks(evidence, t608_final=False)
        self.assertEqual(next(item for item in tasks if item["id"] == "T102")["status"], "~")

    def test_source_checkbox_cannot_make_missing_gate_pass(self):
        evidence = base_evidence(Path("/tmp"))
        tasks = a.derive_tasks(evidence, t608_final=False, source_status={"T102": "x"})
        self.assertEqual(next(item for item in tasks if item["id"] == "T102")["status"], "~")

    def test_t608_is_not_x_before_final_readback(self):
        evidence = base_evidence(Path("/tmp"))
        tasks = a.derive_tasks(evidence, t608_final=False)
        self.assertEqual(next(item for item in tasks if item["id"] == "T608")["status"], "~")

    def test_evidence_fingerprint_mismatch_is_rejected(self):
        evidence = base_evidence(Path("/tmp"))
        evidence["evidence_fingerprint"] = "0" * 64
        self.assertRaises(a.AcceptanceError, a.validate_evidence, evidence, Path("/tmp"))


class ExternalBindingTests(unittest.TestCase):
    def external_record(self, gate: str, subject: dict, root: Path, project: str = "quillframe", candidate: str = "CH001", fp: str = "e" * 64, receipt: str = "f" * 64) -> dict:
        target = {"environment": "production", "version": a.VERSION, "project_id": project, "candidate_id": candidate}
        if gate == "T409.external":
            proof = {"kind": "workos_cloudflare_deployment", "deployment_id": "deploy-1", "deployment_receipt_fingerprint": "1" * 64, "credentials_used": True, "deployed": True}
            approval = {"actor": "authorized_human", "status": "verified"}
        elif gate == "T606.external":
            proof = {"kind": "real_ch001_author_chain", "independent_reviewer_id": "reviewer-1", "model_invocation_id": "model-run-1", "model_execution_performed": True, "chain": ["candidate_visible", "accept", "settle", "publish"], "receipt_schema": "quillframe_host_bridge_result_v11", "candidate_artifact_fingerprint": fp, "acceptance_receipt_fingerprint": "2" * 64, "settlement_receipt_fingerprint": "3" * 64, "publication_receipt_fingerprint": "4" * 64}
            approval = {"actor": "authorized_human", "status": "verified"}
        else:
            proof = {"kind": "promotion_approval", "target_identity": target, "approved": True, "depends_on": ["T409.external", "T606.external"]}
            approval = {"actor": "authorized_human", "status": "approved"}
        record = {
            "id": f"external-{gate}",
            "gate_id": gate,
            "subject": subject,
            "subject_after": subject,
            "started_at": "2026-08-20T00:00:00Z",
            "finished_at": "2026-08-20T00:00:01Z",
            "result": "pass",
            "artifacts": [],
            "project_id": project,
            "candidate_id": candidate,
            "candidate_fingerprint": fp,
            "receipt_fingerprint": receipt,
            "target_identity": target,
            "approval": approval,
            "proof": proof,
        }
        payload = {"schema": "quillframe_external_acceptance_proof_v1", "gate_id": gate, "project_id": project, "candidate_id": candidate, "candidate_fingerprint": fp, "receipt_fingerprint": receipt, "target_identity": target, "proof": proof}
        raw = json.dumps(payload, sort_keys=True).encode()
        artifact = write_bytes(root, f"proof/{gate}.json", raw)
        artifact["role"] = "external-proof"
        record["artifacts"] = [artifact]
        return record

    def test_t409_requires_real_deployment_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = self.external_record("T409.external", subject, root)
            record["proof"] = {"kind": "fake"}
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "external_evidence", subject, root)

    def test_t606_requires_real_chain_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = self.external_record("T606.external", subject, root)
            record["proof"] = {"kind": "fake"}
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "external_evidence", subject, root)

    def test_t607_requires_explicit_approval_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            record = self.external_record("T607.approval", subject, root)
            record["proof"] = {"kind": "fake"}
            self.assertRaises(a.AcceptanceError, a.validate_record, record, "external_evidence", subject, root)

    def test_t409_t606_cross_binding_rejects_project_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            t409 = self.external_record("T409.external", subject, root)
            t606 = self.external_record("T606.external", subject, root, project="other")
            self.assertRaises(a.AcceptanceError, a.validate_external_cross_binding, [t409, t606], subject)

    def test_t409_t606_cross_binding_rejects_candidate_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            t409 = self.external_record("T409.external", subject, root)
            t606 = self.external_record("T606.external", subject, root, candidate="CH002")
            self.assertRaises(a.AcceptanceError, a.validate_external_cross_binding, [t409, t606], subject)

    def test_t409_t606_cross_binding_rejects_fingerprint_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            t409 = self.external_record("T409.external", subject, root)
            t606 = self.external_record("T606.external", subject, root, fp="1" * 64)
            self.assertRaises(a.AcceptanceError, a.validate_external_cross_binding, [t409, t606], subject)

    def test_t607_requires_same_target_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            t409 = self.external_record("T409.external", subject, root)
            t606 = self.external_record("T606.external", subject, root)
            t607 = self.external_record("T607.approval", subject, root)
            t607["target_identity"]["project_id"] = "other"
            self.assertRaises(a.AcceptanceError, a.validate_external_cross_binding, [t409, t606, t607], subject)

    def test_external_only_cannot_authorize_with_local_blocks(self):
        evidence = base_evidence(Path("/tmp"))
        self.assertFalse(a.release_ready(evidence, a.derive_tasks(evidence, False), False))

    def test_dirty_subject_cannot_authorize(self):
        evidence = base_evidence(Path("/tmp"), make_subject(dirty=True))
        self.assertFalse(a.release_ready(evidence, a.derive_tasks(evidence, False), False))

    def test_t607_is_derived_gate_not_direct_task_result(self):
        self.assertIn("T607.approval", a.TASK_REQUIREMENTS["T607"])
        self.assertIn("T409.external", a.TASK_REQUIREMENTS["T607"])
        self.assertIn("T606.external", a.TASK_REQUIREMENTS["T607"])


class T605AdapterTests(unittest.TestCase):
    def test_t605_adapter_is_one_central_schema_function(self):
        adapter = a.t605_schema_adapter()
        self.assertEqual(adapter["schema"], "quillframe_browser_acceptance_v1")
        self.assertEqual(adapter["matrix_count"], 40)

    def test_t605_manifest_requires_exact_top_keys(self):
        adapter = a.t605_schema_adapter()
        self.assertEqual(set(adapter["manifest_keys"]), {"artifacts", "artifacts_root", "browser", "build", "chapter_scope", "errors", "gate", "generated_at", "global_checks", "matrix_count", "schema", "status", "subject", "surfaces", "task"})
        self.assertEqual(adapter["build_keys"], {"start_fingerprint", "end_fingerprint", "input_fingerprint", "site_finalizer_fingerprint", "stable"})

    def test_t605_manifest_rejects_wrong_matrix_count(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["matrix_count"] = 39
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_41_matrix_count(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["matrix_count"] = 41
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_wrong_viewport_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["surfaces"][0]["viewports"][0]["id"] = "fake"
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_wrong_mode_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["surfaces"][0]["viewports"][0]["mode"]["id"] = "fake"
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_duplicate_surface(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["surfaces"][1]["surface"] = "site"
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_screenshot_path_spoof(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["surfaces"][0]["viewports"][0]["screenshot"]["path"] = "site/screenshots/fake.png"
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_missing_screenshot_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["artifacts"][0]["sha256"] = "sha256:" + "0" * 64
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_failed_typed_check(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["surfaces"][0]["checks"][0]["status"] = "fail"
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_manifest_rejects_missing_required_check(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = a.synthetic_t605_manifest(make_subject(), Path(directory))
            manifest["surfaces"][0]["viewports"][0]["checks"] = []
            self.assertRaises(a.AcceptanceError, a.validate_t605_manifest, manifest, make_subject(), Path(directory))

    def test_t605_subject_must_be_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(make_subject(), root)
            manifest["subject"]["end"]["commit"] = "f" * 40
            with self.assertRaises(a.AcceptanceError):
                a.validate_t605_manifest(manifest, make_subject(), root)

    def test_t605_build_finalizer_is_typed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(make_subject(), root)
            manifest["build"]["site_finalizer_fingerprint"] = "wrong"
            with self.assertRaises(a.AcceptanceError):
                a.validate_t605_manifest(manifest, make_subject(), root)

    def test_t605_dist_build_and_acceptance_input_fingerprint_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            manifest = a.synthetic_t605_manifest(subject, root)
            manifest["build"]["start_fingerprint"] = "sha256:" + "f" * 64
            manifest["build"]["end_fingerprint"] = "sha256:" + "f" * 64
            a.validate_t605_manifest(manifest, subject, root)
            manifest["build"]["input_fingerprint"] = "sha256:" + "0" * 64
            with self.assertRaises(a.AcceptanceError):
                a.validate_t605_manifest(manifest, subject, root)

    def test_t605_rejects_millisecond_timestamp_until_contract_is_seconds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(make_subject(), root)
            manifest["generated_at"] = "2026-08-20T00:00:00.123Z"
            with self.assertRaises(a.AcceptanceError):
                a.validate_t605_manifest(manifest, make_subject(), root)

    def test_t605_artifact_rejects_extra_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(make_subject(), root)
            manifest["artifacts"][0]["extra"] = True
            with self.assertRaises(a.AcceptanceError):
                a.validate_t605_manifest(manifest, make_subject(), root)

    def test_t605_global_checks_are_ordered_and_typed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(make_subject(), root)
            manifest["global_checks"][0]["id"] = "machine_contracts"
            with self.assertRaises(a.AcceptanceError):
                a.validate_t605_manifest(manifest, make_subject(), root)

    def test_t605_gate_cannot_be_satisfied_by_command_result(self):
        self.assertEqual(a.GATES["T605.browser.full"].kind, "browser_manifest")

    def test_t310_gate_is_independent_of_t605(self):
        self.assertNotEqual(a.TASK_REQUIREMENTS["T310"], a.TASK_REQUIREMENTS["T605"])

    def test_t310_strict_manifest_binds_smoke_artifacts(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_local_browser_manifest(subject, root)
            a.validate_local_browser_manifest(manifest, subject, root)

    def test_t310_rejects_fake_quick_demo_truth(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_local_browser_manifest(subject, root)
            manifest["quick_demo"]["model_execution_performed"] = True
            with self.assertRaises(a.AcceptanceError):
                a.validate_local_browser_manifest(manifest, subject, root)

    def test_t310_rejects_missing_launch_artifact(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_local_browser_manifest(subject, root)
            manifest["artifacts"] = manifest["artifacts"][:2]
            with self.assertRaises(a.AcceptanceError):
                a.validate_local_browser_manifest(manifest, subject, root)


class PublisherTests(unittest.TestCase):
    def staged(self, root: Path, names: tuple[str, ...] = ("a", "b")) -> dict[str, Path]:
        stage = root / "stage"
        stage.mkdir()
        result = {}
        for name in names:
            path = stage / name
            path.write_text(f"new-{name}")
            result[name] = path
        return result

    def test_publisher_rejects_noncanonical_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(a.AcceptanceError):
                a.publish({"../escape": root / "x"}, root, expected_names={"x"})

    def test_publisher_rejects_stage_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            stage = root / "stage"
            stage.mkdir()
            (stage / "x").symlink_to(Path(outside) / "secret")
            with self.assertRaises(a.AcceptanceError):
                a.publish({"x": stage / "x"}, root, expected_names={"x"})

    def test_publisher_rejects_stage_hardlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            stage.mkdir()
            first = stage / "a"
            second = stage / "b"
            first.write_text("shared")
            os.link(first, second)
            with self.assertRaises(a.AcceptanceError):
                a.publish({"a": first, "b": second}, root, expected_names={"a", "b"})

    def test_read_owned_rejects_non_singleton_inode_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            first.write_text("shared")
            os.link(first, second)
            with self.assertRaises(a.AcceptanceError):
                a.read_owned(first)

    def test_publisher_replaces_existing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("old")
            staged = self.staged(root, ("a",))
            a.publish(staged, root, expected_names={"a"})
            self.assertEqual((root / "a").read_text(), "new-a")

    def test_publisher_uses_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".acceptance.lock").write_text("competitor")
            with self.assertRaises(a.AcceptanceError):
                a.publish(self.staged(root), root, expected_names={"a", "b"})

    def test_initial_journal_failure_cleans_owned_lock_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = self.staged(root, ("a",))
            with mock.patch.object(a, "_journal_write", side_effect=OSError("journal crash")):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a"})
            self.assertFalse((root / ".acceptance.lock").exists())
            self.assertFalse((root / ".acceptance.journal").exists())
            self.assertEqual([item.name for item in root.iterdir()], ["stage"])

    def test_journal_writer_does_not_follow_predictable_temp_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            sentinel = Path(outside) / "sentinel"
            sentinel.write_text("unchanged")
            (root / ".acceptance.journal.tmp").symlink_to(sentinel)
            value = {"schema": "quillframe_acceptance_publish_v1", "token": "a" * 32, "phase": "BACKUP", "names": [], "entries": []}
            a._journal_write(root / ".acceptance.journal", value)
            self.assertEqual(sentinel.read_text(), "unchanged")
            self.assertTrue((root / ".acceptance.journal.tmp").is_symlink())
            self.assertEqual(a.parse_json((root / ".acceptance.journal").read_text())["token"], "a" * 32)

    def test_journal_writer_rejects_target_symlink_without_touching_outside(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            sentinel = Path(outside) / "sentinel"
            sentinel.write_text("unchanged")
            (root / ".acceptance.journal").symlink_to(sentinel)
            value = {"schema": "quillframe_acceptance_publish_v1", "token": "b" * 32, "phase": "BACKUP", "names": [], "entries": []}
            with self.assertRaises(a.AcceptanceError):
                a._journal_write(root / ".acceptance.journal", value)
            self.assertEqual(sentinel.read_text(), "unchanged")

    def test_journal_writer_rejects_competing_owned_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            competing = {"schema": "quillframe_acceptance_publish_v1", "token": "c" * 32, "phase": "BACKUP", "names": [], "entries": []}
            (root / ".acceptance.journal").write_text(json.dumps(competing))
            replacement = {"schema": "quillframe_acceptance_publish_v1", "token": "d" * 32, "phase": "BACKUP", "names": [], "entries": []}
            with self.assertRaises(a.AcceptanceError):
                a._journal_write(root / ".acceptance.journal", replacement)
            self.assertEqual(a.parse_json((root / ".acceptance.journal").read_text())["token"], "c" * 32)

    def test_journal_writer_detects_concurrent_temp_swap_without_touching_sentinel(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            sentinel = Path(outside) / "sentinel"
            sentinel.write_text("unchanged")
            value = {"schema": "quillframe_acceptance_publish_v1", "token": "e" * 32, "phase": "BACKUP", "names": [], "entries": []}
            a._journal_write(root / ".acceptance.journal", value)
            replacement = dict(value)
            replacement["phase"] = "INSTALL"
            real_replace = os.replace

            def hostile_replace(source, target, *, src_dir_fd=None, dst_dir_fd=None):
                os.unlink(source, dir_fd=src_dir_fd)
                os.symlink(sentinel, source, dir_fd=src_dir_fd)
                return real_replace(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

            with mock.patch.object(os, "replace", side_effect=hostile_replace):
                with self.assertRaises((a.AcceptanceError, OSError)):
                    a._journal_write(root / ".acceptance.journal", replacement)
            self.assertEqual(sentinel.read_text(), "unchanged")

    def test_publisher_recovery_after_backup_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("old-a")
            (root / "b").write_text("old-b")
            staged = self.staged(root)
            with mock.patch.object(a, "rename_owned", side_effect=[None, OSError("backup crash")]):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a", "b"})
            a.recover(root)
            self.assertEqual((root / "a").read_text(), "old-a")
            self.assertEqual((root / "b").read_text(), "old-b")

    def test_publisher_recovery_after_install_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("old-a")
            (root / "b").write_text("old-b")
            staged = self.staged(root)
            original = a.link_owned
            count = [0]

            def fail_once(*args, **kwargs):
                count[0] += 1
                if count[0] == 2:
                    raise OSError("install crash")
                return original(*args, **kwargs)

            with mock.patch.object(a, "link_owned", side_effect=fail_once):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a", "b"})
            a.recover(root)
            self.assertEqual((root / "a").read_text(), "old-a")
            self.assertEqual((root / "b").read_text(), "old-b")

    def test_publisher_preserves_competitor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("old-a")
            staged = self.staged(root, ("a",))
            with mock.patch.object(a, "link_owned", side_effect=OSError("install crash")):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a"})
            (root / "a").write_text("competitor")
            with self.assertRaises(a.AcceptanceError):
                a.recover(root)
            self.assertEqual((root / "a").read_text(), "competitor")

    def test_publisher_final_readback_detects_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = self.staged(root, ("a",))
            with mock.patch.object(a, "read_owned", side_effect=OSError("readback")):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a"})

    def test_recovery_rejects_journal_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "journal"
            target.write_text("{}")
            (root / ".acceptance.journal").symlink_to(target)
            with self.assertRaises(a.AcceptanceError):
                a.recover(root)

    def test_recovery_rejects_competing_lock_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = self.staged(root, ("a",))
            (root / "a").write_text("old")
            with mock.patch.object(a, "rename_owned", side_effect=OSError("backup crash")):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a"})
            (root / ".acceptance.lock").write_text("competitor")
            with self.assertRaises(a.AcceptanceError):
                a.recover(root)

    def test_recovery_rejects_backup_ancestor_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            staged = self.staged(root, ("a",))
            (root / "a").write_text("old")
            with mock.patch.object(a, "rename_owned", side_effect=OSError("backup crash")):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a"})
            journal = a.parse_json((root / ".acceptance.journal").read_text())
            backup = root / f".backup-{journal['token']}"
            replacement = Path(outside) / "backup"
            replacement.mkdir()
            backup.rmdir()
            backup.symlink_to(replacement, target_is_directory=True)
            with self.assertRaises(a.AcceptanceError):
                a.recover(root)

    def test_recovery_cleanup_competitor_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = self.staged(root, ("a",))
            with mock.patch.object(a, "_fsync_directory", side_effect=[None, None, OSError("cleanup crash")]):
                with self.assertRaises(OSError):
                    a.publish(staged, root, expected_names={"a"})
            (root / "a").write_text("competitor")
            with self.assertRaises(a.AcceptanceError):
                a.recover(root)
            self.assertEqual((root / "a").read_text(), "competitor")

    def test_publisher_requires_same_filesystem_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = Path("/dev/shm") / f"qf-acceptance-stage-{os.getpid()}"
            if not stage.parent.exists():
                self.skipTest("no shared tmpfs")
            stage.mkdir(exist_ok=True)
            try:
                path = stage / "a"
                path.write_text("x")
                with self.assertRaises(a.AcceptanceError):
                    a.publish({"a": path}, root, expected_names={"a"})
            finally:
                path.unlink(missing_ok=True)
                stage.rmdir()


class TwoPhaseReportTests(unittest.TestCase):
    def _repo_fixture(self, root: Path) -> Path:
        root.mkdir(parents=True)
        (root / "VERSION").write_text(a.VERSION)
        spec = root / "specs" / "024-quillframe-all-in-one-1-0"
        spec.mkdir(parents=True)
        lines = "\n".join(f"- [ ] {task} description-{task}" for task in a.CANONICAL_TASK_IDS) + "\n"
        (spec / "tasks.en.md").write_text(lines)
        (spec / "tasks.zh-CN.md").write_text(lines.replace("description-", "描述-"))
        return root

    def test_t605_valid_fixture_is_accepted(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(subject, root)
            a.validate_t605_manifest(manifest, subject, root)

    def test_generate_runs_provisional_and_final_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repo_fixture(Path(directory) / "repo")
            evidence_root = Path(directory) / "evidence"
            evidence_root.mkdir()
            evidence = base_evidence(evidence_root)
            (evidence_root / "evidence.json").write_text(json.dumps(evidence))
            output = Path(directory) / "acceptance"
            report = a.generate(root, evidence_root / "evidence.json", output)
            self.assertEqual(report["gates"]["t608_phase"], "x")
            self.assertEqual(report["status"], "acceptance_incomplete")
            self.assertEqual(set(item.name for item in output.iterdir()), a.CANONICAL_OUTPUT_NAMES)
            self.assertEqual(len(report["rendered_artifacts"]), 4)

    def test_generate_never_authorizes_external_only_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repo_fixture(Path(directory) / "repo")
            evidence_root = Path(directory) / "evidence"
            evidence_root.mkdir()
            evidence = base_evidence(evidence_root)
            subject = evidence["acceptance_subject"]
            records = []
            for gate_id, kind, proof, approval in (
                ("T409.external", "workos_cloudflare_deployment", {"kind": "workos_cloudflare_deployment", "deployment_id": "deploy-1", "deployment_receipt_fingerprint": "1" * 64, "credentials_used": True, "deployed": True}, {"actor": "authorized_human", "status": "verified"}),
                ("T606.external", "real_ch001_author_chain", {"kind": "real_ch001_author_chain", "independent_reviewer_id": "reviewer-1", "model_invocation_id": "model-run-1", "model_execution_performed": True, "chain": ["candidate_visible", "accept", "settle", "publish"], "receipt_schema": "quillframe_host_bridge_result_v11", "candidate_artifact_fingerprint": "e" * 64, "acceptance_receipt_fingerprint": "2" * 64, "settlement_receipt_fingerprint": "3" * 64, "publication_receipt_fingerprint": "4" * 64}, {"actor": "authorized_human", "status": "verified"}),
                ("T607.approval", "promotion_approval", {"kind": "promotion_approval", "target_identity": {"environment": "production", "version": a.VERSION, "project_id": subject["project_id"], "candidate_id": subject["candidate_id"]}, "approved": True, "depends_on": ["T409.external", "T606.external"]}, {"actor": "authorized_human", "status": "approved"}),
            ):
                target = {"environment": "production", "version": a.VERSION, "project_id": subject["project_id"], "candidate_id": subject["candidate_id"]}
                payload = {"schema": "quillframe_external_acceptance_proof_v1", "gate_id": gate_id, "project_id": subject["project_id"], "candidate_id": subject["candidate_id"], "candidate_fingerprint": "e" * 64, "receipt_fingerprint": "f" * 64, "target_identity": target, "proof": proof}
                artifact = write_bytes(evidence_root, f"{gate_id}.proof", json.dumps(payload, sort_keys=True).encode())
                artifact["role"] = "external-proof"
                records.append({"id": gate_id, "gate_id": gate_id, "subject": subject, "subject_after": subject, "started_at": "2026-08-20T00:00:00Z", "finished_at": "2026-08-20T00:00:01Z", "result": "pass", "artifacts": [artifact], "project_id": subject["project_id"], "candidate_id": subject["candidate_id"], "candidate_fingerprint": "e" * 64, "receipt_fingerprint": "f" * 64, "target_identity": target, "approval": approval, "proof": proof})
            evidence["external_evidence"] = records
            evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
            (evidence_root / "evidence.json").write_text(json.dumps(evidence))
            report = a.generate(root, evidence_root / "evidence.json", Path(directory) / "acceptance")
            self.assertFalse(report["release_promotion_authorized"])
            self.assertEqual(report["status"], "acceptance_incomplete")

    def test_provisional_phase_is_tilde(self):
        self.assertEqual(a.T608_PROVISIONAL, "~")

    def test_final_phase_is_x(self):
        self.assertEqual(a.T608_FINAL, "x")

    def test_report_renderers_are_distinct_by_language(self):
        tasks = [{"id": "T000", "status": "~", "requirements": ["G0.scope"]}]
        report = {"evidence_fingerprint": "e" * 64, "status": "blocked", "gates": {"t608_phase": "~"}}
        self.assertNotEqual(a.render_markdown(report, tasks, "en", True), a.render_markdown(report, tasks, "zh-CN", True))

    def test_report_renderers_are_distinct_by_view(self):
        tasks = [{"id": "T000", "status": "~", "requirements": ["G0.scope"]}]
        report = {"evidence_fingerprint": "e" * 64, "status": "blocked", "gates": {"t608_phase": "~"}}
        self.assertNotEqual(a.render_markdown(report, tasks, "en", True), a.render_markdown(report, tasks, "en", False))

    def test_json_self_hash_is_explicitly_excluded(self):
        self.assertEqual(a.JSON_SELF_HASH_POLICY, "excluded_by_contract")

    def test_rendered_artifacts_are_four_markdown_descriptors(self):
        self.assertEqual(len(a.MARKDOWN_NAMES), 4)
        self.assertNotIn(f"{a.VERSION}.json", a.MARKDOWN_NAMES)

    def test_final_report_requires_all_tasks_x(self):
        tasks = [{"status": "x"}, {"status": "~"}]
        self.assertFalse(a.all_local_tasks_pass(tasks))

    def test_final_report_requires_t608_x(self):
        self.assertFalse(a.final_gate_ready({"t608_phase": "~"}))
        self.assertTrue(a.final_gate_ready({"t608_phase": "x"}))


class RunnerContractTests(unittest.TestCase):
    def test_runner_cli_has_no_arbitrary_command_argument(self):
        source = (Path(__file__).parents[1] / "release" / "run_acceptance.py").read_text()
        self.assertNotIn("--command", source)

    def test_runner_has_identity_scripts(self):
        names = {item.name for item in a.RUNNER_COMMANDS}
        self.assertIn("identity", names)
        self.assertIn("peer_contract", names)

    def test_runner_has_full_python_suite_and_compile(self):
        names = {item.name for item in a.RUNNER_COMMANDS}
        self.assertIn("python_full", names)
        self.assertIn("python_compile", names)

    def test_runner_emits_every_required_command_gate_once_from_its_fixed_owner(self):
        emitted: dict[str, list[str]] = {}
        for command in a.RUNNER_COMMANDS:
            for gate_id in command.gate_ids:
                emitted.setdefault(gate_id, []).append(command.name)
                self.assertEqual(a.GATES[gate_id].command_name, command.name)
        required = {
            gate_id
            for requirements in a.TASK_REQUIREMENTS.values()
            for gate_id in requirements
            if gate_id not in a.DERIVED_GATES and a.GATES[gate_id].kind == "command"
        }
        self.assertEqual(required - emitted.keys(), set())
        self.assertTrue(all(len(owners) == 1 for owners in emitted.values()))

    def test_complete_fixed_runner_and_browser_evidence_marks_every_local_task_complete(self):
        evidence = base_evidence(Path("/tmp"))
        evidence["commands"] = [
            {"gate_id": gate_id, "result": "pass"}
            for command in a.RUNNER_COMMANDS
            for gate_id in command.gate_ids
        ]
        evidence["browser_manifests"] = [
            {"gate_id": "T310.browser.local", "result": "pass"},
            {"gate_id": "T605.browser.full", "result": "pass"},
        ]
        tasks = a.derive_tasks(evidence, True)
        incomplete = [item["id"] for item in tasks if item["id"] not in a.EXTERNAL_TASKS and item["status"] != "x"]
        self.assertEqual(incomplete, [])

    def test_runner_matches_every_deterministic_core_ci_quality_command(self):
        expected = {
            "version_consistency": ("python", "scripts/version_consistency.py"),
            "machine_namespace": ("python", "scripts/machine_namespace_hygiene.py"),
            "framework_hygiene": ("python", "scripts/framework_hygiene.py"),
            "quillframe_docs_quality": ("python", "scripts/quillframe_docs_quality.py"),
            "design_system_quality": ("python", "scripts/design_system_quality.py"),
            "semantic_reference_integrity": ("python", "scripts/semantic_reference_integrity.py"),
        }
        commands = {item.name: item.argv for item in a.RUNNER_COMMANDS}
        for name, argv in expected.items():
            self.assertEqual(commands.get(name), argv)

    def test_runner_compile_surface_is_ci_equivalent(self):
        command = next(item for item in a.RUNNER_COMMANDS if item.name == "python_compile")
        self.assertEqual(command.argv, (
            "python", "-m", "compileall", "-q",
            "agent_runtime", "corpus", "evals", "harness", "learning",
            "model_runtime", "persistence", "production_runtime", "publication",
            "quality", "quillframe", "release", "studio", "core_operations.py",
            "project_resolution.py", "quillframe.py",
        ))

    def test_ci_invokes_the_native_fixed_acceptance_runner(self):
        workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "quillframe-ci.yml").read_text()
        normalized = " ".join(workflow.split())
        self.assertIn("python release/run_acceptance.py --repo-root . --output /tmp/quillframe-acceptance-ci", normalized)
        self.assertNotIn("python -m release.run_acceptance", normalized)

    def test_runner_has_real_framework_selftest(self):
        item = next(item for item in a.RUNNER_COMMANDS if item.name == "framework_selftest")
        self.assertEqual(item.argv, ("python", "quillframe.py", "self-test"))

    def test_runner_has_bundle_build_and_verify(self):
        names = {item.name for item in a.RUNNER_COMMANDS}
        self.assertIn("bundle_build", names)
        self.assertIn("bundle_verify", names)

    def test_runner_has_frozen_install(self):
        item = next(item for item in a.RUNNER_COMMANDS if item.name == "pnpm_frozen")
        self.assertIn("--frozen-lockfile", item.argv)

    def test_runner_has_root_quality_test_type_build(self):
        names = {item.name for item in a.RUNNER_COMMANDS}
        self.assertTrue({"quality", "test", "typecheck", "build"} <= names)

    def test_runner_has_wheel_install_smoke(self):
        names = {item.name for item in a.RUNNER_COMMANDS}
        self.assertTrue({"wheel_build", "wheel_install_smoke"} <= names)

    def test_runner_has_t603_t605_cloud(self):
        names = {item.name for item in a.RUNNER_COMMANDS}
        self.assertTrue({"t603_site_smoke", "t603_studio_smoke", "t603_local_launch", "cloud_security", "t605_browser"} <= names)

    def test_t605_environment_uses_repo_root_previews_and_chrome_bin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.mkdir()
            repo = root / "repo"
            repo.mkdir()
            environment = runner.command_environment(
                "t605_browser",
                {"PATH": "/bin", "CHROME_BIN": "/opt/chromium", "QF_REPO_ROOT": "wrong", "QF_START_PREVIEWS": "0", "API_TOKEN": "secret"},
                output,
                repo,
            )
            self.assertEqual(environment["QF_REPO_ROOT"], str(repo))
            self.assertEqual(environment["QF_START_PREVIEWS"], "1")
            self.assertEqual(environment["QF_BROWSER_EVIDENCE_DIR"], str(output))
            self.assertEqual(environment["CHROME_BIN"], "/opt/chromium")
            self.assertNotIn("API_TOKEN", environment)
            command = next(item for item in a.RUNNER_COMMANDS if item.name == "t605_browser")
            self.assertEqual(command.argv, ("corepack", "pnpm", "--filter", "@quillframe/product-site", "browser:acceptance:t605"))
            source = (Path(__file__).parents[1] / "release" / "run_acceptance.py").read_text()
            self.assertIn('path = output / "browser-acceptance-v1.json"', source)

    def test_runner_consumes_root_t605_manifest_with_strict_validator(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = a.synthetic_t605_manifest(subject, root)
            (root / "browser-acceptance-v1.json").write_text(json.dumps(manifest, sort_keys=True))
            records, blocks = runner.consume_t605_manifest(root, subject)
            self.assertEqual(blocks, [])
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["gate_id"], "T605.browser.full")
            (root / "site" / "screenshots" / "wide-light.png").write_bytes(b"mutated")
            records, blocks = runner.consume_t605_manifest(root, subject)
            self.assertEqual(records, [])
            self.assertTrue(any("rejected" in item for item in blocks))

    def test_t310_composer_produces_pass_from_distinct_smoke_artifacts(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            (root / "commands").mkdir()
            (root / "commands" / "t603_site_smoke.stdout.txt").write_text("browser_smoke=PASS\n")
            (root / "commands" / "t603_studio_smoke.stdout.txt").write_text("browser_smoke=PASS\n")
            (root / "commands" / "t603_local_launch.stdout.txt").write_text("local_launch_smoke=PASS\nlocal_launch_profile=local\nlocal_launch_core_bound=true\nlocal_launch_cloud_upload_started=false\n")
            for relative in (
                "t603-site-smoke/home-desktop.png",
                "t603-site-smoke/home-demo-complete.png",
                "t603-site-smoke/home-phone.png",
                "t603-site-smoke/docs-desktop.png",
                "t603-studio-smoke/studio-desktop.png",
                "t603-studio-smoke/studio-phone.png",
                "t603-studio-smoke/studio-dark.png",
                "t603-local-launch/local-launch-bound.png",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((relative + "\n").encode())
            command_results = {name: {"result": "pass", "exit_code": 0} for name in ("t603_site_smoke", "t603_studio_smoke", "t603_local_launch")}
            path = runner.compose_t310_manifest(root, subject, subject, command_results)
            manifest = a.read_json_descriptor(root, path.name)
            a.validate_local_browser_manifest(manifest, subject, root)
            self.assertEqual(manifest["status"], "pass")
            self.assertEqual(len(manifest["artifacts"]), 8)

    def test_t310_composer_mutated_artifact_is_rejected_on_readback(self):
        subject = make_subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            (root / "commands").mkdir()
            (root / "commands" / "t603_site_smoke.stdout.txt").write_text("browser_smoke=PASS\n")
            (root / "commands" / "t603_studio_smoke.stdout.txt").write_text("browser_smoke=PASS\n")
            (root / "commands" / "t603_local_launch.stdout.txt").write_text("local_launch_smoke=PASS\nlocal_launch_profile=local\nlocal_launch_core_bound=true\nlocal_launch_cloud_upload_started=false\n")
            for relative in (
                "t603-site-smoke/home-desktop.png",
                "t603-site-smoke/home-demo-complete.png",
                "t603-site-smoke/home-phone.png",
                "t603-site-smoke/docs-desktop.png",
                "t603-studio-smoke/studio-desktop.png",
                "t603-studio-smoke/studio-phone.png",
                "t603-studio-smoke/studio-dark.png",
                "t603-local-launch/local-launch-bound.png",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"stable-image")
            command_results = {name: {"result": "pass", "exit_code": 0} for name in ("t603_site_smoke", "t603_studio_smoke", "t603_local_launch")}
            runner.compose_t310_manifest(root, subject, subject, command_results)
            (root / "t603-site-smoke" / "home-desktop.png").write_bytes(b"tampered-image")
            manifest = a.read_json_descriptor(root, "t310-local-browser.json")
            with self.assertRaises(a.AcceptanceError):
                a.validate_local_browser_manifest(manifest, subject, root)

    def test_runner_records_post_subject(self):
        self.assertIn("subject_after", a.COMMAND_RECORD_KEYS)

    def test_runner_has_process_group_timeout(self):
        source = (Path(__file__).parents[1] / "release" / "run_acceptance.py").read_text()
        self.assertIn("killpg", source)
        self.assertIn("SIGKILL", source)

    def test_runner_redacts_output(self):
        self.assertNotIn("Bearer abc", a.redact_text("Bearer abc"))

    def test_runner_child_environment_drops_secret_names(self):
        env = runner.child_environment({
            "PATH": "/bin",
            "HOME": "/tmp/home",
            "NPM_CONFIG_STORE_DIR": "/tmp/quillframe-pnpm-store",
            "NPM_CONFIG_REGISTRY": "https://untrusted.invalid",
            "API_TOKEN": "sentinel",
            "COOKIE": "cookie-value",
            "QF_SENTINEL": "should-not-pass",
        })
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(env["NPM_CONFIG_STORE_DIR"], "/tmp/quillframe-pnpm-store")
        self.assertNotIn("NPM_CONFIG_REGISTRY", env)
        self.assertNotIn("API_TOKEN", env)
        self.assertNotIn("COOKIE", env)
        self.assertNotIn("QF_SENTINEL", env)

    def test_runner_exit_code_fails_closed_on_any_local_gate_or_browser_block(self):
        passing = {
            command.name: {"result": "pass", "exit_code": 0}
            for command in a.RUNNER_COMMANDS
        }
        self.assertEqual(runner.acceptance_exit_code(passing, []), 0)
        self.assertEqual(runner.acceptance_exit_code({}, []), 1)
        failed = dict(passing)
        failed["python_full"] = {"result": "failed", "exit_code": 1}
        self.assertEqual(
            runner.acceptance_exit_code(failed, []),
            1,
        )
        inconsistent = dict(passing)
        inconsistent["python_full"] = {"result": "pass", "exit_code": 1}
        self.assertEqual(
            runner.acceptance_exit_code(inconsistent, []),
            1,
        )
        self.assertEqual(runner.acceptance_exit_code(passing, ["T605 manifest missing"]), 1)

    def test_runner_python_commands_use_the_invoking_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            argv = runner.substitute(("python", "-V"), Path(directory))
        self.assertEqual(argv[0], sys.executable)

    def test_runner_bounded_output_replaces_environment_secret_and_headers(self):
        raw = b"sentinel Authorization: Bearer abc Cookie: sid=123 https://user:pass@example.test/path"
        safe = runner.bounded_output(raw, secret_values=("sentinel",))
        text = safe.decode()
        self.assertNotIn("sentinel", text)
        self.assertNotIn("Bearer abc", text)
        self.assertNotIn("sid=123", text)
        self.assertNotIn("user:pass@", text)

    def test_evidence_readback_rejects_secret_diagnostic_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            evidence = base_evidence(root, subject)
            record = command_record("T102.schema.catalog", subject, root)
            descriptor = record["artifacts"][0]
            (root / descriptor["path"]).write_bytes(b"Authorization: Bearer raw-secret")
            descriptor["size"] = len(b"Authorization: Bearer raw-secret")
            descriptor["sha256"] = hashlib.sha256(b"Authorization: Bearer raw-secret").hexdigest()
            descriptor["role"] = "stdout"
            evidence["commands"] = [record]
            evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
            with self.assertRaises(a.AcceptanceError):
                a.validate_evidence(evidence, root)

    def test_evidence_readback_rejects_absolute_diagnostic_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = make_subject()
            evidence = base_evidence(root, subject)
            record = command_record("T102.schema.catalog", subject, root)
            descriptor = record["artifacts"][0]
            raw = b"diagnostic path /opt/private/output"
            (root / descriptor["path"]).write_bytes(raw)
            descriptor["size"] = len(raw)
            descriptor["sha256"] = hashlib.sha256(raw).hexdigest()
            descriptor["role"] = "stdout"
            evidence["commands"] = [record]
            evidence["evidence_fingerprint"] = a.evidence_fingerprint(evidence)
            with self.assertRaises(a.AcceptanceError):
                a.validate_evidence(evidence, root)

    def test_runner_kills_process_group_after_term_ignores(self):
        code, _stdout, _stderr, _started, _finished = runner.run_process(("python", "-c", "import signal\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nimport time\ntime.sleep(10)"), Path("/tmp"), 10)
        self.assertIn(code, {124, 137})


if __name__ == "__main__":
    unittest.main()
