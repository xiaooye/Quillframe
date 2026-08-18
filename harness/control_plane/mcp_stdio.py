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

from control_plane import ControlPlane

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "quillframe-control-plane",
    "title": "Quillframe Control Plane",
    "version": "0.9.0",
}

TOOLS: list[dict[str, Any]] = [
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


def text_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}], "structuredContent": value if isinstance(value, dict) else {"value": value}, "isError": is_error}


class MCPServer:
    def __init__(self, db_path: str):
        self.cp = ControlPlane(db_path)
        self.cp.init()
        self.initialized = False

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
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