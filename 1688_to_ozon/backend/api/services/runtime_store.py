from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .dashboard_store import load_job_history, refresh_dashboard_files


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class JobRecord:
    job_id: str
    status: str = "pending"
    message: str = "Job queued"
    source: str = ""
    mode: str = ""
    error: str | None = None
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    progress: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "message": self.message,
            "source": self.source,
            "mode": self.mode,
            "error": self.error,
            "total": self.total,
            "processed": self.processed,
            "success": self.success,
            "failed": self.failed,
            "progress": dict(self.progress),
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RuntimeStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._files: dict[str, Path] = {}
        self._load_history()

    def _load_history(self) -> None:
        for payload in load_job_history():
            job_id = str(payload.get("job_id") or "").strip()
            if not job_id:
                continue
            self._jobs[job_id] = JobRecord(
                job_id=job_id,
                status=str(payload.get("status") or "pending"),
                message=str(payload.get("message") or "Job queued"),
                source=str(payload.get("source") or ""),
                mode=str(payload.get("mode") or ""),
                error=str(payload.get("error")) if payload.get("error") is not None else None,
                total=int(payload.get("total") or 0),
                processed=int(payload.get("processed") or 0),
                success=int(payload.get("success") or 0),
                failed=int(payload.get("failed") or 0),
                progress=dict(payload.get("progress") or {}),
                result=payload.get("result"),
                created_at=str(payload.get("created_at") or _utc_now()),
                updated_at=str(payload.get("updated_at") or _utc_now()),
            )

    def _persist(self) -> None:
        refresh_dashboard_files([record.to_dict() for record in self._jobs.values()])

    def create_job(
        self,
        message: str = "Job queued",
        *,
        source: str = "",
        mode: str = "",
    ) -> JobRecord:
        with self._lock:
            record = JobRecord(
                job_id=uuid4().hex,
                message=message,
                source=source,
                mode=mode,
            )
            self._jobs[record.job_id] = record
            self._persist()
            return record

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
        error: str | None = None,
        total: int | None = None,
        processed: int | None = None,
        success: int | None = None,
        failed: int | None = None,
        progress: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
    ) -> JobRecord:
        with self._lock:
            record = self._jobs[job_id]
            if status is not None:
                record.status = status
            if message is not None:
                record.message = message
            if error is not None:
                record.error = error
            if total is not None:
                record.total = max(total, 0)
            if processed is not None:
                record.processed = max(processed, 0)
            if success is not None:
                record.success = max(success, 0)
            if failed is not None:
                record.failed = max(failed, 0)
            if progress is not None:
                record.progress = dict(progress)
            if result is not None:
                record.result = result
            record.updated_at = _utc_now()
            self._persist()
            return record

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def register_file(self, path: Path) -> tuple[str, Path]:
        with self._lock:
            file_id = uuid4().hex
            self._files[file_id] = path
            return file_id, path

    def get_file(self, file_id: str) -> Path | None:
        with self._lock:
            return self._files.get(file_id)


runtime_store = RuntimeStore()
