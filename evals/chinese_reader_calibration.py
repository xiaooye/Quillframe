"""Prepare and measure a small blind Chinese-prose calibration, without dispatch.

Reader jobs use the registered contract. Production-review *criteria* use its
entire contract snapshot through the existing eval_judge route: they are not
production reviews and cannot supply independent-release evidence. Fixtures and
their hidden labels are original synthetic author hypotheses, not human gold.

This module never starts a worker, repairs a result, scores prose, or promotes a
rule. A separately authorized caller must run each worker in a fresh, packet-only
context and supply its actual final result and execution identity. Reversing the
schedule requires new calls; this unary evaluation is not a pairwise preference
test. Only final semantic-worker result envelopes belong here, never host
reasoning logs. Hosts emitting a bare judgment must also archive those exact
model bytes; their deterministic envelope must use actual host metadata, not
model-reported identity, and must not be called the raw model response.
"""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.evaluation_execution_identity import (
    build_identity, canonical_bytes, file_fingerprint, fingerprint, validate_identity,
)
from harness.semantic_workers.semantic_worker_router import (
    find_forbidden_keys, find_named_keys, load_contract_registry,
    make_contract_job, make_eval_jobs, resolve_contract_registry,
    validate_contract_input, validate_job, validate_result, worker_job_view,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = Path(__file__).with_name("fixtures") / "chinese_reader_calibration.json"
READER = "reader.engagement_audit"
REVIEW = "quality.production_review"
CONTRACTS = (READER, REVIEW)
PRIVATE_KEYS = {"pair_id", "sample_id", "sample_description", "author_notes",
                "shared_events", "expected_result", "expectation_basis"}
CONTEXT_KEYS = {"genre_profile", "platform_profile", "chapter_position", "reader_grip"}
DISCLAIMER = (
    "Original synthetic fixtures; labels are provisional author hypotheses, not "
    "human quality validation or market evidence. Counts describe model/label "
    "agreement only. No production review, release, learning promotion or Canon authority."
)


def _raw_fingerprint(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return canonical_bytes(value) + b"\n"


def _strict_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out

    def invalid(_: str) -> None:
        raise ValueError("non-finite JSON number")

    def number(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("non-finite JSON number")
        return parsed

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=invalid, parse_float=number)


def _seal(value: dict[str, Any], key: str) -> dict[str, Any]:
    value[key] = fingerprint({k: v for k, v in value.items() if k != key})
    return value


def _check_seal(value: dict[str, Any], key: str) -> None:
    if value.get(key) != fingerprint({k: v for k, v in value.items() if k != key}):
        raise ValueError(f"{key} mismatch")


def load_suite(path: Path = DEFAULT_SUITE) -> dict[str, Any]:
    suite = _strict_json(Path(path).read_bytes())
    if not isinstance(suite, dict) or suite.get("schema") != "quillframe_chinese_reader_calibration_suite_v1":
        raise ValueError("calibration suite schema mismatch")
    provenance = suite.get("provenance", {})
    if (provenance.get("authorship") != "original_synthetic_assistant_authored"
            or any(provenance.get(k) is not False for k in (
                "derived_from_consumer", "derived_from_external_prose",
                "human_quality_validated", "market_evidence"))):
        raise ValueError("suite must disclose synthetic, non-consumer, unvalidated provenance")
    pairs = suite.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("paired samples required")
    pair_ids, sample_ids, texts = set(), set(), set()
    for pair in pairs:
        if not isinstance(pair, dict) or not isinstance(pair.get("pair_id"), str) or not pair["pair_id"]:
            raise ValueError("pair_id required")
        if pair["pair_id"] in pair_ids:
            raise ValueError("duplicate pair_id")
        pair_ids.add(pair["pair_id"])
        context = pair.get("reader_context")
        if not isinstance(context, dict) or set(context) != CONTEXT_KEYS:
            raise ValueError("reader context must contain only the declared reading profile")
        if any(not isinstance(context[k], str) or not context[k].strip() for k in CONTEXT_KEYS):
            raise ValueError("reader context values must be nonempty strings")
        samples = pair.get("samples")
        if not isinstance(samples, list) or len(samples) != 2:
            raise ValueError("each pair requires two complete samples")
        if {s.get("expected_result") for s in samples} != {"pass", "fail"}:
            raise ValueError("each pair requires one provisional pass and one fail hypothesis")
        for sample in samples:
            sid, paragraphs = sample.get("sample_id"), sample.get("paragraphs")
            if not isinstance(sid, str) or not sid or sid in sample_ids:
                raise ValueError("sample_id must be unique and nonempty")
            if (not isinstance(paragraphs, list) or not paragraphs
                    or any(not isinstance(p, str) or not p.strip() for p in paragraphs)):
                raise ValueError("complete sample paragraphs required")
            text = "\n\n".join(paragraphs)
            if text in texts:
                raise ValueError("duplicate sample text")
            texts.add(text)
            sample_ids.add(sid)
    return suite


def _source(contract_id: str, registry_path: Path | None) -> dict[str, Any]:
    path = Path(registry_path) if registry_path is not None else resolve_contract_registry(contract_id)[0]
    raw = path.read_bytes()
    registry = load_contract_registry(path)
    if path.read_bytes() != raw or registry != _strict_json(raw):
        raise ValueError("source registry changed while freezing its snapshot")
    contract = registry["contracts"].get(contract_id)
    if not isinstance(contract, dict):
        raise ValueError(f"missing source contract: {contract_id}")
    return {"contract_id": contract_id, "registry_schema": registry["schema"],
            "registry_version": registry["version"],
            "registry_file_fingerprint": _raw_fingerprint(raw),
            "contract_fingerprint": fingerprint(contract), "contract": deepcopy(contract)}


def _harness_binding() -> dict[str, str]:
    return {name: file_fingerprint(ROOT / name) for name in (
        "HARNESS_MANIFEST.yaml", "evals/build_judge_queue.py", "evals/run_evals.py",
        "evals/chinese_reader_calibration.py", "evals/evaluation_execution_identity.py",
        "harness/semantic_workers/model_contract_catalog.json",
        "harness/semantic_workers/semantic_worker_router.py",
        "harness/semantic_workers/semantic_worker_runner.py",
    )}


@dataclass(frozen=True)
class PreparedCalibration:
    """Keep the answer key separate; dispatch only worker_packet(), never this object."""

    blind_queue: dict[str, Any]
    jobs_payload: dict[str, Any]
    private_manifest: dict[str, Any]


def prepare_calibration(*, run_id: str, order_seed: str,
                        presentation_order: str = "forward", suite_path: Path = DEFAULT_SUITE,
                        registry_path: Path | None = None,
                        created_at: str | None = None) -> PreparedCalibration:
    """Prepare eight jobs for the shipped four scenes; no model is invoked.

    registry_path selects an explicitly supplied eval snapshot only. It cannot
    alter the registry used by production dispatch or release validation.
    """
    if not isinstance(run_id, str) or not run_id or not isinstance(order_seed, str) or not order_seed:
        raise ValueError("run_id and order_seed required")
    if presentation_order not in {"forward", "reverse"}:
        raise ValueError("presentation_order must be forward or reverse")
    suite = load_suite(suite_path)
    sources = {cid: _source(cid, registry_path) for cid in CONTRACTS}
    samples = [(pair, sample) for pair in suite["pairs"] for sample in pair["samples"]]
    samples.sort(key=lambda entry: fingerprint([order_seed, entry[1]["sample_id"]]))
    schedule = [(pair, sample, cid) for pair, sample in samples for cid in CONTRACTS]
    if presentation_order == "reverse":
        schedule.reverse()
    when = created_at or datetime.now(timezone.utc).isoformat()
    session = "CAL-" + fingerprint(run_id)[7:27]
    cases, jobs, dispatches = [], [], []
    for pair, sample, cid in schedule:
        source = sources[cid]
        # Never project arbitrary fixture metadata, even if the blind blacklist
        # does not know its key. Only prose and an explicit neutral profile cross.
        text = "\n\n".join(sample["paragraphs"])
        payload = {"candidate_text": text, "candidate_fingerprint": _raw_fingerprint(text.encode("utf-8")),
                   **{key: pair["reader_context"][key] for key in sorted(CONTEXT_KEYS)}}
        errors = validate_contract_input(cid, source["contract"], payload)
        if errors:
            raise ValueError("source contract input invalid: " + "; ".join(errors))
        alias = "SCENE-" + fingerprint([run_id, sample["sample_id"]])[7:27]
        case_id = fingerprint([run_id, sample["sample_id"], cid])[7:31]
        case = {"id": case_id, "type": "registered_reader" if cid == READER else "contract_criteria_calibration",
                "domain": "chinese_prose", "fixture": {
                    "calibration_only": True, "source_contract_snapshot": deepcopy(source),
                    "payload": deepcopy(payload)},
                "rubric": deepcopy(source["contract"]["rubric"]),
                "judgment_contract": deepcopy(source["contract"]["output_contract"])}
        if cid == READER:
            job = make_contract_job(cid, alias, payload, registry_path=registry_path,
                                    job_id="SEM-CAL-" + case_id, source_session_id=session)
        else:
            job = make_eval_jobs({"blind": True, "suite_version": suite["suite_version"],
                                  "cases": [case]}, source_session_id=session)["jobs"][0]
        job["created_at"] = when
        job["provenance"].update({"calibration_only": True, "production_release_eligible": False,
                                  "source_contract_id": cid,
                                  "source_contract_fingerprint": source["contract_fingerprint"],
                                  "source_registry_fingerprint": source["registry_file_fingerprint"]})
        jobs.append(job)
        cases.append(case)
        dispatches.append({"job_id": job["job_id"], "sample_id": sample["sample_id"],
                           "pair_id": pair["pair_id"], "source_contract_id": cid,
                           "source_contract_fingerprint": source["contract_fingerprint"],
                           "execution_kind": "registered_reader" if cid == READER else "criteria_snapshot_eval_judge",
                           "expected_result": sample["expected_result"],
                           "genre_profile": payload["genre_profile"],
                           "reading_profile_fingerprint": fingerprint(pair["reader_context"]),
                           "candidate_fingerprint": payload["candidate_fingerprint"],
                           "job_fingerprint": fingerprint(job)})
    queue = {"schema": "quillframe_blind_eval_queue_v1", "suite_version": suite["suite_version"],
             "blind": True, "cases": cases}
    jobs_payload = {"semantic_worker_queue_version": "2", "source_suite_version": suite["suite_version"],
                    "blind": True, "calibration_only": True, "production_release_eligible": False, "jobs": jobs}
    components = _harness_binding()
    manifest = {"schema": "quillframe_chinese_reader_calibration_plan_v1", "run_id": run_id,
                "suite_version": suite["suite_version"], "suite_file_fingerprint": file_fingerprint(suite_path),
                "fixture_provenance": deepcopy(suite["provenance"]), "disclaimer": DISCLAIMER,
                "calibration_only": True, "production_release_eligible": False,
                "order_seed": order_seed, "presentation_order": presentation_order,
                "source_contracts": sources, "planned_semantic_calls": len(jobs),
                "fresh_packet_only_worker_required": True, "dispatches": dispatches,
                "queue_fingerprint": _raw_fingerprint(_json_bytes(queue)),
                "jobs_fingerprint": _raw_fingerprint(_json_bytes(jobs_payload)),
                "harness_components": components, "harness_fingerprint": fingerprint(components)}
    _seal(manifest, "manifest_fingerprint")
    prepared = PreparedCalibration(queue, jobs_payload, manifest)
    validate_prepared(prepared)
    return prepared


def validate_prepared(prepared: PreparedCalibration) -> None:
    manifest = prepared.private_manifest
    _check_seal(manifest, "manifest_fingerprint")
    if manifest.get("schema") != "quillframe_chinese_reader_calibration_plan_v1":
        raise ValueError("calibration plan schema mismatch")
    if (manifest.get("calibration_only") is not True or manifest.get("production_release_eligible") is not False
            or prepared.jobs_payload.get("calibration_only") is not True
            or prepared.jobs_payload.get("production_release_eligible") is not False
            or prepared.blind_queue.get("blind") is not True or prepared.jobs_payload.get("blind") is not True):
        raise ValueError("calibration authority/blindness boundary changed")
    for name, data in (("queue", prepared.blind_queue), ("jobs", prepared.jobs_payload)):
        if manifest.get(name + "_fingerprint") != _raw_fingerprint(_json_bytes(data)):
            raise ValueError(name + " fingerprint mismatch")
    leaks = find_forbidden_keys(prepared.blind_queue) + find_named_keys(prepared.blind_queue, PRIVATE_KEYS)
    leaks += find_named_keys(prepared.jobs_payload, PRIVATE_KEYS)
    if leaks:
        raise ValueError("private calibration metadata leaked")
    jobs = prepared.jobs_payload["jobs"]
    dispatches = manifest["dispatches"]
    if len(jobs) != len(dispatches) or len(jobs) != manifest["planned_semantic_calls"]:
        raise ValueError("calibration schedule mismatch")
    if len({j["job_id"] for j in jobs}) != len(jobs):
        raise ValueError("duplicate calibration job")
    for job, entry, case in zip(jobs, dispatches, prepared.blind_queue["cases"], strict=True):
        if job["job_id"] != entry["job_id"] or fingerprint(job) != entry["job_fingerprint"]:
            raise ValueError("job binding mismatch")
        if validate_job(job):
            raise ValueError("invalid calibration job")
        if (job["provenance"].get("calibration_only") is not True
                or job["provenance"].get("production_release_eligible") is not False):
            raise ValueError("job must remain calibration-only")
        cid = entry["source_contract_id"]
        source = manifest["source_contracts"][cid]
        contract = source["contract"]
        if source["contract_fingerprint"] != fingerprint(contract):
            raise ValueError("contract snapshot fingerprint mismatch")
        if job["rubric"] != contract["rubric"] or job["output_contract"] != contract["output_contract"]:
            raise ValueError("calibration must preserve the complete source rubric/output contract")
        if case["fixture"]["source_contract_snapshot"] != source:
            raise ValueError("queue contract snapshot mismatch")
        if cid == READER:
            payload = job["input"]["payload"]
            if (job["kind"] != contract["kind"] or job["input"]["model_contract_id"] != cid
                    or job["input"]["model_contract_version"] != source["registry_version"]
                    or job["input"]["purpose"] != contract.get("purpose")
                    or job["permissions"] != contract["permissions"]):
                raise ValueError("Reader job differs from its source contract")
        else:
            if (cid != REVIEW or job["kind"] != "eval_judge"
                    or job["permissions"]["allowed_result_scope"] != "observation"
                    or "model_contract_id" in job["input"] or "dispatch_proof" in job
                    or job["input"]["fixture"] != case["fixture"]):
                raise ValueError("criteria snapshot must remain an isolated eval_judge")
            payload = job["input"]["fixture"]["payload"]
        if (validate_contract_input(cid, contract, payload) or payload != case["fixture"]["payload"]
                or set(payload) != CONTEXT_KEYS | {"candidate_text", "candidate_fingerprint"}
                or _raw_fingerprint(payload["candidate_text"].encode("utf-8")) != entry["candidate_fingerprint"]
                or payload["candidate_fingerprint"] != entry["candidate_fingerprint"]
                or fingerprint({k: payload[k] for k in CONTEXT_KEYS}) != entry["reading_profile_fingerprint"]):
            raise ValueError("candidate/input binding mismatch")


def worker_packet(prepared: PreparedCalibration, job_id: str) -> dict[str, Any]:
    """The only worker projection: one scene, no label map or counterpart."""
    validate_prepared(prepared)
    jobs = {j["job_id"]: j for j in prepared.jobs_payload["jobs"]}
    if job_id not in jobs:
        raise ValueError("unknown calibration job")
    return worker_job_view(jobs[job_id])


def _write_new(path: Path, raw: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(raw)


def save_prepared(prepared: PreparedCalibration, directory: Path) -> dict[str, str]:
    """Write a fresh eval-only directory; never overwrite a run or combine labels with packets."""
    validate_prepared(prepared)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for name, value in (("queue.json", prepared.blind_queue), ("jobs.json", prepared.jobs_payload),
                        ("private-manifest.json", prepared.private_manifest)):
        _write_new(directory / name, _json_bytes(value))
    return {name: prepared.private_manifest[name] for name in (
        "manifest_fingerprint", "queue_fingerprint", "jobs_fingerprint", "harness_fingerprint")}


def _validate_saved(prepared: PreparedCalibration, directory: Path) -> None:
    saved = _strict_json((directory / "private-manifest.json").read_bytes())
    if saved != prepared.private_manifest:
        raise ValueError("saved directory belongs to a different prepared run")
    for name in ("queue", "jobs"):
        if file_fingerprint(directory / (name + ".json")) != prepared.private_manifest[name + "_fingerprint"]:
            raise ValueError("saved " + name + " fingerprint mismatch")


def load_prepared(directory: Path) -> PreparedCalibration:
    """Reload the original frozen schedule rather than regenerate IDs or retry jobs."""
    directory = Path(directory)
    prepared = PreparedCalibration(
        _strict_json((directory / "queue.json").read_bytes()),
        _strict_json((directory / "jobs.json").read_bytes()),
        _strict_json((directory / "private-manifest.json").read_bytes()))
    validate_prepared(prepared)
    _validate_saved(prepared, directory)
    return prepared


def capture_execution_identity(prepared: PreparedCalibration, *, directory: Path,
                               capabilities: Path, candidate_commit: str, model_id: str,
                               reasoning_effort: str, env: dict[str, str]) -> dict[str, Any]:
    """Bind caller-supplied actual run settings; this captures identity, not execution."""
    validate_prepared(prepared)
    if _harness_binding() != prepared.private_manifest["harness_components"]:
        raise ValueError("calibration harness changed after preparation")
    directory = Path(directory)
    _validate_saved(prepared, directory)
    identity = build_identity(root=ROOT, queue=directory / "queue.json", jobs=directory / "jobs.json",
                              capabilities=Path(capabilities), candidate_commit=candidate_commit,
                              model_id=model_id, reasoning_effort=reasoning_effort,
                              domain="chinese_prose_calibration", env=env)
    identity["evaluation"].update({
        "harness_components": deepcopy(prepared.private_manifest["harness_components"]),
        "harness_fingerprint": prepared.private_manifest["harness_fingerprint"],
        "calibration_plan_fingerprint": prepared.private_manifest["manifest_fingerprint"],
    })
    return _seal(identity, "identity_fingerprint")


def _identity_errors(prepared: PreparedCalibration, identity: dict[str, Any]) -> list[str]:
    try:
        errors = validate_identity(identity)
    except (TypeError, AttributeError, KeyError, ValueError):
        return ["malformed execution identity"]
    evaluation = identity.get("evaluation", {})
    for key in ("queue_fingerprint", "jobs_fingerprint", "harness_fingerprint"):
        if evaluation.get(key) != prepared.private_manifest[key]:
            errors.append("execution identity " + key + " mismatch")
    return errors


def _classify(job: dict[str, Any], raw: bytes, identity: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    result: dict[str, Any] = {}
    try:
        result = _strict_json(raw)
        if not isinstance(result, dict):
            raise ValueError("result must be object")
        errors = validate_result(job, result)
        worker = result.get("worker", {})
        reviewer = identity["reviewer"]
        if worker.get("provider") != reviewer["provider"] or worker.get("model_or_reviewer") != reviewer["model_id"]:
            errors.append("worker/execution identity mismatch")
        execution = result.get("execution") or {}
        refs = {k: execution[k] for k in ("worker_session_id", "attempt_id")
                if isinstance(execution.get(k), str) and execution[k]}
        if isinstance(worker.get("run_reference"), str) and worker["run_reference"]:
            refs["run_reference"] = worker["run_reference"]
        if not any(k in refs for k in ("worker_session_id", "run_reference")):
            errors.append("actual worker lifecycle reference required; attempt_id alone is insufficient")
        if result.get("proposals"):
            errors.append("calibration cannot propose production actions")
        if result.get("status") == "completed" and result.get("errors"):
            errors.append("completed result contains errors")
    except (UnicodeError, ValueError, TypeError, AttributeError, KeyError, RecursionError):
        errors, refs = ["invalid strict JSON/result envelope"], {}
    status = "invalid" if errors else result["status"]
    return {"status": status, "semantic_result": result["judgment"]["result"] if status == "completed" else None,
            "errors": errors, "invocation_refs": refs}


def record_result(prepared: PreparedCalibration, *, directory: Path, job_id: str,
                  raw_result: bytes, execution_identity: dict[str, Any]) -> dict[str, Any]:
    """Preserve one actual semantic-worker result envelope byte for byte, even if invalid.

    An identity/reference supplied here is recorded evidence, not proof that a
    host ran or that its context was isolated. The authorized execution owner
    must retain and check the underlying host lifecycle separately.
    """
    job = worker_packet(prepared, job_id)
    if not isinstance(raw_result, bytes):
        raise ValueError("raw_result must be original final-result bytes")
    errors = _identity_errors(prepared, execution_identity)
    if errors:
        raise ValueError("; ".join(errors))
    observation = _classify(job, raw_result, execution_identity)
    directory = Path(directory)
    _validate_saved(prepared, directory)
    relative = Path("observations") / hashlib.sha256(job_id.encode()).hexdigest()[:24]
    target = directory / relative
    target.mkdir(parents=True, exist_ok=False)
    _write_new(target / "raw-result.json", raw_result)
    _write_new(target / "execution-identity.json", _json_bytes(execution_identity))
    receipt = {"schema": "quillframe_chinese_reader_calibration_observation_v1",
               "calibration_only": True, "production_release_eligible": False,
               "recorded_at": datetime.now(timezone.utc).isoformat(),
               "manifest_fingerprint": prepared.private_manifest["manifest_fingerprint"],
               "job_id": job_id, "input_fingerprint": job["input_fingerprint"],
               "raw_result_file": (relative / "raw-result.json").as_posix(),
               "raw_result_fingerprint": _raw_fingerprint(raw_result),
               "execution_identity_fingerprint": execution_identity["identity_fingerprint"],
               **observation}
    _seal(receipt, "observation_fingerprint")
    _write_new(target / "receipt.json", _json_bytes(receipt))
    return receipt


def summarize(prepared: PreparedCalibration, directory: Path) -> dict[str, Any]:
    """Count completed semantic verdicts against hidden hypotheses, never score the prose."""
    validate_prepared(prepared)
    directory = Path(directory)
    if directory.exists():
        _validate_saved(prepared, directory)
    jobs = {job["job_id"]: job for job in prepared.jobs_payload["jobs"]}
    receipts: dict[str, Any] = {}
    identities: dict[str, Any] = {}
    seen_refs: dict[tuple[str, str], str] = {}
    reused: set[str] = set()
    for path in sorted((directory / "observations").glob("*/receipt.json")):
        receipt = _strict_json(path.read_bytes())
        _check_seal(receipt, "observation_fingerprint")
        jid = receipt["job_id"]
        if jid not in jobs or jid in receipts:
            raise ValueError("unknown or duplicate observation")
        if receipt.get("manifest_fingerprint") != prepared.private_manifest["manifest_fingerprint"]:
            raise ValueError("observation belongs to a different calibration")
        if receipt.get("input_fingerprint") != jobs[jid]["input_fingerprint"]:
            raise ValueError("observation input fingerprint mismatch")
        raw = (path.parent / "raw-result.json").read_bytes()
        identity = _strict_json((path.parent / "execution-identity.json").read_bytes())
        if (receipt["raw_result_fingerprint"] != _raw_fingerprint(raw)
                or receipt["execution_identity_fingerprint"] != identity["identity_fingerprint"]
                or _identity_errors(prepared, identity)):
            raise ValueError("raw result/execution evidence binding mismatch")
        actual = _classify(jobs[jid], raw, identity)
        if any(receipt.get(k) != v for k, v in actual.items()):
            raise ValueError("observation disagrees with exact raw result")
        for key, ref in actual["invocation_refs"].items():
            scoped = (identity["reviewer"]["provider"], ref)
            if scoped in seen_refs and seen_refs[scoped] != jid:
                reused.update({jid, seen_refs[scoped]})
            seen_refs[scoped] = jid
        receipts[jid], identities[jid] = receipt, identity
    rows, groups = [], {}
    for entry in prepared.private_manifest["dispatches"]:
        jid, cid = entry["job_id"], entry["source_contract_id"]
        receipt = receipts.get(jid)
        status = "pending" if receipt is None else "invalid" if jid in reused else receipt["status"]
        observed = receipt["semantic_result"] if status == "completed" else None
        expected = entry["expected_result"]
        row = {**entry, "status": status, "observed_result": observed,
               "false_acceptance": observed == "pass" and expected == "fail",
               "false_rejection": observed == "fail" and expected == "pass",
               "raw_result_file": receipt["raw_result_file"] if receipt else None,
               "raw_result_fingerprint": receipt["raw_result_fingerprint"] if receipt else None,
               "execution_identity_fingerprint": receipt["execution_identity_fingerprint"] if receipt else None,
               "invocation_refs": deepcopy(receipt["invocation_refs"]) if receipt else {},
               "errors": ["worker invocation reused; fresh packet-only worker required"] if jid in reused
               else receipt["errors"] if receipt else []}
        rows.append(row)
        group = groups.setdefault(cid, {"planned": 0, "completed": 0, "pending": 0, "invalid": 0,
                                        "failed": 0, "unsupported": 0, "false_acceptance_count": 0,
                                        "false_rejection_count": 0, "evaluated_fail_hypotheses": 0,
                                        "evaluated_pass_hypotheses": 0})
        group["planned"] += 1
        group[status] += 1
        group["false_acceptance_count"] += int(row["false_acceptance"])
        group["false_rejection_count"] += int(row["false_rejection"])
        if status == "completed":
            group["evaluated_" + expected + "_hypotheses"] += 1
    for group in groups.values():
        for outcome, label in (("false_acceptance", "fail"), ("false_rejection", "pass")):
            denominator = group["evaluated_" + label + "_hypotheses"]
            group[outcome + "_rate"] = group[outcome + "_count"] / denominator if denominator else None
    configurations = {fingerprint({**{key: identity.get(key) for key in (
        "candidate", "reviewer", "environment", "resource_budget")},
        "capabilities_fingerprint": identity["evaluation"].get("capabilities_fingerprint"),
        "harness_fingerprint": identity["evaluation"].get("harness_fingerprint")}) for identity in identities.values()}
    comparable = len(configurations) <= 1
    pending = any(row["status"] == "pending" for row in rows)
    complete = all(row["status"] == "completed" for row in rows)
    summary = {"schema": "quillframe_chinese_reader_calibration_report_v1",
               "calibration_only": True, "production_release_eligible": False, "disclaimer": DISCLAIMER,
               "status": "INCOMPARABLE" if not comparable else "COMPLETE" if complete
               else "PENDING_MODEL" if pending else "INCOMPLETE",
               "manifest_fingerprint": prepared.private_manifest["manifest_fingerprint"],
               "suite_file_fingerprint": prepared.private_manifest["suite_file_fingerprint"],
               "source_contracts": deepcopy(prepared.private_manifest["source_contracts"]),
               "presentation_order": prepared.private_manifest["presentation_order"],
               "order_seed": prepared.private_manifest["order_seed"],
               "groups": groups, "observations": rows,
               "execution_identities": identities,
               "execution_configuration_consistent": comparable,
               "execution_configuration_fingerprints": sorted(configurations),
               "contains_private_expectations": True,
               "host_isolation_independently_verified": False,
               "unary_schedule_not_pairwise_preference": True,
               "model_calls_dispatched_by_this_module": 0}
    return _seal(summary, "report_fingerprint")


def compare_reports(reference: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    """Describe a registry or schedule control; never recommend promotion from four scenes."""
    for report in (reference, comparison):
        _check_seal(report, "report_fingerprint")
        if report.get("schema") != "quillframe_chinese_reader_calibration_report_v1":
            raise ValueError("calibration report schema mismatch")
    if reference["suite_file_fingerprint"] != comparison["suite_file_fingerprint"]:
        raise ValueError("comparison requires the same frozen texts and hidden hypotheses")
    keyed = [{(row["sample_id"], row["source_contract_id"]): row for row in report["observations"]}
             for report in (reference, comparison)]
    if set(keyed[0]) != set(keyed[1]) or reference["order_seed"] != comparison["order_seed"]:
        raise ValueError("comparison sample set/order seed mismatch")
    for key in keyed[0]:
        if any(keyed[0][key][field] != keyed[1][key][field] for field in (
                "candidate_fingerprint", "reading_profile_fingerprint", "expected_result")):
            raise ValueError("comparison changed text, reading profile or hidden hypothesis")
    configurations = [report["execution_configuration_fingerprints"] for report in (reference, comparison)]
    refs = [{value for row in report["observations"] for value in row["invocation_refs"].values()}
            for report in (reference, comparison)]
    reused = bool(refs[0] & refs[1])
    complete = all(report["status"] == "COMPLETE" for report in (reference, comparison))
    controlled = (not reused and all(report["execution_configuration_consistent"] for report in (reference, comparison))
                  and len(configurations[0]) == 1 and configurations[0] == configurations[1])
    if (reused or any(not report["execution_configuration_consistent"] for report in (reference, comparison))
            or (all(configurations) and configurations[0] != configurations[1])):
        status = "INCOMPARABLE"
    elif any(report["status"] == "PENDING_MODEL" for report in (reference, comparison)):
        status = "PENDING_MODEL"
    else:
        status = "COMPARABLE" if complete and controlled else "INCOMPLETE"
    changes = [{"sample_id": key[0], "source_contract_id": key[1],
                "reference_result": keyed[0][key]["observed_result"],
                "comparison_result": keyed[1][key]["observed_result"]}
               for key in keyed[0] if keyed[0][key]["status"] == keyed[1][key]["status"] == "completed"
               and keyed[0][key]["observed_result"] != keyed[1][key]["observed_result"]]
    result = {"schema": "quillframe_chinese_reader_calibration_comparison_v1",
              "calibration_only": True, "production_release_eligible": False, "disclaimer": DISCLAIMER,
              "status": status, "reference_report_fingerprint": reference["report_fingerprint"],
              "comparison_report_fingerprint": comparison["report_fingerprint"],
              "reference_source_contracts": reference["source_contracts"],
              "comparison_source_contracts": comparison["source_contracts"],
              "presentation_orders": [reference["presentation_order"], comparison["presentation_order"]],
              "changed_factors": [name for name, changed in (
                  ("contract_snapshot", reference["source_contracts"] != comparison["source_contracts"]),
                  ("presentation_schedule", reference["presentation_order"] != comparison["presentation_order"])) if changed],
              "worker_lifecycle_reused_across_runs": reused,
              "verdict_changes": changes, "count_deltas": {},
              "causal_quality_improvement_established": False,
              "unary_schedule_not_pairwise_preference": True}
    if status == "COMPARABLE":
        result["count_deltas"] = {cid: {key: comparison["groups"][cid][key] - reference["groups"][cid][key]
                                        for key in ("false_acceptance_count", "false_rejection_count")}
                                  for cid in CONTRACTS}
    return _seal(result, "comparison_fingerprint")
