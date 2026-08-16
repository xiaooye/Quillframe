#!/usr/bin/env python3
"""Optional mechanical prose instrumentation for NovelForge.

This module is not a default Reader input and never produces literary truth.
Agents may call it on demand when mechanical measurements would help investigate
a semantic observation.  Generic NovelForge does not preload these numbers into
Blind Reader, Rule Auditor, Writer, or Editor context.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean, median
from typing import Any

SCHEMA = "novelforge_prose_telemetry_v2"
SENTENCE_END = re.compile(r"(?<=[。！？!?])|(?<=[.!?])(?=\s|$)")
DIALOGUE_PREFIX = tuple("\"'“‘「『")


def _paragraphs(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"\n\s*\n+", text.replace("\r\n", "\n")) if x.strip()]


def _sentences(paragraph: str) -> list[str]:
    bits = [x.strip() for x in SENTENCE_END.split(paragraph) if x.strip()]
    return bits or ([paragraph.strip()] if paragraph.strip() else [])


def _is_dialogue_only(paragraph: str) -> bool:
    stripped = paragraph.strip()
    return bool(stripped and stripped.startswith(DIALOGUE_PREFIX) and stripped.endswith(tuple("\"'”’」』")))


def _looks_fragment(sentence: str) -> bool:
    s = sentence.strip().strip("\"'“”‘’「」『』")
    return bool(s and len(s) <= 12 and s[-1:] not in "。！？!?.,;；：:")


def analyze(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be non-empty string")
    paragraphs = _paragraphs(text)
    sentence_lists = [_sentences(p) for p in paragraphs]
    sentences = [s for group in sentence_lists for s in group]
    sentence_lengths = [len(re.sub(r"\s+", "", s)) for s in sentences]
    spp = [len(group) for group in sentence_lists]
    dialogue_only = [_is_dialogue_only(p) for p in paragraphs]
    fragments = [_looks_fragment(s) for s in sentences]

    max_short_run = 0
    current = 0
    for p, count in zip(paragraphs, spp):
        short = count == 1 and len(re.sub(r"\s+", "", p)) <= 40
        current = current + 1 if short else 0
        max_short_run = max(max_short_run, current)

    n_p = len(paragraphs)
    n_s = len(sentences)
    return {
        "schema": SCHEMA,
        "paragraph_count": n_p,
        "sentence_count": n_s,
        "one_sentence_paragraph_ratio": sum(n == 1 for n in spp) / n_p if n_p else 0.0,
        "dialogue_only_paragraph_ratio": sum(dialogue_only) / n_p if n_p else 0.0,
        "sentences_per_paragraph": {
            "min": min(spp) if spp else 0,
            "max": max(spp) if spp else 0,
            "mean": mean(spp) if spp else 0.0,
            "median": median(spp) if spp else 0.0,
            "distribution": spp,
        },
        "sentence_length_chars": {
            "min": min(sentence_lengths) if sentence_lengths else 0,
            "max": max(sentence_lengths) if sentence_lengths else 0,
            "mean": mean(sentence_lengths) if sentence_lengths else 0.0,
            "median": median(sentence_lengths) if sentence_lengths else 0.0,
            "distribution": sentence_lengths,
        },
        "fragment_signal_ratio": sum(fragments) / n_s if n_s else 0.0,
        "max_consecutive_short_paragraph_run": max_short_run,
        "literary_verdict": None,
        "optional_diagnostic_tool": True,
        "default_production_context": False,
        "default_blind_reader_input": False,
        "metric_thresholds_are_generic_truth": False,
        "semantic_interpretation_required": True,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> dict[str, Any]:
    mixed = "第一段有两句。第二句继续推进。\n\n“停。”\n\n第三段重新展开，动作改变了局面。随后人物才回答。"
    short = "跑。\n\n停。\n\n看。\n\n门开了。"
    a = analyze(mixed)
    b = analyze(short)
    ok = all([
        a["paragraph_count"] == 3,
        a["sentences_per_paragraph"]["max"] >= 2,
        b["one_sentence_paragraph_ratio"] == 1.0,
        b["max_consecutive_short_paragraph_run"] == 4,
        a["literary_verdict"] is None and b["literary_verdict"] is None,
        a["optional_diagnostic_tool"] is True,
        a["default_blind_reader_input"] is False,
        a["metric_thresholds_are_generic_truth"] is False,
    ])
    return {
        "schema": SCHEMA,
        "prose_telemetry_contract": "PASS" if ok else "FAIL",
        "signals_only": True,
        "optional_diagnostic_tool": True,
        "default_production_context": False,
        "default_blind_reader_input": False,
        "short_paragraphs_auto_fail": False,
        "semantic_interpretation_required": True,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge optional prose telemetry")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--text")
    a.add_argument("--file")
    sub.add_parser("self-test")
    ns = p.parse_args()
    if ns.cmd == "self-test":
        out = self_test()
    else:
        if bool(ns.text) == bool(ns.file):
            raise ValueError("provide exactly one of --text or --file")
        text = ns.text if ns.text else Path(ns.file).read_text(encoding="utf-8")
        out = analyze(text)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("prose_telemetry_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
