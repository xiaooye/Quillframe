"""Shared hard timing bounds; these limits do not authorize model calls."""

from __future__ import annotations

import math


DEADLINE_HEADER = "X-Quillframe-Deadline-Unix-Ms"
REQUEST_KEY_HEADER = "X-Quillframe-Model-Request-Key"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180.0
# Active production workers may legitimately outlive an interactive client.
# Production jobs use this finite value for initial admission and each HTTP
# poll. A launched keyed CLI worker is heartbeat-governed and has no default
# process-lifetime timeout; this value is not its lifetime.
MAX_REQUEST_TIMEOUT_SECONDS = 86_400.0
DURABLE_REQUEST_TIMEOUT_MS = int(MAX_REQUEST_TIMEOUT_SECONDS * 1000)
DEFAULT_RELAY_TIMEOUT_SECONDS = 170.0
MAX_RELAY_TIMEOUT_SECONDS = 86_390.0
RELAY_RESPONSE_RESERVE_SECONDS = 10.0
DEFAULT_RELAY_RESPONSE_WAIT_SECONDS = 5.0
DEFAULT_WORKER_TIMEOUT_SECONDS = 150.0
MAX_WORKER_TIMEOUT_SECONDS = 86_370.0
PUBLISH_RESERVE_SECONDS = 5.0


def validate_request_timeout(value: float) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0 < value <= MAX_REQUEST_TIMEOUT_SECONDS or not math.isfinite(value)):
        raise ValueError("model timeout must be finite, positive and at most 86400 seconds")
    return float(value)
