#!/usr/bin/env python3
"""Deterministic Story Loom / WeiUI integration checks."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
TOKENS_PATH = BRAND / "tokens.json"
INTEGRATION_PATH = BRAND / "weiui.integration.json"
THEME_PATH = BRAND / "story-loom.weiui.css"
PROVENANCE_PATH = ROOT / "assets" / "provenance.json"
APP_CONFIG_PATH = ROOT / "studio" / "app" / "weiui.config.json"
STUDIO_STYLE_ROOT = ROOT / "studio" / "app" / "src" / "styles"
GENERATED_CSS_PATH = STUDIO_STYLE_ROOT / "vendor" / "weiui.generated.css"
GENERATED_TOKENS_PATH = STUDIO_STYLE_ROOT / "vendor" / "weiui.tokens.generated.css"
# The Studio now has one CSS entrypoint. Treat every top-level stylesheet it
# composes as custom product CSS instead of pinning a stale filename list.
STUDIO_CUSTOM_CSS_PATHS = sorted(
    path for path in STUDIO_STYLE_ROOT.glob("*.css") if path.name != "index.css"
)


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


def weiui_config_fingerprint(normalized: dict) -> str:
    # Matches @weiui/css/config: JSON.stringify(normalized) with the contract's
    # fixed insertion order and already-sorted selection arrays.
    rendered = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def normalized_weiui_config(value: dict) -> dict:
    allowed = {"schema", "foundation", "a11y", "elements", "utilities", "output"}
    require(not (set(value) - allowed), "WeiUI config has unknown top-level keys")
    require(value.get("schema") == "weiui_css_config_v1", "unexpected WeiUI config schema")
    require(isinstance(value.get("foundation", True), bool), "WeiUI foundation must be boolean")
    normalized: dict[str, object] = {
        "schema": "weiui_css_config_v1",
        "foundation": value.get("foundation", True),
    }
    for key in ("a11y", "elements", "utilities"):
        items = value.get(key, [])
        require(isinstance(items, list) and all(isinstance(item, str) and item.strip() for item in items), f"WeiUI {key} must be string list")
        normalized[key] = sorted(set(item.strip() for item in items))
    output = value.get("output", "weiui.generated.css")
    require(isinstance(output, str) and output.strip(), "WeiUI config output must be non-empty string")
    require(not Path(output).is_absolute() and ".." not in Path(output).parts, "WeiUI config output must remain project-relative")
    normalized["output"] = output.strip()
    return normalized


def main() -> int:
    tokens = load(TOKENS_PATH)
    integration = load(INTEGRATION_PATH)
    provenance = load(PROVENANCE_PATH)
    config = load(APP_CONFIG_PATH)
    css = THEME_PATH.read_text(encoding="utf-8")

    require(tokens.get("schema") == "quillframe_brand_tokens_v2", "unexpected token schema")
    require(integration.get("schema") == "quillframe_weiui_integration_v2", "unexpected WeiUI integration schema")

    source = integration.get("source", {})
    require(source.get("repository") == "xiaooye/weiui", "WeiUI source repository must be exact")
    commit = str(source.get("commit", ""))
    require(bool(re.fullmatch(r"[0-9a-f]{40}", commit)), "WeiUI source must pin an exact commit")
    require(source.get("license") == "MIT", "WeiUI license provenance must be MIT")

    consumption = integration.get("consumption", {})
    require(consumption.get("phase_2c_framework") == "SolidJS", "Phase 2C framework must remain SolidJS")
    require(consumption.get("theme_layer") == "wui-theme", "consumer theme layer must be wui-theme")
    require(consumption.get("runtime_javascript_from_weiui") is False, "Studio foundation must not require WeiUI runtime JavaScript")
    require(consumption.get("allowed_packages") == ["@weiui/tokens", "@weiui/css"], "allowed WeiUI packages drifted")
    forbidden = set(consumption.get("forbidden_runtime_packages", []))
    require({"@weiui/headless", "@weiui/react"}.issubset(forbidden), "Solid Studio must forbid React runtime packages")
    require(consumption.get("generic_component_css_owner") == "@weiui/css", "WeiUI must own generic Studio component CSS")
    require(consumption.get("story_loom_css_scope") == "theme_tokens_and_product_identity", "Story Loom CSS scope drifted")
    require(consumption.get("studio_custom_css_scope") == "composition_layout_and_quillframe_specific_information_architecture", "Studio custom CSS scope drifted")
    require(consumption.get("custom_generic_component_chrome_allowed") is False, "Studio must not fork generic component chrome")
    required_generic_primitives = set(consumption.get("required_generic_primitives", []))
    require(required_generic_primitives == {
        "alert", "app-bar", "badge", "bottom-nav", "button", "card", "code",
        "command-palette", "empty-state", "input", "sidebar",
    }, "required generic WeiUI primitive set drifted")

    delivery = consumption.get("css_delivery", {})
    require(delivery.get("mode") == "config_generated_checked_in", "WeiUI CSS delivery must remain config-generated + checked-in")
    require(delivery.get("config_schema") == "weiui_css_config_v1", "unexpected WeiUI config contract")
    require(delivery.get("manifest_schema") == "weiui_css_bundle_manifest_v1", "unexpected WeiUI bundle manifest contract")
    require(delivery.get("config_path") == APP_CONFIG_PATH.relative_to(ROOT).as_posix(), "WeiUI config path drifted")
    require(delivery.get("generated_css") == GENERATED_CSS_PATH.relative_to(ROOT).as_posix(), "generated CSS path drifted")
    require(delivery.get("generated_tokens") == GENERATED_TOKENS_PATH.relative_to(ROOT).as_posix(), "generated tokens path drifted")
    require(delivery.get("tokens_remain_separate") is True, "WeiUI tokens must remain an explicit separate artifact")
    require(delivery.get("regeneration_requires_exact_pin") is True, "WeiUI regeneration must bind exact source pin")

    normalized_config = normalized_weiui_config(config)
    require(normalized_config["foundation"] is True, "Studio WeiUI bundle must retain foundation")
    require(set(normalized_config["a11y"]) == {"focus", "motion", "sr-only"}, "Studio WeiUI bundle must retain focus/motion/sr-only a11y fragments")
    require(required_generic_primitives.issubset(set(normalized_config["elements"])), "Studio WeiUI bundle is missing a required generic primitive")
    require("*" not in normalized_config["elements"], "Studio must use an explicit on-demand element selection")
    config_fp = weiui_config_fingerprint(normalized_config)

    require(GENERATED_CSS_PATH.is_file(), "generated WeiUI CSS is missing")
    require(GENERATED_TOKENS_PATH.is_file(), "generated WeiUI tokens CSS is missing")
    generated_css = GENERATED_CSS_PATH.read_text(encoding="utf-8")
    generated_tokens = GENERATED_TOKENS_PATH.read_text(encoding="utf-8")
    require("Generated by @weiui/css config layer" in generated_css, "generated WeiUI CSS provenance header missing")
    require(f"config-fingerprint: {config_fp}" in generated_css, "generated WeiUI CSS fingerprint does not bind current config")
    require("manifest-schema: weiui_css_bundle_manifest_v1" in generated_css, "generated WeiUI manifest provenance missing")
    for selector in (
        ".wui-alert", ".wui-app-bar", ".wui-badge", ".wui-bottom-nav", ".wui-button",
        ".wui-card", ".wui-code-block", ".wui-command", ".wui-empty-state", ".wui-input", ".wui-sidebar",
    ):
        require(selector in generated_css, f"generated WeiUI CSS missing {selector}")
    require(".wui-dialog" not in generated_css, "generated WeiUI CSS unexpectedly contains unselected dialog fragment")
    require("@layer wui-reset, wui-tokens, wui-theme, wui-base, wui-elements, wui-utilities;" in generated_css, "generated WeiUI cascade registration missing")
    require("--wui-color-background" in generated_tokens, "generated WeiUI token artifact looks incomplete")

    custom_css = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_CUSTOM_CSS_PATHS)
    require("!important" not in custom_css, "Studio custom CSS must not fight WeiUI with !important")
    for forbidden_selector in (
        ".nf-status", ".nf-alert {", ".nf-card-sunken", ".nf-bottom-nav-item[data-active",
    ):
        require(forbidden_selector not in custom_css, f"Studio custom CSS reimplements WeiUI chrome: {forbidden_selector}")
    app_shell = (ROOT / "studio" / "app" / "src" / "AppShell.tsx").read_text(encoding="utf-8")
    components = (ROOT / "studio" / "app" / "src" / "components.tsx").read_text(encoding="utf-8")
    observability_ui = (ROOT / "studio" / "app" / "src" / "observability-ui.tsx").read_text(encoding="utf-8")
    observability_routes = "\n".join(
        (ROOT / "studio" / "app" / "src" / "routes" / name).read_text(encoding="utf-8")
        for name in ("Semantic.tsx", "Diagnostics.tsx")
    )
    for required_usage in (
        "wui-sidebar", "wui-app-bar", "wui-bottom-nav", "wui-command", "wui-button", "wui-badge",
    ):
        require(required_usage in app_shell, f"Studio shell is not based on WeiUI primitive {required_usage}")
    for required_usage in ("wui-card", "wui-alert", "wui-code-block"):
        require(required_usage in components, f"shared Studio component is not based on WeiUI primitive {required_usage}")
    for required_usage in ("wui-alert", "wui-badge"):
        require(required_usage in observability_ui, f"observability utility is not based on WeiUI primitive {required_usage}")
    require("wui-card" in observability_routes, "live observability routes are not based on WeiUI primitive wui-card")

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
    require(performance.get("weiui_runtime_javascript_required") is False, "WeiUI JS runtime must remain absent")
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
        "--qf-lane-project-fill", "--qf-lane-runtime-fill", "--qf-touch-target-min",
    ):
        require(variable in css, f"theme CSS missing {variable}")

    assets = {item.get("id"): item for item in provenance.get("assets", []) if isinstance(item, dict)}
    required_provenance = {
        "brand-tokens-v2", "weiui-integration-v2", "story-loom-weiui-theme-v1",
        "weiui-studio-bundle-config-v1", "weiui-studio-generated-css-v1", "weiui-studio-generated-tokens-v1",
    }
    require(required_provenance.issubset(assets), "design-system/generated-bundle provenance is incomplete")
    for asset_id in ("weiui-integration-v2", "story-loom-weiui-theme-v1", "weiui-studio-generated-css-v1", "weiui-studio-generated-tokens-v1"):
        require(commit in str(assets[asset_id].get("license_note", "")), f"{asset_id} provenance must bind exact WeiUI commit")

    print(json.dumps({
        "schema": "quillframe_story_loom_design_system_check_v2",
        "status": "pass",
        "weiui_commit": commit,
        "weiui_config_fingerprint": config_fp,
        "generated_css_bytes": GENERATED_CSS_PATH.stat().st_size,
        "generated_tokens_bytes": GENERATED_TOKENS_PATH.stat().st_size,
        "theme_layer": consumption["theme_layer"],
        "generic_component_css_owner": consumption["generic_component_css_owner"],
        "studio_custom_css_scope": consumption["studio_custom_css_scope"],
        "runtime_javascript_from_weiui": False,
        "minimum_touch_target_px": interaction["minimum_touch_target_px"],
        "baseline_locales": i18n["baseline_locales"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
