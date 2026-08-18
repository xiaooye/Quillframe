#!/usr/bin/env python3
"""Explicit opt-in live compatibility probe for one user-supplied Model API.

Normal CI must never run this file. It requires QUILLFRAME_LIVE_MODEL_TEST=1
plus a live endpoint. The access token is read transiently and never printed.
"""
from __future__ import annotations

import json
import os
import sys

from model_runtime import EnvSecretStore, ModelRuntime


def main() -> int:
    if os.getenv("QUILLFRAME_LIVE_MODEL_TEST") != "1":
        print(json.dumps({"status": "skipped", "reason": "QUILLFRAME_LIVE_MODEL_TEST!=1"}))
        return 0
    endpoint = os.getenv("QUILLFRAME_LIVE_MODEL_ENDPOINT", "").strip()
    if not endpoint:
        print(json.dumps({"status": "failed", "reason": "QUILLFRAME_LIVE_MODEL_ENDPOINT required"}))
        return 2
    token_ref = "env:QUILLFRAME_LIVE_MODEL_TOKEN"
    store = EnvSecretStore()
    token = store.resolve(token_ref) if store.present(token_ref) else ""
    runtime = ModelRuntime(store)
    snapshot = runtime.connect(endpoint, token, credential_ref=token_ref if token else None)
    preferred = os.getenv("QUILLFRAME_LIVE_MODEL_PREFERENCE", "").strip() or snapshot.models[0].model_id
    model = runtime.probe_model(snapshot.service_id, preferred, verify_tools=os.getenv("QUILLFRAME_LIVE_VERIFY_TOOLS") == "1")
    print(json.dumps({
        "status": "passed",
        "service_id": snapshot.service_id,
        "endpoint": snapshot.endpoint,
        "models_discovered": len(snapshot.models),
        "model_id": model.model_id,
        "protocol": model.protocol,
        "capabilities": {name: evidence.state for name, evidence in model.capabilities.items()},
        "secret_serialized": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
