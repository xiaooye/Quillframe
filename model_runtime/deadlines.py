"""Shared hard timing bounds; these limits do not authorize model calls."""

from __future__ import annotations

import math


DEADLINE_HEADER = "X-Quillframe-Deadline-Unix-Ms"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180.0
MAX_REQUEST_TIMEOUT_SECONDS = 600.0
DEFAULT_RELAY_TIMEOUT_SECONDS = 170.0
MAX_RELAY_TIMEOUT_SECONDS = 590.0
RELAY_RESPONSE_RESERVE_SECONDS = 10.0
DEFAULT_WORKER_TIMEOUT_SECONDS = 150.0
MAX_WORKER_TIMEOUT_SECONDS = 570.0
PUBLISH_RESERVE_SECONDS = 5.0


def validate_request_timeout(value: float) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0 < value <= MAX_REQUEST_TIMEOUT_SECONDS or not math.isfinite(value)):
        raise ValueError("model timeout must be finite, positive and at most 600 seconds")
    return float(value)
