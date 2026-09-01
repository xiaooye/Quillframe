from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from harness.context_runtime import fingerprint
from harness.semantic_workers.semantic_worker_router import fingerprint_for, make_contract_job
from learning.author_voice import AuthorVoiceService, VOICE_FIELDS


class AuthorVoiceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "author.sqlite"
        self.service = AuthorVoiceService(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def source_payload(
        self,
        text: str,
        *,
        scope: str = "project",
        project_id: str | None = "PROJECT-A",
        source_kind: str = "user_authored_prose",
    ) -> dict:
        value = {
            "scope": scope,
            "source_kind": source_kind,
            "source_ref": "author-fixture:" + fingerprint(text)[7:23],
            "content_text": text,
            "content_fingerprint": fingerprint(text),
            "rights": {
                "rights_class": "redistributable",
                "rights_basis": "Synthetic author-owned fixture.",
                "storage_intent": "full_text",
                "excerpt_purpose": None,
                "writer_use_authorized": True,
            },
            "author_confirmed": True,
            "living_author_imitation": False,
            "model_generated": False,
            "rejected_candidate": False,
            "applicability": {"language": "zh-CN"},
        }
        if scope == "project":
            value["project_id"] = project_id
        return value

    @staticmethod
    def compiler_source(source: dict) -> dict:
        return {
            "source_id": source["source_id"],
            "source_kind": source["source_kind"],
            "content_text": source["content_text"],
            "content_fingerprint": source["content_fingerprint"],
            "rights_binding": {
                "rights_class": source["rights"]["rights_class"],
                "rights_basis": source["rights"]["rights_basis"],
                "storage_intent": source["rights"]["storage_intent"],
                "excerpt_purpose": source["rights"]["excerpt_purpose"],
                "writer_use_authorized": True,
            },
            "author_confirmed": True,
            "applicability": source["applicability"],
        }

    def binding(self, sources: list[dict], *, scope: str) -> dict:
        payload = {
            "scope": scope,
            "sources": [self.compiler_source(source) for source in sources],
        }
        job = make_contract_job("learning.author_voice_compile", "VOICE-FIXTURE", payload)
        judgment = {
            "confidence": 0.9,
            "fields": {field: "Synthetic bounded mechanism." for field in VOICE_FIELDS},
            "source_ids": [source["source_id"] for source in sources],
            "source_fingerprints": {
                source["source_id"]: source["content_fingerprint"] for source in sources
            },
            "anchor_source_ids": [
                source["source_id"] for source in sources
                if source["source_kind"] != "explicit_author_feedback"
            ][:4],
            "uncertainties": [],
        }
        result = {
            "job_id": job["job_id"],
            "subject_id": job["subject_id"],
            "kind": job["kind"],
            "input_fingerprint": job["input_fingerprint"],
            "status": "completed",
            "worker": {"provider": "fixture", "model_or_reviewer": "fixture-model"},
            "judgment": judgment,
            "proposals": [],
            "errors": [],
        }
        return {
            "job": job,
            "result": result,
            "binding_fingerprint": fingerprint({"job": job, "result": result}),
        }

    def create_and_activate(
        self, text: str, *, scope: str = "project", project_id: str | None = "PROJECT-A"
    ) -> dict:
        source = self.service.register_source(
            self.source_payload(text, scope=scope, project_id=project_id)
        )
        payload = {"scope": scope, "compiler_binding": self.binding([source], scope=scope)}
        if scope == "project":
            payload["project_id"] = project_id
        candidate = self.service.create_candidate(payload)
        return self.service.activate(
            candidate["sheet_id"],
            expected_version=candidate["version"],
            expected_sheet_fingerprint=candidate["sheet_fingerprint"],
            confirmation_ref="author-confirmation:fixture",
        )

    def test_project_voice_isolated_and_user_voice_is_fallback_only(self) -> None:
        project = self.create_and_activate("项目甲作者自有文本。")
        self.assertEqual(
            project["sheet"]["sheet_id"],
            AuthorVoiceService.snapshot_readonly(self.db, project_id="PROJECT-A")["active_sheet"]["sheet_id"],
        )
        self.assertEqual(
            "disabled",
            AuthorVoiceService.snapshot_readonly(self.db, project_id="PROJECT-B")["status"],
        )
        user = self.create_and_activate("用户级作者自有文本。", scope="user", project_id=None)
        self.assertEqual(
            user["sheet"]["sheet_id"],
            AuthorVoiceService.snapshot_readonly(self.db, project_id="PROJECT-B")["active_sheet"]["sheet_id"],
        )
        self.assertEqual(
            project["sheet"]["sheet_id"],
            AuthorVoiceService.snapshot_readonly(self.db, project_id="PROJECT-A")["active_sheet"]["sheet_id"],
        )

    def test_ineligible_positive_sources_fail_closed(self) -> None:
        for field, value in (
            ("model_generated", True),
            ("rejected_candidate", True),
            ("living_author_imitation", True),
            ("author_confirmed", False),
        ):
            with self.subTest(field=field):
                payload = self.source_payload("不合格来源-" + field)
                payload[field] = value
                with self.assertRaises(ValueError):
                    self.service.register_source(payload)
        payload = self.source_payload("未授权来源")
        payload["rights"]["writer_use_authorized"] = False
        with self.assertRaises(ValueError):
            self.service.register_source(payload)

    def test_compiler_job_must_bind_exact_registered_text_rights_and_scope(self) -> None:
        source = self.service.register_source(self.source_payload("精确编译来源。"))
        binding = self.binding([source], scope="project")
        forged = deepcopy(binding)
        forged["job"]["input"]["payload"]["sources"][0]["content_text"] = "另一段文本。"
        forged["job"]["input_fingerprint"] = fingerprint_for(forged["job"])
        forged["result"]["input_fingerprint"] = forged["job"]["input_fingerprint"]
        forged["binding_fingerprint"] = fingerprint({"job": forged["job"], "result": forged["result"]})
        with self.assertRaises(ValueError):
            self.service.create_candidate({
                "scope": "project",
                "project_id": "PROJECT-A",
                "compiler_binding": forged,
            })
        with self.assertRaises(ValueError):
            self.service.create_candidate({
                "scope": "project",
                "project_id": "PROJECT-B",
                "compiler_binding": binding,
            })

    def test_activation_and_snapshot_fail_closed_on_fingerprint_or_source_corruption(self) -> None:
        source = self.service.register_source(self.source_payload("不可篡改来源。"))
        candidate = self.service.create_candidate({
            "scope": "project",
            "project_id": "PROJECT-A",
            "compiler_binding": self.binding([source], scope="project"),
        })
        with self.assertRaises(ValueError):
            self.service.activate(
                candidate["sheet_id"],
                expected_version=1,
                expected_sheet_fingerprint="sha256:" + "0" * 64,
                confirmation_ref="author-confirmation:wrong-sheet",
            )
        self.service.activate(
            candidate["sheet_id"],
            expected_version=1,
            expected_sheet_fingerprint=candidate["sheet_fingerprint"],
            confirmation_ref="author-confirmation:exact-sheet",
        )
        connection = sqlite3.connect(self.db)
        try:
            connection.execute(
                "UPDATE author_voice_sources SET content_text='tampered' WHERE source_id=?",
                (source["source_id"],),
            )
            connection.commit()
        finally:
            connection.close()
        self.assertEqual(
            "disabled",
            AuthorVoiceService.snapshot_readonly(self.db, project_id="PROJECT-A")["status"],
        )


if __name__ == "__main__":
    unittest.main()
