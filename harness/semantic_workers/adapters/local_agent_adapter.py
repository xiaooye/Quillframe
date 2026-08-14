#!/usr/bin/env python3
"""Local Codex/Claude independent semantic-review adapter.

stdin: one semantic job JSON
stdout: one semantic result JSON
A fresh subprocess and temporary workspace are used for each job.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
WORKER_DIR = HERE.parent.parent
if str(WORKER_DIR) not in sys.path: sys.path.insert(0, str(WORKER_DIR))
from semantic_worker_router import validate_job, validate_result  # noqa: E402

SUPPORTED_KINDS = {"eval_judge", "artifact_audit"}
JUDGMENT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["verdict","result","codes","evidence","confidence"],
    "properties": {
        "verdict": {"type": ["string","null"], "enum": ["accept","reject",None]},
        "result": {"type": ["string","null"], "enum": ["pass","fail",None]},
        "codes": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    }
}


def dump(v: Any) -> None: print(json.dumps(v, ensure_ascii=False, separators=(",", ":")))
def exe(name: str) -> str | None: return shutil.which(name)

def select(requested: str) -> str | None:
    if requested == "codex": return "codex" if exe("codex") else None
    if requested == "claude": return "claude" if exe("claude") else None
    return "codex" if exe("codex") else ("claude" if exe("claude") else None)


def empty_judgment() -> dict[str, Any]: return {"verdict": None, "result": None, "codes": [], "evidence": [], "confidence": 0.0}

def typed(job: dict[str, Any], provider: str, status: str, *, judgment: dict[str, Any] | None = None, run_ref: str | None = None, errors: list[str] | None = None) -> dict[str, Any]:
    lineage = dict(job.get("execution") or {})
    lineage["worker_session_id"] = lineage.get("worker_session_id") or f"SES-LOCAL-{uuid.uuid4().hex}"
    lineage["attempt_id"] = lineage.get("attempt_id") or f"ATT-{uuid.uuid4().hex}"
    return {
        "job_id": job.get("job_id","unknown"), "subject_id": job.get("subject_id","unknown"), "kind": job.get("kind","eval_judge"),
        "input_fingerprint": job.get("input_fingerprint","sha256:" + "0" * 64), "status": status,
        "worker": {"provider": f"{provider}_cli", "model_or_reviewer": os.getenv(f"NOVEL_OS_{provider.upper()}_MODEL", f"{provider} configured model"), "run_reference": run_ref},
        "judgment": judgment or empty_judgment(), "proposals": [], "errors": errors or [], "execution": lineage,
    }


def prompt(job: dict[str, Any]) -> str:
    bounded = {k: job.get(k) for k in ("kind","subject_id","input_fingerprint","input","rubric","output_contract","permissions","provenance")}
    return (
        "You are an independent semantic reviewer in a fiction-production harness. Judge ONLY the blind packet below. "
        "Do not inspect repository/project files, do not search for expected labels, do not use tools, and do not provide private chain-of-thought. "
        "Return ONLY one JSON object with verdict accept/reject/null, result pass/fail/null, codes string[], evidence short observable findings[], confidence 0..1. "
        "Do not propose Canon settlement, OS promotion, durable user-taste writes, permissions, or story-direction writes.\n\n" +
        json.dumps(bounded, ensure_ascii=False, indent=2)
    )


def parse_json_text(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()[1:]
        if lines and lines[-1].strip() == "```": lines = lines[:-1]
        value = "\n".join(lines).strip()
    obj = json.loads(value)
    if not isinstance(obj, dict): raise ValueError("judgment must be object")
    return obj


def validate_judgment(j: dict[str, Any]) -> list[str]:
    e: list[str] = []; required = {"verdict","result","codes","evidence","confidence"}
    if set(j) != required: e.append("judgment fields must exactly match schema")
    if j.get("verdict") not in {None,"accept","reject"}: e.append("invalid verdict")
    if j.get("result") not in {None,"pass","fail"}: e.append("invalid result")
    if not isinstance(j.get("codes"), list) or not all(isinstance(x,str) for x in j.get("codes",[])): e.append("codes must be string array")
    if not isinstance(j.get("evidence"), list) or not all(isinstance(x,str) for x in j.get("evidence",[])): e.append("evidence must be string array")
    c = j.get("confidence")
    if not isinstance(c,(int,float)) or isinstance(c,bool) or not 0 <= c <= 1: e.append("confidence must be 0..1")
    return e


def codex_command(schema: Path, output: Path) -> list[str]:
    cmd = [exe("codex") or "codex", "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--output-schema", str(schema), "--output-last-message", str(output)]
    model = os.getenv("NOVEL_OS_CODEX_MODEL", "").strip()
    if model: cmd += ["--model", model]
    return cmd + ["-"]


def claude_command() -> list[str]:
    cmd = [exe("claude") or "claude", "-p", "Review the semantic packet supplied on stdin and return only the requested JSON judgment.", "--output-format", "json", "--max-turns", "1", "--permission-mode", "plan"]
    model = os.getenv("NOVEL_OS_CLAUDE_MODEL", "").strip()
    if model: cmd += ["--model", model]
    return cmd


def extract_claude(stdout: str) -> dict[str, Any]:
    outer = json.loads(stdout)
    if isinstance(outer, dict):
        if isinstance(outer.get("structured_output"), dict): return outer["structured_output"]
        if isinstance(outer.get("result"), dict): return outer["result"]
        if isinstance(outer.get("result"), str): return parse_json_text(outer["result"])
        if {"verdict","result","codes","evidence","confidence"}.issubset(outer): return outer
    raise ValueError("Claude JSON has no parseable judgment")


def execute(job: dict[str, Any], requested: str, timeout: int) -> dict[str, Any]:
    errors = validate_job(job); provider = select(requested); label = provider or (requested if requested in {"codex","claude"} else "codex")
    if errors: return typed(job, label, "failed", errors=["invalid semantic job: " + "; ".join(errors)])
    if job["kind"] not in SUPPORTED_KINDS: return typed(job, label, "unsupported", errors=[f"unsupported kind={job['kind']}"])
    if provider is None: return typed(job, label, "failed", errors=[f"local agent unavailable: {requested}"])
    run_ref = f"local-{provider}:{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="novel-os-semantic-") as td:
        wd = Path(td)
        try:
            if provider == "codex":
                schema = wd / "judgment.schema.json"; output = wd / "judgment.json"; schema.write_text(json.dumps(JUDGMENT_SCHEMA), encoding="utf-8")
                proc = subprocess.run(codex_command(schema, output), input=prompt(job), text=True, capture_output=True, cwd=wd, timeout=timeout, check=False)
                if proc.returncode != 0: return typed(job, provider, "failed", run_ref=run_ref, errors=[f"Codex exited {proc.returncode}: {proc.stderr.strip()[:2000]}"])
                if not output.exists(): return typed(job, provider, "failed", run_ref=run_ref, errors=["Codex produced no output file"])
                judgment = parse_json_text(output.read_text(encoding="utf-8"))
            else:
                proc = subprocess.run(claude_command(), input=prompt(job), text=True, capture_output=True, cwd=wd, timeout=timeout, check=False)
                if proc.returncode != 0: return typed(job, provider, "failed", run_ref=run_ref, errors=[f"Claude exited {proc.returncode}: {proc.stderr.strip()[:2000]}"])
                judgment = extract_claude(proc.stdout)
        except subprocess.TimeoutExpired: return typed(job, provider, "failed", run_ref=run_ref, errors=[f"{provider} timeout after {timeout}s"])
        except (OSError, ValueError, json.JSONDecodeError) as exc: return typed(job, provider, "failed", run_ref=run_ref, errors=[f"{provider} execution invalid: {exc}"])
    shape = validate_judgment(judgment)
    if shape: return typed(job, provider, "failed", run_ref=run_ref, errors=shape)
    result = typed(job, provider, "completed", judgment=judgment, run_ref=run_ref)
    binding = validate_result(job, result)
    return result if not binding else typed(job, provider, "failed", run_ref=run_ref, errors=["self-validation: " + "; ".join(binding)])


def self_test() -> int:
    sample = {"verdict":"accept","result":None,"codes":[],"evidence":["fixture"],"confidence":0.8}
    parsed = extract_claude(json.dumps({"type":"result","result":json.dumps(sample)}))
    cmd = codex_command(Path("/tmp/schema.json"), Path("/tmp/out.json"))
    ok = not validate_judgment(parsed) and "exec" in cmd and "--ephemeral" in cmd and "--output-schema" in cmd and "--sandbox" in cmd
    dump({"local_agent_adapter_contract":"PASS" if ok else "FAIL","codex_binary_detected":bool(exe("codex")),"claude_binary_detected":bool(exe("claude")),"isolated_temp_workspace":True})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--provider", choices=["auto","codex","claude"], default=os.getenv("NOVEL_OS_LOCAL_AGENT_PROVIDER","auto")); p.add_argument("--timeout", type=int, default=180); p.add_argument("--capabilities", action="store_true"); p.add_argument("--self-test", action="store_true"); args=p.parse_args()
    if args.self_test: return self_test()
    if args.capabilities:
        selected=select(args.provider); dump({"adapter":"local-agent-cli","adapter_version":"0.2","requested_provider":args.provider,"selected_provider":selected,"codex_binary_available":bool(exe("codex")),"claude_binary_available":bool(exe("claude")),"available":selected is not None,"supported_kinds":sorted(SUPPORTED_KINDS),"independence_boundary":"separate_local_agent_process","api_key_required_by_harness":False}); return 0
    try: job=json.load(sys.stdin)
    except Exception as exc: dump({"status":"failed","errors":[f"stdin job invalid: {exc}"]}); return 1
    result=execute(job,args.provider,args.timeout); dump(result); return 0 if result.get("status") in {"completed","unsupported"} else 1


if __name__ == "__main__": raise SystemExit(main())
