from __future__ import annotations

import logging
import threading

from app.settings import Settings
from db.repositories.command_log import CommandLogRepository
from db.repositories.notification_log import NotificationLogRepository
from db.repositories.order_state import OrderStateRepository
from db.repositories.poll_jobs import PollJobsRepository
from db.repositories.return_state import ReturnStateRepository
from db.repositories.shop_channels import ShopChannelsRepository
from db.repositories.shop_credentials import ShopCredentialsRepository
from db.repositories.shops import ShopsRepository
from db.schema import create_schema
from db.session import Database
from formatters.message_formatter import MessageFormatter
from integrations.lark_client import LarkWebhookClient
from integrations.telegram_client import TelegramBotClient
from services.command_router import CommandRouter
from services.command_server import CommandServer
from services.notifications import NotificationService
from services.polling import PollingService
from services.scheduler import Scheduler
from services.worker import Worker, default_worker_name


class Container:
    def __init__(
        self,
        settings: Settings,
        logger: logging.Logger,
        *,
        enable_command_server: bool = True,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.database = Database(settings.database_url)
        create_schema(self.database)

        self.shops = ShopsRepository(self.database)
        self.credentials = ShopCredentialsRepository(self.database)
        self.channels = ShopChannelsRepository(self.database)
        self.poll_jobs = PollJobsRepository(self.database)
        self.order_states = OrderStateRepository(self.database)
        self.return_states = ReturnStateRepository(self.database)
        self.notification_logs = NotificationLogRepository(self.database)
        self.command_logs = CommandLogRepository(self.database)
        self.formatter = MessageFormatter()
        self.lark_client = LarkWebhookClient(settings.request_timeout_seconds, logger)
        self.telegram_client = TelegramBotClient(settings.request_timeout_seconds, logger)
        self.notifications = NotificationService(
            self.notification_logs,
            self.lark_client,
            self.telegram_client,
            logger,
        )
        self.polling = PollingService(
            self.order_states,
            self.return_states,
            self.notifications,
            self.formatter,
            logger,
        )
        self.scheduler = Scheduler(
            shops=self.shops,
            poll_jobs=self.poll_jobs,
            sleep_seconds=settings.scheduler_sleep_seconds,
            max_retry=settings.default_max_retry,
            logger=logger,
        )
        self.worker = Worker(
            settings=settings,
            worker_name=default_worker_name(),
            shops=self.shops,
            credentials=self.credentials,
            channels=self.channels,
            poll_jobs=self.poll_jobs,
            polling=self.polling,
            sleep_seconds=settings.worker_sleep_seconds,
            logger=logger,
        )
        self.command_router = None
        self.command_server = None
        if enable_command_server:
            self.command_router = CommandRouter(
                settings=settings,
                shops=self.shops,
                credentials=self.credentials,
                order_states=self.order_states,
                return_states=self.return_states,
                notification_logs=self.notification_logs,
                command_logs=self.command_logs,
                formatter=self.formatter,
                logger=logger,
            )
            self.command_server = CommandServer(
                host=settings.lark_command_host,
                port=settings.lark_command_port,
                telegram_bot_token=settings.telegram_command_bot_token,
                allowed_chat_ids=settings.telegram_allowed_chat_ids,
                router=self.command_router,
                shop_channels=self.channels,
                lark_client=self.lark_client,
                telegram_client=self.telegram_client,
                logger=logger,
            )

    def run_all(self) -> None:
        self.notify_startup()
        threads: list[threading.Thread] = [
            threading.Thread(target=self.scheduler.run, name="scheduler", daemon=True),
            threading.Thread(target=self.worker.run, name="worker", daemon=True),
        ]
        if self.command_server is not None and self.command_server.server is not None:
            threads.append(
                threading.Thread(
                    target=self.command_server.serve_lark_forever,
                    name="command-http",
                    daemon=True,
                )
            )
        if self.command_server is not None and self.settings.telegram_command_bot_token:
            threads.append(
                threading.Thread(
                    target=self.command_server.poll_telegram_forever,
                    name="command-telegram",
                    daemon=True,
                )
            )
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def stop_all(self) -> None:
        self.scheduler.stop()
        self.worker.stop()
        if self.command_server is not None:
            self.command_server.shutdown()

    def notify_startup(self) -> None:
        channels = self.channels.list_active_by_type("lark")
        sent_targets: set[str] = set()
        for channel in channels:
            if channel.target in sent_targets:
                continue
            sent_targets.add(channel.target)
            try:
                self.lark_client.send_message(
                    channel.target,
                    "Ozon bot da khoi dong. Scheduler, worker va command server dang san sang.",
                )
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Startup notification failed for channel=%s: %s", channel.id, exc)
