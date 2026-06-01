from __future__ import annotations

import logging
from typing import Any

from core.models import ShopChannel
from db.repositories.notification_log import NotificationLogRepository
from integrations.lark_client import LarkWebhookClient
from integrations.telegram_client import TelegramBotClient


class NotificationService:
    def __init__(
        self,
        notification_logs: NotificationLogRepository,
        lark_client: LarkWebhookClient,
        telegram_client: TelegramBotClient,
        logger: logging.Logger,
    ) -> None:
        self.notification_logs = notification_logs
        self.lark_client = lark_client
        self.telegram_client = telegram_client
        self.logger = logger

    def send_once(
        self,
        shop_id: int,
        channels: list[ShopChannel],
        event_type: str,
        entity_key: str,
        payload: dict[str, Any],
        message: str,
    ) -> None:
        for channel in channels:
            idempotency_key = (
                f"{shop_id}:{event_type}:{entity_key}:{payload.get('status') or ''}:"
                f"{channel.channel_type}:{channel.target}"
            )
            if self.notification_logs.has(idempotency_key):
                continue
            self._send(channel, message)
            self.notification_logs.save(
                shop_id=shop_id,
                channel_type=channel.channel_type,
                event_type=event_type,
                entity_key=entity_key,
                idempotency_key=idempotency_key,
                payload=payload,
            )

    def _send(self, channel: ShopChannel, message: str) -> None:
        if channel.channel_type == "lark":
            self.lark_client.send_message(channel.target, message)
            return
        if channel.channel_type == "telegram":
            if not channel.secret:
                raise ValueError("Telegram channel is missing bot token in secret")
            self.telegram_client.send_message(channel.secret, channel.target, message)
            return
        self.logger.warning("Unsupported channel type %s", channel.channel_type)
