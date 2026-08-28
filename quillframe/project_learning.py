"""Core source binding and trusted execution for Project-only learning."""
from __future__ import annotations

from typing import Any, Callable

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import fingerprint_text


class ProjectLearningOperations:
    def __init__(self, store, learning):
        self.store = store
        self.learning = learning

    def _project(self, project_id: str) -> None:
        with self.store.open_project(project_id):
            pass

    def _source(self, project_id: str, *, candidate_id: str, candidate_fingerprint: str,
                document_id: str, run_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("""SELECT c.*,r.content,r.content_fingerprint AS revision_fingerprint,
                r.document_id AS revision_document_id,d.story_node_id,u.session_id,u.created_at AS run_created_at
                FROM candidates c JOIN document_revisions r ON r.revision_id=c.revision_id
                JOIN documents d ON d.document_id=c.document_id JOIN runs u ON u.run_id=c.run_id
                WHERE c.candidate_id=?""", (candidate_id,)).fetchone()
            if row is None:
                raise OperationError('feedback_source_missing', 'feedback requires an existing released candidate')
            source = dict(row)
            if (source['run_id'] != run_id or source['document_id'] != document_id
                    or source['revision_document_id'] != document_id
                    or source['content_fingerprint'] != candidate_fingerprint
                    or source['revision_fingerprint'] != candidate_fingerprint
                    or fingerprint_text(source['content']) != candidate_fingerprint):
                raise OperationError('feedback_source_mismatch', 'feedback does not bind this exact candidate, document and run')
            if not source['session_id'] or not source['story_node_id']:
                raise OperationError('feedback_source_mismatch', 'feedback source requires a registered chapter and runtime session')
            CoreOperations._validated_production_release(conn, source)
        return {'run_id': source['run_id'], 'session_id': source['session_id'],
                'created_at': source['run_created_at'], 'task_mode': 'LEARN',
                'chapter_id': source['story_node_id']}

    def observe(self, project_id: str, *, event_id: str, feedback_text: str, evidence_kind: str,
                candidate_id: str, candidate_fingerprint: str, document_id: str, run_id: str,
                source_type: str = 'author', source_id: str = 'author') -> dict[str, Any]:
        bound = self._source(project_id, candidate_id=candidate_id, candidate_fingerprint=candidate_fingerprint,
                             document_id=document_id, run_id=run_id)
        return self.learning.observe(project_id=project_id, event_id=event_id, feedback_text=feedback_text,
            evidence_kind=evidence_kind, candidate_id=candidate_id, candidate_fingerprint=candidate_fingerprint,
            document_id=document_id, run_id=run_id, session_id=bound['session_id'], source_type=source_type,
            source_id=source_id, current_task={'task_mode': 'LEARN', 'chapter_id': bound['chapter_id']})

    def get_feedback(self, project_id: str, *, event_id: str) -> dict[str, Any]:
        self._project(project_id)
        return self.learning.get_feedback(project_id=project_id, event_id=event_id)

    def list_feedback(self, project_id: str, *, limit: int = 50) -> dict[str, Any]:
        self._project(project_id)
        return self.learning.list_feedback(project_id=project_id, limit=limit)

    def _feedback_source(self, project_id: str, event: dict[str, Any]):
        source = self._source(project_id, **{key: event[key] for key in
            ('candidate_id', 'candidate_fingerprint', 'document_id', 'run_id')})
        if source['session_id'] != event['session_id']:
            raise OperationError('feedback_source_mismatch', 'feedback session no longer matches its original run')
        return source

    @staticmethod
    def _runner(runtime, *, source: dict[str, Any], service_id: str, model_id: str | None,
                contract_id: str, validate_source: Callable[[], Any]):
        from production_runtime.semantic import RegisteredSemanticExecutor

        def execute(job):
            if job.get('input', {}).get('model_contract_id') != contract_id:
                raise OperationError('learning_contract_mismatch', 'learning may execute only its prepared registered contract')
            validate_source()
            binding = RegisteredSemanticExecutor(runtime).execute_prepared(semantic_job=job, run=source,
                service_id=service_id, model_preference=model_id, runtime_role=contract_id.replace('.', '_'))
            # A slow model response cannot outlive the evidence that authorized it.
            validate_source()
            return binding['result']
        return execute

    def execute(self, project_id: str, *, event_id: str, service_id: str, model_id: str | None, runtime):
        from learning.feedback_intake import CONTRACT_ID
        event = self.get_feedback(project_id, event_id=event_id)
        source = self._feedback_source(project_id, event)
        return self.learning.execute(project_id=project_id, event_id=event_id, run_semantic=self._runner(
            runtime, source=source, service_id=service_id, model_id=model_id, contract_id=CONTRACT_ID,
            validate_source=lambda: self._feedback_source(project_id, event)))

    def list_preferences(self, project_id: str, *, limit: int = 100):
        self._project(project_id)
        return self.learning.list_preferences(project_id=project_id, limit=limit)

    def get_preference(self, project_id: str, *, hypothesis_id: str):
        self._project(project_id)
        return self.learning.get_preference(project_id=project_id, hypothesis_id=hypothesis_id)

    def _preference_sources(self, project_id: str, hypothesis_id: str):
        preference = self.get_preference(project_id, hypothesis_id=hypothesis_id)
        sources = []
        for evidence in preference['evidence']:
            event = self.get_feedback(project_id, event_id=evidence['feedback_event_ref'])
            if event.get('source_type') not in {'author', 'human_reader'}:
                raise OperationError('human_feedback_required', 'project preferences require explicit human feedback')
            sources.append(self._feedback_source(project_id, event))
        if not sources:
            raise OperationError('feedback_source_missing', 'preference review requires its original bound feedback')
        return sources

    def review(self, project_id: str, *, hypothesis_id: str, expected_version: int,
               service_id: str, model_id: str | None, runtime):
        sources = self._preference_sources(project_id, hypothesis_id)
        return self.learning.execute_activation_review(project_id=project_id, hypothesis_id=hypothesis_id,
            expected_version=expected_version, run_semantic=self._runner(runtime, source=sources[0],
                service_id=service_id, model_id=model_id, contract_id='learning.promotion_review',
                validate_source=lambda: self._preference_sources(project_id, hypothesis_id)))

    def activate(self, project_id: str, **args):
        self._preference_sources(project_id, args['hypothesis_id'])
        return self.learning.activate(project_id=project_id, **args)

    def deactivate(self, project_id: str, **args):
        self._project(project_id)
        return self.learning.deactivate(project_id=project_id, **args)
