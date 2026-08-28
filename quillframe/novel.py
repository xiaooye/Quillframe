"""Core-owned chapter, planning and story projections for native novels."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from core_operations import CoreOperations, OperationError
from harness.planning_horizon import create_region, normalize_policy, admit_realization
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso

READER_INTENT_KEYS = frozenset({
    'reader_question', 'visible_reward', 'character_choice', 'cost',
    'net_change', 'next_chapter_pull',
})


def text_value(value: Any, name: str, *, maximum: int = 512, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > maximum or '\x00' in value:
        raise OperationError('invalid_args', name + ' is invalid')
    return value if empty else value.strip()


def require_authorized(value: Any) -> None:
    if value is not True:
        raise OperationError('authorization_required', 'an explicit author action is required')


def json_object(value: str, name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise OperationError('project_state_invalid', name + ' is malformed') from exc
    if not isinstance(parsed, dict):
        raise OperationError('project_state_invalid', name + ' must be an object')
    return parsed


def resolve_chapter_target(conn, chapter_id: Any, document_id: Any = None, target_ref: Any = None) -> dict[str, Any]:
    chapter_id = text_value(chapter_id, 'chapter_id')
    chapter = conn.execute("SELECT * FROM story_nodes WHERE node_id=? AND kind='chapter'", (chapter_id,)).fetchone()
    if chapter is None:
        raise OperationError('chapter_not_found', 'chapter_id is not registered in this project')
    if document_id is None and isinstance(target_ref, str) and not target_ref.startswith('chapter:'):
        document_id = target_ref
    if document_id is None:
        documents = conn.execute("SELECT document_id FROM documents WHERE story_node_id=? AND document_kind='manuscript'", (chapter_id,)).fetchall()
        if len(documents) != 1:
            raise OperationError('chapter_document_ambiguous', 'select one registered chapter manuscript')
        document_id = documents[0]['document_id']
    document_id = text_value(document_id, 'document_id')
    document = conn.execute("SELECT document_id,story_node_id FROM documents WHERE document_id=? AND document_kind='manuscript'", (document_id,)).fetchone()
    if document is None or document['story_node_id'] != chapter_id:
        raise OperationError('chapter_document_mismatch', 'document is not the selected chapter manuscript')
    if target_ref is not None and target_ref not in {document_id, 'chapter:' + chapter_id}:
        raise OperationError('chapter_target_mismatch', 'run target does not match the selected chapter/document')
    metadata = json_object(chapter['metadata_json'], 'chapter metadata')
    reading_order = chapter['ordinal']
    story_order = metadata.get('story_order', reading_order)
    if type(reading_order) is not int or reading_order < 0 or type(story_order) is not int or story_order < 0:
        raise OperationError('chapter_order_invalid', 'chapter orders must be declared non-negative integers')
    return {'chapter_id': chapter_id, 'document_id': document_id,
            'current_reading_order': reading_order, 'current_story_order': story_order}


def acceptance_target(conn, acceptance: Any, target_ref: str) -> dict[str, Any]:
    document = conn.execute('SELECT story_node_id FROM documents WHERE document_id=?', (acceptance['document_id'],)).fetchone()
    if document is None or not document['story_node_id']:
        raise OperationError('settlement_target_invalid', 'accepted manuscript has no chapter')
    target = resolve_chapter_target(conn, document['story_node_id'], acceptance['document_id'])
    if target_ref != 'chapter:' + target['chapter_id']:
        raise OperationError('settlement_target_mismatch', 'settlement must target the accepted manuscript chapter')
    return target


def latest_acceptance(conn, document_id: str):
    return conn.execute("""SELECT a.acceptance_id,a.candidate_fingerprint,c.run_id,c.revision_id,c.status,
        r.content,r.content_fingerprint,r.authority_class
        FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
        JOIN document_revisions r ON r.revision_id=c.revision_id
        WHERE c.document_id=? ORDER BY a.created_at DESC,a.rowid DESC LIMIT 1""", (document_id,)).fetchone()


def current_head(conn, chapter_id: str, document_id: str) -> tuple[dict[str, Any] | None, bool]:
    row = conn.execute('SELECT * FROM canon_state WHERE state_key=?', ('chapter:' + chapter_id,)).fetchone()
    accepted = latest_acceptance(conn, document_id)
    if row is None:
        return None, accepted is not None
    head = json_object(row['value_json'], 'chapter head')
    valid = (
        fingerprint_text(canonical_json(head)) == row['content_fingerprint']
        and accepted is not None and accepted['status'] == 'accepted'
        and head.get('acceptance_id') == accepted['acceptance_id']
        and head.get('document_id') == document_id
        and head.get('revision_id') == accepted['revision_id']
        and head.get('content_fingerprint') == accepted['candidate_fingerprint'] == accepted['content_fingerprint']
        and accepted['authority_class'] == 'accepted'
        and fingerprint_text(accepted['content']) == accepted['content_fingerprint']
    )
    stale = accepted is not None and conn.execute(
        "SELECT 1 FROM chapter_dependencies WHERE chapter_id=? AND run_id=? AND status='stale' LIMIT 1",
        (chapter_id, accepted['run_id']),
    ).fetchone() is not None
    settled = conn.execute("SELECT 1 FROM settlements WHERE acceptance_id=? AND target_ref=? AND status='settled' AND after_fingerprint=?", (head.get('acceptance_id'), 'chapter:' + chapter_id, row['content_fingerprint'])).fetchone()
    if not valid or stale or settled is None:
        return None, True
    return {**head, 'head_fingerprint': row['content_fingerprint']}, False


def bind_prior_dependencies(conn, target: dict[str, Any], run_id: str) -> None:
    rows = conn.execute("""SELECT n.node_id,d.document_id FROM story_nodes n
        JOIN documents d ON d.story_node_id=n.node_id AND d.document_kind='manuscript'
        WHERE n.kind='chapter' AND n.ordinal<? ORDER BY n.ordinal,n.node_id""", (target['current_reading_order'],)).fetchall()
    stamp = now_iso()
    for row in rows:
        head, stale = current_head(conn, row['node_id'], row['document_id'])
        if head is None:
            raise OperationError('prior_chapter_not_ready', 'preceding chapters require current accepted and settled manuscripts', detail={'chapter_id': row['node_id'], 'needs_review': stale})
        conn.execute("INSERT INTO chapter_dependencies(chapter_id,source_chapter_id,source_fingerprint,run_id,status,created_at,updated_at) VALUES(?,?,?,?,'current',?,?)", (target['chapter_id'], row['node_id'], head['head_fingerprint'], run_id, stamp, stamp))


def invalidate_dependencies(conn, chapter_id: str, before_fingerprint: str, after_fingerprint: str) -> list[str]:
    if before_fingerprint == after_fingerprint or before_fingerprint == 'absent':
        return []
    rows = conn.execute("SELECT DISTINCT chapter_id FROM chapter_dependencies WHERE source_chapter_id=? AND source_fingerprint=? AND status='current'", (chapter_id, before_fingerprint)).fetchall()
    conn.execute("UPDATE chapter_dependencies SET status='stale',updated_at=? WHERE source_chapter_id=? AND source_fingerprint=?", (now_iso(), chapter_id, before_fingerprint))
    return [row['chapter_id'] for row in rows]


class NovelOperations:
    def __init__(self, store: QuillframeStore):
        self.store = store

    @staticmethod
    def _receipt(conn, kind: str, key: str, request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        result = {**result, 'request_fingerprint': fingerprint_text(canonical_json(request))}
        conn.execute('INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?)', ('rcpt_' + uuid.uuid4().hex, kind, key, canonical_json(result), now_iso()))
        return result

    @staticmethod
    def _replay(conn, kind: str, key: str, request: dict[str, Any]):
        return CoreOperations._idempotency_replay_or_conflict(conn, idempotency_key=key, receipt_kind=kind, request_fingerprint=fingerprint_text(canonical_json(request)))

    def chapter_list(self, project_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            rows = conn.execute("""SELECT n.node_id,n.title,n.ordinal,n.parent_id,d.document_id,
                (SELECT r.revision_id FROM document_revisions r WHERE r.document_id=d.document_id ORDER BY r.created_at DESC,r.rowid DESC LIMIT 1) AS current_revision_id
                FROM story_nodes n JOIN documents d ON d.story_node_id=n.node_id AND d.document_kind='manuscript'
                WHERE n.kind='chapter' ORDER BY n.ordinal,n.node_id,d.document_id""").fetchall()
            items = []
            for row in rows:
                head, needs_review = current_head(conn, row['node_id'], row['document_id'])
                items.append({'chapter_id': row['node_id'], 'title': row['title'], 'ordinal': row['ordinal'], 'parent_id': row['parent_id'], 'document_id': row['document_id'], 'current_revision_id': row['current_revision_id'], 'current_acceptance_id': head['acceptance_id'] if head else None, 'needs_review': needs_review})
        return {'schema': 'quillframe_chapter_list_v1', 'project_id': project_id, 'items': items, 'authority': False}

    def chapter_create(self, project_id: str, *, title: str, idempotency_key: str, user_authorized: bool, parent_id: str | None = None) -> dict[str, Any]:
        require_authorized(user_authorized)
        title = text_value(title, 'title')
        key = text_value(idempotency_key, 'idempotency_key')
        if parent_id is not None:
            parent_id = text_value(parent_id, 'parent_id')
        request = {'operation': 'chapter.create', 'project_id': project_id, 'title': title, 'parent_id': parent_id}
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                prior = self._replay(conn, 'chapter_create', key, request)
                if prior:
                    conn.commit()
                    return prior
                if parent_id is not None and conn.execute("SELECT 1 FROM story_nodes WHERE node_id=? AND kind IN ('book','volume','arc','unit')", (parent_id,)).fetchone() is None:
                    raise OperationError('chapter_parent_invalid', 'chapter parent is not a registered book/volume/arc/unit')
                ordinal = conn.execute("SELECT COALESCE(MAX(ordinal),0)+1 FROM story_nodes WHERE kind='chapter'").fetchone()[0]
                numbers = [int(row[0][2:]) for row in conn.execute("SELECT node_id FROM story_nodes WHERE kind='chapter'") if re.fullmatch(r'CH[0-9]{3,}', row[0])]
                chapter_id = 'CH' + str(max(numbers, default=0) + 1).zfill(3)
                document_id = 'DOC-' + chapter_id
                conn.execute("INSERT INTO story_nodes(node_id,parent_id,kind,ordinal,title,metadata_json) VALUES(?,?,'chapter',?,?,'{}')", (chapter_id, parent_id, ordinal, title))
                conn.execute("INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?,?,'manuscript',?,?)", (document_id, chapter_id, title, now_iso()))
                result = self._receipt(conn, 'chapter_create', key, request, {'schema': 'quillframe_chapter_create_result_v1', 'project_id': project_id, 'chapter_id': chapter_id, 'document_id': document_id, 'ordinal': ordinal, 'authority': False})
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def _plan_target(conn, target_ref: Any) -> tuple[str, int | None]:
        target_ref = text_value(target_ref, 'target_ref')
        if target_ref == 'book':
            return 'DESIGN-BOOK', None
        if target_ref.startswith('chapter:'):
            node = conn.execute("SELECT ordinal FROM story_nodes WHERE node_id=? AND kind='chapter'", (target_ref[8:],)).fetchone()
            if node is not None:
                return 'PLAN-CHAPTER', node['ordinal']
        if target_ref.startswith('volume:'):
            node = conn.execute("SELECT ordinal FROM story_nodes WHERE node_id=? AND kind='volume'", (target_ref[7:],)).fetchone()
            if node is not None:
                return 'DESIGN-VOLUME', None
        raise OperationError('plan_target_invalid', 'plan target is not a registered novel scope')

    def plan_inspect(self, project_id: str, *, target_ref: str | None = None) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            if target_ref is not None:
                self._plan_target(conn, target_ref)
            rows = conn.execute("SELECT * FROM plans WHERE status='active'" + (' AND target_id=?' if target_ref is not None else '') + ' ORDER BY target_id,created_at,plan_id', (target_ref,) if target_ref is not None else ()).fetchall()
            items = []
            for row in rows:
                payload = json_object(row['plan_json'], 'plan')
                items.append({'plan_id': row['plan_id'], 'target_ref': row['target_id'], 'title': payload.get('title', row['target_id']), 'content': payload.get('content', ''), 'version': payload.get('version', 1), 'status': row['status'], 'reader_intent': payload.get('reader_intent', {}), 'expectation_refs': payload.get('expectation_refs', []), 'horizon': payload.get('horizon')})
        return {'schema': 'quillframe_plan_inspection_v1', 'project_id': project_id, 'items': items, 'authority': False}

    def plan_save(self, project_id: str, *, target_ref: str, title: str, content: str, expected_version: int, idempotency_key: str, user_authorized: bool, reader_intent: dict[str, str] | None = None, expectation_refs: list[str] | None = None) -> dict[str, Any]:
        require_authorized(user_authorized)
        title = text_value(title, 'title')
        content = text_value(content, 'content', maximum=200000, empty=True)
        key = text_value(idempotency_key, 'idempotency_key')
        if type(expected_version) is not int or expected_version < 0:
            raise OperationError('invalid_args', 'expected_version must be a non-negative integer')
        reader_intent = reader_intent if reader_intent is not None else {}
        if not isinstance(reader_intent, dict) or set(reader_intent) - READER_INTENT_KEYS:
            raise OperationError('invalid_args', 'reader_intent contains unsupported fields')
        reader_intent = {name: text_value(value, name, maximum=4000, empty=True) for name, value in reader_intent.items()}
        expectation_refs = expectation_refs if expectation_refs is not None else []
        if not isinstance(expectation_refs, list) or len(expectation_refs) > 100:
            raise OperationError('invalid_args', 'expectation_refs must be a bounded list')
        expectation_refs = [text_value(value, 'expectation_ref') for value in expectation_refs]
        if len(set(expectation_refs)) != len(expectation_refs):
            raise OperationError('invalid_args', 'expectation_refs must be unique')
        request = {'operation': 'plan.save', 'project_id': project_id, 'target_ref': target_ref, 'title': title, 'content': content, 'expected_version': expected_version, 'reader_intent': reader_intent, 'expectation_refs': expectation_refs}
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                prior = self._replay(conn, 'plan_save', key, request)
                if prior:
                    conn.commit()
                    return prior
                mode, order = self._plan_target(conn, target_ref)
                for reference in expectation_refs:
                    if conn.execute('SELECT 1 FROM expectations WHERE expectation_id=?', (reference,)).fetchone() is None:
                        raise OperationError('expectation_not_found', 'plan references an unknown reader expectation')
                existing = conn.execute("SELECT * FROM plans WHERE target_id=? AND status='active' ORDER BY updated_at DESC,rowid DESC LIMIT 1", (target_ref,)).fetchone()
                before_version = json_object(existing['plan_json'], 'plan').get('version', 1) if existing else 0
                if expected_version != before_version:
                    raise OperationError('plan_version_conflict', 'plan changed after it was opened', detail={'actual_version': before_version})
                plan_id = existing['plan_id'] if existing else 'plan_' + uuid.uuid4().hex
                version = before_version + 1
                policy = normalize_policy({'schema': 'quillframe_planning_horizon_policy_v1', 'profile_id': 'author-confirmed-serial', 'strength_depth_ceiling': {'open': 'arc_boundary', 'soft': 'beat', 'hard': 'chapter_detail'}, 'allowed_promoter_actor_classes': ['user']})
                region = create_region(policy, {'schema': 'quillframe_planning_horizon_region_request_v1', 'project_id': project_id, 'region_id': plan_id + ':' + str(version), 'plan_ref': plan_id, 'commitment_strength': 'hard' if order is not None else 'open', 'max_planning_depth': 'chapter_detail' if order is not None else 'arc_boundary', 'story_order': {'start': order, 'end': order} if order is not None else None, 'dependency_refs': expectation_refs})
                admission = admit_realization(policy, region, {'schema': 'quillframe_planning_horizon_admission_request_v1', 'region_id': region['region_id'], 'expected_version': region['version'], 'expected_fingerprint': region['artifact_fingerprint'], 'artifact_kind': 'chapter_plan' if order is not None else 'arc_role'})
                if admission['status'] != 'allowed':
                    raise OperationError('planning_depth_not_admitted', 'plan exceeds its author-confirmed commitment horizon')
                payload = {'title': title, 'content': content, 'version': version, 'reader_intent': reader_intent, 'expectation_refs': expectation_refs, 'horizon': {'policy': policy, 'region': region, 'admission': admission}}
                stamp = now_iso()
                payload_fp = fingerprint_text(canonical_json(payload))
                if existing:
                    conn.execute('UPDATE plans SET plan_json=?,content_fingerprint=?,updated_at=? WHERE plan_id=?', (canonical_json(payload), payload_fp, stamp, plan_id))
                else:
                    conn.execute("INSERT INTO plans(plan_id,task_mode,target_id,status,plan_json,content_fingerprint,created_at,updated_at) VALUES(?,?,?,'active',?,?,?,?)", (plan_id, mode, target_ref, canonical_json(payload), payload_fp, stamp, stamp))
                conn.execute('INSERT INTO plan_versions(plan_id,version,payload_json,content_fingerprint,created_at) VALUES(?,?,?,?,?)', (plan_id, version, canonical_json(payload), payload_fp, stamp))
                result = self._receipt(conn, 'plan_save', key, request, {'schema': 'quillframe_plan_save_result_v1', 'project_id': project_id, 'target_ref': target_ref, 'plan_id': plan_id, **payload, 'status': 'active', 'authority': False})
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    def story_inspect(self, project_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            characters = [{**dict(row), 'state': json.loads(row['state_json']), 'authority_class': 'accepted'} for row in conn.execute('SELECT * FROM characters ORDER BY character_id')]
            relationships = [{**dict(row), 'state': json.loads(row['state_json']), 'authority_class': 'accepted'} for row in conn.execute('SELECT * FROM relationships ORDER BY relationship_id')]
            world = [{**dict(row), 'truth': json.loads(row['truth_json']), 'authority_class': 'accepted'} for row in conn.execute('SELECT * FROM world_entities ORDER BY entity_id')]
            timeline = [dict(row) for row in conn.execute('SELECT * FROM timeline_events ORDER BY story_order,event_id')]
            canon = [{**dict(row), 'value': json.loads(row['value_json'])} for row in conn.execute('SELECT * FROM canon_state ORDER BY state_key')]
            dependencies = [dict(row) for row in conn.execute('SELECT chapter_id,source_chapter_id,source_fingerprint,run_id,status FROM chapter_dependencies ORDER BY chapter_id,source_chapter_id,created_at')]
            sources = {(row['entity_type'], row['entity_id']): dict(row) for row in conn.execute('SELECT * FROM narrative_state_sources')}
            for entity_type, rows, key in (('character', characters, 'character_id'), ('relationship', relationships, 'relationship_id'),
                                            ('world', world, 'entity_id'), ('timeline', timeline, 'event_id')):
                for row in rows:
                    origin = sources.get((entity_type, row[key]))
                    row['source_state'] = origin['state'] if origin else 'untracked'
                    row['source_chapter_id'] = origin['chapter_id'] if origin else None
        for rows, raw in ((characters, 'state_json'), (relationships, 'state_json'), (world, 'truth_json'), (canon, 'value_json')):
            for row in rows:
                row.pop(raw, None)
        return {'schema': 'quillframe_story_inspection_v1', 'project_id': project_id, 'characters': characters, 'relationships': relationships, 'timeline': timeline, 'canon': canon, 'dependencies': dependencies, 'world': world, 'authority': False}
