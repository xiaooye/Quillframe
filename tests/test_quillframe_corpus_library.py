"""Focused safety and lifecycle tests for :mod:`corpus.library`."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from corpus.library import (
    CorpusLibrary,
    CorpusLibraryError,
    STUDY_SIZE,
    _private_profile_signal,
    _private_title_family,
)
from corpus.style_sampling import (
    MAX_SOURCE_CHARS as STYLE_IN_MEMORY_SOURCE_CHARS,
    fingerprint_source_text,
    sample_style_windows,
    style_window_passes_hygiene,
    validate_sampling_manifest,
)


METRICS = {
    "sampled_chars": 3_000,
    "paragraph_count": 30,
    "sentence_count": 90,
    "mean_sentence_chars_milli": 33_333,
    "dialogue_char_ratio_ppm": 120_000,
    "unique_char_ratio_ppm": 80_000,
    "punctuation_ratio_ppm": 60_000,
}


class CorpusLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.sources = self.root / "private-sources"
        self.sources.mkdir()
        self.db_path = self.root / "private" / "corpus.sqlite"
        self.public_root = self.root / "public"
        self.library = CorpusLibrary(self.db_path, public_root=self.public_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _alpha_token(index: int) -> str:
        value = index
        characters: list[str] = []
        for _ in range(4):
            characters.append(chr(ord("a") + value % 26))
            value //= 26
        return "".join(reversed(characters))

    def _work_path(self, index: int) -> Path:
        return self.sources / f"private-story-{self._alpha_token(index)}.txt"

    @staticmethod
    def _general_body(identity: int, *, chars: int = 100_200) -> str:
        prefix = (
            f"supersecretmarker{identity:03d} 开端行动。人物作出选择！\n\n"
            f"中段因果推进 {identity:03d}。\n\n"
            f"收束回应前因 {identity:03d}。\n\n"
        )
        filler = "narrative action continues through consequence. "
        return (prefix + filler * ((chars - len(prefix)) // len(filler) + 1))[:chars]

    def _write_txt_works(
        self, count: int, *, duplicate_last: bool = False, chars: int = 100_200
    ) -> None:
        for index in range(count):
            identity = 0 if duplicate_last and index == count - 1 else index
            self._work_path(index).write_text(
                self._general_body(identity, chars=chars), encoding="utf-8", newline="\n"
            )

    @staticmethod
    def _write_epub(
        path: Path,
        *,
        container_doctype: str = "",
        package_doctype: str = "",
        chapter_doctype: str = "",
        title: str = "Private Proper Name",
    ) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("mimetype", "application/epub+zip")
            archive.writestr(
                "META-INF/container.xml",
                "<?xml version='1.0'?>"
                + container_doctype
                + "<container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'>"
                "<rootfiles><rootfile full-path='OEBPS/package.opf'/></rootfiles></container>",
            )
            archive.writestr(
                "OEBPS/package.opf",
                "<?xml version='1.0'?>"
                + package_doctype
                + "<package xmlns='http://www.idpf.org/2007/opf' "
                "xmlns:dc='http://purl.org/dc/elements/1.1/' version='3.0'>"
                f"<metadata><dc:title>{title}</dc:title><dc:creator>Private Creator</dc:creator>"
                "</metadata><manifest><item id='c1' href='c1.xhtml' media-type='application/xhtml+xml'/>"
                "</manifest><spine><itemref idref='c1'/></spine></package>",
            )
            archive.writestr(
                "OEBPS/c1.xhtml",
                chapter_doctype
                + "<html><body><p>合法正文第一段。</p><script>secret script</script>"
                "<p>合法正文第二段。</p></body></html>",
            )

    def _confirmed(self) -> tuple[dict, dict]:
        scan = self.library.scan_collection(
            self.sources,
            collection_id="COLLECTION-TEST",
            rights_basis="test fixtures owned by caller",
            language="zh-CN",
        )
        proposed = self.library.propose_selection(
            "STUDY-TEST", collection_id=scan["collection_id"], seed="fixed-seed",
            profile="general",
        )
        confirmed = self.library.confirm_selection(
            proposed["study_id"], expected_hash=proposed["proposal_hash"]
        )
        return scan, confirmed

    def _complete(self) -> tuple[dict, dict]:
        scan, confirmed = self._confirmed()
        for work in confirmed["works"]:
            status = self.library.mark_studied(
                confirmed["study_id"], work["public_work_id"], metrics=METRICS
            )
        self.assertEqual(status["status"], "complete")
        return scan, self.library.study_status(confirmed["study_id"])

    @staticmethod
    def _style_fingerprint(label: str) -> str:
        return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()

    def _style_completion_fixture(self) -> dict[str, object]:
        style_run_id = "STYLE-RUN-SYNTHETIC"
        used_source_set_fingerprint = "sha256:" + hashlib.sha256(
            json.dumps(
                {
                    "schema": "quillframe_style_used_source_set_v1",
                    "style_run_id": style_run_id,
                    "used_sources": [{
                        "public_work_id": "PW-SYNTHETIC-USED",
                        "ordinal": 1,
                        "activation_cycle": 1,
                        "activation_kind": "seed",
                        "source_fingerprints": [self._style_fingerprint("source-used")],
                    }],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        receipt = {
            "schema": "quillframe_corpus_style_completion_receipt_v1",
            "style_run_id": style_run_id,
            "study_id": "STUDY-STYLE-SYNTHETIC",
            "public_study_id": "PS-" + "a" * 32,
            "profile": "general",
            "checklist_hash": self._style_fingerprint("checklist"),
            "protocol_fingerprint": self._style_fingerprint("protocol"),
            "sampling_config_fingerprint": self._style_fingerprint("sampling-config"),
            "semantic_config_fingerprint": self._style_fingerprint("semantic-config"),
            "semantic_evidence_fingerprint": self._style_fingerprint("semantic-evidence"),
            "used_source_set_fingerprint": used_source_set_fingerprint,
            "candidate_bundle_fingerprint": self._style_fingerprint("candidate-bundle"),
            "candidate_artifact_fingerprint": self._style_fingerprint("candidate-artifact"),
            "craft_pack_fingerprint": self._style_fingerprint("craft-pack"),
        }
        receipt["receipt_fingerprint"] = "sha256:" + hashlib.sha256(
            json.dumps(
                receipt,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        return receipt

    def _install_style_completion_fixture(self, receipt: dict[str, object]) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE style_analysis_runs (
                    style_run_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL,
                    protocol_fingerprint TEXT NOT NULL,
                    sampling_config_fingerprint TEXT NOT NULL,
                    semantic_config_fingerprint TEXT NOT NULL,
                    semantic_evidence_fingerprint TEXT,
                    used_source_set_fingerprint TEXT
                );
                CREATE TABLE style_work_steps (
                    style_run_id TEXT NOT NULL,
                    public_work_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    activation_cycle INTEGER,
                    activation_kind TEXT,
                    state TEXT NOT NULL
                );
                CREATE TABLE style_sample_steps (
                    style_run_id TEXT NOT NULL,
                    public_work_id TEXT NOT NULL,
                    source_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO studies(study_id,public_study_id,profile,state,seed,proposal_hash,"
                "checklist_hash) VALUES(?,?,?,'running',?,?,NULL)",
                (
                    receipt["study_id"],
                    receipt["public_study_id"],
                    receipt["profile"],
                    "synthetic-seed",
                    self._style_fingerprint("proposal"),
                ),
            )
            connection.execute(
                "INSERT INTO collections(collection_id,root_path,rights_class,rights_basis,language) "
                "VALUES('COL-STYLE-SYNTHETIC',?,'analysis_only','synthetic fixture','zh-CN')",
                (str(self.root / "style-synthetic"),),
            )
            connection.execute(
                "UPDATE studies SET collection_id='COL-STYLE-SYNTHETIC' WHERE study_id=?",
                (receipt["study_id"],),
            )
            for ordinal, public_work_id in enumerate(
                ("PW-SYNTHETIC-USED", "PW-SYNTHETIC-UNUSED"), 1
            ):
                work_id = f"WORK-STYLE-SYNTHETIC-{ordinal}"
                version_id = f"VERSION-STYLE-SYNTHETIC-{ordinal}"
                connection.execute(
                    "INSERT INTO logical_works(work_id,collection_id,public_work_id,logical_key) "
                    "VALUES(?,'COL-STYLE-SYNTHETIC',?,?)",
                    (work_id, public_work_id, f"style-synthetic-{ordinal}"),
                )
                connection.execute(
                    "INSERT INTO source_versions(version_id,work_id,version_number,sha256,"
                    "media_type,char_count,parse_state) VALUES(?,?,1,?,'txt',1,'ok')",
                    (version_id, work_id, f"{ordinal:064x}"),
                )
                connection.execute(
                    "UPDATE logical_works SET active_version_id=? WHERE work_id=?",
                    (version_id, work_id),
                )
                connection.execute(
                    "INSERT INTO study_works(study_id,work_id,version_id,ordinal,state) "
                    "VALUES(?,?,?,?, 'selected')",
                    (receipt["study_id"], work_id, version_id, ordinal),
                )
            connection.execute(
                "UPDATE studies SET checklist_hash=? WHERE study_id=?",
                (receipt["checklist_hash"], receipt["study_id"]),
            )
            connection.execute(
                "INSERT INTO style_analysis_runs(style_run_id,study_id,protocol_fingerprint,"
                "sampling_config_fingerprint,semantic_config_fingerprint,"
                "semantic_evidence_fingerprint,used_source_set_fingerprint) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    receipt["style_run_id"],
                    receipt["study_id"],
                    receipt["protocol_fingerprint"],
                    receipt["sampling_config_fingerprint"],
                    receipt["semantic_config_fingerprint"],
                    receipt["semantic_evidence_fingerprint"],
                    receipt["used_source_set_fingerprint"],
                ),
            )
            connection.execute(
                "INSERT INTO style_work_steps(style_run_id,public_work_id,ordinal,"
                "activation_cycle,activation_kind,state) VALUES(?,?,1,1,'seed','complete')",
                (receipt["style_run_id"], "PW-SYNTHETIC-USED"),
            )
            connection.execute(
                "INSERT INTO style_work_steps(style_run_id,public_work_id,ordinal,"
                "activation_cycle,activation_kind,state) VALUES(?,?,2,NULL,NULL,'pending')",
                (receipt["style_run_id"], "PW-SYNTHETIC-UNUSED"),
            )
            connection.execute(
                "INSERT INTO style_sample_steps(style_run_id,public_work_id,source_fingerprint,state) "
                "VALUES(?,?,?,'complete')",
                (
                    receipt["style_run_id"], "PW-SYNTHETIC-USED",
                    self._style_fingerprint("source-used"),
                ),
            )
            connection.commit()

    def test_private_metadata_triage_covers_reviewed_boundary_conventions(self) -> None:
        synthetic_pairs = (
            (
                "soushu42_com@雾海时钟_1-39.26 作品作者：Fixture",
                "《雾海时钟》排版40_08_作品作者：Fixture",
            ),
            (
                "云剑航程1~30",
                "雲劍航程（1-30章）作品作者：Fixture",
            ),
            (
                "《星雲歸航》⊙1_卷4（完本）",
                "星云归航_1_1090_作品作者：Fixture",
            ),
        )
        for left, right in synthetic_pairs:
            with self.subTest(left=left, right=right):
                self.assertEqual(
                    _private_title_family(left),
                    _private_title_family(right),
                )

        for title in (
            "成人内容合成标记",
            "R18 synthetic marker",
            "情色合成标记",
            "合成后宫测试",
            "合成双修测试",
            "NTR Synthetic Marker",
            "合成欲望测试",
        ):
            with self.subTest(title=title):
                self.assertNotEqual(_private_profile_signal([title]), "general")

    def test_selection_requires_120_distinct_logical_works_and_freezes_membership(self) -> None:
        self._write_txt_works(STUDY_SIZE, duplicate_last=True)
        first = self.library.scan_collection(self.sources)
        self.assertEqual(first["logical_works"], STUDY_SIZE - 1)
        with self.assertRaises(CorpusLibraryError) as missing_profile:
            self.library.propose_selection(seed="fixed")
        self.assertEqual(missing_profile.exception.code, "study_profile_required")
        insufficient = self.library.propose_selection(seed="fixed", profile="general")
        self.assertEqual(insufficient["status"], "insufficient_eligible_works")
        self.assertEqual(insufficient["eligible"], STUDY_SIZE - 2)
        self.assertEqual(
            insufficient["exclusion_counts"]["alias_identity_conflict"], 1
        )
        self.assertFalse(insufficient["study_created"])

        final_path = self._work_path(STUDY_SIZE - 1)
        final_path.write_text(
            self._general_body(STUDY_SIZE - 1), encoding="utf-8"
        )
        second = self.library.scan_collection(self.sources)
        self.assertEqual(second["logical_works"], STUDY_SIZE)
        proposed = self.library.propose_selection(
            "STUDY-LOCK", seed="fixed", profile="general"
        )
        self.assertEqual(proposed["status"], "proposed")
        self.assertEqual(proposed["profile"], "general")
        self.assertEqual(proposed["work_states"]["pending"], STUDY_SIZE)
        before_private_preview = self.library.selection_private_preview("STUDY-LOCK")
        first_title = before_private_preview["works"][0]["display_label"]
        with closing(sqlite3.connect(self.db_path)) as connection:
            version_id = connection.execute(
                "SELECT version_id FROM study_works WHERE study_id=? AND ordinal=1",
                ("STUDY-LOCK",),
            ).fetchone()[0]
            connection.execute(
                "UPDATE source_versions SET private_metadata_json=? WHERE version_id=?",
                (json.dumps({"title": first_title, "creator": "Local Creator"}), version_id),
            )
            connection.commit()
        private_preview = self.library.selection_private_preview("STUDY-LOCK")
        self.assertTrue(private_preview["private_local_only"])
        self.assertFalse(private_preview["redistributable"])
        self.assertFalse(private_preview["raw_text_included"])
        self.assertEqual(private_preview["work_count"], STUDY_SIZE)
        self.assertEqual(private_preview["works"][0]["display_label"], first_title)
        self.assertEqual(private_preview["works"][0]["creator"], "Local Creator")
        self.assertTrue(private_preview["works"][0]["relative_locator"].endswith(".txt"))
        self.assertNotIn("creator", proposed["works"][0])
        with self.assertRaises(CorpusLibraryError) as missing_hash:
            self.library.confirm_selection("STUDY-LOCK")
        self.assertEqual(
            missing_hash.exception.code, "selection_confirmation_hash_required"
        )
        with self.assertRaises(CorpusLibraryError) as wrong_hash:
            self.library.confirm_selection(
                "STUDY-LOCK", expected_hash="sha256:" + "0" * 64
            )
        self.assertEqual(wrong_hash.exception.code, "selection_hash_mismatch")
        self.assertEqual(
            self.library.study_status("STUDY-LOCK")["status"], "proposed"
        )
        confirmed = self.library.confirm_selection(
            "STUDY-LOCK", expected_hash=proposed["proposal_hash"]
        )
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertTrue(confirmed["checklist_locked"])
        self.assertEqual(confirmed["work_states"]["selected"], STUDY_SIZE)
        replay = self.library.confirm_selection(
            "STUDY-LOCK", expected_hash=confirmed["checklist_hash"]
        )
        self.assertEqual(replay["checklist_hash"], confirmed["checklist_hash"])

        with closing(sqlite3.connect(self.db_path)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE studies SET checklist_hash=? WHERE study_id=?",
                    ("sha256:" + "0" * 64, confirmed["study_id"]),
                )
        with closing(sqlite3.connect(self.db_path)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE studies SET profile='adult_explicit' WHERE study_id=?",
                    (confirmed["study_id"],),
                )

    def test_unconfirmed_proposal_refresh_preserves_v5_identity_and_rebinds_hash(self) -> None:
        self._write_txt_works(STUDY_SIZE + 1)
        scan = self.library.scan_collection(
            self.sources, collection_id="COL-REFRESH-V5"
        )
        proposed = self.library.propose_selection(
            "STUDY-GENERAL-QUALITY-REBUILD-V5",
            collection_id=scan["collection_id"],
            seed="same-v5-seed",
            profile="general",
        )
        old_ids = [row["public_work_id"] for row in proposed["works"]]
        preview = self.library.selection_private_preview(proposed["study_id"])
        removed = self.sources / PurePosixPath(preview["works"][0]["relative_locator"])
        removed.unlink()
        self.library.scan_collection(self.sources, collection_id=scan["collection_id"])

        with self.assertRaises(CorpusLibraryError) as stale:
            self.library.refresh_proposed_selection(
                proposed["study_id"], expected_proposal_hash="sha256:" + "0" * 64
            )
        self.assertEqual(stale.exception.code, "selection_refresh_hash_mismatch")

        refreshed = self.library.refresh_proposed_selection(
            proposed["study_id"], expected_proposal_hash=proposed["proposal_hash"]
        )
        self.assertEqual(refreshed["study_id"], proposed["study_id"])
        self.assertEqual(refreshed["public_study_id"], proposed["public_study_id"])
        self.assertEqual(refreshed["profile"], "general")
        self.assertEqual(refreshed["status"], "proposed")
        self.assertTrue(refreshed["identity_preserved"])
        self.assertTrue(refreshed["membership_changed"])
        self.assertEqual(refreshed["previous_proposal_hash"], proposed["proposal_hash"])
        self.assertNotEqual(refreshed["proposal_hash"], proposed["proposal_hash"])
        self.assertNotEqual(
            [row["public_work_id"] for row in refreshed["works"]], old_ids
        )

        confirmed = self.library.confirm_selection(
            refreshed["study_id"], expected_hash=refreshed["proposal_hash"]
        )
        with self.assertRaises(CorpusLibraryError) as locked:
            self.library.refresh_proposed_selection(
                confirmed["study_id"], expected_proposal_hash=confirmed["checklist_hash"]
            )
        self.assertEqual(
            locked.exception.code, "selection_refresh_requires_unconfirmed_proposal"
        )

    def test_exact_byte_alias_rescan_keeps_canonical_private_metadata_stable(self) -> None:
        body = self._general_body(42)
        canonical = self.sources / "a-original-title.txt"
        alias = self.sources / "z-copy-title.txt"
        canonical.write_text(body, encoding="utf-8")
        alias.write_text(body, encoding="utf-8")

        first = self.library.scan_collection(self.sources, collection_id="COL-ALIASES")
        self.assertEqual(first["logical_works"], 1)
        self.assertEqual(first["new_versions"], 1)
        with closing(sqlite3.connect(self.db_path)) as connection:
            metadata_before = connection.execute(
                "SELECT private_metadata_json FROM source_versions"
            ).fetchone()[0]
            locators = connection.execute(
                "SELECT relative_path,work_id,version_id FROM source_files "
                "ORDER BY relative_path"
            ).fetchall()

        second = self.library.scan_collection(self.sources, collection_id="COL-ALIASES")
        self.assertEqual(second["logical_works"], 1)
        self.assertEqual(second["new_versions"], 0)
        self.assertEqual(second["refreshed_versions"], 0)
        self.assertEqual(second["invalidated_studies"], 0)
        self.assertEqual(len(locators), 2)
        self.assertEqual({row[1] for row in locators}, {locators[0][1]})
        self.assertEqual({row[2] for row in locators}, {locators[0][2]})
        with closing(sqlite3.connect(self.db_path)) as connection:
            metadata_after = connection.execute(
                "SELECT private_metadata_json FROM source_versions"
            ).fetchone()[0]
        self.assertEqual(metadata_after, metadata_before)
        self.assertEqual(json.loads(metadata_after)["title"], canonical.stem)

    def test_confirmation_recomputes_the_ordered_membership_hash(self) -> None:
        self._write_txt_works(STUDY_SIZE + 1, chars=500)
        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-MEMBERSHIP-HASH"
            )
            proposal = self.library.propose_selection(
                "STUDY-MEMBERSHIP-HASH",
                collection_id=scan["collection_id"],
                seed="membership-hash",
                profile="general",
            )
        with closing(sqlite3.connect(self.db_path)) as connection:
            replacement = connection.execute(
                "SELECT w.work_id,w.active_version_id FROM logical_works w "
                "WHERE NOT EXISTS(SELECT 1 FROM study_works sw "
                "WHERE sw.study_id=? AND sw.work_id=w.work_id)",
                (proposal["study_id"],),
            ).fetchone()
            self.assertIsNotNone(replacement)
            connection.execute(
                "UPDATE study_works SET work_id=?,version_id=? "
                "WHERE study_id=? AND ordinal=1",
                (
                    replacement[0],
                    replacement[1],
                    proposal["study_id"],
                ),
            )
            connection.commit()

        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            with self.assertRaises(CorpusLibraryError) as caught:
                self.library.confirm_selection(
                    proposal["study_id"], expected_hash=proposal["proposal_hash"]
                )
        self.assertEqual(caught.exception.code, "selection_membership_hash_changed")
        status = self.library.study_status(proposal["study_id"])
        self.assertEqual(status["status"], "invalidated")
        self.assertEqual(
            status["invalidation_reason"], "selection_membership_hash_changed"
        )
        self.assertIsNone(status["checklist_hash"])
        self.assertEqual(status["proposal_hash"], proposal["proposal_hash"])

    def test_confirmation_replays_seeded_top_120_and_detects_pool_drift(self) -> None:
        self._write_txt_works(STUDY_SIZE, chars=500)
        late_path = self.sources / "late-eligible-story.txt"
        late_path.write_text(self._general_body(999, chars=99), encoding="utf-8")
        with patch("corpus.library.GENERAL_MIN_CHARS", 100):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-POOL-DRIFT"
            )
            with closing(sqlite3.connect(self.db_path)) as connection:
                ids = connection.execute(
                    "SELECT w.public_work_id,f.relative_path FROM logical_works w "
                    "JOIN source_files f ON f.work_id=w.work_id "
                    "WHERE f.collection_id=?",
                    (scan["collection_id"],),
                ).fetchall()
            late_id = next(row[0] for row in ids if row[1] == late_path.name)
            eligible_ids = [row[0] for row in ids if row[1] != late_path.name]
            seed = next(
                str(candidate)
                for candidate in range(100_000)
                if hashlib.sha256(
                    (str(candidate) + "\0" + late_id).encode("utf-8")
                ).digest()
                < min(
                    hashlib.sha256(
                        (str(candidate) + "\0" + public_id).encode("utf-8")
                    ).digest()
                    for public_id in eligible_ids
                )
            )
            proposal = self.library.propose_selection(
                "STUDY-POOL-DRIFT",
                collection_id=scan["collection_id"],
                seed=seed,
                profile="general",
            )
            late_path.write_text(
                self._general_body(999, chars=600), encoding="utf-8"
            )
            rescan = self.library.scan_collection(
                self.sources, collection_id="COL-POOL-DRIFT"
            )
            self.assertEqual(rescan["invalidated_studies"], 0)
            with self.assertRaises(CorpusLibraryError) as caught:
                self.library.confirm_selection(
                    proposal["study_id"], expected_hash=proposal["proposal_hash"]
                )
        self.assertEqual(caught.exception.code, "selection_pool_changed")
        self.assertEqual(
            self.library.study_status(proposal["study_id"])["invalidation_reason"],
            "selection_pool_changed",
        )

    def test_confirmation_allows_a_new_candidate_ranked_after_top_120(self) -> None:
        self._write_txt_works(STUDY_SIZE, chars=500)
        late_path = self.sources / "late-rank-121-story.txt"
        late_path.write_text(self._general_body(998, chars=99), encoding="utf-8")
        with patch("corpus.library.GENERAL_MIN_CHARS", 100):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-RANK-121"
            )
            with closing(sqlite3.connect(self.db_path)) as connection:
                ids = connection.execute(
                    "SELECT w.public_work_id,f.relative_path FROM logical_works w "
                    "JOIN source_files f ON f.work_id=w.work_id "
                    "WHERE f.collection_id=?",
                    (scan["collection_id"],),
                ).fetchall()
            late_id = next(row[0] for row in ids if row[1] == late_path.name)
            eligible_ids = [row[0] for row in ids if row[1] != late_path.name]
            seed = next(
                str(candidate)
                for candidate in range(100_000)
                if hashlib.sha256(
                    (str(candidate) + "\0" + late_id).encode("utf-8")
                ).digest()
                > max(
                    hashlib.sha256(
                        (str(candidate) + "\0" + public_id).encode("utf-8")
                    ).digest()
                    for public_id in eligible_ids
                )
            )
            proposal = self.library.propose_selection(
                "STUDY-RANK-121",
                collection_id=scan["collection_id"],
                seed=seed,
                profile="general",
            )
            late_path.write_text(
                self._general_body(998, chars=600), encoding="utf-8"
            )
            self.library.scan_collection(
                self.sources, collection_id="COL-RANK-121"
            )
            confirmed = self.library.confirm_selection(
                proposal["study_id"], expected_hash=proposal["proposal_hash"]
            )
        self.assertEqual(confirmed["status"], "confirmed")

    def test_all_available_alias_locators_drive_identity_risk_and_preview(self) -> None:
        for index in range(STUDY_SIZE):
            (self.sources / f"Neutral Alias Fixture {self._alpha_token(index)}.txt").write_text(
                self._general_body(index, chars=500), encoding="utf-8"
            )
        for index in range(STUDY_SIZE - 1):
            (self.sources / f"R18 Adult Alias Fixture {self._alpha_token(index)}.txt").write_text(
                f"adult fixture {index}", encoding="utf-8"
            )

        adult_body = "same adult alias bytes"
        adult_clean = self.sources / "a-《Alias Adult Work》clean-copy.txt"
        adult_r18 = self.sources / "b-《Alias Adult Work》R18-explicit-copy.txt"
        adult_clean.write_text(adult_body, encoding="utf-8")
        adult_r18.write_text(adult_body, encoding="utf-8")

        conflict_body = "same conflicting identity bytes"
        (self.sources / "Alias Identity Alpha.txt").write_text(
            conflict_body, encoding="utf-8"
        )
        (self.sources / "Alias Identity Beta.txt").write_text(
            conflict_body, encoding="utf-8"
        )

        derivative_body = "same derivative alias bytes"
        (self.sources / "《Alias Derivative Work》clean.txt").write_text(
            derivative_body, encoding="utf-8"
        )
        (self.sources / "《Alias Derivative Work》加料续改.txt").write_text(
            derivative_body, encoding="utf-8"
        )

        creator_body = "same creator alias bytes"
        (self.sources / "《Alias Creator Work》作者：Alice.txt").write_text(
            creator_body, encoding="utf-8"
        )
        (self.sources / "《Alias Creator Work》作者：Bob.txt").write_text(
            creator_body, encoding="utf-8"
        )

        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-ALL-ALIASES"
            )
            general = self.library.propose_selection(
                "STUDY-ALL-ALIASES-GENERAL",
                collection_id=scan["collection_id"],
                seed="general-aliases",
                profile="general",
            )
            adult = self.library.propose_selection(
                "STUDY-ALL-ALIASES-ADULT",
                collection_id=scan["collection_id"],
                seed="adult-aliases",
                profile="adult_explicit",
            )
            self.assertEqual(general["status"], "proposed")
            self.assertEqual(adult["status"], "proposed")
            for proposal in (general, adult):
                self.assertEqual(
                    proposal["exclusion_counts"]["alias_identity_conflict"], 1
                )
                self.assertEqual(
                    proposal["exclusion_counts"]["derivative_ambiguous"], 1
                )
                self.assertEqual(
                    proposal["exclusion_counts"]["creator_conflict_ambiguous"], 1
                )

            private_before = self.library.selection_private_preview(adult["study_id"])
            alias_before = next(
                work for work in private_before["works"]
                if "Alias Adult Work" in work["display_label"]
            )
            self.assertEqual(alias_before["display_label"], adult_clean.stem)

            adult_clean.unlink()
            rescan = self.library.scan_collection(
                self.sources, collection_id="COL-ALL-ALIASES"
            )
            self.assertEqual(rescan["invalidated_studies"], 0)
            private_after = self.library.selection_private_preview(adult["study_id"])
            alias_after = next(
                work for work in private_after["works"]
                if "Alias Adult Work" in work["display_label"]
            )
            self.assertEqual(alias_after["display_label"], adult_r18.stem)
            self.assertEqual(alias_after["relative_locator"], adult_r18.name)
            confirmed = self.library.confirm_selection(
                adult["study_id"], expected_hash=adult["proposal_hash"]
            )
        self.assertEqual(confirmed["status"], "confirmed")

    def test_transient_windows_and_range_receipts_never_persist_passages(self) -> None:
        self._write_txt_works(STUDY_SIZE)
        _scan, confirmed = self._confirmed()
        public_work_id = confirmed["works"][0]["public_work_id"]

        windows = self.library.materialize_windows(
            confirmed["study_id"], public_work_id
        )
        self.assertEqual(windows["window_count"], 3)
        self.assertLessEqual(windows["total_chars"], 4_000)
        self.assertFalse(windows["persisted"])
        self.assertEqual(
            [window["scope"] for window in windows["windows"]],
            ["opening", "middle", "closing"],
        )

        batch = self.library.prepare_ranges(
            confirmed["study_id"], public_work_id,
            rubric={"rubric_id": "narrative_craft_v1", "causal_weight": 3},
        )
        self.assertEqual(batch["range_count"], 3)
        receipt_keys = set().union(*(receipt.keys() for receipt in batch["ranges"]))
        self.assertNotIn("passage", receipt_keys)
        self.assertNotIn("text", receipt_keys)
        self.assertNotIn("content", receipt_keys)
        range_id = batch["ranges"][0]["range_id"]
        ephemeral = self.library.materialize_range(range_id)
        self.assertLessEqual(ephemeral["char_count"], 4_000)
        self.assertFalse(ephemeral["persisted"])

        leaked_marker = re.search(r"supersecretmarker\d+", ephemeral["passage"])
        self.assertIsNotNone(leaked_marker)
        with self.assertRaises(CorpusLibraryError) as caught:
            self.library.complete_range(
                range_id,
                {"label": leaked_marker.group(0)},
            )
        self.assertEqual(caught.exception.code, "judgment_source_overlap")

        with self.assertRaises(CorpusLibraryError) as embedded_quote:
            self.library.complete_range(
                range_id,
                {
                    "mechanism": (
                        "abstract setup before "
                        + leaked_marker.group(0)[:12]
                        + " followed by unrelated analysis"
                    )
                },
            )
        self.assertEqual(embedded_quote.exception.code, "judgment_source_overlap")

        receipt = self.library.complete_range(
            range_id,
            {
                "confidence": 0.8,
                "decision": "pass",
                "mechanisms": [
                    {
                        "mechanism": "causal pressure increases through delayed consequences",
                        "observed_effect": "the next decision remains legible without a fixed beat quota",
                    }
                ],
            },
        )
        self.assertEqual(receipt["status"], "complete")
        self.assertNotIn("judgment", receipt)
        self.assertNotIn("passage", receipt)

        # Raw prose and the sentinel must not occur in any SQLite page/WAL.
        with closing(sqlite3.connect(self.db_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(range_jobs)")
            }
            self.assertFalse({"passage", "text", "content", "excerpt"} & columns)
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        database_bytes = self.db_path.read_bytes()
        self.assertNotIn("supersecretmarker000".encode("utf-8"), database_bytes)
        self.assertNotIn(ephemeral["passage"].encode("utf-8"), database_bytes)

    def test_profile_pool_deduplicates_title_families_and_reports_only_counts(self) -> None:
        for index in range(STUDY_SIZE):
            token = self._alpha_token(index)
            (self.sources / f"General Craft Story {token}.txt").write_text(
                self._general_body(index), encoding="utf-8"
            )
            (self.sources / f"R18 Explicit Story {token}.txt").write_text(
                f"synthetic adult-profile fixture {index} " * 20, encoding="utf-8"
            )
        (self.sources / "《General Craft Story aaaa》01_200连载_作者：Fixture.txt").write_text(
            self._general_body(500, chars=110_000), encoding="utf-8"
        )
        ambiguous_labels = (
            "NTR Ambiguous Story",
            "Synthetic 后宫 Boundary",
            "Synthetic 双修 Boundary",
            "Synthetic 欲望 Boundary",
            "Synthetic XP Boundary",
        )
        for offset, ambiguous_label in enumerate(ambiguous_labels):
            (self.sources / f"{ambiguous_label}.txt").write_text(
                self._general_body(501 + offset), encoding="utf-8"
            )
        (self.sources / "export_20260101_010101.txt").write_text(
            self._general_body(600), encoding="utf-8"
        )
        (self.sources / "Short General Story.txt").write_text(
            self._general_body(601, chars=99_999), encoding="utf-8"
        )
        derivative_labels = (
            "《General Craft Story aaab》AI续写_作品作者：Derivative",
            "《General Craft Story aaac》加料版_作品作者：Derivative",
            "《General Craft Story aaad》衍生版_作品作者：Derivative",
        )
        for offset, derivative_label in enumerate(derivative_labels):
            (self.sources / f"{derivative_label}.txt").write_text(
                self._general_body(700 + offset, chars=150_000), encoding="utf-8"
            )

        scan = self.library.scan_collection(self.sources, collection_id="COL-PROFILES")
        general = self.library.propose_selection(
            "STUDY-GENERAL-PROFILE",
            collection_id=scan["collection_id"],
            seed="fixed",
            profile="general",
        )
        adult = self.library.propose_selection(
            "STUDY-ADULT-PROFILE",
            collection_id=scan["collection_id"],
            seed="fixed",
            profile="adult_explicit",
        )

        self.assertEqual(general["status"], "proposed")
        self.assertEqual(adult["status"], "proposed")
        self.assertEqual(general["work_count"], STUDY_SIZE)
        self.assertEqual(adult["work_count"], STUDY_SIZE)
        self.assertTrue(
            set(work["public_work_id"] for work in general["works"]).isdisjoint(
                work["public_work_id"] for work in adult["works"]
            )
        )
        self.assertEqual(general["exclusion_counts"]["logical_family_alternate"], 1)
        self.assertEqual(
            general["exclusion_counts"]["strong_adult_profile_mismatch"], STUDY_SIZE
        )
        self.assertEqual(
            general["exclusion_counts"]["ambiguous_profile"],
            len(ambiguous_labels),
        )
        self.assertEqual(general["exclusion_counts"]["identity_unknown"], 1)
        self.assertEqual(general["exclusion_counts"]["below_minimum_chars"], 1)
        self.assertEqual(general["exclusion_counts"]["derivative_ambiguous"], 3)
        self.assertEqual(
            adult["exclusion_counts"]["not_strong_adult_profile_mismatch"],
            STUDY_SIZE + 2,
        )
        self.assertEqual(
            adult["exclusion_counts"]["ambiguous_profile"],
            len(ambiguous_labels),
        )
        self.assertEqual(adult["exclusion_counts"]["identity_unknown"], 1)
        self.assertEqual(adult["exclusion_counts"]["below_minimum_chars"], 0)
        self.assertEqual(adult["exclusion_counts"]["derivative_ambiguous"], 3)
        private = self.library.selection_private_preview(general["study_id"])
        labels = {work["display_label"] for work in private["works"]}
        self.assertIn("《General Craft Story aaaa》01_200连载_作者：Fixture", labels)
        self.assertNotIn("General Craft Story aaaa", labels)
        self.assertTrue(labels.isdisjoint(derivative_labels))
        serialized = json.dumps(general, ensure_ascii=False)
        self.assertNotIn("General Craft Story", serialized)
        self.assertNotIn("R18 Explicit Story", serialized)

    def test_body_and_appearance_descriptors_remain_general_profile_signals(self) -> None:
        appearance_labels = (
            "巨乳剑士的旅程",
            "爆乳护卫的辉煌",
            "丰乳美人图",
            "肥臀舞者纪事",
            "身材描写手记",
            "容貌与服饰美学",
        )
        for index, label in enumerate(appearance_labels):
            (self.sources / f"{label}.txt").write_text(
                self._general_body(index, chars=500), encoding="utf-8"
            )
        (self.sources / "乳交露骨情节.txt").write_text(
            self._general_body(999, chars=500), encoding="utf-8"
        )

        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-APPEARANCE-SIGNALS"
            )
            with self.library._connect() as connection:
                general, general_exclusions = self.library._selection_pool(
                    connection, scan["collection_id"], "general"
                )
                adult, adult_exclusions = self.library._selection_pool(
                    connection, scan["collection_id"], "adult_explicit"
                )

        self.assertEqual(len(general), len(appearance_labels))
        self.assertEqual(len(adult), 1)
        self.assertEqual(general_exclusions["strong_adult_profile_mismatch"], 1)
        self.assertEqual(
            adult_exclusions["not_strong_adult_profile_mismatch"],
            len(appearance_labels),
        )

    def test_all_bound_txt_style_sampling_streams_below_legacy_threshold(self) -> None:
        self._write_txt_works(STUDY_SIZE, chars=2_400)
        target = self._work_path(0)
        body_line = (
            "“今天出发。”她说，随后整理宽外套。"
            "镜中的她留着长发，身材丰满，巨乳只是人物外貌的一部分。"
        )
        source_text = (
            "第一章\n"
            + "\n\n".join(f"{body_line} 这是第{index}段的合成行动。" for index in range(24))
            + "\n尾声\n她们彼此信任，最后一起回家。\n"
        )
        # Exercise the streaming decoder fallback as well as the all-TXT route.
        target.write_text(source_text, encoding="gb18030", newline="\n")
        normalized_text = source_text.strip()
        self.assertLess(len(normalized_text), STYLE_IN_MEMORY_SOURCE_CHARS)

        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-STYLE-STREAM-SMALL"
            )
            proposed = self.library.propose_selection(
                "STUDY-STYLE-STREAM-SMALL",
                collection_id=scan["collection_id"],
                seed="style-stream-small-seed",
                profile="general",
            )
            confirmed = self.library.confirm_selection(
                proposed["study_id"], expected_hash=proposed["proposal_hash"]
            )
        preview = self.library.selection_private_preview(confirmed["study_id"])
        public_work_id = next(
            work["public_work_id"]
            for work in preview["works"]
            if work["relative_locator"] == target.name
        )
        roles = ("dialogue", "body_appearance", "ending")
        expected = sample_style_windows(
            normalized_text,
            source_fingerprint=fingerprint_source_text(normalized_text),
            requested_roles=roles,
            max_windows=4,
            max_window_chars=1_800,
            candidate_filter=style_window_passes_hygiene,
        )

        with patch.object(
            self.library,
            "_read_stable_bytes",
            side_effect=AssertionError("every TXT style path must stream"),
        ):
            started = self.library.start_study(confirmed["study_id"])
            self.assertEqual(started["status"], "running")
            first = self.library.sample_style_work(
                confirmed["study_id"],
                public_work_id,
                requested_roles=roles,
                max_windows=4,
            )
            second = self.library.sample_style_work(
                confirmed["study_id"],
                public_work_id,
                requested_roles=roles,
                max_windows=4,
                prior_manifest=first["manifest"],
            )
            window = first["manifest"]["windows"][0]
            descriptor = {
                **window,
                "source_fingerprint": first["decoded_text_fingerprint"],
                "upstream_source_fingerprint": first["upstream_source_fingerprint"],
            }
            materialized = self.library.materialize_style_window(
                confirmed["study_id"], public_work_id, descriptor
            )

        validate_sampling_manifest(first["manifest"])
        self.assertEqual(first["manifest"], expected["manifest"])
        self.assertEqual(first["ephemeral_windows"], expected["ephemeral_windows"])
        self.assertEqual(second["manifest"]["sampling_round"], 2)
        self.assertTrue(
            any("巨乳" in item["text"] for item in first["ephemeral_windows"])
        )
        expected_passage = next(
            item["text"]
            for item in first["ephemeral_windows"]
            if item["window_id"] == window["window_id"]
        )
        self.assertEqual(materialized["passage"], expected_passage)
        self.assertEqual(
            materialized["passage_fingerprint"], window["passage_fingerprint"]
        )

    def test_small_epub_keeps_memory_style_path_and_oversize_fails_typed(self) -> None:
        self._write_txt_works(STUDY_SIZE - 1, chars=2_400)
        target = self.sources / "owned-style.epub"
        self._write_epub(target, title="Owned Style Fixture")
        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-STYLE-EPUB-PATH"
            )
            proposed = self.library.propose_selection(
                "STUDY-STYLE-EPUB-PATH",
                collection_id=scan["collection_id"],
                seed="style-epub-path-seed",
                profile="general",
            )
            confirmed = self.library.confirm_selection(
                proposed["study_id"], expected_hash=proposed["proposal_hash"]
            )
        preview = self.library.selection_private_preview(confirmed["study_id"])
        public_work_id = next(
            work["public_work_id"]
            for work in preview["works"]
            if work["relative_locator"] == target.name
        )
        self.library.start_study(confirmed["study_id"])

        with patch.object(
            self.library,
            "_read_stable_bytes",
            wraps=self.library._read_stable_bytes,
        ) as whole_read:
            sampled = self.library.sample_style_work(
                confirmed["study_id"],
                public_work_id,
                requested_roles=("opening",),
                max_windows=1,
            )
            window = sampled["manifest"]["windows"][0]
            descriptor = {
                **window,
                "source_fingerprint": sampled["decoded_text_fingerprint"],
                "upstream_source_fingerprint": sampled["upstream_source_fingerprint"],
            }
            materialized = self.library.materialize_style_window(
                confirmed["study_id"], public_work_id, descriptor
            )
        self.assertGreaterEqual(whole_read.call_count, 2)
        self.assertEqual(materialized["passage_fingerprint"], window["passage_fingerprint"])

        with self.library._connect() as connection:
            connection.execute(
                "UPDATE source_versions SET char_count=? WHERE version_id=("
                "SELECT sw.version_id FROM study_works sw JOIN logical_works w "
                "ON w.work_id=sw.work_id WHERE sw.study_id=? AND w.public_work_id=?"
                ")",
                (
                    STYLE_IN_MEMORY_SOURCE_CHARS + 1,
                    confirmed["study_id"],
                    public_work_id,
                ),
            )
            connection.commit()
        with self.assertRaises(CorpusLibraryError) as sample_error:
            self.library.sample_style_work(
                confirmed["study_id"],
                public_work_id,
                requested_roles=("opening",),
                max_windows=1,
            )
        self.assertEqual(sample_error.exception.code, "style_large_source_type_unsupported")
        with self.assertRaises(CorpusLibraryError) as materialize_error:
            self.library.materialize_style_window(
                confirmed["study_id"], public_work_id, descriptor
            )
        self.assertEqual(
            materialize_error.exception.code, "style_large_source_type_unsupported"
        )

    def test_large_bound_txt_style_sampling_and_materialization_never_use_full_read(self) -> None:
        self._write_txt_works(STUDY_SIZE, chars=2_400)
        target = self._work_path(0)
        clean_paragraph = (
            "“干净的合成对话。”朋友说，她想起过去，随后转身跑过雨中的街道。"
            "镜中的人留着长发，身材丰满，巨乳被宽外套遮住。"
            + "这是完全合成的节奏填充句。" * 100
        )
        clean_chapter = "Chapter 1\n" + clean_paragraph + "\n"
        repetitions = 8_000_200 // len(clean_chapter) + 1
        target.write_text(
            "第一章\n"
            "站点残留 https://fiction.invalid.example/read 点击下一页。\n***\n"
            + clean_chapter * repetitions
            + "尾声\n她们彼此信任，最后一起回家。\n",
            encoding="utf-8",
            newline="\n",
        )
        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-STYLE-STREAM"
            )
            proposed = self.library.propose_selection(
                "STUDY-STYLE-STREAM",
                collection_id=scan["collection_id"],
                seed="style-stream-seed",
                profile="general",
            )
            confirmed = self.library.confirm_selection(
                proposed["study_id"], expected_hash=proposed["proposal_hash"]
            )
        preview = self.library.selection_private_preview(confirmed["study_id"])
        public_work_id = next(
            work["public_work_id"]
            for work in preview["works"]
            if work["relative_locator"] == target.name
        )

        with (
            patch.object(
                self.library,
                "_read_stable_bytes",
                side_effect=AssertionError("large style path must not read a whole source"),
            ),
        ):
            started = self.library.start_study(confirmed["study_id"])
            self.assertEqual(started["status"], "running")
            first = self.library.sample_style_work(
                confirmed["study_id"],
                public_work_id,
                requested_roles=("dialogue", "body_appearance", "ending"),
                max_windows=4,
            )
            second = self.library.sample_style_work(
                confirmed["study_id"],
                public_work_id,
                requested_roles=("dialogue", "body_appearance", "ending"),
                max_windows=4,
                prior_manifest=first["manifest"],
            )
            self.assertEqual(second["manifest"]["sampling_round"], 2)
            window = first["manifest"]["windows"][0]
            descriptor = {
                **window,
                "source_fingerprint": first["decoded_text_fingerprint"],
                "upstream_source_fingerprint": first["upstream_source_fingerprint"],
            }
            materialized = self.library.materialize_style_window(
                confirmed["study_id"], public_work_id, descriptor
            )

        self.assertEqual(
            materialized["passage_fingerprint"], window["passage_fingerprint"]
        )
        self.assertNotIn("https://", materialized["passage"])
        self.assertFalse(first["passages_persisted"])
        self.assertNotIn("干净的合成对话".encode("utf-8"), self.db_path.read_bytes())

    def test_confirmation_revalidates_private_family_and_profile(self) -> None:
        self._write_txt_works(STUDY_SIZE, chars=500)
        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(self.sources, collection_id="COL-REVALIDATE")
            family_proposal = self.library.propose_selection(
                "STUDY-FAMILY-REVALIDATE",
                collection_id=scan["collection_id"],
                seed="family",
                profile="general",
            )
            family_private = self.library.selection_private_preview(family_proposal["study_id"])
            replaced_family = family_private["works"][0]["display_label"]
            (self.sources / f"《{replaced_family}》01_200连载.txt").write_text(
                self._general_body(999, chars=800), encoding="utf-8"
            )
            self.library.scan_collection(self.sources, collection_id="COL-REVALIDATE")
            with self.assertRaises(CorpusLibraryError) as family_error:
                self.library.confirm_selection(
                    family_proposal["study_id"],
                    expected_hash=family_proposal["proposal_hash"],
                )
            self.assertEqual(family_error.exception.code, "selection_pool_changed")
            self.assertEqual(
                self.library.study_status(family_proposal["study_id"])["status"],
                "invalidated",
            )

        # A fresh ledger isolates the profile-change check from the duplicate
        # family deliberately introduced above.
        other_root = self.root / "profile-revalidation"
        other_sources = other_root / "sources"
        other_sources.mkdir(parents=True)
        other_library = CorpusLibrary(other_root / "corpus.sqlite", other_root / "public")
        for index in range(STUDY_SIZE):
            (other_sources / f"Neutral Story {self._alpha_token(index)}.txt").write_text(
                self._general_body(index, chars=500), encoding="utf-8"
            )
        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = other_library.scan_collection(other_sources, collection_id="COL-PROFILE-CHECK")
            profile_proposal = other_library.propose_selection(
                "STUDY-PROFILE-REVALIDATE",
                collection_id=scan["collection_id"],
                seed="profile",
                profile="general",
            )
            profile_private = other_library.selection_private_preview(
                profile_proposal["study_id"]
            )
            old_locator = profile_private["works"][0]["relative_locator"]
            old_path = other_sources / PurePosixPath(old_locator)
            old_path.rename(
                other_sources
                / f"《{old_path.stem}》R18-explicit-reclassified.txt"
            )
            other_library.scan_collection(
                other_sources, collection_id="COL-PROFILE-CHECK"
            )
            with self.assertRaises(CorpusLibraryError) as profile_error:
                other_library.confirm_selection(
                    profile_proposal["study_id"],
                    expected_hash=profile_proposal["proposal_hash"],
                )
            self.assertEqual(profile_error.exception.code, "selection_pool_changed")
            self.assertEqual(
                other_library.study_status(profile_proposal["study_id"])["status"],
                "invalidated",
            )

    def test_derivative_editions_are_quarantined_and_creator_conflicts_exclude_family(self) -> None:
        for index in range(STUDY_SIZE):
            (self.sources / f"Neutral Story {self._alpha_token(index)}.txt").write_text(
                self._general_body(index, chars=500), encoding="utf-8"
            )
        derivative_markers = (
            "AI续写",
            "加料版",
            "续写",
            "续改",
            "同人文",
            "同人整合",
            "二改",
            "改写",
            "修改版",
            "重置",
            "衔接",
            "和谐章节",
        )
        derivative_labels: list[str] = []
        for index, marker in enumerate(derivative_markers):
            label = f"《Neutral Story {self._alpha_token(index)}》{marker}_作者：Derivative"
            derivative_labels.append(label)
            (self.sources / f"{label}.txt").write_text(
                self._general_body(500 + index, chars=2_000), encoding="utf-8"
            )
        safe_token = self._alpha_token(20)
        safe_labels = (
            f"《Neutral Story {safe_token}》番外_作者：SameCreator",
            f"《Neutral Story {safe_token}》插图版_作者：SameCreator",
            f"《Neutral Story {safe_token}》校对版_作者：SameCreator",
        )
        for offset, label in enumerate(safe_labels, 1):
            (self.sources / f"{label}.txt").write_text(
                self._general_body(600 + offset, chars=1_000 + offset * 100),
                encoding="utf-8",
            )
        creator_conflict_labels = (
            "《Creator Conflict Story》01_100连载_作者：Alice",
            "Creator Conflict Story - by Bob",
        )
        for offset, label in enumerate(creator_conflict_labels):
            (self.sources / f"{label}.txt").write_text(
                self._general_body(700 + offset, chars=800 + offset * 100),
                encoding="utf-8",
            )

        with patch("corpus.library.GENERAL_MIN_CHARS", 1):
            scan = self.library.scan_collection(
                self.sources, collection_id="COL-DERIVATIVE-CREATOR"
            )
            proposal = self.library.propose_selection(
                "STUDY-DERIVATIVE-CREATOR",
                collection_id=scan["collection_id"],
                seed="derivative",
                profile="general",
            )
        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(
            proposal["exclusion_counts"]["derivative_ambiguous"],
            len(derivative_markers),
        )
        self.assertEqual(
            proposal["exclusion_counts"]["creator_conflict_ambiguous"], 2
        )
        self.assertEqual(proposal["exclusion_counts"]["logical_family_alternate"], 3)
        private = self.library.selection_private_preview(proposal["study_id"])
        selected_labels = {work["display_label"] for work in private["works"]}
        self.assertTrue(set(derivative_labels).isdisjoint(selected_labels))
        self.assertTrue(set(creator_conflict_labels).isdisjoint(selected_labels))
        self.assertIn(safe_labels[-1], selected_labels)

    def test_style_completion_receipt_binds_ai_native_semantic_evidence_immutably(self) -> None:
        receipt = self._style_completion_fixture()
        self._install_style_completion_fixture(receipt)

        recorded = self.library.record_style_completion(**receipt)

        self.assertEqual(
            recorded["semantic_config_fingerprint"],
            receipt["semantic_config_fingerprint"],
        )
        self.assertEqual(
            recorded["semantic_evidence_fingerprint"],
            receipt["semantic_evidence_fingerprint"],
        )
        self.assertEqual(
            recorded["used_source_set_fingerprint"],
            receipt["used_source_set_fingerprint"],
        )
        with closing(sqlite3.connect(self.db_path)) as connection:
            stored = connection.execute(
                "SELECT semantic_config_fingerprint,semantic_evidence_fingerprint,"
                "used_source_set_fingerprint,state "
                "FROM style_completion_receipts WHERE style_run_id=?",
                (receipt["style_run_id"],),
            ).fetchone()
            self.assertEqual(
                stored,
                (
                    receipt["semantic_config_fingerprint"],
                    receipt["semantic_evidence_fingerprint"],
                    receipt["used_source_set_fingerprint"],
                    "complete",
                ),
            )
            membership_states = connection.execute(
                "SELECT w.public_work_id,sw.state FROM study_works sw "
                "JOIN logical_works w ON w.work_id=sw.work_id "
                "WHERE sw.study_id=? ORDER BY sw.ordinal",
                (receipt["study_id"],),
            ).fetchall()
            self.assertEqual(
                membership_states,
                [
                    ("PW-SYNTHETIC-USED", "studied"),
                    ("PW-SYNTHETIC-UNUSED", "selected"),
                ],
            )
            for column in (
                "semantic_config_fingerprint",
                "semantic_evidence_fingerprint",
                "used_source_set_fingerprint",
            ):
                with self.subTest(column=column):
                    with self.assertRaisesRegex(
                        sqlite3.IntegrityError,
                        "style_completion_receipt_immutable",
                    ):
                        connection.execute(
                            f"UPDATE style_completion_receipts SET {column}=? "
                            "WHERE style_run_id=?",
                            (self._style_fingerprint("forged"), receipt["style_run_id"]),
                        )

        # An exact retry remains idempotent and cannot create a second receipt.
        replayed = self.library.record_style_completion(**receipt)
        self.assertEqual(replayed["receipt_fingerprint"], receipt["receipt_fingerprint"])
        with closing(sqlite3.connect(self.db_path)) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM style_completion_receipts"
                ).fetchone()[0],
                1,
            )

    def test_style_completion_receipt_rejects_missing_forged_and_drifted_semantics(self) -> None:
        receipt = self._style_completion_fixture()
        self._install_style_completion_fixture(receipt)

        for missing_key in (
            "semantic_config_fingerprint",
            "semantic_evidence_fingerprint",
            "used_source_set_fingerprint",
        ):
            with self.subTest(missing=missing_key):
                missing = dict(receipt)
                missing.pop(missing_key)
                with self.assertRaises(CorpusLibraryError) as raised:
                    self.library.record_style_completion(**missing)
                self.assertEqual(
                    raised.exception.code,
                    "style_completion_receipt_invalid",
                )

        for drifted_key in (
            "semantic_config_fingerprint",
            "semantic_evidence_fingerprint",
            "used_source_set_fingerprint",
        ):
            with self.subTest(drifted=drifted_key):
                drifted = dict(receipt)
                drifted[drifted_key] = self._style_fingerprint(
                    f"forged-{drifted_key}"
                )
                drifted["receipt_fingerprint"] = "sha256:" + hashlib.sha256(
                    json.dumps(
                        {
                            key: value
                            for key, value in drifted.items()
                            if key != "receipt_fingerprint"
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")
                ).hexdigest()
                with self.assertRaises(CorpusLibraryError) as raised:
                    self.library.record_style_completion(**drifted)
                self.assertEqual(
                    raised.exception.code,
                    "style_completion_runner_binding_mismatch",
                )

        invalid_format = dict(receipt)
        invalid_format["semantic_evidence_fingerprint"] = "not-a-fingerprint"
        invalid_format["receipt_fingerprint"] = self._style_fingerprint("irrelevant")
        with self.assertRaises(CorpusLibraryError) as raised:
            self.library.record_style_completion(**invalid_format)
        self.assertEqual(raised.exception.code, "style_completion_receipt_invalid")

        with closing(sqlite3.connect(self.db_path)) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM style_completion_receipts"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT state FROM studies WHERE study_id=?",
                    (receipt["study_id"],),
                ).fetchone()[0],
                "running",
            )

    def test_style_completion_receipt_replay_rejects_stored_semantic_drift(self) -> None:
        receipt = self._style_completion_fixture()
        self._install_style_completion_fixture(receipt)
        self.library.record_style_completion(**receipt)

        # Simulate out-of-band database tampering after removing the normal
        # immutable guard.  The idempotent load path must still compare every
        # semantic binding, not trust receipt identity alone.
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                "DROP TRIGGER immutable_style_completion_receipt"
            )
            connection.execute(
                "UPDATE style_completion_receipts "
                "SET semantic_evidence_fingerprint=? WHERE style_run_id=?",
                (
                    self._style_fingerprint("stored-drift"),
                    receipt["style_run_id"],
                ),
            )
            connection.commit()

        with self.assertRaises(CorpusLibraryError) as raised:
            self.library.record_style_completion(**receipt)
        self.assertEqual(
            raised.exception.code,
            "style_completion_receipt_conflict",
        )

    def test_legacy_style_receipts_migrate_fail_closed_and_upgrade_trigger(self) -> None:
        legacy_path = self.root / "legacy" / "corpus.sqlite"
        legacy_path.parent.mkdir()
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE style_completion_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    style_run_id TEXT NOT NULL UNIQUE,
                    study_id TEXT NOT NULL,
                    public_study_id TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    checklist_hash TEXT NOT NULL,
                    protocol_fingerprint TEXT NOT NULL,
                    sampling_config_fingerprint TEXT NOT NULL,
                    candidate_bundle_fingerprint TEXT NOT NULL,
                    candidate_artifact_fingerprint TEXT,
                    craft_pack_fingerprint TEXT,
                    receipt_fingerprint TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    created_at TEXT
                );
                CREATE TRIGGER immutable_style_completion_receipt
                BEFORE UPDATE OF receipt_id,style_run_id,study_id,public_study_id,profile,
                    checklist_hash,protocol_fingerprint,sampling_config_fingerprint,
                    candidate_bundle_fingerprint,candidate_artifact_fingerprint,
                    craft_pack_fingerprint,receipt_fingerprint
                ON style_completion_receipts
                BEGIN SELECT RAISE(ABORT, 'style_completion_receipt_immutable'); END;
                """
            )
            fingerprint = self._style_fingerprint("legacy")
            connection.execute(
                "INSERT INTO style_completion_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "STYLE-RECEIPT-LEGACY",
                    "STYLE-RUN-LEGACY",
                    "STUDY-LEGACY",
                    "PS-" + "b" * 32,
                    "general",
                    fingerprint,
                    fingerprint,
                    fingerprint,
                    fingerprint,
                    fingerprint,
                    fingerprint,
                    fingerprint,
                    "complete",
                    "2026-01-01T00:00:00Z",
                ),
            )
            connection.commit()

        CorpusLibrary(legacy_path, public_root=self.root / "legacy-public")

        with closing(sqlite3.connect(legacy_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(style_completion_receipts)"
                )
            }
            self.assertTrue(
                {
                    "semantic_config_fingerprint",
                    "semantic_evidence_fingerprint",
                    "used_source_set_fingerprint",
                }.issubset(columns)
            )
            migrated = connection.execute(
                "SELECT state,semantic_config_fingerprint,semantic_evidence_fingerprint,"
                "used_source_set_fingerprint "
                "FROM style_completion_receipts WHERE style_run_id='STYLE-RUN-LEGACY'"
            ).fetchone()
            self.assertEqual(migrated, ("invalidated", None, None, None))
            trigger_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' "
                "AND name='immutable_style_completion_receipt'"
            ).fetchone()[0]
            self.assertIn("semantic_config_fingerprint", trigger_sql)
            self.assertIn("semantic_evidence_fingerprint", trigger_sql)
            self.assertIn("used_source_set_fingerprint", trigger_sql)

    def test_direct_metric_completion_cannot_bypass_semantic_release_receipt(self) -> None:
        self._write_txt_works(STUDY_SIZE)
        _scan, completed = self._complete()
        with self.assertRaises(CorpusLibraryError) as preview_error:
            self.library.preview_public(completed["study_id"])
        self.assertEqual(
            preview_error.exception.code, "semantic_completion_receipt_missing"
        )
        decision = self.library.validate_public(study_id=completed["study_id"])
        self.assertFalse(decision["valid"])
        self.assertIn("semantic_completion_receipt_missing", decision["errors"])
        with self.assertRaises(CorpusLibraryError) as release_error:
            self.library.release_public(
                completed["study_id"],
                preview_token="preview-" + "0" * 64,
                manifest_fingerprint="sha256:" + "0" * 64,
            )
        self.assertEqual(
            release_error.exception.code, "semantic_completion_receipt_missing"
        )

    def test_source_version_change_invalidates_study_without_mutating_hash(self) -> None:
        self._write_txt_works(STUDY_SIZE)
        _scan, confirmed = self._confirmed()
        checklist_hash = confirmed["checklist_hash"]
        changed = self._work_path(0)
        changed.write_text(
            self._general_body(999), encoding="utf-8"
        )
        scan = self.library.scan_collection(self.sources)
        self.assertGreaterEqual(scan["invalidated_studies"], 1)
        status = self.library.study_status(confirmed["study_id"])
        self.assertEqual(status["status"], "invalidated")
        self.assertEqual(status["checklist_hash"], checklist_hash)

    def test_epub_parser_reads_spine_and_rejects_traversal_members(self) -> None:
        good = self.sources / "owned.epub"
        self._write_epub(good)
        good_scan = self.library.scan_collection(self.sources)
        self.assertEqual(good_scan["rejected_files"], 0)
        self.assertEqual(good_scan["logical_works"], 1)

        bad = self.sources / "traversal.epub"
        with zipfile.ZipFile(bad, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("../outside.txt", "must never escape")
            archive.writestr("META-INF/container.xml", "<container/>")
        bad_scan = self.library.scan_collection(self.sources)
        self.assertEqual(bad_scan["rejected_files"], 1)
        self.assertEqual(bad_scan["error_counts"]["epub_unsafe_member_path"], 1)
        self.assertFalse((self.root / "outside.txt").exists())

    def test_epub_embedded_title_is_primary_but_all_alias_locators_signal_profile(self) -> None:
        primary = self.sources / "a-unrelated-name.epub"
        alias = self.sources / "b-R18-unrelated-name.epub"
        self._write_epub(primary, title="Embedded Primary Work")
        alias.write_bytes(primary.read_bytes())
        scan = self.library.scan_collection(
            self.sources, collection_id="COL-EPUB-ALIASES"
        )
        self.assertEqual(scan["logical_works"], 1)
        with self.library._connect() as connection:
            general, general_exclusions = self.library._selection_pool(
                connection, scan["collection_id"], "general"
            )
            adult, adult_exclusions = self.library._selection_pool(
                connection, scan["collection_id"], "adult_explicit"
            )
        self.assertEqual(general, [])
        self.assertEqual(
            general_exclusions["strong_adult_profile_mismatch"], 1
        )
        self.assertEqual(len(adult), 1)
        self.assertEqual(adult[0]["family_key"], "embeddedprimarywork")
        self.assertEqual(adult_exclusions["alias_identity_conflict"], 0)

    def test_epub_doctype_policy_accepts_inert_forms_and_rejects_unsafe_forms(self) -> None:
        accepted = self.sources / "doctype-owned.epub"
        self._write_epub(
            accepted,
            container_doctype="<!DOCTYPE container>",
            package_doctype=(
                '<!DOCTYPE package PUBLIC "-//IDPF//DTD OPF 3.0//EN" '
                '"https://example.invalid/opf.dtd">'
            ),
            chapter_doctype='<!DOCTYPE html SYSTEM "about:legacy-compat">',
        )
        accepted_scan = self.library.scan_collection(self.sources)
        self.assertEqual(accepted_scan["rejected_files"], 0)
        self.assertEqual(accepted_scan["logical_works"], 1)

        unsafe_declarations = {
            "internal-subset": '<!DOCTYPE html [<!ENTITY x "boom">]>',
            "internal-subset-no-entity": "<!DOCTYPE html [<!ELEMENT html ANY>]>",
            "entity": '<!ENTITY x "boom">',
            "multiple": "<!DOCTYPE html><!DOCTYPE html>",
            "malformed-public": '<!DOCTYPE html PUBLIC "missing-system-id">',
        }
        for index, (name, declaration) in enumerate(unsafe_declarations.items()):
            with self.subTest(name=name):
                case_root = self.root / f"doctype-case-{index}"
                case_sources = case_root / "sources"
                case_sources.mkdir(parents=True)
                self._write_epub(
                    case_sources / f"{name}.epub", chapter_doctype=declaration
                )
                case_library = CorpusLibrary(
                    case_root / "corpus.sqlite", case_root / "public"
                )
                rejected = case_library.scan_collection(case_sources)
                self.assertEqual(rejected["rejected_files"], 1)
                self.assertEqual(rejected["error_counts"], {"epub_unsafe_xml": 1})

    def test_same_digest_parser_recovery_refreshes_derivatives_without_new_version(self) -> None:
        source = self.sources / "parser-recovery.epub"
        self._write_epub(
            source,
            chapter_doctype='<!DOCTYPE html SYSTEM "about:legacy-compat">',
            title="Recovered Private Title",
        )
        with patch.object(
            self.library,
            "_decode_epub",
            side_effect=CorpusLibraryError("epub_unsafe_xml"),
        ):
            rejected = self.library.scan_collection(
                self.sources, collection_id="COL-PARSER-RECOVERY"
            )
        self.assertEqual(rejected["rejected_files"], 1)
        with closing(sqlite3.connect(self.db_path)) as connection:
            version_before = connection.execute(
                "SELECT version_id,work_id,sha256,parse_state,error_code,char_count "
                "FROM source_versions"
            ).fetchone()
            connection.execute(
                "INSERT INTO studies(study_id,public_study_id,collection_id,profile,state,seed,proposal_hash) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    "STUDY-PARSER-DEPENDENCY",
                    "PS-" + "a" * 32,
                    "COL-PARSER-RECOVERY",
                    "general",
                    "proposed",
                    "seed",
                    "sha256:" + "b" * 64,
                ),
            )
            connection.execute(
                "INSERT INTO study_works(study_id,work_id,version_id,ordinal,state) "
                "VALUES(?,?,?,?,?)",
                (
                    "STUDY-PARSER-DEPENDENCY",
                    version_before[1],
                    version_before[0],
                    1,
                    "pending",
                ),
            )
            connection.commit()
        self.assertEqual(version_before[3], "error")
        self.assertEqual(version_before[4], "epub_unsafe_xml")
        self.assertEqual(version_before[5], 0)

        recovered = self.library.scan_collection(self.sources)
        self.assertEqual(recovered["rejected_files"], 0)
        self.assertEqual(recovered["new_versions"], 0)
        self.assertEqual(recovered["refreshed_versions"], 1)
        self.assertEqual(recovered["invalidated_studies"], 1)
        with closing(sqlite3.connect(self.db_path)) as connection:
            versions = connection.execute(
                "SELECT version_id,sha256,parse_state,error_code,char_count,private_metadata_json "
                "FROM source_versions"
            ).fetchall()
            study = connection.execute(
                "SELECT state,invalidation_reason FROM studies WHERE study_id=?",
                ("STUDY-PARSER-DEPENDENCY",),
            ).fetchone()
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0][0], version_before[0])
        self.assertEqual(versions[0][1], version_before[2])
        self.assertEqual(versions[0][2], "ok")
        self.assertIsNone(versions[0][3])
        self.assertGreater(versions[0][4], 0)
        self.assertEqual(
            json.loads(versions[0][5])["title"], "Recovered Private Title"
        )
        self.assertEqual(study, ("invalidated", "source_parse_derivation_changed"))
        self.assertNotIn("合法正文第一段".encode("utf-8"), self.db_path.read_bytes())

    def test_family_normalization_handles_snapshot_suffixes_and_safe_han_variants(self) -> None:
        labels = (
            "《星云归航》⊙1-508",
            "《星雲歸航》排版1663章",
            "星云归航01_48章",
        )
        for index, label in enumerate(labels):
            (self.sources / f"{label}.txt").write_text(
                self._general_body(index), encoding="utf-8"
            )
        for index in range(STUDY_SIZE - 1):
            (self.sources / f"Distinct General Story {self._alpha_token(index)}.txt").write_text(
                self._general_body(index + 10), encoding="utf-8"
            )
        scan = self.library.scan_collection(self.sources)
        proposal = self.library.propose_selection(
            "STUDY-HAN-FAMILY", collection_id=scan["collection_id"], seed="han", profile="general"
        )
        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["work_count"], STUDY_SIZE)
        self.assertEqual(proposal["exclusion_counts"]["logical_family_alternate"], 2)
        private = self.library.selection_private_preview(proposal["study_id"])
        family_labels = [
            work["display_label"]
            for work in private["works"]
            if _private_title_family(work["display_label"]) == "星云归航"
        ]
        self.assertEqual(len(family_labels), 1)


if __name__ == "__main__":
    unittest.main()
