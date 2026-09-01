"""Host-owned event coordinator for already-authorized production executions."""
from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


class ProductionCoordinator:
    def __init__(
        self,
        runtime_factory: Callable[[], Any],
        project_ids: Callable[[], Iterable[str]],
        *,
        interval_seconds: float = 5.0,
    ) -> None:
        if not 0.5 <= interval_seconds <= 10.0:
            raise ValueError("interval_seconds must be from 0.5 to 10 seconds")
        self.runtime_factory = runtime_factory
        self.project_ids = project_ids
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def tick(self) -> list[dict[str, Any]]:
        projects = sorted({
            project_id for project_id in self.project_ids()
            if isinstance(project_id, str) and project_id
        })
        reports: list[dict[str, Any]] = []
        if projects:
            with ThreadPoolExecutor(
                max_workers=min(8, len(projects)),
                thread_name_prefix="qf-production-project",
            ) as pool:
                futures = {
                    pool.submit(self.runtime_factory().resume_ready_runs, project_id): project_id
                    for project_id in projects
                }
                for future in as_completed(futures):
                    reports.append(future.result())
        reports.sort(key=lambda item: str(item.get("project_id") or ""))
        return reports

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    self.tick()
                except Exception:
                    # One tick never terminates the host. Durable wakes remain
                    # unconsumed and will be retried on the next interval.
                    pass
                self._stop.wait(self.interval_seconds)

        self._thread = threading.Thread(target=loop, name="quillframe-production-coordinator", daemon=True)
        self._thread.start()

    def stop(self, *, timeout: float = 10.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
            if not thread.is_alive():
                self._thread = None
