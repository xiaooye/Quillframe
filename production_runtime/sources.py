from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Protocol

from agent_runtime import AgentJob, AgentResult
from harness.context_runtime import fingerprint
from persistence.context_repository import ContextRepository
from persistence.quillframe_sqlite import QuillframeStore

from .contracts import MECHANISM_CONTEXT_STAGE, assert_secret_free


class AgentRuntimeLike(Protocol):
    def run(self, job: AgentJob, *, cancellation: Any = None) -> AgentResult: ...


CONTEXT_STAGE_IDS = tuple(dict.fromkeys(MECHANISM_CONTEXT_STAGE.values()))


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return deepcopy(fallback)


def _source(*, object_id: str, object_type: str, authority: str, lifecycle: str,
            domain: str, model_view: dict[str, Any], profile: dict[str, Any] | None,
            status: str | None = None) -> dict[str, Any]:
    assert_secret_free(model_view, label=f"context source {object_id}")
    return {
        "object_id": object_id, "object_type": object_type, "authority": authority,
        "lifecycle": lifecycle, "domain": domain, "source_fingerprint": fingerprint(model_view),
        "stages": list(CONTEXT_STAGE_IDS), "model_view": model_view, "profile": profile, "status": status,
    }


class ProjectContextSourceLoader:
    """Tracked pre-freeze Project read; stage workers never receive this loader."""

    def __init__(self, store: QuillframeStore, context_repository: ContextRepository) -> None:
        self.store = store
        self.context_repository = context_repository

    def load(self, project_id: str) -> list[dict[str, Any]]:
        current_profiles: dict[str, dict[str, Any]] = {}
        for profile in self.context_repository.list_profiles(project_id):
            if profile.get("status") == "current" and profile.get("source_object_id") not in current_profiles:
                current_profiles[str(profile["source_object_id"])] = profile
        p = current_profiles.get
        items: list[dict[str, Any]] = []
        with self.store.open_project(project_id) as conn:
            for row in conn.execute("SELECT * FROM characters ORDER BY character_id"):
                view = {"character_id": row["character_id"], "name": row["name"], "agenda": row["agenda"], "voice_notes": row["voice_notes"], "state": _json(row["state_json"], {})}
                items.append(_source(object_id=row["character_id"], object_type="character", authority="accepted", lifecycle="accepted", domain="character", model_view=view, profile=p(row["character_id"])))
            for row in conn.execute("SELECT * FROM relationships ORDER BY relationship_id"):
                view = {"relationship_id": row["relationship_id"], "participant_a": row["participant_a"], "participant_b": row["participant_b"], "relationship_type": row["relationship_type"], "state": _json(row["state_json"], {})}
                items.append(_source(object_id=row["relationship_id"], object_type="relationship", authority="accepted", lifecycle="accepted", domain="relationship", model_view=view, profile=p(row["relationship_id"])))
            for row in conn.execute("SELECT * FROM world_entities ORDER BY entity_id"):
                view = {"entity_id": row["entity_id"], "entity_type": row["entity_type"], "name": row["name"], "truth": _json(row["truth_json"], {})}
                items.append(_source(object_id=row["entity_id"], object_type="world_fact", authority="accepted", lifecycle="accepted", domain="world", model_view=view, profile=p(row["entity_id"])))
            for row in conn.execute("SELECT * FROM locations ORDER BY location_id"):
                view = {"location_id": row["location_id"], "name": row["name"], "description": row["description"], "state": _json(row["state_json"], {})}
                items.append(_source(object_id=row["location_id"], object_type="location", authority="accepted", lifecycle="accepted", domain="location", model_view=view, profile=p(row["location_id"])))
            for row in conn.execute("SELECT * FROM timeline_events ORDER BY story_order,event_id"):
                authority = str(row["authority_class"])
                view = {"event_id": row["event_id"], "story_order": row["story_order"], "title": row["title"], "description": row["description"], "source_ref": row["source_ref"]}
                items.append(_source(object_id=row["event_id"], object_type="timeline_event", authority=authority, lifecycle=authority, domain="timeline", model_view=view, profile=p(row["event_id"])))
            for row in conn.execute("SELECT * FROM story_nodes ORDER BY kind,ordinal,node_id"):
                view = {"node_id": row["node_id"], "parent_id": row["parent_id"], "kind": row["kind"], "ordinal": row["ordinal"], "title": row["title"], "pov_character_id": row["pov_character_id"], "location_id": row["location_id"], "metadata": _json(row["metadata_json"], {})}
                items.append(_source(object_id=row["node_id"], object_type="story_node", authority="active_plan", lifecycle="active_plan", domain="story", model_view=view, profile=p(row["node_id"])))
            for row in conn.execute("SELECT * FROM plans ORDER BY updated_at,plan_id"):
                status = str(row["status"]); authority = "active_plan" if status in {"active", "completed"} else "proposal"; lifecycle = "superseded" if status in {"superseded", "completed"} else authority
                view = {"plan_id": row["plan_id"], "task_mode": row["task_mode"], "target_id": row["target_id"], "plan": _json(row["plan_json"], {})}
                items.append(_source(object_id=row["plan_id"], object_type="plan", authority=authority, lifecycle=lifecycle, domain="plan", model_view=view, profile=p(row["plan_id"]), status=status))
            for row in conn.execute("SELECT * FROM canon_claims ORDER BY claim_id"):
                authority = str(row["authority_class"])
                view = {"claim_id": row["claim_id"], "subject_ref": row["subject_ref"], "predicate": row["predicate"], "value": _json(row["value_json"], None), "evidence_ref": row["evidence_ref"], "valid_from_story_order": row["valid_from_story_order"], "valid_to_story_order": row["valid_to_story_order"]}
                items.append(_source(object_id=row["claim_id"], object_type="canon_claim", authority=authority, lifecycle=authority, domain="canon", model_view=view, profile=p(row["claim_id"])))
            for row in conn.execute("SELECT * FROM character_knowledge ORDER BY knowledge_id"):
                view = {"knowledge_id": row["knowledge_id"], "character_id": row["character_id"], "claim_ref": row["claim_ref"], "fact": _json(row["fact_json"], {}), "available_from_story_order": row["available_from_story_order"], "evidence_ref": row["evidence_ref"], "confidence": row["confidence"]}
                items.append(_source(object_id=row["knowledge_id"], object_type="character_knowledge", authority="accepted", lifecycle="accepted", domain="character_knowledge", model_view=view, profile=p(row["knowledge_id"])))
            for row in conn.execute("SELECT * FROM research_claims ORDER BY research_claim_id"):
                view = {"research_claim_id": row["research_claim_id"], "source_id": row["source_id"], "claim_text": row["claim_text"], "citation": _json(row["citation_json"], {}), "fictionalization_notes": row["fictionalization_notes"], "character_knowledge_boundary": _json(row["character_knowledge_boundary_json"], {}), "canon_status": row["canon_status"]}
                items.append(_source(object_id=row["research_claim_id"], object_type="research", authority="research", lifecycle="active", domain="research", model_view=view, profile=p(row["research_claim_id"])))
            for row in conn.execute("SELECT r.*,d.title,d.story_node_id FROM document_revisions r JOIN documents d ON d.document_id=r.document_id WHERE r.authority_class='accepted' ORDER BY r.created_at,r.revision_id"):
                oid = str(row["revision_id"]); view = {"revision_id": oid, "document_id": row["document_id"], "title": row["title"], "story_node_id": row["story_node_id"], "content": row["content"]}
                items.append(_source(object_id=oid, object_type="accepted_manuscript", authority="accepted", lifecycle="accepted", domain="manuscript", model_view=view, profile=p(oid)))
        return items

    @staticmethod
    def state_projection(items: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, dict[str, Any]], str]:
        fingerprints = {str(item["object_id"]): str(item["source_fingerprint"]) for item in items}
        states = {str(item["object_id"]): {"source_fingerprint": item["source_fingerprint"], "authority": item["authority"], "lifecycle": item["lifecycle"], "domain": item["domain"], "exclusion": None} for item in items}
        return fingerprints, states, fingerprint({key: states[key] for key in sorted(states)})
