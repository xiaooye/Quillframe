#!/usr/bin/env python3
"""Deterministic Story Loom / WeiUI integration checks."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
TOKENS_PATH = BRAND / "tokens.json"
INTEGRATION_PATH = BRAND / "weiui.integration.json"
THEME_PATH = BRAND / "story-loom.weiui.css"
PROVENANCE_PATH = ROOT / "assets" / "provenance.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"story-loom-design-system: FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def channel(value: int) -> float:
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    require(bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_color)), f"invalid hex color {hex_color!r}")
    raw = hex_color[1:]
    r, g, b = (channel(int(raw[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    tokens = load(TOKENS_PATH)
    integration = load(INTEGRATION_PATH)
    provenance = load(PROVENANCE_PATH)
    css = THEME_PATH.read_text(encoding="utf-8")

    require(tokens.get("schema") == "novelforge_brand_tokens_v2", "unexpected token schema")
    require(integration.get("schema") == "novelforge_weiui_integration_v1", "unexpected WeiUI integration schema")

    source = integration.get("source", {})
    require(source.get("repository") == "xiaooye/weiui", "WeiUI source repository must be exact")
    require(bool(re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", "")))), "WeiUI source must pin an exact commit")
    require(source.get("license") == "MIT", "WeiUI license provenance must be MIT")

    consumption = integration.get("consumption", {})
    require(consumption.get("theme_layer") == "wui-theme", "consumer theme layer must be wui-theme")
    require(consumption.get("runtime_javascript_from_weiui") is False, "Studio foundation must not require WeiUI runtime JavaScript")
    require(consumption.get("allowed_packages") == ["@weiui/tokens", "@weiui/css"], "allowed WeiUI packages drifted")
    forbidden = set(consumption.get("forbidden_runtime_packages", []))
    require({"@weiui/headless", "@weiui/react"}.issubset(forbidden), "Solid Studio must forbid React runtime packages")

    app = tokens.get("app", {})
    interaction = app.get("interaction", {})
    responsive = app.get("responsive", {})
    i18n = app.get("i18n", {})
    motion = app.get("motion", {})
    performance = app.get("performance", {})

    require(interaction.get("minimum_touch_target_px", 0) >= 44, "touch target budget must be at least 44px")
    require(interaction.get("focus_ring_width_px") == 3, "focus ring must remain 3px")
    require(interaction.get("focus_ring_offset_px") == 2, "focus ring offset must remain 2px")
    require(responsive.get("mobile_first") is True, "Studio must remain mobile-first")
    require(responsive.get("phone_workspace_mode") == "focus-first", "phone workspace must remain focus-first")
    require(i18n.get("baseline_locales") == ["en-US", "zh-CN"], "baseline locale contract drifted")
    require(i18n.get("logical_properties_required") is True, "logical properties are required")
    require(i18n.get("fixed_width_text_assumptions_allowed") is False, "fixed-width locale assumptions are forbidden")
    require(motion.get("idle_animation_allowed") is False, "idle decorative animation must stay disabled")
    require(motion.get("reduced_motion_required") is True, "reduced-motion support is required")
    require(performance.get("weiui_runtime_javascript_required") is False, "WeiUI JS runtime must remain optional/absent")
    require(performance.get("polling_by_default_allowed") is False, "polling must not become a UI default")

    for mode in ("light", "dark"):
        theme = app.get("theme", {}).get(mode, {})
        for role in ("primary", "destructive", "success", "warning"):
            ratio = contrast(theme[role], theme[f"{role}_foreground"])
            require(ratio >= 4.5, f"{mode} {role} contrast {ratio:.2f}:1 is below 4.5:1")

    require("@layer wui-theme" in css, "theme CSS must use wui-theme")
    require(":root" in css and ".dark" in css, "theme CSS must define light and dark modes")
    require("!important" not in css, "theme CSS must not use !important")
    require(".wui-" not in css, "Story Loom theme must not fork WeiUI component selectors")
    for variable in (
        "--wui-color-background", "--wui-color-foreground", "--wui-color-primary",
        "--wui-color-ring", "--wui-color-success", "--wui-color-warning",
        "--nf-lane-project-fill", "--nf-lane-runtime-fill", "--nf-touch-target-min",
    ):
        require(variable in css, f"theme CSS missing {variable}")

    assets = provenance.get("assets", [])
    ids = {item.get("id") for item in assets if isinstance(item, dict)}
    require({"brand-tokens-v2", "weiui-integration-v1", "story-loom-weiui-theme-v1"}.issubset(ids), "design-system provenance is incomplete")

    print(json.dumps({
        "schema": "novelforge_story_loom_design_system_check_v1",
        "status": "pass",
        "weiui_commit": source["commit"],
        "theme_layer": consumption["theme_layer"],
        "runtime_javascript_from_weiui": False,
        "minimum_touch_target_px": interaction["minimum_touch_target_px"],
        "baseline_locales": i18n["baseline_locales"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
