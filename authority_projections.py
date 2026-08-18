from __future__ import annotations

from typing import Any

from persistence.quillframe_sqlite import QuillframeStore


def settlement_preflight(store: QuillframeStore, project_id: str, acceptance_id: str, target_ref: str) -> dict[str, Any]:
    """Read-only exact-before projection for an explicitly prepared Settlement.

    This does not authorize or perform Settlement. The returned fingerprint is
    intentionally consumed later by settlement.apply as its compare-and-swap
    precondition.
    """
    with store.open_project(project_id) as conn:
        acceptance = conn.execute(
            """SELECT a.acceptance_id,a.candidate_id,a.candidate_fingerprint,c.status AS candidate_status,
                      c.revision_id,r.authority_class AS revision_authority
               FROM acceptance_evidence a
               JOIN candidates c ON c.candidate_id=a.candidate_id
               LEFT JOIN document_revisions r ON r.revision_id=c.revision_id
               WHERE a.acceptance_id=?""",
            (acceptance_id,),
        ).fetchone()
        if not acceptance:
            raise KeyError(f"acceptance not found: {acceptance_id}")
        current = conn.execute("SELECT content_fingerprint,authority_class,evidence_ref,updated_at FROM canon_state WHERE state_key=?", (target_ref,)).fetchone()
    return {
        "schema": "quillframe_settlement_preflight_v1",
        "project_id": project_id,
        "acceptance_id": acceptance_id,
        "target_ref": target_ref,
        "candidate_id": acceptance["candidate_id"],
        "candidate_fingerprint": acceptance["candidate_fingerprint"],
        "candidate_status": acceptance["candidate_status"],
        "revision_authority": acceptance["revision_authority"],
        "expected_before_fingerprint": current["content_fingerprint"] if current else "absent",
        "current_state": dict(current) if current else None,
        "ready": acceptance["candidate_status"] == "accepted" and acceptance["revision_authority"] == "accepted",
        "authority": False,
        "settlement_authority": False,
        "mutation_performed": False,
    }
