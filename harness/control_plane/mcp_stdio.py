#!/usr/bin/env python3
"""Minimal stdio MCP adapter for the Quillframe Control Plane.

Implements MCP 2025-06-18 lifecycle + tools/list + tools/call over newline-
delimited JSON-RPC. Stdout is reserved for MCP messages; diagnostics go stderr.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Support both ``python -m harness.control_plane.mcp_stdio`` and the release
#/CI form that executes this file by path.  The latter otherwise puts only
# ``harness/control_plane`` on sys.path, so the novel-kernel imports fail.
ROOT = Path(__file__).resolve().parents[2]
CONTROL_PLANE_DIR = Path(__file__).resolve().parent
for _path in (str(ROOT), str(CONTROL_PLANE_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from control_plane import ControlPlane
from core_operations import CoreOperations
from harness.project_projection import preview as projection_preview
from harness.project_projection import status as projection_status
from persistence.quillframe_sqlite import QuillframeStore

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "quillframe-control-plane",
    "title": "Quillframe Control Plane",
    "version": "0.9.1",
    "product_boundary": "host_runs_agent_quillframe_governs_novel",
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "quillframe_capabilities",
        "title": "Novelist-facing Quillframe capabilities",
        "description": "Discover the novelist-facing, internal/ops, and privileged author surfaces without granting authority.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "authority": False},
    },
    {
        "name": "quillframe_project_inspect",
        "title": "Inspect fiction Project",
        "description": "Read the Project projection and story-contract counts. This does not expose private runtime stores or grant authority.",
        "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string", "minLength": 1}}, "required": ["project_id"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "project.inspect", "authority": False},
    },
    {
        "name": "quillframe_project_projection_preview",
        "title": "Preview mapped Project projection",
        "description": "Compile the explicit Project Context Manifest without SQLite mutation or model execution.",
        "inputSchema": {"type": "object", "properties": {"project_root": {"type": "string", "minLength": 1}}, "required": ["project_root"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "project.projection.preview", "authority": False},
    },
    {
        "name": "quillframe_project_projection_status",
        "title": "Read mapped Project projection status",
        "description": "Report projection/source readiness and fingerprints without returning model output.",
        "inputSchema": {"type": "object", "properties": {"project_root": {"type": "string", "minLength": 1}, "data_dir": {"type": ["string", "null"]}}, "required": ["project_root"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "project.projection.status", "authority": False},
    },
    {
        "name": "quillframe_author_run_start",
        "title": "Start bounded author run",
        "description": "Register one explicitly named Quillframe task mode. The host/model must still execute and satisfy all gates; raw draft remains private.",
        "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string", "minLength": 1}, "task_mode": {"type": "string", "minLength": 1}, "target_ref": {"type": ["string", "null"]}, "payload": {"type": "object"}, "session_id": {"type": ["string", "null"]}, "idempotency_key": {"type": ["string", "null"]}}, "required": ["project_id", "task_mode", "payload"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "author.run.start", "authority": False},
    },
    {
        "name": "quillframe_candidate_review_get",
        "title": "Read released candidate review",
        "description": "Read exact candidate review evidence only when production release and fresh independent evidence validate.",
        "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string", "minLength": 1}, "candidate_id": {"type": "string", "minLength": 1}}, "required": ["project_id", "candidate_id"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "candidate.review.get", "authority": False},
    },
    {
        "name": "quillframe_candidate_visible_get",
        "title": "Read Review Draft",
        "description": "Return manuscript text only through the exact production-release visibility boundary; pending, stale, or unreleased candidates return no text.",
        "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string", "minLength": 1}, "candidate_id": {"type": "string", "minLength": 1}}, "required": ["project_id", "candidate_id"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "candidate.visible.get", "authority": False},
    },
    {
        "name": "quillframe_candidate_reject",
        "title": "Reject candidate",
        "description": "Record an explicit user-authorized review rejection. It never accepts or settles Canon.",
        "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string", "minLength": 1}, "candidate_id": {"type": "string", "minLength": 1}, "candidate_fingerprint": {"type": "string", "minLength": 1}, "authorized_by": {"type": "string", "minLength": 1}, "authorization": {"type": "object"}, "idempotency_key": {"type": "string", "minLength": 1}, "reason": {"type": ["string", "null"]}, "user_authorized": {"const": True}}, "required": ["project_id", "candidate_id", "candidate_fingerprint", "authorized_by", "authorization", "idempotency_key", "user_authorized"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "candidate.reject", "requires_explicit_user_authorization": True, "authority": False},
    },
    {
        "name": "quillframe_candidate_revision_request",
        "title": "Request candidate revision",
        "description": "Record an explicit user-authorized revision request with exact candidate binding. It never accepts or settles Canon.",
        "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string", "minLength": 1}, "candidate_id": {"type": "string", "minLength": 1}, "candidate_fingerprint": {"type": "string", "minLength": 1}, "revision_request": {"type": "object"}, "authorized_by": {"type": "string", "minLength": 1}, "authorization": {"type": "object"}, "idempotency_key": {"type": "string", "minLength": 1}, "user_authorized": {"const": True}}, "required": ["project_id", "candidate_id", "candidate_fingerprint", "revision_request", "authorized_by", "authorization", "idempotency_key", "user_authorized"], "additionalProperties": False},
        "_meta": {"surface_class": "novelist_facing", "mapped_operation": "candidate.revision.request", "requires_explicit_user_authorization": True, "authority": False},
    },
    {
        "name": "quillframe_status",
        "title": "Quillframe runtime status",
        "description": "Read operational Session/Event/Handoff store status. This is not Canon state.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "quillframe_session_put",
        "title": "Persist Quillframe session",
        "description": "Persist a Quillframe session snapshot with optional optimistic version check. Operational state only.",
        "inputSchema": {"type": "object", "properties": {"session": {"type": "object"}, "expected_version": {"type": ["integer", "null"], "minimum": 0}}, "required": ["session"], "additionalProperties": False},
    },
    {
        "name": "quillframe_session_get",
        "title": "Read Quillframe session",
        "description": "Read one persisted Quillframe session by session_id.",
        "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string", "minLength": 1}}, "required": ["session_id"], "additionalProperties": False},
    },
    {
        "name": "quillframe_session_list",
        "title": "List Quillframe sessions",
        "description": "List persisted session summaries, optionally scoped to one resource/project.",
        "inputSchema": {"type": "object", "properties": {"resource_id": {"type": ["string", "null"]}}, "additionalProperties": False},
    },
    {
        "name": "quillframe_event_ingest",
        "title": "Ingest Quillframe event",
        "description": "Idempotently ingest a typed quillframe_event_v1 request/observation/result. Events do not grant Canon authority.",
        "inputSchema": {"type": "object", "properties": {"event": {"type": "object"}}, "required": ["event"], "additionalProperties": False},
    },
    {
        "name": "quillframe_handoff_submit",
        "title": "Submit bounded handoff",
        "description": "Queue a typed bounded cross-session handoff. Canon/framework behavior/taste write permissions must remain false.",
        "inputSchema": {"type": "object", "properties": {"handoff": {"type": "object"}}, "required": ["handoff"], "additionalProperties": False},
    },
    {
        "name": "quillframe_handoff_claim",
        "title": "Claim handoff lease",
        "description": "Atomically claim the oldest eligible queued/expired handoff using a bounded worker lease.",
        "inputSchema": {"type": "object", "properties": {"worker_id": {"type": "string", "minLength": 1}, "target_session_class": {"type": ["string", "null"]}, "lease_seconds": {"type": "integer", "minimum": 1, "maximum": 86400, "default": 300}}, "required": ["worker_id"], "additionalProperties": False},
    },
    {
        "name": "quillframe_handoff_get",
        "title": "Read handoff",
        "description": "Read one handoff, lease and bound result state.",
        "inputSchema": {"type": "object", "properties": {"handoff_id": {"type": "string", "minLength": 1}}, "required": ["handoff_id"], "additionalProperties": False},
    },
    {
        "name": "quillframe_handoff_complete",
        "title": "Complete claimed handoff",
        "description": "Complete a handoff only while the caller owns a live lease. Does not itself consume downstream result side effects.",
        "inputSchema": {"type": "object", "properties": {"handoff_id": {"type": "string", "minLength": 1}, "worker_id": {"type": "string", "minLength": 1}, "result": {"type": "object"}, "failed": {"type": "boolean", "default": False}}, "required": ["handoff_id", "worker_id", "result"], "additionalProperties": False},
    },
    {
        "name": "quillframe_result_consume",
        "title": "Consume result exactly once",
        "description": "Record exactly-once logical consumption of a result hash by one named consumer. Duplicate delivery with the same hash is safe.",
        "inputSchema": {"type": "object", "properties": {"source_type": {"type": "string", "minLength": 1}, "source_id": {"type": "string", "minLength": 1}, "consumer": {"type": "string", "minLength": 1}, "payload_hash": {"type": "string", "minLength": 1}}, "required": ["source_type", "source_id", "consumer", "payload_hash"], "additionalProperties": False},
    },
]

# The legacy session/event/handoff/consume tools remain available to hosts, but
# are explicitly internal/ops.  Novelist-facing tools above map to the same
# Core operation contracts rather than creating a second authority API.
for _tool in TOOLS:
    _tool.setdefault("_meta", {"surface_class": "internal_ops", "authority": False})


def text_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}], "structuredContent": value if isinstance(value, dict) else {"value": value}, "isError": is_error}


def agent_safe_candidate_review(review: dict[str, Any]) -> dict[str, Any]:
    """Project review evidence for MCP, without a manuscript side channel.

    Studio may use the richer Core projection because it separately invokes the
    exact visibility boundary before rendering text.  A model-discoverable MCP
    tool must not receive candidate/incumbent content or a reconstructable diff;
    released manuscript text remains exclusive to ``candidate.visible.get``.
    """
    safe = dict(review)
    safe["schema"] = "quillframe_candidate_review_evidence_projection_v1"
    for key in ("candidate_revision", "incumbent_revision"):
        revision = review.get(key)
        if isinstance(revision, dict):
            safe[key] = {
                field: revision[field]
                for field in (
                    "revision_id",
                    "document_id",
                    "parent_revision_id",
                    "content_fingerprint",
                    "authority_class",
                    "source",
                    "created_at",
                )
                if field in revision
            }
        else:
            safe[key] = None
    safe.pop("diff", None)
    safe["manuscript_access"] = "candidate.visible.get_only"
    return safe


class MCPServer:
    def __init__(self, db_path: str):
        self.cp = ControlPlane(db_path)
        self.cp.init()
        self.initialized = False

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "quillframe_capabilities":
            return {
                "schema": "quillframe_mcp_surface_manifest_v1",
                "product_boundary": "host_runs_agent_quillframe_governs_novel",
                "surface_classes": {
                    "novelist_facing": [
                        "project.inspect", "project.projection.preview", "project.projection.status",
                        "author.run.start", "candidate.review.get", "candidate.visible.get",
                        "candidate.reject", "candidate.revision.request",
                    ],
                    "internal_ops": [
                        "session", "event", "handoff", "leases", "consume-once", "provider/runtime diagnostics",
                    ],
                    "privileged_author": ["candidate.accept", "settlement.apply"],
                },
                "authority": False,
                "canon_authority": False,
                "settlement_authority": False,
            }
        if name == "quillframe_project_inspect":
            return CoreOperations(QuillframeStore()).project_inspect(args["project_id"])
        if name == "quillframe_project_projection_preview":
            return projection_preview(Path(args["project_root"]))
        if name == "quillframe_project_projection_status":
            data_dir = Path(args["data_dir"]) if args.get("data_dir") else None
            return projection_status(Path(args["project_root"]), data_dir=data_dir)
        if name == "quillframe_author_run_start":
            return CoreOperations(QuillframeStore()).start_author_run(
                args["project_id"], task_mode=args["task_mode"], target_ref=args.get("target_ref"),
                payload=args["payload"], session_id=args.get("session_id"), idempotency_key=args.get("idempotency_key"),
            )
        if name == "quillframe_candidate_review_get":
            review = CoreOperations(QuillframeStore()).candidate_review_get(args["project_id"], candidate_id=args["candidate_id"])
            return agent_safe_candidate_review(review)
        if name == "quillframe_candidate_visible_get":
            return CoreOperations(QuillframeStore()).candidate_visible_get(args["project_id"], candidate_id=args["candidate_id"])
        if name == "quillframe_candidate_reject":
            if args.get("user_authorized") is not True:
                raise ValueError("candidate.reject requires an explicit user action")
            return CoreOperations(QuillframeStore()).reject_candidate(
                args["project_id"], candidate_id=args["candidate_id"], candidate_fingerprint=args["candidate_fingerprint"],
                authorized_by=args["authorized_by"], authorization=args["authorization"], idempotency_key=args["idempotency_key"], reason=args.get("reason"),
            )
        if name == "quillframe_candidate_revision_request":
            if args.get("user_authorized") is not True:
                raise ValueError("candidate.revision.request requires an explicit user action")
            return CoreOperations(QuillframeStore()).request_candidate_revision(
                args["project_id"], candidate_id=args["candidate_id"], candidate_fingerprint=args["candidate_fingerprint"],
                revision_request=args["revision_request"], authorized_by=args["authorized_by"], authorization=args["authorization"], idempotency_key=args["idempotency_key"],
            )
        if name == "quillframe_status": return self.cp.status()
        if name == "quillframe_session_put": return self.cp.put_session(args["session"], expected_version=args.get("expected_version"))
        if name == "quillframe_session_get":
            value = self.cp.get_session(args["session_id"])
            if value is None: raise ValueError("session not found")
            return value
        if name == "quillframe_session_list": return {"sessions": self.cp.list_sessions(args.get("resource_id"))}
        if name == "quillframe_event_ingest": return self.cp.ingest_event(args["event"])
        if name == "quillframe_handoff_submit": return self.cp.submit_handoff(args["handoff"])
        if name == "quillframe_handoff_claim": return {"claim": self.cp.claim_handoff(args["worker_id"], target_session_class=args.get("target_session_class"), lease_seconds=int(args.get("lease_seconds", 300)))}
        if name == "quillframe_handoff_get":
            value = self.cp.get_handoff(args["handoff_id"])
            if value is None: raise ValueError("handoff not found")
            return value
        if name == "quillframe_handoff_complete": return self.cp.complete_handoff(args["handoff_id"], args["worker_id"], args["result"], failed=bool(args.get("failed", False)))
        if name == "quillframe_result_consume": return self.cp.consume_once(args["source_type"], args["source_id"], args["consumer"], args["payload_hash"])
        raise KeyError(name)

    def handle(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        method = msg.get("method"); rid = msg.get("id")
        if method == "notifications/initialized": self.initialized = True; return None
        if method == "initialize":
            self.initialized = False
            return {"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER_INFO, "instructions": "Operational Quillframe runtime tools only. They do not grant Canon or framework-behavior authority."}}
        if method == "ping": return {"jsonrpc": "2.0", "id": rid, "result": {}}
        if not self.initialized: return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32002, "message": "server not initialized"}}
        if method == "tools/list": return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
        if method == "tools/call":
            params = msg.get("params") or {}; name = params.get("name"); args = params.get("arguments") or {}
            if not isinstance(args, dict): return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": "tool arguments must be object"}}
            if name not in {t["name"] for t in TOOLS}: return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"unknown tool {name!r}"}}
            try: value = self.call_tool(name, args); return {"jsonrpc": "2.0", "id": rid, "result": text_result(value)}
            except Exception as exc: return {"jsonrpc": "2.0", "id": rid, "result": text_result({"error": type(exc).__name__, "message": str(exc)}, is_error=True)}
        if rid is None: return None
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        server = MCPServer(str(Path(td) / "runtime.db"))
        init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "self-test", "version": "1"}}})
        pre = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        listed = server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        status = server.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "quillframe_status", "arguments": {}}})
        ok = init is not None and init["result"]["protocolVersion"] == PROTOCOL_VERSION and pre is not None and pre.get("error", {}).get("code") == -32002 and listed is not None and len(listed["result"]["tools"]) >= 8 and status is not None and status["result"]["isError"] is False and status["result"]["structuredContent"]["schema"] == "quillframe_control_plane_v1"
        return {"mcp_stdio_contract": "PASS" if ok else "FAIL", "protocol_version": PROTOCOL_VERSION, "requires_initialize": True, "tool_count": len(TOOLS), "stdout_reserved_for_jsonrpc": True}


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe MCP stdio control-plane adapter")
    p.add_argument("--db", default=os.getenv("QUILLFRAME_DB", ".quillframe/runtime.db"))
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2)); return 0
    server = MCPServer(args.db)
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw: continue
        try:
            msg = json.loads(raw)
            if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0": raise ValueError("invalid JSON-RPC 2.0 message")
            response = server.handle(msg)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"{type(exc).__name__}: {exc}"}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n"); sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
