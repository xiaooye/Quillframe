"""Regression coverage for the loopback Studio Core command lane."""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from studio import local_server


class LocalServerBridgeSerializationTests(unittest.TestCase):
    def test_concurrent_http_requests_enter_host_bridge_one_at_a_time(self) -> None:
        with tempfile.TemporaryDirectory(prefix="quillframe-local-server-") as temporary:
            dist = Path(temporary)
            (dist / "index.html").write_text(
                "<meta name='quillframe-studio-token' content='__QUILLFRAME_STUDIO_TOKEN__'>",
                encoding="utf-8",
            )
            active = 0
            maximum_active = 0
            guard = threading.Lock()

            def fake_invoke(request):
                nonlocal active, maximum_active
                with guard:
                    active += 1
                    maximum_active = max(maximum_active, active)
                try:
                    time.sleep(0.02)
                    return {"schema": "test_result", "request_id": request["request_id"]}
                finally:
                    with guard:
                        active -= 1

            server = local_server.create_server(dist, token="serialization-token")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def send(index: int) -> str:
                body = json.dumps({
                    "schema": "test_request",
                    "request_id": f"request-{index}",
                }).encode("utf-8")
                request = urllib.request.Request(
                    base + "/api/bridge/invoke",
                    method="POST",
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Quillframe-Studio-Token": "serialization-token",
                        "Origin": base,
                        "Sec-Fetch-Site": "same-origin",
                    },
                )
                return json.loads(urllib.request.urlopen(request, timeout=5).read())["request_id"]

            try:
                with patch.object(local_server, "invoke", side_effect=fake_invoke):
                    with ThreadPoolExecutor(max_workers=8) as pool:
                        request_ids = list(pool.map(send, range(8)))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

        self.assertEqual(set(request_ids), {f"request-{index}" for index in range(8)})
        self.assertEqual(maximum_active, 1)


if __name__ == "__main__":
    unittest.main()
