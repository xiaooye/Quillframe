#!/usr/bin/env python3
"""Run one source-free, two-arm fiction instruction audition.

The runner performs exactly two direct Surface Writer calls against one frozen
scene contract.  It records provider usage and private arm provenance, then
exports only an anonymous A/B pair for the author.  It never judges prose,
promotes Craft, writes Canon, or invokes a reviewer.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from harness.integrations.chat_host_relay import SCHEMA as RELAY_SCHEMA, deadline_fields
from harness.integrations.codex_cli_relay import DriverConfig, RelayDriver


PLAN_SCHEMA = "quillframe_source_free_fiction_ab_plan_v1"
RECEIPT_SCHEMA = "quillframe_source_free_fiction_ab_receipt_v1"
EXPORT_SCHEMA = "quillframe_source_free_fiction_ab_blind_export_v1"
ARMS = ("baseline", "treatment")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _canonical(value)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def validate_plan(value: Any) -> dict[str, Any]:
    exact = {
        "schema", "run_id", "task_mode", "model_id", "source_free_voice_baseline",
        "scene_contract", "shared_author_objectives", "arm_instructions", "authority",
    }
    if not isinstance(value, dict) or set(value) != exact:
        raise ValueError("fiction A/B plan fields are invalid")
    if value.get("schema") != PLAN_SCHEMA or value.get("task_mode") != "SYSTEM-IMPROVE":
        raise ValueError("fiction A/B plan schema or task mode is invalid")
    if value.get("source_free_voice_baseline") is not True or value.get("authority") is not False:
        raise ValueError("fiction A/B plan must be source-free and non-authoritative")
    for key in ("run_id", "model_id", "shared_author_objectives"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"fiction A/B {key} must be non-empty text")
    scene = value.get("scene_contract")
    if not isinstance(scene, dict) or not scene:
        raise ValueError("fiction A/B scene_contract must be a non-empty object")
    forbidden = {
        "prose", "sample", "voice_sheet", "accepted_prose_tail", "rejected_prose",
        "reviewer_analysis", "repair_explanation", "private_character_enactment",
    }
    if forbidden.intersection(scene):
        raise ValueError("fiction A/B scene contract contains forbidden prose context")
    instructions = value.get("arm_instructions")
    if not isinstance(instructions, dict) or set(instructions) != set(ARMS):
        raise ValueError("fiction A/B requires exact baseline and treatment instructions")
    if any(not isinstance(instructions[arm], str) or not instructions[arm].strip() for arm in ARMS):
        raise ValueError("fiction A/B arm instructions must be non-empty text")
    forbidden_budget_fields = {
        "max_output_tokens", "max_tokens", "max_cost_micros", "run_cost_budget",
        "token_ceiling", "cost_ceiling",
    }
    if forbidden_budget_fields.intersection(value):
        raise ValueError("fiction A/B plan must not impose an author token or cost ceiling")
    return json.loads(json.dumps(value, ensure_ascii=False))


def writer_messages(plan: dict[str, Any], arm: str) -> list[dict[str, str]]:
    if arm not in ARMS:
        raise ValueError("unknown fiction A/B arm")
    common = (
        "你是本次 source-free 中文小说测试的 Surface Writer。只使用消息内的场景合同，"
        "直接写成可独立阅读的中文小说正文。不要调用工具，不要解释写法，不要输出标题、"
        "提纲、评语、检查清单或模型身份。正文从第一个字到最后一个字都由你生成。"
    )
    payload = {
        "source_free_voice_baseline": True,
        "shared_author_objectives": plan["shared_author_objectives"],
        "scene_realization_contract": plan["scene_contract"],
        "writer_instruction": plan["arm_instructions"][arm],
    }
    return [
        {"role": "system", "content": common},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def _request_packet(plan: dict[str, Any], arm: str) -> tuple[str, dict[str, Any]]:
    request_id = "req_" + uuid.uuid4().hex
    created = time.time()
    timing = deadline_fields(created, 590.0, None)
    messages = writer_messages(plan, arm)
    request_key = hashlib.sha256(_canonical({
        "run_id": plan["run_id"], "arm": arm, "model_id": plan["model_id"],
        "messages": messages,
    })).hexdigest()
    return request_id, {
        "schema": RELAY_SCHEMA,
        "request_id": request_id,
        **timing,
        "durable_pending": True,
        "request_key_fingerprint": request_key,
        "run_id": plan["run_id"],
        "request": {
            "model": "quillframe-chat-host-relay",
            "messages": messages,
            "response_format": {"type": "text"},
            "metadata": {"run_id": plan["run_id"]},
        },
        "manager_transport": True,
        "independent_review_evidence": False,
        "authority": False,
    }


def _exclusive_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


def _read_ledger(queue: Path) -> list[dict[str, Any]]:
    path = queue / "calls.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _confirmed_or_degraded_output(
    queue: Path, result: dict[str, Any], plan: dict[str, Any], arm: str,
) -> tuple[str, Any, str, list[str]]:
    failures = result.get("failure_codes") or []
    status = result.get("status")
    if status == "submitted":
        response = json.loads((queue / f'{result["request_id"]}.response.json').read_text(encoding="utf-8"))
        text = response.get("content")
        usage = response.get("usage")
        validation = "relay_submitted"
    elif (
        status == "failed"
        and result.get("returncode") == 0
        and result.get("output_matches_final_message") is True
        and isinstance(result.get("usage"), dict)
        and set(failures).issubset({"forbidden_cli_item", "invalid_cli_item"})
        and isinstance(result.get("output_file"), str)
    ):
        raw = (queue / result["output_file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != result.get("output_sha256"):
            raise RuntimeError(f"fiction A/B {arm} preserved output fingerprint changed")
        text = raw.decode("utf-8")
        usage = result["usage"]
        validation = "completed_with_preserved_cli_diagnostics"
    else:
        raise RuntimeError(f"fiction A/B {arm} call failed: {result}")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"fiction A/B {arm} returned empty prose")
    request_path = queue / f'{result["request_id"]}.request.json'
    packet = json.loads(request_path.read_text(encoding="utf-8"))
    if packet.get("request", {}).get("messages") != writer_messages(plan, arm):
        raise RuntimeError(f"fiction A/B {arm} preserved request no longer matches the plan")
    return text, usage, validation, list(failures)


def _recover_existing(queue: Path, plan: dict[str, Any], arm: str) -> tuple[str, Any, str, list[str]] | None:
    rows = _read_ledger(queue)
    finished = [row for row in rows if row.get("event") == "cli_finished"]
    if not finished:
        return None
    result = finished[-1]
    started = next(
        (row for row in rows if row.get("event") == "cli_started" and row.get("request_id") == result.get("request_id")),
        None,
    )
    if not isinstance(started, dict) or started.get("model") != plan["model_id"]:
        raise RuntimeError(f"fiction A/B {arm} existing checkpoint model mismatch")
    return _confirmed_or_degraded_output(queue, result, plan, arm)


def _render_html(export: dict[str, Any]) -> str:
    cards = []
    for item in export["candidates"]:
        cards.append(
            '<article class="card"><h2>版本 '
            + html.escape(item["label"])
            + "</h2><div class=\"prose\">"
            + "<br>".join(html.escape(item["text"]).splitlines())
            + "</div></article>"
        )
    return """<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>单样本匿名 A/B</title>
<style>body{margin:0;background:#f4f1ea;color:#25231f;font:17px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:860px;margin:auto;padding:20px}h1{font-size:1.35rem}.note{color:#675f53}.card{background:#fff;border-radius:14px;padding:18px;margin:18px 0;box-shadow:0 2px 14px #00000012}.card h2{margin-top:0;font-size:1.15rem}.prose{white-space:normal}footer{color:#675f53;font-size:.92rem;padding:10px 0 30px}</style></head><body><main>
<h1>单样本匿名 A/B</h1><p class=\"note\">请只按阅读感受选择 A、B，或“两者都不接受”。模型与指令身份已隐藏。</p>""" + "".join(cards) + """
<footer>这是一轮 source-free、100% AI-generated 测试；没有中文样本、旧稿或模型评委。</footer></main></body></html>"""


def run(
    plan_path: Path, output_dir: Path, cli_binary: str, *,
    allow_model_execution: bool, resume: bool = False,
) -> dict[str, Any]:
    plan_raw = plan_path.read_bytes()
    plan = validate_plan(json.loads(plan_raw.decode("utf-8")))
    if not allow_model_execution:
        raise ValueError("explicit --allow-model-execution is required")
    output_dir.mkdir(parents=True, exist_ok=resume)
    source_snapshot = hashlib.sha256(plan_raw).hexdigest()
    private_arms: list[dict[str, Any]] = []
    for index, arm in enumerate(ARMS):
        queue = output_dir / ("relay" if index == 0 else f"relay-{arm}")
        recovered = _recover_existing(queue, plan, arm) if resume else None
        if recovered is None:
            driver = RelayDriver(DriverConfig(
                queue=queue, cli_binary=cli_binary, run_id=plan["run_id"],
                source_snapshot_sha256=source_snapshot, model=plan["model_id"],
                reasoning_effort="xhigh", allow_model_execution=True,
                round_limit=2, manager_limit=1, worker_seconds=None,
            ))
            request_id, packet = _request_packet(plan, arm)
            request_path = queue / f"{request_id}.request.json"
            _exclusive_json(request_path, packet)
            result = driver.process_request(request_path)
            if not isinstance(result, dict):
                raise RuntimeError(f"fiction A/B {arm} did not return a typed relay result")
            text, usage, transport_validation, diagnostics = _confirmed_or_degraded_output(
                queue, result, plan, arm,
            )
        else:
            text, usage, transport_validation, diagnostics = recovered
            rows = _read_ledger(queue)
            request_id = next(row["request_id"] for row in reversed(rows) if row.get("event") == "cli_finished")
            packet = json.loads((queue / f"{request_id}.request.json").read_text(encoding="utf-8"))
        private_arms.append({
            "arm": arm, "request_id": request_id,
            "instruction_fingerprint": _sha(plan["arm_instructions"][arm]),
            "request_fingerprint": _sha(packet), "output_fingerprint": _sha(text.encode("utf-8")),
            "usage": usage, "transport_validation": transport_validation,
            "transport_diagnostics": diagnostics, "text": text,
        })
    order = [0, 1]
    secrets.SystemRandom().shuffle(order)
    labels = ("A", "B")
    candidates = []
    mapping = []
    for label, index in zip(labels, order):
        item = private_arms[index]
        candidates.append({"label": label, "text": item["text"], "output_fingerprint": item["output_fingerprint"]})
        mapping.append({"label": label, "arm": item["arm"], "output_fingerprint": item["output_fingerprint"]})
    export = {
        "schema": EXPORT_SCHEMA, "run_id": plan["run_id"],
        "source_free_voice_baseline": True, "model_identity_hidden": True,
        "candidates": candidates, "authority": False,
    }
    receipt = {
        "schema": RECEIPT_SCHEMA, "run_id": plan["run_id"], "task_mode": "SYSTEM-IMPROVE",
        "plan_fingerprint": _sha(plan), "scene_fingerprint": _sha(plan["scene_contract"]),
        "source_snapshot_sha256": source_snapshot, "model_id": plan["model_id"],
        "source_free_voice_baseline": True, "call_count": 2,
        "arms": private_arms, "blind_mapping": mapping,
        "literary_judgment": "author_only", "framework_promotion": False, "authority": False,
    }
    _exclusive_json(output_dir / "blind-export.json", export)
    _exclusive_json(output_dir / "private-receipt.json", receipt)
    (output_dir / "ab.html").write_text(_render_html(export), encoding="utf-8")
    return {"output_dir": str(output_dir), "blind_export": export, "receipt": receipt}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--codex-cli", required=True)
    parser.add_argument("--allow-model-execution", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    result = run(
        args.plan, args.output_dir, args.codex_cli,
        allow_model_execution=args.allow_model_execution,
        resume=args.resume,
    )
    print(json.dumps({
        "status": "completed", "output_dir": result["output_dir"],
        "candidate_fingerprints": [item["output_fingerprint"] for item in result["blind_export"]["candidates"]],
        "call_count": result["receipt"]["call_count"], "authority": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
