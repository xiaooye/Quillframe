from pathlib import Path
import json

# Persistence: canonical global Project registry query.
p = Path('persistence/quillframe_sqlite.py')
text = p.read_text(encoding='utf-8')
marker = '''    def create_project(self, project_id: str, title: str, language: str = "zh-CN") -> ProjectLocation:\n'''
method = '''    def list_projects(self, limit: int = 100) -> list[dict[str, Any]]:\n        """Return the canonical global Project registry projection."""\n        self.initialize_global()\n        bounded = max(1, min(int(limit), 500))\n        with _connect(self.global_db) as conn:\n            rows = conn.execute(\n                "SELECT project_id,title,language,project_schema_version,registered_at,last_opened_at "\n                "FROM project_registry ORDER BY last_opened_at DESC, project_id LIMIT ?",\n                (bounded,),\n            ).fetchall()\n        return [dict(row) for row in rows]\n\n'''
if '    def list_projects(self, limit: int = 100)' not in text:
    if marker not in text:
        raise SystemExit('persistence create_project marker not found')
    text = text.replace(marker, method + marker, 1)
p.write_text(text, encoding='utf-8')

# Core operations.
p = Path('core_operations.py')
text = p.read_text(encoding='utf-8')
project_marker = '''    def start_author_run(\n'''
project_methods = r'''    def project_list(self, *, limit: int = 100) -> dict[str, Any]:
        return {
            "schema": "quillframe_project_registry_projection_v1",
            "items": self.store.list_projects(limit),
            "authority": False,
            "canon_authority": False,
        }

    def document_list(self, project_id: str, *, document_kind: str | None = None, limit: int = 500) -> dict[str, Any]:
        bounded = max(1, min(int(limit), 500))
        with self.store.open_project(project_id) as conn:
            if document_kind is not None:
                rows = conn.execute(
                    """SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at,
                    r.revision_id AS latest_revision_id,r.content_fingerprint AS latest_content_fingerprint,
                    r.authority_class AS latest_authority_class,r.created_at AS latest_revision_created_at
                    FROM documents d
                    LEFT JOIN document_revisions r ON r.revision_id=(
                      SELECT rr.revision_id FROM document_revisions rr
                      WHERE rr.document_id=d.document_id ORDER BY rr.created_at DESC,rr.rowid DESC LIMIT 1
                    )
                    WHERE d.document_kind=? ORDER BY d.created_at,d.document_id LIMIT ?""",
                    (document_kind, bounded),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at,
                    r.revision_id AS latest_revision_id,r.content_fingerprint AS latest_content_fingerprint,
                    r.authority_class AS latest_authority_class,r.created_at AS latest_revision_created_at
                    FROM documents d
                    LEFT JOIN document_revisions r ON r.revision_id=(
                      SELECT rr.revision_id FROM document_revisions rr
                      WHERE rr.document_id=d.document_id ORDER BY rr.created_at DESC,rr.rowid DESC LIMIT 1
                    )
                    ORDER BY d.created_at,d.document_id LIMIT ?""",
                    (bounded,),
                ).fetchall()
        return {
            "schema": "quillframe_document_list_projection_v1",
            "project_id": project_id,
            "document_kind": document_kind,
            "items": [dict(row) for row in rows],
            "authority": False,
            "canon_authority": False,
        }

    @staticmethod
    def _candidate_revision_request_receipt(conn, candidate_id: str) -> dict[str, Any] | None:  # noqa: ANN001
        rows = conn.execute(
            "SELECT payload_json FROM receipts WHERE receipt_kind='candidate_revision_request' ORDER BY created_at DESC,rowid DESC"
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("candidate_id") == candidate_id:
                return payload
        return None

    def candidate_review_get(self, project_id: str, *, candidate_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            candidate = conn.execute(
                """SELECT c.*,r.parent_revision_id,r.content AS candidate_content,
                r.content_fingerprint AS revision_fingerprint,r.authority_class AS revision_authority_class
                FROM candidates c LEFT JOIN document_revisions r ON r.revision_id=c.revision_id
                WHERE c.candidate_id=?""",
                (candidate_id,),
            ).fetchone()
            if not candidate:
                raise OperationError("candidate_not_found", candidate_id)
            c = dict(candidate)
            if not c.get("revision_id") or c.get("revision_fingerprint") != c.get("content_fingerprint"):
                raise OperationError("stale_review", "Candidate revision no longer matches its review fingerprint")
            parent = None
            if c.get("parent_revision_id"):
                row = conn.execute(
                    "SELECT revision_id,document_id,content,content_fingerprint,authority_class,created_at FROM document_revisions WHERE revision_id=?",
                    (c["parent_revision_id"],),
                ).fetchone()
                parent = dict(row) if row else None
            current_review_rows = conn.execute(
                "SELECT * FROM review_evidence WHERE candidate_id=? AND candidate_fingerprint=? AND independent=1 AND stale=0 ORDER BY created_at DESC,rowid DESC",
                (candidate_id, c["content_fingerprint"]),
            ).fetchall()
            any_review = conn.execute("SELECT COUNT(*) FROM review_evidence WHERE candidate_id=?", (candidate_id,)).fetchone()[0]
            if not current_review_rows:
                raise OperationError("stale_review" if any_review else "review_pending", "fresh fingerprint-bound independent Review evidence is unavailable")
            independent = json.loads(current_review_rows[0]["result_json"])
            stage_rows = conn.execute(
                "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY created_at,rowid",
                (c.get("run_id"),),
            ).fetchall() if c.get("run_id") else []
            stage_receipts = []
            for row in stage_rows:
                try:
                    stage_receipts.append(json.loads(row["payload_json"]))
                except (TypeError, json.JSONDecodeError):
                    continue
            by_mechanism = {row.get("mechanism"): row for row in stage_receipts if isinstance(row, dict)}
            required = ("reader_engagement", "character_simulation", "continuity", "independent_semantic_gate", "user_visible_gate")
            if any(name not in by_mechanism for name in required):
                raise OperationError("review_pending", "Candidate Review evidence is not complete")
            revision_request = self._candidate_revision_request_receipt(conn, candidate_id)

        diff = None
        if parent:
            diff = self.store.compare_revisions(project_id, parent["revision_id"], c["revision_id"])
        return {
            "schema": "quillframe_candidate_review_projection_v1",
            "project_id": project_id,
            "candidate": {
                "candidate_id": c["candidate_id"],
                "candidate_fingerprint": c["content_fingerprint"],
                "document_id": c.get("document_id"),
                "run_id": c.get("run_id"),
                "task_mode": c.get("task_mode"),
                "candidate_kind": c.get("candidate_kind"),
                "persisted_status": c.get("status"),
                "effective_status": "revision_requested" if revision_request and c.get("status") == "review_draft" else c.get("status"),
                "user_visible_gate": c.get("user_visible_gate"),
            },
            "candidate_revision": {
                "revision_id": c["revision_id"],
                "content": c["candidate_content"],
                "content_fingerprint": c["revision_fingerprint"],
                "authority_class": c["revision_authority_class"],
            },
            "incumbent_revision": parent,
            "diff": diff,
            "evidence": {
                "reader": by_mechanism["reader_engagement"],
                "character": by_mechanism["character_simulation"],
                "continuity": by_mechanism["continuity"],
                "independent": independent,
                "production_readiness": independent.get("production_readiness"),
                "user_visible_gate": by_mechanism["user_visible_gate"],
            },
            "revision_request": revision_request,
            "private_reasoning_exposed": False,
            "authority": False,
            "canon_authority": False,
            "settlement_authority": False,
        }

'''
if '    def project_list(self, *, limit: int = 100)' not in text:
    if project_marker not in text:
        raise SystemExit('core start_author_run marker not found')
    text = text.replace(project_marker, project_methods + project_marker, 1)

accept_marker = '''            evidence = conn.execute(\n                "SELECT COUNT(*) FROM review_evidence WHERE candidate_id=? AND candidate_fingerprint=? AND independent=1 AND stale=0",\n'''
accept_guard = '''            if self._candidate_revision_request_receipt(conn, candidate_id):\n                raise OperationError("candidate_revision_requested", "Candidate has a durable revision request and cannot be accepted")\n'''
if 'candidate_revision_requested", "Candidate has a durable revision request' not in text:
    if accept_marker not in text:
        raise SystemExit('accept evidence marker not found')
    text = text.replace(accept_marker, accept_guard + accept_marker, 1)

settle_marker = '''    def settle(\n'''
candidate_actions = r'''    def reject_candidate(
        self,
        project_id: str,
        *,
        candidate_id: str,
        candidate_fingerprint: str,
        authorized_by: str,
        authorization: dict[str, Any],
        idempotency_key: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise OperationError("idempotency_required", "Candidate rejection requires an idempotency key")
        with self.store.open_project(project_id) as conn:
            prior = conn.execute(
                "SELECT payload_json FROM receipts WHERE receipt_kind='candidate_reject' AND idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if prior:
                return json.loads(prior["payload_json"])
            conn.execute("BEGIN IMMEDIATE")
            candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
            if not candidate:
                conn.rollback()
                raise OperationError("candidate_not_found", candidate_id)
            if candidate["content_fingerprint"] != candidate_fingerprint:
                conn.rollback()
                raise OperationError("candidate_fingerprint_mismatch", "candidate changed since Review")
            accepted = conn.execute("SELECT 1 FROM acceptance_evidence WHERE candidate_id=? LIMIT 1", (candidate_id,)).fetchone()
            if candidate["status"] == "accepted" or accepted:
                conn.rollback()
                raise OperationError("already_accepted", "Accepted Candidate cannot be rejected")
            if candidate["status"] != "review_draft" or self._candidate_revision_request_receipt(conn, candidate_id):
                conn.rollback()
                raise OperationError("stale_state", "Candidate is no longer an actionable Review Draft")
            conn.execute("UPDATE candidates SET status='rejected' WHERE candidate_id=?", (candidate_id,))
            stamp = now_iso()
            result = {
                "schema": "quillframe_candidate_rejection_result_v1",
                "candidate_id": candidate_id,
                "candidate_fingerprint": candidate_fingerprint,
                "before_status": "review_draft",
                "status": "rejected",
                "authorized_by": authorized_by,
                "authorization": authorization,
                "reason": reason,
                "canon_mutated": False,
                "settled": False,
                "authority": False,
            }
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_reject", idempotency_key, canonical_json(result), stamp),
            )
            if candidate["run_id"]:
                conn.execute(
                    "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                    ("evt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_rejected", canonical_json({"candidate_id": candidate_id, "candidate_fingerprint": candidate_fingerprint}), stamp),
                )
            conn.commit()
            return result

    def request_candidate_revision(
        self,
        project_id: str,
        *,
        candidate_id: str,
        candidate_fingerprint: str,
        revision_request: dict[str, Any],
        authorized_by: str,
        authorization: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise OperationError("idempotency_required", "Request Revision requires an idempotency key")
        if not isinstance(revision_request, dict) or not revision_request:
            raise OperationError("invalid_args", "revision_request must be a non-empty object")
        with self.store.open_project(project_id) as conn:
            prior = conn.execute(
                "SELECT payload_json FROM receipts WHERE receipt_kind='candidate_revision_request' AND idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if prior:
                return json.loads(prior["payload_json"])
            conn.execute("BEGIN IMMEDIATE")
            candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
            if not candidate:
                conn.rollback()
                raise OperationError("candidate_not_found", candidate_id)
            if candidate["content_fingerprint"] != candidate_fingerprint:
                conn.rollback()
                raise OperationError("candidate_fingerprint_mismatch", "candidate changed since Review")
            accepted = conn.execute("SELECT 1 FROM acceptance_evidence WHERE candidate_id=? LIMIT 1", (candidate_id,)).fetchone()
            if candidate["status"] == "accepted" or accepted:
                conn.rollback()
                raise OperationError("already_accepted", "Accepted Candidate cannot request revision")
            if candidate["status"] != "review_draft" or self._candidate_revision_request_receipt(conn, candidate_id):
                conn.rollback()
                raise OperationError("stale_state", "Candidate is no longer an actionable Review Draft")
            stamp = now_iso()
            request_id = "revreq_" + uuid.uuid4().hex
            result = {
                "schema": "quillframe_candidate_revision_request_result_v1",
                "revision_request_id": request_id,
                "candidate_id": candidate_id,
                "candidate_fingerprint": candidate_fingerprint,
                "persisted_candidate_status": candidate["status"],
                "effective_status": "revision_requested",
                "revision_request": revision_request,
                "authorized_by": authorized_by,
                "authorization": authorization,
                "next_action": {
                    "operation": "author.run.start",
                    "task_mode": "REVISE",
                    "target_ref": candidate["document_id"],
                    "requires_explicit_user_action": True,
                    "auto_started": False,
                    "source_candidate_id": candidate_id,
                    "source_candidate_fingerprint": candidate_fingerprint,
                },
                "canon_mutated": False,
                "settled": False,
                "authority": False,
            }
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_revision_request", idempotency_key, canonical_json(result), stamp),
            )
            if candidate["run_id"]:
                conn.execute(
                    "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                    ("evt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_revision_requested", canonical_json({"candidate_id": candidate_id, "candidate_fingerprint": candidate_fingerprint, "revision_request_id": request_id}), stamp),
                )
            conn.commit()
            return result

    def settlement_preflight(self, project_id: str, *, acceptance_id: str, target_ref: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            acceptance = conn.execute(
                """SELECT a.acceptance_id,a.candidate_id,a.candidate_fingerprint,c.status AS candidate_status,
                c.revision_id,c.content_fingerprint,c.document_id
                FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
                WHERE a.acceptance_id=?""",
                (acceptance_id,),
            ).fetchone()
            if not acceptance:
                raise OperationError("acceptance_not_found", acceptance_id)
            if acceptance["candidate_status"] != "accepted" or acceptance["candidate_fingerprint"] != acceptance["content_fingerprint"]:
                raise OperationError("not_settleable", "Acceptance/Candidate binding is not settleable")
            if not acceptance["revision_id"]:
                raise OperationError("not_settleable", "Accepted Candidate has no document revision")
            revision = conn.execute(
                "SELECT revision_id,document_id,content_fingerprint,authority_class FROM document_revisions WHERE revision_id=?",
                (acceptance["revision_id"],),
            ).fetchone()
            if not revision or revision["authority_class"] != "accepted" or revision["content_fingerprint"] != acceptance["candidate_fingerprint"]:
                raise OperationError("not_settleable", "Accepted source revision is missing or no longer matches the Acceptance")
            settled = conn.execute(
                "SELECT settlement_id,status,after_fingerprint FROM settlements WHERE acceptance_id=? AND target_ref=? AND status='settled' ORDER BY created_at DESC LIMIT 1",
                (acceptance_id, target_ref),
            ).fetchone()
            if settled:
                raise OperationError("not_settleable", "Acceptance is already settled to this target", detail=dict(settled))
            current = conn.execute("SELECT content_fingerprint FROM canon_state WHERE state_key=?", (target_ref,)).fetchone()
            before = current["content_fingerprint"] if current else "absent"
        return {
            "schema": "quillframe_settlement_preflight_v1",
            "project_id": project_id,
            "acceptance_id": acceptance_id,
            "candidate_id": acceptance["candidate_id"],
            "candidate_fingerprint": acceptance["candidate_fingerprint"],
            "document_id": acceptance["document_id"],
            "revision_id": acceptance["revision_id"],
            "target_ref": target_ref,
            "expected_before_fingerprint": before,
            "current_before_fingerprint": before,
            "settleable": True,
            "mutation_performed": False,
            "canon_mutated": False,
            "authority": False,
        }

'''
if '    def reject_candidate(' not in text:
    if settle_marker not in text:
        raise SystemExit('settle marker not found')
    text = text.replace(settle_marker, candidate_actions + settle_marker, 1)

text = text.replace(
    '"project.create", "project.inspect", "project.search", "project.backup",\n                "document.create", "document.revision.save", "document.revision.compare",\n                "author.run.start", "candidate.accept", "settlement.apply",',
    '"project.create", "project.list", "project.inspect", "project.search", "project.backup",\n                "document.create", "document.list", "document.revision.save", "document.revision.compare",\n                "author.run.start", "candidate.review.get", "candidate.accept", "candidate.reject", "candidate.revision.request",\n                "settlement.preflight", "settlement.apply",',
)
p.write_text(text, encoding='utf-8')

# Host Bridge handlers + dispatch + v8 self-test.
p = Path('studio/host_bridge.py')
text = p.read_text(encoding='utf-8')
marker = '''def _project_create(args: dict[str, Any], _: str):\n'''
handler = '''def _project_list(args: dict[str, Any], _: str):\n    return ops().project_list(limit=int(args.get("limit") or 100))\n\n\n'''
if 'def _project_list(' not in text:
    if marker not in text:
        raise SystemExit('bridge project create marker not found')
    text = text.replace(marker, handler + marker, 1)
marker = '''def _document_create(args: dict[str, Any], _: str):\n'''
handler = '''def _document_list(args: dict[str, Any], _: str):\n    return ops().document_list(\n        require(args, "project_id"),\n        document_kind=args.get("document_kind") if isinstance(args.get("document_kind"), str) else None,\n        limit=int(args.get("limit") or 500),\n    )\n\n\n'''
if 'def _document_list(' not in text:
    text = text.replace(marker, handler + marker, 1)
marker = '''def _candidate_accept(args: dict[str, Any], _: str):\n'''
handler = '''def _candidate_review_get(args: dict[str, Any], _: str):\n    return ops().candidate_review_get(require(args, "project_id"), candidate_id=require(args, "candidate_id"))\n\n\ndef _candidate_reject(args: dict[str, Any], _: str):\n    if args.get("user_authorized") is not True:\n        raise BridgeError("authorization_required", "candidate.reject requires an explicit user action")\n    return ops().reject_candidate(\n        require(args, "project_id"), candidate_id=require(args, "candidate_id"),\n        candidate_fingerprint=require(args, "candidate_fingerprint"), authorized_by=require(args, "authorized_by"),\n        authorization=require(args, "authorization", dict), idempotency_key=require(args, "idempotency_key"),\n        reason=args.get("reason") if isinstance(args.get("reason"), str) else None,\n    )\n\n\ndef _candidate_revision_request(args: dict[str, Any], _: str):\n    if args.get("user_authorized") is not True:\n        raise BridgeError("authorization_required", "candidate.revision.request requires an explicit user action")\n    return ops().request_candidate_revision(\n        require(args, "project_id"), candidate_id=require(args, "candidate_id"),\n        candidate_fingerprint=require(args, "candidate_fingerprint"), revision_request=require(args, "revision_request", dict),\n        authorized_by=require(args, "authorized_by"), authorization=require(args, "authorization", dict),\n        idempotency_key=require(args, "idempotency_key"),\n    )\n\n\ndef _settlement_preflight(args: dict[str, Any], _: str):\n    return ops().settlement_preflight(\n        require(args, "project_id"), acceptance_id=require(args, "acceptance_id"), target_ref=require(args, "target_ref")\n    )\n\n\n'''
if 'def _candidate_review_get(' not in text:
    text = text.replace(marker, handler + marker, 1)

text = text.replace('    "project.create": _project_create,', '    "project.create": _project_create,\n    "project.list": _project_list,')
text = text.replace('    "document.create": _document_create,', '    "document.create": _document_create,\n    "document.list": _document_list,')
text = text.replace('    "candidate.accept": _candidate_accept,', '    "candidate.review.get": _candidate_review_get,\n    "candidate.accept": _candidate_accept,\n    "candidate.reject": _candidate_reject,\n    "candidate.revision.request": _candidate_revision_request,')
text = text.replace('    "settlement.apply": _settle,', '    "settlement.preflight": _settlement_preflight,\n    "settlement.apply": _settle,')
text = text.replace('"contract_version": "7"', '"contract_version": "8"')
p.write_text(text, encoding='utf-8')

# Machine contract v8.
p = Path('studio/host_bridge_contract.json')
contract = json.loads(p.read_text(encoding='utf-8'))
contract['version'] = '8'
ops = contract['operations']
ops['project.list'] = {"kind": "query", "required_args": []}
ops['document.list'] = {"kind": "query", "required_args": ["project_id"]}
ops['candidate.review.get'] = {"kind": "query", "required_args": ["project_id", "candidate_id"]}
ops['candidate.reject'] = {
    "kind": "authority_command",
    "required_args": ["project_id", "candidate_id", "candidate_fingerprint", "authorized_by", "authorization", "idempotency_key", "user_authorized"],
    "allowed_surfaces": ["cli", "local_app", "hosted_web"],
}
ops['candidate.revision.request'] = {
    "kind": "authority_command",
    "required_args": ["project_id", "candidate_id", "candidate_fingerprint", "revision_request", "authorized_by", "authorization", "idempotency_key", "user_authorized"],
    "allowed_surfaces": ["cli", "local_app", "hosted_web"],
}
ops['settlement.preflight'] = {
    "kind": "query",
    "required_args": ["project_id", "acceptance_id", "target_ref"],
    "allowed_surfaces": ["cli", "local_app", "hosted_web"],
}
contract['invariants']['request_revision_auto_starts_revise'] = False
contract['invariants']['settlement_preflight_mutates_canon'] = False
contract['invariants']['browser_project_registry_authority'] = False
p.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Existing Host Bridge tests expect v8 and new primitives.
p = Path('tests/test_quillframe_production_host_bridge.py')
tests = p.read_text(encoding='utf-8')
tests = tests.replace('test_v7_contract_exposes_production_external_review_and_model_service_primitives', 'test_v8_contract_exposes_authoring_production_and_model_service_primitives')
tests = tests.replace('self.assertEqual(contract["version"], "7")', 'self.assertEqual(contract["version"], "8")')
tests = tests.replace('self.assertEqual(report["contract_version"], "7")', 'self.assertEqual(report["contract_version"], "8")')
needle = '''            "project.restore",\n'''
repl = '''            "project.restore",\n            "project.list",\n            "document.list",\n            "candidate.review.get",\n            "candidate.reject",\n            "candidate.revision.request",\n            "settlement.preflight",\n'''
if '            "project.list",' not in tests:
    tests = tests.replace(needle, repl, 1)
p.write_text(tests, encoding='utf-8')

# Deterministic Core lifecycle/integration coverage.
Path('tests/test_quillframe_authoring_primitives.py').write_text('''from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, now_iso


class AuthoringPrimitiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.ops = CoreOperations(self.store)
        self.store.create_project("P", "Project P", "zh-CN")
        self.store.create_document("P", "DOC", "Chapter")
        first = self.store.save_revision("P", "DOC", "incumbent", expected_parent_revision_id=None, source="test")
        second = self.store.save_revision("P", "DOC", "candidate", expected_parent_revision_id=first["revision_id"], source="test", authority_class="review")
        self.first = first
        self.second = second
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute("INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", ("RUN", "DRAFT", "DOC", "completed", "sha256:req", stamp, stamp))
            conn.execute("INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("C", "DOC", second["revision_id"], "RUN", "DRAFT", "draft", "review_draft", second["content_fingerprint"], "PASS", stamp))
            for mechanism in ("reader_engagement", "character_simulation", "continuity", "independent_semantic_gate", "user_visible_gate"):
                payload = {"mechanism": mechanism, "stage_result_fingerprint": f"sha256:{mechanism}", "judgment": {"status": "pass"}, "private_reasoning_exposed": False}
                conn.execute("INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)", (f"R-{mechanism}", "RUN", "production_stage", f"RUN:{mechanism}", canonical_json(payload), stamp))
            review = {"model_contract_id": "quality.production_review", "production_readiness": {"ready_for_user_visible_review": True}, "private_reasoning_exposed": False}
            conn.execute("INSERT INTO review_evidence(review_id,candidate_id,evidence_kind,result_json,candidate_fingerprint,reviewer_fingerprint,independent,stale,created_at) VALUES(?,?,?,?,?,?,1,0,?)", ("REV", "C", "quality.production_review", canonical_json(review), second["content_fingerprint"], "sha256:peer", stamp))
            conn.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_project_and_document_registry_are_core_owned_read_only_projections(self):
        projects = self.ops.project_list()
        self.assertEqual(projects["items"][0]["project_id"], "P")
        self.assertFalse(projects["authority"])
        docs = self.ops.document_list("P")
        self.assertEqual(docs["items"][0]["document_id"], "DOC")
        self.assertEqual(docs["items"][0]["latest_revision_id"], self.second["revision_id"])
        self.assertEqual(docs["items"][0]["latest_content_fingerprint"], self.second["content_fingerprint"])
        self.assertFalse(docs["authority"])

    def test_candidate_review_projection_is_exact_and_contains_safe_required_evidence(self):
        review = self.ops.candidate_review_get("P", candidate_id="C")
        self.assertEqual(review["candidate"]["candidate_fingerprint"], self.second["content_fingerprint"])
        self.assertEqual(review["candidate_revision"]["content"], "candidate")
        self.assertEqual(review["incumbent_revision"]["content"], "incumbent")
        self.assertTrue(review["diff"]["diff"])
        self.assertEqual(set(review["evidence"]), {"reader", "character", "continuity", "independent", "production_readiness", "user_visible_gate"})
        self.assertFalse(review["private_reasoning_exposed"])

    def test_candidate_reject_is_idempotent_exact_and_terminal(self):
        result = self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "reject"}, idempotency_key="reject-1", reason="not right")
        replay = self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "reject"}, idempotency_key="reject-1")
        self.assertEqual(result, replay)
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["canon_mutated"])
        with self.assertRaises(OperationError) as stale:
            self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={}, idempotency_key="reject-2")
        self.assertEqual(stale.exception.code, "stale_state")

    def test_request_revision_is_durable_does_not_auto_start_revise_and_blocks_accept(self):
        result = self.ops.request_candidate_revision("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], revision_request={"instruction": "fix pacing"}, authorized_by="user", authorization={"intent": "request_revision"}, idempotency_key="rr-1")
        self.assertEqual(result["effective_status"], "revision_requested")
        self.assertFalse(result["next_action"]["auto_started"])
        self.assertEqual(result["next_action"]["task_mode"], "REVISE")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT status FROM candidates WHERE candidate_id='C'").fetchone()[0], "review_draft")
        review = self.ops.candidate_review_get("P", candidate_id="C")
        self.assertEqual(review["candidate"]["effective_status"], "revision_requested")
        with self.assertRaises(OperationError) as blocked:
            self.ops.accept_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "accept"}, idempotency_key="accept-after-rr")
        self.assertEqual(blocked.exception.code, "candidate_revision_requested")

    def test_settlement_preflight_is_authoritative_and_read_only_then_apply_uses_exact_before(self):
        acceptance = self.ops.accept_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "accept"}, idempotency_key="accept-1")
        with self.store.open_project("P") as conn:
            before_counts = (conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0], conn.execute("SELECT COUNT(*) FROM canon_state").fetchone()[0])
        preflight = self.ops.settlement_preflight("P", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:DOC")
        self.assertEqual(preflight["expected_before_fingerprint"], "absent")
        self.assertTrue(preflight["settleable"])
        self.assertFalse(preflight["mutation_performed"])
        with self.store.open_project("P") as conn:
            after_counts = (conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0], conn.execute("SELECT COUNT(*) FROM canon_state").fetchone()[0])
        self.assertEqual(before_counts, after_counts)
        settled = self.ops.settle("P", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:DOC", expected_before_fingerprint=preflight["expected_before_fingerprint"], user_authorized=True, idempotency_key="settle-1")
        self.assertEqual(settled["status"], "settled")

    def test_candidate_actions_fail_closed_on_wrong_fingerprint(self):
        with self.assertRaises(OperationError) as rejected:
            self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint="sha256:wrong", authorized_by="user", authorization={}, idempotency_key="bad-reject")
        self.assertEqual(rejected.exception.code, "candidate_fingerprint_mismatch")
        with self.assertRaises(OperationError) as revision:
            self.ops.request_candidate_revision("P", candidate_id="C", candidate_fingerprint="sha256:wrong", revision_request={"instruction": "x"}, authorized_by="user", authorization={}, idempotency_key="bad-revision")
        self.assertEqual(revision.exception.code, "candidate_fingerprint_mismatch")


if __name__ == "__main__":
    unittest.main()
''', encoding='utf-8')
