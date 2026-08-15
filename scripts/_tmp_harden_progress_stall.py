#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "harness/control_plane/progress_stall.py"
SCHEMA = ROOT / "harness/control_plane/progress_stall.schema.json"
WORKFLOW = ROOT / ".github/workflows/novelforge-progress-stall.yml"
EXPECTED = {
    RUNTIME: "043a17fe610b0c4222ed7033cbcf60994b63365c",
    SCHEMA: "91a3d82ca15108c220624718f85f3085b1a1027c",
    WORKFLOW: "21f5c73719676067f53fe0016c00407f7bf1cfd8",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = b"blob " + str(len(data)).encode() + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    for path, expected in EXPECTED.items():
        actual = git_blob_sha(path)
        if actual != expected:
            raise SystemExit(f"before-blob mismatch {path.relative_to(ROOT)} expected={expected} actual={actual}")

    text = RUNTIME.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'CLASSIFICATIONS = {"advancing", "exact_no_op", "waiting", "transport_retry_no_op"}\nSHA_PREFIX = "sha256:"\n',
        'CLASSIFICATIONS = {"advancing", "exact_no_op", "waiting", "transport_retry_no_op"}\n'
        'PROGRESS_SOURCE_KIND = "deterministic_runtime"\n'
        'SHA_PREFIX = "sha256:"\n',
        "source constant",
    )
    text = replace_once(
        text,
        '    if event.get("authority_scope") != "observation":\n'
        '        raise ValueError("progress authority_scope must be observation")\n'
        '    resource_id = nonempty(event.get("resource_id"), "resource_id")\n',
        '    if event.get("authority_scope") != "observation":\n'
        '        raise ValueError("progress authority_scope must be observation")\n'
        '    source = event.get("source")\n'
        '    if not isinstance(source, dict) or source.get("kind") != PROGRESS_SOURCE_KIND:\n'
        '        raise ValueError("progress observation source must be deterministic_runtime")\n'
        '    resource_id = nonempty(event.get("resource_id"), "resource_id")\n',
        "source validation",
    )
    text = replace_once(
        text,
        '        "schema", "kind", "progress_scope_id", "checkpoint_id", "workflow_cursor",\n',
        '        "schema", "kind", "progress_scope_id", "session_binding", "checkpoint_id", "workflow_cursor",\n',
        "payload session binding field",
    )
    text = replace_once(
        text,
        '    progress_scope_id = nonempty(payload.get("progress_scope_id"), "progress_scope_id")\n'
        '    checkpoint_id = nonempty(payload.get("checkpoint_id"), "checkpoint_id")\n',
        '    progress_scope_id = nonempty(payload.get("progress_scope_id"), "progress_scope_id")\n'
        '    session_binding = payload.get("session_binding")\n'
        '    if not isinstance(session_binding, dict):\n'
        '        raise ValueError("session_binding must be object")\n'
        '    exact_fields(session_binding, {"version", "payload_hash"}, "session_binding")\n'
        '    session_version = session_binding.get("version")\n'
        '    if not isinstance(session_version, int) or session_version < 1:\n'
        '        raise ValueError("session_binding.version must be positive integer")\n'
        '    session_payload_hash = session_binding.get("payload_hash")\n'
        '    if not is_sha(session_payload_hash):\n'
        '        raise ValueError("session_binding.payload_hash must be sha256:<64 hex>")\n'
        '    checkpoint_id = nonempty(payload.get("checkpoint_id"), "checkpoint_id")\n',
        "parse session binding",
    )
    text = replace_once(
        text,
        '        "progress_scope_id": progress_scope_id,\n'
        '        "checkpoint_id": checkpoint_id,\n',
        '        "progress_scope_id": progress_scope_id,\n'
        '        "session_version": session_version,\n'
        '        "session_payload_hash": session_payload_hash,\n'
        '        "checkpoint_id": checkpoint_id,\n',
        "normalized session binding",
    )
    text = replace_once(
        text,
        'def _scope_events(cp: control_plane.ControlPlane, session_id: str, progress_scope_id: str) -> list[dict[str, Any]]:\n',
        'def _validate_session_binding(cp: control_plane.ControlPlane, normalized: dict[str, Any]) -> None:\n'
        '    current = cp.get_session(normalized["session_id"])\n'
        '    if current is None:\n'
        '        raise ValueError("progress observation requires durable session state")\n'
        '    if current["version"] != normalized["session_version"]:\n'
        '        raise ValueError("progress session version mismatch")\n'
        '    if current["payload_hash"] != normalized["session_payload_hash"]:\n'
        '        raise ValueError("progress session payload hash mismatch")\n'
        '    session = current.get("session")\n'
        '    if not isinstance(session, dict) or session.get("resource_id") != normalized["resource_id"]:\n'
        '        raise ValueError("progress session resource mismatch")\n'
        '    runs = session.get("runs")\n'
        '    if not isinstance(runs, list) or not runs or not isinstance(runs[-1], dict):\n'
        '        raise ValueError("progress session must expose current run")\n'
        '    if runs[-1].get("run_id") != normalized["run_id"]:\n'
        '        raise ValueError("progress observation run is not current durable session run")\n'
        '\n'
        '\n'
        'def _scope_events(cp: control_plane.ControlPlane, session_id: str, progress_scope_id: str) -> list[dict[str, Any]]:\n',
        "session binding validator",
    )
    text = replace_once(
        text,
        '    chain = _ordered_chain(_scope_events(cp, normalized["session_id"], normalized["progress_scope_id"]))\n',
        '    _validate_session_binding(cp, normalized)\n'
        '    chain = _ordered_chain(_scope_events(cp, normalized["session_id"], normalized["progress_scope_id"]))\n',
        "record session binding",
    )
    text = replace_once(
        text,
        'def fixture_event(\n'
        '    event_id: str,\n'
        '    before: str,\n'
        '    after: str,\n'
        '    *,\n'
        '    predecessor: str | None,\n'
        '    operation_input: str,\n'
        '    execution_state: str = "executed",\n'
        '    retry_of: str | None = None,\n'
        '    run_id: str = "RUN-P",\n'
        '    checkpoint: str = "CKP-P",\n'
        '    scope: str = "draft-loop",\n'
        ') -> dict[str, Any]:\n',
        'def fixture_session(run_ids: list[str]) -> dict[str, Any]:\n'
        '    return {\n'
        '        "session_id": "SES-P", "resource_id": "BOOK-P", "project_id": "PROJECT-P",\n'
        '        "role": "manager", "status": "running",\n'
        '        "runs": [{"run_id": run_id, "status": "running"} for run_id in run_ids],\n'
        '    }\n'
        '\n'
        '\n'
        'def fixture_binding(session: dict[str, Any], version: int) -> dict[str, Any]:\n'
        '    return {"version": version, "payload_hash": control_plane.digest(session)}\n'
        '\n'
        '\n'
        'def fixture_event(\n'
        '    event_id: str,\n'
        '    before: str,\n'
        '    after: str,\n'
        '    *,\n'
        '    predecessor: str | None,\n'
        '    operation_input: str,\n'
        '    execution_state: str = "executed",\n'
        '    retry_of: str | None = None,\n'
        '    run_id: str = "RUN-P",\n'
        '    checkpoint: str = "CKP-P",\n'
        '    scope: str = "draft-loop",\n'
        '    session_binding: dict[str, Any] | None = None,\n'
        ') -> dict[str, Any]:\n'
        '    if session_binding is None:\n'
        '        session_binding = fixture_binding(fixture_session(["RUN-P"]), 1)\n',
        "fixture session binding",
    )
    text = replace_once(
        text,
        '        "source": {"kind": "self_test", "actor": "progress_stall.py", "transport": "local", "external_ref": None},\n',
        '        "source": {"kind": PROGRESS_SOURCE_KIND, "actor": "progress_stall.py", "transport": "local", "external_ref": None},\n',
        "fixture source kind",
    )
    text = replace_once(
        text,
        '            "progress_scope_id": scope,\n'
        '            "checkpoint_id": checkpoint,\n',
        '            "progress_scope_id": scope,\n'
        '            "session_binding": session_binding,\n'
        '            "checkpoint_id": checkpoint,\n',
        "fixture payload binding",
    )
    text = replace_once(
        text,
        '    cp = control_plane.ControlPlane(path)\n'
        '    cp.init()\n'
        '\n'
        '    first = fixture_event("EV-P-A", "a", "b", predecessor=None, operation_input="1")\n',
        '    cp = control_plane.ControlPlane(path)\n'
        '    cp.init()\n'
        '    session_v1 = fixture_session(["RUN-P"])\n'
        '    stored_v1 = cp.put_session(session_v1)\n'
        '    binding_v1 = {"version": stored_v1["version"], "payload_hash": stored_v1["payload_hash"]}\n'
        '\n'
        '    first = fixture_event("EV-P-A", "a", "b", predecessor=None, operation_input="1", session_binding=binding_v1)\n',
        "selftest durable session",
    )
    for old, new, label in [
        ('fixture_event("EV-P-B", "b", "b", predecessor="EV-P-A", operation_input="2")', 'fixture_event("EV-P-B", "b", "b", predecessor="EV-P-A", operation_input="2", session_binding=binding_v1)', 'noop1'),
        ('fixture_event("EV-P-C", "b", "b", predecessor="EV-P-A", operation_input="3")', 'fixture_event("EV-P-C", "b", "b", predecessor="EV-P-A", operation_input="3", session_binding=binding_v1)', 'stale'),
        ('"EV-P-D", "b", "b", predecessor="EV-P-B", operation_input="2", retry_of="EV-P-B"\n    )', '"EV-P-D", "b", "b", predecessor="EV-P-B", operation_input="2", retry_of="EV-P-B", session_binding=binding_v1\n    )', 'retry'),
        ('"EV-P-E", "b", "b", predecessor="EV-P-D", operation_input="4", execution_state="awaiting_user"\n    )', '"EV-P-E", "b", "b", predecessor="EV-P-D", operation_input="4", execution_state="awaiting_user", session_binding=binding_v1\n    )', 'waiting'),
        ('fixture_event("EV-P-F", "b", "b", predecessor="EV-P-E", operation_input="5")', 'fixture_event("EV-P-F", "b", "b", predecessor="EV-P-E", operation_input="5", session_binding=binding_v1)', 'noop2'),
    ]:
        text = replace_once(text, old, new, label)
    text = replace_once(
        text,
        '    advancing = fixture_event("EV-P-A2", "b", "c", predecessor="EV-P-F", operation_input="6", run_id="RUN-P2", checkpoint="CKP-P2")\n'
        '    record_observation(cp, advancing)\n',
        '    session_v2 = fixture_session(["RUN-P", "RUN-P2"])\n'
        '    stored_v2 = cp.put_session(session_v2, expected_version=stored_v1["version"])\n'
        '    binding_v2 = {"version": stored_v2["version"], "payload_hash": stored_v2["payload_hash"]}\n'
        '    advancing = fixture_event("EV-P-A2", "b", "c", predecessor="EV-P-F", operation_input="6", run_id="RUN-P2", checkpoint="CKP-P2", session_binding=binding_v2)\n'
        '    record_observation(cp, advancing)\n'
        '    duplicate_after_resume = record_observation(cp, no_op_1)\n'
        '    stale_session = fixture_event("EV-P-S", "c", "c", predecessor="EV-P-A2", operation_input="s", run_id="RUN-P2", checkpoint="CKP-P2", session_binding=binding_v1)\n'
        '    stale_session_binding_blocked = blocked(lambda: record_observation(cp, stale_session))\n'
        '    stale_run = fixture_event("EV-P-R", "c", "c", predecessor="EV-P-A2", operation_input="r", run_id="RUN-P", checkpoint="CKP-P2", session_binding=binding_v2)\n'
        '    stale_run_blocked = blocked(lambda: record_observation(cp, stale_run))\n',
        "resume/current run binding tests",
    )
    text = replace_once(
        text,
        '    slow_advancing = fixture_event("EV-P-A3", "c", "d", predecessor="EV-P-A2", operation_input="7", run_id="RUN-P2", checkpoint="CKP-P3")\n',
        '    slow_advancing = fixture_event("EV-P-A3", "c", "d", predecessor="EV-P-A2", operation_input="7", run_id="RUN-P2", checkpoint="CKP-P3", session_binding=binding_v2)\n',
        "slow advancing binding",
    )
    text = replace_once(
        text,
        '    wrong_retry = fixture_event("EV-P-X", "d", "d", predecessor="EV-P-A3", operation_input="9", retry_of="EV-P-A3")\n',
        '    wrong_retry = fixture_event("EV-P-X", "d", "d", predecessor="EV-P-A3", operation_input="9", retry_of="EV-P-A3", run_id="RUN-P2", session_binding=binding_v2)\n',
        "wrong retry binding",
    )
    text = replace_once(
        text,
        '    completion_claim = fixture_event("EV-P-Y", "d", "d", predecessor="EV-P-A3", operation_input="8")\n',
        '    completion_claim = fixture_event("EV-P-Y", "d", "d", predecessor="EV-P-A3", operation_input="8", run_id="RUN-P2", session_binding=binding_v2)\n',
        "completion binding",
    )
    text = replace_once(
        text,
        '    completion_claim["payload"]["complete"] = True\n'
        '    completion_claim_blocked = blocked(lambda: validate_progress_event(completion_claim))\n',
        '    completion_claim["payload"]["complete"] = True\n'
        '    completion_claim_blocked = blocked(lambda: validate_progress_event(completion_claim))\n'
        '    bad_source = fixture_event("EV-P-Q", "d", "d", predecessor="EV-P-A3", operation_input="q", run_id="RUN-P2", session_binding=binding_v2)\n'
        '    bad_source["source"]["kind"] = "semantic_worker"\n'
        '    nondeterministic_source_blocked = blocked(lambda: validate_progress_event(bad_source))\n',
        "source negative test",
    )
    text = replace_once(
        text,
        '        "identical_replay_is_idempotent": duplicate["duplicate"] is True,\n',
        '        "identical_replay_is_idempotent": duplicate["duplicate"] is True,\n'
        '        "old_duplicate_remains_idempotent_after_session_advance": duplicate_after_resume["duplicate"] is True,\n'
        '        "nondeterministic_source_cannot_self_report_progress": nondeterministic_source_blocked,\n'
        '        "stale_session_binding_fails_closed": stale_session_binding_blocked,\n'
        '        "stale_run_cannot_append_progress": stale_run_blocked,\n',
        "new checks",
    )
    RUNTIME.write_text(text, encoding="utf-8")

    schema = SCHEMA.read_text(encoding="utf-8")
    schema = replace_once(
        schema,
        '"schema", "kind", "progress_scope_id", "checkpoint_id", "workflow_cursor",',
        '"schema", "kind", "progress_scope_id", "session_binding", "checkpoint_id", "workflow_cursor",',
        "schema required session binding",
    )
    schema = replace_once(
        schema,
        '        "progress_scope_id": {"$ref": "#/$defs/nonempty"},\n'
        '        "checkpoint_id": {"$ref": "#/$defs/nonempty"},\n',
        '        "progress_scope_id": {"$ref": "#/$defs/nonempty"},\n'
        '        "session_binding": {\n'
        '          "type": "object",\n'
        '          "additionalProperties": false,\n'
        '          "required": ["version", "payload_hash"],\n'
        '          "properties": {\n'
        '            "version": {"type": "integer", "minimum": 1},\n'
        '            "payload_hash": {"$ref": "#/$defs/sha"}\n'
        '          }\n'
        '        },\n'
        '        "checkpoint_id": {"$ref": "#/$defs/nonempty"},\n',
        "schema session binding definition",
    )
    SCHEMA.write_text(schema, encoding="utf-8")

    workflow = WORKFLOW.read_text(encoding="utf-8")
    workflow = replace_once(
        workflow,
        "          assert d['identical_replay_is_idempotent'] is True\n",
        "          assert d['identical_replay_is_idempotent'] is True\n"
        "          assert d['old_duplicate_remains_idempotent_after_session_advance'] is True\n"
        "          assert d['nondeterministic_source_cannot_self_report_progress'] is True\n"
        "          assert d['stale_session_binding_fails_closed'] is True\n"
        "          assert d['stale_run_cannot_append_progress'] is True\n",
        "workflow new assertions",
    )
    WORKFLOW.write_text(workflow, encoding="utf-8")

    for cmd in (
        ["python", "-m", "py_compile", str(RUNTIME.relative_to(ROOT))],
        ["python", "-m", "json.tool", str(SCHEMA.relative_to(ROOT))],
        ["python", str(RUNTIME.relative_to(ROOT)), "self-test", "--path", "/tmp/novelforge-progress-stall-hardening.db"],
    ):
        subprocess.run(cmd, cwd=ROOT, check=True)

    for path in (RUNTIME, SCHEMA, WORKFLOW):
        print(f"TARGET_BLOB {path.relative_to(ROOT)} {git_blob_sha(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
