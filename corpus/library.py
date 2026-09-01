#!/usr/bin/env python3
"""Rights-bounded local corpus ledger and anonymous public export.

The private SQLite ledger deliberately stores file locations and private source
metadata, but never stores source prose.  Source text is decoded only while a
scan or a bounded three-window analysis is executing.  The public side has a
closed numeric schema so filenames, titles, creators, excerpts, and paths have
nowhere to leak.
"""
from __future__ import annotations

import codecs
import hashlib
import html
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import sqlite3
import stat
import tempfile
import unicodedata
import uuid
import zipfile
from typing import Any, Iterable, Mapping, Sequence
import xml.etree.ElementTree as ET


STUDY_SIZE = 120
GENERAL_MIN_CHARS = 100_000
MAX_WINDOW_CHARS = 4_000
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_EPUB_ENTRIES = 5_000
MAX_EPUB_EXPANDED_BYTES = 128 * 1024 * 1024
MAX_EPUB_MEMBER_BYTES = 32 * 1024 * 1024
MAX_EPUB_TEXT_CHARS = 24_000_000

PUBLIC_WORK_SCHEMA = "quillframe_public_corpus_work_v1"
PUBLIC_MANIFEST_SCHEMA = "quillframe_public_corpus_manifest_v1"
PUBLIC_VALIDATION_SCHEMA = "quillframe_public_corpus_validation_v1"

METRIC_KEYS = (
    "sampled_chars",
    "paragraph_count",
    "sentence_count",
    "mean_sentence_chars_milli",
    "dialogue_char_ratio_ppm",
    "unique_char_ratio_ppm",
    "punctuation_ratio_ppm",
)

CRAFT_AXES = (
    "sentence",
    "scene",
    "chapter",
    "pacing",
    "dialogue",
    "pov",
    "tension",
    "sensory",
)
CRAFT_LABELS: dict[str, tuple[str, ...]] = {
    "sentence": ("clipped", "balanced", "extended"),
    "scene": ("fragmented", "balanced", "sustained"),
    "chapter": ("low_segmentation", "moderate_segmentation", "high_segmentation"),
    "pacing": ("brisk", "mixed", "deliberate"),
    "dialogue": ("sparse", "mixed", "dialogue_forward"),
    "pov": ("unresolved",),
    "tension": ("low_signal", "variable_signal", "high_signal"),
    "sensory": ("unresolved",),
}
_MECHANISM_BOUNDARIES = {"anonymous_three_window_sample"}
_MECHANISM_COUNTEREXAMPLES = {
    "non_dominant_profiles_present",
    "axis_evidence_unresolved",
    "no_observed_counterexample_in_sample",
}
_MECHANISM_FAILURE_MODES = {"descriptive_not_prescriptive"}
_CONTROLLED_PUBLIC_STRINGS = (
    {label for labels in CRAFT_LABELS.values() for label in labels}
    | _MECHANISM_BOUNDARIES
    | _MECHANISM_COUNTEREXAMPLES
    | _MECHANISM_FAILURE_MODES
    | set(CRAFT_AXES)
    | {"general", "adult_explicit"}
)
_DERIVED_SHORT_ENUMS = {
    "low", "medium", "high", "pass", "fail", "unknown", "unresolved",
    "opening", "middle", "closing", "present", "absent", "mixed",
}

_PUBLIC_WORK_KEYS = {
    "schema",
    "public_work_id",
    "profile",
    "study_ordinal",
    "source_version",
    "metrics",
    "craft_profile",
    "record_fingerprint",
}
_PUBLIC_MANIFEST_KEYS = {
    "schema",
    "public_study_id",
    "profile",
    "study_state",
    "work_count",
    "checklist_hash",
    "aggregate_metrics",
    "aggregate_mechanisms",
    "works",
    "preview_token",
    "manifest_fingerprint",
}
_FORBIDDEN_PUBLIC_KEYS = {
    "author",
    "authors",
    "creator",
    "creators",
    "title",
    "source_title",
    "source",
    "source_ref",
    "source_path",
    "path",
    "filepath",
    "file_path",
    "filename",
    "display_label",
    "relative_locator",
    "directory",
    "root",
    "url",
    "uri",
    "rights_basis",
    "content",
    "body",
    "text",
    "raw",
    "raw_text",
    "excerpt",
    "quote",
    "summary",
    "name",
    "proper_name",
}
_PUBLIC_ID_RE = re.compile(r"^(?:PW|PS)-[0-9a-f]{32}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^preview-[0-9a-f]{64}$")
_PATH_LIKE_RE = re.compile(
    r"(?:^[A-Za-z]:[\\/]|[\\/]|\.\.|file:|(?:^|[^A-Za-z])users(?:[^A-Za-z]|$)|~[\\/])",
    re.IGNORECASE,
)
_XML_DOCTYPE_START_RE = re.compile(r"<!\s*DOCTYPE\b", re.IGNORECASE)
_XML_ENTITY_DECL_RE = re.compile(r"<!\s*ENTITY\b", re.IGNORECASE)
_XML_QUOTED_LITERAL = r'(?:"[^"<>\[\]]*"|\'[^\'<>\[\]]*\')'
_XML_ALLOWED_DOCTYPE_RE = re.compile(
    rf"<!DOCTYPE\s+[A-Za-z_][A-Za-z0-9_.:-]*"
    rf"(?:\s+SYSTEM\s+{_XML_QUOTED_LITERAL}"
    rf"|\s+PUBLIC\s+{_XML_QUOTED_LITERAL}\s+{_XML_QUOTED_LITERAL})?\s*>",
    re.IGNORECASE,
)
_XML_PROLOG_PREFIX_RE = re.compile(
    r"\A\ufeff?\s*(?:<\?xml\b.*?\?>\s*)?"
    r"(?:(?:<!--.*?-->|<\?(?!xml\b).*?\?>)\s*)*\Z",
    re.IGNORECASE | re.DOTALL,
)

_STRONG_ADULT_TITLE_RE = re.compile(
    r"(?:\br[_ -]?18\b|adult[_ -]?explicit|成人(?:向|内容|小说|读物|限制级|分级|专区)|"
    r"情色|色情|淫|性交|性爱|性奴|"
    r"做爱|肏|爆干|巨屌|鸡巴|阴茎|阴道|阴蒂|龟头|肛交|射精|精液|"
    r"肉便|母猪|肉文|里番|乱伦|强奸|双修鼎炉|泄精|纵欲|发情|"
    r"肉棒|巨根|配种|寝取|凌辱|乳交|口交|"
    r"内射|媚药|春药|隐奸|野爹|黄文|飞机杯)",
    re.IGNORECASE,
)
_AMBIGUOUS_ADULT_TITLE_RE = re.compile(
    r"(?:\bntr\b|\bntl\b|成人|黄毛|后宫|合欢宗|调教|催眠|恶堕|绿帽|"
    r"绿了|母上|妈妈|母亲|儿媳|熟女|猎妈|仙母|人妻|情事|欲望|寻欢|"
    r"百美|艳谭|艳遇|情花|福利回|播种|随便做|除膜|慰道|[xXｘＸ]奴|"
    r"[xXｘＸ]压抑|双修|师娘|继母|美母|夺爱|红颜|禁忌|艳|绿途|"
    r"女大男|黄发|假太监|"
    r"(?:^|[^A-Za-z])xp(?:[^A-Za-z]|$))",
    re.IGNORECASE,
)
_DERIVATIVE_TITLE_RE = re.compile(
    r"(?:ai\s*(?:加料|续写)|加料(?:版)?|续(?:写|改)|同人(?:文|整合)?|二改|改写|修改版|"
    r"重置|衔接|和谐章节|(?:系列)?合集|整合版|衍生版|draft)",
    re.IGNORECASE,
)
_GENERIC_IDENTITY_RE = re.compile(
    r"^(?:untitled|unknown|document|text|book|novel|download|export)\d*$"
    r"|^(?:未命名|无标题|新建文本文档)\d*$"
    r"|^[0-9a-f]{16,}$",
    re.IGNORECASE,
)
_HIGH_CONFIDENCE_HAN_FAMILY_TRANSLATION = str.maketrans(
    {
        "從": "从", "茲": "兹", "體": "体", "說": "说", "試": "试",
        "書": "书", "國": "国", "學": "学", "術": "术", "傳": "传",
        "門": "门", "風": "风", "雲": "云", "龍": "龙", "馬": "马",
        "劍": "剑", "萬": "万", "與": "与", "為": "为", "這": "这",
        "個": "个", "來": "来", "開": "开", "關": "关", "時": "时",
        "長": "长", "無": "无", "會": "会", "異": "异", "殺": "杀",
        "愛": "爱", "夢": "梦", "覺": "觉", "頭": "头", "靈": "灵",
        "麗": "丽", "華": "华", "東": "东", "葉": "叶", "黃": "黄",
        "貴": "贵", "師": "师", "權": "权", "轉": "转", "職": "职",
        "網": "网", "絡": "络", "電": "电", "機": "机", "現": "现",
        "實": "实", "寶": "宝", "戰": "战", "爭": "争", "歸": "归",
        "讀": "读", "寫": "写", "導": "导", "標": "标", "記": "记",
        "錄": "录", "隨": "随", "爐": "炉", "壞": "坏", "壓": "压",
        "應": "应", "該": "该", "點": "点", "聲": "声", "樂": "乐",
        "還": "还", "讓": "让", "聖": "圣", "墮": "堕", "續": "续",
        "號": "号", "編": "编", "輯": "辑", "結": "结", "終": "终",
        "總": "总", "臺": "台", "裡": "里", "裏": "里", "後": "后",
        "惡": "恶", "調": "调", "亂": "乱", "強": "强", "慾": "欲", "髮": "发",
        "縱": "纵", "豔": "艳", "姦": "奸", "騷": "骚",
    }
)


class CorpusLibraryError(ValueError):
    """Stable local API error with a machine-readable code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class _ClosingConnection(sqlite3.Connection):
    """A transaction context that also releases Windows file handles."""

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc, traceback))
        finally:
            self.close()


class _BodyTextExtractor(HTMLParser):
    _BLOCKS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div",
        "dl", "dt", "figcaption", "figure", "footer", "h1", "h2", "h3",
        "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
        "p", "pre", "section", "table", "td", "th", "tr", "ul",
    }
    _SKIP = {"script", "style", "noscript", "svg", "math"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        lowered = tag.casefold()
        if lowered in self._SKIP:
            self.skip_depth += 1
        elif not self.skip_depth and lowered in self._BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in self._SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and lowered in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return _normalize_text(html.unescape("".join(self.parts)))


def _now_sql() -> str:
    # SQLite owns the persisted timestamp format; this helper is only for SQL
    # defaults expressed consistently in update statements.
    return "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _selection_material(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build the one canonical, ordered representation bound by a checklist hash."""

    return [
        {
            "public_work_id": row["public_work_id"],
            "source_version": row["version_number"],
            "source_fingerprint": "sha256:" + row["sha256"],
        }
        for row in rows
    ]


def _selection_fingerprint(profile: str, rows: Iterable[Mapping[str, Any]]) -> str:
    return _fingerprint({"profile": profile, "works": _selection_material(rows)})


def _rank_selection_pool(
    rows: Iterable[Mapping[str, Any]], seed: str
) -> list[Mapping[str, Any]]:
    """Return the deterministic top-120 used by both proposal and confirmation."""

    return sorted(
        rows,
        key=lambda row: (
            hashlib.sha256(
                (seed + "\0" + str(row["public_work_id"])).encode("utf-8")
            ).digest(),
            str(row["public_work_id"]),
            str(row["active_version_id"]),
        ),
    )[:STUDY_SIZE]


def _random_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    cleaned: list[str] = []
    for character in value:
        category = unicodedata.category(character)
        if character in {"\n", "\t"}:
            cleaned.append(character)
        elif category not in {"Cc", "Cf", "Cs"}:
            cleaned.append(character)
    value = "".join(cleaned)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    return value.strip()


_STREAM_NORMALIZATION_CARRY = 4_096
_STREAM_PENDING_WHITESPACE = 65_536


def _hangul_may_compose(left: str, right: str) -> bool:
    left_code = ord(left)
    right_code = ord(right)
    left_is_l = 0x1100 <= left_code <= 0x115F or 0xA960 <= left_code <= 0xA97C
    right_is_v = 0x1160 <= right_code <= 0x11A7 or 0xD7B0 <= right_code <= 0xD7C6
    left_is_v = 0x1160 <= left_code <= 0x11A7 or 0xD7B0 <= left_code <= 0xD7C6
    right_is_t = 0x11A8 <= right_code <= 0x11FF or 0xD7CB <= right_code <= 0xD7FB
    left_is_lv = 0xAC00 <= left_code <= 0xD7A3 and (left_code - 0xAC00) % 28 == 0
    return (left_is_l and right_is_v) or ((left_is_v or left_is_lv) and right_is_t)


def _iter_nfc_characters(chunks: Iterable[str]) -> Iterable[str]:
    """Yield NFC characters while retaining the only suffix future input can alter."""

    carry = ""
    for chunk in chunks:
        if not isinstance(chunk, str):
            raise CorpusLibraryError("txt_decode_failed")
        carry += chunk
        while len(carry) > _STREAM_NORMALIZATION_CARRY * 2:
            split = len(carry) - _STREAM_NORMALIZATION_CARRY
            while split > 0 and unicodedata.combining(carry[split]):
                split -= 1
            while split > 0 and _hangul_may_compose(carry[split - 1], carry[split]):
                split -= 1
            if split <= 0:
                raise CorpusLibraryError("txt_normalization_sequence_limit")
            normalized = unicodedata.normalize("NFC", carry[:split])
            yield from normalized
            carry = carry[split:]
    if carry:
        yield from unicodedata.normalize("NFC", carry)


def _iter_clean_normalized_characters(chunks: Iterable[str]) -> Iterable[str]:
    """Stream the transformations performed by :func:`_normalize_text`."""

    pending_cr = False
    pending_ascii_space = False
    after_newline = False
    newline_run = 0

    def transformed(character: str) -> Iterable[str]:
        nonlocal pending_ascii_space, after_newline, newline_run
        category = unicodedata.category(character)
        if character not in {"\n", "\t"} and category in {"Cc", "Cf", "Cs"}:
            return ()
        if character in {" ", "\t"}:
            if not after_newline:
                pending_ascii_space = True
            return ()
        if character == "\n":
            pending_ascii_space = False
            after_newline = True
            newline_run += 1
            return ("\n",) if newline_run <= 3 else ()
        prefix: tuple[str, ...] = ()
        if pending_ascii_space and not after_newline:
            prefix = (" ",)
        pending_ascii_space = False
        after_newline = False
        newline_run = 0
        return (*prefix, character)

    for character in _iter_nfc_characters(chunks):
        if pending_cr:
            pending_cr = False
            yield from transformed("\n")
            if character == "\n":
                continue
        if character == "\r":
            pending_cr = True
            continue
        yield from transformed(character)
    if pending_cr:
        yield from transformed("\n")


def _iter_normalized_text_chunks(chunks: Iterable[str]) -> Iterable[str]:
    """Return exactly normalized text in bounded chunks, including final strip."""

    started = False
    pending_whitespace: list[str] = []
    output: list[str] = []
    for character in _iter_clean_normalized_characters(chunks):
        if not started:
            if character.isspace():
                continue
            started = True
            output.append(character)
        elif character.isspace():
            pending_whitespace.append(character)
            if len(pending_whitespace) > _STREAM_PENDING_WHITESPACE:
                raise CorpusLibraryError("txt_trailing_whitespace_limit")
        else:
            if pending_whitespace:
                output.extend(pending_whitespace)
                pending_whitespace = []
            output.append(character)
        if len(output) >= 65_536:
            yield "".join(output)
            output = []
    # Pending whitespace is deliberately discarded to reproduce ``strip``.
    if output:
        yield "".join(output)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _decode_xml_bytes(data: bytes, error_code: str) -> str:
    """Decode EPUB XML using the encodings XML/EPUB permit without guessing."""

    encoding = "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    elif data.startswith(b"\x00<\x00?"):
        encoding = "utf-16-be"
    elif data.startswith(b"<\x00?\x00"):
        encoding = "utf-16-le"
    elif b"\x00" in data:
        raise CorpusLibraryError("epub_unsafe_xml")
    try:
        return data.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise CorpusLibraryError(error_code) from exc


def _strip_safe_doctype(value: str) -> str:
    """Remove one externally inert DOCTYPE after validating its exact form.

    ElementTree must never be given a declaration that could define or resolve
    entities.  EPUBs commonly contain an inert XHTML DOCTYPE, so a single
    simple, PUBLIC, or SYSTEM declaration is accepted only in the XML prolog.
    Any external identifier remains an unobserved literal: the whole declaration
    is stripped before parsing and is never resolved or fetched.  Internal
    subsets, ENTITY declarations, malformed declarations, and multiple
    declarations remain fail-closed.
    """

    if _XML_ENTITY_DECL_RE.search(value):
        raise CorpusLibraryError("epub_unsafe_xml")
    starts = list(_XML_DOCTYPE_START_RE.finditer(value))
    if not starts:
        return value
    if len(starts) != 1:
        raise CorpusLibraryError("epub_unsafe_xml")
    start = starts[0].start()
    declaration = _XML_ALLOWED_DOCTYPE_RE.match(value, start)
    if declaration is None:
        raise CorpusLibraryError("epub_unsafe_xml")
    if _XML_PROLOG_PREFIX_RE.fullmatch(value[:start]) is None:
        raise CorpusLibraryError("epub_unsafe_xml")
    return value[:start] + value[declaration.end():]


def _normal_overlap_text(value: str) -> str:
    return "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", value)
        if character.isalnum() or "\u3400" <= character <= "\u9fff"
    )


def _private_title_family(value: str) -> str | None:
    """Return a conservative private logical-title key, or ``None``.

    This intentionally handles only high-confidence filename conventions.  It
    does not use source prose, fuzzy similarity, or an author-attribution model.
    An uncertain identity is safer to exclude than to let an edition or chapter
    snapshot occupy a second study slot.
    """

    title = unicodedata.normalize("NFKC", str(value or "")).translate(
        _HIGH_CONFIDENCE_HAN_FAMILY_TRANSLATION
    ).strip()
    if not title:
        return None
    title = re.sub(
        r"^(?:(?:www[._-])?(?:soushu\d*[_-]?com|sxsy[_-]?org))@",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"@(?:sosdbot)\s*$", "", title, flags=re.IGNORECASE)

    bracketed = re.findall(r"《([^》]{1,200})》", title)
    if bracketed:
        title = bracketed[0]
    else:
        square = re.findall(r"【([^】]{1,200})】", title)
        for candidate in square:
            if not re.search(r"精校|校对|修订|全本|完本|完结|排版", candidate):
                title = candidate
                break

    title = re.sub(r"(?:[_+\s-]*(?:作品)?作者[：:].*)$", "", title)
    title = re.sub(
        r"(?:[_-]\s*by\s*[_:：-]\s*|\s+-\s+by\s+|[（(]\s*by\s+)"
        r"[A-Za-z0-9\u3400-\u9fff·.][A-Za-z0-9\u3400-\u9fff·. ]{0,79}[）)]?\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"(?:[_+\s-]*tags?[：_:].*)$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^(?:【[^】]*(?:精校|校对|修订|排版)[^】]*】\s*)+", "", title)

    edition_words = (
        r"(?:精校|校对|修订|修改|排版|加料|重置|全本|完本|完结|连载中?|"
        r"完整版|无缺章|番外|衔接|第\s*\d+\s*版)"
    )
    # Remove trailing parenthesized range/edition annotations only when the
    # entire annotation is mechanical; substantive subtitles remain identity.
    mechanical_parenthetical = re.compile(
        rf"[（(]\s*(?:(?:\d+(?:\s*[-_~～.至]\s*\d+)*(?:\s*章(?:上|下)?)?)|(?:{edition_words})|[\s+_,.-])+\s*[）)]\s*$",
        re.IGNORECASE,
    )
    previous = None
    while previous != title:
        previous = title
        title = mechanical_parenthetical.sub("", title).strip()

    snapshot_suffixes = (
        rf"(?:[_\s+.⊙-]*(?:排版\s*)?(?:0*1\s*[-_]\s*)?\d+"
        rf"(?:\s*[-_~～.]\s*\d+)+(?:\s*(?:章|节|卷))?(?:[_\s+.-]*{edition_words})*)$",
        rf"(?:[_\s+.⊙-]*(?:0*1\s*[-_]?\s*)?(?:卷[一二三四五六七八九十百0-9]+[_\s.-]*)?"
        rf"第?\s*\d+\s*[-_]\s*\d+\s*章(?:[_\s+.-]*{edition_words})*)$",
        rf"(?:[_\s+.⊙-]*(?:0*1\s*[-_]?\s*)?卷[一二三四五六七八九十百0-9]+"
        rf"第\s*\d+\s*章(?:[_\s+.-]*{edition_words})*)$",
        rf"(?:[_\s+.⊙-]*(?:至|到)\s*\d+\s*章(?:[_\s+.-]*{edition_words})*)$",
        r"(?:\s*⊙\s*0*1(?:[_\s.~-].*)?)$",
        rf"(?:[_\s+.⊙-]+{edition_words})+$",
    )
    previous = None
    while previous != title:
        previous = title
        for pattern in snapshot_suffixes:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE).strip()

    key = "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", title)
        if character.isalnum()
    )
    if not key or key.isdigit() or _GENERIC_IDENTITY_RE.fullmatch(key):
        return None
    if len(key) < 2 or (key.isascii() and len(key) < 4):
        return None
    return key


def _private_profile_signal(values: Iterable[str]) -> str:
    texts = [
        unicodedata.normalize("NFKC", str(value or "")).translate(
            _HIGH_CONFIDENCE_HAN_FAMILY_TRANSLATION
        )
        for value in values
    ]
    if any(_STRONG_ADULT_TITLE_RE.search(value) for value in texts):
        return "adult_explicit"
    if any(_AMBIGUOUS_ADULT_TITLE_RE.search(value) for value in texts):
        return "ambiguous"
    return "general"


def _private_creator_keys(metadata_creator: Any, values: Iterable[str]) -> set[str]:
    candidates: list[str] = []
    if str(metadata_creator or "").strip():
        candidates.append(str(metadata_creator).strip())
    for raw_value in values:
        value = unicodedata.normalize("NFKC", str(raw_value or ""))
        author = re.search(
            r"(?:作品)?作者[：:]\s*([A-Za-z0-9\u3400-\u9fff·.]{1,80})",
            value,
            re.IGNORECASE,
        )
        if author:
            candidates.append(author.group(1))
        byline = re.search(
            r"(?:[_-]\s*by\s*[_:：-]\s*|\s+-\s+by\s+|[（(]\s*by\s+)"
            r"([A-Za-z0-9\u3400-\u9fff·.][A-Za-z0-9\u3400-\u9fff·. ]{0,79})[）)]?\s*$",
            value,
            re.IGNORECASE,
        )
        if byline:
            candidates.append(byline.group(1).strip())
    keys: set[str] = set()
    for candidate in candidates:
        key = "".join(
            character.casefold()
            for character in unicodedata.normalize("NFKC", candidate).translate(
                _HIGH_CONFIDENCE_HAN_FAMILY_TRANSLATION
            )
            if character.isalnum()
        )
        if key:
            keys.add(key)
    return keys


def _safe_identifier(value: str, kind: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise CorpusLibraryError(f"invalid_{kind}")
    return value


class CorpusLibrary:
    """Local private corpus library with a closed anonymous export surface."""

    def __init__(self, db_path: str | Path, public_root: str | Path | None = None) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.public_root = (
            Path(public_root).expanduser().resolve()
            if public_root is not None
            else (Path(__file__).resolve().parent / "general")
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    # ------------------------------------------------------------------
    # SQLite ledger
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path, timeout=30, factory=_ClosingConnection
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS collections (
                    collection_id TEXT PRIMARY KEY,
                    root_path TEXT NOT NULL UNIQUE,
                    rights_class TEXT NOT NULL CHECK(rights_class IN ('redistributable','analysis_only','unknown')),
                    rights_basis TEXT NOT NULL,
                    language TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE TABLE IF NOT EXISTS logical_works (
                    work_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL REFERENCES collections(collection_id),
                    public_work_id TEXT NOT NULL UNIQUE,
                    logical_key TEXT NOT NULL,
                    active_version_id TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    UNIQUE(collection_id, logical_key)
                );
                CREATE TABLE IF NOT EXISTS source_versions (
                    version_id TEXT PRIMARY KEY,
                    work_id TEXT NOT NULL REFERENCES logical_works(work_id),
                    version_number INTEGER NOT NULL CHECK(version_number > 0),
                    sha256 TEXT NOT NULL CHECK(length(sha256) = 64),
                    media_type TEXT NOT NULL CHECK(media_type IN ('txt','epub')),
                    char_count INTEGER NOT NULL DEFAULT 0 CHECK(char_count >= 0),
                    parse_state TEXT NOT NULL CHECK(parse_state IN ('ok','error')),
                    error_code TEXT,
                    private_metadata_json TEXT NOT NULL DEFAULT '{}',
                    available INTEGER NOT NULL DEFAULT 1 CHECK(available IN (0,1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    UNIQUE(work_id, version_number),
                    UNIQUE(work_id, sha256)
                );
                CREATE TABLE IF NOT EXISTS source_files (
                    file_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL REFERENCES collections(collection_id),
                    relative_path TEXT NOT NULL,
                    work_id TEXT NOT NULL REFERENCES logical_works(work_id),
                    version_id TEXT NOT NULL REFERENCES source_versions(version_id),
                    available INTEGER NOT NULL DEFAULT 1 CHECK(available IN (0,1)),
                    last_seen_token TEXT NOT NULL,
                    UNIQUE(collection_id, relative_path)
                );
                CREATE TABLE IF NOT EXISTS studies (
                    study_id TEXT PRIMARY KEY,
                    public_study_id TEXT NOT NULL UNIQUE,
                    collection_id TEXT REFERENCES collections(collection_id),
                    profile TEXT NOT NULL DEFAULT 'general' CHECK(profile IN ('general','adult_explicit')),
                    state TEXT NOT NULL CHECK(state IN ('proposed','confirmed','running','paused','complete','invalidated')),
                    seed TEXT NOT NULL,
                    proposal_hash TEXT NOT NULL,
                    checklist_hash TEXT,
                    invalidation_reason TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE TABLE IF NOT EXISTS study_works (
                    study_id TEXT NOT NULL REFERENCES studies(study_id) ON DELETE CASCADE,
                    work_id TEXT NOT NULL REFERENCES logical_works(work_id),
                    version_id TEXT NOT NULL REFERENCES source_versions(version_id),
                    ordinal INTEGER NOT NULL CHECK(ordinal BETWEEN 1 AND 120),
                    state TEXT NOT NULL CHECK(state IN ('pending','selected','studied','invalidated')),
                    metrics_json TEXT,
                    analysis_fingerprint TEXT,
                    PRIMARY KEY(study_id, work_id),
                    UNIQUE(study_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS releases (
                    release_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL UNIQUE REFERENCES studies(study_id),
                    public_study_id TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL CHECK(state IN ('released','invalidated')),
                    manifest_fingerprint TEXT NOT NULL,
                    artifact_dir TEXT NOT NULL,
                    invalidation_reason TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE TABLE IF NOT EXISTS range_jobs (
                    range_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL REFERENCES studies(study_id),
                    work_id TEXT NOT NULL REFERENCES logical_works(work_id),
                    version_id TEXT NOT NULL REFERENCES source_versions(version_id),
                    scope TEXT NOT NULL CHECK(scope IN ('opening','middle','closing')),
                    range_start INTEGER NOT NULL CHECK(range_start >= 0),
                    range_end INTEGER NOT NULL CHECK(range_end >= range_start),
                    source_fingerprint TEXT NOT NULL,
                    passage_fingerprint TEXT NOT NULL,
                    rubric_json TEXT NOT NULL,
                    job_fingerprint TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL CHECK(state IN ('ready','complete','invalidated')),
                    judgment_json TEXT,
                    judgment_fingerprint TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    completed_at TEXT,
                    UNIQUE(study_id, work_id, version_id, scope, job_fingerprint)
                );
                CREATE TABLE IF NOT EXISTS semantic_completion_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    study_id TEXT NOT NULL UNIQUE REFERENCES studies(study_id),
                    run_id TEXT NOT NULL UNIQUE,
                    public_study_id TEXT NOT NULL,
                    profile TEXT NOT NULL CHECK(profile IN ('general','adult_explicit')),
                    checklist_hash TEXT NOT NULL,
                    range_job_count INTEGER NOT NULL,
                    work_synthesis_count INTEGER NOT NULL,
                    benchmark_job_fingerprint TEXT NOT NULL,
                    benchmark_result_fingerprint TEXT NOT NULL,
                    candidate_bundle_fingerprint TEXT NOT NULL,
                    receipt_fingerprint TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL CHECK(state IN ('complete','invalidated')),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE TABLE IF NOT EXISTS style_completion_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    style_run_id TEXT NOT NULL UNIQUE,
                    study_id TEXT NOT NULL REFERENCES studies(study_id),
                    public_study_id TEXT NOT NULL,
                    profile TEXT NOT NULL CHECK(profile IN ('general','adult_explicit')),
                    checklist_hash TEXT NOT NULL,
                    protocol_fingerprint TEXT NOT NULL,
                    sampling_config_fingerprint TEXT NOT NULL,
                    semantic_config_fingerprint TEXT NOT NULL,
                    semantic_evidence_fingerprint TEXT NOT NULL,
                    used_source_set_fingerprint TEXT NOT NULL,
                    candidate_bundle_fingerprint TEXT NOT NULL,
                    candidate_artifact_fingerprint TEXT,
                    craft_pack_fingerprint TEXT,
                    receipt_fingerprint TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL CHECK(state IN ('complete','invalidated')),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE INDEX IF NOT EXISTS source_versions_sha_idx ON source_versions(sha256);
                CREATE INDEX IF NOT EXISTS source_files_version_idx ON source_files(version_id, available);
                CREATE INDEX IF NOT EXISTS study_works_version_idx ON study_works(version_id);
                CREATE INDEX IF NOT EXISTS range_jobs_study_idx ON range_jobs(study_id, work_id);

                CREATE TRIGGER IF NOT EXISTS immutable_confirmed_checklist
                BEFORE UPDATE OF checklist_hash ON studies
                WHEN OLD.checklist_hash IS NOT NULL
                     AND NOT (NEW.checklist_hash IS OLD.checklist_hash)
                BEGIN
                    SELECT RAISE(ABORT, 'confirmed_checklist_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_confirmed_membership_update
                BEFORE UPDATE OF work_id, version_id, ordinal ON study_works
                WHEN (SELECT checklist_hash FROM studies WHERE study_id=OLD.study_id) IS NOT NULL
                     AND (NEW.work_id != OLD.work_id OR NEW.version_id != OLD.version_id OR NEW.ordinal != OLD.ordinal)
                BEGIN
                    SELECT RAISE(ABORT, 'confirmed_membership_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_confirmed_membership_delete
                BEFORE DELETE ON study_works
                WHEN (SELECT checklist_hash FROM studies WHERE study_id=OLD.study_id) IS NOT NULL
                BEGIN
                    SELECT RAISE(ABORT, 'confirmed_membership_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_confirmed_membership_insert
                BEFORE INSERT ON study_works
                WHEN (SELECT checklist_hash FROM studies WHERE study_id=NEW.study_id) IS NOT NULL
                BEGIN
                    SELECT RAISE(ABORT, 'confirmed_membership_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_range_job_locator
                BEFORE UPDATE OF study_id,work_id,version_id,scope,range_start,range_end,
                                 source_fingerprint,passage_fingerprint,rubric_json,job_fingerprint
                ON range_jobs
                BEGIN
                    SELECT RAISE(ABORT, 'range_job_locator_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_semantic_completion_receipt
                BEFORE UPDATE OF receipt_id,study_id,run_id,public_study_id,profile,
                                 checklist_hash,range_job_count,work_synthesis_count,
                                 benchmark_job_fingerprint,benchmark_result_fingerprint,
                                 candidate_bundle_fingerprint,receipt_fingerprint
                ON semantic_completion_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'semantic_completion_receipt_immutable');
                END;

                """
            )
            study_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(studies)")
            }
            if "profile" not in study_columns:
                connection.execute(
                    "ALTER TABLE studies ADD COLUMN profile TEXT NOT NULL DEFAULT 'general' "
                    "CHECK(profile IN ('general','adult_explicit'))"
                )
            connection.execute(
                "CREATE TRIGGER IF NOT EXISTS immutable_confirmed_profile "
                "BEFORE UPDATE OF profile ON studies "
                "WHEN OLD.checklist_hash IS NOT NULL AND NEW.profile != OLD.profile "
                "BEGIN SELECT RAISE(ABORT, 'confirmed_profile_immutable'); END"
            )
            style_receipt_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(style_completion_receipts)"
                )
            }
            for column in (
                "semantic_config_fingerprint",
                "semantic_evidence_fingerprint",
                "used_source_set_fingerprint",
            ):
                if column not in style_receipt_columns:
                    # SQLite cannot add a required column to a non-empty legacy
                    # table without fabricating a value.  Keep the migration
                    # truthful: legacy receipts receive NULL and are invalidated
                    # below, while every new Library write requires a real
                    # runner-bound sha256 value.
                    connection.execute(
                        f"ALTER TABLE style_completion_receipts ADD COLUMN {column} TEXT"
                    )
            connection.execute(
                "UPDATE style_completion_receipts SET state='invalidated' "
                "WHERE semantic_config_fingerprint IS NULL "
                "OR length(semantic_config_fingerprint) != 71 "
                "OR substr(semantic_config_fingerprint,1,7) != 'sha256:' "
                "OR substr(semantic_config_fingerprint,8) GLOB '*[^0-9a-f]*' "
                "OR semantic_evidence_fingerprint IS NULL "
                "OR length(semantic_evidence_fingerprint) != 71 "
                "OR substr(semantic_evidence_fingerprint,1,7) != 'sha256:' "
                "OR substr(semantic_evidence_fingerprint,8) GLOB '*[^0-9a-f]*' "
                "OR used_source_set_fingerprint IS NULL "
                "OR length(used_source_set_fingerprint) != 71 "
                "OR substr(used_source_set_fingerprint,1,7) != 'sha256:' "
                "OR substr(used_source_set_fingerprint,8) GLOB '*[^0-9a-f]*'"
            )
            # Recreate rather than CREATE IF NOT EXISTS so databases carrying
            # the previous trigger cannot leave the new evidence bindings
            # mutable after migration.
            connection.execute(
                "DROP TRIGGER IF EXISTS immutable_style_completion_receipt"
            )
            connection.execute(
                "CREATE TRIGGER immutable_style_completion_receipt "
                "BEFORE UPDATE OF receipt_id,style_run_id,study_id,public_study_id,profile,"
                "checklist_hash,protocol_fingerprint,sampling_config_fingerprint,"
                "semantic_config_fingerprint,semantic_evidence_fingerprint,"
                "used_source_set_fingerprint,"
                "candidate_bundle_fingerprint,candidate_artifact_fingerprint,"
                "craft_pack_fingerprint,receipt_fingerprint "
                "ON style_completion_receipts "
                "BEGIN SELECT RAISE(ABORT, 'style_completion_receipt_immutable'); END"
            )

    # ------------------------------------------------------------------
    # Safe source access
    # ------------------------------------------------------------------
    @staticmethod
    def _inside(root: Path, candidate: Path) -> bool:
        try:
            return os.path.commonpath((str(root), str(candidate))) == str(root)
        except (OSError, ValueError):
            return False

    def _read_stable_bytes(self, path: Path, *, limit: int = MAX_SOURCE_BYTES) -> bytes:
        if path.is_symlink():
            raise CorpusLibraryError("source_symlink_rejected")
        try:
            before = path.stat()
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        if not stat.S_ISREG(before.st_mode):
            raise CorpusLibraryError("source_not_regular_file")
        if before.st_size > limit:
            raise CorpusLibraryError("source_size_limit")
        try:
            with path.open("rb") as stream:
                data = stream.read(limit + 1)
            after = path.stat()
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        if len(data) > limit:
            raise CorpusLibraryError("source_size_limit")
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after:
            raise CorpusLibraryError("source_changed_during_read")
        return data

    def _hash_stable_file(
        self, path: Path, *, limit: int = MAX_SOURCE_BYTES
    ) -> tuple[str, int]:
        """Hash one regular file in chunks without retaining its bytes."""

        if path.is_symlink():
            raise CorpusLibraryError("source_symlink_rejected")
        try:
            before = path.stat()
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        if not stat.S_ISREG(before.st_mode):
            raise CorpusLibraryError("source_not_regular_file")
        if before.st_size > limit:
            raise CorpusLibraryError("source_size_limit")
        digest = hashlib.sha256()
        observed = 0
        try:
            with path.open("rb") as stream:
                while True:
                    chunk = stream.read(256 * 1024)
                    if not chunk:
                        break
                    observed += len(chunk)
                    if observed > limit:
                        raise CorpusLibraryError("source_size_limit")
                    digest.update(chunk)
            after = path.stat()
        except CorpusLibraryError:
            raise
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after or observed != before.st_size:
            raise CorpusLibraryError("source_changed_during_read")
        return digest.hexdigest(), observed

    @staticmethod
    def _txt_stream_encoding_candidates(path: Path) -> tuple[str, ...]:
        try:
            with path.open("rb") as stream:
                prefix = stream.read(4)
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        if prefix.startswith(b"\xef\xbb\xbf"):
            return ("utf-8-sig",)
        if prefix.startswith((b"\xff\xfe", b"\xfe\xff")):
            return ("utf-16",)
        return ("utf-8", "gb18030", "big5")

    def _iter_stable_decoded_txt(
        self,
        path: Path,
        *,
        encoding: str,
        expected_sha256: str,
    ) -> Iterable[str]:
        """Strictly decode one stable TXT while simultaneously binding raw SHA-256."""

        if path.is_symlink():
            raise CorpusLibraryError("source_symlink_rejected")
        try:
            before = path.stat()
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        if not stat.S_ISREG(before.st_mode):
            raise CorpusLibraryError("source_not_regular_file")
        if before.st_size > MAX_SOURCE_BYTES:
            raise CorpusLibraryError("source_size_limit")
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        digest = hashlib.sha256()
        observed = 0
        try:
            with path.open("rb") as stream:
                while True:
                    raw = stream.read(256 * 1024)
                    if not raw:
                        break
                    observed += len(raw)
                    if observed > MAX_SOURCE_BYTES:
                        raise CorpusLibraryError("source_size_limit")
                    digest.update(raw)
                    decoded = decoder.decode(raw, final=False)
                    if decoded:
                        yield decoded
                final = decoder.decode(b"", final=True)
                if final:
                    yield final
            after = path.stat()
        except UnicodeDecodeError as exc:
            raise CorpusLibraryError("txt_decode_failed") from exc
        except CorpusLibraryError:
            raise
        except OSError as exc:
            raise CorpusLibraryError("source_unavailable") from exc
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after or observed != before.st_size:
            raise CorpusLibraryError("source_changed_during_read")
        if digest.hexdigest() != expected_sha256:
            raise CorpusLibraryError("style_source_dependency_mismatch")

    def _iter_normalized_stable_txt(
        self,
        path: Path,
        *,
        encoding: str,
        expected_sha256: str,
    ) -> Iterable[str]:
        return _iter_normalized_text_chunks(
            self._iter_stable_decoded_txt(
                path, encoding=encoding, expected_sha256=expected_sha256
            )
        )

    @staticmethod
    def _decode_txt(data: bytes) -> str:
        candidates: list[str]
        if data.startswith(b"\xef\xbb\xbf"):
            candidates = ["utf-8-sig"]
        elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
            candidates = ["utf-16"]
        else:
            candidates = ["utf-8", "gb18030", "big5"]
        for encoding in candidates:
            try:
                return _normalize_text(data.decode(encoding, errors="strict"))
            except UnicodeDecodeError:
                continue
        raise CorpusLibraryError("txt_decode_failed")

    @staticmethod
    def _safe_epub_name(name: str) -> str:
        if not name or "\x00" in name or "\\" in name:
            raise CorpusLibraryError("epub_unsafe_member_path")
        if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
            raise CorpusLibraryError("epub_unsafe_member_path")
        parts = PurePosixPath(name).parts
        if any(part in {"", ".", ".."} for part in parts):
            raise CorpusLibraryError("epub_unsafe_member_path")
        normalized = posixpath.normpath(name)
        if normalized.startswith("../") or normalized == "..":
            raise CorpusLibraryError("epub_unsafe_member_path")
        return normalized

    @staticmethod
    def _safe_xml(data: bytes, error_code: str) -> ET.Element:
        decoded = _decode_xml_bytes(data, error_code)
        decoded = _strip_safe_doctype(decoded)
        try:
            return ET.fromstring(decoded)
        except (ET.ParseError, ValueError) as exc:
            raise CorpusLibraryError(error_code) from exc

    def _decode_epub(self, data: bytes) -> tuple[str, dict[str, str]]:
        import io

        try:
            archive = zipfile.ZipFile(io.BytesIO(data), "r")
        except (OSError, zipfile.BadZipFile) as exc:
            raise CorpusLibraryError("epub_invalid_zip") from exc
        with archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_EPUB_ENTRIES:
                raise CorpusLibraryError("epub_entry_limit")
            names: dict[str, zipfile.ZipInfo] = {}
            folded_names: set[str] = set()
            total_expanded = 0
            for info in infos:
                safe_name = self._safe_epub_name(info.filename)
                folded = safe_name.casefold()
                if safe_name in names or folded in folded_names:
                    raise CorpusLibraryError("epub_duplicate_member")
                names[safe_name] = info
                folded_names.add(folded)
                if info.flag_bits & 0x1:
                    raise CorpusLibraryError("epub_encrypted_member")
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and stat.S_ISLNK(mode):
                    raise CorpusLibraryError("epub_symlink_member")
                if info.file_size > MAX_EPUB_MEMBER_BYTES:
                    raise CorpusLibraryError("epub_member_size_limit")
                total_expanded += info.file_size
                if total_expanded > MAX_EPUB_EXPANDED_BYTES:
                    raise CorpusLibraryError("epub_expanded_size_limit")
                if info.compress_size == 0 and info.file_size > 0:
                    raise CorpusLibraryError("epub_compression_ratio_limit")
                if info.compress_size and info.file_size / info.compress_size > 250:
                    raise CorpusLibraryError("epub_compression_ratio_limit")

            def member(name: str) -> bytes:
                safe_name = self._safe_epub_name(name)
                info = names.get(safe_name)
                if info is None:
                    raise CorpusLibraryError("epub_required_member_missing")
                try:
                    value = archive.read(info)
                except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                    raise CorpusLibraryError("epub_member_read_failed") from exc
                if len(value) != info.file_size or len(value) > MAX_EPUB_MEMBER_BYTES:
                    raise CorpusLibraryError("epub_member_size_mismatch")
                return value

            container = self._safe_xml(
                member("META-INF/container.xml"), "epub_container_invalid"
            )
            rootfile_path = ""
            for element in container.iter():
                if _local_name(element.tag) == "rootfile":
                    rootfile_path = str(element.attrib.get("full-path") or "").strip()
                    if rootfile_path:
                        break
            opf_path = self._safe_epub_name(rootfile_path)
            opf_root = self._safe_xml(member(opf_path), "epub_package_invalid")
            opf_dir = posixpath.dirname(opf_path)

            metadata: dict[str, str] = {}
            for element in opf_root.iter():
                local = _local_name(element.tag)
                if local in {"identifier", "title", "creator", "language"} and element.text:
                    normalized = _normalize_text(element.text)
                    if normalized and local not in metadata:
                        metadata[local] = normalized[:1_000]

            manifest: dict[str, tuple[str, str]] = {}
            spine: list[str] = []
            for element in opf_root.iter():
                local = _local_name(element.tag)
                if local == "item":
                    item_id = str(element.attrib.get("id") or "").strip()
                    href = str(element.attrib.get("href") or "").split("#", 1)[0].strip()
                    media_type = str(element.attrib.get("media-type") or "").strip().casefold()
                    if item_id and href:
                        joined = self._safe_epub_name(posixpath.normpath(posixpath.join(opf_dir, href)))
                        manifest[item_id] = (joined, media_type)
                elif local == "itemref":
                    idref = str(element.attrib.get("idref") or "").strip()
                    if idref:
                        spine.append(idref)
            if not spine:
                raise CorpusLibraryError("epub_spine_missing")

            chapters: list[str] = []
            total_chars = 0
            for idref in spine:
                item = manifest.get(idref)
                if item is None:
                    raise CorpusLibraryError("epub_spine_item_missing")
                chapter_path, media_type = item
                if media_type not in {"application/xhtml+xml", "text/html", ""}:
                    continue
                raw = member(chapter_path)
                try:
                    decoded = raw.decode("utf-8-sig", errors="strict")
                except UnicodeDecodeError:
                    try:
                        decoded = raw.decode("utf-16", errors="strict")
                    except UnicodeDecodeError as exc:
                        raise CorpusLibraryError("epub_chapter_decode_failed") from exc
                decoded = _strip_safe_doctype(decoded)
                parser = _BodyTextExtractor()
                try:
                    parser.feed(decoded)
                    parser.close()
                except (UnicodeError, ValueError) as exc:
                    raise CorpusLibraryError("epub_chapter_parse_failed") from exc
                chapter = parser.text()
                if chapter:
                    total_chars += len(chapter)
                    if total_chars > MAX_EPUB_TEXT_CHARS:
                        raise CorpusLibraryError("epub_text_size_limit")
                    chapters.append(chapter)
            if not chapters:
                raise CorpusLibraryError("epub_text_missing")
            return _normalize_text("\n\n".join(chapters)), metadata

    def _extract_document(self, path: Path) -> tuple[bytes, str, dict[str, str], str]:
        data = self._read_stable_bytes(path)
        suffix = path.suffix.casefold()
        if suffix == ".txt":
            text = self._decode_txt(data)
            metadata = {"title": path.stem[:1_000]}
            media_type = "txt"
        elif suffix == ".epub":
            text, metadata = self._decode_epub(data)
            if metadata.get("title"):
                metadata["title_source"] = "embedded"
            media_type = "epub"
        else:
            raise CorpusLibraryError("unsupported_source_type")
        return data, text, metadata, media_type

    # ------------------------------------------------------------------
    # Collection scan and dependency invalidation
    # ------------------------------------------------------------------
    def scan_collection(
        self,
        collection: str | Path,
        *,
        collection_id: str | None = None,
        rights_class: str = "analysis_only",
        rights_basis: str = "caller_declared_authorized_copy_for_analysis",
        language: str | None = None,
        recursive: bool = True,
    ) -> dict[str, Any]:
        root = Path(collection).expanduser().resolve()
        if not root.is_dir():
            raise CorpusLibraryError("collection_not_found")
        if root.is_symlink():
            raise CorpusLibraryError("collection_symlink_rejected")
        if rights_class not in {"redistributable", "analysis_only", "unknown"}:
            raise CorpusLibraryError("invalid_rights_class")
        rights_basis = str(rights_basis or "").strip()
        if not rights_basis:
            raise CorpusLibraryError("rights_basis_required")
        if collection_id is not None:
            collection_id = _safe_identifier(collection_id, "collection_id")
        root_text = str(root)
        scan_token = uuid.uuid4().hex
        patterns: Iterable[Path]
        patterns = root.rglob("*") if recursive else root.glob("*")
        candidates: list[Path] = []
        for candidate in patterns:
            if candidate.suffix.casefold() not in {".txt", ".epub"}:
                continue
            if candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if self._inside(root, resolved):
                candidates.append(resolved)
        candidates.sort(key=lambda item: item.relative_to(root).as_posix().casefold())

        new_works = new_versions = unchanged_versions = refreshed_versions = rejected = 0
        invalidated: set[str] = set()
        error_counts: dict[str, int] = {}
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM collections WHERE root_path=?", (root_text,)
            ).fetchone()
            if existing is not None:
                if collection_id is not None and collection_id != existing["collection_id"]:
                    raise CorpusLibraryError("collection_identity_conflict")
                collection_id = existing["collection_id"]
                connection.execute(
                    "UPDATE collections SET rights_class=?, rights_basis=?, language=?, "
                    "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE collection_id=?",
                    (rights_class, rights_basis, language, collection_id),
                )
                if existing["rights_class"] != "unknown" and rights_class == "unknown":
                    affected = connection.execute(
                        "SELECT DISTINCT s.study_id FROM studies s "
                        "JOIN study_works sw ON sw.study_id=s.study_id "
                        "JOIN logical_works w ON w.work_id=sw.work_id "
                        "WHERE w.collection_id=? AND s.state!='invalidated'",
                        (collection_id,),
                    ).fetchall()
                    for affected_study in affected:
                        self._invalidate_study(
                            connection,
                            affected_study["study_id"],
                            "rights_class_no_longer_eligible",
                        )
                        invalidated.add(affected_study["study_id"])
            else:
                collection_id = collection_id or _random_id("COL")
                connection.execute(
                    "INSERT INTO collections(collection_id,root_path,rights_class,rights_basis,language) "
                    "VALUES(?,?,?,?,?)",
                    (collection_id, root_text, rights_class, rights_basis, language),
                )

            for path in candidates:
                relative_path = path.relative_to(root).as_posix()
                digest = ""
                text = ""
                metadata: dict[str, str] = {}
                media_type = path.suffix.casefold().lstrip(".")
                parse_state = "ok"
                error_code: str | None = None
                try:
                    raw, text, metadata, media_type = self._extract_document(path)
                    digest = hashlib.sha256(raw).hexdigest()
                except CorpusLibraryError as exc:
                    parse_state = "error"
                    error_code = exc.code
                    rejected += 1
                    error_counts[error_code] = error_counts.get(error_code, 0) + 1
                    try:
                        raw = self._read_stable_bytes(path)
                        digest = hashlib.sha256(raw).hexdigest()
                    except CorpusLibraryError:
                        # A file that cannot be stably read is not entered as a
                        # version.  No partial prose or exception text is kept.
                        continue
                private_metadata = {
                    key: str(value)[:1_000]
                    for key, value in metadata.items()
                    if key in {
                        "identifier", "title", "title_source", "creator", "language"
                    }
                    and value
                }
                private_metadata_json = json.dumps(
                    private_metadata, ensure_ascii=False, sort_keys=True
                )

                file_row = connection.execute(
                    "SELECT * FROM source_files WHERE collection_id=? AND relative_path=?",
                    (collection_id, relative_path),
                ).fetchone()
                work_row: sqlite3.Row | None = None
                if file_row is not None:
                    work_row = connection.execute(
                        "SELECT * FROM logical_works WHERE work_id=?", (file_row["work_id"],)
                    ).fetchone()
                    previous_digest = connection.execute(
                        "SELECT sha256 FROM source_versions WHERE version_id=?",
                        (file_row["version_id"],),
                    ).fetchone()
                    alias_exists = connection.execute(
                        "SELECT 1 FROM source_files WHERE work_id=? AND file_id<>? AND available=1 LIMIT 1",
                        (file_row["work_id"], file_row["file_id"]),
                    ).fetchone()
                    if (
                        previous_digest is not None
                        and previous_digest["sha256"] != digest
                        and alias_exists is not None
                    ):
                        # An exact-copy alias that later diverges becomes a new
                        # logical work; it must not silently replace the shared
                        # work or erase the still-present original version.
                        work_row = None
                else:
                    # Identical copies within a collection are aliases of one
                    # logical work and therefore cannot pad a 120-work study.
                    work_row = connection.execute(
                        "SELECT w.* FROM logical_works w JOIN source_versions v ON v.work_id=w.work_id "
                        "WHERE w.collection_id=? AND v.sha256=? ORDER BY w.created_at LIMIT 1",
                        (collection_id, digest),
                    ).fetchone()
                if work_row is None:
                    work_id = _random_id("WORK")
                    public_work_id = _random_id("PW")
                    logical_key = hashlib.sha256(
                        (collection_id + "\0" + relative_path.casefold()).encode("utf-8")
                    ).hexdigest()
                    connection.execute(
                        "INSERT INTO logical_works(work_id,collection_id,public_work_id,logical_key) "
                        "VALUES(?,?,?,?)",
                        (work_id, collection_id, public_work_id, logical_key),
                    )
                    work_row = connection.execute(
                        "SELECT * FROM logical_works WHERE work_id=?", (work_id,)
                    ).fetchone()
                    new_works += 1
                work_id = work_row["work_id"]

                version_row = connection.execute(
                    "SELECT * FROM source_versions WHERE work_id=? AND sha256=?",
                    (work_id, digest),
                ).fetchone()
                if version_row is None:
                    previous_version_id = work_row["active_version_id"]
                    next_number = connection.execute(
                        "SELECT COALESCE(MAX(version_number),0)+1 FROM source_versions WHERE work_id=?",
                        (work_id,),
                    ).fetchone()[0]
                    version_id = _random_id("VER")
                    connection.execute(
                        "INSERT INTO source_versions(version_id,work_id,version_number,sha256,media_type,"
                        "char_count,parse_state,error_code,private_metadata_json,available) "
                        "VALUES(?,?,?,?,?,?,?,?,?,1)",
                        (
                            version_id, work_id, next_number, digest, media_type, len(text),
                            parse_state, error_code,
                            private_metadata_json,
                        ),
                    )
                    connection.execute(
                        "UPDATE logical_works SET active_version_id=? WHERE work_id=?",
                        (version_id, work_id),
                    )
                    new_versions += 1
                    if previous_version_id and previous_version_id != version_id:
                        invalidated.update(
                            self._invalidate_version_dependency(
                                connection, previous_version_id, "source_version_changed"
                            )
                        )
                else:
                    version_id = version_row["version_id"]
                    unchanged_versions += 1
                    canonical_locator_row = connection.execute(
                        "SELECT relative_path FROM source_files WHERE version_id=? AND available=1 "
                        "ORDER BY relative_path LIMIT 1",
                        (version_id,),
                    ).fetchone()
                    canonical_same_locator = (
                        file_row is not None
                        and file_row["version_id"] == version_id
                        and canonical_locator_row is not None
                        and canonical_locator_row["relative_path"] == relative_path
                    )
                    core_derivation_changed = (
                        version_row["media_type"] != media_type
                        or int(version_row["char_count"]) != len(text)
                        or version_row["parse_state"] != parse_state
                        or version_row["error_code"] != error_code
                    )
                    metadata_changed = (
                        version_row["private_metadata_json"] != private_metadata_json
                    )
                    if core_derivation_changed or (
                        canonical_same_locator and metadata_changed
                    ):
                        refreshed_versions += 1
                        connection.execute(
                            "UPDATE source_versions SET media_type=?,char_count=?,parse_state=?,"
                            "error_code=?,private_metadata_json=?,available=1 WHERE version_id=?",
                            (
                                media_type,
                                len(text),
                                parse_state,
                                error_code,
                                private_metadata_json,
                                version_id,
                            ),
                        )
                        invalidated.update(
                            self._invalidate_version_dependency(
                                connection, version_id, "source_parse_derivation_changed"
                            )
                        )
                    if work_row["active_version_id"] != version_id:
                        previous_version_id = work_row["active_version_id"]
                        connection.execute(
                            "UPDATE logical_works SET active_version_id=? WHERE work_id=?",
                            (version_id, work_id),
                        )
                        if previous_version_id:
                            invalidated.update(
                                self._invalidate_version_dependency(
                                    connection, previous_version_id, "source_version_changed"
                                )
                            )
                    connection.execute(
                        "UPDATE source_versions SET available=1 WHERE version_id=?", (version_id,)
                    )

                if file_row is None:
                    connection.execute(
                        "INSERT INTO source_files(file_id,collection_id,relative_path,work_id,version_id,"
                        "available,last_seen_token) VALUES(?,?,?,?,?,1,?)",
                        (_random_id("FILE"), collection_id, relative_path, work_id, version_id, scan_token),
                    )
                else:
                    connection.execute(
                        "UPDATE source_files SET work_id=?,version_id=?,available=1,last_seen_token=? "
                        "WHERE file_id=?",
                        (work_id, version_id, scan_token, file_row["file_id"]),
                    )

            formerly_available = {
                row["version_id"]
                for row in connection.execute(
                    "SELECT DISTINCT version_id FROM source_files WHERE collection_id=? "
                    "AND available=1 AND last_seen_token<>?",
                    (collection_id, scan_token),
                )
            }
            connection.execute(
                "UPDATE source_files SET available=0 WHERE collection_id=? AND last_seen_token<>?",
                (collection_id, scan_token),
            )
            for version_id in formerly_available:
                remaining = connection.execute(
                    "SELECT 1 FROM source_files WHERE version_id=? AND available=1 LIMIT 1",
                    (version_id,),
                ).fetchone()
                if remaining is None:
                    connection.execute(
                        "UPDATE source_versions SET available=0 WHERE version_id=?", (version_id,)
                    )
                    invalidated.update(
                        self._invalidate_version_dependency(
                            connection, version_id, "source_file_unavailable"
                        )
                    )

            logical_count = connection.execute(
                "SELECT COUNT(*) FROM logical_works WHERE collection_id=?", (collection_id,)
            ).fetchone()[0]

        return {
            "schema": "quillframe_corpus_scan_v1",
            "status": "completed",
            "collection_id": collection_id,
            "files_seen": len(candidates),
            "logical_works": logical_count,
            "new_logical_works": new_works,
            "new_versions": new_versions,
            "unchanged_versions": unchanged_versions,
            "refreshed_versions": refreshed_versions,
            "rejected_files": rejected,
            "error_counts": dict(sorted(error_counts.items())),
            "invalidated_studies": len(invalidated),
            "rights_class": rights_class,
            "raw_text_persisted": False,
        }

    def _invalidate_version_dependency(
        self, connection: sqlite3.Connection, version_id: str, reason: str
    ) -> set[str]:
        rows = connection.execute(
            "SELECT DISTINCT s.study_id,s.state,s.checklist_hash,"
            "(SELECT COUNT(*) FROM study_works member WHERE member.study_id=s.study_id) AS member_count "
            "FROM studies s JOIN study_works sw ON sw.study_id=s.study_id "
            "WHERE sw.version_id=? AND s.state!='invalidated'",
            (version_id,),
        ).fetchall()
        # A complete, still-unconfirmed proposal is a mutable review draft:
        # source drift must make it refreshable, not destroy its identity.
        # Confirmed/running/completed studies remain fail-closed, while an
        # incomplete or malformed proposed dependency is still invalidated.
        study_ids = {
            row["study_id"]
            for row in rows
            if not (
                row["state"] == "proposed"
                and row["checklist_hash"] is None
                and row["member_count"] == STUDY_SIZE
            )
        }
        if not study_ids:
            return set()
        placeholders = ",".join("?" for _ in study_ids)
        parameters = (reason, *sorted(study_ids))
        connection.execute(
            f"UPDATE studies SET state='invalidated',invalidation_reason=?,"
            f"updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
            f"WHERE study_id IN ({placeholders})",
            parameters,
        )
        connection.execute(
            f"UPDATE study_works SET state='invalidated' WHERE version_id=? "
            f"AND study_id IN ({placeholders})",
            (version_id, *sorted(study_ids)),
        )
        connection.execute(
            f"UPDATE releases SET state='invalidated',invalidation_reason=? "
            f"WHERE study_id IN ({placeholders})",
            parameters,
        )
        connection.execute(
            f"UPDATE range_jobs SET state='invalidated' WHERE version_id=? "
            f"AND study_id IN ({placeholders}) AND state!='invalidated'",
            (version_id, *sorted(study_ids)),
        )
        connection.execute(
            f"UPDATE semantic_completion_receipts SET state='invalidated' "
            f"WHERE study_id IN ({placeholders}) AND state!='invalidated'",
            tuple(sorted(study_ids)),
        )
        return study_ids

    # ------------------------------------------------------------------
    # Fixed 120-work study lifecycle
    # ------------------------------------------------------------------
    def _selection_pool(
        self,
        connection: sqlite3.Connection,
        collection_id: str | None,
        profile: str,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Build a private, profile-safe pool with one representative per title family."""

        params: list[Any] = []
        collection_clause = ""
        if collection_id is not None:
            collection_clause = "AND w.collection_id=?"
            params.append(collection_id)
        rows = connection.execute(
            "SELECT w.work_id,w.public_work_id,w.active_version_id,w.collection_id,"
            "c.rights_class,v.version_number,v.sha256,v.media_type,v.char_count,"
            "v.parse_state,v.error_code,v.private_metadata_json,v.available "
            "FROM logical_works w JOIN collections c ON c.collection_id=w.collection_id "
            "LEFT JOIN source_versions v ON v.version_id=w.active_version_id "
            f"WHERE 1=1 {collection_clause}",
            params,
        ).fetchall()
        locator_params: list[Any] = []
        locator_collection_clause = ""
        if collection_id is not None:
            locator_collection_clause = "AND f.collection_id=?"
            locator_params.append(collection_id)
        locator_rows = connection.execute(
            "SELECT f.version_id,f.relative_path FROM source_files f "
            "WHERE f.available=1 "
            f"{locator_collection_clause} ORDER BY f.version_id,f.relative_path",
            locator_params,
        ).fetchall()
        locators_by_version: dict[str, list[str]] = {}
        for locator_row in locator_rows:
            locators_by_version.setdefault(locator_row["version_id"], []).append(
                locator_row["relative_path"]
            )
        exclusions = {
            "source_ineligible": 0,
            "identity_unknown": 0,
            "alias_identity_conflict": 0,
            "below_minimum_chars": 0,
            "strong_adult_profile_mismatch": 0,
            "not_strong_adult_profile_mismatch": 0,
            "ambiguous_profile": 0,
            "derivative_ambiguous": 0,
            "creator_conflict_ambiguous": 0,
            "logical_family_alternate": 0,
        }
        families: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if (
                row["rights_class"] not in {"analysis_only", "redistributable"}
                or row["active_version_id"] is None
                or row["parse_state"] != "ok"
                or not row["available"]
            ):
                exclusions["source_ineligible"] += 1
                continue
            locators = locators_by_version.get(row["active_version_id"], [])
            if not locators:
                exclusions["source_ineligible"] += 1
                continue
            try:
                metadata = json.loads(row["private_metadata_json"] or "{}")
            except (TypeError, ValueError):
                metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            metadata_title = str(metadata.get("title") or "").strip()
            locator_titles = [PurePosixPath(locator).stem for locator in locators]
            is_epub = row["media_type"] == "epub"
            embedded_title = (
                metadata_title
                if is_epub and metadata.get("title_source") == "embedded"
                else ""
            )
            identity_values = [
                value
                for value in (
                    ([embedded_title] if embedded_title else [])
                    + locator_titles
                )
                if value
            ]
            if any(_DERIVATIVE_TITLE_RE.search(value) for value in identity_values):
                exclusions["derivative_ambiguous"] += 1
                continue
            family_key = _private_title_family(embedded_title) if embedded_title else None
            if family_key is None:
                locator_family_keys = [
                    _private_title_family(locator_title)
                    for locator_title in locator_titles
                ]
                valid_locator_keys = {
                    key for key in locator_family_keys if key is not None
                }
                if not valid_locator_keys:
                    exclusions["identity_unknown"] += 1
                    continue
                if (
                    len(valid_locator_keys) != 1
                    or any(key is None for key in locator_family_keys)
                ):
                    exclusions["alias_identity_conflict"] += 1
                    continue
                family_key = next(iter(valid_locator_keys))
            item = {
                "work_id": row["work_id"],
                "public_work_id": row["public_work_id"],
                "active_version_id": row["active_version_id"],
                "version_number": row["version_number"],
                "sha256": row["sha256"],
                "char_count": row["char_count"],
                "media_type": row["media_type"],
                "family_key": family_key,
                "profile_signal": _private_profile_signal(identity_values),
                "creator_keys": _private_creator_keys(
                    metadata.get("creator") if is_epub else None,
                    identity_values,
                ),
                "metadata_quality": (
                    int(bool(embedded_title))
                    + int(is_epub and bool(metadata.get("creator")))
                ),
            }
            families.setdefault(family_key, []).append(item)

        eligible: list[dict[str, Any]] = []
        for family_key in sorted(families):
            members = families[family_key]
            creator_keys = set().union(
                *(member["creator_keys"] for member in members)
            )
            if len(creator_keys) > 1:
                exclusions["creator_conflict_ambiguous"] += len(members)
                continue
            signals = {str(member["profile_signal"]) for member in members}
            if "ambiguous" in signals or len(signals) != 1:
                exclusions["ambiguous_profile"] += len(members)
                continue
            family_signal = next(iter(signals))
            if profile == "general" and family_signal != "general":
                exclusions["strong_adult_profile_mismatch"] += len(members)
                continue
            if profile == "adult_explicit" and family_signal != "adult_explicit":
                exclusions["not_strong_adult_profile_mismatch"] += len(members)
                continue
            profile_members: list[dict[str, Any]] = []
            for member in members:
                if profile == "general" and int(member["char_count"]) < GENERAL_MIN_CHARS:
                    exclusions["below_minimum_chars"] += 1
                else:
                    profile_members.append(member)
            if not profile_members:
                continue
            ranked = sorted(
                profile_members,
                key=lambda member: (
                    -int(member["char_count"]),
                    -int(member["version_number"]),
                    -int(member["metadata_quality"]),
                    str(member["public_work_id"]),
                ),
            )
            eligible.append(ranked[0])
            exclusions["logical_family_alternate"] += len(ranked) - 1
        return eligible, exclusions

    def propose_selection(
        self,
        study_id: str | None = None,
        *,
        collection_id: str | None = None,
        seed: str | int | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        study_id = _safe_identifier(study_id, "study_id") if study_id else _random_id("STUDY")
        if profile is None:
            raise CorpusLibraryError("study_profile_required")
        if profile not in {"general", "adult_explicit"}:
            raise CorpusLibraryError("study_profile_invalid")
        if collection_id is not None:
            collection_id = _safe_identifier(collection_id, "collection_id")
        seed_text = str(seed) if seed is not None else uuid.uuid4().hex
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM studies WHERE study_id=? OR public_study_id=?",
                (study_id, study_id),
            ).fetchone()
            if existing is not None:
                if existing["profile"] != profile:
                    raise CorpusLibraryError("study_profile_conflict")
                _current_pool, exclusion_counts = self._selection_pool(
                    connection, existing["collection_id"], profile
                )
                replay = self._study_status(connection, existing["study_id"], include_works=True)
                replay["exclusion_counts"] = exclusion_counts
                return replay
            if collection_id is not None and connection.execute(
                "SELECT 1 FROM collections WHERE collection_id=?", (collection_id,)
            ).fetchone() is None:
                raise CorpusLibraryError("collection_not_found")
            eligible, exclusion_counts = self._selection_pool(
                connection, collection_id, profile
            )
            if len(eligible) < STUDY_SIZE:
                return {
                    "schema": "quillframe_corpus_selection_v1",
                    "status": "insufficient_eligible_works",
                    "required": STUDY_SIZE,
                    "eligible": len(eligible),
                    "profile": profile,
                    "exclusion_counts": exclusion_counts,
                    "study_created": False,
                }
            ranked = _rank_selection_pool(eligible, seed_text)
            proposal_hash = _selection_fingerprint(profile, ranked)
            public_study_id = _random_id("PS")
            connection.execute(
                "INSERT INTO studies(study_id,public_study_id,collection_id,profile,state,seed,proposal_hash) "
                "VALUES(?,?,?,?,'proposed',?,?)",
                (study_id, public_study_id, collection_id, profile, seed_text, proposal_hash),
            )
            connection.executemany(
                "INSERT INTO study_works(study_id,work_id,version_id,ordinal,state) "
                "VALUES(?,?,?,?, 'pending')",
                [
                    (study_id, row["work_id"], row["active_version_id"], ordinal)
                    for ordinal, row in enumerate(ranked, 1)
                ],
            )
            result = self._study_status(connection, study_id, include_works=True)
            result["exclusion_counts"] = exclusion_counts
            return result

    def refresh_proposed_selection(
        self,
        study_id: str,
        *,
        expected_proposal_hash: str,
    ) -> dict[str, Any]:
        """Atomically rerank an unconfirmed proposal without changing its identity.

        This is intentionally narrower than invalidation/rebuild.  It exists
        for a still-human-reviewed proposal whose eligibility rules or scanned
        source versions changed before confirmation.  Confirmed membership is
        protected by the existing SQLite triggers and can never use this path.
        """

        study_id = _safe_identifier(study_id, "study_id")
        if not _HASH_RE.fullmatch(str(expected_proposal_hash or "")):
            raise CorpusLibraryError("selection_refresh_hash_invalid")
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] != "proposed" or study["checklist_hash"] is not None:
                raise CorpusLibraryError("selection_refresh_requires_unconfirmed_proposal")
            if study["proposal_hash"] != expected_proposal_hash:
                raise CorpusLibraryError("selection_refresh_hash_mismatch")

            # A proposal must not already own analysis evidence.  Check each
            # table only when it exists so older databases remain readable.
            for table, column in (
                ("range_jobs", "study_id"),
                ("study_runs", "study_id"),
                ("style_analysis_runs", "study_id"),
                ("semantic_completion_receipts", "study_id"),
                ("style_completion_receipts", "study_id"),
            ):
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if exists and connection.execute(
                    f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1", (study["study_id"],)
                ).fetchone():
                    raise CorpusLibraryError("selection_refresh_analysis_dependency_exists")

            eligible, exclusion_counts = self._selection_pool(
                connection, study["collection_id"], study["profile"]
            )
            if len(eligible) < STUDY_SIZE:
                return {
                    "schema": "quillframe_corpus_selection_refresh_v1",
                    "status": "insufficient_eligible_works",
                    "study_id": study["study_id"],
                    "public_study_id": study["public_study_id"],
                    "profile": study["profile"],
                    "required": STUDY_SIZE,
                    "eligible": len(eligible),
                    "proposal_hash": study["proposal_hash"],
                    "previous_proposal_hash": study["proposal_hash"],
                    "membership_changed": False,
                    "exclusion_counts": exclusion_counts,
                    "study_refreshed": False,
                }
            ranked = _rank_selection_pool(eligible, study["seed"])
            proposal_hash = _selection_fingerprint(study["profile"], ranked)
            before = [
                (row["work_id"], row["version_id"])
                for row in connection.execute(
                    "SELECT work_id,version_id FROM study_works WHERE study_id=? ORDER BY ordinal",
                    (study["study_id"],),
                )
            ]
            after = [(row["work_id"], row["active_version_id"]) for row in ranked]
            if len(after) != STUDY_SIZE or len({work_id for work_id, _ in after}) != STUDY_SIZE:
                raise CorpusLibraryError("selection_refresh_cardinality_invalid")

            connection.execute("DELETE FROM study_works WHERE study_id=?", (study["study_id"],))
            connection.executemany(
                "INSERT INTO study_works(study_id,work_id,version_id,ordinal,state) "
                "VALUES(?,?,?,?, 'pending')",
                [
                    (study["study_id"], row["work_id"], row["active_version_id"], ordinal)
                    for ordinal, row in enumerate(ranked, 1)
                ],
            )
            connection.execute(
                "UPDATE studies SET proposal_hash=?,invalidation_reason=NULL,"
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE study_id=?",
                (proposal_hash, study["study_id"]),
            )
            result = self._study_status(connection, study["study_id"], include_works=True)
            result.update(
                {
                    "schema": "quillframe_corpus_selection_refresh_v1",
                    "previous_proposal_hash": expected_proposal_hash,
                    "membership_changed": before != after,
                    "exclusion_counts": exclusion_counts,
                    "study_refreshed": True,
                    "identity_preserved": True,
                }
            )
            return result

    def confirm_selection(
        self,
        study_id: str,
        *,
        expected_hash: str | None = None,
        proposal_hash: str | None = None,
    ) -> dict[str, Any]:
        if expected_hash is None and proposal_hash is None:
            raise CorpusLibraryError("selection_confirmation_hash_required")
        if expected_hash is not None and proposal_hash is not None and expected_hash != proposal_hash:
            raise CorpusLibraryError("selection_confirmation_hash_conflict")
        expected = expected_hash if expected_hash is not None else proposal_hash
        if not _HASH_RE.fullmatch(str(expected or "")):
            raise CorpusLibraryError("selection_confirmation_hash_invalid")
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] == "invalidated":
                raise CorpusLibraryError("study_invalidated")
            if study["checklist_hash"] is not None:
                if expected != study["checklist_hash"]:
                    raise CorpusLibraryError("selection_hash_mismatch")
                return self._study_status(connection, study["study_id"], include_works=True)
            if study["state"] != "proposed":
                raise CorpusLibraryError("study_not_proposed")
            if expected != study["proposal_hash"]:
                raise CorpusLibraryError("selection_hash_mismatch")
            membership = connection.execute(
                "SELECT sw.*,w.public_work_id,w.active_version_id,v.version_number,v.sha256,"
                "v.parse_state,v.available "
                "FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                "JOIN source_versions v ON v.version_id=sw.version_id "
                "WHERE sw.study_id=? ORDER BY sw.ordinal",
                (study["study_id"],),
            ).fetchall()
            if len(membership) != STUDY_SIZE or len({row["work_id"] for row in membership}) != STUDY_SIZE:
                self._invalidate_study(connection, study["study_id"], "selection_cardinality_changed")
                connection.commit()
                raise CorpusLibraryError("selection_cardinality_invalid")
            current_membership_hash = _selection_fingerprint(
                study["profile"], membership
            )
            if current_membership_hash != study["proposal_hash"]:
                self._invalidate_study(
                    connection,
                    study["study_id"],
                    "selection_membership_hash_changed",
                )
                connection.commit()
                raise CorpusLibraryError("selection_membership_hash_changed")
            current_pool, _exclusion_counts = self._selection_pool(
                connection, study["collection_id"], study["profile"]
            )
            current_ranked = _rank_selection_pool(current_pool, study["seed"])
            membership_pairs = [
                (row["work_id"], row["version_id"]) for row in membership
            ]
            ranked_pairs = [
                (row["work_id"], row["active_version_id"])
                for row in current_ranked
            ]
            if ranked_pairs != membership_pairs:
                self._invalidate_study(
                    connection, study["study_id"], "selection_pool_changed"
                )
                connection.commit()
                raise CorpusLibraryError("selection_pool_changed")
            for row in membership:
                if (
                    row["active_version_id"] != row["version_id"]
                    or row["parse_state"] != "ok"
                    or not row["available"]
                ):
                    self._invalidate_study(connection, study["study_id"], "selection_dependency_changed")
                    connection.commit()
                    raise CorpusLibraryError("selection_dependency_changed")
            connection.execute(
                "UPDATE study_works SET state='selected' WHERE study_id=?", (study["study_id"],)
            )
            # Membership is updated before checklist_hash because the database
            # trigger freezes work/version/ordinal as soon as this is non-null.
            connection.execute(
                "UPDATE studies SET state='confirmed',checklist_hash=proposal_hash,"
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE study_id=?",
                (study["study_id"],),
            )
            return self._study_status(connection, study["study_id"], include_works=True)

    def _find_study(self, connection: sqlite3.Connection, identifier: str) -> sqlite3.Row:
        identifier = str(identifier or "").strip()
        row = connection.execute(
            "SELECT * FROM studies WHERE study_id=? OR public_study_id=?",
            (identifier, identifier),
        ).fetchone()
        if row is None:
            release = connection.execute(
                "SELECT study_id FROM releases WHERE release_id=?", (identifier,)
            ).fetchone()
            if release is not None:
                row = connection.execute(
                    "SELECT * FROM studies WHERE study_id=?", (release["study_id"],)
                ).fetchone()
        if row is None:
            raise CorpusLibraryError("study_not_found")
        return row

    def _study_status(
        self, connection: sqlite3.Connection, study_id: str, *, include_works: bool
    ) -> dict[str, Any]:
        study = self._find_study(connection, study_id)
        counts = {
            row["state"]: row["amount"]
            for row in connection.execute(
                "SELECT state,COUNT(*) AS amount FROM study_works WHERE study_id=? GROUP BY state",
                (study["study_id"],),
            )
        }
        result: dict[str, Any] = {
            "schema": "quillframe_corpus_study_status_v1",
            "study_id": study["study_id"],
            "public_study_id": study["public_study_id"],
            "profile": study["profile"],
            "status": study["state"],
            "required_works": STUDY_SIZE,
            "work_count": sum(counts.values()),
            "work_states": {key: counts.get(key, 0) for key in ("pending", "selected", "studied", "invalidated")},
            "proposal_hash": study["proposal_hash"],
            "checklist_hash": study["checklist_hash"],
            "checklist_locked": study["checklist_hash"] is not None,
            "raw_text_persisted": False,
        }
        if study["invalidation_reason"]:
            result["invalidation_reason"] = study["invalidation_reason"]
        if include_works:
            result["works"] = [
                {
                    "public_work_id": row["public_work_id"],
                    "ordinal": row["ordinal"],
                    "source_version": row["version_number"],
                    "status": row["state"],
                }
                for row in connection.execute(
                    "SELECT w.public_work_id,sw.ordinal,v.version_number,sw.state "
                    "FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                    "JOIN source_versions v ON v.version_id=sw.version_id "
                    "WHERE sw.study_id=? ORDER BY sw.ordinal",
                    (study["study_id"],),
                )
            ]
        return result

    def study_status(self, study_id: str, *, include_works: bool = True) -> dict[str, Any]:
        with self._connect() as connection:
            return self._study_status(connection, study_id, include_works=include_works)

    def selection_private_preview(self, study_id: str) -> dict[str, Any]:
        """Show the exact local checklist for human confirmation, never export it."""

        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            rows = connection.execute(
                "SELECT sw.ordinal,w.public_work_id,v.version_number,v.media_type,"
                "v.private_metadata_json,"
                "(SELECT f.relative_path FROM source_files f WHERE f.version_id=v.version_id "
                " AND f.available=1 ORDER BY f.relative_path LIMIT 1) AS relative_locator "
                "FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                "JOIN source_versions v ON v.version_id=sw.version_id "
                "WHERE sw.study_id=? ORDER BY sw.ordinal",
                (study["study_id"],),
            ).fetchall()
            works: list[dict[str, Any]] = []
            for row in rows:
                try:
                    metadata = json.loads(row["private_metadata_json"])
                except (TypeError, json.JSONDecodeError):
                    metadata = {}
                title = str(metadata.get("title") or "").strip() if isinstance(metadata, dict) else ""
                creator = str(metadata.get("creator") or "").strip() if isinstance(metadata, dict) else ""
                locator = str(row["relative_locator"] or "")
                locator_label = PurePosixPath(locator).stem if locator else ""
                embedded_title = (
                    title
                    if row["media_type"] == "epub"
                    and isinstance(metadata, dict)
                    and metadata.get("title_source") == "embedded"
                    else ""
                )
                display_label = (
                    (embedded_title or locator_label)
                    if row["media_type"] == "epub"
                    else locator_label
                ) or row["public_work_id"]
                item = {
                    "ordinal": row["ordinal"],
                    "public_work_id": row["public_work_id"],
                    "display_label": display_label,
                    "relative_locator": locator,
                    "media_type": row["media_type"],
                    "source_version": row["version_number"],
                }
                if creator:
                    item["creator"] = creator
                works.append(item)
            return {
                "schema": "quillframe_corpus_selection_private_preview_v1",
                "study_id": study["study_id"],
                "public_study_id": study["public_study_id"],
                "profile": study["profile"],
                "status": study["state"],
                "proposal_hash": study["proposal_hash"],
                "checklist_hash": study["checklist_hash"],
                "work_count": len(works),
                "works": works,
                "private_local_only": True,
                "redistributable": False,
                "raw_text_included": False,
            }

    def start_study(self, study_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] in {"confirmed", "paused"}:
                if not self._verify_study_dependencies(connection, study["study_id"]):
                    raise CorpusLibraryError("source_dependency_mismatch")
                connection.execute(
                    "UPDATE studies SET state='running',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                    "WHERE study_id=?",
                    (study["study_id"],),
                )
            elif study["state"] not in {"running", "complete"}:
                raise CorpusLibraryError("study_not_startable")
            return self._study_status(connection, study["study_id"], include_works=False)

    def resume_study(self, study_id: str) -> dict[str, Any]:
        return self.start_study(study_id)

    def pause_study(self, study_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] == "running":
                connection.execute(
                    "UPDATE studies SET state='paused',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                    "WHERE study_id=?",
                    (study["study_id"],),
                )
            elif study["state"] != "paused":
                raise CorpusLibraryError("study_not_pauseable")
            return self._study_status(connection, study["study_id"], include_works=False)

    def cancel_study(self, study_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] != "invalidated":
                self._invalidate_study(connection, study["study_id"], "cancelled_by_caller")
            return self._study_status(connection, study["study_id"], include_works=False)

    def _invalidate_study(
        self, connection: sqlite3.Connection, study_id: str, reason: str
    ) -> None:
        connection.execute(
            "UPDATE studies SET state='invalidated',invalidation_reason=?,"
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE study_id=?",
            (reason, study_id),
        )
        connection.execute(
            "UPDATE study_works SET state='invalidated' WHERE study_id=? AND state!='invalidated'",
            (study_id,),
        )
        connection.execute(
            "UPDATE releases SET state='invalidated',invalidation_reason=? WHERE study_id=?",
            (reason, study_id),
        )
        connection.execute(
            "UPDATE range_jobs SET state='invalidated' WHERE study_id=? AND state!='invalidated'",
            (study_id,),
        )
        connection.execute(
            "UPDATE semantic_completion_receipts SET state='invalidated' "
            "WHERE study_id=? AND state!='invalidated'",
            (study_id,),
        )

    # ------------------------------------------------------------------
    # Transient three-window analysis (never persisted as prose)
    # ------------------------------------------------------------------
    def _bound_source(
        self, connection: sqlite3.Connection, study_identifier: str, public_work_id: str
    ) -> tuple[sqlite3.Row, sqlite3.Row, Path]:
        study, row, candidates = self._bound_source_candidates(
            connection, study_identifier, public_work_id
        )
        for candidate in candidates:
            try:
                data = self._read_stable_bytes(candidate)
            except CorpusLibraryError:
                continue
            if hashlib.sha256(data).hexdigest() == row["sha256"]:
                return study, row, candidate
        self._invalidate_version_dependency(connection, row["version_id"], "source_dependency_mismatch")
        connection.commit()
        raise CorpusLibraryError("source_dependency_mismatch")

    def _bound_source_candidates(
        self, connection: sqlite3.Connection, study_identifier: str, public_work_id: str
    ) -> tuple[sqlite3.Row, sqlite3.Row, list[Path]]:
        """Resolve safe bound locators without materializing any source bytes."""

        study = self._find_study(connection, study_identifier)
        if study["state"] == "invalidated":
            raise CorpusLibraryError("study_invalidated")
        row = connection.execute(
            "SELECT sw.*,w.public_work_id,w.collection_id,w.active_version_id,"
            "v.sha256,v.version_number,v.parse_state,"
            "v.available,v.char_count,v.media_type,c.root_path FROM study_works sw "
            "JOIN logical_works w ON w.work_id=sw.work_id "
            "JOIN source_versions v ON v.version_id=sw.version_id "
            "JOIN collections c ON c.collection_id=w.collection_id "
            "WHERE sw.study_id=? AND w.public_work_id=?",
            (study["study_id"], public_work_id),
        ).fetchone()
        if row is None:
            raise CorpusLibraryError("study_work_not_found")
        if (
            row["active_version_id"] != row["version_id"]
            or row["parse_state"] != "ok"
            or not bool(row["available"])
        ):
            self._invalidate_version_dependency(
                connection, row["version_id"], "source_dependency_mismatch"
            )
            connection.commit()
            raise CorpusLibraryError("style_source_not_current")
        paths = connection.execute(
            "SELECT relative_path FROM source_files WHERE version_id=? AND available=1 ORDER BY relative_path",
            (row["version_id"],),
        ).fetchall()
        root = Path(row["root_path"]).resolve()
        candidates: list[Path] = []
        for path_row in paths:
            entry = root / path_row["relative_path"]
            candidate = entry.resolve()
            if (
                not entry.is_symlink()
                and candidate == entry
                and self._inside(root, candidate)
                and candidate.is_file()
                and not candidate.is_symlink()
            ):
                candidates.append(candidate)
        if not candidates:
            self._invalidate_version_dependency(
                connection, row["version_id"], "source_dependency_mismatch"
            )
            connection.commit()
            raise CorpusLibraryError("source_dependency_mismatch")
        return study, row, candidates

    @staticmethod
    def _three_ranges(length: int, budget: int) -> list[tuple[int, int]]:
        allocations = [budget // 3, budget // 3, budget // 3]
        for index in range(budget % 3):
            allocations[index] += 1
        if length <= budget:
            # Partition the whole short work into three ordered windows.
            first = math.ceil(length / 3)
            second = math.ceil((length - first) / 2)
            return [(0, first), (first, first + second), (first + second, length)]
        starts = [
            0,
            max(allocations[0], (length - allocations[1]) // 2),
            length - allocations[2],
        ]
        if starts[1] + allocations[1] > starts[2]:
            starts[1] = max(allocations[0], starts[2] - allocations[1])
        return [(start, start + amount) for start, amount in zip(starts, allocations)]

    def materialize_windows(
        self,
        study_id: str,
        public_work_id: str,
        *,
        max_chars: int = MAX_WINDOW_CHARS,
    ) -> dict[str, Any]:
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 3 <= max_chars <= MAX_WINDOW_CHARS:
            raise CorpusLibraryError("window_budget_invalid")
        with self._connect() as connection:
            study, row, path = self._bound_source(connection, study_id, public_work_id)
            raw, text, _metadata, _media_type = self._extract_document(path)
            if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                self._invalidate_version_dependency(connection, row["version_id"], "source_dependency_mismatch")
                connection.commit()
                raise CorpusLibraryError("source_dependency_mismatch")
            budget = min(max_chars, len(text))
            ranges = self._three_ranges(len(text), budget)
            labels = ("opening", "middle", "closing")
            windows = [
                {"scope": label, "start": start, "end": end, "text": text[start:end]}
                for label, (start, end) in zip(labels, ranges)
            ]
            return {
                "schema": "quillframe_corpus_transient_windows_v1",
                "public_study_id": study["public_study_id"],
                "public_work_id": row["public_work_id"],
                "source_version": row["version_number"],
                "windows": windows,
                "total_chars": sum(len(window["text"]) for window in windows),
                "max_chars": max_chars,
                "window_count": 3,
                "persisted": False,
            }

    materialize_ranges = materialize_windows

    # ------------------------------------------------------------------
    # Transient chapter/scene-aware style sampling (never persists prose)
    # ------------------------------------------------------------------
    def sample_style_work(
        self,
        study_id: str,
        public_work_id: str,
        *,
        requested_roles: Iterable[str],
        max_windows: int = 6,
        prior_manifest: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sample one exact bound work and return only call-scoped prose.

        The sampler binds its manifest to the decoded full-text fingerprint.
        The independent ``upstream_source_fingerprint`` binds the same call to
        the immutable raw-byte source version in this library (important for
        EPUB, where container bytes and decoded prose intentionally differ).
        """

        from corpus.style_sampling import (
            MAX_SOURCE_CHARS as STYLE_IN_MEMORY_SOURCE_CHARS,
            StyleSamplingError,
            fingerprint_source_text,
            sample_style_chunks,
            sample_style_windows,
            style_window_passes_hygiene,
        )

        roles = tuple(requested_roles)
        with self._connect() as connection:
            study, row, candidates = self._bound_source_candidates(
                connection, study_id, public_work_id
            )
            if row["media_type"] == "txt":
                result: dict[str, Any] | None = None
                last_error: CorpusLibraryError | None = None
                for path in candidates:
                    for encoding in self._txt_stream_encoding_candidates(path):
                        try:
                            result = sample_style_chunks(
                                self._iter_normalized_stable_txt(
                                    path,
                                    encoding=encoding,
                                    expected_sha256=row["sha256"],
                                ),
                                requested_roles=roles,
                                max_windows=max_windows,
                                max_window_chars=1800,
                                prior_manifest=prior_manifest,
                                candidate_filter=style_window_passes_hygiene,
                            )
                            break
                        except CorpusLibraryError as exc:
                            last_error = exc
                            if exc.code != "txt_decode_failed":
                                break
                        except StyleSamplingError as exc:
                            raise CorpusLibraryError(exc.code) from exc
                    if result is not None:
                        break
                if result is None:
                    if last_error is not None and last_error.code in {
                        "style_source_dependency_mismatch",
                        "source_changed_during_read",
                        "source_unavailable",
                    }:
                        self._invalidate_version_dependency(
                            connection,
                            row["version_id"],
                            "style_source_dependency_mismatch",
                        )
                        connection.commit()
                        raise CorpusLibraryError(
                            "style_source_dependency_mismatch"
                        ) from last_error
                    raise last_error or CorpusLibraryError("txt_decode_failed")
                upstream_fingerprint = "sha256:" + row["sha256"]
                text_fingerprint = result["manifest"]["source_binding"][
                    "source_fingerprint"
                ]
            else:
                if int(row["char_count"]) > STYLE_IN_MEMORY_SOURCE_CHARS:
                    raise CorpusLibraryError("style_large_source_type_unsupported")
                study, row, path = self._bound_source(
                    connection, study_id, public_work_id
                )
                raw, text, _metadata, _media_type = self._extract_document(path)
                upstream_fingerprint = "sha256:" + hashlib.sha256(raw).hexdigest()
                if upstream_fingerprint != "sha256:" + row["sha256"]:
                    self._invalidate_version_dependency(
                        connection, row["version_id"], "style_source_dependency_mismatch"
                    )
                    connection.commit()
                    raise CorpusLibraryError("style_source_dependency_mismatch")
                text_fingerprint = fingerprint_source_text(text)
                result = sample_style_windows(
                    text,
                    source_fingerprint=text_fingerprint,
                    requested_roles=roles,
                    max_windows=max_windows,
                    max_window_chars=1800,
                    prior_manifest=prior_manifest,
                    candidate_filter=style_window_passes_hygiene,
                )
            return {
                **result,
                "public_study_id": study["public_study_id"],
                "public_work_id": row["public_work_id"],
                "source_version": row["version_number"],
                "upstream_source_fingerprint": upstream_fingerprint,
                "decoded_text_fingerprint": text_fingerprint,
                "passages_persisted": False,
            }

    @staticmethod
    def _style_paragraph_spans(passage: str, style_range_id: str) -> list[dict[str, Any]]:
        spans: list[dict[str, Any]] = []
        for index, match in enumerate(re.finditer(r"[^\n]+(?:\n+|$)", passage), 1):
            start, end = match.span()
            while end > start and passage[end - 1] == "\n":
                end -= 1
            while start < end and passage[start].isspace():
                start += 1
            while end > start and passage[end - 1].isspace():
                end -= 1
            if start < end:
                spans.append(
                    {
                        "span_ref": f"SPAN-{hashlib.sha256((style_range_id + ':' + str(index)).encode('utf-8')).hexdigest()[:24]}",
                        "start": start,
                        "end": end,
                    }
                )
        if not spans:
            spans = [{"span_ref": f"SPAN-{hashlib.sha256(style_range_id.encode('utf-8')).hexdigest()[:24]}",
                      "start": 0, "end": len(passage)}]
        return spans[:64]

    def materialize_style_window(
        self,
        study_id: str,
        public_work_id: str,
        descriptor: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Reopen one source-free sampler descriptor and return transient prose."""

        from corpus.style_sampling import (
            MAX_SOURCE_CHARS as STYLE_IN_MEMORY_SOURCE_CHARS,
            StyleSamplingError,
            fingerprint_source_text,
            materialize_style_chunk_span,
            style_window_passes_hygiene,
        )

        if not isinstance(descriptor, Mapping):
            raise CorpusLibraryError("style_window_descriptor_invalid")
        expected = {
            "window_id", "span", "role", "candidate_roles", "functional_layers",
            "passage_fingerprint", "unicode_chars", "chapter_ordinal", "scene_ordinal",
            "paragraph_start_ordinal", "paragraph_end_ordinal", "source_fingerprint",
            "upstream_source_fingerprint",
        }
        if set(descriptor) != expected:
            raise CorpusLibraryError("style_window_descriptor_not_closed")
        span = descriptor.get("span")
        if not isinstance(span, Mapping) or set(span) != {"start", "end"}:
            raise CorpusLibraryError("style_window_span_invalid")
        start, end = span.get("start"), span.get("end")
        if (
            isinstance(start, bool) or not isinstance(start, int) or start < 0
            or isinstance(end, bool) or not isinstance(end, int) or end <= start
            or end - start > 1800
        ):
            raise CorpusLibraryError("style_window_span_invalid")
        with self._connect() as connection:
            _study, row, candidates = self._bound_source_candidates(
                connection, study_id, public_work_id
            )
            if row["media_type"] == "txt":
                rebound: Mapping[str, Any] | None = None
                last_error: Exception | None = None
                for path in candidates:
                    for encoding in self._txt_stream_encoding_candidates(path):
                        try:
                            rebound = materialize_style_chunk_span(
                                self._iter_normalized_stable_txt(
                                    path,
                                    encoding=encoding,
                                    expected_sha256=row["sha256"],
                                ),
                                source_fingerprint=descriptor["source_fingerprint"],
                                start=start,
                                end=end,
                                passage_fingerprint=descriptor[
                                    "passage_fingerprint"
                                ],
                            )
                            break
                        except CorpusLibraryError as exc:
                            last_error = exc
                            if exc.code != "txt_decode_failed":
                                break
                        except StyleSamplingError as exc:
                            raise CorpusLibraryError(exc.code) from exc
                    if rebound is not None:
                        break
                if rebound is None:
                    if isinstance(last_error, CorpusLibraryError) and last_error.code in {
                        "style_source_dependency_mismatch",
                        "source_changed_during_read",
                        "source_unavailable",
                    }:
                        self._invalidate_version_dependency(
                            connection,
                            row["version_id"],
                            "style_source_dependency_mismatch",
                        )
                        connection.commit()
                        raise CorpusLibraryError(
                            "style_source_dependency_mismatch"
                        ) from last_error
                    if last_error is not None:
                        raise last_error
                    raise CorpusLibraryError("txt_decode_failed")
                upstream = "sha256:" + row["sha256"]
                decoded = str(rebound["source_fingerprint"])
                passage = str(rebound["passage"])
            else:
                if int(row["char_count"]) > STYLE_IN_MEMORY_SOURCE_CHARS:
                    raise CorpusLibraryError("style_large_source_type_unsupported")
                _study, row, path = self._bound_source(
                    connection, study_id, public_work_id
                )
                raw, text, _metadata, _media_type = self._extract_document(path)
                upstream = "sha256:" + hashlib.sha256(raw).hexdigest()
                if (
                    upstream != descriptor["upstream_source_fingerprint"]
                    or upstream != "sha256:" + row["sha256"]
                ):
                    self._invalidate_version_dependency(
                        connection,
                        row["version_id"],
                        "style_source_dependency_mismatch",
                    )
                    connection.commit()
                    raise CorpusLibraryError("style_source_dependency_mismatch")
                decoded = fingerprint_source_text(text)
                if decoded != descriptor["source_fingerprint"] or end > len(text):
                    raise CorpusLibraryError("style_window_source_binding_mismatch")
                passage = text[start:end]
                if (
                    fingerprint_source_text(passage)
                    != descriptor["passage_fingerprint"]
                    or len(passage) != descriptor["unicode_chars"]
                ):
                    raise CorpusLibraryError("style_window_passage_binding_mismatch")
            if upstream != descriptor["upstream_source_fingerprint"]:
                raise CorpusLibraryError("style_source_dependency_mismatch")
            if len(passage) != descriptor["unicode_chars"]:
                raise CorpusLibraryError("style_window_passage_binding_mismatch")
            if not style_window_passes_hygiene(passage):
                raise CorpusLibraryError("style_window_hygiene_rejected")
            style_range_id = "STYLE-" + hashlib.sha256(
                _canonical_bytes(
                    {"study": study_id, "work": public_work_id, "window": descriptor["window_id"]}
                )
            ).hexdigest()[:32]
            return {
                "schema": "quillframe_corpus_ephemeral_style_window_v1",
                "window_id": descriptor["window_id"],
                "passage": passage,
                "paragraph_spans": self._style_paragraph_spans(passage, style_range_id),
                "source_fingerprint": decoded,
                "upstream_source_fingerprint": upstream,
                "passage_fingerprint": descriptor["passage_fingerprint"],
                "persisted": False,
            }

    def verify_style_source_dependency(
        self,
        study_id: str,
        public_work_id: str,
        *,
        version_id: str,
        source_sha256: str,
    ) -> dict[str, Any]:
        """Re-open one bound source through the stable-read path without prose output."""

        study_id = _safe_identifier(study_id, "study_id")
        public_work_id = _safe_identifier(public_work_id, "public_work_id")
        version_id = _safe_identifier(version_id, "version_id")
        if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise CorpusLibraryError("style_source_dependency_fingerprint_invalid")
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] == "invalidated":
                raise CorpusLibraryError("study_invalidated")
            bound = connection.execute(
                "SELECT sw.version_id,w.work_id,v.sha256,c.root_path FROM study_works sw "
                "JOIN logical_works w ON w.work_id=sw.work_id "
                "JOIN source_versions v ON v.version_id=sw.version_id "
                "JOIN collections c ON c.collection_id=w.collection_id "
                "WHERE sw.study_id=? AND w.public_work_id=?",
                (study["study_id"], public_work_id),
            ).fetchone()
            if (
                bound is None
                or bound["version_id"] != version_id
                or bound["sha256"] != source_sha256
            ):
                raise CorpusLibraryError("style_source_dependency_binding_mismatch")
            paths = connection.execute(
                "SELECT relative_path FROM source_files WHERE version_id=? AND work_id=? "
                "AND available=1 ORDER BY relative_path",
                (version_id, bound["work_id"]),
            ).fetchall()
            root = Path(bound["root_path"]).resolve()
        actual: str | None = None
        for path_row in paths:
            entry = root / path_row["relative_path"]
            candidate = entry.resolve()
            if (
                entry.is_symlink()
                or candidate != entry
                or not self._inside(root, candidate)
                or not candidate.is_file()
            ):
                continue
            try:
                digest, _size = self._hash_stable_file(candidate)
            except CorpusLibraryError:
                continue
            if digest == source_sha256:
                actual = digest
                break
        if actual is None:
            raise CorpusLibraryError("style_source_dependency_drift")
        return {
            "schema": "quillframe_corpus_style_source_dependency_receipt_v1",
            "public_work_id": public_work_id,
            "version_id": version_id,
            "source_fingerprint": "sha256:" + actual,
            "dependency_fingerprint": _fingerprint(
                {
                    "public_work_id": public_work_id,
                    "version_id": version_id,
                    "source_fingerprint": "sha256:" + actual,
                }
            ),
            "source_prose_included": False,
            "authority": False,
        }

    def style_leakage_reference_batches(
        self,
        study_id: str,
        *,
        public_work_ids: Iterable[str] | None = None,
        chunk_chars: int = 360_000,
        chunks_per_batch: int = 8,
    ) -> Iterable[dict[str, str]]:
        """Yield bounded transient source chunks for exhaustive local overlap checks."""

        if (
            isinstance(chunk_chars, bool) or not isinstance(chunk_chars, int)
            or not 10_000 <= chunk_chars <= 450_000
            or isinstance(chunks_per_batch, bool) or not isinstance(chunks_per_batch, int)
            or not 1 <= chunks_per_batch <= 10
        ):
            raise CorpusLibraryError("style_leakage_batch_config_invalid")
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            bound_work_ids = [
                row["public_work_id"] for row in connection.execute(
                    "SELECT w.public_work_id FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                    "WHERE sw.study_id=? ORDER BY sw.ordinal", (study["study_id"],)
                )
            ]
            if public_work_ids is None:
                work_ids = bound_work_ids
            else:
                requested = [_safe_identifier(value, "public_work_id") for value in public_work_ids]
                if not requested or len(requested) != len(set(requested)):
                    raise CorpusLibraryError("style_leakage_work_set_invalid")
                if not set(requested).issubset(set(bound_work_ids)):
                    raise CorpusLibraryError("style_leakage_work_set_invalid")
                work_ids = requested
        batch: dict[str, str] = {}
        overlap = 64
        for public_work_id in work_ids:
            with self._connect() as connection:
                _study, row, path = self._bound_source(connection, study_id, public_work_id)
                raw, text, _metadata, _media_type = self._extract_document(path)
                if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                    self._invalidate_version_dependency(
                        connection, row["version_id"], "style_leakage_source_mismatch"
                    )
                    connection.commit()
                    raise CorpusLibraryError("style_leakage_source_mismatch")
            start = 0
            ordinal = 1
            while start < len(text):
                end = min(len(text), start + chunk_chars)
                reference_id = f"{public_work_id}:C{ordinal:05d}"
                batch[reference_id] = text[start:end]
                if len(batch) >= chunks_per_batch:
                    yield batch
                    batch = {}
                if end == len(text):
                    break
                start = end - overlap
                ordinal += 1
        if batch:
            yield batch

    def record_style_completion(self, **receipt: Any) -> dict[str, Any]:
        """Bind a completed style graph and close the study without promotion."""

        required = {
            "schema", "style_run_id", "study_id", "public_study_id", "profile",
            "checklist_hash", "protocol_fingerprint", "sampling_config_fingerprint",
            "semantic_config_fingerprint", "semantic_evidence_fingerprint",
            "used_source_set_fingerprint",
            "candidate_bundle_fingerprint", "candidate_artifact_fingerprint",
            "craft_pack_fingerprint", "receipt_fingerprint",
        }
        if set(receipt) != required or receipt.get("schema") != "quillframe_corpus_style_completion_receipt_v1":
            raise CorpusLibraryError("style_completion_receipt_invalid")
        for key in (
            "checklist_hash", "protocol_fingerprint", "sampling_config_fingerprint",
            "semantic_config_fingerprint", "semantic_evidence_fingerprint",
            "used_source_set_fingerprint",
            "candidate_bundle_fingerprint", "receipt_fingerprint",
        ):
            if not isinstance(receipt.get(key), str) or not _HASH_RE.fullmatch(receipt[key]):
                raise CorpusLibraryError("style_completion_receipt_invalid")
        for key in ("candidate_artifact_fingerprint", "craft_pack_fingerprint"):
            if receipt.get(key) is not None and (
                not isinstance(receipt[key], str) or not _HASH_RE.fullmatch(receipt[key])
            ):
                raise CorpusLibraryError("style_completion_receipt_invalid")
        expected_fp = _fingerprint({key: receipt[key] for key in receipt if key != "receipt_fingerprint"})
        if receipt["receipt_fingerprint"] != expected_fp:
            raise CorpusLibraryError("style_completion_receipt_fingerprint_mismatch")
        with self._connect() as connection:
            study = self._find_study(connection, receipt["study_id"])
            if (
                study["public_study_id"] != receipt["public_study_id"]
                or study["profile"] != receipt["profile"]
                or study["checklist_hash"] != receipt["checklist_hash"]
            ):
                raise CorpusLibraryError("style_completion_study_binding_mismatch")
            try:
                run = connection.execute(
                    "SELECT * FROM style_analysis_runs WHERE style_run_id=? AND study_id=?",
                    (receipt["style_run_id"], study["study_id"]),
                ).fetchone()
                incomplete = connection.execute(
                    "SELECT COUNT(*) FROM style_work_steps WHERE style_run_id=? "
                    "AND activation_cycle IS NOT NULL AND state!='complete'",
                    (receipt["style_run_id"],),
                ).fetchone()[0]
                used_rows = connection.execute(
                    "SELECT public_work_id,ordinal,activation_cycle,activation_kind,state "
                    "FROM style_work_steps WHERE style_run_id=? AND activation_cycle IS NOT NULL "
                    "ORDER BY ordinal",
                    (receipt["style_run_id"],),
                ).fetchall()
                used_sources = []
                for work in used_rows:
                    source_fingerprints = [
                        row["source_fingerprint"]
                        for row in connection.execute(
                            "SELECT DISTINCT source_fingerprint FROM style_sample_steps "
                            "WHERE style_run_id=? AND public_work_id=? AND state='complete' "
                            "ORDER BY source_fingerprint",
                            (receipt["style_run_id"], work["public_work_id"]),
                        )
                    ]
                    used_sources.append({
                        "public_work_id": work["public_work_id"],
                        "ordinal": work["ordinal"],
                        "activation_cycle": work["activation_cycle"],
                        "activation_kind": work["activation_kind"],
                        "source_fingerprints": source_fingerprints,
                    })
                recomputed_used_source_set_fingerprint = _fingerprint({
                    "schema": "quillframe_style_used_source_set_v1",
                    "style_run_id": receipt["style_run_id"],
                    "used_sources": used_sources,
                })
            except sqlite3.Error as exc:
                raise CorpusLibraryError("style_completion_runner_state_unavailable") from exc
            if (
                run is None or incomplete or run["protocol_fingerprint"] != receipt["protocol_fingerprint"]
                or run["sampling_config_fingerprint"] != receipt["sampling_config_fingerprint"]
                or "semantic_config_fingerprint" not in run.keys()
                or run["semantic_config_fingerprint"] != receipt["semantic_config_fingerprint"]
                or "semantic_evidence_fingerprint" not in run.keys()
                or run["semantic_evidence_fingerprint"] != receipt["semantic_evidence_fingerprint"]
                or "used_source_set_fingerprint" not in run.keys()
                or run["used_source_set_fingerprint"] != receipt["used_source_set_fingerprint"]
                or receipt["used_source_set_fingerprint"]
                != recomputed_used_source_set_fingerprint
                or not used_rows
                or any(row["state"] != "complete" for row in used_rows)
                or any(
                    not row["source_fingerprints"]
                    or any(not _HASH_RE.fullmatch(value) for value in row["source_fingerprints"])
                    for row in used_sources
                )
            ):
                raise CorpusLibraryError("style_completion_runner_binding_mismatch")
            existing = connection.execute(
                "SELECT * FROM style_completion_receipts WHERE style_run_id=?",
                (receipt["style_run_id"],),
            ).fetchone()
            if existing is not None:
                stored_receipt = {
                    key: (
                        "quillframe_corpus_style_completion_receipt_v1"
                        if key == "schema" else existing[key]
                    )
                    for key in required
                }
                if existing["state"] != "complete" or stored_receipt != receipt:
                    raise CorpusLibraryError("style_completion_receipt_conflict")
            else:
                connection.execute(
                    "INSERT INTO style_completion_receipts(receipt_id,style_run_id,study_id,"
                    "public_study_id,profile,checklist_hash,protocol_fingerprint,sampling_config_fingerprint,"
                    "semantic_config_fingerprint,semantic_evidence_fingerprint,"
                    "used_source_set_fingerprint,"
                    "candidate_bundle_fingerprint,candidate_artifact_fingerprint,craft_pack_fingerprint,"
                    "receipt_fingerprint,state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'complete')",
                    (
                        _random_id("STYLE-RECEIPT"), receipt["style_run_id"], study["study_id"],
                        receipt["public_study_id"], receipt["profile"], receipt["checklist_hash"],
                        receipt["protocol_fingerprint"], receipt["sampling_config_fingerprint"],
                        receipt["semantic_config_fingerprint"],
                        receipt["semantic_evidence_fingerprint"],
                        receipt["used_source_set_fingerprint"],
                        receipt["candidate_bundle_fingerprint"], receipt["candidate_artifact_fingerprint"],
                        receipt["craft_pack_fingerprint"], receipt["receipt_fingerprint"],
                    ),
                )
            connection.execute(
                "UPDATE study_works SET state='studied' WHERE study_id=? AND state!='invalidated' "
                "AND work_id IN (SELECT sw.work_id FROM style_work_steps steps "
                "JOIN logical_works sw ON sw.public_work_id=steps.public_work_id "
                "WHERE steps.style_run_id=? AND steps.activation_cycle IS NOT NULL "
                "AND steps.state='complete')",
                (study["study_id"], receipt["style_run_id"]),
            )
            connection.execute(
                "UPDATE studies SET state='complete',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                "WHERE study_id=?", (study["study_id"],),
            )
        return {
            "schema": "quillframe_corpus_style_completion_receipt_v1",
            "status": "complete",
            "style_run_id": receipt["style_run_id"],
            "semantic_config_fingerprint": receipt["semantic_config_fingerprint"],
            "semantic_evidence_fingerprint": receipt["semantic_evidence_fingerprint"],
            "used_source_set_fingerprint": receipt["used_source_set_fingerprint"],
            "receipt_fingerprint": receipt["receipt_fingerprint"],
            "authority": False,
        }

    @staticmethod
    def _safe_derived_payload(value: Any, *, kind: str) -> Any:
        """Return a JSON-safe, prose-hostile derived payload.

        Range rubrics and judgments may contain numeric structure and compact
        machine labels.  Natural-language strings, suspicious field names,
        non-finite numbers, and deep/large structures are rejected before any
        durable write.  This makes a receipt useful without turning it into a
        covert excerpt store.
        """

        node_count = 0

        def visit(node: Any, depth: int) -> Any:
            nonlocal node_count
            node_count += 1
            if node_count > 512 or depth > 8:
                raise CorpusLibraryError(f"{kind}_size_limit")
            if node is None or isinstance(node, bool):
                return node
            if isinstance(node, (int, float)) and not isinstance(node, bool):
                if not math.isfinite(node) or abs(node) > 100_000_000:
                    raise CorpusLibraryError(f"{kind}_numeric_value_invalid")
                return node
            if isinstance(node, str):
                node = _normalize_text(node)
                if not node or len(node) > 2_000:
                    raise CorpusLibraryError(f"{kind}_string_invalid")
                if _PATH_LIKE_RE.search(node):
                    raise CorpusLibraryError(f"{kind}_path_forbidden")
                return node
            if isinstance(node, Mapping):
                if len(node) > 64:
                    raise CorpusLibraryError(f"{kind}_size_limit")
                result: dict[str, Any] = {}
                for raw_key, child in node.items():
                    key = str(raw_key)
                    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key):
                        raise CorpusLibraryError(f"{kind}_field_invalid")
                    if key.casefold() in _FORBIDDEN_PUBLIC_KEYS:
                        raise CorpusLibraryError(f"{kind}_text_field_forbidden")
                    result[key] = visit(child, depth + 1)
                return result
            if isinstance(node, (list, tuple)):
                if len(node) > 64:
                    raise CorpusLibraryError(f"{kind}_size_limit")
                return [visit(child, depth + 1) for child in node]
            raise CorpusLibraryError(f"{kind}_type_invalid")

        normalized = visit(value, 0)
        if len(_canonical_bytes(normalized)) > 64 * 1024:
            raise CorpusLibraryError(f"{kind}_size_limit")
        return normalized

    def prepare_ranges(
        self,
        study_id: str,
        public_work_id: str,
        *,
        rubric: Any = "quillframe_craft_numeric_v1",
        max_chars: int = MAX_WINDOW_CHARS,
    ) -> dict[str, Any]:
        """Create three durable locators/fingerprints without storing passages."""

        safe_rubric = self._safe_derived_payload(rubric, kind="rubric")
        materialized = self.materialize_windows(
            study_id, public_work_id, max_chars=max_chars
        )
        rubric_json = json.dumps(
            safe_rubric, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        receipts: list[dict[str, Any]] = []
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            bound = connection.execute(
                "SELECT sw.work_id,sw.version_id,v.sha256 FROM study_works sw "
                "JOIN logical_works w ON w.work_id=sw.work_id "
                "JOIN source_versions v ON v.version_id=sw.version_id "
                "WHERE sw.study_id=? AND w.public_work_id=?",
                (study["study_id"], public_work_id),
            ).fetchone()
            if bound is None:
                raise CorpusLibraryError("study_work_not_found")
            source_sample = _normal_overlap_text(
                "".join(window["text"] for window in materialized["windows"])
            )
            if self._payload_leaks_source(
                safe_rubric,
                source_sample,
                self._private_terms(connection, study["study_id"]),
            ):
                raise CorpusLibraryError("rubric_source_overlap")
            source_fingerprint = "sha256:" + bound["sha256"]
            for window in materialized["windows"]:
                passage_fingerprint = _fingerprint(window["text"])
                locator = {
                    "public_study_id": study["public_study_id"],
                    "public_work_id": public_work_id,
                    "source_version": materialized["source_version"],
                    "scope": window["scope"],
                    "start": window["start"],
                    "end": window["end"],
                    "source_fingerprint": source_fingerprint,
                    "passage_fingerprint": passage_fingerprint,
                    "rubric": safe_rubric,
                }
                job_fingerprint = _fingerprint(locator)
                existing = connection.execute(
                    "SELECT * FROM range_jobs WHERE job_fingerprint=?",
                    (job_fingerprint,),
                ).fetchone()
                if existing is None:
                    range_id = _random_id("RANGE")
                    connection.execute(
                        "INSERT INTO range_jobs(range_id,study_id,work_id,version_id,scope,range_start,"
                        "range_end,source_fingerprint,passage_fingerprint,rubric_json,job_fingerprint,state) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,'ready')",
                        (
                            range_id,
                            study["study_id"],
                            bound["work_id"],
                            bound["version_id"],
                            window["scope"],
                            window["start"],
                            window["end"],
                            source_fingerprint,
                            passage_fingerprint,
                            rubric_json,
                            job_fingerprint,
                        ),
                    )
                    existing = connection.execute(
                        "SELECT * FROM range_jobs WHERE range_id=?", (range_id,)
                    ).fetchone()
                receipts.append(self._range_receipt(existing, safe_rubric))
        # The transient materialized passages fall out of scope here; only the
        # receipts above were written to SQLite.
        return {
            "schema": "quillframe_corpus_ephemeral_range_batch_v1",
            "public_study_id": materialized["public_study_id"],
            "public_work_id": public_work_id,
            "range_count": 3,
            "total_chars": materialized["total_chars"],
            "ranges": receipts,
            "passages_persisted": False,
        }

    create_range_job = prepare_ranges
    prepare_range_jobs = prepare_ranges

    @staticmethod
    def _range_receipt(row: sqlite3.Row, rubric: Any | None = None) -> dict[str, Any]:
        if rubric is None:
            rubric = json.loads(row["rubric_json"])
        return {
            "schema": "quillframe_corpus_range_receipt_v1",
            "range_id": row["range_id"],
            "scope": row["scope"],
            "status": row["state"],
            "source_fingerprint": row["source_fingerprint"],
            "passage_fingerprint": row["passage_fingerprint"],
            "job_fingerprint": row["job_fingerprint"],
            "judgment_fingerprint": row["judgment_fingerprint"],
            "rubric": rubric,
            "passage_persisted": False,
        }

    def range_status(self, range_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM range_jobs WHERE range_id=?", (range_id,)
            ).fetchone()
            if row is None:
                raise CorpusLibraryError("range_not_found")
            return self._range_receipt(row)

    def materialize_range(self, range_id: str) -> dict[str, Any]:
        """Reopen and fingerprint-check one locator, returning transient prose."""

        with self._connect() as connection:
            job = connection.execute(
                "SELECT r.*,w.public_work_id,s.public_study_id FROM range_jobs r "
                "JOIN logical_works w ON w.work_id=r.work_id "
                "JOIN studies s ON s.study_id=r.study_id WHERE r.range_id=?",
                (range_id,),
            ).fetchone()
            if job is None:
                raise CorpusLibraryError("range_not_found")
            if job["state"] == "invalidated":
                raise CorpusLibraryError("range_invalidated")
            _study, bound, path = self._bound_source(
                connection, job["study_id"], job["public_work_id"]
            )
            if bound["version_id"] != job["version_id"]:
                connection.execute(
                    "UPDATE range_jobs SET state='invalidated' WHERE range_id=?", (range_id,)
                )
                connection.commit()
                raise CorpusLibraryError("range_version_mismatch")
            raw, text, _metadata, _media = self._extract_document(path)
            source_fingerprint = "sha256:" + hashlib.sha256(raw).hexdigest()
            if source_fingerprint != job["source_fingerprint"]:
                self._invalidate_version_dependency(
                    connection, job["version_id"], "range_source_fingerprint_mismatch"
                )
                connection.commit()
                raise CorpusLibraryError("range_source_fingerprint_mismatch")
            start, end = job["range_start"], job["range_end"]
            if start > len(text) or end > len(text) or end - start > MAX_WINDOW_CHARS:
                connection.execute(
                    "UPDATE range_jobs SET state='invalidated' WHERE range_id=?", (range_id,)
                )
                connection.commit()
                raise CorpusLibraryError("range_bounds_invalid")
            passage = text[start:end]
            if _fingerprint(passage) != job["passage_fingerprint"]:
                connection.execute(
                    "UPDATE range_jobs SET state='invalidated' WHERE range_id=?", (range_id,)
                )
                connection.commit()
                raise CorpusLibraryError("range_passage_fingerprint_mismatch")
            return {
                "schema": "quillframe_corpus_ephemeral_range_v1",
                "range_id": job["range_id"],
                "scope": job["scope"],
                "passage": passage,
                "char_count": len(passage),
                "source_fingerprint": job["source_fingerprint"],
                "passage_fingerprint": job["passage_fingerprint"],
                "rubric": json.loads(job["rubric_json"]),
                "persisted": False,
            }

    @staticmethod
    def _derived_strings(value: Any) -> list[str]:
        strings: list[str] = []
        if isinstance(value, Mapping):
            for child in value.values():
                strings.extend(CorpusLibrary._derived_strings(child))
        elif isinstance(value, (list, tuple)):
            for child in value:
                strings.extend(CorpusLibrary._derived_strings(child))
        elif isinstance(value, str):
            strings.append(value)
        return strings

    @classmethod
    def _payload_leaks_source(
        cls, value: Any, normalized_source: str, private_terms: set[str]
    ) -> bool:
        normalized_strings = [
            _normal_overlap_text(item) for item in cls._derived_strings(value)
        ]
        normalized_strings = [item for item in normalized_strings if item]
        for candidate in normalized_strings:
            if (
                2 <= len(candidate) < 12
                and candidate in normalized_source
                and candidate not in _DERIVED_SHORT_ENUMS
            ):
                return True
            if len(candidate) >= 12 and candidate in normalized_source:
                return True
            # A longer derived sentence can still contain a short copied span.
            # Check the minimum protected window rather than only the whole
            # candidate (or a 24-character window), so embedded 12–23 character
            # source phrases fail closed as well.
            if len(candidate) >= 12 and any(
                candidate[index : index + 12] in normalized_source
                for index in range(0, len(candidate) - 11)
            ):
                return True
            if any(
                len(term) >= 3 and (term in candidate or candidate in term)
                for term in private_terms
                if len(candidate) >= 3
            ):
                return True
        concatenated = "".join(normalized_strings)
        if len(concatenated) >= 24 and any(
            concatenated[index : index + 24] in normalized_source
            for index in range(0, len(concatenated) - 23)
        ):
            return True
        return False

    def complete_range(self, range_id: str, judgment: Any) -> dict[str, Any]:
        """Persist only a leak-checked derived judgment, never the passage."""

        safe_judgment = self._safe_derived_payload(judgment, kind="judgment")
        transient = self.materialize_range(range_id)
        passage_normalized = _normal_overlap_text(transient["passage"])
        judgment_json = json.dumps(
            safe_judgment, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        judgment_fingerprint = _fingerprint(safe_judgment)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM range_jobs WHERE range_id=?", (range_id,)
            ).fetchone()
            if row is None:
                raise CorpusLibraryError("range_not_found")
            if row["state"] == "complete":
                if row["judgment_fingerprint"] != judgment_fingerprint:
                    raise CorpusLibraryError("range_judgment_conflict")
                return self._range_receipt(row)
            if row["state"] != "ready":
                raise CorpusLibraryError("range_not_ready")
            # Re-check private metadata labels in addition to source-passage
            # overlap.  The stored judgment may only contain safe tokens, but
            # an accidental title/creator token is still blocked.
            private_terms = self._private_terms(connection, row["study_id"])
            if self._payload_leaks_source(
                safe_judgment, passage_normalized, private_terms
            ):
                raise CorpusLibraryError("judgment_source_overlap")
            connection.execute(
                "UPDATE range_jobs SET state='complete',judgment_json=?,judgment_fingerprint=?,"
                "completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE range_id=?",
                (judgment_json, judgment_fingerprint, range_id),
            )
            updated = connection.execute(
                "SELECT * FROM range_jobs WHERE range_id=?", (range_id,)
            ).fetchone()
            return self._range_receipt(updated)

    complete_range_job = complete_range

    def invoke_range(self, range_id: str, callback: Any) -> dict[str, Any]:
        """Optional caller-owned model hook; only its derived result is stored."""

        if not callable(callback):
            raise CorpusLibraryError("range_callback_not_callable")
        transient = self.materialize_range(range_id)
        try:
            judgment = callback(
                {
                    "range_id": transient["range_id"],
                    "scope": transient["scope"],
                    "passage": transient["passage"],
                    "rubric": transient["rubric"],
                }
            )
        finally:
            # Make the intended lifetime explicit.  Python does not promise an
            # immediate memory wipe, but no durable layer receives this value.
            transient = None
        return self.complete_range(range_id, judgment)

    @staticmethod
    def _metrics_for_text(text: str) -> dict[str, int]:
        length = len(text)
        paragraphs = [part for part in re.split(r"\n+", text) if part.strip()]
        sentences = [part for part in re.split(r"[。！？!?…]+", text) if part.strip()]
        dialogue_chars = sum(1 for character in text if character in "“”‘’\"『』「」")
        punctuation = sum(1 for character in text if unicodedata.category(character).startswith("P"))
        visible = [character for character in text if not character.isspace()]
        return {
            "sampled_chars": length,
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "mean_sentence_chars_milli": round(length * 1_000 / max(1, len(sentences))),
            "dialogue_char_ratio_ppm": round(dialogue_chars * 1_000_000 / max(1, length)),
            "unique_char_ratio_ppm": round(len(set(visible)) * 1_000_000 / max(1, len(visible))),
            "punctuation_ratio_ppm": round(punctuation * 1_000_000 / max(1, length)),
        }

    @staticmethod
    def _validate_metrics(metrics: Mapping[str, Any]) -> dict[str, int | float]:
        if set(metrics) != set(METRIC_KEYS):
            raise CorpusLibraryError("metrics_schema_invalid")
        result: dict[str, int | float] = {}
        for key in METRIC_KEYS:
            value = metrics[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise CorpusLibraryError("metrics_value_invalid")
            if value < 0 or value > 100_000_000:
                raise CorpusLibraryError("metrics_value_out_of_range")
            result[key] = value
        return result

    @staticmethod
    def _craft_profile(metrics: Mapping[str, int | float]) -> dict[str, dict[str, Any]]:
        """Project coarse descriptive signals; never generation targets."""

        sampled = max(1.0, float(metrics["sampled_chars"]))
        sentences = max(1.0, float(metrics["sentence_count"]))
        paragraphs = max(1.0, float(metrics["paragraph_count"]))
        mean_sentence = float(metrics["mean_sentence_chars_milli"])
        dialogue = float(metrics["dialogue_char_ratio_ppm"])
        punctuation = float(metrics["punctuation_ratio_ppm"])
        confidence = min(1_000_000, round(sampled / MAX_WINDOW_CHARS * 1_000_000))

        sentence_label = "clipped" if mean_sentence < 18_000 else (
            "extended" if mean_sentence > 38_000 else "balanced"
        )
        sentences_per_paragraph = sentences / paragraphs
        scene_label = "fragmented" if sentences_per_paragraph < 2.0 else (
            "sustained" if sentences_per_paragraph > 6.0 else "balanced"
        )
        segmentation = paragraphs * MAX_WINDOW_CHARS / sampled
        chapter_label = "low_segmentation" if segmentation < 12 else (
            "high_segmentation" if segmentation > 45 else "moderate_segmentation"
        )
        pacing_label = "brisk" if mean_sentence < 20_000 else (
            "deliberate" if mean_sentence > 40_000 else "mixed"
        )
        dialogue_label = "sparse" if dialogue < 80_000 else (
            "dialogue_forward" if dialogue > 280_000 else "mixed"
        )
        tension_signal = min(1_000_000, round(punctuation * 4 + dialogue / 2))
        tension_label = "low_signal" if tension_signal < 220_000 else (
            "high_signal" if tension_signal > 520_000 else "variable_signal"
        )
        return {
            "sentence": {
                "label": sentence_label,
                "signal_ppm": min(1_000_000, round(mean_sentence / 60_000 * 1_000_000)),
                "confidence_ppm": confidence,
            },
            "scene": {
                "label": scene_label,
                "signal_ppm": min(1_000_000, round(sentences_per_paragraph / 10 * 1_000_000)),
                "confidence_ppm": confidence,
            },
            "chapter": {
                "label": chapter_label,
                "signal_ppm": min(1_000_000, round(segmentation / 80 * 1_000_000)),
                "confidence_ppm": min(confidence, 600_000),
            },
            "pacing": {
                "label": pacing_label,
                "signal_ppm": max(0, 1_000_000 - min(1_000_000, round(mean_sentence / 55_000 * 1_000_000))),
                "confidence_ppm": min(confidence, 650_000),
            },
            "dialogue": {
                "label": dialogue_label,
                "signal_ppm": min(1_000_000, round(dialogue)),
                "confidence_ppm": confidence,
            },
            # These axes cannot be inferred responsibly from the seven coarse
            # surface metrics.  They remain explicit unresolved values instead
            # of fabricating a POV or sensory claim.
            "pov": {"label": "unresolved", "signal_ppm": 0, "confidence_ppm": 0},
            "tension": {
                "label": tension_label,
                "signal_ppm": tension_signal,
                "confidence_ppm": min(confidence, 350_000),
            },
            "sensory": {"label": "unresolved", "signal_ppm": 0, "confidence_ppm": 0},
        }

    @staticmethod
    def _validate_craft_profile(profile: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(profile, dict) or set(profile) != set(CRAFT_AXES):
            raise CorpusLibraryError("craft_profile_schema_invalid")
        result: dict[str, dict[str, Any]] = {}
        for axis in CRAFT_AXES:
            item = profile.get(axis)
            if not isinstance(item, dict) or set(item) != {"label", "signal_ppm", "confidence_ppm"}:
                raise CorpusLibraryError("craft_axis_schema_invalid")
            if item.get("label") not in CRAFT_LABELS[axis]:
                raise CorpusLibraryError("craft_axis_label_invalid")
            for field in ("signal_ppm", "confidence_ppm"):
                value = item.get(field)
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1_000_000:
                    raise CorpusLibraryError("craft_axis_value_invalid")
            result[axis] = dict(item)
        return result

    @staticmethod
    def _aggregate_mechanisms(
        works: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        mechanisms: list[dict[str, Any]] = []
        for axis in CRAFT_AXES:
            counts: dict[str, int] = {}
            confidences: list[int] = []
            for work in works:
                item = work["craft_profile"][axis]
                counts[item["label"]] = counts.get(item["label"], 0) + 1
                confidences.append(item["confidence_ppm"])
            dominant = sorted(counts, key=lambda label: (-counts[label], label))[0]
            support_count = counts[dominant]
            if dominant == "unresolved":
                counterexample = "axis_evidence_unresolved"
            elif len(counts) > 1:
                counterexample = "non_dominant_profiles_present"
            else:
                counterexample = "no_observed_counterexample_in_sample"
            mechanisms.append(
                {
                    "axis": axis,
                    "mechanism_label": dominant,
                    "support_count": support_count,
                    "prevalence_ppm": round(support_count * 1_000_000 / len(works)),
                    "mean_confidence_ppm": round(sum(confidences) / len(confidences)),
                    "applicability_boundary": "anonymous_three_window_sample",
                    "counterexample": counterexample,
                    "failure_mode": "descriptive_not_prescriptive",
                }
            )
        return mechanisms

    def analyze_work(self, study_id: str, public_work_id: str) -> dict[str, Any]:
        materialized = self.materialize_windows(study_id, public_work_id)
        sample = "\n".join(window["text"] for window in materialized["windows"])
        metrics = self._metrics_for_text(sample)
        return self.mark_studied(study_id, public_work_id, metrics=metrics)

    def mark_studied(
        self,
        study_id: str,
        public_work_id: str,
        *,
        metrics: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized = self._validate_metrics(metrics)
        analysis_fingerprint = _fingerprint(normalized)
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] == "confirmed":
                connection.execute("UPDATE studies SET state='running' WHERE study_id=?", (study["study_id"],))
                study = self._find_study(connection, study["study_id"])
            if study["state"] not in {"running", "complete"}:
                raise CorpusLibraryError("study_not_running")
            self._bound_source(connection, study["study_id"], public_work_id)
            row = connection.execute(
                "SELECT sw.* FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
                "WHERE sw.study_id=? AND w.public_work_id=?",
                (study["study_id"], public_work_id),
            ).fetchone()
            if row is None:
                raise CorpusLibraryError("study_work_not_found")
            if row["state"] == "studied":
                if row["analysis_fingerprint"] != analysis_fingerprint:
                    raise CorpusLibraryError("analysis_result_conflict")
            elif row["state"] != "selected":
                raise CorpusLibraryError("study_work_not_selected")
            else:
                connection.execute(
                    "UPDATE study_works SET state='studied',metrics_json=?,analysis_fingerprint=? "
                    "WHERE study_id=? AND work_id=?",
                    (
                        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        analysis_fingerprint,
                        study["study_id"],
                        row["work_id"],
                    ),
                )
            incomplete = connection.execute(
                "SELECT COUNT(*) FROM study_works WHERE study_id=? AND state!='studied'",
                (study["study_id"],),
            ).fetchone()[0]
            if incomplete == 0:
                connection.execute(
                    "UPDATE studies SET state='complete',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                    "WHERE study_id=?",
                    (study["study_id"],),
                )
            return self._study_status(connection, study["study_id"], include_works=False)

    # ------------------------------------------------------------------
    # Semantic study completion receipt
    # ------------------------------------------------------------------
    @staticmethod
    def _semantic_receipt_material(values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema": "quillframe_corpus_semantic_completion_receipt_v1",
            "study_id": values["study_id"],
            "run_id": values["run_id"],
            "public_study_id": values["public_study_id"],
            "profile": values["profile"],
            "checklist_hash": values["checklist_hash"],
            "range_job_count": values["range_job_count"],
            "work_synthesis_count": values["work_synthesis_count"],
            "benchmark_job_fingerprint": values["benchmark_job_fingerprint"],
            "benchmark_result_fingerprint": values["benchmark_result_fingerprint"],
            "candidate_bundle_fingerprint": values["candidate_bundle_fingerprint"],
        }

    def _runner_completion_facts(
        self,
        connection: sqlite3.Connection,
        study: sqlite3.Row,
        run_id: str,
        *,
        require_completed_runner: bool,
    ) -> dict[str, Any]:
        """Mechanically prove that every required semantic step is durable.

        The runner and library deliberately share one SQLite database.  This
        check therefore does not trust caller-supplied counts: it rebinds the
        run, all 360 range observations, all 120 work syntheses, the benchmark,
        and the candidate bundle to the frozen study membership.
        """

        try:
            run = connection.execute(
                "SELECT * FROM study_runs WHERE run_id=? AND study_id=?",
                (run_id, study["study_id"]),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            raise CorpusLibraryError("semantic_runner_state_missing") from exc
        if run is None:
            raise CorpusLibraryError("semantic_runner_state_missing")
        allowed_statuses = {"completed"} if require_completed_runner else {"running", "failed", "completed"}
        if run["status"] not in allowed_statuses or run["benchmark_state"] != "complete":
            raise CorpusLibraryError("semantic_runner_state_incomplete")
        for field in ("benchmark_job_fingerprint", "benchmark_result_fingerprint"):
            if not _HASH_RE.fullmatch(str(run[field] or "")):
                raise CorpusLibraryError("semantic_benchmark_fingerprint_invalid")
        if (
            run["public_study_id"] != study["public_study_id"]
            or run["profile"] != study["profile"]
            or run["checklist_hash"] != study["checklist_hash"]
        ):
            raise CorpusLibraryError("semantic_runner_study_binding_mismatch")

        try:
            bundle = json.loads(run["candidate_bundle_json"] or "")
        except (TypeError, json.JSONDecodeError) as exc:
            raise CorpusLibraryError("semantic_candidate_bundle_invalid") from exc
        if not isinstance(bundle, dict):
            raise CorpusLibraryError("semantic_candidate_bundle_invalid")
        bundle_fingerprint = str(bundle.get("bundle_fingerprint") or "")
        if not _HASH_RE.fullmatch(bundle_fingerprint):
            raise CorpusLibraryError("semantic_candidate_bundle_invalid")
        fingerprint_input = dict(bundle)
        fingerprint_input.pop("bundle_fingerprint", None)
        if _fingerprint(fingerprint_input) != bundle_fingerprint:
            raise CorpusLibraryError("semantic_candidate_bundle_invalid")
        if (
            bundle.get("run_id") != run_id
            or bundle.get("public_study_id") != study["public_study_id"]
            or bundle.get("profile") != study["profile"]
        ):
            raise CorpusLibraryError("semantic_candidate_bundle_binding_mismatch")

        expected_work_ids = {
            row["public_work_id"]
            for row in connection.execute(
                "SELECT w.public_work_id FROM study_works sw "
                "JOIN logical_works w ON w.work_id=sw.work_id WHERE sw.study_id=?",
                (study["study_id"],),
            )
        }
        if len(expected_work_ids) != STUDY_SIZE:
            raise CorpusLibraryError("semantic_study_membership_invalid")
        try:
            work_rows = connection.execute(
                "SELECT public_work_id,state,semantic_job_fingerprint,"
                "semantic_result_fingerprint,work_judgment_json "
                "FROM study_work_steps WHERE run_id=? ORDER BY ordinal",
                (run_id,),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise CorpusLibraryError("semantic_runner_state_missing") from exc
        if len(work_rows) != STUDY_SIZE or {row["public_work_id"] for row in work_rows} != expected_work_ids:
            raise CorpusLibraryError("semantic_work_synthesis_count_invalid")
        for row in work_rows:
            if row["state"] != "complete":
                raise CorpusLibraryError("semantic_work_synthesis_incomplete")
            if not _HASH_RE.fullmatch(str(row["semantic_job_fingerprint"] or "")) or not _HASH_RE.fullmatch(
                str(row["semantic_result_fingerprint"] or "")
            ):
                raise CorpusLibraryError("semantic_work_synthesis_fingerprint_invalid")
            try:
                work_judgment = json.loads(row["work_judgment_json"] or "")
            except (TypeError, json.JSONDecodeError) as exc:
                raise CorpusLibraryError("semantic_work_synthesis_invalid") from exc
            if not isinstance(work_judgment, dict) or work_judgment.get("public_work_id") != row["public_work_id"]:
                raise CorpusLibraryError("semantic_work_synthesis_binding_mismatch")

        try:
            range_rows = connection.execute(
                "SELECT sr.range_id,sr.public_work_id,sr.range_ordinal,sr.state,sr.source_fingerprint,"
                "sr.passage_fingerprint,sr.job_fingerprint,sr.semantic_result_fingerprint,"
                "sr.judgment_json,sr.judgment_fingerprint,lr.study_id AS library_study_id,"
                "lr.state AS library_state,lr.judgment_fingerprint AS library_judgment_fingerprint "
                "FROM study_range_steps sr LEFT JOIN range_jobs lr ON lr.range_id=sr.range_id "
                "WHERE sr.run_id=? ORDER BY sr.public_work_id,sr.range_ordinal",
                (run_id,),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise CorpusLibraryError("semantic_runner_state_missing") from exc
        expected_range_count = STUDY_SIZE * 3
        if len(range_rows) != expected_range_count:
            raise CorpusLibraryError("semantic_range_job_count_invalid")
        range_ordinals: dict[str, set[int]] = {work_id: set() for work_id in expected_work_ids}
        for row in range_rows:
            work_id = row["public_work_id"]
            if work_id not in range_ordinals:
                raise CorpusLibraryError("semantic_range_work_binding_mismatch")
            range_ordinals[work_id].add(row["range_ordinal"])
            if row["state"] != "complete" or row["library_state"] != "complete":
                raise CorpusLibraryError("semantic_range_job_incomplete")
            if row["library_study_id"] != study["study_id"]:
                raise CorpusLibraryError("semantic_range_study_binding_mismatch")
            for field in (
                "source_fingerprint",
                "passage_fingerprint",
                "job_fingerprint",
                "semantic_result_fingerprint",
                "judgment_fingerprint",
            ):
                if not _HASH_RE.fullmatch(str(row[field] or "")):
                    raise CorpusLibraryError("semantic_range_fingerprint_invalid")
            if row["library_judgment_fingerprint"] != row["judgment_fingerprint"]:
                raise CorpusLibraryError("semantic_range_judgment_binding_mismatch")
            try:
                range_judgment = json.loads(row["judgment_json"] or "")
            except (TypeError, json.JSONDecodeError) as exc:
                raise CorpusLibraryError("semantic_range_judgment_invalid") from exc
            if (
                not isinstance(range_judgment, dict)
                or range_judgment.get("range_id") != row["range_id"]
                or _fingerprint(range_judgment) != row["judgment_fingerprint"]
            ):
                raise CorpusLibraryError("semantic_range_judgment_invalid")
        if any(ordinals != {1, 2, 3} for ordinals in range_ordinals.values()):
            raise CorpusLibraryError("semantic_range_cardinality_invalid")

        return {
            "range_job_count": len(range_rows),
            "work_synthesis_count": len(work_rows),
            "benchmark_job_fingerprint": run["benchmark_job_fingerprint"],
            "benchmark_result_fingerprint": run["benchmark_result_fingerprint"],
            "candidate_bundle_fingerprint": bundle_fingerprint,
            "runner_completion_receipt_fingerprint": run["completion_receipt_fingerprint"],
        }

    def record_semantic_completion(
        self,
        *,
        study_id: str,
        run_id: str,
        public_study_id: str,
        profile: str,
        checklist_hash: str,
        range_job_count: int,
        work_synthesis_count: int,
        benchmark_job_fingerprint: str,
        benchmark_result_fingerprint: str,
        candidate_bundle_fingerprint: str,
    ) -> dict[str, Any]:
        """Persist an idempotent receipt only after the same-DB runner proves completion."""

        run_id = _safe_identifier(run_id, "run_id")
        with self._connect() as connection:
            study = self._find_study(connection, study_id)
            if study["state"] != "complete":
                raise CorpusLibraryError("study_not_complete")
            supplied = {
                "study_id": study["study_id"],
                "run_id": run_id,
                "public_study_id": str(public_study_id),
                "profile": str(profile),
                "checklist_hash": str(checklist_hash),
                "range_job_count": range_job_count,
                "work_synthesis_count": work_synthesis_count,
                "benchmark_job_fingerprint": str(benchmark_job_fingerprint),
                "benchmark_result_fingerprint": str(benchmark_result_fingerprint),
                "candidate_bundle_fingerprint": str(candidate_bundle_fingerprint),
            }
            if (
                supplied["public_study_id"] != study["public_study_id"]
                or supplied["profile"] != study["profile"]
                or supplied["checklist_hash"] != study["checklist_hash"]
            ):
                raise CorpusLibraryError("semantic_completion_study_binding_mismatch")
            if range_job_count != STUDY_SIZE * 3 or work_synthesis_count != STUDY_SIZE:
                raise CorpusLibraryError("semantic_completion_count_invalid")
            facts = self._runner_completion_facts(
                connection, study, run_id, require_completed_runner=False
            )
            for key in (
                "range_job_count",
                "work_synthesis_count",
                "benchmark_job_fingerprint",
                "benchmark_result_fingerprint",
                "candidate_bundle_fingerprint",
            ):
                if supplied[key] != facts[key]:
                    raise CorpusLibraryError("semantic_completion_fact_mismatch")
            material = self._semantic_receipt_material(supplied)
            receipt_fingerprint = _fingerprint(material)
            receipt_id = "SEMREC-" + receipt_fingerprint.removeprefix("sha256:")[:32]
            existing = connection.execute(
                "SELECT * FROM semantic_completion_receipts WHERE study_id=? OR run_id=?",
                (study["study_id"], run_id),
            ).fetchone()
            if existing is not None:
                if existing["receipt_fingerprint"] != receipt_fingerprint or existing["state"] != "complete":
                    raise CorpusLibraryError("semantic_completion_receipt_conflict")
                return {
                    **material,
                    "receipt_id": existing["receipt_id"],
                    "receipt_fingerprint": receipt_fingerprint,
                    "status": "complete",
                    "idempotent": True,
                    "authority_granted": False,
                }
            connection.execute(
                "INSERT INTO semantic_completion_receipts(receipt_id,study_id,run_id,"
                "public_study_id,profile,checklist_hash,range_job_count,work_synthesis_count,"
                "benchmark_job_fingerprint,benchmark_result_fingerprint,"
                "candidate_bundle_fingerprint,receipt_fingerprint,state) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'complete')",
                (
                    receipt_id,
                    study["study_id"],
                    run_id,
                    study["public_study_id"],
                    study["profile"],
                    study["checklist_hash"],
                    range_job_count,
                    work_synthesis_count,
                    benchmark_job_fingerprint,
                    benchmark_result_fingerprint,
                    candidate_bundle_fingerprint,
                    receipt_fingerprint,
                ),
            )
            return {
                **material,
                "receipt_id": receipt_id,
                "receipt_fingerprint": receipt_fingerprint,
                "status": "complete",
                "idempotent": False,
                "authority_granted": False,
            }

    def _require_semantic_completion_receipt(
        self, connection: sqlite3.Connection, study: sqlite3.Row
    ) -> sqlite3.Row:
        receipt = connection.execute(
            "SELECT * FROM semantic_completion_receipts WHERE study_id=?",
            (study["study_id"],),
        ).fetchone()
        if receipt is None:
            raise CorpusLibraryError("semantic_completion_receipt_missing")
        try:
            if receipt["state"] != "complete":
                raise CorpusLibraryError("semantic_completion_receipt_invalid")
            material = self._semantic_receipt_material(receipt)
            if _fingerprint(material) != receipt["receipt_fingerprint"]:
                raise CorpusLibraryError("semantic_completion_receipt_invalid")
            if (
                receipt["public_study_id"] != study["public_study_id"]
                or receipt["profile"] != study["profile"]
                or receipt["checklist_hash"] != study["checklist_hash"]
                or receipt["range_job_count"] != STUDY_SIZE * 3
                or receipt["work_synthesis_count"] != STUDY_SIZE
            ):
                raise CorpusLibraryError("semantic_completion_receipt_invalid")
            facts = self._runner_completion_facts(
                connection,
                study,
                receipt["run_id"],
                require_completed_runner=True,
            )
            for key in (
                "range_job_count",
                "work_synthesis_count",
                "benchmark_job_fingerprint",
                "benchmark_result_fingerprint",
                "candidate_bundle_fingerprint",
            ):
                if receipt[key] != facts[key]:
                    raise CorpusLibraryError("semantic_completion_receipt_invalid")
            if facts["runner_completion_receipt_fingerprint"] != receipt["receipt_fingerprint"]:
                raise CorpusLibraryError("semantic_completion_receipt_invalid")
        except (KeyError, TypeError, sqlite3.Error, CorpusLibraryError) as exc:
            if isinstance(exc, CorpusLibraryError) and exc.code == "semantic_completion_receipt_missing":
                raise
            raise CorpusLibraryError("semantic_completion_receipt_invalid") from exc
        return receipt

    # ------------------------------------------------------------------
    # Anonymous public preview, validation, and atomic release
    # ------------------------------------------------------------------
    def _verify_study_dependencies(
        self, connection: sqlite3.Connection, study_id: str
    ) -> bool:
        rows = connection.execute(
            "SELECT DISTINCT version_id FROM study_works WHERE study_id=?", (study_id,)
        ).fetchall()
        for version in rows:
            bound = connection.execute(
                "SELECT v.sha256,c.root_path FROM source_versions v "
                "JOIN logical_works w ON w.work_id=v.work_id "
                "JOIN collections c ON c.collection_id=w.collection_id WHERE v.version_id=?",
                (version["version_id"],),
            ).fetchone()
            if bound is None:
                self._invalidate_study(connection, study_id, "source_dependency_missing")
                connection.commit()
                return False
            root = Path(bound["root_path"]).resolve()
            paths = connection.execute(
                "SELECT relative_path FROM source_files WHERE version_id=? AND available=1",
                (version["version_id"],),
            ).fetchall()
            matched = False
            for item in paths:
                entry = root / item["relative_path"]
                candidate = entry.resolve()
                if (
                    entry.is_symlink()
                    or candidate != entry
                    or not self._inside(root, candidate)
                    or candidate.is_symlink()
                    or not candidate.is_file()
                ):
                    continue
                try:
                    digest, _size = self._hash_stable_file(candidate)
                except CorpusLibraryError:
                    continue
                if digest == bound["sha256"]:
                    matched = True
                    break
            if not matched:
                self._invalidate_version_dependency(connection, version["version_id"], "source_dependency_mismatch")
                connection.commit()
                return False
        return True

    def _public_manifest(self, connection: sqlite3.Connection, study: sqlite3.Row) -> dict[str, Any]:
        if study["state"] != "complete":
            raise CorpusLibraryError("study_not_complete")
        self._require_semantic_completion_receipt(connection, study)
        rows = connection.execute(
            "SELECT sw.ordinal,sw.metrics_json,w.public_work_id,v.version_number "
            "FROM study_works sw JOIN logical_works w ON w.work_id=sw.work_id "
            "JOIN source_versions v ON v.version_id=sw.version_id "
            "WHERE sw.study_id=? ORDER BY sw.ordinal",
            (study["study_id"],),
        ).fetchall()
        if len(rows) != STUDY_SIZE or any(row["metrics_json"] is None for row in rows):
            raise CorpusLibraryError("study_results_incomplete")
        works: list[dict[str, Any]] = []
        metric_columns: dict[str, list[float]] = {key: [] for key in METRIC_KEYS}
        for row in rows:
            try:
                metrics = self._validate_metrics(json.loads(row["metrics_json"]))
            except (json.JSONDecodeError, TypeError) as exc:
                raise CorpusLibraryError("stored_metrics_invalid") from exc
            work: dict[str, Any] = {
                "schema": PUBLIC_WORK_SCHEMA,
                "public_work_id": row["public_work_id"],
                "profile": study["profile"],
                "study_ordinal": row["ordinal"],
                "source_version": row["version_number"],
                "metrics": metrics,
                "craft_profile": self._craft_profile(metrics),
            }
            work["record_fingerprint"] = _fingerprint(work)
            works.append(work)
            for key in METRIC_KEYS:
                metric_columns[key].append(float(metrics[key]))
        aggregate = {
            key: {
                "minimum": min(values),
                "maximum": max(values),
                "mean": round(sum(values) / len(values), 6),
            }
            for key, values in metric_columns.items()
        }
        manifest: dict[str, Any] = {
            "schema": PUBLIC_MANIFEST_SCHEMA,
            "public_study_id": study["public_study_id"],
            "profile": study["profile"],
            "study_state": "complete",
            "work_count": STUDY_SIZE,
            "checklist_hash": study["checklist_hash"],
            "aggregate_metrics": aggregate,
            "aggregate_mechanisms": self._aggregate_mechanisms(works),
            "works": works,
        }
        manifest_fingerprint = _fingerprint(manifest)
        manifest["preview_token"] = "preview-" + hashlib.sha256(
            (manifest_fingerprint + "\0" + study["public_study_id"]).encode("ascii")
        ).hexdigest()
        manifest["manifest_fingerprint"] = manifest_fingerprint
        return manifest

    def preview_public(
        self, study_id: str | None = None, *, release_id: str | None = None
    ) -> dict[str, Any]:
        identifier = study_id or release_id
        if not identifier:
            raise CorpusLibraryError("study_id_required")
        with self._connect() as connection:
            study = self._find_study(connection, identifier)
            if not self._verify_study_dependencies(connection, study["study_id"]):
                raise CorpusLibraryError("source_dependency_mismatch")
            study = self._find_study(connection, study["study_id"])
            return self._public_manifest(connection, study)

    @staticmethod
    def _walk_public(value: Any, *, depth: int = 0) -> Iterable[tuple[str | None, Any]]:
        if depth > 12:
            raise CorpusLibraryError("public_payload_depth_limit")
        if isinstance(value, dict):
            if len(value) > 1_000:
                raise CorpusLibraryError("public_payload_size_limit")
            for key, nested in value.items():
                yield str(key), nested
                yield from CorpusLibrary._walk_public(nested, depth=depth + 1)
        elif isinstance(value, list):
            if len(value) > 1_000:
                raise CorpusLibraryError("public_payload_size_limit")
            for nested in value:
                yield None, nested
                yield from CorpusLibrary._walk_public(nested, depth=depth + 1)

    def _load_public_payload(self, payload: Mapping[str, Any] | str | Path) -> dict[str, Any]:
        if isinstance(payload, Mapping):
            # Canonical round-trip removes custom mapping/list subclasses.
            try:
                encoded = _canonical_bytes(payload)
            except (TypeError, ValueError) as exc:
                raise CorpusLibraryError("public_payload_not_json") from exc
            if len(encoded) > 8 * 1024 * 1024:
                raise CorpusLibraryError("public_payload_size_limit")
            result = json.loads(encoded)
        else:
            path = Path(payload).expanduser().resolve()
            try:
                if path.stat().st_size > 8 * 1024 * 1024:
                    raise CorpusLibraryError("public_payload_size_limit")
                result = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise CorpusLibraryError("public_payload_read_failed") from exc
        if not isinstance(result, dict):
            raise CorpusLibraryError("public_payload_not_object")
        return result

    def _validate_public_structure(self, manifest: dict[str, Any]) -> list[str]:
        errors: set[str] = set()
        if set(manifest) != _PUBLIC_MANIFEST_KEYS:
            errors.add("manifest_fields_invalid")
        if manifest.get("schema") != PUBLIC_MANIFEST_SCHEMA:
            errors.add("manifest_schema_invalid")
        if not _PUBLIC_ID_RE.fullmatch(str(manifest.get("public_study_id") or "")):
            errors.add("public_study_id_invalid")
        manifest_profile = manifest.get("profile")
        if manifest_profile not in {"general", "adult_explicit"}:
            errors.add("study_profile_invalid")
        if manifest.get("study_state") != "complete":
            errors.add("study_state_invalid")
        if manifest.get("work_count") != STUDY_SIZE:
            errors.add("work_count_invalid")
        if not _HASH_RE.fullmatch(str(manifest.get("checklist_hash") or "")):
            errors.add("checklist_hash_invalid")
        if not _HASH_RE.fullmatch(str(manifest.get("manifest_fingerprint") or "")):
            errors.add("manifest_fingerprint_invalid")
        if not _TOKEN_RE.fullmatch(str(manifest.get("preview_token") or "")):
            errors.add("preview_token_invalid")

        try:
            walked = list(self._walk_public(manifest))
        except CorpusLibraryError as exc:
            errors.add(exc.code)
            walked = []
        for key, value in walked:
            if key is not None and key.casefold() in _FORBIDDEN_PUBLIC_KEYS:
                errors.add("forbidden_public_field")
            if isinstance(value, str) and _PATH_LIKE_RE.search(value):
                errors.add("path_like_public_value")

        works = manifest.get("works")
        if not isinstance(works, list) or len(works) != STUDY_SIZE:
            errors.add("works_cardinality_invalid")
            works = []
        seen_ids: set[str] = set()
        profiles_valid = True
        for work in works:
            if not isinstance(work, dict) or set(work) != _PUBLIC_WORK_KEYS:
                errors.add("work_fields_invalid")
                continue
            if work.get("schema") != PUBLIC_WORK_SCHEMA:
                errors.add("work_schema_invalid")
            public_work_id = str(work.get("public_work_id") or "")
            if not re.fullmatch(r"PW-[0-9a-f]{32}", public_work_id):
                errors.add("public_work_id_invalid")
            if public_work_id in seen_ids:
                errors.add("duplicate_public_work_id")
            seen_ids.add(public_work_id)
            if work.get("profile") != manifest_profile:
                errors.add("profile_binding_mismatch")
            ordinal = work.get("study_ordinal")
            version = work.get("source_version")
            if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= STUDY_SIZE:
                errors.add("study_ordinal_invalid")
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                errors.add("source_version_invalid")
            metrics = work.get("metrics")
            if not isinstance(metrics, dict):
                errors.add("metrics_schema_invalid")
            else:
                try:
                    self._validate_metrics(metrics)
                except CorpusLibraryError as exc:
                    errors.add(exc.code)
            try:
                self._validate_craft_profile(work.get("craft_profile"))
            except CorpusLibraryError as exc:
                errors.add(exc.code)
                profiles_valid = False
            else:
                if isinstance(metrics, dict):
                    try:
                        expected_profile = self._craft_profile(self._validate_metrics(metrics))
                    except CorpusLibraryError:
                        profiles_valid = False
                    else:
                        if work.get("craft_profile") != expected_profile:
                            errors.add("craft_profile_metric_mismatch")
                            profiles_valid = False
            claimed = work.get("record_fingerprint")
            work_base = {key: value for key, value in work.items() if key != "record_fingerprint"}
            if claimed != _fingerprint(work_base):
                errors.add("record_fingerprint_mismatch")
        if works and {work.get("study_ordinal") for work in works if isinstance(work, dict)} != set(range(1, STUDY_SIZE + 1)):
            errors.add("study_ordinals_not_exact")

        aggregate = manifest.get("aggregate_metrics")
        if not isinstance(aggregate, dict) or set(aggregate) != set(METRIC_KEYS):
            errors.add("aggregate_schema_invalid")
        else:
            for key in METRIC_KEYS:
                summary = aggregate.get(key)
                if not isinstance(summary, dict) or set(summary) != {"minimum", "maximum", "mean"}:
                    errors.add("aggregate_summary_invalid")
                    continue
                values = [summary.get(name) for name in ("minimum", "maximum", "mean")]
                if any(
                    isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                    for value in values
                ):
                    errors.add("aggregate_value_invalid")
            if works and not any(code.startswith("metrics_") for code in errors):
                for key in METRIC_KEYS:
                    values = [float(work["metrics"][key]) for work in works]
                    expected = {
                        "minimum": min(values),
                        "maximum": max(values),
                        "mean": round(sum(values) / len(values), 6),
                    }
                    if aggregate.get(key) != expected:
                        errors.add("aggregate_value_mismatch")
                        break

        mechanisms = manifest.get("aggregate_mechanisms")
        mechanism_keys = {
            "axis",
            "mechanism_label",
            "support_count",
            "prevalence_ppm",
            "mean_confidence_ppm",
            "applicability_boundary",
            "counterexample",
            "failure_mode",
        }
        if not isinstance(mechanisms, list) or len(mechanisms) != len(CRAFT_AXES):
            errors.add("aggregate_mechanisms_schema_invalid")
        else:
            seen_axes: set[str] = set()
            for mechanism in mechanisms:
                if not isinstance(mechanism, dict) or set(mechanism) != mechanism_keys:
                    errors.add("aggregate_mechanism_fields_invalid")
                    continue
                axis = mechanism.get("axis")
                if axis not in CRAFT_AXES or axis in seen_axes:
                    errors.add("aggregate_mechanism_axis_invalid")
                    continue
                seen_axes.add(axis)
                if mechanism.get("mechanism_label") not in CRAFT_LABELS[axis]:
                    errors.add("aggregate_mechanism_label_invalid")
                support = mechanism.get("support_count")
                if isinstance(support, bool) or not isinstance(support, int) or not 1 <= support <= STUDY_SIZE:
                    errors.add("aggregate_mechanism_support_invalid")
                for field in ("prevalence_ppm", "mean_confidence_ppm"):
                    value = mechanism.get(field)
                    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1_000_000:
                        errors.add("aggregate_mechanism_value_invalid")
                if mechanism.get("applicability_boundary") not in _MECHANISM_BOUNDARIES:
                    errors.add("aggregate_mechanism_boundary_invalid")
                if mechanism.get("counterexample") not in _MECHANISM_COUNTEREXAMPLES:
                    errors.add("aggregate_mechanism_counterexample_invalid")
                if mechanism.get("failure_mode") not in _MECHANISM_FAILURE_MODES:
                    errors.add("aggregate_mechanism_failure_mode_invalid")
            if works and profiles_valid and mechanisms != self._aggregate_mechanisms(works):
                errors.add("aggregate_mechanisms_value_mismatch")

        base = {
            key: value
            for key, value in manifest.items()
            if key not in {"manifest_fingerprint", "preview_token"}
        }
        expected_fingerprint = _fingerprint(base)
        if manifest.get("manifest_fingerprint") != expected_fingerprint:
            errors.add("manifest_fingerprint_mismatch")
        expected_token = "preview-" + hashlib.sha256(
            (expected_fingerprint + "\0" + str(manifest.get("public_study_id") or "")).encode("ascii", errors="ignore")
        ).hexdigest()
        if manifest.get("preview_token") != expected_token:
            errors.add("preview_token_mismatch")
        return sorted(errors)

    def _private_terms(self, connection: sqlite3.Connection, study_id: str) -> set[str]:
        terms: set[str] = set()
        rows = connection.execute(
            "SELECT v.private_metadata_json,f.relative_path FROM study_works sw "
            "JOIN source_versions v ON v.version_id=sw.version_id "
            "LEFT JOIN source_files f ON f.version_id=v.version_id "
            "WHERE sw.study_id=?",
            (study_id,),
        ).fetchall()
        for row in rows:
            values: list[str] = [Path(row["relative_path"] or "").stem]
            try:
                metadata = json.loads(row["private_metadata_json"])
                if isinstance(metadata, dict):
                    values.extend(str(value) for value in metadata.values())
            except (TypeError, json.JSONDecodeError):
                pass
            for value in values:
                normalized = _normal_overlap_text(value)
                if len(normalized) >= 3:
                    terms.add(normalized)
        return terms

    @staticmethod
    def _candidate_public_prose(manifest: dict[str, Any]) -> set[str]:
        candidates: set[str] = set()
        stack: list[Any] = [manifest]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
            elif isinstance(value, str):
                normalized = _normal_overlap_text(value)
                if (
                    len(normalized) >= 24
                    and not _HASH_RE.fullmatch(value)
                    and not _PUBLIC_ID_RE.fullmatch(value)
                    and not _TOKEN_RE.fullmatch(value)
                    and value not in {PUBLIC_WORK_SCHEMA, PUBLIC_MANIFEST_SCHEMA}
                    and value not in _CONTROLLED_PUBLIC_STRINGS
                ):
                    candidates.add(normalized)
        return candidates

    def _has_source_overlap(
        self, connection: sqlite3.Connection, study_id: str, candidates: set[str]
    ) -> bool:
        if not candidates:
            return False
        rows = connection.execute(
            "SELECT DISTINCT w.public_work_id FROM study_works sw "
            "JOIN logical_works w ON w.work_id=sw.work_id WHERE sw.study_id=?",
            (study_id,),
        ).fetchall()
        for row in rows:
            try:
                _study, _bound, path = self._bound_source(
                    connection, study_id, row["public_work_id"]
                )
                _raw, text, _metadata, _media = self._extract_document(path)
            except CorpusLibraryError:
                return True
            normalized_source = _normal_overlap_text(text)
            if any(candidate in normalized_source for candidate in candidates):
                return True
        return False

    def validate_public(
        self,
        payload: Mapping[str, Any] | str | Path | None = None,
        *,
        study_id: str | None = None,
        release_id: str | None = None,
    ) -> dict[str, Any]:
        if payload is None:
            identifier = study_id or release_id
            if not identifier:
                raise CorpusLibraryError("public_payload_or_study_required")
            try:
                manifest = self.preview_public(identifier)
            except CorpusLibraryError as exc:
                return {"schema": PUBLIC_VALIDATION_SCHEMA, "valid": False, "errors": [exc.code]}
        else:
            try:
                manifest = self._load_public_payload(payload)
            except CorpusLibraryError as exc:
                return {"schema": PUBLIC_VALIDATION_SCHEMA, "valid": False, "errors": [exc.code]}
        errors = set(self._validate_public_structure(manifest))
        public_study_id = str(manifest.get("public_study_id") or "")
        with self._connect() as connection:
            try:
                study = self._find_study(connection, study_id or public_study_id)
            except CorpusLibraryError as exc:
                errors.add(exc.code)
                study = None
            if study is not None:
                if study["public_study_id"] != public_study_id:
                    errors.add("public_study_binding_mismatch")
                if study["profile"] != manifest.get("profile"):
                    errors.add("study_profile_binding_mismatch")
                if study["state"] != "complete":
                    errors.add("study_not_complete")
                if study["checklist_hash"] != manifest.get("checklist_hash"):
                    errors.add("checklist_binding_mismatch")
                try:
                    self._require_semantic_completion_receipt(connection, study)
                except CorpusLibraryError as exc:
                    errors.add(exc.code)
                if not self._verify_study_dependencies(connection, study["study_id"]):
                    errors.add("source_dependency_mismatch")
                public_strings = {
                    _normal_overlap_text(value)
                    for _key, value in self._walk_public(manifest)
                    if isinstance(value, str)
                }
                if self._private_terms(connection, study["study_id"]) & public_strings:
                    errors.add("private_name_overlap")
                candidates = self._candidate_public_prose(manifest)
                if self._has_source_overlap(connection, study["study_id"], candidates):
                    errors.add("source_text_overlap")
        return {
            "schema": PUBLIC_VALIDATION_SCHEMA,
            "valid": not errors,
            "errors": sorted(errors),
            "public_study_id": public_study_id or None,
            "manifest_fingerprint": manifest.get("manifest_fingerprint"),
        }

    def release_public(
        self,
        study_id: str | None = None,
        *,
        release_id: str | None = None,
        preview_token: str,
        manifest_fingerprint: str,
    ) -> dict[str, Any]:
        identifier = study_id or release_id
        if not identifier:
            raise CorpusLibraryError("study_id_required")
        with self._connect() as connection:
            study = self._find_study(connection, identifier)
            manifest = self._public_manifest(connection, study)
            if preview_token != manifest["preview_token"]:
                raise CorpusLibraryError("preview_token_mismatch")
            if manifest_fingerprint != manifest["manifest_fingerprint"]:
                raise CorpusLibraryError("manifest_fingerprint_mismatch")
            decision = self.validate_public(manifest, study_id=study["study_id"])
            if not decision["valid"]:
                raise CorpusLibraryError("public_validation_failed", ",".join(decision["errors"]))
            existing_release = connection.execute(
                "SELECT * FROM releases WHERE study_id=?", (study["study_id"],)
            ).fetchone()
            assigned_release_id = (
                release_id
                if release_id and release_id not in {study["study_id"], study["public_study_id"]}
                else _random_id("REL")
            )
            assigned_release_id = _safe_identifier(assigned_release_id, "release_id")
            release_id_owner = connection.execute(
                "SELECT study_id FROM releases WHERE release_id=?", (assigned_release_id,)
            ).fetchone()
            if release_id_owner is not None and release_id_owner["study_id"] != study["study_id"]:
                raise CorpusLibraryError("release_id_conflict")
            target = (self.public_root / study["public_study_id"]).resolve()
            if not self._inside(self.public_root.resolve(), target):
                raise CorpusLibraryError("public_target_invalid")
            manifest_path = target / "manifest.json"
            if existing_release is not None and existing_release["state"] == "released":
                if (
                    release_id
                    and release_id not in {
                        study["study_id"],
                        study["public_study_id"],
                        existing_release["release_id"],
                    }
                ):
                    raise CorpusLibraryError("release_id_conflict")
                try:
                    disk_manifest = self._load_public_payload(manifest_path)
                except CorpusLibraryError as exc:
                    raise CorpusLibraryError("released_artifact_missing") from exc
                if disk_manifest.get("manifest_fingerprint") != manifest_fingerprint:
                    raise CorpusLibraryError("released_artifact_conflict")
                return {
                    "schema": "quillframe_public_corpus_release_v1",
                    "status": "released",
                    "release_id": existing_release["release_id"],
                    "public_study_id": study["public_study_id"],
                    "manifest_fingerprint": manifest_fingerprint,
                    "idempotent": True,
                }
            if target.exists():
                raise CorpusLibraryError("public_target_conflict")
            self.public_root.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".quillframe-public-", dir=self.public_root)).resolve()
            try:
                works_dir = stage / "works"
                works_dir.mkdir()
                manifest_text = json.dumps(
                    manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
                ) + "\n"
                (stage / "manifest.json").write_text(manifest_text, encoding="utf-8", newline="\n")
                for work in manifest["works"]:
                    work_text = json.dumps(
                        work, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
                    ) + "\n"
                    (works_dir / f"{work['public_work_id']}.json").write_text(
                        work_text, encoding="utf-8", newline="\n"
                    )
                os.replace(stage, target)
            except Exception:
                if stage.exists() and self._inside(self.public_root.resolve(), stage):
                    shutil.rmtree(stage)
                raise
            try:
                connection.execute(
                    "INSERT INTO releases(release_id,study_id,public_study_id,state,manifest_fingerprint,artifact_dir) "
                    "VALUES(?,?,?,'released',?,?)",
                    (
                        assigned_release_id, study["study_id"], study["public_study_id"],
                        manifest_fingerprint, str(target),
                    ),
                )
            except sqlite3.Error as exc:
                if target.is_dir() and self._inside(self.public_root.resolve(), target):
                    shutil.rmtree(target)
                raise CorpusLibraryError("release_ledger_write_failed") from exc
            return {
                "schema": "quillframe_public_corpus_release_v1",
                "status": "released",
                "release_id": assigned_release_id,
                "public_study_id": study["public_study_id"],
                "manifest_fingerprint": manifest_fingerprint,
                "idempotent": False,
            }

    def list_public(self) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT r.*,s.checklist_hash,s.profile FROM releases r JOIN studies s ON s.study_id=r.study_id "
                "ORDER BY r.public_study_id"
            ).fetchall()
            for row in rows:
                item = {
                    "public_study_id": row["public_study_id"],
                    "profile": row["profile"],
                    "status": row["state"],
                    "manifest_fingerprint": row["manifest_fingerprint"],
                    "checklist_hash": row["checklist_hash"],
                    "work_count": STUDY_SIZE,
                }
                items.append(item)
        return {
            "schema": "quillframe_public_corpus_index_v1",
            "count": len(items),
            "items": items,
        }

    def get_public(
        self,
        identifier: str | None = None,
        *,
        public_study_id: str | None = None,
        public_work_id: str | None = None,
    ) -> dict[str, Any]:
        lookup = public_work_id or public_study_id or identifier
        if not lookup:
            raise CorpusLibraryError("public_identifier_required")
        with self._connect() as connection:
            if str(lookup).startswith("PW-"):
                release = connection.execute(
                    "SELECT r.* FROM releases r JOIN study_works sw ON sw.study_id=r.study_id "
                    "JOIN logical_works w ON w.work_id=sw.work_id WHERE w.public_work_id=?",
                    (lookup,),
                ).fetchone()
            else:
                release = connection.execute(
                    "SELECT * FROM releases WHERE public_study_id=? OR release_id=?",
                    (lookup, lookup),
                ).fetchone()
            if release is None:
                raise CorpusLibraryError("public_artifact_not_found")
            if release["state"] != "released":
                return {
                    "schema": "quillframe_public_corpus_lookup_v1",
                    "status": "invalidated",
                    "public_study_id": release["public_study_id"],
                }
            artifact_dir = Path(release["artifact_dir"]).resolve()
            if not self._inside(self.public_root.resolve(), artifact_dir):
                raise CorpusLibraryError("released_artifact_location_invalid")
            manifest_path = artifact_dir / "manifest.json"
            if manifest_path.is_symlink():
                raise CorpusLibraryError("released_artifact_symlink_rejected")
            manifest = self._load_public_payload(manifest_path)
            decision = self.validate_public(manifest)
            if not decision["valid"]:
                raise CorpusLibraryError("released_artifact_invalid")
            if str(lookup).startswith("PW-"):
                for work in manifest["works"]:
                    if work["public_work_id"] == lookup:
                        return work
                raise CorpusLibraryError("public_artifact_not_found")
            return manifest


__all__ = ["CorpusLibrary", "CorpusLibraryError", "STUDY_SIZE", "MAX_WINDOW_CHARS"]
