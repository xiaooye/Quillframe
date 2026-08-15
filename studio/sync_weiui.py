#!/usr/bin/env python3
"""Regenerate/verify Studio's checked-in WeiUI CSS from the exact integration pin.

The script deliberately does not clone or fetch repositories. The caller must
provide a WeiUI checkout, which CI pins independently. This keeps network and
source acquisition separate from deterministic artifact generation.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "assets" / "brand" / "weiui.integration.json"
CONFIG = ROOT / "studio" / "app" / "weiui.config.json"
CSS_TARGET = ROOT / "studio" / "app" / "src" / "styles" / "vendor" / "weiui.generated.css"
TOKENS_TARGET = ROOT / "studio" / "app" / "src" / "styles" / "vendor" / "weiui.tokens.generated.css"


def run(argv: list[str], cwd: Path) -> None:
    proc = subprocess.run(argv, cwd=str(cwd), text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(argv)}")


def output(argv: list[str], cwd: Path) -> str:
    return subprocess.check_output(argv, cwd=str(cwd), text=True).strip()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_checkout(weiui_root: Path, expected: str) -> None:
    actual = output(["git", "rev-parse", "HEAD"], weiui_root)
    if actual != expected:
        raise SystemExit(f"WeiUI checkout mismatch: expected {expected}, got {actual}")


def build_upstream(weiui_root: Path) -> None:
    run(["pnpm", "install", "--frozen-lockfile"], weiui_root)
    run(["pnpm", "--filter", "@weiui/a11y", "build"], weiui_root)
    run(["pnpm", "--filter", "@weiui/tokens", "build"], weiui_root)
    run(["pnpm", "--filter", "@weiui/css", "build"], weiui_root)
    run(["pnpm", "--filter", "@weiui/css", "test"], weiui_root)


def generate(weiui_root: Path, consumer_root: Path) -> tuple[Path, Path]:
    config_copy = consumer_root / "studio" / "app" / "weiui.config.json"
    config_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CONFIG, config_copy)
    cli = weiui_root / "packages" / "css" / "dist" / "config-cli.mjs"
    run(["node", str(cli), "bundle", str(config_copy)], weiui_root)
    config = load(config_copy)
    css = config_copy.parent / config["output"]
    tokens = consumer_root / "studio" / "app" / "src" / "styles" / "vendor" / "weiui.tokens.generated.css"
    tokens.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(weiui_root / "packages" / "tokens" / "dist" / "tokens.css", tokens)
    return css, tokens


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate or verify exact-pinned WeiUI artifacts for Studio")
    parser.add_argument("--weiui-root", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    integration = load(INTEGRATION)
    if integration.get("schema") != "novelforge_weiui_integration_v2":
        raise SystemExit("unexpected NovelForge WeiUI integration schema")
    expected = integration.get("source", {}).get("commit")
    if not isinstance(expected, str) or len(expected) != 40:
        raise SystemExit("WeiUI integration does not contain an exact commit")

    weiui_root = Path(args.weiui_root).resolve()
    assert_checkout(weiui_root, expected)
    build_upstream(weiui_root)

    with tempfile.TemporaryDirectory(prefix="novelforge-weiui-sync-") as temp:
        generated_css, generated_tokens = generate(weiui_root, Path(temp))
        if args.write:
            CSS_TARGET.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(generated_css, CSS_TARGET)
            shutil.copy2(generated_tokens, TOKENS_TARGET)
            status = "written"
        else:
            if not CSS_TARGET.is_file() or not TOKENS_TARGET.is_file():
                raise SystemExit("checked-in WeiUI generated artifacts are missing")
            if not filecmp.cmp(generated_css, CSS_TARGET, shallow=False):
                raise SystemExit("checked-in WeiUI CSS does not match exact-pinned regeneration")
            if not filecmp.cmp(generated_tokens, TOKENS_TARGET, shallow=False):
                raise SystemExit("checked-in WeiUI tokens do not match exact-pinned regeneration")
            status = "verified"

    print(json.dumps({
        "schema": "novelforge_weiui_sync_v1",
        "status": status,
        "weiui_commit": expected,
        "config": CONFIG.relative_to(ROOT).as_posix(),
        "generated_css": CSS_TARGET.relative_to(ROOT).as_posix(),
        "generated_tokens": TOKENS_TARGET.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
