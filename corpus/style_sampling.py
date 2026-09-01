#!/usr/bin/env python3
"""Ephemeral, structure-aware sampling for prose-style research.

The sampler accepts either a bounded in-memory ``str`` or a bounded iterable
of normalized text chunks.  The streaming path keeps full call-scoped prose
only in an anonymous temporary spool and returns the same two deliberately
separate projections:

* ``manifest`` is a closed, prose-free record that may be persisted; and
* ``ephemeral_windows`` contains the exact source slices for the current call
  and must not be persisted by this module's consumers.

The v1 ``role`` field is retained for API compatibility, but it carries only
a deterministic candidate-retrieval hint.  Surface words and punctuation may
nominate a window for semantic review; they are never a scene/style finding,
a quality score, or an adult-content classifier.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
import sqlite3
import tempfile
from bisect import bisect_right
from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, BinaryIO


STYLE_SAMPLING_RESULT_SCHEMA = "quillframe_style_sampling_result_v1"
STYLE_SAMPLING_MANIFEST_SCHEMA = "quillframe_style_sampling_manifest_v1"

STYLE_SAMPLE_ROLES = (
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
)

ROLE_LAYERS: dict[str, tuple[str, ...]] = {
    "boundary": ("opening", "transition", "ending"),
    "interaction": ("dialogue", "action", "relationship"),
    "reflection": ("interiority", "exposition"),
    "description": ("environment", "body_appearance"),
}
_ROLE_TO_LAYER = {
    role: layer for layer, roles in ROLE_LAYERS.items() for role in roles
}
_ROLE_HINT_BITS = {
    role: 1 << index for index, role in enumerate(STYLE_SAMPLE_ROLES)
}

DEFAULT_MAX_WINDOWS = 12
DEFAULT_MAX_WINDOW_CHARS = 1_800
DEFAULT_MAX_OVERLAP_RATIO = 0.35
MIN_WINDOW_CHARS = 32
MAX_WINDOW_CHARS = 4_000
MAX_WINDOWS = 64
MAX_SOURCE_CHARS = 8_000_000
MAX_SOURCE_BYTES = 32 * 1024 * 1024
# The in-memory API above deliberately retains its original limits.  A
# separate chunk-stream API may describe a larger source while keeping only
# bounded windows and source-free candidate metadata in memory.  These are
# protocol/input ceilings, not permission to materialize a whole source.
MAX_STREAM_SOURCE_CHARS = 32_000_000
MAX_STREAM_SOURCE_UTF8_BYTES = 128 * 1024 * 1024
MAX_STREAM_PROSE_UNITS = 2_000_000
MAX_STREAM_CHUNK_CHARS = 262_144
MAX_STREAM_CHUNK_UTF8_BYTES = 1 * 1024 * 1024

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_WINDOW_ID_RE = re.compile(r"^style-window-[0-9a-f]{24}$")

_CHAPTER_HEADING_RE = re.compile(
    r"^(?:"
    r"#{1,6}\s+\S.*|"
    r"第[0-9０-９零〇一二两兩三四五六七八九十百千万萬]+"
    r"(?:章|节|節|卷|回|部|篇|幕|集)(?:\s*.*)?|"
    r"(?:序章|楔子|引子|前言|终章|終章|尾声|尾聲|后记|後記|番外)(?:\s*.*)?|"
    r"(?:(?:chapter|chap(?:ter)?\.?|part|book|episode)\s+"
    r"(?:[0-9]{1,5}|[ivxlcdm]{1,12}|[a-z]+(?:-[a-z]+)*)(?:\s*[:.\-—]\s*.*|\s+.*)?)|"
    r"(?:prologue|epilogue)(?:\s*[:.\-—]\s*.*|\s+.*)?|"
    r"[0-9]{1,4}[.)：:]\s+\S.{0,100}"
    r")$",
    re.IGNORECASE,
)
_SCENE_SEPARATOR_RE = re.compile(
    r"^(?:(?:[*＊]\s*){3,}|(?:[-—–_=~]\s*){3,}|#{3,}|[◆◇※❖✦☙]{1,8})$"
)

_DIALOGUE_PAIR_RE = re.compile(
    r"“[^”\n]{1,}”|「[^」\n]{1,}」|『[^』\n]{1,}』|\"[^\"\n]{2,}\""
)
_DIALOGUE_LINE_RE = re.compile(r"(?m)^\s*(?:[—-]\s+|[“「『\"])")
_DECLARATIVE_PUNCTUATION_RE = re.compile(r"[。！？.!?](?:\s|$)")

_ROLE_SIGNAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "action": re.compile(
        r"(?:冲向|冲进|冲出|奔跑|跑去|追赶|逃开|抓住|推开|拉住|拔出|"
        r"撞上|砍下|踢向|扑向|转身|轉身|抬手|挥动|揮動|开枪|開槍|"
        r"slam(?:med|s)?|rush(?:ed|es)?|run|ran|grab(?:bed|s)?|push(?:ed|es)?|"
        r"pull(?:ed|s)?|strike|struck|hit|kick(?:ed|s)?|lunge(?:d|s)?|"
        r"turn(?:ed|s)?|chase(?:d|s)?|flee|fled)",
        re.IGNORECASE,
    ),
    "interiority": re.compile(
        r"(?:心里|心中|念头|想到|想起|觉得|覺得|意识到|意識到|记得|記得|"
        r"希望|害怕|犹豫|猶豫|明白|不由得|wonder(?:ed|s)?|thought|felt|"
        r"realiz(?:ed|es)|remember(?:ed|s)?|hop(?:ed|es)|fear(?:ed|s)?|"
        r"believ(?:ed|es)|knew|inside)",
        re.IGNORECASE,
    ),
    "exposition": re.compile(
        r"(?:曾经|曾經|过去|過去|多年前|原来|原來|因为|因為|历史|歷史|"
        r"一直以来|一直以來|事实上|事實上|通常|意味着|意味著|那时候|那時候|"
        r"for years|used to|because|history|had once|in those days|"
        r"the reason|was known|meant that)",
        re.IGNORECASE,
    ),
    "environment": re.compile(
        r"(?:天空|雨声|雨水|风声|風吹|风吹|雪地|阳光|陽光|月光|街道|"
        r"房间|房間|山谷|河面|树林|樹林|空气|空氣|气味|氣味|温度|溫度|"
        r"sunlight|moonlight|rain|wind|snow|sky|street|room|forest|river|"
        r"air|scent|shadow|temperature)",
        re.IGNORECASE,
    ),
    "body_appearance": re.compile(
        r"(?:脸庞|臉龐|面容|容貌|外貌|眼睛|眼眸|眉眼|头发|頭髮|长发|長髮|"
        r"短发|短髮|发丝|髮絲|嘴唇|肩膀|胸口|胸部|乳房|巨乳|腰身|腰肢|"
        r"臀部|双腿|雙腿|皮肤|皮膚|身材|高挑|瘦削|丰满|豐滿|"
        r"breasts?|chest|waist|hips?|legs?|skin|hair|eyes?|face|lips?|"
        r"shoulders?|body|figure|tall|slender)",
        re.IGNORECASE,
    ),
    "relationship": re.compile(
        r"(?:朋友|母亲|母親|父亲|父親|妈妈|媽媽|爸爸|兄弟|姐妹|爱人|愛人|"
        r"恋人|戀人|丈夫|妻子|同伴|敌人|敵人|信任|背叛|彼此|我们之间|我們之間|"
        r"friends?|mother|father|brother|sister|lover|husband|wife|partner|"
        r"trust|betray|between them|each other)",
        re.IGNORECASE,
    ),
    "transition": re.compile(
        r"(?:后来|後來|随后|隨後|与此同时|與此同時|第二天|次日|转眼|轉眼|"
        r"不久后|不久後|片刻后|片刻後|另一边|另一邊|多年后|多年後|当天晚上|當天晚上|"
        r"the next (?:day|morning|night)|later|meanwhile|elsewhere|afterward|"
        r"hours later|years later|that evening)",
        re.IGNORECASE,
    ),
}

# Source-host boilerplate is not prose-style evidence.  These expressions are
# intentionally generic: they detect transport/navigation markup rather than
# a particular private site, title, or collection.  A hit rejects the whole
# candidate window; the sampler never edits source text into a synthetic
# replacement.
_WINDOW_HYGIENE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "url_or_domain",
        re.compile(
            r"(?:https?://|ftp://|www\.)\S+|"
            r"(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\.)+"
            r"(?:com|net|org|cn|io|co|me|tv|cc|info|xyz)(?:[/:?#]\S*)?",
            re.IGNORECASE,
        ),
    ),
    (
        "html_or_script",
        re.compile(
            r"</?(?:html|head|body|script|style|iframe|div|span|p|br|a|img|"
            r"meta|link|table|tr|td|form|input)\b[^>]*>|"
            r"(?:javascript|data):[a-z0-9/+.-]+[,;]",
            re.IGNORECASE,
        ),
    ),
    (
        "distribution_or_navigation_boilerplate",
        re.compile(
            r"(?:本(?:书|文|章节).{0,24}(?:整理|校对|上传|转载|下载)|"
            r"仅供.{0,20}(?:学习|交流|试阅)|请勿.{0,20}(?:传播|商用|转载)|"
            r"(?:最新|备用网址|官方)网址|手机用户请|点击(?:下一页|加入书签|收藏)|"
            r"章节内容正在(?:手打|更新)|(?:txt|epub)\s*(?:全集)?下载|"
            r"更多精彩.{0,16}(?:访问|搜索|尽在)|"
            r"download(?:ed)?\s+(?:this|the)\s+(?:book|text)\s+from|"
            r"visit\s+(?:our|the)\s+(?:website|site)\s+(?:at|for)|"
            r"(?:next|previous)\s+(?:chapter|page)\s*[|>»])",
            re.IGNORECASE,
        ),
    ),
)


class StyleSamplingError(ValueError):
    """Typed validation or binding failure raised by the style sampler."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class _Atom:
    start: int
    end: int
    chapter_ordinal: int
    scene_ordinal: int
    paragraph_ordinal: int
    atom_ordinal: int
    candidate_hint_mask: int


@dataclass(frozen=True)
class _Candidate:
    start: int
    end: int
    chapter_ordinal: int
    scene_ordinal: int
    paragraph_start_ordinal: int
    paragraph_end_ordinal: int
    candidate_roles: tuple[str, ...]
    passage_fingerprint: str


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StyleSamplingError("value_not_canonical_json") from exc


def _fingerprint_value(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def fingerprint_source_text(text: str) -> str:
    """Return the exact UTF-8 fingerprint used to bind an ephemeral source."""

    if not isinstance(text, str):
        raise StyleSamplingError("source_text_must_be_string")
    try:
        raw = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise StyleSamplingError("source_text_not_utf8_encodable") from exc
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def style_window_hygiene_reason(text: str) -> str | None:
    """Return a generic boilerplate reason, or ``None`` for an eligible window.

    This is a deterministic transport-hygiene boundary only.  It does not
    judge literary quality, content profile, anatomy/appearance language, or
    whether a passage is adult content.
    """

    if not isinstance(text, str):
        raise StyleSamplingError("window_hygiene_text_must_be_string")
    for reason, pattern in _WINDOW_HYGIENE_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def style_window_passes_hygiene(text: str) -> bool:
    """Return whether *text* is free of generic host/markup boilerplate."""

    return style_window_hygiene_reason(text) is None


def _require_int(value: Any, code: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StyleSamplingError(code)
    if value < minimum or value > maximum:
        raise StyleSamplingError(code)
    return value


def _validate_source(text: Any, source_fingerprint: Any) -> tuple[str, int]:
    if not isinstance(text, str):
        raise StyleSamplingError("source_text_must_be_string")
    if not text.strip():
        raise StyleSamplingError("source_text_empty")
    if "\x00" in text:
        raise StyleSamplingError("source_text_contains_nul")
    if len(text) > MAX_SOURCE_CHARS:
        raise StyleSamplingError("source_text_too_many_characters")
    try:
        source_bytes = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise StyleSamplingError("source_text_not_utf8_encodable") from exc
    if source_bytes > MAX_SOURCE_BYTES:
        raise StyleSamplingError("source_text_too_many_bytes")
    if not isinstance(source_fingerprint, str) or not _HASH_RE.fullmatch(
        source_fingerprint
    ):
        raise StyleSamplingError("invalid_source_fingerprint")
    actual = fingerprint_source_text(text)
    if actual != source_fingerprint:
        raise StyleSamplingError("source_fingerprint_mismatch")
    return actual, source_bytes


def _validate_requested_roles(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise StyleSamplingError("requested_roles_must_be_sequence")
    roles = tuple(value)
    if not roles:
        raise StyleSamplingError("requested_roles_empty")
    if any(not isinstance(role, str) or role not in STYLE_SAMPLE_ROLES for role in roles):
        raise StyleSamplingError("requested_role_unknown")
    if len(set(roles)) != len(roles):
        raise StyleSamplingError("requested_roles_duplicate")
    return roles


def _trimmed_line_span(raw_line: str, offset: int) -> tuple[int, int, str]:
    line = raw_line.rstrip("\r\n")
    left = len(line) - len(line.lstrip())
    right = len(line.rstrip())
    return offset + left, offset + right, line[left:right]


def _choose_chunk_break(text: str, start: int, hard_end: int) -> int:
    lower = start + max(1, (hard_end - start) // 2)
    region = text[lower:hard_end]
    sentence_breaks = list(
        re.finditer(r"(?:[。！？；]|[.!?;](?:\s+|$))", region)
    )
    if sentence_breaks:
        return lower + sentence_breaks[-1].end()
    whitespace = [match.end() for match in re.finditer(r"\s+", region)]
    if whitespace:
        return lower + whitespace[-1]
    return hard_end


def _split_long_span(
    text: str,
    *,
    start: int,
    end: int,
    max_window_chars: int,
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start
    while end - cursor > max_window_chars:
        hard_end = cursor + max_window_chars
        cut = _choose_chunk_break(text, cursor, hard_end)
        trimmed_end = cut
        while trimmed_end > cursor and text[trimmed_end - 1].isspace():
            trimmed_end -= 1
        if trimmed_end <= cursor:
            trimmed_end = hard_end
            cut = hard_end
        spans.append((cursor, trimmed_end))
        cursor = cut
        while cursor < end and text[cursor].isspace():
            cursor += 1
    if cursor < end:
        spans.append((cursor, end))
    return spans


def _segment_source(
    text: str, *, max_window_chars: int
) -> tuple[list[_Atom], dict[str, int]]:
    atoms: list[_Atom] = []
    offset = 0
    chapter_ordinal = 1
    scene_ordinal = 1
    paragraph_ordinal = 0
    atom_ordinal = 0
    heading_count = 0
    scene_separator_count = 0
    prose_seen_anywhere = False
    prose_seen_in_chapter = False
    prose_seen_in_scene = False

    for raw_line in text.splitlines(keepends=True):
        line_start, line_end, stripped = _trimmed_line_span(raw_line, offset)
        offset += len(raw_line)
        if not stripped:
            continue
        if _CHAPTER_HEADING_RE.fullmatch(stripped):
            heading_count += 1
            if prose_seen_in_chapter:
                chapter_ordinal += 1
            elif not prose_seen_anywhere:
                chapter_ordinal = 1
            scene_ordinal = 1
            prose_seen_in_chapter = False
            prose_seen_in_scene = False
            continue
        if _SCENE_SEPARATOR_RE.fullmatch(stripped):
            scene_separator_count += 1
            if prose_seen_in_scene:
                scene_ordinal += 1
            prose_seen_in_scene = False
            continue

        paragraph_ordinal += 1
        for chunk_start, chunk_end in _split_long_span(
            text,
            start=line_start,
            end=line_end,
            max_window_chars=max_window_chars,
        ):
            atom_ordinal += 1
            atoms.append(
                _Atom(
                    start=chunk_start,
                    end=chunk_end,
                    chapter_ordinal=chapter_ordinal,
                    scene_ordinal=scene_ordinal,
                    paragraph_ordinal=paragraph_ordinal,
                    atom_ordinal=atom_ordinal,
                    candidate_hint_mask=_surface_candidate_hint_mask(
                        text[chunk_start:chunk_end]
                    ),
                )
            )
        prose_seen_anywhere = True
        prose_seen_in_chapter = True
        prose_seen_in_scene = True

    if not atoms:
        raise StyleSamplingError("source_has_no_prose_units")

    chapter_count = len({atom.chapter_ordinal for atom in atoms})
    scene_count = len(
        {(atom.chapter_ordinal, atom.scene_ordinal) for atom in atoms}
    )
    return atoms, {
        "chapter_count": chapter_count,
        "scene_count": scene_count,
        "paragraph_count": paragraph_ordinal,
        "unit_count": len(atoms),
        "chapter_heading_count": heading_count,
        "scene_separator_count": scene_separator_count,
    }


def _surface_candidate_hint_mask(source_slice: str) -> int:
    """Index cheap retrieval hints once for one structural prose atom.

    ``search`` deliberately stops at the first hit.  Frequency is not a
    quality signal, and repeating a keyword must not make a passage look more
    semantically authoritative.  Candidate spans aggregate these precomputed
    bits instead of rescanning their text once per role.
    """

    hint_mask = 0
    if _DIALOGUE_PAIR_RE.search(source_slice) or _DIALOGUE_LINE_RE.search(
        source_slice
    ):
        hint_mask |= _ROLE_HINT_BITS["dialogue"]

    for role, pattern in _ROLE_SIGNAL_PATTERNS.items():
        if pattern.search(source_slice):
            hint_mask |= _ROLE_HINT_BITS[role]

    # A longer declarative unit may be retrieved for semantic exposition
    # review.  Punctuation remains only a cheap fallback hint.
    if not hint_mask & _ROLE_HINT_BITS["dialogue"] and len(source_slice.strip()) >= 48:
        if _DECLARATIVE_PUNCTUATION_RE.search(source_slice):
            hint_mask |= _ROLE_HINT_BITS["exposition"]
    return hint_mask


def _span_candidate_hint_mask(
    *, first_index: int, last_seen_by_role: Sequence[int]
) -> int:
    """Return roles seen at or after ``first_index`` in a bounded span."""

    return sum(
        _ROLE_HINT_BITS[role]
        for role, last_seen in zip(STYLE_SAMPLE_ROLES, last_seen_by_role)
        if last_seen >= first_index
    )


def _candidate_roles_from_mask(hint_mask: int) -> tuple[str, ...]:
    return tuple(
        role for role in STYLE_SAMPLE_ROLES if hint_mask & _ROLE_HINT_BITS[role]
    )


def _candidate_from_span(
    text: str,
    atoms: list[_Atom],
    first_index: int,
    last_index: int,
    *,
    scene_first: Mapping[tuple[int, int], int],
    scene_last: Mapping[tuple[int, int], int],
    chapter_first: Mapping[int, int],
    chapter_last: Mapping[int, int],
    last_seen_hints: Sequence[Sequence[int]],
    candidate_filter: Callable[[str], bool] | None = None,
) -> _Candidate | None:
    first = atoms[first_index]
    last = atoms[last_index]
    start, end = first.start, last.end
    source_slice = text[start:end]
    if candidate_filter is not None and not candidate_filter(source_slice):
        return None
    hint_mask = _span_candidate_hint_mask(
        first_index=first_index,
        last_seen_by_role=last_seen_hints[last_index],
    )
    scene_key = (first.chapter_ordinal, first.scene_ordinal)

    if first_index == 0:
        hint_mask |= _ROLE_HINT_BITS["opening"]
    elif first_index == chapter_first[first.chapter_ordinal]:
        hint_mask |= _ROLE_HINT_BITS["opening"] | _ROLE_HINT_BITS["transition"]
    elif first_index == scene_first[scene_key]:
        hint_mask |= _ROLE_HINT_BITS["opening"] | _ROLE_HINT_BITS["transition"]

    if last_index == len(atoms) - 1:
        hint_mask |= _ROLE_HINT_BITS["ending"]
    elif last_index == chapter_last[last.chapter_ordinal]:
        hint_mask |= _ROLE_HINT_BITS["ending"]
    elif last_index == scene_last[(last.chapter_ordinal, last.scene_ordinal)]:
        hint_mask |= _ROLE_HINT_BITS["ending"]

    if not hint_mask:
        hint_mask = _ROLE_HINT_BITS["exposition"]
    roles = _candidate_roles_from_mask(hint_mask)
    return _Candidate(
        start=start,
        end=end,
        chapter_ordinal=first.chapter_ordinal,
        scene_ordinal=first.scene_ordinal,
        paragraph_start_ordinal=first.paragraph_ordinal,
        paragraph_end_ordinal=last.paragraph_ordinal,
        candidate_roles=roles,
        passage_fingerprint=fingerprint_source_text(source_slice),
    )


def _build_candidates(
    text: str,
    atoms: list[_Atom],
    *,
    target_window_chars: int,
    max_window_chars: int,
    candidate_filter: Callable[[str], bool] | None = None,
) -> tuple[list[_Candidate], int]:
    scene_first: dict[tuple[int, int], int] = {}
    scene_last: dict[tuple[int, int], int] = {}
    chapter_first: dict[int, int] = {}
    chapter_last: dict[int, int] = {}
    for index, atom in enumerate(atoms):
        scene_key = (atom.chapter_ordinal, atom.scene_ordinal)
        scene_first.setdefault(scene_key, index)
        scene_last[scene_key] = index
        chapter_first.setdefault(atom.chapter_ordinal, index)
        chapter_last[atom.chapter_ordinal] = index

    last_seen = [-1] * len(STYLE_SAMPLE_ROLES)
    last_seen_hints: list[tuple[int, ...]] = []
    for index, atom in enumerate(atoms):
        for role_index, role in enumerate(STYLE_SAMPLE_ROLES):
            if atom.candidate_hint_mask & _ROLE_HINT_BITS[role]:
                last_seen[role_index] = index
        last_seen_hints.append(tuple(last_seen))

    raw_spans: list[tuple[int, int]] = []
    for index, atom in enumerate(atoms):
        scene_key = (atom.chapter_ordinal, atom.scene_ordinal)

        forward = index
        while forward + 1 < len(atoms):
            next_atom = atoms[forward + 1]
            if (next_atom.chapter_ordinal, next_atom.scene_ordinal) != scene_key:
                break
            if next_atom.end - atom.start > max_window_chars:
                break
            if atoms[forward].end - atom.start >= target_window_chars:
                break
            forward += 1
        raw_spans.append((index, forward))

        backward = index
        while backward - 1 >= 0:
            previous_atom = atoms[backward - 1]
            if (previous_atom.chapter_ordinal, previous_atom.scene_ordinal) != scene_key:
                break
            if atom.end - previous_atom.start > max_window_chars:
                break
            if atom.end - atoms[backward].start >= target_window_chars:
                break
            backward -= 1
        raw_spans.append((backward, index))

    unique_spans = sorted(set(raw_spans), key=lambda span: (span[0], span[1]))
    candidates = [
        candidate
        for first_index, last_index in unique_spans
        if (
            candidate := _candidate_from_span(
            text,
            atoms,
            first_index,
            last_index,
            scene_first=scene_first,
            scene_last=scene_last,
                chapter_first=chapter_first,
                chapter_last=chapter_last,
                last_seen_hints=last_seen_hints,
                candidate_filter=candidate_filter,
            )
        ) is not None
    ]
    return candidates, len(raw_spans) - len(unique_spans)


def _overlap_ppm(left_start: int, left_end: int, right_start: int, right_end: int) -> int:
    intersection = max(0, min(left_end, right_end) - max(left_start, right_start))
    if intersection == 0:
        return 0
    denominator = min(left_end - left_start, right_end - right_start)
    return intersection * 1_000_000 // max(1, denominator)


def _candidate_is_novel(
    candidate: _Candidate,
    *,
    used_hashes: set[str],
    used_spans: Sequence[tuple[int, int]],
    max_overlap_ppm: int,
) -> bool:
    if candidate.passage_fingerprint in used_hashes:
        return False
    return all(
        _overlap_ppm(candidate.start, candidate.end, start, end) <= max_overlap_ppm
        for start, end in used_spans
    )


def _window_id_from_parts(
    source_fingerprint: str,
    *,
    start: int,
    end: int,
    passage_fingerprint: str,
) -> str:
    digest = hashlib.sha256(
        (
            f"{source_fingerprint}:{start}:{end}:"
            f"{passage_fingerprint}"
        ).encode("ascii")
    ).hexdigest()
    return "style-window-" + digest[:24]


def _window_id(source_fingerprint: str, candidate: _Candidate) -> str:
    return _window_id_from_parts(
        source_fingerprint,
        start=candidate.start,
        end=candidate.end,
        passage_fingerprint=candidate.passage_fingerprint,
    )


def _window_record(
    source_fingerprint: str, candidate: _Candidate, primary_role: str
) -> dict[str, Any]:
    layers = tuple(
        layer
        for layer in ROLE_LAYERS
        if any(_ROLE_TO_LAYER[role] == layer for role in candidate.candidate_roles)
    )
    return {
        "window_id": _window_id(source_fingerprint, candidate),
        "span": {"start": candidate.start, "end": candidate.end},
        "role": primary_role,
        "candidate_roles": list(candidate.candidate_roles),
        "functional_layers": list(layers),
        "passage_fingerprint": candidate.passage_fingerprint,
        "unicode_chars": candidate.end - candidate.start,
        "chapter_ordinal": candidate.chapter_ordinal,
        "scene_ordinal": candidate.scene_ordinal,
        "paragraph_start_ordinal": candidate.paragraph_start_ordinal,
        "paragraph_end_ordinal": candidate.paragraph_end_ordinal,
    }


def _rank_candidate(
    candidate: _Candidate,
    *,
    role: str,
    uncovered_roles: set[str],
    used_chapters: set[int],
    used_scenes: set[tuple[int, int]],
    target_window_chars: int,
) -> tuple[int, int, int, int, int, int, str]:
    # Requested-role membership was already established by the caller.  Rank
    # only for structural position, retrieval breadth, and diversity; keyword
    # frequency is intentionally absent.  Opening/ending keep their literal
    # edge meaning instead of being displaced by a denser surface-hint window.
    structural_position = (
        -candidate.start
        if role == "opening"
        else (candidate.end if role == "ending" else 0)
    )
    return (
        structural_position,
        len(uncovered_roles.intersection(candidate.candidate_roles)),
        int(candidate.chapter_ordinal not in used_chapters),
        int((candidate.chapter_ordinal, candidate.scene_ordinal) not in used_scenes),
        -abs((candidate.end - candidate.start) - target_window_chars),
        -candidate.start,
        candidate.passage_fingerprint,
    )


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


_MANIFEST_KEYS = {
    "schema",
    "sampling_round",
    "previous_manifest_fingerprint",
    "source_binding",
    "segmentation",
    "selection_contract",
    "role_assignment",
    "persistence_boundary",
    "windows",
    "current_window_ids",
    "coverage",
    "functional_layers",
    "novelty",
    "saturation",
    "manifest_fingerprint",
}
_SOURCE_BINDING_KEYS = {"source_fingerprint", "unicode_chars", "utf8_bytes"}
_SEGMENTATION_KEYS = {
    "chapter_count",
    "scene_count",
    "paragraph_count",
    "unit_count",
    "chapter_heading_count",
    "scene_separator_count",
    "chapter_boundary_mode",
    "scene_boundary_mode",
    "paragraph_boundary_mode",
}
_SELECTION_KEYS = {
    "requested_roles",
    "max_windows_per_call",
    "target_window_chars",
    "max_window_chars",
    "max_overlap_ppm",
    "deterministic",
    "overlap_suppression",
}
_ROLE_ASSIGNMENT_KEYS = {
    "state",
    "method",
    "keywords_are_candidates_only",
    "semantic_literary_judgment_performed",
    "adult_content_classification_performed",
}
_CANDIDATE_HINT_ASSIGNMENT = {
    "state": "candidate_hint_only",
    "method": "structural_positions_and_precomputed_candidate_hints",
    "keywords_are_candidates_only": True,
    "semantic_literary_judgment_performed": False,
    "adult_content_classification_performed": False,
}
# Manifests emitted before candidate hints were precomputed remain replayable.
# The legacy declaration has the same no-semantic-judgment boundary.
_LEGACY_CANDIDATE_ASSIGNMENT = {
    "state": "candidate_only",
    "method": "structural_boundaries_and_surface_signals",
    "keywords_are_candidates_only": True,
    "semantic_literary_judgment_performed": False,
    "adult_content_classification_performed": False,
}
_PERSISTENCE_KEYS = {"manifest_contains_prose", "ephemeral_windows_persistable"}
_WINDOW_KEYS = {
    "window_id",
    "span",
    "role",
    "candidate_roles",
    "functional_layers",
    "passage_fingerprint",
    "unicode_chars",
    "chapter_ordinal",
    "scene_ordinal",
    "paragraph_start_ordinal",
    "paragraph_end_ordinal",
}
_SPAN_KEYS = {"start", "end"}
_COVERAGE_KEYS = {
    "state",
    "requested_roles",
    "covered_roles",
    "coverage_gaps",
    "gap_reasons",
}
_GAP_REASON_KEYS = {"role", "reason"}
_LAYER_KEYS = {"layer", "requested_roles", "covered_roles", "coverage_gaps", "state"}
_NOVELTY_KEYS = {
    "state",
    "cumulative_window_count",
    "current_window_count",
    "unique_window_hash_count",
    "distinct_chapter_count",
    "distinct_scene_count",
    "duplicate_candidate_hashes",
    "duplicate_candidate_spans",
}
_SATURATION_KEYS = {
    "state",
    "remaining_nonoverlapping_candidates",
    "remaining_gap_candidate_roles",
    "overlap_suppressed_candidates",
}


def _expect_mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StyleSamplingError(code)
    return value


def _expect_exact_keys(value: Mapping[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise StyleSamplingError(code)


def _expect_string_list(
    value: Any, allowed: set[str], code: str, *, unique: bool = True
) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise StyleSamplingError(code)
    if any(item not in allowed for item in value):
        raise StyleSamplingError(code)
    if unique and len(set(value)) != len(value):
        raise StyleSamplingError(code)
    return value


def validate_sampling_manifest(manifest: Mapping[str, Any]) -> None:
    """Fail closed unless *manifest* matches the prose-free schema exactly."""

    manifest = _expect_mapping(manifest, "manifest_must_be_mapping")
    _expect_exact_keys(manifest, _MANIFEST_KEYS, "manifest_not_closed")
    if manifest.get("schema") != STYLE_SAMPLING_MANIFEST_SCHEMA:
        raise StyleSamplingError("manifest_schema_invalid")
    sampling_round = _require_int(
        manifest.get("sampling_round"),
        "sampling_round_invalid",
        minimum=1,
        maximum=1_000_000,
    )
    previous = manifest.get("previous_manifest_fingerprint")
    if previous is not None and (not isinstance(previous, str) or not _HASH_RE.fullmatch(previous)):
        raise StyleSamplingError("previous_manifest_fingerprint_invalid")
    if (sampling_round == 1) != (previous is None):
        raise StyleSamplingError("sampling_round_chain_invalid")

    source = _expect_mapping(manifest.get("source_binding"), "source_binding_invalid")
    _expect_exact_keys(source, _SOURCE_BINDING_KEYS, "source_binding_not_closed")
    if not isinstance(source.get("source_fingerprint"), str) or not _HASH_RE.fullmatch(
        source["source_fingerprint"]
    ):
        raise StyleSamplingError("manifest_source_fingerprint_invalid")
    source_chars = _require_int(
        source.get("unicode_chars"),
        "manifest_source_chars_invalid",
        minimum=1,
        maximum=MAX_STREAM_SOURCE_CHARS,
    )
    _require_int(
        source.get("utf8_bytes"),
        "manifest_source_bytes_invalid",
        minimum=1,
        maximum=MAX_STREAM_SOURCE_UTF8_BYTES,
    )

    segmentation = _expect_mapping(manifest.get("segmentation"), "segmentation_invalid")
    _expect_exact_keys(segmentation, _SEGMENTATION_KEYS, "segmentation_not_closed")
    for key in (
        "chapter_count",
        "scene_count",
        "paragraph_count",
        "unit_count",
    ):
        _require_int(
            segmentation.get(key),
            f"{key}_invalid",
            minimum=1,
            maximum=MAX_STREAM_SOURCE_CHARS,
        )
    for key in ("chapter_heading_count", "scene_separator_count"):
        _require_int(
            segmentation.get(key),
            f"{key}_invalid",
            minimum=0,
            maximum=MAX_STREAM_SOURCE_CHARS,
        )
    if segmentation.get("chapter_boundary_mode") != "common_zh_en_headings":
        raise StyleSamplingError("chapter_boundary_mode_invalid")
    if segmentation.get("scene_boundary_mode") != "explicit_scene_markers":
        raise StyleSamplingError("scene_boundary_mode_invalid")
    if segmentation.get("paragraph_boundary_mode") != "logical_nonempty_lines":
        raise StyleSamplingError("paragraph_boundary_mode_invalid")

    selection = _expect_mapping(manifest.get("selection_contract"), "selection_contract_invalid")
    _expect_exact_keys(selection, _SELECTION_KEYS, "selection_contract_not_closed")
    requested = _expect_string_list(
        selection.get("requested_roles"), set(STYLE_SAMPLE_ROLES), "selection_roles_invalid"
    )
    if not requested:
        raise StyleSamplingError("selection_roles_invalid")
    _require_int(selection.get("max_windows_per_call"), "max_windows_invalid", minimum=1, maximum=MAX_WINDOWS)
    target_chars = _require_int(
        selection.get("target_window_chars"),
        "target_window_chars_invalid",
        minimum=MIN_WINDOW_CHARS,
        maximum=MAX_WINDOW_CHARS,
    )
    maximum_chars = _require_int(
        selection.get("max_window_chars"),
        "max_window_chars_invalid",
        minimum=MIN_WINDOW_CHARS,
        maximum=MAX_WINDOW_CHARS,
    )
    if target_chars > maximum_chars:
        raise StyleSamplingError("target_window_exceeds_maximum")
    _require_int(selection.get("max_overlap_ppm"), "max_overlap_invalid", minimum=0, maximum=999_999)
    if selection.get("deterministic") is not True or selection.get("overlap_suppression") is not True:
        raise StyleSamplingError("selection_guarantees_invalid")

    role_assignment = _expect_mapping(manifest.get("role_assignment"), "role_assignment_invalid")
    _expect_exact_keys(role_assignment, _ROLE_ASSIGNMENT_KEYS, "role_assignment_not_closed")
    if dict(role_assignment) not in (
        _CANDIDATE_HINT_ASSIGNMENT,
        _LEGACY_CANDIDATE_ASSIGNMENT,
    ):
        raise StyleSamplingError("role_assignment_boundary_invalid")

    persistence = _expect_mapping(manifest.get("persistence_boundary"), "persistence_boundary_invalid")
    _expect_exact_keys(persistence, _PERSISTENCE_KEYS, "persistence_boundary_not_closed")
    if dict(persistence) != {
        "manifest_contains_prose": False,
        "ephemeral_windows_persistable": False,
    }:
        raise StyleSamplingError("persistence_boundary_invalid")

    windows = manifest.get("windows")
    if not isinstance(windows, list):
        raise StyleSamplingError("manifest_windows_invalid")
    window_ids: list[str] = []
    hashes: list[str] = []
    derived_covered: set[str] = set()
    for window in windows:
        window = _expect_mapping(window, "manifest_window_invalid")
        _expect_exact_keys(window, _WINDOW_KEYS, "manifest_window_not_closed")
        window_id = window.get("window_id")
        if not isinstance(window_id, str) or not _WINDOW_ID_RE.fullmatch(window_id):
            raise StyleSamplingError("window_id_invalid")
        window_ids.append(window_id)
        span = _expect_mapping(window.get("span"), "window_span_invalid")
        _expect_exact_keys(span, _SPAN_KEYS, "window_span_not_closed")
        start = _require_int(span.get("start"), "window_start_invalid", minimum=0, maximum=source_chars)
        end = _require_int(span.get("end"), "window_end_invalid", minimum=1, maximum=source_chars)
        if start >= end:
            raise StyleSamplingError("window_span_invalid")
        if window.get("unicode_chars") != end - start or end - start > maximum_chars:
            raise StyleSamplingError("window_char_count_invalid")
        role = window.get("role")
        # Cumulative manifests retain windows selected for earlier AI
        # retrieval hints.  Their primary role stays bound to that historical
        # round even when the current round asks a narrower question.
        if role not in STYLE_SAMPLE_ROLES:
            raise StyleSamplingError("window_role_invalid")
        candidate_roles = _expect_string_list(
            window.get("candidate_roles"), set(STYLE_SAMPLE_ROLES), "candidate_roles_invalid"
        )
        if not candidate_roles or role not in candidate_roles:
            raise StyleSamplingError("candidate_roles_invalid")
        derived_covered.update(set(candidate_roles).intersection(requested))
        layers = _expect_string_list(
            window.get("functional_layers"), set(ROLE_LAYERS), "window_layers_invalid"
        )
        expected_layers = [
            layer
            for layer in ROLE_LAYERS
            if any(_ROLE_TO_LAYER[candidate_role] == layer for candidate_role in candidate_roles)
        ]
        if layers != expected_layers:
            raise StyleSamplingError("window_layers_invalid")
        passage_hash = window.get("passage_fingerprint")
        if not isinstance(passage_hash, str) or not _HASH_RE.fullmatch(passage_hash):
            raise StyleSamplingError("passage_fingerprint_invalid")
        expected_window_id = _window_id_from_parts(
            source["source_fingerprint"],
            start=start,
            end=end,
            passage_fingerprint=passage_hash,
        )
        if window_id != expected_window_id:
            raise StyleSamplingError("window_id_binding_invalid")
        hashes.append(passage_hash)
        for key in (
            "chapter_ordinal",
            "scene_ordinal",
            "paragraph_start_ordinal",
            "paragraph_end_ordinal",
        ):
            _require_int(
                window.get(key),
                f"window_{key}_invalid",
                minimum=1,
                maximum=MAX_STREAM_SOURCE_CHARS,
            )
        if window["chapter_ordinal"] > segmentation["chapter_count"]:
            raise StyleSamplingError("window_chapter_ordinal_invalid")
        if window["scene_ordinal"] > segmentation["scene_count"]:
            raise StyleSamplingError("window_scene_ordinal_invalid")
        if window["paragraph_end_ordinal"] > segmentation["paragraph_count"]:
            raise StyleSamplingError("window_paragraph_ordinal_invalid")
        if window["paragraph_start_ordinal"] > window["paragraph_end_ordinal"]:
            raise StyleSamplingError("window_paragraph_span_invalid")
    if len(set(window_ids)) != len(window_ids) or len(set(hashes)) != len(hashes):
        raise StyleSamplingError("manifest_window_duplicate")

    current_ids = manifest.get("current_window_ids")
    if not isinstance(current_ids, list) or any(not isinstance(value, str) for value in current_ids):
        raise StyleSamplingError("current_window_ids_invalid")
    if len(set(current_ids)) != len(current_ids) or not set(current_ids).issubset(window_ids):
        raise StyleSamplingError("current_window_ids_invalid")
    current_id_set = set(current_ids)
    if any(
        window["window_id"] in current_id_set and window["role"] not in requested
        for window in windows
    ):
        raise StyleSamplingError("current_window_role_invalid")

    coverage = _expect_mapping(manifest.get("coverage"), "coverage_invalid")
    _expect_exact_keys(coverage, _COVERAGE_KEYS, "coverage_not_closed")
    coverage_requested = _expect_string_list(
        coverage.get("requested_roles"), set(STYLE_SAMPLE_ROLES), "coverage_roles_invalid"
    )
    covered = _expect_string_list(
        coverage.get("covered_roles"), set(STYLE_SAMPLE_ROLES), "covered_roles_invalid"
    )
    gaps = _expect_string_list(
        coverage.get("coverage_gaps"), set(STYLE_SAMPLE_ROLES), "coverage_gaps_invalid"
    )
    if coverage_requested != requested:
        raise StyleSamplingError("coverage_requested_roles_mismatch")
    expected_covered = [role for role in requested if role in derived_covered]
    expected_gaps = [role for role in requested if role not in derived_covered]
    if covered != expected_covered or gaps != expected_gaps:
        raise StyleSamplingError("coverage_projection_invalid")
    expected_coverage_state = "complete" if not gaps else ("partial" if covered else "none")
    if coverage.get("state") != expected_coverage_state:
        raise StyleSamplingError("coverage_state_invalid")
    gap_reasons = coverage.get("gap_reasons")
    if not isinstance(gap_reasons, list) or len(gap_reasons) != len(gaps):
        raise StyleSamplingError("gap_reasons_invalid")
    allowed_gap_reasons = {
        "no_candidate",
        "overlap_or_duplicate_suppressed",
        "window_budget_reached",
    }
    for expected_role, item in zip(gaps, gap_reasons):
        item = _expect_mapping(item, "gap_reason_invalid")
        _expect_exact_keys(item, _GAP_REASON_KEYS, "gap_reason_not_closed")
        if item.get("role") != expected_role or item.get("reason") not in allowed_gap_reasons:
            raise StyleSamplingError("gap_reason_invalid")

    layers = manifest.get("functional_layers")
    if not isinstance(layers, list) or len(layers) != len(ROLE_LAYERS):
        raise StyleSamplingError("functional_layers_invalid")
    for expected_layer, item in zip(ROLE_LAYERS, layers):
        item = _expect_mapping(item, "functional_layer_invalid")
        _expect_exact_keys(item, _LAYER_KEYS, "functional_layer_not_closed")
        if item.get("layer") != expected_layer:
            raise StyleSamplingError("functional_layer_invalid")
        layer_requested = [role for role in requested if role in ROLE_LAYERS[expected_layer]]
        layer_covered = [role for role in covered if role in ROLE_LAYERS[expected_layer]]
        layer_gaps = [role for role in gaps if role in ROLE_LAYERS[expected_layer]]
        if item.get("requested_roles") != layer_requested:
            raise StyleSamplingError("functional_layer_requested_invalid")
        if item.get("covered_roles") != layer_covered or item.get("coverage_gaps") != layer_gaps:
            raise StyleSamplingError("functional_layer_coverage_invalid")
        expected_state = "not_requested" if not layer_requested else (
            "complete" if not layer_gaps else ("partial" if layer_covered else "none")
        )
        if item.get("state") != expected_state:
            raise StyleSamplingError("functional_layer_state_invalid")

    novelty = _expect_mapping(manifest.get("novelty"), "novelty_invalid")
    _expect_exact_keys(novelty, _NOVELTY_KEYS, "novelty_not_closed")
    for key in _NOVELTY_KEYS - {"state"}:
        _require_int(
            novelty.get(key),
            f"novelty_{key}_invalid",
            minimum=0,
            maximum=MAX_STREAM_SOURCE_CHARS,
        )
    if novelty.get("cumulative_window_count") != len(windows):
        raise StyleSamplingError("novelty_window_count_invalid")
    if novelty.get("current_window_count") != len(current_ids):
        raise StyleSamplingError("novelty_current_count_invalid")
    if novelty.get("unique_window_hash_count") != len(set(hashes)):
        raise StyleSamplingError("novelty_hash_count_invalid")
    distinct_chapters = {window["chapter_ordinal"] for window in windows}
    distinct_scenes = {
        (window["chapter_ordinal"], window["scene_ordinal"])
        for window in windows
    }
    if novelty.get("distinct_chapter_count") != len(distinct_chapters):
        raise StyleSamplingError("novelty_chapter_count_invalid")
    if novelty.get("distinct_scene_count") != len(distinct_scenes):
        raise StyleSamplingError("novelty_scene_count_invalid")
    if not windows:
        expected_novelty_state = "not_observed"
    elif len(windows) == 1:
        expected_novelty_state = "single_window"
    elif len(distinct_chapters) > 1:
        expected_novelty_state = "multi_chapter"
    elif len(distinct_scenes) > 1:
        expected_novelty_state = "multi_scene"
    else:
        expected_novelty_state = "within_scene"
    if novelty.get("state") != expected_novelty_state:
        raise StyleSamplingError("novelty_state_invalid")

    saturation = _expect_mapping(manifest.get("saturation"), "saturation_invalid")
    _expect_exact_keys(saturation, _SATURATION_KEYS, "saturation_not_closed")
    if saturation.get("state") not in {
        "coverage_complete",
        "window_budget_reached",
        "role_candidates_exhausted",
    }:
        raise StyleSamplingError("saturation_state_invalid")
    for key in ("remaining_nonoverlapping_candidates", "overlap_suppressed_candidates"):
        _require_int(
            saturation.get(key),
            f"saturation_{key}_invalid",
            minimum=0,
            maximum=MAX_STREAM_SOURCE_CHARS,
        )
    remaining_gap_roles = _expect_string_list(
        saturation.get("remaining_gap_candidate_roles"),
        set(STYLE_SAMPLE_ROLES),
        "remaining_gap_candidate_roles_invalid",
    )
    if not set(remaining_gap_roles).issubset(gaps):
        raise StyleSamplingError("remaining_gap_candidate_roles_invalid")
    if not gaps and saturation.get("state") != "coverage_complete":
        raise StyleSamplingError("saturation_state_invalid")
    if gaps and saturation.get("state") == "coverage_complete":
        raise StyleSamplingError("saturation_state_invalid")
    if saturation.get("state") == "window_budget_reached" and not remaining_gap_roles:
        raise StyleSamplingError("saturation_state_invalid")

    manifest_hash = manifest.get("manifest_fingerprint")
    if not isinstance(manifest_hash, str) or not _HASH_RE.fullmatch(manifest_hash):
        raise StyleSamplingError("manifest_fingerprint_invalid")
    unsigned = dict(manifest)
    unsigned.pop("manifest_fingerprint")
    if _fingerprint_value(unsigned) != manifest_hash:
        raise StyleSamplingError("manifest_fingerprint_mismatch")


def _validate_prior_manifest_against_source(
    prior_manifest: Mapping[str, Any],
    *,
    text: str,
    source_fingerprint: str,
    requested_roles: tuple[str, ...],
    target_window_chars: int,
    max_window_chars: int,
    max_overlap_ppm: int,
) -> dict[str, Any]:
    validate_sampling_manifest(prior_manifest)
    prior = _copy_json(prior_manifest)
    if prior["source_binding"]["source_fingerprint"] != source_fingerprint:
        raise StyleSamplingError("prior_manifest_source_mismatch")
    if prior["source_binding"]["unicode_chars"] != len(text):
        raise StyleSamplingError("prior_manifest_source_size_mismatch")
    if prior["source_binding"]["utf8_bytes"] != len(text.encode("utf-8")):
        raise StyleSamplingError("prior_manifest_source_size_mismatch")
    selection = prior["selection_contract"]
    # A prior manifest binds the historical retrieval request that produced
    # its windows.  A later AI-planned round may legitimately ask for a
    # different, narrower evidence hint; the manifest fingerprint preserves
    # the old request while the new manifest records the current one.
    if selection["target_window_chars"] != target_window_chars:
        raise StyleSamplingError("prior_manifest_target_window_mismatch")
    if selection["max_window_chars"] != max_window_chars:
        raise StyleSamplingError("prior_manifest_max_window_mismatch")
    if selection["max_overlap_ppm"] != max_overlap_ppm:
        raise StyleSamplingError("prior_manifest_overlap_mismatch")
    for window in prior["windows"]:
        start = window["span"]["start"]
        end = window["span"]["end"]
        if fingerprint_source_text(text[start:end]) != window["passage_fingerprint"]:
            raise StyleSamplingError("prior_manifest_passage_binding_mismatch")
    return prior


def _adaptive_target(source_chars: int, max_windows: int, max_window_chars: int) -> int:
    evidence_slots = max(1, max_windows * 2)
    proposed = math.ceil(source_chars / evidence_slots)
    return min(max_window_chars, max(240, proposed, MIN_WINDOW_CHARS))


def sample_style_windows(
    text: str,
    *,
    source_fingerprint: str,
    requested_roles: Sequence[str] = STYLE_SAMPLE_ROLES,
    max_windows: int = DEFAULT_MAX_WINDOWS,
    target_window_chars: int | None = None,
    max_window_chars: int = DEFAULT_MAX_WINDOW_CHARS,
    max_overlap_ratio: float = DEFAULT_MAX_OVERLAP_RATIO,
    prior_manifest: Mapping[str, Any] | None = None,
    candidate_filter: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Select deterministic style-evidence candidates from ephemeral *text*.

    ``prior_manifest`` may be supplied for a later adaptive call.  Its closed
    window metadata is rebound to the current text before previous hashes and
    spans are used for novelty suppression.  Candidate-role hints from prior
    rounds do not satisfy the current retrieval request: each adaptive call
    attempts fresh role coverage while the returned manifest remains
    cumulative.  ``ephemeral_windows`` contains only newly selected source
    slices from this call.
    """

    source_fingerprint, source_bytes = _validate_source(text, source_fingerprint)
    roles = _validate_requested_roles(requested_roles)
    max_windows = _require_int(
        max_windows, "max_windows_invalid", minimum=1, maximum=MAX_WINDOWS
    )
    max_window_chars = _require_int(
        max_window_chars,
        "max_window_chars_invalid",
        minimum=MIN_WINDOW_CHARS,
        maximum=MAX_WINDOW_CHARS,
    )
    if target_window_chars is None:
        target_window_chars = _adaptive_target(
            len(text), max_windows, max_window_chars
        )
    else:
        target_window_chars = _require_int(
            target_window_chars,
            "target_window_chars_invalid",
            minimum=MIN_WINDOW_CHARS,
            maximum=MAX_WINDOW_CHARS,
        )
    if target_window_chars > max_window_chars:
        raise StyleSamplingError("target_window_exceeds_maximum")
    if (
        isinstance(max_overlap_ratio, bool)
        or not isinstance(max_overlap_ratio, (int, float))
        or not math.isfinite(float(max_overlap_ratio))
        or float(max_overlap_ratio) < 0
        or float(max_overlap_ratio) >= 1
    ):
        raise StyleSamplingError("max_overlap_ratio_invalid")
    max_overlap_ppm = int(float(max_overlap_ratio) * 1_000_000)
    if candidate_filter is not None and not callable(candidate_filter):
        raise StyleSamplingError("candidate_filter_invalid")

    atoms, segmentation_counts = _segment_source(
        text, max_window_chars=max_window_chars
    )
    candidates, duplicate_span_count = _build_candidates(
        text,
        atoms,
        target_window_chars=target_window_chars,
        max_window_chars=max_window_chars,
        candidate_filter=candidate_filter,
    )

    prior: dict[str, Any] | None = None
    if prior_manifest is not None:
        prior = _validate_prior_manifest_against_source(
            prior_manifest,
            text=text,
            source_fingerprint=source_fingerprint,
            requested_roles=roles,
            target_window_chars=target_window_chars,
            max_window_chars=max_window_chars,
            max_overlap_ppm=max_overlap_ppm,
        )

    prior_windows: list[dict[str, Any]] = (
        _copy_json(prior["windows"]) if prior is not None else []
    )
    used_hashes = {window["passage_fingerprint"] for window in prior_windows}
    used_spans = [
        (window["span"]["start"], window["span"]["end"])
        for window in prior_windows
    ]
    current_round_covered: set[str] = set()
    used_chapters = {window["chapter_ordinal"] for window in prior_windows}
    used_scenes = {
        (window["chapter_ordinal"], window["scene_ordinal"])
        for window in prior_windows
    }

    selected: list[tuple[_Candidate, str]] = []

    def eligible(candidate: _Candidate) -> bool:
        return _candidate_is_novel(
            candidate,
            used_hashes=used_hashes,
            used_spans=used_spans,
            max_overlap_ppm=max_overlap_ppm,
        )

    def add(candidate: _Candidate, primary_role: str) -> None:
        selected.append((candidate, primary_role))
        used_hashes.add(candidate.passage_fingerprint)
        used_spans.append((candidate.start, candidate.end))
        current_round_covered.update(
            set(candidate.candidate_roles).intersection(roles)
        )
        used_chapters.add(candidate.chapter_ordinal)
        used_scenes.add((candidate.chapter_ordinal, candidate.scene_ordinal))

    for role in roles:
        if role in current_round_covered or len(selected) >= max_windows:
            continue
        choices = [
            candidate
            for candidate in candidates
            if role in candidate.candidate_roles and eligible(candidate)
        ]
        if not choices:
            continue
        uncovered = set(roles) - current_round_covered
        best = max(
            choices,
            key=lambda candidate: _rank_candidate(
                candidate,
                role=role,
                uncovered_roles=uncovered,
                used_chapters=used_chapters,
                used_scenes=used_scenes,
                target_window_chars=target_window_chars,
            ),
        )
        add(best, role)

    if prior is not None and set(roles).issubset(current_round_covered):
        # A later adaptive round stops as soon as the requested role coverage
        # is complete; it never emits extra prose merely to fill a quota.
        desired_current_count = len(selected)
    else:
        desired_current_count = min(
            max_windows,
            max(1, min(len(roles), 6, math.ceil(math.sqrt(len(atoms))))),
        )
    while len(selected) < desired_current_count:
        choices = [
            candidate
            for candidate in candidates
            if set(candidate.candidate_roles).intersection(roles) and eligible(candidate)
        ]
        if not choices:
            break
        choices.sort(
            key=lambda candidate: (
                int(candidate.chapter_ordinal not in used_chapters),
                int((candidate.chapter_ordinal, candidate.scene_ordinal) not in used_scenes),
                len(set(candidate.candidate_roles).intersection(roles)),
                -abs((candidate.end - candidate.start) - target_window_chars),
                -candidate.start,
                candidate.passage_fingerprint,
            ),
            reverse=True,
        )
        best = choices[0]
        primary = next(role for role in roles if role in best.candidate_roles)
        add(best, primary)

    current_records = [
        _window_record(source_fingerprint, candidate, primary_role)
        for candidate, primary_role in selected
    ]
    all_windows = prior_windows + current_records
    all_windows.sort(
        key=lambda window: (
            window["span"]["start"],
            window["span"]["end"],
            window["window_id"],
        )
    )
    current_ids = [record["window_id"] for record in current_records]

    cumulative_covered = {
        role
        for window in all_windows
        for role in window["candidate_roles"]
        if role in roles
    }
    covered_roles = [role for role in roles if role in cumulative_covered]
    coverage_gaps = [role for role in roles if role not in cumulative_covered]

    remaining_candidates = [candidate for candidate in candidates if eligible(candidate)]
    remaining_gap_roles = [
        role
        for role in coverage_gaps
        if any(role in candidate.candidate_roles for candidate in remaining_candidates)
    ]
    candidate_roles_anywhere = {
        role for candidate in candidates for role in candidate.candidate_roles
    }
    gap_reasons = []
    for role in coverage_gaps:
        if role not in candidate_roles_anywhere:
            reason = "no_candidate"
        elif len(selected) >= max_windows and role in remaining_gap_roles:
            reason = "window_budget_reached"
        else:
            reason = "overlap_or_duplicate_suppressed"
        gap_reasons.append({"role": role, "reason": reason})

    if not coverage_gaps:
        coverage_state = "complete"
        saturation_state = "coverage_complete"
    elif len(selected) >= max_windows and remaining_gap_roles:
        coverage_state = "partial" if covered_roles else "none"
        saturation_state = "window_budget_reached"
    else:
        coverage_state = "partial" if covered_roles else "none"
        saturation_state = "role_candidates_exhausted"

    functional_layers = []
    for layer, layer_roles in ROLE_LAYERS.items():
        layer_requested = [role for role in roles if role in layer_roles]
        layer_covered = [role for role in covered_roles if role in layer_roles]
        layer_gaps = [role for role in coverage_gaps if role in layer_roles]
        layer_state = "not_requested" if not layer_requested else (
            "complete" if not layer_gaps else ("partial" if layer_covered else "none")
        )
        functional_layers.append(
            {
                "layer": layer,
                "requested_roles": layer_requested,
                "covered_roles": layer_covered,
                "coverage_gaps": layer_gaps,
                "state": layer_state,
            }
        )

    distinct_chapters = {window["chapter_ordinal"] for window in all_windows}
    distinct_scenes = {
        (window["chapter_ordinal"], window["scene_ordinal"])
        for window in all_windows
    }
    if not all_windows:
        novelty_state = "not_observed"
    elif len(all_windows) == 1:
        novelty_state = "single_window"
    elif len(distinct_chapters) > 1:
        novelty_state = "multi_chapter"
    elif len(distinct_scenes) > 1:
        novelty_state = "multi_scene"
    else:
        novelty_state = "within_scene"

    candidate_hash_counts: dict[str, int] = {}
    for candidate in candidates:
        candidate_hash_counts[candidate.passage_fingerprint] = (
            candidate_hash_counts.get(candidate.passage_fingerprint, 0) + 1
        )
    duplicate_hashes = sum(count - 1 for count in candidate_hash_counts.values() if count > 1)
    overlap_suppressed = sum(
        1
        for candidate in candidates
        if candidate.passage_fingerprint not in used_hashes
        and any(
            _overlap_ppm(candidate.start, candidate.end, start, end) > max_overlap_ppm
            for start, end in used_spans
        )
    )

    segmentation = {
        **segmentation_counts,
        "chapter_boundary_mode": "common_zh_en_headings",
        "scene_boundary_mode": "explicit_scene_markers",
        "paragraph_boundary_mode": "logical_nonempty_lines",
    }
    unsigned_manifest: dict[str, Any] = {
        "schema": STYLE_SAMPLING_MANIFEST_SCHEMA,
        "sampling_round": 1 if prior is None else prior["sampling_round"] + 1,
        "previous_manifest_fingerprint": None
        if prior is None
        else prior["manifest_fingerprint"],
        "source_binding": {
            "source_fingerprint": source_fingerprint,
            "unicode_chars": len(text),
            "utf8_bytes": source_bytes,
        },
        "segmentation": segmentation,
        "selection_contract": {
            "requested_roles": list(roles),
            "max_windows_per_call": max_windows,
            "target_window_chars": target_window_chars,
            "max_window_chars": max_window_chars,
            "max_overlap_ppm": max_overlap_ppm,
            "deterministic": True,
            "overlap_suppression": True,
        },
        "role_assignment": dict(_CANDIDATE_HINT_ASSIGNMENT),
        "persistence_boundary": {
            "manifest_contains_prose": False,
            "ephemeral_windows_persistable": False,
        },
        "windows": all_windows,
        "current_window_ids": current_ids,
        "coverage": {
            "state": coverage_state,
            "requested_roles": list(roles),
            "covered_roles": covered_roles,
            "coverage_gaps": coverage_gaps,
            "gap_reasons": gap_reasons,
        },
        "functional_layers": functional_layers,
        "novelty": {
            "state": novelty_state,
            "cumulative_window_count": len(all_windows),
            "current_window_count": len(current_records),
            "unique_window_hash_count": len(
                {window["passage_fingerprint"] for window in all_windows}
            ),
            "distinct_chapter_count": len(distinct_chapters),
            "distinct_scene_count": len(distinct_scenes),
            "duplicate_candidate_hashes": duplicate_hashes,
            "duplicate_candidate_spans": duplicate_span_count,
        },
        "saturation": {
            "state": saturation_state,
            "remaining_nonoverlapping_candidates": len(remaining_candidates),
            "remaining_gap_candidate_roles": remaining_gap_roles,
            "overlap_suppressed_candidates": overlap_suppressed,
        },
    }
    manifest = {
        **unsigned_manifest,
        "manifest_fingerprint": _fingerprint_value(unsigned_manifest),
    }
    validate_sampling_manifest(manifest)

    record_by_id = {record["window_id"]: record for record in current_records}
    ephemeral_windows = []
    for candidate, primary_role in selected:
        record = record_by_id[_window_id(source_fingerprint, candidate)]
        ephemeral_windows.append(
            {
                "window_id": record["window_id"],
                "source_fingerprint": source_fingerprint,
                "span": dict(record["span"]),
                "role": primary_role,
                "candidate_roles": list(record["candidate_roles"]),
                "passage_fingerprint": candidate.passage_fingerprint,
                "text": text[candidate.start : candidate.end],
                "persistence": "ephemeral_call_only",
            }
        )

    return {
        "schema": STYLE_SAMPLING_RESULT_SCHEMA,
        "manifest": manifest,
        "ephemeral_windows": ephemeral_windows,
    }


def _read_utf32_span(
    stream: BinaryIO, start: int, end: int
) -> str:
    """Read one character-addressed span from an anonymous UTF-32 spool."""

    stream.seek(start * 4)
    raw = stream.read((end - start) * 4)
    if len(raw) != (end - start) * 4:
        raise StyleSamplingError("stream_source_span_unavailable")
    try:
        return raw.decode("utf-32-le", errors="strict")
    except UnicodeDecodeError as exc:  # pragma: no cover - internal invariant
        raise StyleSamplingError("stream_source_spool_invalid") from exc


class _StreamAtomSpool:
    """Segment a normalized character stream with bounded line memory.

    Only source-free offsets and structural ordinals enter SQLite.  The
    character data itself lives in an anonymous ``TemporaryFile`` owned by the
    outer call and is destroyed before the result is returned.
    """

    def __init__(self, connection: sqlite3.Connection, *, max_window_chars: int) -> None:
        self.connection = connection
        self.max_window_chars = max_window_chars
        connection.execute(
            "CREATE TABLE atoms("
            "atom_ordinal INTEGER PRIMARY KEY,start_char INTEGER NOT NULL,end_char INTEGER NOT NULL,"
            "chapter_ordinal INTEGER NOT NULL,scene_ordinal INTEGER NOT NULL,"
            "paragraph_ordinal INTEGER NOT NULL,chapter_first INTEGER NOT NULL,"
            "scene_first INTEGER NOT NULL,chapter_last INTEGER NOT NULL DEFAULT 0,"
            "scene_last INTEGER NOT NULL DEFAULT 0,global_first INTEGER NOT NULL,"
            "global_last INTEGER NOT NULL DEFAULT 0,"
            "candidate_hint_mask INTEGER NOT NULL)"
        )
        self.offset = 0
        self.line_start = 0
        self.line_buffer: list[str] = []
        self.long_line = False
        self.paragraph_started = False
        self.chapter_ordinal = 1
        self.scene_ordinal = 1
        self.paragraph_ordinal = 0
        self.atom_ordinal = 0
        self.heading_count = 0
        self.separator_count = 0
        self.prose_anywhere = False
        self.prose_in_chapter = False
        self.prose_in_scene = False
        self.last_atom_ordinal: int | None = None

    def _mark_last(
        self, *, scene: bool = False, chapter: bool = False, global_: bool = False
    ) -> None:
        if self.last_atom_ordinal is None:
            return
        updates: list[str] = []
        if scene:
            updates.append("scene_last=1")
        if chapter:
            updates.append("chapter_last=1")
        if global_:
            updates.append("global_last=1")
        if updates:
            self.connection.execute(
                f"UPDATE atoms SET {','.join(updates)} WHERE atom_ordinal=?",
                (self.last_atom_ordinal,),
            )

    def _start_paragraph(self) -> None:
        if not self.paragraph_started:
            self.paragraph_ordinal += 1
            self.paragraph_started = True

    def _emit_atom(self, start: int, end: int, source_slice: str) -> None:
        if end <= start:
            return
        if len(source_slice) != end - start:  # pragma: no cover - spool invariant
            raise StyleSamplingError("stream_atom_span_invalid")
        self._start_paragraph()
        self.atom_ordinal += 1
        if self.atom_ordinal > MAX_STREAM_PROSE_UNITS:
            raise StyleSamplingError("stream_source_too_many_prose_units")
        self.connection.execute(
            "INSERT INTO atoms(atom_ordinal,start_char,end_char,chapter_ordinal,"
            "scene_ordinal,paragraph_ordinal,chapter_first,scene_first,global_first,"
            "candidate_hint_mask) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                self.atom_ordinal,
                start,
                end,
                self.chapter_ordinal,
                self.scene_ordinal,
                self.paragraph_ordinal,
                int(not self.prose_in_chapter),
                int(not self.prose_in_scene),
                int(not self.prose_anywhere),
                _surface_candidate_hint_mask(source_slice),
            ),
        )
        self.last_atom_ordinal = self.atom_ordinal
        self.prose_anywhere = True
        self.prose_in_chapter = True
        self.prose_in_scene = True

    def _flush_long_prefixes(self) -> None:
        while len(self.line_buffer) > self.max_window_chars:
            value = "".join(self.line_buffer)
            if not self.paragraph_started:
                left = len(value) - len(value.lstrip())
                if left:
                    self.line_start += left
                    value = value[left:]
                    self.line_buffer = list(value)
                    if len(value) <= self.max_window_chars:
                        return
            hard_end = self.max_window_chars
            cut = _choose_chunk_break(value, 0, hard_end)
            trimmed_end = cut
            while trimmed_end > 0 and value[trimmed_end - 1].isspace():
                trimmed_end -= 1
            if trimmed_end <= 0:
                trimmed_end = hard_end
                cut = hard_end
            self._emit_atom(
                self.line_start,
                self.line_start + trimmed_end,
                value[:trimmed_end],
            )
            drop = cut
            while drop < len(value) and value[drop].isspace():
                drop += 1
            self.line_start += drop
            self.line_buffer = list(value[drop:])

    def _finish_line(self) -> None:
        value = "".join(self.line_buffer)
        if self.long_line:
            right = len(value.rstrip())
            if right:
                self._emit_atom(
                    self.line_start,
                    self.line_start + right,
                    value[:right],
                )
        else:
            left = len(value) - len(value.lstrip())
            right = len(value.rstrip())
            stripped = value[left:right]
            if stripped:
                if _CHAPTER_HEADING_RE.fullmatch(stripped):
                    self.heading_count += 1
                    if self.prose_in_chapter:
                        self._mark_last(scene=True, chapter=True)
                        self.chapter_ordinal += 1
                    elif not self.prose_anywhere:
                        self.chapter_ordinal = 1
                    self.scene_ordinal = 1
                    self.prose_in_chapter = False
                    self.prose_in_scene = False
                elif _SCENE_SEPARATOR_RE.fullmatch(stripped):
                    self.separator_count += 1
                    if self.prose_in_scene:
                        self._mark_last(scene=True)
                        self.scene_ordinal += 1
                    self.prose_in_scene = False
                else:
                    self._emit_atom(
                        self.line_start + left,
                        self.line_start + right,
                        stripped,
                    )
        self.line_buffer = []
        self.long_line = False
        self.paragraph_started = False

    def feed(self, chunk: str) -> None:
        for character in chunk:
            if character == "\n":
                self._finish_line()
                self.offset += 1
                self.line_start = self.offset
                continue
            self.line_buffer.append(character)
            self.offset += 1
            if len(self.line_buffer) > self.max_window_chars:
                self.long_line = True
                self._flush_long_prefixes()

    def finish(self) -> dict[str, int]:
        self._finish_line()
        if not self.atom_ordinal:
            raise StyleSamplingError("source_has_no_prose_units")
        self._mark_last(scene=True, chapter=True, global_=True)
        chapter_count = int(
            self.connection.execute(
                "SELECT COUNT(DISTINCT chapter_ordinal) FROM atoms"
            ).fetchone()[0]
        )
        scene_count = int(
            self.connection.execute(
                "SELECT COUNT(*) FROM (SELECT 1 FROM atoms GROUP BY chapter_ordinal,scene_ordinal)"
            ).fetchone()[0]
        )
        return {
            "chapter_count": chapter_count,
            "scene_count": scene_count,
            "paragraph_count": self.paragraph_ordinal,
            "unit_count": self.atom_ordinal,
            "chapter_heading_count": self.heading_count,
            "scene_separator_count": self.separator_count,
        }


def _candidate_from_spooled_atoms(
    source_stream: BinaryIO,
    first: sqlite3.Row,
    last: sqlite3.Row,
    *,
    last_seen_by_role: Sequence[int],
    candidate_filter: Callable[[str], bool] | None,
) -> _Candidate | None:
    start = int(first["start_char"])
    end = int(last["end_char"])
    source_slice = _read_utf32_span(source_stream, start, end)
    if candidate_filter is not None and not candidate_filter(source_slice):
        return None
    hint_mask = _span_candidate_hint_mask(
        first_index=int(first["atom_ordinal"]),
        last_seen_by_role=last_seen_by_role,
    )
    if bool(first["global_first"]):
        hint_mask |= _ROLE_HINT_BITS["opening"]
    elif bool(first["chapter_first"]):
        hint_mask |= _ROLE_HINT_BITS["opening"] | _ROLE_HINT_BITS["transition"]
    elif bool(first["scene_first"]):
        hint_mask |= _ROLE_HINT_BITS["opening"] | _ROLE_HINT_BITS["transition"]

    if bool(last["global_last"]):
        hint_mask |= _ROLE_HINT_BITS["ending"]
    elif bool(last["chapter_last"]):
        hint_mask |= _ROLE_HINT_BITS["ending"]
    elif bool(last["scene_last"]):
        hint_mask |= _ROLE_HINT_BITS["ending"]
    if not hint_mask:
        hint_mask = _ROLE_HINT_BITS["exposition"]
    roles = _candidate_roles_from_mask(hint_mask)
    return _Candidate(
        start=start,
        end=end,
        chapter_ordinal=int(first["chapter_ordinal"]),
        scene_ordinal=int(first["scene_ordinal"]),
        paragraph_start_ordinal=int(first["paragraph_ordinal"]),
        paragraph_end_ordinal=int(last["paragraph_ordinal"]),
        candidate_roles=roles,
        passage_fingerprint=fingerprint_source_text(source_slice),
    )


def _spool_stream_candidates(
    connection: sqlite3.Connection,
    source_stream: BinaryIO,
    *,
    target_window_chars: int,
    max_window_chars: int,
    candidate_filter: Callable[[str], bool] | None,
) -> int:
    """Build a prose-free candidate table in bounded memory.

    Forward spans use a queue and backward spans use a bisected sliding list;
    every atom enters and leaves each structure once.  The temporary database
    carries offsets, candidate-hint masks, and hashes only, never source text.
    """

    connection.execute(
        "CREATE TABLE candidates("
        "start_char INTEGER NOT NULL,end_char INTEGER NOT NULL,"
        "chapter_ordinal INTEGER NOT NULL,scene_ordinal INTEGER NOT NULL,"
        "paragraph_start_ordinal INTEGER NOT NULL,paragraph_end_ordinal INTEGER NOT NULL,"
        "role_mask INTEGER NOT NULL,"
        "passage_fingerprint TEXT NOT NULL,PRIMARY KEY(start_char,end_char))"
    )
    connection.execute(
        "CREATE INDEX candidate_role_mask_idx ON candidates(role_mask,start_char,end_char)"
    )
    accepted_span_calls = 0

    def offer(
        first: sqlite3.Row,
        last: sqlite3.Row,
        last_seen_by_role: Sequence[int],
    ) -> None:
        nonlocal accepted_span_calls
        candidate = _candidate_from_spooled_atoms(
            source_stream,
            first,
            last,
            last_seen_by_role=last_seen_by_role,
            candidate_filter=candidate_filter,
        )
        if candidate is None:
            return
        accepted_span_calls += 1
        role_mask = sum(
            1 << STYLE_SAMPLE_ROLES.index(role) for role in candidate.candidate_roles
        )
        connection.execute(
            "INSERT OR IGNORE INTO candidates(start_char,end_char,chapter_ordinal,"
            "scene_ordinal,paragraph_start_ordinal,paragraph_end_ordinal,role_mask,"
            "passage_fingerprint) VALUES(?,?,?,?,?,?,?,?)",
            (
                candidate.start,
                candidate.end,
                candidate.chapter_ordinal,
                candidate.scene_ordinal,
                candidate.paragraph_start_ordinal,
                candidate.paragraph_end_ordinal,
                role_mask,
                candidate.passage_fingerprint,
            ),
        )

    pending: deque[sqlite3.Row] = deque()
    recent: list[sqlite3.Row] = []
    recent_starts: list[int] = []
    recent_head = 0
    previous: sqlite3.Row | None = None
    previous_last_seen: tuple[int, ...] | None = None
    last_seen = [-1] * len(STYLE_SAMPLE_ROLES)
    scene_key: tuple[int, int] | None = None

    def flush_scene() -> None:
        nonlocal pending
        if previous is not None:
            if previous_last_seen is None:  # pragma: no cover - scan invariant
                raise StyleSamplingError("stream_candidate_hint_index_invalid")
            while pending:
                offer(pending.popleft(), previous, previous_last_seen)

    cursor = connection.execute("SELECT * FROM atoms ORDER BY atom_ordinal")
    for row in cursor:
        current_key = (int(row["chapter_ordinal"]), int(row["scene_ordinal"]))
        if scene_key is not None and current_key != scene_key:
            flush_scene()
            pending = deque()
            recent = []
            recent_starts = []
            recent_head = 0
            previous = None
            previous_last_seen = None
        scene_key = current_key

        atom_ordinal = int(row["atom_ordinal"])
        atom_hint_mask = int(row["candidate_hint_mask"])
        for role_index, role in enumerate(STYLE_SAMPLE_ROLES):
            if atom_hint_mask & _ROLE_HINT_BITS[role]:
                last_seen[role_index] = atom_ordinal
        current_last_seen = tuple(last_seen)

        while (
            pending
            and int(row["end_char"]) - int(pending[0]["start_char"])
            > max_window_chars
        ):
            if previous is None:  # pragma: no cover - queue invariant
                raise StyleSamplingError("stream_candidate_queue_invalid")
            if previous_last_seen is None:  # pragma: no cover - scan invariant
                raise StyleSamplingError("stream_candidate_hint_index_invalid")
            offer(pending.popleft(), previous, previous_last_seen)
        pending.append(row)
        while (
            pending
            and int(row["end_char"]) - int(pending[0]["start_char"])
            >= target_window_chars
        ):
            offer(pending.popleft(), row, current_last_seen)

        recent.append(row)
        recent_starts.append(int(row["start_char"]))
        while (
            recent_head < len(recent)
            and int(row["end_char"]) - int(recent[recent_head]["start_char"])
            > max_window_chars
        ):
            recent_head += 1
        if recent_head >= len(recent):  # pragma: no cover - atom length invariant
            raise StyleSamplingError("stream_candidate_window_invalid")
        threshold = int(row["end_char"]) - target_window_chars
        backward_index = bisect_right(
            recent_starts, threshold, lo=recent_head
        ) - 1
        if backward_index < recent_head:
            backward_index = recent_head
        offer(recent[backward_index], row, current_last_seen)
        if recent_head > 4_096:
            recent = recent[recent_head:]
            recent_starts = recent_starts[recent_head:]
            recent_head = 0
        previous = row
        previous_last_seen = current_last_seen
    flush_scene()
    unique_count = int(connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0])
    return accepted_span_calls - unique_count


def _candidate_from_db_row(row: sqlite3.Row) -> _Candidate:
    role_mask = int(row["role_mask"])
    return _Candidate(
        start=int(row["start_char"]),
        end=int(row["end_char"]),
        chapter_ordinal=int(row["chapter_ordinal"]),
        scene_ordinal=int(row["scene_ordinal"]),
        paragraph_start_ordinal=int(row["paragraph_start_ordinal"]),
        paragraph_end_ordinal=int(row["paragraph_end_ordinal"]),
        candidate_roles=_candidate_roles_from_mask(role_mask),
        passage_fingerprint=str(row["passage_fingerprint"]),
    )


def _validate_stream_prior_manifest(
    prior_manifest: Mapping[str, Any],
    *,
    source_stream: BinaryIO,
    source_fingerprint: str,
    source_chars: int,
    source_bytes: int,
    requested_roles: tuple[str, ...],
    target_window_chars: int,
    max_window_chars: int,
    max_overlap_ppm: int,
) -> dict[str, Any]:
    validate_sampling_manifest(prior_manifest)
    prior = _copy_json(prior_manifest)
    source = prior["source_binding"]
    if source["source_fingerprint"] != source_fingerprint:
        raise StyleSamplingError("prior_manifest_source_mismatch")
    if source["unicode_chars"] != source_chars or source["utf8_bytes"] != source_bytes:
        raise StyleSamplingError("prior_manifest_source_size_mismatch")
    selection = prior["selection_contract"]
    # Keep the prior round's role request bound inside its own fingerprint,
    # but allow the semantic planner to change the current retrieval hint.
    if selection["target_window_chars"] != target_window_chars:
        raise StyleSamplingError("prior_manifest_target_window_mismatch")
    if selection["max_window_chars"] != max_window_chars:
        raise StyleSamplingError("prior_manifest_max_window_mismatch")
    if selection["max_overlap_ppm"] != max_overlap_ppm:
        raise StyleSamplingError("prior_manifest_overlap_mismatch")
    for window in prior["windows"]:
        start = int(window["span"]["start"])
        end = int(window["span"]["end"])
        if fingerprint_source_text(_read_utf32_span(source_stream, start, end)) != window[
            "passage_fingerprint"
        ]:
            raise StyleSamplingError("prior_manifest_passage_binding_mismatch")
    return prior


def _build_stream_sampling_result(
    connection: sqlite3.Connection,
    source_stream: BinaryIO,
    *,
    source_fingerprint: str,
    source_chars: int,
    source_bytes: int,
    segmentation_counts: Mapping[str, int],
    duplicate_span_count: int,
    roles: tuple[str, ...],
    max_windows: int,
    target_window_chars: int,
    max_window_chars: int,
    max_overlap_ppm: int,
    prior: Mapping[str, Any] | None,
) -> dict[str, Any]:
    prior_windows: list[dict[str, Any]] = (
        _copy_json(prior["windows"]) if prior is not None else []
    )
    used_hashes = {window["passage_fingerprint"] for window in prior_windows}
    used_spans = [
        (int(window["span"]["start"]), int(window["span"]["end"]))
        for window in prior_windows
    ]
    current_round_covered: set[str] = set()
    used_chapters = {int(window["chapter_ordinal"]) for window in prior_windows}
    used_scenes = {
        (int(window["chapter_ordinal"]), int(window["scene_ordinal"]))
        for window in prior_windows
    }
    selected: list[tuple[_Candidate, str]] = []

    def eligible(candidate: _Candidate) -> bool:
        return _candidate_is_novel(
            candidate,
            used_hashes=used_hashes,
            used_spans=used_spans,
            max_overlap_ppm=max_overlap_ppm,
        )

    def add(candidate: _Candidate, primary_role: str) -> None:
        selected.append((candidate, primary_role))
        used_hashes.add(candidate.passage_fingerprint)
        used_spans.append((candidate.start, candidate.end))
        current_round_covered.update(
            set(candidate.candidate_roles).intersection(roles)
        )
        used_chapters.add(candidate.chapter_ordinal)
        used_scenes.add((candidate.chapter_ordinal, candidate.scene_ordinal))

    def candidates_for_role(role: str | None = None) -> Iterable[_Candidate]:
        if role is None:
            rows = connection.execute(
                "SELECT * FROM candidates ORDER BY start_char,end_char"
            )
        else:
            role_bit = 1 << STYLE_SAMPLE_ROLES.index(role)
            rows = connection.execute(
                "SELECT * FROM candidates WHERE (role_mask & ?) != 0 "
                "ORDER BY start_char,end_char",
                (role_bit,),
            )
        for row in rows:
            yield _candidate_from_db_row(row)

    for role in roles:
        if role in current_round_covered or len(selected) >= max_windows:
            continue
        uncovered = set(roles) - current_round_covered
        best: _Candidate | None = None
        best_rank: tuple[int, int, int, int, int, int, str] | None = None
        for candidate in candidates_for_role(role):
            if not eligible(candidate):
                continue
            rank = _rank_candidate(
                candidate,
                role=role,
                uncovered_roles=uncovered,
                used_chapters=used_chapters,
                used_scenes=used_scenes,
                target_window_chars=target_window_chars,
            )
            if best_rank is None or rank > best_rank:
                best = candidate
                best_rank = rank
        if best is not None:
            add(best, role)

    if prior is not None and set(roles).issubset(current_round_covered):
        desired_current_count = len(selected)
    else:
        desired_current_count = min(
            max_windows,
            max(
                1,
                min(
                    len(roles),
                    6,
                    math.ceil(math.sqrt(int(segmentation_counts["unit_count"]))),
                ),
            ),
        )
    while len(selected) < desired_current_count:
        best = None
        best_rank: tuple[int, int, int, int, int, str] | None = None
        for candidate in candidates_for_role():
            if not set(candidate.candidate_roles).intersection(roles) or not eligible(
                candidate
            ):
                continue
            rank = (
                int(candidate.chapter_ordinal not in used_chapters),
                int(
                    (candidate.chapter_ordinal, candidate.scene_ordinal)
                    not in used_scenes
                ),
                len(set(candidate.candidate_roles).intersection(roles)),
                -abs((candidate.end - candidate.start) - target_window_chars),
                -candidate.start,
                candidate.passage_fingerprint,
            )
            if best_rank is None or rank > best_rank:
                best = candidate
                best_rank = rank
        if best is None:
            break
        primary = next(role for role in roles if role in best.candidate_roles)
        add(best, primary)

    current_records = [
        _window_record(source_fingerprint, candidate, primary_role)
        for candidate, primary_role in selected
    ]
    all_windows = prior_windows + current_records
    all_windows.sort(
        key=lambda window: (
            window["span"]["start"],
            window["span"]["end"],
            window["window_id"],
        )
    )
    current_ids = [record["window_id"] for record in current_records]
    cumulative_covered = {
        role
        for window in all_windows
        for role in window["candidate_roles"]
        if role in roles
    }
    covered_roles = [role for role in roles if role in cumulative_covered]
    coverage_gaps = [role for role in roles if role not in cumulative_covered]

    remaining_count = 0
    remaining_role_mask = 0
    candidate_role_mask = 0
    overlap_suppressed = 0
    for candidate in candidates_for_role():
        role_mask = sum(
            1 << STYLE_SAMPLE_ROLES.index(role) for role in candidate.candidate_roles
        )
        candidate_role_mask |= role_mask
        if eligible(candidate):
            remaining_count += 1
            remaining_role_mask |= role_mask
        elif candidate.passage_fingerprint not in used_hashes and any(
            _overlap_ppm(candidate.start, candidate.end, start, end)
            > max_overlap_ppm
            for start, end in used_spans
        ):
            overlap_suppressed += 1
    remaining_gap_roles = [
        role
        for role in coverage_gaps
        if remaining_role_mask & (1 << STYLE_SAMPLE_ROLES.index(role))
    ]
    gap_reasons = []
    for role in coverage_gaps:
        bit = 1 << STYLE_SAMPLE_ROLES.index(role)
        if not candidate_role_mask & bit:
            reason = "no_candidate"
        elif len(selected) >= max_windows and role in remaining_gap_roles:
            reason = "window_budget_reached"
        else:
            reason = "overlap_or_duplicate_suppressed"
        gap_reasons.append({"role": role, "reason": reason})

    if not coverage_gaps:
        coverage_state = "complete"
        saturation_state = "coverage_complete"
    elif len(selected) >= max_windows and remaining_gap_roles:
        coverage_state = "partial" if covered_roles else "none"
        saturation_state = "window_budget_reached"
    else:
        coverage_state = "partial" if covered_roles else "none"
        saturation_state = "role_candidates_exhausted"

    functional_layers = []
    for layer, layer_roles in ROLE_LAYERS.items():
        layer_requested = [role for role in roles if role in layer_roles]
        layer_covered = [role for role in covered_roles if role in layer_roles]
        layer_gaps = [role for role in coverage_gaps if role in layer_roles]
        layer_state = "not_requested" if not layer_requested else (
            "complete" if not layer_gaps else ("partial" if layer_covered else "none")
        )
        functional_layers.append(
            {
                "layer": layer,
                "requested_roles": layer_requested,
                "covered_roles": layer_covered,
                "coverage_gaps": layer_gaps,
                "state": layer_state,
            }
        )

    distinct_chapters = {int(window["chapter_ordinal"]) for window in all_windows}
    distinct_scenes = {
        (int(window["chapter_ordinal"]), int(window["scene_ordinal"]))
        for window in all_windows
    }
    if not all_windows:
        novelty_state = "not_observed"
    elif len(all_windows) == 1:
        novelty_state = "single_window"
    elif len(distinct_chapters) > 1:
        novelty_state = "multi_chapter"
    elif len(distinct_scenes) > 1:
        novelty_state = "multi_scene"
    else:
        novelty_state = "within_scene"
    duplicate_hashes = int(
        connection.execute(
            "SELECT COALESCE(SUM(candidate_count-1),0) FROM "
            "(SELECT COUNT(*) AS candidate_count FROM candidates "
            "GROUP BY passage_fingerprint HAVING COUNT(*)>1)"
        ).fetchone()[0]
    )

    unsigned_manifest: dict[str, Any] = {
        "schema": STYLE_SAMPLING_MANIFEST_SCHEMA,
        "sampling_round": 1 if prior is None else int(prior["sampling_round"]) + 1,
        "previous_manifest_fingerprint": None
        if prior is None
        else prior["manifest_fingerprint"],
        "source_binding": {
            "source_fingerprint": source_fingerprint,
            "unicode_chars": source_chars,
            "utf8_bytes": source_bytes,
        },
        "segmentation": {
            **dict(segmentation_counts),
            "chapter_boundary_mode": "common_zh_en_headings",
            "scene_boundary_mode": "explicit_scene_markers",
            "paragraph_boundary_mode": "logical_nonempty_lines",
        },
        "selection_contract": {
            "requested_roles": list(roles),
            "max_windows_per_call": max_windows,
            "target_window_chars": target_window_chars,
            "max_window_chars": max_window_chars,
            "max_overlap_ppm": max_overlap_ppm,
            "deterministic": True,
            "overlap_suppression": True,
        },
        "role_assignment": dict(_CANDIDATE_HINT_ASSIGNMENT),
        "persistence_boundary": {
            "manifest_contains_prose": False,
            "ephemeral_windows_persistable": False,
        },
        "windows": all_windows,
        "current_window_ids": current_ids,
        "coverage": {
            "state": coverage_state,
            "requested_roles": list(roles),
            "covered_roles": covered_roles,
            "coverage_gaps": coverage_gaps,
            "gap_reasons": gap_reasons,
        },
        "functional_layers": functional_layers,
        "novelty": {
            "state": novelty_state,
            "cumulative_window_count": len(all_windows),
            "current_window_count": len(current_records),
            "unique_window_hash_count": len(
                {window["passage_fingerprint"] for window in all_windows}
            ),
            "distinct_chapter_count": len(distinct_chapters),
            "distinct_scene_count": len(distinct_scenes),
            "duplicate_candidate_hashes": duplicate_hashes,
            "duplicate_candidate_spans": duplicate_span_count,
        },
        "saturation": {
            "state": saturation_state,
            "remaining_nonoverlapping_candidates": remaining_count,
            "remaining_gap_candidate_roles": remaining_gap_roles,
            "overlap_suppressed_candidates": overlap_suppressed,
        },
    }
    manifest = {
        **unsigned_manifest,
        "manifest_fingerprint": _fingerprint_value(unsigned_manifest),
    }
    validate_sampling_manifest(manifest)
    record_by_id = {record["window_id"]: record for record in current_records}
    ephemeral_windows = []
    for candidate, primary_role in selected:
        record = record_by_id[_window_id(source_fingerprint, candidate)]
        passage = _read_utf32_span(source_stream, candidate.start, candidate.end)
        ephemeral_windows.append(
            {
                "window_id": record["window_id"],
                "source_fingerprint": source_fingerprint,
                "span": dict(record["span"]),
                "role": primary_role,
                "candidate_roles": list(record["candidate_roles"]),
                "passage_fingerprint": candidate.passage_fingerprint,
                "text": passage,
                "persistence": "ephemeral_call_only",
            }
        )
    return {
        "schema": STYLE_SAMPLING_RESULT_SCHEMA,
        "manifest": manifest,
        "ephemeral_windows": ephemeral_windows,
    }


def sample_style_chunks(
    chunks: Iterable[str],
    *,
    requested_roles: Sequence[str] = STYLE_SAMPLE_ROLES,
    max_windows: int = DEFAULT_MAX_WINDOWS,
    target_window_chars: int | None = None,
    max_window_chars: int = DEFAULT_MAX_WINDOW_CHARS,
    max_overlap_ratio: float = DEFAULT_MAX_OVERLAP_RATIO,
    prior_manifest: Mapping[str, Any] | None = None,
    candidate_filter: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Sample a normalized source stream without materializing the whole work.

    ``chunks`` must yield the exact normalized decoded text in order.  The
    function writes it only to an anonymous, call-scoped UTF-32 temporary file
    so character spans can be rebound without keeping the source in memory.
    The temporary SQLite database contains offsets/candidate hints/hashes
    only.  Both resources are closed before this function returns; only
    selected ephemeral windows contain prose.

    The original :func:`sample_style_windows` limits and output remain
    unchanged.  This API has separate, explicit stream ceilings and therefore
    does not disguise a larger in-memory allocation as a limit increase.
    """

    if isinstance(chunks, (str, bytes)) or not isinstance(chunks, Iterable):
        raise StyleSamplingError("source_chunks_must_be_iterable")
    roles = _validate_requested_roles(requested_roles)
    max_windows = _require_int(
        max_windows, "max_windows_invalid", minimum=1, maximum=MAX_WINDOWS
    )
    max_window_chars = _require_int(
        max_window_chars,
        "max_window_chars_invalid",
        minimum=MIN_WINDOW_CHARS,
        maximum=MAX_WINDOW_CHARS,
    )
    if target_window_chars is not None:
        target_window_chars = _require_int(
            target_window_chars,
            "target_window_chars_invalid",
            minimum=MIN_WINDOW_CHARS,
            maximum=MAX_WINDOW_CHARS,
        )
        if target_window_chars > max_window_chars:
            raise StyleSamplingError("target_window_exceeds_maximum")
    if (
        isinstance(max_overlap_ratio, bool)
        or not isinstance(max_overlap_ratio, (int, float))
        or not math.isfinite(float(max_overlap_ratio))
        or float(max_overlap_ratio) < 0
        or float(max_overlap_ratio) >= 1
    ):
        raise StyleSamplingError("max_overlap_ratio_invalid")
    if candidate_filter is not None and not callable(candidate_filter):
        raise StyleSamplingError("candidate_filter_invalid")
    max_overlap_ppm = int(float(max_overlap_ratio) * 1_000_000)

    connection = sqlite3.connect("")
    connection.row_factory = sqlite3.Row
    try:
        with tempfile.TemporaryFile(mode="w+b") as source_stream:
            segmenter = _StreamAtomSpool(
                connection, max_window_chars=max_window_chars
            )
            source_hash = hashlib.sha256()
            source_chars = 0
            source_bytes = 0
            for chunk in chunks:
                if not isinstance(chunk, str):
                    raise StyleSamplingError("source_chunk_must_be_string")
                if not chunk:
                    continue
                if len(chunk) > MAX_STREAM_CHUNK_CHARS:
                    raise StyleSamplingError("source_chunk_too_many_characters")
                if "\x00" in chunk:
                    raise StyleSamplingError("source_text_contains_nul")
                if "\r" in chunk:
                    raise StyleSamplingError("stream_source_not_normalized")
                encoded = chunk.encode("utf-8", errors="strict")
                if len(encoded) > MAX_STREAM_CHUNK_UTF8_BYTES:
                    raise StyleSamplingError("source_chunk_too_many_bytes")
                source_chars += len(chunk)
                source_bytes += len(encoded)
                if source_chars > MAX_STREAM_SOURCE_CHARS:
                    raise StyleSamplingError("stream_source_too_many_characters")
                if source_bytes > MAX_STREAM_SOURCE_UTF8_BYTES:
                    raise StyleSamplingError("stream_source_too_many_bytes")
                source_hash.update(encoded)
                source_stream.write(chunk.encode("utf-32-le", errors="strict"))
                segmenter.feed(chunk)
            if source_chars == 0:
                raise StyleSamplingError("source_text_empty")
            segmentation_counts = segmenter.finish()
            source_fingerprint = "sha256:" + source_hash.hexdigest()
            if target_window_chars is None:
                resolved_target = _adaptive_target(
                    source_chars, max_windows, max_window_chars
                )
            else:
                resolved_target = target_window_chars
            prior: dict[str, Any] | None = None
            if prior_manifest is not None:
                prior = _validate_stream_prior_manifest(
                    prior_manifest,
                    source_stream=source_stream,
                    source_fingerprint=source_fingerprint,
                    source_chars=source_chars,
                    source_bytes=source_bytes,
                    requested_roles=roles,
                    target_window_chars=resolved_target,
                    max_window_chars=max_window_chars,
                    max_overlap_ppm=max_overlap_ppm,
                )
            duplicate_spans = _spool_stream_candidates(
                connection,
                source_stream,
                target_window_chars=resolved_target,
                max_window_chars=max_window_chars,
                candidate_filter=candidate_filter,
            )
            return _build_stream_sampling_result(
                connection,
                source_stream,
                source_fingerprint=source_fingerprint,
                source_chars=source_chars,
                source_bytes=source_bytes,
                segmentation_counts=segmentation_counts,
                duplicate_span_count=duplicate_spans,
                roles=roles,
                max_windows=max_windows,
                target_window_chars=resolved_target,
                max_window_chars=max_window_chars,
                max_overlap_ppm=max_overlap_ppm,
                prior=prior,
            )
    except UnicodeEncodeError as exc:
        raise StyleSamplingError("source_text_not_utf8_encodable") from exc
    finally:
        connection.close()


def materialize_style_chunk_span(
    chunks: Iterable[str],
    *,
    source_fingerprint: str,
    start: int,
    end: int,
    passage_fingerprint: str,
) -> dict[str, Any]:
    """Rebind one stream span while retaining only that bounded passage."""

    if not isinstance(source_fingerprint, str) or not _HASH_RE.fullmatch(
        source_fingerprint
    ):
        raise StyleSamplingError("invalid_source_fingerprint")
    if not isinstance(passage_fingerprint, str) or not _HASH_RE.fullmatch(
        passage_fingerprint
    ):
        raise StyleSamplingError("invalid_passage_fingerprint")
    start = _require_int(
        start, "window_start_invalid", minimum=0, maximum=MAX_STREAM_SOURCE_CHARS
    )
    end = _require_int(
        end, "window_end_invalid", minimum=1, maximum=MAX_STREAM_SOURCE_CHARS
    )
    if end <= start or end - start > MAX_WINDOW_CHARS:
        raise StyleSamplingError("window_span_invalid")
    digest = hashlib.sha256()
    cursor = 0
    utf8_bytes = 0
    passage_parts: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, str):
            raise StyleSamplingError("source_chunk_must_be_string")
        if not chunk:
            continue
        if len(chunk) > MAX_STREAM_CHUNK_CHARS:
            raise StyleSamplingError("source_chunk_too_many_characters")
        if "\x00" in chunk or "\r" in chunk:
            raise StyleSamplingError("stream_source_not_normalized")
        encoded = chunk.encode("utf-8", errors="strict")
        if len(encoded) > MAX_STREAM_CHUNK_UTF8_BYTES:
            raise StyleSamplingError("source_chunk_too_many_bytes")
        digest.update(encoded)
        utf8_bytes += len(encoded)
        next_cursor = cursor + len(chunk)
        overlap_start = max(start, cursor)
        overlap_end = min(end, next_cursor)
        if overlap_start < overlap_end:
            passage_parts.append(
                chunk[overlap_start - cursor : overlap_end - cursor]
            )
        cursor = next_cursor
        if cursor > MAX_STREAM_SOURCE_CHARS or utf8_bytes > MAX_STREAM_SOURCE_UTF8_BYTES:
            raise StyleSamplingError("stream_source_size_limit")
    actual_source = "sha256:" + digest.hexdigest()
    if actual_source != source_fingerprint or end > cursor:
        raise StyleSamplingError("style_window_source_binding_mismatch")
    passage = "".join(passage_parts)
    if len(passage) != end - start or fingerprint_source_text(passage) != passage_fingerprint:
        raise StyleSamplingError("style_window_passage_binding_mismatch")
    return {
        "passage": passage,
        "source_fingerprint": actual_source,
        "passage_fingerprint": passage_fingerprint,
        "unicode_chars": cursor,
        "utf8_bytes": utf8_bytes,
    }


class StyleSampler:
    """Small object facade for hosts that prefer a named sampler service."""

    roles = STYLE_SAMPLE_ROLES
    role_layers = ROLE_LAYERS

    @staticmethod
    def fingerprint(text: str) -> str:
        return fingerprint_source_text(text)

    @staticmethod
    def sample(text: str, *, source_fingerprint: str, **options: Any) -> dict[str, Any]:
        return sample_style_windows(
            text, source_fingerprint=source_fingerprint, **options
        )

    @staticmethod
    def sample_chunks(chunks: Iterable[str], **options: Any) -> dict[str, Any]:
        return sample_style_chunks(chunks, **options)

    @staticmethod
    def validate_manifest(manifest: Mapping[str, Any]) -> None:
        validate_sampling_manifest(manifest)


__all__ = [
    "DEFAULT_MAX_OVERLAP_RATIO",
    "DEFAULT_MAX_WINDOW_CHARS",
    "DEFAULT_MAX_WINDOWS",
    "MAX_SOURCE_BYTES",
    "MAX_SOURCE_CHARS",
    "MAX_STREAM_PROSE_UNITS",
    "MAX_STREAM_CHUNK_CHARS",
    "MAX_STREAM_CHUNK_UTF8_BYTES",
    "MAX_STREAM_SOURCE_CHARS",
    "MAX_STREAM_SOURCE_UTF8_BYTES",
    "MAX_WINDOW_CHARS",
    "MAX_WINDOWS",
    "MIN_WINDOW_CHARS",
    "ROLE_LAYERS",
    "STYLE_SAMPLE_ROLES",
    "STYLE_SAMPLING_MANIFEST_SCHEMA",
    "STYLE_SAMPLING_RESULT_SCHEMA",
    "StyleSampler",
    "StyleSamplingError",
    "fingerprint_source_text",
    "materialize_style_chunk_span",
    "sample_style_chunks",
    "sample_style_windows",
    "style_window_hygiene_reason",
    "style_window_passes_hygiene",
    "validate_sampling_manifest",
]
