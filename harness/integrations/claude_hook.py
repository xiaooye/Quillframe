#!/usr/bin/env python3
"""Deterministic Claude Code lifecycle hook → local NovelForge Control Plane.

Reads one Claude hook JSON object from stdin. No model calls. No Canon writes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
CP_DIR=ROOT/"harness"/"control_plane"
if str(CP_DIR) not in sys.path: sys.path.insert(0,str(CP_DIR))
from control_plane import ControlPlane  # noqa: E402


def os_session_id(native:str)->str:
    return "SES-CLAUDE-"+hashlib.sha256(native.encode("utf-8")).hexdigest()[:24]

def main()->int:
    try:
        event=json.load(sys.stdin)
        if not isinstance(event,dict): raise ValueError("hook input must be object")
        native=str(event.get("session_id") or "")
        if not native: return 0
        sid=os_session_id(native)
        cp=ControlPlane(os.getenv("NOVELFORGE_DB",str(ROOT/".novelforge"/"runtime.db")));cp.init()
        existing=cp.get_session(sid)
        payload=(dict(existing["session"]) if existing else {
            "session_id":sid,
            "resource_id":os.getenv("NOVELFORGE_RESOURCE_ID","RUNTIME-LOCAL"),
            "project_id":os.getenv("NOVELFORGE_PROJECT_ID"),
            "role":"manager",
            "status":"running",
            "transport":"local_agent_cli",
            "backend":"claude_code",
            "provider_session_id":native,
        })
        name=event.get("hook_event_name")
        if name=="SessionStart": payload["status"]="running"
        elif name=="SessionEnd": payload["status"]="idle"
        payload["hook_last_event"]={
            "name":name,
            "cwd":event.get("cwd"),
            "source":event.get("source"),
            "tool_name":event.get("tool_name"),
            "tool_use_id":event.get("tool_use_id"),
        }
        cp.put_session(payload,expected_version=existing["version"] if existing else 0)
        return 0
    except Exception as exc:
        print(f"novelforge Claude hook warning: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 0  # telemetry must not break normal Claude operation

if __name__=="__main__":raise SystemExit(main())
