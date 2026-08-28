from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Protocol

from agent_runtime import AgentJob, AgentResult
from harness.context_runtime import fingerprint
from persistence.context_repository import ContextRepository
from persistence.quillframe_sqlite import QuillframeStore, fingerprint_text
from quality.reader_expectation import pressure_report

from .contracts import MECHANISM_CONTEXT_STAGE, ProductionRunError, assert_secret_free


class AgentRuntimeLike(Protocol):
    def run(self, job: AgentJob, *, cancellation: Any = None) -> AgentResult: ...


CONTEXT_STAGE_IDS = tuple(dict.fromkeys(MECHANISM_CONTEXT_STAGE.values()))
BLIND_READER_STAGES = {"reader_engagement", "independent_review"}
EDITOR_STAGE_IDS = tuple(stage for stage in CONTEXT_STAGE_IDS if stage not in BLIND_READER_STAGES)


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return deepcopy(fallback)


def _source(*, object_id: str, object_type: str, authority: str, lifecycle: str,
            domain: str, model_view: dict[str, Any], profile: dict[str, Any] | None,
            status: str | None = None, stages: tuple[str, ...] = EDITOR_STAGE_IDS,
            pinned: bool = False) -> dict[str, Any]:
    assert_secret_free(model_view, label=f"context source {object_id}")
    return {
        "object_id": object_id, "object_type": object_type, "authority": authority,
        "lifecycle": lifecycle, "domain": domain, "source_fingerprint": fingerprint(model_view),
        "stages": list(stages), "model_view": model_view, "profile": profile, "status": status,
        "pinned": pinned, "required_for_grounding": pinned,
        "pinned_stages": list(stages) if pinned else [],
    }


class ProjectContextSourceLoader:
    """Tracked pre-freeze Project read; stage workers never receive this loader."""

    def __init__(self, store: QuillframeStore, context_repository: ContextRepository) -> None:
        self.store = store
        self.context_repository = context_repository

    def load(self, project_id: str, *, chapter_id: str, document_id: str,
             current_story_order: int, current_reading_order: int) -> list[dict[str, Any]]:
        for value in (current_story_order, current_reading_order):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ProductionRunError("target_context_invalid", "context requires explicit non-negative chronology cutoffs")
        current_profiles: dict[str, dict[str, Any]] = {}
        for profile in self.context_repository.list_profiles(project_id):
            if profile.get("status") == "current" and profile.get("source_object_id") not in current_profiles:
                current_profiles[str(profile["source_object_id"])] = profile
        p = current_profiles.get
        items: list[dict[str, Any]] = []
        with self.store.open_project(project_id) as conn:
            target = conn.execute(
                "SELECT n.*,d.document_id,d.document_kind FROM story_nodes n JOIN documents d ON d.story_node_id=n.node_id "
                "WHERE n.node_id=? AND d.document_id=?", (chapter_id, document_id),
            ).fetchone()
            if not target or target["kind"] != "chapter" or target["document_kind"] != "manuscript":
                raise ProductionRunError("target_context_invalid", "frozen chapter/document association no longer exists")
            metadata = _json(target["metadata_json"], {})
            story_order = metadata.get("story_order", target["ordinal"])
            if not isinstance(story_order, int) or isinstance(story_order, bool) or story_order != current_story_order or target["ordinal"] != current_reading_order:
                raise ProductionRunError("target_context_invalid", "chapter ordering changed since the author request")
            ancestor_ids = {chapter_id}
            book_plan_targets = {"book"}
            parent_id = target["parent_id"]
            while parent_id is not None:
                if parent_id in ancestor_ids:
                    raise ProductionRunError("target_context_invalid", "story hierarchy contains a cycle")
                ancestor_ids.add(parent_id)
                parent = conn.execute("SELECT parent_id,kind FROM story_nodes WHERE node_id=?", (parent_id,)).fetchone()
                if parent is None:
                    raise ProductionRunError("target_context_invalid", "chapter hierarchy has a missing parent")
                if parent["kind"] == "book":
                    book_plan_targets.add(parent_id)
                parent_id = parent["parent_id"]
            history = self._settled_history(conn, current_reading_order)
            history_ids = {item["story_node_id"] for item in history}
            history_by_id = {item["story_node_id"]: item for item in history}
            stale_entities = set()
            for source in conn.execute("SELECT * FROM narrative_state_sources"):
                prior = history_by_id.get(source["chapter_id"])
                if source["state"] != "current" or prior is None \
                        or source["acceptance_id"] != prior["acceptance_id"] \
                        or source["source_fingerprint"] != prior["content_fingerprint"]:
                    stale_entities.add((source["entity_type"], source["entity_id"]))

            def source_is_visible(source_ref: str | None) -> bool:
                if source_ref and source_ref.startswith("chapter:"):
                    return source_ref[len("chapter:"):] in history_ids
                return True

            for row in conn.execute("SELECT * FROM characters ORDER BY character_id"):
                if ("character", row["character_id"]) in stale_entities:
                    continue
                view = {"character_id": row["character_id"], "name": row["name"], "agenda": row["agenda"], "voice_notes": row["voice_notes"], "state": _json(row["state_json"], {})}
                items.append(_source(object_id=row["character_id"], object_type="character", authority="accepted", lifecycle="accepted", domain="character", model_view=view, profile=p(row["character_id"])))
            for row in conn.execute("SELECT * FROM relationships ORDER BY relationship_id"):
                if ("relationship", row["relationship_id"]) in stale_entities:
                    continue
                view = {"relationship_id": row["relationship_id"], "participant_a": row["participant_a"], "participant_b": row["participant_b"], "relationship_type": row["relationship_type"], "state": _json(row["state_json"], {})}
                items.append(_source(object_id=row["relationship_id"], object_type="relationship", authority="accepted", lifecycle="accepted", domain="relationship", model_view=view, profile=p(row["relationship_id"])))
            for row in conn.execute("SELECT * FROM world_entities ORDER BY entity_id"):
                if ("world", row["entity_id"]) in stale_entities:
                    continue
                view = {"entity_id": row["entity_id"], "entity_type": row["entity_type"], "name": row["name"], "truth": _json(row["truth_json"], {})}
                items.append(_source(object_id=row["entity_id"], object_type="world_fact", authority="accepted", lifecycle="accepted", domain="world", model_view=view, profile=p(row["entity_id"])))
            for row in conn.execute("SELECT * FROM locations ORDER BY location_id"):
                view = {"location_id": row["location_id"], "name": row["name"], "description": row["description"], "state": _json(row["state_json"], {})}
                items.append(_source(object_id=row["location_id"], object_type="location", authority="accepted", lifecycle="accepted", domain="location", model_view=view, profile=p(row["location_id"])))
            for row in conn.execute("SELECT * FROM timeline_events WHERE story_order<=? ORDER BY story_order,event_id", (current_story_order,)):
                if ("timeline", row["event_id"]) in stale_entities:
                    continue
                authority = str(row["authority_class"])
                if authority not in {"accepted", "locked"} or not source_is_visible(row["source_ref"]):
                    continue
                view = {"event_id": row["event_id"], "story_order": row["story_order"], "title": row["title"], "description": row["description"], "source_ref": row["source_ref"]}
                items.append(_source(object_id=row["event_id"], object_type="timeline_event", authority=authority, lifecycle=authority, domain="timeline", model_view=view, profile=p(row["event_id"])))
            for row in conn.execute("SELECT * FROM story_nodes ORDER BY kind,ordinal,node_id"):
                if row["node_id"] not in ancestor_ids:
                    continue
                view = {"node_id": row["node_id"], "parent_id": row["parent_id"], "kind": row["kind"], "ordinal": row["ordinal"], "title": row["title"], "pov_character_id": row["pov_character_id"], "location_id": row["location_id"], "metadata": _json(row["metadata_json"], {})}
                items.append(_source(object_id=row["node_id"], object_type="story_node", authority="active_plan", lifecycle="active_plan", domain="story", model_view=view, profile=p(row["node_id"])))
            for row in conn.execute("SELECT * FROM plans ORDER BY updated_at,plan_id"):
                target_id = str(row["target_id"])
                if target_id not in {"book", *ancestor_ids, *("chapter:" + oid for oid in ancestor_ids)}:
                    continue
                status = str(row["status"]); authority = "active_plan" if status in {"active", "completed"} else "proposal"; lifecycle = "superseded" if status in {"superseded", "completed"} else authority
                view = {"plan_id": row["plan_id"], "task_mode": row["task_mode"], "target_id": row["target_id"], "plan": _json(row["plan_json"], {})}
                # The exact manuscript/chapter association was verified above.
                # Its active plans are task inputs, not a relevance ranking or Canon.
                pinned = status == "active" and (
                    row["task_mode"] == "PLAN-CHAPTER" and target_id in {chapter_id, "chapter:" + chapter_id}
                    or row["task_mode"] == "DESIGN-BOOK" and target_id in book_plan_targets
                )
                items.append(_source(object_id=row["plan_id"], object_type="plan", authority=authority, lifecycle=lifecycle, domain="plan", model_view=view, profile=p(row["plan_id"]), status=status, pinned=pinned))
            for row in conn.execute("SELECT * FROM canon_claims ORDER BY claim_id"):
                authority = str(row["authority_class"])
                if authority not in {"accepted", "locked"} or not source_is_visible(row["evidence_ref"]):
                    continue
                if row["valid_from_story_order"] is not None and row["valid_from_story_order"] > current_story_order:
                    continue
                if row["valid_to_story_order"] is not None and row["valid_to_story_order"] < current_story_order:
                    continue
                view = {"claim_id": row["claim_id"], "subject_ref": row["subject_ref"], "predicate": row["predicate"], "value": _json(row["value_json"], None), "evidence_ref": row["evidence_ref"], "valid_from_story_order": row["valid_from_story_order"], "valid_to_story_order": row["valid_to_story_order"]}
                items.append(_source(object_id=row["claim_id"], object_type="canon_claim", authority=authority, lifecycle=authority, domain="canon", model_view=view, profile=p(row["claim_id"])))
            for row in conn.execute("SELECT * FROM character_knowledge WHERE available_from_story_order<=? ORDER BY knowledge_id", (current_story_order,)):
                if ("knowledge", row["knowledge_id"]) in stale_entities:
                    continue
                if not source_is_visible(row["evidence_ref"]):
                    continue
                view = {"knowledge_id": row["knowledge_id"], "character_id": row["character_id"], "claim_ref": row["claim_ref"], "fact": _json(row["fact_json"], {}), "available_from_story_order": row["available_from_story_order"], "evidence_ref": row["evidence_ref"], "confidence": row["confidence"]}
                items.append(_source(object_id=row["knowledge_id"], object_type="character_knowledge", authority="accepted", lifecycle="accepted", domain="character_knowledge", model_view=view, profile=p(row["knowledge_id"])))
            for row in conn.execute("SELECT * FROM research_claims ORDER BY research_claim_id"):
                view = {"research_claim_id": row["research_claim_id"], "source_id": row["source_id"], "claim_text": row["claim_text"], "citation": _json(row["citation_json"], {}), "fictionalization_notes": row["fictionalization_notes"], "character_knowledge_boundary": _json(row["character_knowledge_boundary_json"], {}), "canon_status": row["canon_status"]}
                items.append(_source(object_id=row["research_claim_id"], object_type="research", authority="research", lifecycle="active", domain="research", model_view=view, profile=p(row["research_claim_id"])))
            for view in history:
                oid = view["revision_id"]
                items.append(_source(object_id=oid, object_type="accepted_manuscript", authority="accepted", lifecycle="accepted", domain="manuscript", model_view=view, profile=p(oid), stages=CONTEXT_STAGE_IDS))
            pressure = pressure_report(conn, current_order=current_reading_order)
            expectations = [row for key in ("active", "dormant", "overdue") for row in pressure[key]
                            if row["last_touched_order"] < current_reading_order]
            ledger_id = "reader-expectations:" + project_id
            items.append(_source(object_id=ledger_id, object_type="runtime_state", authority="derived", lifecycle="derived",
                                 domain="reader_pressure", model_view={"expectations": expectations, "source_type": "model_proxy",
                                                                       "current_reading_order": current_reading_order}, profile=p(ledger_id)))
        return items

    @staticmethod
    def _settled_history(conn, current_reading_order: int) -> list[dict[str, Any]]:  # noqa: ANN001
        """Only current, accepted, settled chapter heads can be reading history."""
        history = []
        for head in conn.execute("SELECT * FROM canon_state WHERE state_key LIKE 'chapter:%' ORDER BY state_key"):
            chapter_id = head["state_key"][len("chapter:"):]
            chapter = conn.execute("SELECT * FROM story_nodes WHERE node_id=? AND kind='chapter'", (chapter_id,)).fetchone()
            if not chapter or chapter["ordinal"] >= current_reading_order:
                continue
            value = _json(head["value_json"], None)
            if not isinstance(value, dict) or fingerprint(value) != head["content_fingerprint"]:
                raise ProductionRunError("settled_source_invalid", "current chapter head fingerprint does not match")
            from quillframe.novel import current_head
            current, stale = current_head(conn, chapter_id, value.get("document_id"))
            if current is None or stale:
                raise ProductionRunError("settled_source_stale", "a prior chapter has a newer acceptance or obsolete source dependency")
            row = conn.execute(
                "SELECT r.*,d.title,d.story_node_id,d.document_kind,a.candidate_fingerprint,c.content_fingerprint AS candidate_content_fingerprint,c.run_id AS candidate_run_id "
                "FROM document_revisions r JOIN documents d ON d.document_id=r.document_id "
                "JOIN candidates c ON c.revision_id=r.revision_id AND c.document_id=d.document_id "
                "JOIN acceptance_evidence a ON a.candidate_id=c.candidate_id "
                "WHERE r.revision_id=? AND d.document_id=? AND c.candidate_id=? AND a.acceptance_id=?",
                (value.get("revision_id"), value.get("document_id"), value.get("candidate_id"), value.get("acceptance_id")),
            ).fetchone()
            settlement = conn.execute(
                "SELECT settlement_id FROM settlements WHERE target_ref=? AND acceptance_id=? AND after_fingerprint=? AND status='settled'",
                (head["state_key"], value.get("acceptance_id"), head["content_fingerprint"]),
            ).fetchone()
            expected = value.get("content_fingerprint")
            if not row or not settlement or row["story_node_id"] != chapter_id or row["document_kind"] != "manuscript" \
                    or row["authority_class"] != "accepted" or any(fp != expected for fp in (
                        row["content_fingerprint"], row["candidate_content_fingerprint"], row["candidate_fingerprint"],
                        fingerprint_text(row["content"]))):
                raise ProductionRunError("settled_source_invalid", "current chapter head has no exact accepted settlement source")
            stale = conn.execute("SELECT 1 FROM chapter_dependencies WHERE chapter_id=? AND run_id=? AND status='stale' LIMIT 1",
                                 (chapter_id, row["candidate_run_id"])).fetchone()
            if stale:
                raise ProductionRunError("settled_source_stale", "a prior settled chapter depends on an obsolete source revision")
            history.append({
                "revision_id": row["revision_id"], "document_id": row["document_id"], "title": row["title"],
                "story_node_id": chapter_id, "reading_order": chapter["ordinal"], "content": row["content"],
                "content_fingerprint": expected, "settlement_head_fingerprint": head["content_fingerprint"],
                "acceptance_id": value["acceptance_id"],
            })
        return sorted(history, key=lambda item: (item["reading_order"], item["story_node_id"]))

    @staticmethod
    def state_projection(items: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, dict[str, Any]], str]:
        fingerprints = {str(item["object_id"]): str(item["source_fingerprint"]) for item in items}
        states = {str(item["object_id"]): {"source_fingerprint": item["source_fingerprint"], "authority": item["authority"], "lifecycle": item["lifecycle"], "domain": item["domain"], "stages": item["stages"], "pinned": bool(item.get("pinned")), "pinned_stages": item.get("pinned_stages", []), "required_for_grounding": bool(item.get("required_for_grounding")), "exclusion": None} for item in items}
        return fingerprints, states, fingerprint({key: states[key] for key in sorted(states)})
