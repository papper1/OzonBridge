from __future__ import annotations

import logging
from typing import Any

from core.models import Shop
from db.repositories.order_state import OrderStateRepository
from db.repositories.return_state import ReturnStateRepository
from formatters.message_formatter import MessageFormatter
from integrations.ozon_client import OzonClient
from services.notifications import NotificationService


class PollingService:
    def __init__(
        self,
        order_states: OrderStateRepository,
        return_states: ReturnStateRepository,
        notifications: NotificationService,
        formatter: MessageFormatter,
        logger: logging.Logger,
    ) -> None:
        self.order_states = order_states
        self.return_states = return_states
        self.notifications = notifications
        self.formatter = formatter
        self.logger = logger

    def sync_orders(
        self,
        shop: Shop,
        channels: list,
        ozon_client: OzonClient,
        lookback_days: int = 30,
    ) -> None:
        for order in ozon_client.collect_recent_orders(lookback_days):
            posting_number = str(order.get("posting_number") or "").strip()
            if not posting_number:
                continue
            status = str(order.get("status") or "unknown").strip() or "unknown"
            old_state = self.order_states.get(shop.id, posting_number)
            last_notified_status = old_state["last_notified_status"] if old_state else None
            should_notify = False
            if status == "awaiting_packaging" and last_notified_status != status:
                should_notify = True
                message = self.formatter.format_order(order)
                event_type = "order"
            elif status == "cancelled" and last_notified_status != status:
                should_notify = True
                reason = order.get("cancel_reason") or ozon_client.get_cancel_reason(posting_number)
                message = self.formatter.format_cancelled_order(order, reason)
                event_type = "cancelled"
            else:
                message = ""
                event_type = "order"

            if should_notify:
                self.notifications.send_once(
                    shop_id=shop.id,
                    channels=channels,
                    event_type=event_type,
                    entity_key=posting_number,
                    payload=order,
                    message=message,
                )
                last_notified_status = status

            self.order_states.upsert(
                shop.id,
                posting_number,
                raw_payload=order,
                last_status=status,
                last_notified_status=last_notified_status,
            )

    def sync_returns(
        self,
        shop: Shop,
        channels: list,
        ozon_client: OzonClient,
    ) -> None:
        items = ozon_client.get_recent_returns(limit=20)
        for item in items:
            return_number = str(item.get("return_number") or "").strip()
            if not return_number:
                continue
            status = str(item.get("status") or "unknown").strip() or "unknown"
            last_state = self.return_states.get(shop.id, return_number)
            last_notified_status = last_state["last_notified_status"] if last_state else None
            if last_notified_status != status:
                message = self.formatter.format_return(item)
                event_type = "refund"
                if str(item.get("return_type") or "").strip().lower() == "cancellation":
                    event_type = "cancellation_request"
                self.notifications.send_once(
                    shop_id=shop.id,
                    channels=channels,
                    event_type=event_type,
                    entity_key=return_number,
                    payload=item,
                    message=message,
                )
                last_notified_status = status
            self.return_states.upsert(
                shop.id,
                return_number,
                raw_payload=item,
                last_status=status,
                last_notified_status=last_notified_status,
            )
