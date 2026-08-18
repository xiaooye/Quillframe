#!/usr/bin/env python3
"""Codex compatibility wrapper for Quillframe's unified host bootstrap."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from host_bootstrap import main_for_host  # noqa: E402


def main() -> int:
    return main_for_host("codex")


if __name__ == "__main__":
    raise SystemExit(main())
