from __future__ import annotations

import logging
import threading

from core.enums import JobType
from db.repositories.poll_jobs import PollJobsRepository
from db.repositories.shops import ShopsRepository


class Scheduler:
    def __init__(
        self,
        shops: ShopsRepository,
        poll_jobs: PollJobsRepository,
        sleep_seconds: int,
        max_retry: int,
        logger: logging.Logger,
    ) -> None:
        self.shops = shops
        self.poll_jobs = poll_jobs
        self.sleep_seconds = sleep_seconds
        self.max_retry = max_retry
        self.logger = logger
        self.stop_event = threading.Event()

    def run(self) -> None:
        while not self.stop_event.is_set():
            for shop in self.shops.list_due():
                enqueued = False
                for job_type in (JobType.SYNC_ORDERS.value, JobType.SYNC_RETURNS.value):
                    if self.poll_jobs.enqueue_if_missing(shop.id, job_type, self.max_retry):
                        enqueued = True
                if enqueued:
                    self.logger.info("Queued jobs for shop=%s", shop.code)
                self.shops.schedule_next_poll(shop.id, shop.poll_interval_seconds)
            self.stop_event.wait(self.sleep_seconds)

    def stop(self) -> None:
        self.stop_event.set()
