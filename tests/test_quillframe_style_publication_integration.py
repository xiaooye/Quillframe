"""Focused Core integration tests for the explicit Style Atlas protocol."""
from __future__ import annotations

import json
import hashlib
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from core_operations import (
    CORPUS_LEGACY_ANALYSIS_PROTOCOL_ID,
    CORPUS_STYLE_ANALYSIS_PROTOCOL_ID,
    CoreOperations,
    OperationError,
)
from corpus.library import CorpusLibrary, CorpusLibraryError
from persistence.quillframe_sqlite import QuillframeStore


ATLAS_FP = "sha256:" + "a" * 64
STYLE_FP = "sha256:" + "1" * 64
CRAFT_FP = "sha256:" + "2" * 64
RECEIPT_FP = "sha256:" + "3" * 64


class _Library:
    def __init__(self, public_root: Path) -> None:
        self.public_root = public_root
        self.db_path = public_root / "private.sqlite"
        self.calls: list[tuple[str, tuple, dict]] = []

    def study_status(self, study_id: str, *, include_works: bool) -> dict:
        self.calls.append(("study_status", (study_id,), {"include_works": include_works}))
        return {"study_id": study_id}

    def preview_public(self, *args, **kwargs):
        self.calls.append(("preview_public", args, kwargs))
        return {"schema": "legacy-preview"}

    def validate_public(self, *args, **kwargs):
        self.calls.append(("validate_public", args, kwargs))
        return {"schema": "legacy-validation"}

    def release_public(self, *args, **kwargs):
        self.calls.append(("release_public", args, kwargs))
        return {"schema": "legacy-release"}

    def list_public(self, *args, **kwargs):
        self.calls.append(("list_public", args, kwargs))
        return {"schema": "legacy-list"}

    def get_public(self, *args, **kwargs):
        self.calls.append(("get_public", args, kwargs))
        return {"schema": "legacy-get"}


class _Runner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def trusted_publication_material_for_study(self, study_id: str) -> dict:
        self.calls.append(study_id)
        return {
            "schema": "quillframe_corpus_trusted_style_publication_material_v1",
            "candidate_bundle": {"bundle_fingerprint": "sha256:" + "b" * 64},
            "forbidden_identity_terms": ["private licensed work"],
        }


class _Publication:
    MAX_ATLAS_BYTES = 262_144

    def __init__(self) -> None:
        self.preview_calls: list[tuple[dict, dict]] = []

    def build_style_atlas_preview(self, bundle: dict, **kwargs) -> dict:
        self.preview_calls.append((bundle, kwargs))
        return {
            "schema": "quillframe_public_general_style_atlas_preview_v1",
            "atlas": {
                "schema": "quillframe_public_general_style_atlas_v1",
                "atlas_fingerprint": ATLAS_FP,
            },
            "release_gates": {"semantic_leakage": {"status": "pending"}},
            "preview_token": "style-preview-" + "b" * 64,
            "preview_fingerprint": "sha256:" + "e" * 64,
        }

    @staticmethod
    def validate_style_atlas(atlas: dict) -> list[str]:
        return [] if atlas.get("atlas_fingerprint") == ATLAS_FP else ["atlas_fingerprint_mismatch"]

    @staticmethod
    def validate_style_registry(registry: dict) -> list[str]:
        return [] if registry.get("schema") == "test-style-registry" else ["style_registry_invalid"]

    @staticmethod
    def atlas_filename(atlas_fingerprint: str) -> str:
        if atlas_fingerprint != ATLAS_FP:
            raise ValueError("atlas_fingerprint_invalid")
        return "style-atlas-" + "a" * 64 + ".json"

    @staticmethod
    def release_receipt_filename(receipt_fingerprint: str) -> str:
        if receipt_fingerprint != RECEIPT_FP:
            raise ValueError("release_receipt_fingerprint_invalid")
        return "style-release-receipt-" + "3" * 64 + ".json"

    @staticmethod
    def validate_style_release_receipt(receipt: dict) -> list[str]:
        return [] if receipt.get("receipt_fingerprint") == RECEIPT_FP else [
            "release_receipt_fingerprint_mismatch"
        ]


class StylePublicationCoreIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.operations = CoreOperations(QuillframeStore(self.root / "data"))
        self.library = _Library(self.root / "public")
        self.runner = _Runner()
        self.publication = _Publication()

    def _style_patches(self):
        return (
            patch.object(self.operations, "corpus_library", return_value=self.library),
            patch.object(
                self.operations,
                "corpus_study_runner",
                return_value=(self.library, self.runner),
            ),
            patch.object(
                self.operations,
                "_corpus_style_publication_module",
                return_value=self.publication,
            ),
        )

    def test_style_preview_loads_only_trusted_db_material_and_legacy_is_unchanged(self) -> None:
        first, second, third = self._style_patches()
        with first, second, third:
            preview = self.operations.corpus_preview_public(
                "STUDY-1", analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
        self.assertEqual(preview["atlas"]["atlas_fingerprint"], ATLAS_FP)
        self.assertEqual(self.runner.calls, ["STUDY-1"])
        self.assertEqual(
            self.publication.preview_calls[0][0],
            {"bundle_fingerprint": "sha256:" + "b" * 64},
        )
        self.assertEqual(
            self.publication.preview_calls[0][1]["forbidden_identity_terms"],
            ["private licensed work"],
        )
        with self.assertRaises(OperationError) as raised:
            with first, second, third:
                self.operations.corpus_preview_public(
                    "STUDY-1",
                    analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID,
                    candidate_bundle={"caller": "must never be trusted"},
                )
        self.assertEqual(raised.exception.code, "corpus_style_preview_args_invalid")

        with patch.object(self.operations, "corpus_library", return_value=self.library):
            legacy = self.operations.corpus_preview_public(
                "STUDY-LEGACY", release_id="v1",
                analysis_protocol_id=CORPUS_LEGACY_ANALYSIS_PROTOCOL_ID,
            )
        self.assertEqual(legacy["schema"], "legacy-preview")
        self.assertIn(("preview_public", ("STUDY-LEGACY",), {"release_id": "v1"}), self.library.calls)

    def test_style_validate_is_schema_only_and_style_release_stays_blocked(self) -> None:
        atlas = {"schema": "quillframe_public_general_style_atlas_v1", "atlas_fingerprint": ATLAS_FP}
        with patch.object(
            self.operations, "_corpus_style_publication_module", return_value=self.publication
        ):
            result = self.operations.corpus_validate_public(
                atlas, analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "valid")
        self.assertFalse(result["authority"])
        with self.assertRaises(OperationError) as raised:
            self.operations.corpus_release_public(
                "STUDY-1", analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID,
                preview_token="style-preview-" + "b" * 64,
                atlas_fingerprint=ATLAS_FP,
            )
        self.assertEqual(raised.exception.code, "corpus_style_release_trusted_receipts_required")

    def test_style_registry_list_and_get_verify_exact_content_addressed_atlas(self) -> None:
        self.library.public_root.mkdir(parents=True)
        release = {
            "atlas_fingerprint": ATLAS_FP,
            "style_artifact_fingerprint": STYLE_FP,
            "craft_artifact_fingerprint": CRAFT_FP,
            "analysis_protocol_version": "1",
            "content_zone": "general",
            "preview_fingerprint": "sha256:" + "4" * 64,
            "preview_token": "style-preview-" + "5" * 64,
            "release_receipt_fingerprint": RECEIPT_FP,
        }
        registry = {
            "schema": "test-style-registry",
            "registry_fingerprint": "sha256:" + "c" * 64,
            "releases": [release],
        }
        (self.library.public_root / "style_registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        atlas = {
            "schema": "quillframe_public_general_style_atlas_v1",
            "atlas_fingerprint": ATLAS_FP,
            "style_artifact_fingerprint": STYLE_FP,
            "craft_artifact_fingerprint": CRAFT_FP,
            "analysis_protocol_version": "1",
            "content_zone": "general",
        }
        atlas_path = self.library.public_root / self.publication.atlas_filename(ATLAS_FP)
        atlas_path.write_text(json.dumps(atlas), encoding="utf-8")
        receipt = {
            "receipt_fingerprint": RECEIPT_FP,
            "atlas_fingerprint": ATLAS_FP,
            "preview_fingerprint": release["preview_fingerprint"],
            "preview_token": release["preview_token"],
            "style_artifact_fingerprint": STYLE_FP,
            "craft_artifact_fingerprint": CRAFT_FP,
        }
        receipt_path = self.library.public_root / self.publication.release_receipt_filename(RECEIPT_FP)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with (
            patch.object(self.operations, "corpus_library", return_value=self.library),
            patch.object(
                self.operations, "_corpus_style_publication_module", return_value=self.publication
            ),
        ):
            listed = self.operations.corpus_list_public(
                analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
            loaded = self.operations.corpus_get_public(
                ATLAS_FP, analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["items"][0]["atlas_fingerprint"], ATLAS_FP)
        self.assertEqual(loaded["atlas_fingerprint"], ATLAS_FP)
        self.assertFalse(loaded["authority"])

        mismatched_registry = json.loads(json.dumps(registry))
        mismatched_registry["releases"][0]["craft_artifact_fingerprint"] = "sha256:" + "d" * 64
        (self.library.public_root / "style_registry.json").write_text(
            json.dumps(mismatched_registry), encoding="utf-8"
        )
        with (
            patch.object(self.operations, "corpus_library", return_value=self.library),
            patch.object(
                self.operations, "_corpus_style_publication_module", return_value=self.publication
            ),
            self.assertRaises(OperationError) as registry_binding_error,
        ):
            self.operations.corpus_get_public(
                ATLAS_FP, analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
        self.assertEqual(registry_binding_error.exception.code, "released_style_atlas_invalid")

        (self.library.public_root / "style_registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        receipt_path.write_text(
            json.dumps({**receipt, "craft_artifact_fingerprint": "sha256:" + "d" * 64}),
            encoding="utf-8",
        )
        with (
            patch.object(self.operations, "corpus_library", return_value=self.library),
            patch.object(
                self.operations, "_corpus_style_publication_module", return_value=self.publication
            ),
            self.assertRaises(OperationError) as receipt_binding_error,
        ):
            self.operations.corpus_get_public(
                ATLAS_FP, analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
        self.assertEqual(receipt_binding_error.exception.code, "released_style_receipt_invalid")

        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        atlas_path.write_text(json.dumps({**atlas, "atlas_fingerprint": "sha256:" + "d" * 64}), encoding="utf-8")
        with (
            patch.object(self.operations, "corpus_library", return_value=self.library),
            patch.object(
                self.operations, "_corpus_style_publication_module", return_value=self.publication
            ),
            self.assertRaises(OperationError) as raised,
        ):
            self.operations.corpus_list_public(
                analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID
            )
        self.assertEqual(raised.exception.code, "released_style_atlas_invalid")

    def test_committed_empty_style_registry_is_read_through_exact_public_root(self) -> None:
        public_root = Path(__file__).resolve().parents[1] / "corpus" / "general"
        result = self.operations.corpus_list_public(
            analysis_protocol_id=CORPUS_STYLE_ANALYSIS_PROTOCOL_ID,
            db_path=self.root / "corpus.sqlite",
            public_root=public_root,
        )
        self.assertEqual(result["schema"], "quillframe_public_general_style_index_v1")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["items"], [])

    def test_stable_source_verifier_detects_post_scan_byte_drift_without_mutation(self) -> None:
        sources = self.root / "sources"
        sources.mkdir()
        source = sources / "licensed-work.txt"
        original = b"synthetic licensed source bytes"
        source.write_bytes(original)
        digest = hashlib.sha256(original).hexdigest()
        library = CorpusLibrary(self.root / "source-check.sqlite", public_root=self.root / "unused")
        with closing(sqlite3.connect(library.db_path)) as connection:
            connection.execute(
                "INSERT INTO collections(collection_id,root_path,rights_class,rights_basis) "
                "VALUES('COL-1',?,'analysis_only','synthetic test fixture')",
                (str(sources.resolve()),),
            )
            connection.execute(
                "INSERT INTO logical_works(work_id,collection_id,public_work_id,logical_key,active_version_id) "
                "VALUES('WORK-1','COL-1',?,'fixture','VERSION-1')",
                ("PW-" + "1" * 32,),
            )
            connection.execute(
                "INSERT INTO source_versions(version_id,work_id,version_number,sha256,media_type,"
                "char_count,parse_state,private_metadata_json,available) "
                "VALUES('VERSION-1','WORK-1',1,?,'txt',32,'ok','{}',1)",
                (digest,),
            )
            connection.execute(
                "INSERT INTO source_files(file_id,collection_id,relative_path,work_id,version_id,"
                "available,last_seen_token) VALUES('FILE-1','COL-1','licensed-work.txt',"
                "'WORK-1','VERSION-1',1,'scan-1')"
            )
            connection.execute(
                "INSERT INTO studies(study_id,public_study_id,collection_id,profile,state,seed,"
                "proposal_hash,checklist_hash) VALUES('STUDY-1',?,'COL-1','general','proposed',"
                "'seed',?,NULL)",
                ("PS-" + "2" * 32, "sha256:" + "3" * 64),
            )
            connection.execute(
                "INSERT INTO study_works(study_id,work_id,version_id,ordinal,state) "
                "VALUES('STUDY-1','WORK-1','VERSION-1',1,'studied')"
            )
            connection.execute(
                "UPDATE studies SET state='complete',checklist_hash=? WHERE study_id='STUDY-1'",
                ("sha256:" + "4" * 64,),
            )
            connection.commit()
        receipt = library.verify_style_source_dependency(
            "STUDY-1", "PW-" + "1" * 32,
            version_id="VERSION-1", source_sha256=digest,
        )
        self.assertEqual(receipt["source_fingerprint"], "sha256:" + digest)
        self.assertFalse(receipt["source_prose_included"])

        source.write_bytes(original + b" drift")
        with self.assertRaises(CorpusLibraryError) as raised:
            library.verify_style_source_dependency(
                "STUDY-1", "PW-" + "1" * 32,
                version_id="VERSION-1", source_sha256=digest,
            )
        self.assertEqual(raised.exception.code, "style_source_dependency_drift")
        self.assertEqual(library.study_status("STUDY-1", include_works=False)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
