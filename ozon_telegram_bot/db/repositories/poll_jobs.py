from __future__ import annotations

from datetime import timedelta

from core.enums import JobStatus
from core.models import PollJob
from core.utils import utcnow
from db.session import Database


class PollJobsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def enqueue_if_missing(
        self,
        shop_id: int,
        job_type: str,
        max_retry: int,
    ) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO poll_jobs (shop_id, job_type, status, max_retry, next_run_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (shop_id, job_type, JobStatus.QUEUED.value, max_retry),
            ).fetchone()
            conn.commit()
        return row is not None

    def claim_next(self, worker_id: str) -> PollJob | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                WITH candidate AS (
                    SELECT id
                    FROM poll_jobs
                    WHERE status = %s
                      AND next_run_at <= NOW()
                    ORDER BY next_run_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE poll_jobs AS jobs
                SET status = %s,
                    locked_at = NOW(),
                    locked_by = %s,
                    updated_at = NOW()
                FROM candidate
                WHERE jobs.id = candidate.id
                RETURNING jobs.id, jobs.shop_id, jobs.job_type, jobs.status, jobs.retry_count,
                          jobs.max_retry, jobs.next_run_at, jobs.locked_at, jobs.locked_by, jobs.last_error
                """,
                (JobStatus.QUEUED.value, JobStatus.RUNNING.value, worker_id),
            ).fetchone()
            conn.commit()
        return PollJob(**row) if row else None

    def mark_done(self, job_id: int) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE poll_jobs
                SET status = %s,
                    locked_at = NULL,
                    locked_by = NULL,
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (JobStatus.DONE.value, job_id),
            )
            conn.commit()

    def mark_retry_or_failed(self, job: PollJob, error_message: str) -> None:
        retry_count = job.retry_count + 1
        failed = retry_count > job.max_retry
        status = JobStatus.FAILED.value if failed else JobStatus.QUEUED.value
        delay_seconds = min(300, 2**min(retry_count, 8))
        next_run_at = utcnow() + timedelta(seconds=delay_seconds)
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE poll_jobs
                SET status = %s,
                    retry_count = %s,
                    next_run_at = %s,
                    locked_at = NULL,
                    locked_by = NULL,
                    last_error = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, retry_count, next_run_at, error_message[:2000], job.id),
            )
            conn.commit()
