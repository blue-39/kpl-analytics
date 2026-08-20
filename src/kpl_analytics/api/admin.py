from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock, Thread
from typing import Any
from uuid import uuid4

ProgressUpdate = Callable[[str, dict[str, Any] | None], None]
JobOperation = Callable[[ProgressUpdate], dict[str, Any]]


class JobBusyError(RuntimeError):
    pass


class JobManager:
    """Runs one trusted maintenance operation at a time in a background thread."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._job: dict[str, Any] = {
            "id": None,
            "kind": None,
            "status": "idle",
            "message": "暂无任务",
            "progress": {},
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._job)

    def start(self, kind: str, operation: JobOperation) -> dict[str, Any]:
        with self._lock:
            if self._job["status"] == "running":
                raise JobBusyError("已有数据任务正在运行，请等待它完成。")
            job_id = uuid4().hex
            self._job = {
                "id": job_id,
                "kind": kind,
                "status": "running",
                "message": "任务已启动",
                "progress": {},
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": None,
                "result": None,
                "error": None,
            }

        Thread(
            target=self._run,
            args=(job_id, operation),
            name=f"kpl-{kind}-{job_id[:8]}",
            daemon=True,
        ).start()
        return self.snapshot()

    def _run(self, job_id: str, operation: JobOperation) -> None:
        def update(message: str, progress: dict[str, Any] | None = None) -> None:
            with self._lock:
                if self._job["id"] != job_id or self._job["status"] != "running":
                    return
                self._job["message"] = message
                if progress is not None:
                    self._job["progress"] = deepcopy(progress)

        try:
            result = operation(update)
        except Exception as exc:  # Background failures must be visible in the UI.
            with self._lock:
                if self._job["id"] == job_id:
                    self._job.update(
                        status="failed",
                        message="任务执行失败",
                        finished_at=datetime.now(UTC).isoformat(),
                        error=str(exc)[:1000],
                    )
            return

        with self._lock:
            if self._job["id"] == job_id:
                self._job.update(
                    status="succeeded",
                    message="任务执行完成",
                    finished_at=datetime.now(UTC).isoformat(),
                    result=deepcopy(result),
                )
