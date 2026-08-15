#!/usr/bin/env python3
"""NovelForge mid-run author steering: durable input, safe-point binding, consume-once."""
from __future__ import annotations
import argparse, hashlib, json, sys, tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import control_plane  # noqa: E402

EVENT_TYPE = "feedback.observed"
PAYLOAD_KIND = "author_steering"
REQUEST_SCHEMA = "novelforge_author_steering_request_v1"
SAFE_POINT_SCHEMA = "novelforge_author_steering_safe_point_v1"
DECISION_INPUT_SCHEMA = "novelforge_author_steering_decision_input_v1"
DECISION_SCHEMA = "novelforge_author_steering_decision_v1"
RECEIPT_SCHEMA = "novelforge_author_steering_receipt_v1"
SOURCE_KINDS = {"user", "authorized_human"}
SCOPES = {"current_run", "future_runs", "named_target"}
CONSUME_AT = {"next_safe_point", "before_draft", "before_review", "before_user_visible_gate"}
SAFE_KINDS = {"workflow_boundary", "before_draft", "before_review", "before_external_dispatch",
              "after_external_result", "before_consequential_write", "after_consequential_write",
              "before_user_visible_gate"}
WRITE_STATES = {"none", "preflight", "in_progress", "complete"}
ROUTES = {"continue", "rebuild_context", "replan", "regenerate",
          "cancel_handoff", "await_user", "defer_future"}
ACKS = {"exact", "reinterpreted_against_current_state", "await_user", "defer_future"}

def canonical(v: Any) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def fp(v: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(v)).hexdigest()

def nonempty(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{field} must be non-empty string")
    return v.strip()

def is_sha(v: Any) -> bool:
    if not isinstance(v, str) or len(v) != 71 or not v.startswith("sha256:"):
        return False
    try: int(v[7:], 16)
    except ValueError: return False
    return True

def exact(d: dict[str, Any], fields: set[str], name: str) -> None:
    if set(d) != fields:
        raise ValueError(f"{name} fields mismatch missing={sorted(fields-set(d))} extra={sorted(set(d)-fields)}")

def sha_list(v: Any, field: str) -> list[str]:
    if not isinstance(v, list) or any(not is_sha(x) for x in v) or len(v) != len(set(v)):
        raise ValueError(f"{field} must be unique sha256 array")
    return sorted(v)

def str_list(v: Any, field: str) -> list[str]:
    if not isinstance(v, list):
        raise ValueError(f"{field} must be array")
    out = [nonempty(x, field) for x in v]
    if len(out) != len(set(out)):
        raise ValueError(f"{field} must be unique")
    return sorted(out)

def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict): raise ValueError("event must be object")
    control_plane.ControlPlane.validate_event(event)
    if event.get("event_type") != EVENT_TYPE: raise ValueError("steering transport must be feedback.observed")
    if event.get("authority_scope") != "request": raise ValueError("steering authority_scope must be request")
    if event.get("source", {}).get("kind") not in SOURCE_KINDS: raise ValueError("steering source must be user/authorized_human")
    resource = nonempty(event.get("resource_id"), "resource_id")
    session = nonempty(event.get("session_id"), "session_id")
    run = nonempty(event.get("run_id"), "run_id")
    artifacts = sha_list(event.get("artifact_fingerprints"), "artifact_fingerprints")
    p = event.get("payload")
    if not isinstance(p, dict): raise ValueError("payload must be object")
    exact(p, {"schema","kind","instruction","applicability","authored_against_checkpoint_id",
              "authority","canon_authority","framework_write_authority"}, "payload")
    if p["schema"] != REQUEST_SCHEMA or p["kind"] != PAYLOAD_KIND: raise ValueError("invalid steering payload identity")
    instruction = nonempty(p["instruction"], "instruction")
    if len(instruction) > 10000: raise ValueError("instruction too long")
    if any(p[k] is not False for k in ("authority","canon_authority","framework_write_authority")):
        raise ValueError("steering request cannot grant authority")
    a = p["applicability"]
    if not isinstance(a, dict): raise ValueError("applicability must be object")
    exact(a, {"scope","target_ref","consume_at"}, "applicability")
    if a["scope"] not in SCOPES or a["consume_at"] not in CONSUME_AT: raise ValueError("invalid applicability")
    target = a["target_ref"]
    if a["scope"] == "named_target": target = nonempty(target, "target_ref")
    elif target is not None: raise ValueError("target_ref only valid for named_target")
    return {"resource_id":resource,"session_id":session,"run_id":run,"artifact_fingerprints":artifacts,
            "checkpoint_id":nonempty(p["authored_against_checkpoint_id"],"checkpoint"),
            "instruction":instruction,"scope":a["scope"],"target_ref":target,"consume_at":a["consume_at"]}

def normalize_safe(v: Any) -> dict[str, Any]:
    if not isinstance(v, dict): raise ValueError("safe point must be object")
    fields = {"schema","resource_id","session_id","run_id","run_lineage","checkpoint_id","safe_point_id",
              "safe_point_kind","workflow_cursor","artifact_fingerprints","pending_handoff_ids",
              "consequential_write_state"}
    exact(v, fields, "safe_point")
    if v["schema"] != SAFE_POINT_SCHEMA: raise ValueError("invalid safe point schema")
    run = nonempty(v["run_id"], "run_id")
    lineage = str_list(v["run_lineage"], "run_lineage")
    if run not in lineage: raise ValueError("run_lineage must contain current run")
    if v["safe_point_kind"] not in SAFE_KINDS: raise ValueError("invalid safe point kind")
    if v["consequential_write_state"] not in WRITE_STATES: raise ValueError("invalid write state")
    return {"schema":SAFE_POINT_SCHEMA,"resource_id":nonempty(v["resource_id"],"resource_id"),
            "session_id":nonempty(v["session_id"],"session_id"),"run_id":run,"run_lineage":lineage,
            "checkpoint_id":nonempty(v["checkpoint_id"],"checkpoint_id"),
            "safe_point_id":nonempty(v["safe_point_id"],"safe_point_id"),
            "safe_point_kind":v["safe_point_kind"],"workflow_cursor":nonempty(v["workflow_cursor"],"workflow_cursor"),
            "artifact_fingerprints":sha_list(v["artifact_fingerprints"],"artifact_fingerprints"),
            "pending_handoff_ids":str_list(v["pending_handoff_ids"],"pending_handoff_ids"),
            "consequential_write_state":v["consequential_write_state"]}

def stored_event(cp: control_plane.ControlPlane, event_id: str) -> tuple[dict[str, Any], str]:
    with cp.connect() as c:
        row = c.execute("SELECT payload_json,payload_hash FROM events WHERE event_id=?", (nonempty(event_id,"event_id"),)).fetchone()
    if row is None: raise ValueError("unknown steering event")
    return json.loads(row["payload_json"]), row["payload_hash"]

def prepare(cp: control_plane.ControlPlane, event_id: str, safe_point: Any) -> dict[str, Any]:
    s = normalize_safe(safe_point)
    if s["consequential_write_state"] == "in_progress": raise ValueError("cannot consume steering inside consequential write")
    event, event_hash = stored_event(cp, event_id)
    e = validate_event(event)
    if e["consume_at"] != "next_safe_point" and s["safe_point_kind"] != e["consume_at"]:
        return {"schema":DECISION_INPUT_SCHEMA,"status":"not_due","event_id":event["event_id"],
                "event_hash":event_hash,"required_safe_point_kind":e["consume_at"],
                "current_safe_point_kind":s["safe_point_kind"],"decision_input_fingerprint":None,
                "authority":False,"canon_authority":False,"framework_write_authority":False,"model_execution":False}
    drift = []
    if e["resource_id"] != s["resource_id"]: drift.append("resource_id")
    if e["session_id"] != s["session_id"]: drift.append("session_id")
    if e["run_id"] not in s["run_lineage"]: drift.append("run_lineage")
    elif e["run_id"] != s["run_id"]: drift.append("resumed_run")
    if e["checkpoint_id"] != s["checkpoint_id"]: drift.append("checkpoint")
    if set(e["artifact_fingerprints"]) != set(s["artifact_fingerprints"]): drift.append("artifact_fingerprints")
    if {"resource_id","session_id","run_lineage"} & set(drift):
        return {"schema":DECISION_INPUT_SCHEMA,"status":"not_applicable","event_id":event["event_id"],
                "event_hash":event_hash,"binding_state":"target_mismatch","binding_drift":drift,
                "decision_input_fingerprint":None,"authority":False,"canon_authority":False,
                "framework_write_authority":False,"model_execution":False}
    binding = "exact" if not drift else ("resumed_lineage" if set(drift).issubset({"resumed_run","checkpoint"}) else "drifted")
    body = {"schema":DECISION_INPUT_SCHEMA,"status":"ready","event_id":event["event_id"],"event_hash":event_hash,
            "instruction":e["instruction"],"applicability":{"scope":e["scope"],"target_ref":e["target_ref"],"consume_at":e["consume_at"]},
            "authored_against":{"run_id":e["run_id"],"checkpoint_id":e["checkpoint_id"],
                                "artifact_fingerprints":e["artifact_fingerprints"]},
            "safe_point":s,"binding_state":binding,"binding_drift":drift,"authority":False,
            "canon_authority":False,"framework_write_authority":False,"model_execution":False}
    return {**body, "decision_input_fingerprint":fp(body)}

def normalize_decision(v: Any) -> dict[str, Any]:
    if not isinstance(v, dict): raise ValueError("decision must be object")
    fields = {"schema","decision_input_fingerprint","route","binding_acknowledgement",
              "invalidate_artifact_fingerprints","cancel_handoff_ids","deferred_target_ref","reason_ref",
              "authority","canon_authority","framework_write_authority","model_execution"}
    exact(v, fields, "decision")
    if v["schema"] != DECISION_SCHEMA or not is_sha(v["decision_input_fingerprint"]): raise ValueError("invalid decision identity")
    if v["route"] not in ROUTES or v["binding_acknowledgement"] not in ACKS: raise ValueError("invalid decision route/ack")
    if any(v[k] is not False for k in ("authority","canon_authority","framework_write_authority","model_execution")):
        raise ValueError("steering decision cannot grant authority")
    deferred = None if v["deferred_target_ref"] is None else nonempty(v["deferred_target_ref"],"deferred_target_ref")
    return {**v,"invalidate_artifact_fingerprints":sha_list(v["invalidate_artifact_fingerprints"],"invalidations"),
            "cancel_handoff_ids":str_list(v["cancel_handoff_ids"],"cancel_handoff_ids"),
            "deferred_target_ref":deferred,"reason_ref":nonempty(v["reason_ref"],"reason_ref")}

def validate_decision(v: Any, p: dict[str, Any]) -> dict[str, Any]:
    if p.get("status") != "ready": raise ValueError("event not applicable")
    d = normalize_decision(v)
    if d["decision_input_fingerprint"] != p["decision_input_fingerprint"]: raise ValueError("stale decision input")
    binding, ack, route = p["binding_state"], d["binding_acknowledgement"], d["route"]
    if binding == "exact" and ack != "exact": raise ValueError("exact binding requires exact ack")
    if binding != "exact" and ack == "exact": raise ValueError("drift cannot claim exact")
    if binding != "exact" and route not in {"await_user","defer_future"} and ack != "reinterpreted_against_current_state":
        raise ValueError("drifted action requires explicit reinterpretation")
    inv, cancel = set(d["invalidate_artifact_fingerprints"]), set(d["cancel_handoff_ids"])
    if not inv.issubset(set(p["safe_point"]["artifact_fingerprints"])): raise ValueError("invalid artifact invalidation")
    if not cancel.issubset(set(p["safe_point"]["pending_handoff_ids"])): raise ValueError("invalid handoff cancellation")
    if route == "continue" and (inv or cancel or d["deferred_target_ref"]): raise ValueError("continue must be side-effect free")
    if route in {"replan","regenerate"} and p["safe_point"]["artifact_fingerprints"] and not inv:
        raise ValueError(f"{route} requires explicit invalidation")
    if route == "cancel_handoff" and not cancel: raise ValueError("cancel_handoff requires pending ids")
    if route == "await_user" and (inv or cancel or d["deferred_target_ref"]): raise ValueError("await_user must not mutate")
    if route == "defer_future" and (not d["deferred_target_ref"] or inv or cancel): raise ValueError("invalid defer_future")
    if route == "rebuild_context" and (cancel or d["deferred_target_ref"]): raise ValueError("invalid rebuild_context")
    if p["applicability"]["scope"] == "current_run" and route == "defer_future" and ack != "reinterpreted_against_current_state":
        raise ValueError("current-run defer requires reinterpretation")
    return d

def followups(p: dict[str, Any], d: dict[str, Any]) -> list[dict[str, Any]]:
    ops = []
    if d["invalidate_artifact_fingerprints"]:
        ops.append({"op":"invalidate_artifacts","fingerprints":d["invalidate_artifact_fingerprints"],"execution_performed":False})
    if d["route"] in {"rebuild_context","replan","regenerate","await_user"}:
        ops.append({"op":d["route"],"run_id":p["safe_point"]["run_id"],"execution_performed":False})
    elif d["route"] == "cancel_handoff":
        ops += [{"op":"cancel_handoff","handoff_id":x,"execution_performed":False} for x in d["cancel_handoff_ids"]]
    elif d["route"] == "defer_future":
        ops.append({"op":"create_future_note_proposal","target_ref":d["deferred_target_ref"],"execution_performed":False})
    return ops

def consume(cp: control_plane.ControlPlane, event_id: str, safe_point: Any, decision: Any) -> dict[str, Any]:
    p = prepare(cp, event_id, safe_point); d = validate_decision(decision, p)
    _, event_hash = stored_event(cp, event_id)
    c = cp.consume_once("event", event_id, f"author_steering:{p['safe_point']['session_id']}", event_hash)
    return {"schema":RECEIPT_SCHEMA,"event_id":event_id,"event_hash":event_hash,
            "decision_input_fingerprint":p["decision_input_fingerprint"],"decision_fingerprint":fp(d),
            "route":d["route"],"binding_state":p["binding_state"],"consumed":c["consumed"],
            "already_consumed":c["already_consumed"],"consumption_key":c["consumption_key"],
            "required_followup_operations":followups(p,d),"followup_execution_performed":False,
            "authority":False,"canon_authority":False,"project_write_authority":False,
            "framework_write_authority":False,"settlement_authority":False,"model_execution":False}

def fixture_event(eid: str, instruction: str, *, scope="current_run", target=None, consume_at="next_safe_point", run="RUN-1", checkpoint="CKP-1", artifact="a", source="user"):
    return {"schema":control_plane.EVENT_SCHEMA,"event_id":eid,"event_type":EVENT_TYPE,
            "source":{"kind":source,"actor":"author","transport":"self_test","external_ref":None},
            "resource_id":"BOOK-S","session_id":"SES-S","run_id":run,"handoff_id":None,"authority_scope":"request",
            "idempotency_key":"idem-"+eid,"artifact_fingerprints":["sha256:"+artifact*64],
            "created_at":control_plane.now_iso(),"payload":{"schema":REQUEST_SCHEMA,"kind":PAYLOAD_KIND,
            "instruction":instruction,"applicability":{"scope":scope,"target_ref":target,"consume_at":consume_at},
            "authored_against_checkpoint_id":checkpoint,"authority":False,"canon_authority":False,"framework_write_authority":False}}

def fixture_safe(*, run="RUN-1", lineage=None, checkpoint="CKP-1", artifact="a", handoffs=None, write="none", kind="workflow_boundary"):
    return {"schema":SAFE_POINT_SCHEMA,"resource_id":"BOOK-S","session_id":"SES-S","run_id":run,
            "run_lineage":lineage or [run],"checkpoint_id":checkpoint,"safe_point_id":f"SAFE-{run}-{checkpoint}",
            "safe_point_kind":kind,"workflow_cursor":"draft.realization",
            "artifact_fingerprints":["sha256:"+artifact*64],"pending_handoff_ids":handoffs or [],
            "consequential_write_state":write}

def fixture_decision(p, route, *, ack="exact", invalidate=None, cancel=None, deferred=None):
    return {"schema":DECISION_SCHEMA,"decision_input_fingerprint":p["decision_input_fingerprint"],"route":route,
            "binding_acknowledgement":ack,"invalidate_artifact_fingerprints":invalidate or [],
            "cancel_handoff_ids":cancel or [],"deferred_target_ref":deferred,"reason_ref":"selftest:routing",
            "authority":False,"canon_authority":False,"framework_write_authority":False,"model_execution":False}

def blocked(fn):
    try: fn()
    except ValueError: return True
    return False

def self_test(path: Path) -> int:
    if path.exists(): path.unlink()
    cp = control_plane.ControlPlane(path); cp.init()
    e = fixture_event("EV-1","Change current POV."); first=cp.ingest_event(e); dup=cp.ingest_event(e)
    conflict=dict(e); conflict["payload"]=dict(e["payload"]); conflict["payload"]["instruction"]="Different"
    conflict_blocked=blocked(lambda:cp.ingest_event(conflict))
    s=fixture_safe(handoffs=["HO-OLD"]); p=prepare(cp,"EV-1",s); inv=p["safe_point"]["artifact_fingerprints"]
    d=fixture_decision(p,"regenerate",invalidate=inv); r=consume(cp,"EV-1",s,d); replay=consume(cp,"EV-1",s,d)
    write_blocked=blocked(lambda:prepare(cp,"EV-1",fixture_safe(write="in_progress")))
    stale_blocked=blocked(lambda:consume(cp,"EV-1",fixture_safe(checkpoint="CKP-2",artifact="b"),d))
    fe=fixture_event("EV-F","Less exposition next chapter.",scope="future_runs"); cp.ingest_event(fe)
    fs=fixture_safe(); fprep=prepare(cp,"EV-F",fs); fr=consume(cp,"EV-F",fs,fixture_decision(fprep,"defer_future",deferred="next_chapter"))
    re=fixture_event("EV-R","Keep conflict, change agency.",run="RUN-OLD",checkpoint="CKP-OLD"); cp.ingest_event(re)
    rs=fixture_safe(run="RUN-NEW",lineage=["RUN-OLD","RUN-NEW"],checkpoint="CKP-NEW")
    rp=prepare(cp,"EV-R",rs); rr=consume(cp,"EV-R",rs,fixture_decision(rp,"rebuild_context",ack="reinterpreted_against_current_state"))
    ce=fixture_event("EV-C","Stop obsolete reviewer."); cp.ingest_event(ce); cs=fixture_safe(handoffs=["HO-A"])
    cp0=prepare(cp,"EV-C",cs)
    bad_cancel=blocked(lambda:validate_decision(fixture_decision(cp0,"cancel_handoff",cancel=["HO-X"]),cp0))
    cr=consume(cp,"EV-C",cs,fixture_decision(cp0,"cancel_handoff",cancel=["HO-A"]))
    bad_source=blocked(lambda:validate_event(fixture_event("EV-B","No impersonation",source="semantic_worker")))
    due=fixture_event("EV-DUE","Apply this only before review.",consume_at="before_review"); cp.ingest_event(due)
    early=prepare(cp,"EV-DUE",fixture_safe(kind="before_draft")); ontime=prepare(cp,"EV-DUE",fixture_safe(kind="before_review"))
    we=fixture_event("EV-W","Other run",run="RUN-X"); cp.ingest_event(we); na=prepare(cp,"EV-W",fixture_safe())
    checks={
      "typed_event_ingress":first["accepted"] and not first["duplicate"],
      "duplicate_identical_delivery_is_idempotent":dup["duplicate"],
      "conflicting_duplicate_fails_closed":conflict_blocked,
      "safe_point_decision_is_fingerprint_bound":stale_blocked,
      "consequential_write_is_non_interruptible":write_blocked,
      "regenerate_requires_explicit_invalidation":r["route"]=="regenerate" and r["required_followup_operations"][0]["op"]=="invalidate_artifacts",
      "consume_once_survives_replay":r["consumed"] and replay["already_consumed"],
      "future_note_does_not_invalidate_current_candidate":fr["route"]=="defer_future" and all(x["op"]!="invalidate_artifacts" for x in fr["required_followup_operations"]),
      "resume_lineage_can_reinterpret_once":rp["binding_state"]=="resumed_lineage" and rr["consumed"],
      "handoff_cancel_is_bounded_to_pending_ids":bad_cancel and any(x.get("handoff_id")=="HO-A" for x in cr["required_followup_operations"]),
      "non_author_cannot_submit_author_steering":bad_source,
      "consume_at_is_enforced":early["status"]=="not_due" and ontime["status"]=="ready",
      "unrelated_run_does_not_consume_event":na["status"]=="not_applicable",
      "no_followup_side_effects_are_executed_here":all(not x["followup_execution_performed"] for x in [r,fr,rr,cr]),
      "steering_never_grants_durable_authority":all(not x[k] for x in [r,fr,rr,cr] for k in ["authority","canon_authority","project_write_authority","framework_write_authority","settlement_authority"])
    }
    ok=all(checks.values())
    print(json.dumps({"author_steering_contract":"PASS" if ok else "FAIL","transport_event_type":EVENT_TYPE,
      "payload_kind":PAYLOAD_KIND,"request_schema":REQUEST_SCHEMA,"safe_point_schema":SAFE_POINT_SCHEMA,
      "decision_schema":DECISION_SCHEMA,"receipt_schema":RECEIPT_SCHEMA,"routes":sorted(ROUTES),**checks,"model_execution":False},indent=2))
    return 0 if ok else 1

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--db",default=control_plane.DEFAULT_DB)
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("validate-event").add_argument("--event",required=True)
    q=sub.add_parser("prepare"); q.add_argument("--event-id",required=True); q.add_argument("--safe-point",required=True)
    q=sub.add_parser("consume"); q.add_argument("--event-id",required=True); q.add_argument("--safe-point",required=True); q.add_argument("--decision",required=True)
    q=sub.add_parser("self-test"); q.add_argument("--path")
    a=p.parse_args()
    if a.cmd=="self-test": return self_test(Path(a.path) if a.path else Path(tempfile.gettempdir())/"novelforge-author-steering.db")
    cp=control_plane.ControlPlane(a.db); cp.init()
    if a.cmd=="validate-event": out={"valid":True,**validate_event(control_plane.load_json(a.event))}
    elif a.cmd=="prepare": out=prepare(cp,a.event_id,control_plane.load_json(a.safe_point))
    else: out=consume(cp,a.event_id,control_plane.load_json(a.safe_point),control_plane.load_json(a.decision))
    print(json.dumps(out,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())