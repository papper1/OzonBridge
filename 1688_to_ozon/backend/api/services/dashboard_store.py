from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from config import APP_DATA_DIR, CLEAN_DATA_DIR, EXPORT_DIR, RAW_DATA_DIR, ensure_directories


JOB_HISTORY_PATH = APP_DATA_DIR / "job_history.json"
RECENT_JOBS_PATH = APP_DATA_DIR / "recent_jobs.json"
DASHBOARD_SUMMARY_PATH = APP_DATA_DIR / "dashboard_summary.json"

SUPPORTED_SOURCES = ("1688", "SHEIN", "Etsy", "eBay")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_json_atomic(path: Path, payload: Any) -> None:
    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2)
        temp_path = Path(temp_file.name)
    temp_path.replace(path)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_job_history() -> list[dict[str, Any]]:
    payload = _read_json(JOB_HISTORY_PATH, default=[])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def save_job_history(records: list[dict[str, Any]]) -> None:
    normalized = [dict(record) for record in records]
    _write_json_atomic(JOB_HISTORY_PATH, normalized)


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.rglob(pattern))


def _normalize_job(record: dict[str, Any]) -> dict[str, Any]:
    def _as_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    status = str(record.get("status") or "").strip().lower()
    total = _as_int(record.get("total"))
    processed = _as_int(record.get("processed"))
    success = _as_int(record.get("success"))
    failed = _as_int(record.get("failed"))
    updated_at = str(record.get("updated_at") or record.get("updatedAt") or "")

    return {
        "job_id": str(record.get("job_id") or record.get("id") or ""),
        "source": str(record.get("source") or "").strip(),
        "mode": str(record.get("mode") or "").strip(),
        "status": status,
        "message": str(record.get("message") or "").strip(),
        "total": max(total, 0),
        "processed": max(processed, 0),
        "success": max(success, 0),
        "failed": max(failed, 0),
        "updated_at": updated_at,
    }


def write_recent_jobs(records: list[dict[str, Any]]) -> None:
    jobs = [_normalize_job(record) for record in records if record.get("job_id") or record.get("id")]
    jobs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    payload = {
        "generated_at": _utc_now(),
        "items": jobs[:20],
    }
    _write_json_atomic(RECENT_JOBS_PATH, payload)


def write_dashboard_summary(records: list[dict[str, Any]]) -> None:
    normalized_jobs = [_normalize_job(record) for record in records]
    completed_jobs = [
        job for job in normalized_jobs if job["status"] in {"success", "failed"}
    ]

    history_total = sum(job["total"] for job in completed_jobs)
    history_success = sum(job["success"] for job in completed_jobs)
    history_failed = sum(job["failed"] for job in completed_jobs)

    clean_count = _count_files(CLEAN_DATA_DIR, "*.json")
    raw_count = _count_files(RAW_DATA_DIR, "*.json")
    export_count = _count_files(EXPORT_DIR, "*.xlsx")

    total_crawled_products = history_total if history_total > 0 else max(raw_count, clean_count)
    successful_products = history_success if history_total > 0 else clean_count
    failed_products = history_failed if history_total > 0 else max(raw_count - clean_count, 0)

    denominator = total_crawled_products if total_crawled_products > 0 else successful_products + failed_products
    success_rate = round((successful_products / denominator) * 100, 1) if denominator > 0 else 0.0

    payload = {
        "generated_at": _utc_now(),
        "supported_sources": list(SUPPORTED_SOURCES),
        "supported_sources_count": len(SUPPORTED_SOURCES),
        "total_crawled_products": total_crawled_products,
        "successful_products": successful_products,
        "failed_products": failed_products,
        "success_rate": success_rate,
        "exported_files": export_count,
    }
    _write_json_atomic(DASHBOARD_SUMMARY_PATH, payload)


def refresh_dashboard_files(records: list[dict[str, Any]] | None = None) -> None:
    history = load_job_history() if records is None else [dict(record) for record in records]
    save_job_history(history)
    write_recent_jobs(history)
    write_dashboard_summary(history)


if __name__ == "__main__":
    refresh_dashboard_files()
