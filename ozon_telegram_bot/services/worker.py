from __future__ import annotations

import logging
import socket
import threading

from app.settings import Settings
from core.enums import JobType
from db.repositories.poll_jobs import PollJobsRepository
from db.repositories.shop_channels import ShopChannelsRepository
from db.repositories.shop_credentials import ShopCredentialsRepository
from db.repositories.shops import ShopsRepository
from integrations.ozon_client import OzonClient
from services.polling import PollingService
from services.rate_limit import SimpleRateLimiter


class Worker:
    def __init__(
        self,
        settings: Settings,
        worker_name: str,
        shops: ShopsRepository,
        credentials: ShopCredentialsRepository,
        channels: ShopChannelsRepository,
        poll_jobs: PollJobsRepository,
        polling: PollingService,
        sleep_seconds: int,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.worker_name = worker_name
        self.shops = shops
        self.credentials = credentials
        self.channels = channels
        self.poll_jobs = poll_jobs
        self.polling = polling
        self.sleep_seconds = sleep_seconds
        self.logger = logger
        self.stop_event = threading.Event()

    def run(self) -> None:
        while not self.stop_event.is_set():
            job = self.poll_jobs.claim_next(self.worker_name)
            if job is None:
                self.stop_event.wait(self.sleep_seconds)
                continue
            try:
                self._process_job(job)
                self.poll_jobs.mark_done(job.id)
            except Exception as exc:  # pragma: no cover
                shop = self.shops.get_by_id(job.shop_id)
                shop_code = shop.code if shop is not None else "unknown"
                shop_name = shop.name if shop is not None else "unknown"
                self.logger.exception(
                    "Worker failed for job=%s shop_id=%s shop_code=%s shop_name=%s job_type=%s: %s",
                    job.id,
                    job.shop_id,
                    shop_code,
                    shop_name,
                    job.job_type,
                    exc,
                )
                self.poll_jobs.mark_retry_or_failed(job, str(exc))

    def stop(self) -> None:
        self.stop_event.set()

    def _process_job(self, job) -> None:
        shop = self.shops.get_by_id(job.shop_id)
        if shop is None:
            raise RuntimeError(f"Shop {job.shop_id} not found")
        self.logger.info(
            "Processing job=%s shop_id=%s shop_code=%s shop_name=%s job_type=%s",
            job.id,
            shop.id,
            shop.code,
            shop.name,
            job.job_type,
        )
        credential = self.credentials.get_active(shop.id)
        if credential is None:
            raise RuntimeError(f"No active Ozon credential for shop {shop.code}")
        channels = self.channels.list_active(shop.id)
        ozon_client = OzonClient(
            client_id=credential.client_id,
            api_key=credential.api_key,
            base_url=self.settings.ozon_base_url,
            shop_name=shop.name,
            timeout_seconds=self.settings.request_timeout_seconds,
            retry_attempts=self.settings.ozon_retry_attempts,
            retry_backoff_seconds=self.settings.ozon_retry_backoff_seconds,
            rate_limiter=SimpleRateLimiter(self.settings.ozon_rate_limit_per_second),
            logger=self.logger,
        )
        if job.job_type == JobType.SYNC_ORDERS.value:
            self.polling.sync_orders(shop, channels, ozon_client)
        elif job.job_type == JobType.SYNC_RETURNS.value:
            self.polling.sync_returns(shop, channels, ozon_client)
        else:
            raise RuntimeError(f"Unsupported job type {job.job_type}")


def default_worker_name() -> str:
    return f"{socket.gethostname()}-worker"
