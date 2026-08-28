"""Author-confirmed, fingerprint-bound chapter and narrative-state settlement."""
from __future__ import annotations

import json
import uuid
from typing import Any

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import canonical_json, fingerprint_text, now_iso
from quillframe.novel import acceptance_target, current_head, invalidate_dependencies, latest_acceptance, text_value


def digest(value: Any) -> str:
    return fingerprint_text(canonical_json(value))


class ChapterSettlement:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _source(conn, acceptance_id: str, target_ref: str):
        row = conn.execute("""SELECT a.*,c.run_id,c.revision_id,c.document_id,c.content_fingerprint,
            c.status AS candidate_status,c.user_visible_gate,r.content,r.authority_class,r.source,
            r.document_id AS revision_document_id,r.content_fingerprint AS revision_fingerprint
            FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
            LEFT JOIN document_revisions r ON r.revision_id=c.revision_id WHERE a.acceptance_id=?""", (acceptance_id,)).fetchone()
        if row is None:
            raise OperationError('acceptance_not_found', 'acceptance does not exist')
        value = dict(row)
        if (value['candidate_status'] != 'accepted' or value['authority_class'] != 'accepted'
                or value['revision_document_id'] != value['document_id']
                or value['candidate_fingerprint'] != value['content_fingerprint']
                or value['revision_fingerprint'] != value['content_fingerprint']
                or not isinstance(value['content'], str) or fingerprint_text(value['content']) != value['content_fingerprint']):
            raise OperationError('not_settleable', 'accepted manuscript bytes and identity must still match')
        CoreOperations._validated_production_release(conn, value)
        target = acceptance_target(conn, value, target_ref)
        latest = latest_acceptance(conn, value['document_id'])
        if latest is None or latest['acceptance_id'] != acceptance_id:
            raise OperationError('settlement_source_superseded', 'only the latest author acceptance may become the chapter head')
        for dependency in conn.execute('SELECT * FROM chapter_dependencies WHERE chapter_id=? AND run_id=?', (target['chapter_id'], value['run_id'])):
            source_doc = conn.execute("SELECT document_id FROM documents WHERE story_node_id=? AND document_kind='manuscript'", (dependency['source_chapter_id'],)).fetchall()
            head = current_head(conn, dependency['source_chapter_id'], source_doc[0]['document_id'])[0] if len(source_doc) == 1 else None
            if dependency['status'] != 'current' or head is None or head['head_fingerprint'] != dependency['source_fingerprint']:
                raise OperationError('chapter_dependencies_stale', 'a preceding chapter changed after this run was frozen')
        return value, target

    @staticmethod
    def _proposal(conn, source: dict[str, Any], target: dict[str, Any]):
        from production_runtime.semantic import build_narrative_state_proposal, narrative_before_fingerprint
        from production_runtime.contracts import ProductionRunError
        row = conn.execute("SELECT * FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_narrative_proposal' ORDER BY created_at DESC,rowid DESC LIMIT 1", (source['run_id'],)).fetchone()
        if row is None:
            if source['source'] == 'production_runtime':
                raise OperationError('narrative_proposal_missing', 'production settlement requires final-manuscript state evidence')
            return None
        try:
            stored = json.loads(row['state_json'])
            proposal = stored['proposal']
            context = conn.execute("SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_context_bundle' AND artifact_fingerprint=? ORDER BY created_at DESC,rowid DESC LIMIT 1", (source['run_id'], proposal['context_bundle_fingerprint'])).fetchone()
            if context is None:
                raise ValueError('frozen narrative context is missing')
            bundle = json.loads(context['state_json'])
            rebuilt = build_narrative_state_proposal(stored['registered_binding'], bundle)
            if rebuilt != proposal or row['artifact_fingerprint'] != proposal['proposal_fingerprint']:
                raise ValueError('narrative proposal differs from its registered evidence')
            if (proposal['candidate_fingerprint'] != source['content_fingerprint']
                    or proposal['chapter_id'] != target['chapter_id'] or proposal['document_id'] != target['document_id']
                    or stored['registered_binding']['job']['input']['payload']['candidate_text'] != source['content']):
                raise ValueError('narrative proposal does not bind the accepted manuscript')
            for change in proposal['changes']:
                if narrative_before_fingerprint(conn, change['entity_type'], change['entity_id']) != change['before_state_fingerprint']:
                    raise OperationError('narrative_state_conflict', 'narrative source changed since the final manuscript was reviewed')
            return proposal
        except OperationError:
            raise
        except (ValueError, KeyError, TypeError, ProductionRunError) as exc:
            raise OperationError('narrative_proposal_invalid', 'final-manuscript narrative evidence could not be verified') from exc

    def _preflight(self, conn, project_id: str, acceptance_id: str, target_ref: str):
        source, target = self._source(conn, acceptance_id, target_ref)
        if conn.execute("SELECT 1 FROM settlements WHERE acceptance_id=? AND target_ref=? AND status='settled'", (acceptance_id, target_ref)).fetchone():
            raise OperationError('not_settleable', 'acceptance is already settled to this chapter')
        current = conn.execute('SELECT * FROM canon_state WHERE state_key=?', (target_ref,)).fetchone()
        if current and digest(json.loads(current['value_json'])) != current['content_fingerprint']:
            raise OperationError('canon_state_invalid', 'current chapter head fingerprint is invalid')
        before = current['content_fingerprint'] if current else 'absent'
        proposal = self._proposal(conn, source, target)
        from quality.reader_expectation import inspect_project
        observations = [item for item in inspect_project(conn)['observations']
                        if item['candidate_id'] == source['candidate_id'] and item['state'] == 'proposed']
        result = {'schema': 'quillframe_settlement_preflight_v1', 'project_id': project_id,
                  'acceptance_id': acceptance_id, 'candidate_id': source['candidate_id'],
                  'candidate_fingerprint': source['candidate_fingerprint'], 'document_id': source['document_id'],
                  'revision_id': source['revision_id'], 'chapter_id': target['chapter_id'], 'target_ref': target_ref,
                  'expected_before_fingerprint': before, 'current_before_fingerprint': before,
                  'narrative_proposal': proposal, 'reader_observations': observations,
                  'settleable': True, 'mutation_performed': False, 'canon_mutated': False, 'authority': False}
        result['preflight_fingerprint'] = digest(result)
        return result, source, target, current

    def preflight(self, project_id: str, *, acceptance_id: str, target_ref: str):
        with self.store.open_project(project_id) as conn:
            return self._preflight(conn, project_id, acceptance_id, target_ref)[0]

    @staticmethod
    def _apply_narrative(conn, proposal, *, source, target, stamp):
        from production_runtime.semantic import narrative_before_fingerprint
        changes = proposal['changes'] if proposal else []
        results = []
        # All before-state guards were checked together; create characters before references.
        for change in sorted(changes, key=lambda item: item['entity_type'] != 'character'):
            kind, entity_id, fields = change['entity_type'], change['entity_id'], change['fields']
            table, key = {'character': ('characters', 'character_id'), 'relationship': ('relationships', 'relationship_id'),
                          'world': ('world_entities', 'entity_id'), 'timeline': ('timeline_events', 'event_id'),
                          'knowledge': ('character_knowledge', 'knowledge_id')}[kind]
            prior = conn.execute(f'SELECT * FROM {table} WHERE {key}=?', (entity_id,)).fetchone()
            if kind == 'character':
                conn.execute('INSERT INTO characters(character_id,name,agenda,voice_notes,state_json,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(character_id) DO UPDATE SET name=excluded.name,agenda=excluded.agenda,voice_notes=excluded.voice_notes,state_json=excluded.state_json,updated_at=excluded.updated_at', (entity_id, fields['name'], fields['agenda'], fields['voice_notes'], canonical_json(fields['state']), stamp))
            elif kind == 'relationship':
                conn.execute('INSERT INTO relationships(relationship_id,participant_a,participant_b,relationship_type,state_json,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(relationship_id) DO UPDATE SET participant_a=excluded.participant_a,participant_b=excluded.participant_b,relationship_type=excluded.relationship_type,state_json=excluded.state_json,updated_at=excluded.updated_at', (entity_id, fields['participant_a'], fields['participant_b'], fields['relationship_type'], canonical_json(fields['state']), stamp))
            elif kind == 'world':
                conn.execute('INSERT INTO world_entities(entity_id,entity_type,name,truth_json,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(entity_id) DO UPDATE SET entity_type=excluded.entity_type,name=excluded.name,truth_json=excluded.truth_json,updated_at=excluded.updated_at', (entity_id, fields['entity_type'], fields['name'], canonical_json(fields['truth']), stamp))
            elif kind == 'timeline':
                conn.execute("INSERT INTO timeline_events(event_id,story_order,title,description,authority_class,source_ref) VALUES(?,?,?,?,'accepted',?) ON CONFLICT(event_id) DO UPDATE SET story_order=excluded.story_order,title=excluded.title,description=excluded.description,authority_class='accepted',source_ref=excluded.source_ref", (entity_id, fields['story_order'], fields['title'], fields['description'], 'chapter:' + target['chapter_id']))
            elif kind == 'knowledge':
                conn.execute('INSERT INTO character_knowledge(knowledge_id,character_id,claim_ref,fact_json,available_from_story_order,evidence_ref,confidence) VALUES(?,?,NULL,?,?,?,?) ON CONFLICT(knowledge_id) DO UPDATE SET character_id=excluded.character_id,claim_ref=NULL,fact_json=excluded.fact_json,available_from_story_order=excluded.available_from_story_order,evidence_ref=excluded.evidence_ref,confidence=excluded.confidence', (entity_id, fields['character_id'], canonical_json(fields['fact']), fields['available_from_story_order'], 'chapter:' + target['chapter_id'], fields['confidence']))
            conn.execute("INSERT INTO narrative_state_sources(entity_type,entity_id,chapter_id,acceptance_id,source_fingerprint,state,updated_at) VALUES(?,?,?,?,?,'current',?) ON CONFLICT(entity_type,entity_id) DO UPDATE SET chapter_id=excluded.chapter_id,acceptance_id=excluded.acceptance_id,source_fingerprint=excluded.source_fingerprint,state='current',updated_at=excluded.updated_at", (kind, entity_id, target['chapter_id'], source['acceptance_id'], source['content_fingerprint'], stamp))
            results.append({**change, 'before_state': dict(prior) if prior else None,
                            'after_state_fingerprint': narrative_before_fingerprint(conn, kind, entity_id)})
        return results

    def settle(self, project_id: str, *, acceptance_id: str, target_ref: str, expected_before_fingerprint: str,
               user_authorized: bool, idempotency_key: str, expected_preflight_fingerprint: str | None = None):
        if user_authorized is not True:
            raise OperationError('authorization_required', 'settlement requires explicit author confirmation')
        text_value(idempotency_key, 'idempotency_key')
        request_fp = digest({'project_id': project_id, 'acceptance_id': acceptance_id, 'target_ref': target_ref,
                             'expected_before_fingerprint': expected_before_fingerprint,
                             'expected_preflight_fingerprint': expected_preflight_fingerprint})
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                replay = CoreOperations._idempotency_replay_or_conflict(conn, idempotency_key=idempotency_key, receipt_kind='settlement', request_fingerprint=request_fp)
                if replay is not None:
                    conn.commit()
                    return replay
                source, target = self._source(conn, acceptance_id, target_ref)
                current = conn.execute('SELECT * FROM canon_state WHERE state_key=?', (target_ref,)).fetchone()
                before = current['content_fingerprint'] if current else 'absent'
                stamp, settlement_id = now_iso(), 'settle_' + uuid.uuid4().hex
                if before != expected_before_fingerprint:
                    result = {'schema': 'quillframe_settlement_result_v1', 'settlement_id': settlement_id,
                              'status': 'settlement_incomplete', 'target_ref': target_ref,
                              'expected_before_fingerprint': expected_before_fingerprint, 'actual_before_fingerprint': before,
                              'canon_mutated': False, 'request_fingerprint': request_fp}
                    conn.execute("INSERT INTO settlements(settlement_id,acceptance_id,target_ref,before_fingerprint,state_delta_json,status,receipt_json,created_at) VALUES(?,?,?,?,?,'settlement_incomplete',?,?)", (settlement_id, acceptance_id, target_ref, before, '{}', canonical_json(result), stamp))
                else:
                    preflight, source, target, current = self._preflight(conn, project_id, acceptance_id, target_ref)
                    derived = preflight['narrative_proposal'] is not None or bool(preflight['reader_observations'])
                    if (derived or expected_preflight_fingerprint is not None) and expected_preflight_fingerprint != preflight['preflight_fingerprint']:
                        raise OperationError('settlement_preflight_changed', 'review the current state proposal before confirming settlement')
                    value = {key: source[key] for key in ('acceptance_id', 'candidate_id', 'document_id', 'revision_id', 'content_fingerprint', 'run_id')}
                    value.update(chapter_id=target['chapter_id'], reading_order=target['current_reading_order'])
                    after = digest(value)
                    affected = invalidate_dependencies(conn, target['chapter_id'], before, after)
                    from quality.reader_expectation import apply_observation, invalidate_source
                    invalidations = {'observation_ids': [], 'expectation_ids': []}
                    previous = json.loads(current['value_json']) if current else None
                    if previous and previous.get('content_fingerprint') != source['content_fingerprint']:
                        invalidations = invalidate_source(conn, chapter_id=target['chapter_id'], source_fingerprint=previous.get('content_fingerprint'))
                        conn.execute("UPDATE narrative_state_sources SET state='stale',updated_at=? WHERE chapter_id=? AND source_fingerprint=?", (stamp, target['chapter_id'], previous.get('content_fingerprint')))
                    for chapter_id in affected:
                        conn.execute("UPDATE narrative_state_sources SET state='stale',updated_at=? WHERE chapter_id=?", (stamp, chapter_id))
                    narrative = self._apply_narrative(conn, preflight['narrative_proposal'], source=source, target=target, stamp=stamp)
                    conn.execute("INSERT INTO canon_state(state_key,value_json,authority_class,evidence_ref,content_fingerprint,updated_at) VALUES(?,?,'accepted',?,?,?) ON CONFLICT(state_key) DO UPDATE SET value_json=excluded.value_json,authority_class='accepted',evidence_ref=excluded.evidence_ref,content_fingerprint=excluded.content_fingerprint,updated_at=excluded.updated_at", (target_ref, canonical_json(value), acceptance_id, after, stamp))
                    delta = {'before': dict(current) if current else None, 'after': value, 'narrative_changes': narrative,
                             'stale_chapter_ids': affected, 'reader_invalidations': invalidations}
                    result = {'schema': 'quillframe_settlement_result_v1', 'settlement_id': settlement_id, 'status': 'settled',
                              'target_ref': target_ref, 'before_fingerprint': before, 'after_fingerprint': after,
                              'state_delta': delta, 'canon_mutated': True, 'request_fingerprint': request_fp}
                    conn.execute("INSERT INTO settlements(settlement_id,acceptance_id,target_ref,before_fingerprint,after_fingerprint,state_delta_json,status,receipt_json,created_at,completed_at) VALUES(?,?,?,?,?,?,'settled',?,?,?)", (settlement_id, acceptance_id, target_ref, before, after, canonical_json(delta), canonical_json(result), stamp, stamp))
                    memories = [apply_observation(conn, observation_id=item['observation_id'], acceptance_id=acceptance_id,
                                                  user_authorized=True, authorized_by=source['authorized_by'],
                                                  idempotency_key='settle-reader:' + settlement_id + ':' + item['observation_id'])
                                for item in preflight['reader_observations']]
                    result['reader_memory'] = memories
                    conn.execute('UPDATE settlements SET receipt_json=? WHERE settlement_id=?', (canonical_json(result), settlement_id))
                conn.execute('INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?)', ('rcpt_' + uuid.uuid4().hex, 'settlement', idempotency_key, canonical_json(result), stamp))
                conn.commit()
                return result
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
