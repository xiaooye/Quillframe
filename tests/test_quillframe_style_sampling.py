"""Safety and behavior tests for ephemeral style sampling.

All passages below are synthetic fixtures written for these tests.  The suite
does not open or inspect any corpus source file.
"""
from __future__ import annotations

import copy
import json
import tracemalloc
import unittest
from unittest.mock import patch

import corpus.style_sampling as style_sampling
from corpus.style_sampling import (
    ROLE_LAYERS,
    MAX_SOURCE_CHARS,
    MAX_STREAM_CHUNK_CHARS,
    STYLE_SAMPLE_ROLES,
    STYLE_SAMPLING_MANIFEST_SCHEMA,
    STYLE_SAMPLING_RESULT_SCHEMA,
    StyleSampler,
    StyleSamplingError,
    fingerprint_source_text,
    materialize_style_chunk_span,
    sample_style_chunks,
    sample_style_windows,
    style_window_hygiene_reason,
    style_window_passes_hygiene,
    validate_sampling_manifest,
)


SYNTHETIC_STYLE_TEXT = """第一章 雨夜
SAMPLE_PRIVATE_SENTINEL 雨水敲着房间的窗，冷风卷过街道。
“现在就走。”姐姐说。
***
她想起多年前的约定，终于意识到自己一直害怕失去朋友。
随后，她转身冲下楼梯，抓住妹妹的手，把门推开。
***
镜中的人留着长发，眼眸明亮，丰满的身材和巨乳被宽外套遮住。
Chapter 2: Return
Meanwhile, moonlight crossed the empty street and the river smelled of rain.
“I remember,” her old friend said, “because we trusted each other.”
---
The next morning, he ran across the room, pushed the chair aside, and stopped.
Epilogue
At last, they returned home and accepted what their choice had changed.
"""


def _all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_keys(child))
    return keys


def _sample(text: str = SYNTHETIC_STYLE_TEXT, **options: object) -> dict:
    return sample_style_windows(
        text,
        source_fingerprint=fingerprint_source_text(text),
        target_window_chars=options.pop("target_window_chars", 96),
        max_window_chars=options.pop("max_window_chars", 180),
        **options,
    )


class StyleSamplingTests(unittest.TestCase):
    def test_role_catalog_is_functionally_layered_and_complete(self) -> None:
        self.assertEqual(
            STYLE_SAMPLE_ROLES,
            (
                "opening",
                "dialogue",
                "action",
                "interiority",
                "exposition",
                "environment",
                "body_appearance",
                "relationship",
                "transition",
                "ending",
            ),
        )
        flattened = [role for roles in ROLE_LAYERS.values() for role in roles]
        self.assertEqual(set(flattened), set(STYLE_SAMPLE_ROLES))
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_chinese_english_chapters_scenes_and_functional_roles_are_detected(self) -> None:
        result = _sample(max_windows=12, max_overlap_ratio=0.2)

        self.assertEqual(result["schema"], STYLE_SAMPLING_RESULT_SCHEMA)
        manifest = result["manifest"]
        self.assertEqual(manifest["schema"], STYLE_SAMPLING_MANIFEST_SCHEMA)
        self.assertEqual(manifest["segmentation"]["chapter_count"], 3)
        self.assertEqual(manifest["segmentation"]["scene_count"], 6)
        self.assertEqual(manifest["segmentation"]["chapter_heading_count"], 3)
        self.assertEqual(manifest["segmentation"]["scene_separator_count"], 3)
        candidate_roles = {
            role for window in manifest["windows"] for role in window["candidate_roles"]
        }
        self.assertEqual(candidate_roles, set(STYLE_SAMPLE_ROLES))
        self.assertEqual(manifest["coverage"]["state"], "complete")
        self.assertEqual(manifest["coverage"]["coverage_gaps"], [])
        self.assertTrue(all(layer["state"] == "complete" for layer in manifest["functional_layers"]))
        validate_sampling_manifest(manifest)

    def test_manifest_is_closed_and_prose_free_while_windows_are_exact_and_ephemeral(self) -> None:
        result = _sample()
        manifest = result["manifest"]
        serialized_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

        self.assertNotIn("SAMPLE_PRIVATE_SENTINEL", serialized_manifest)
        self.assertNotIn("巨乳", serialized_manifest)
        self.assertFalse(
            _all_keys(manifest).intersection(
                {"text", "raw", "raw_text", "passage", "excerpt", "quote", "summary"}
            )
        )
        self.assertFalse(manifest["persistence_boundary"]["manifest_contains_prose"])
        self.assertFalse(manifest["persistence_boundary"]["ephemeral_windows_persistable"])

        by_id = {window["window_id"]: window for window in manifest["windows"]}
        self.assertEqual(
            {window["window_id"] for window in result["ephemeral_windows"]},
            set(manifest["current_window_ids"]),
        )
        for ephemeral in result["ephemeral_windows"]:
            durable = by_id[ephemeral["window_id"]]
            start, end = ephemeral["span"]["start"], ephemeral["span"]["end"]
            self.assertEqual(ephemeral["text"], SYNTHETIC_STYLE_TEXT[start:end])
            self.assertEqual(
                ephemeral["passage_fingerprint"],
                fingerprint_source_text(ephemeral["text"]),
            )
            self.assertEqual(ephemeral["passage_fingerprint"], durable["passage_fingerprint"])
            self.assertEqual(ephemeral["persistence"], "ephemeral_call_only")

    def test_keyword_roles_are_candidates_and_never_adult_classification(self) -> None:
        text = "第一章\n她照镜子，看见自己的长发、胸部、丰满身材与巨乳。\n尾声\n她披上外套离开。"
        result = _sample(
            text,
            requested_roles=("body_appearance",),
            max_windows=2,
            target_window_chars=40,
            max_window_chars=90,
        )
        manifest = result["manifest"]

        self.assertIn("body_appearance", manifest["coverage"]["covered_roles"])
        self.assertEqual(
            manifest["role_assignment"],
            {
                "state": "candidate_hint_only",
                "method": "structural_positions_and_precomputed_candidate_hints",
                "keywords_are_candidates_only": True,
                "semantic_literary_judgment_performed": False,
                "adult_content_classification_performed": False,
            },
        )
        self.assertTrue(manifest["role_assignment"]["keywords_are_candidates_only"])
        self.assertFalse(
            manifest["role_assignment"]["semantic_literary_judgment_performed"]
        )
        self.assertFalse(
            manifest["role_assignment"]["adult_content_classification_performed"]
        )
        self.assertNotIn("profile", _all_keys(manifest))
        self.assertNotIn("adult_explicit", json.dumps(manifest, ensure_ascii=False))
        self.assertNotIn("scene_function", _all_keys(manifest))
        self.assertNotIn("style_classification", _all_keys(manifest))
        for appearance in (
            "她身材高挑，长发落在肩膀上。",
            "她身材丰满，巨乳被宽外套自然遮住。",
        ):
            with self.subTest(appearance=appearance):
                self.assertIsNone(style_window_hygiene_reason(appearance))
                self.assertTrue(style_window_passes_hygiene(appearance))

    def test_surface_pattern_work_is_once_per_atom_not_once_per_candidate(self) -> None:
        class CountingPattern:
            def __init__(self) -> None:
                self.search_calls = 0

            def search(self, _text: str) -> None:
                self.search_calls += 1
                return None

        text = "第一章\n" + "\n".join(
            f"合成段落{i}沿着一条清楚的结构线展开，并在这里自然结束。"
            for i in range(30)
        )
        options = {
            "requested_roles": ("opening", "ending"),
            "max_windows": 2,
            "target_window_chars": 96,
            "max_window_chars": 160,
            "max_overlap_ratio": 0.1,
        }

        for mode, builder_name in (
            ("in_memory", "_candidate_from_span"),
            ("stream", "_candidate_from_spooled_atoms"),
        ):
            patterns = {
                role: CountingPattern()
                for role in style_sampling._ROLE_SIGNAL_PATTERNS
            }
            builder = getattr(style_sampling, builder_name)
            with self.subTest(mode=mode), patch.object(
                style_sampling, "_ROLE_SIGNAL_PATTERNS", patterns
            ), patch.object(style_sampling, builder_name, wraps=builder) as build_calls:
                if mode == "in_memory":
                    result = sample_style_windows(
                        text,
                        source_fingerprint=fingerprint_source_text(text),
                        **options,
                    )
                else:
                    result = sample_style_chunks(
                        [text[index : index + 19] for index in range(0, len(text), 19)],
                        **options,
                    )

            unit_count = result["manifest"]["segmentation"]["unit_count"]
            self.assertGreater(build_calls.call_count, unit_count)
            self.assertTrue(patterns)
            self.assertEqual(
                {pattern.search_calls for pattern in patterns.values()},
                {unit_count},
            )

    def test_selection_is_deterministic_and_suppresses_overlap(self) -> None:
        first = _sample(max_windows=10, max_overlap_ratio=0.15)
        second = _sample(max_windows=10, max_overlap_ratio=0.15)
        self.assertEqual(first, second)

        windows = first["manifest"]["windows"]
        for index, left in enumerate(windows):
            for right in windows[index + 1 :]:
                left_start, left_end = left["span"]["start"], left["span"]["end"]
                right_start, right_end = right["span"]["start"], right["span"]["end"]
                intersection = max(0, min(left_end, right_end) - max(left_start, right_start))
                smaller = min(left_end - left_start, right_end - right_start)
                self.assertLessEqual(intersection / smaller, 0.15)
        self.assertEqual(
            len({window["passage_fingerprint"] for window in windows}), len(windows)
        )

    def test_adaptive_round_uses_only_closed_prior_metadata_and_returns_new_text_only(self) -> None:
        roles = ("opening", "dialogue", "action", "body_appearance", "ending")
        first = _sample(
            requested_roles=roles,
            max_windows=1,
            max_overlap_ratio=0.1,
        )
        self.assertEqual(len(first["ephemeral_windows"]), 1)

        second = _sample(
            requested_roles=roles,
            max_windows=1,
            max_overlap_ratio=0.1,
            prior_manifest=first["manifest"],
        )
        self.assertEqual(second["manifest"]["sampling_round"], 2)
        self.assertEqual(
            second["manifest"]["previous_manifest_fingerprint"],
            first["manifest"]["manifest_fingerprint"],
        )
        self.assertEqual(len(second["manifest"]["windows"]), 2)
        self.assertEqual(len(second["ephemeral_windows"]), 1)
        self.assertNotEqual(
            first["ephemeral_windows"][0]["passage_fingerprint"],
            second["ephemeral_windows"][0]["passage_fingerprint"],
        )
        validate_sampling_manifest(second["manifest"])

    def test_ai_planner_may_change_role_hints_between_bound_rounds(self) -> None:
        first = _sample(
            requested_roles=("opening",),
            max_windows=1,
            max_overlap_ratio=0.1,
        )
        second = _sample(
            requested_roles=("dialogue", "body_appearance"),
            max_windows=2,
            max_overlap_ratio=0.1,
            prior_manifest=first["manifest"],
        )
        self.assertEqual(
            second["manifest"]["previous_manifest_fingerprint"],
            first["manifest"]["manifest_fingerprint"],
        )
        self.assertEqual(
            second["manifest"]["selection_contract"]["requested_roles"],
            ["dialogue", "body_appearance"],
        )
        self.assertEqual(
            second["manifest"]["windows"][: len(first["manifest"]["windows"])],
            first["manifest"]["windows"],
        )
        validate_sampling_manifest(second["manifest"])

        chunks = [SYNTHETIC_STYLE_TEXT[index : index + 23] for index in range(0, len(SYNTHETIC_STYLE_TEXT), 23)]
        streamed_first = sample_style_chunks(
            chunks,
            requested_roles=("opening",),
            max_windows=1,
            target_window_chars=96,
            max_window_chars=180,
            max_overlap_ratio=0.1,
        )
        streamed_second = sample_style_chunks(
            chunks,
            requested_roles=("dialogue", "body_appearance"),
            max_windows=2,
            target_window_chars=96,
            max_window_chars=180,
            max_overlap_ratio=0.1,
            prior_manifest=streamed_first["manifest"],
        )
        self.assertEqual(streamed_second, second)

    def test_prior_role_hint_does_not_suppress_fresh_adaptive_sample(self) -> None:
        roles = ("opening",)
        first = _sample(requested_roles=roles, max_windows=1)
        second = _sample(
            requested_roles=roles,
            max_windows=1,
            prior_manifest=first["manifest"],
        )

        self.assertIn("opening", first["manifest"]["windows"][0]["candidate_roles"])
        self.assertEqual(len(second["ephemeral_windows"]), 1)
        self.assertEqual(len(second["manifest"]["windows"]), 2)
        self.assertNotEqual(
            first["ephemeral_windows"][0]["passage_fingerprint"],
            second["ephemeral_windows"][0]["passage_fingerprint"],
        )
        first_span = first["ephemeral_windows"][0]["span"]
        second_span = second["ephemeral_windows"][0]["span"]
        intersection = max(
            0,
            min(first_span["end"], second_span["end"])
            - max(first_span["start"], second_span["start"]),
        )
        smaller = min(
            first_span["end"] - first_span["start"],
            second_span["end"] - second_span["start"],
        )
        self.assertLessEqual(intersection / smaller, 0.2)

        chunks = [
            SYNTHETIC_STYLE_TEXT[index : index + 23]
            for index in range(0, len(SYNTHETIC_STYLE_TEXT), 23)
        ]
        streamed_first = sample_style_chunks(
            chunks,
            requested_roles=roles,
            max_windows=1,
            target_window_chars=96,
            max_window_chars=180,
        )
        streamed_second = sample_style_chunks(
            chunks,
            requested_roles=roles,
            max_windows=1,
            target_window_chars=96,
            max_window_chars=180,
            prior_manifest=streamed_first["manifest"],
        )
        self.assertEqual(streamed_first, first)
        self.assertEqual(streamed_second, second)
        validate_sampling_manifest(second["manifest"])

    def test_sparse_source_reports_role_gaps_without_quality_score(self) -> None:
        text = "第一章\n这是一个完全合成的说明句。\n尾声\n合成文本结束。"
        result = _sample(
            text,
            requested_roles=("dialogue", "body_appearance", "relationship"),
            max_windows=2,
            target_window_chars=32,
            max_window_chars=80,
        )
        manifest = result["manifest"]

        self.assertEqual(manifest["coverage"]["state"], "none")
        self.assertEqual(
            manifest["coverage"]["coverage_gaps"],
            ["dialogue", "body_appearance", "relationship"],
        )
        self.assertEqual(manifest["novelty"]["state"], "not_observed")
        self.assertEqual(manifest["saturation"]["state"], "role_candidates_exhausted")
        self.assertFalse(any("score" in key for key in _all_keys(manifest)))
        self.assertEqual(result["ephemeral_windows"], [])

    def test_window_budget_is_reported_separately_from_coverage(self) -> None:
        text = """第一章
开端只有环境：雨水落在街道。
***
“单独的对话窗口。”朋友说。
***
她转身冲出去，抓住门把手。
尾声
故事在这里结束。
"""
        result = _sample(
            text,
            requested_roles=("opening", "dialogue", "action", "ending"),
            max_windows=1,
            target_window_chars=40,
            max_window_chars=80,
            max_overlap_ratio=0.1,
        )
        manifest = result["manifest"]
        self.assertEqual(manifest["coverage"]["state"], "partial")
        self.assertEqual(manifest["saturation"]["state"], "window_budget_reached")
        self.assertTrue(manifest["saturation"]["remaining_gap_candidate_roles"])

    def test_long_single_paragraph_is_bounded_without_losing_span_binding(self) -> None:
        text = "第一章\n" + "她想起旧事，随后跑向窗边。" * 80
        result = _sample(
            text,
            requested_roles=("interiority", "action", "ending"),
            max_windows=6,
            target_window_chars=70,
            max_window_chars=100,
            max_overlap_ratio=0.1,
        )
        manifest = result["manifest"]

        self.assertGreater(manifest["segmentation"]["unit_count"], 1)
        self.assertEqual(manifest["segmentation"]["paragraph_count"], 1)
        for window in result["ephemeral_windows"]:
            self.assertLessEqual(len(window["text"]), 100)
            start, end = window["span"]["start"], window["span"]["end"]
            self.assertEqual(window["text"], text[start:end])

    def test_manifest_validator_rejects_unknown_fields_and_tampering(self) -> None:
        manifest = _sample()["manifest"]
        with_unknown = copy.deepcopy(manifest)
        with_unknown["raw_text"] = "must never fit the closed schema"
        with self.assertRaises(StyleSamplingError) as unknown:
            validate_sampling_manifest(with_unknown)
        self.assertEqual(unknown.exception.code, "manifest_not_closed")

        tampered = copy.deepcopy(manifest)
        tampered["coverage"]["state"] = "complete" if tampered["coverage"]["state"] != "complete" else "none"
        with self.assertRaises(StyleSamplingError):
            validate_sampling_manifest(tampered)

    def test_prior_manifest_must_rebind_to_exact_source_and_closed_contract(self) -> None:
        first = _sample(max_windows=1)
        changed_text = SYNTHETIC_STYLE_TEXT + "\n额外的合成句。"
        with self.assertRaises(StyleSamplingError) as mismatch:
            sample_style_windows(
                changed_text,
                source_fingerprint=fingerprint_source_text(changed_text),
                target_window_chars=96,
                max_window_chars=180,
                max_windows=1,
                prior_manifest=first["manifest"],
            )
        self.assertEqual(mismatch.exception.code, "prior_manifest_source_mismatch")

    def test_source_and_option_validation_fail_closed(self) -> None:
        source_hash = fingerprint_source_text("valid synthetic prose.")
        invalid_calls = (
            lambda: sample_style_windows(123, source_fingerprint=source_hash),
            lambda: sample_style_windows("", source_fingerprint=fingerprint_source_text("")),
            lambda: sample_style_windows("valid synthetic prose.", source_fingerprint="bad"),
            lambda: sample_style_windows(
                "valid synthetic prose.", source_fingerprint="sha256:" + "0" * 64
            ),
            lambda: sample_style_windows(
                "valid synthetic prose.",
                source_fingerprint=source_hash,
                requested_roles="opening",
            ),
            lambda: sample_style_windows(
                "valid synthetic prose.",
                source_fingerprint=source_hash,
                requested_roles=("opening", "opening"),
            ),
            lambda: sample_style_windows(
                "valid synthetic prose.",
                source_fingerprint=source_hash,
                requested_roles=("unknown",),
            ),
            lambda: sample_style_windows(
                "valid synthetic prose.", source_fingerprint=source_hash, max_windows=True
            ),
            lambda: sample_style_windows(
                "valid synthetic prose.",
                source_fingerprint=source_hash,
                target_window_chars=100,
                max_window_chars=80,
            ),
            lambda: sample_style_windows(
                "valid synthetic prose.", source_fingerprint=source_hash, max_overlap_ratio=1.0
            ),
        )
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises(StyleSamplingError):
                    call()

        with patch("corpus.style_sampling.MAX_SOURCE_CHARS", 8):
            text = "synthetic text longer than eight"
            with self.assertRaises(StyleSamplingError) as too_large:
                sample_style_windows(text, source_fingerprint=fingerprint_source_text(text))
        self.assertEqual(too_large.exception.code, "source_text_too_many_characters")

    def test_object_facade_matches_function_api(self) -> None:
        source_hash = StyleSampler.fingerprint(SYNTHETIC_STYLE_TEXT)
        via_object = StyleSampler.sample(
            SYNTHETIC_STYLE_TEXT,
            source_fingerprint=source_hash,
            target_window_chars=96,
            max_window_chars=180,
        )
        via_function = _sample()
        self.assertEqual(via_object, via_function)
        StyleSampler.validate_manifest(via_object["manifest"])

    def test_stream_sampler_is_chunk_boundary_independent_and_matches_small_source(self) -> None:
        options = {
            "requested_roles": STYLE_SAMPLE_ROLES,
            "max_windows": 8,
            "target_window_chars": 96,
            "max_window_chars": 180,
            "max_overlap_ratio": 0.2,
        }
        in_memory = sample_style_windows(
            SYNTHETIC_STYLE_TEXT,
            source_fingerprint=fingerprint_source_text(SYNTHETIC_STYLE_TEXT),
            **options,
        )
        streamed = sample_style_chunks(
            [SYNTHETIC_STYLE_TEXT[index : index + 17] for index in range(0, len(SYNTHETIC_STYLE_TEXT), 17)],
            **options,
        )
        self.assertEqual(streamed, in_memory)
        rebound = materialize_style_chunk_span(
            [SYNTHETIC_STYLE_TEXT[:33], SYNTHETIC_STYLE_TEXT[33:]],
            source_fingerprint=streamed["manifest"]["source_binding"]["source_fingerprint"],
            start=streamed["manifest"]["windows"][0]["span"]["start"],
            end=streamed["manifest"]["windows"][0]["span"]["end"],
            passage_fingerprint=streamed["manifest"]["windows"][0]["passage_fingerprint"],
        )
        self.assertEqual(
            fingerprint_source_text(rebound["passage"]),
            rebound["passage_fingerprint"],
        )

    def test_stream_sampler_handles_over_eight_million_characters_with_bounded_heap(self) -> None:
        paragraph = (
            "“现在行动。”朋友说，她想起过去，随后转身跑过雨中的街道。"
            "镜中长发、眼眸与丰满身材仍清晰可见，彼此的信任改变了选择。"
            + "这是完全合成的节奏填充句。" * 54
        )
        block = "Chapter 1\n" + paragraph + "\n"
        repetitions = MAX_SOURCE_CHARS // len(block) + 2

        def chunks():
            for _ in range(repetitions):
                yield block

        tracemalloc.start()
        try:
            result = sample_style_chunks(
                chunks(), max_windows=6, max_window_chars=1_800
            )
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        manifest = result["manifest"]
        self.assertGreater(manifest["source_binding"]["unicode_chars"], MAX_SOURCE_CHARS)
        self.assertEqual(manifest["segmentation"]["chapter_count"], repetitions)
        self.assertEqual(manifest["segmentation"]["unit_count"], repetitions)
        self.assertLess(peak, 24 * 1024 * 1024)
        self.assertLessEqual(len(result["ephemeral_windows"]), 6)
        validate_sampling_manifest(manifest)

    def test_stream_sampler_rejects_unbounded_single_chunk_before_encoding(self) -> None:
        with self.assertRaises(StyleSamplingError) as caught:
            sample_style_chunks(["合" * (MAX_STREAM_CHUNK_CHARS + 1)])
        self.assertEqual(caught.exception.code, "source_chunk_too_many_characters")

    def test_window_hygiene_rejects_transport_boilerplate_and_selects_clean_fallback(self) -> None:
        text = """第一章
“污染对话。”朋友说。访问 https://fiction.invalid.example/read 获取下一页。
***
<script>window.location='bad';</script><div>章节内容正在手打</div>
***
“干净的合成对话。”朋友说，她转身跑向雨中的街道。
***
镜中的人留着长发，身材丰满，巨乳被宽外套遮住。
尾声
她们彼此信任，最后一起回家。
"""
        result = sample_style_windows(
            text,
            source_fingerprint=fingerprint_source_text(text),
            requested_roles=("dialogue", "body_appearance", "ending"),
            max_windows=4,
            target_window_chars=48,
            max_window_chars=140,
            candidate_filter=style_window_passes_hygiene,
        )
        passages = [window["text"] for window in result["ephemeral_windows"]]
        self.assertTrue(any("干净的合成对话" in passage for passage in passages))
        self.assertTrue(any("巨乳" in passage for passage in passages))
        self.assertTrue(all(style_window_hygiene_reason(passage) is None for passage in passages))
        self.assertNotIn("https://", "".join(passages))
        self.assertNotIn("<script", "".join(passages))


if __name__ == "__main__":
    unittest.main()
