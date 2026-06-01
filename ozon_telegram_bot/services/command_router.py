from __future__ import annotations

import logging
from dataclasses import dataclass

from app.settings import Settings
from db.repositories.command_log import CommandLogRepository
from db.repositories.notification_log import NotificationLogRepository
from db.repositories.order_state import OrderStateRepository
from db.repositories.return_state import ReturnStateRepository
from db.repositories.shop_credentials import ShopCredentialsRepository
from db.repositories.shops import ShopsRepository
from formatters.message_formatter import MessageFormatter
from integrations.ozon_client import OzonClient
from services.rate_limit import SimpleRateLimiter


@dataclass(slots=True)
class CommandResult:
    messages: list[str]
    shop_id: int | None
    command_name: str
    status: str


class CommandRouter:
    def __init__(
        self,
        settings: Settings,
        shops: ShopsRepository,
        credentials: ShopCredentialsRepository,
        order_states: OrderStateRepository,
        return_states: ReturnStateRepository,
        notification_logs: NotificationLogRepository,
        command_logs: CommandLogRepository,
        formatter: MessageFormatter,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.shops = shops
        self.credentials = credentials
        self.order_states = order_states
        self.return_states = return_states
        self.notification_logs = notification_logs
        self.command_logs = command_logs
        self.formatter = formatter
        self.logger = logger

    def handle(self, source: str, command_text: str) -> CommandResult:
        command_name, shop_code = self._parse_command(command_text)
        if command_name == "/help":
            response = [self.formatter.format_help()]
            self.command_logs.save(None, source, command_text, command_name, "ok", response[0])
            return CommandResult(response, None, command_name, "ok")

        shop = self._resolve_shop(shop_code)
        if shop is None:
            response = ["Khong xac dinh duoc shop. Dung /status <shop_code> neu co nhieu shop."]
            self.command_logs.save(None, source, command_text, command_name, "error", response[0])
            return CommandResult(response, None, command_name, "error")

        try:
            if command_name == "/status":
                response = [self.formatter.format_status(shop.name, self._stats(shop.id))]
            elif command_name == "/order":
                orders = [row["raw_payload"] for row in self.order_states.list_by_status(shop.id, "awaiting_packaging", 10)]
                response = self.formatter.format_lines("Don hang", orders, self.formatter.format_order)
            elif command_name == "/refund":
                items = [row["raw_payload"] for row in self.return_states.list_recent(shop.id, 20)]
                refunds = [
                    item for item in items
                    if str(item.get("return_type") or "").strip().lower() != "cancellation"
                ][:10]
                response = self.formatter.format_lines("Refund", refunds, self.formatter.format_return)
            elif command_name == "/cancel":
                items = [row["raw_payload"] for row in self.return_states.list_recent(shop.id, 20)]
                cancels = [
                    item for item in items
                    if str(item.get("return_type") or "").strip().lower() == "cancellation"
                ][:10]
                response = self.formatter.format_lines("Cancellation", cancels, self.formatter.format_return)
            elif command_name == "/order_now":
                response = self._handle_order_now(shop.id)
            else:
                response = ["Lenh khong hop le. Dung /help."]
            response = self._ensure_messages(response, command_name)
            self.command_logs.save(shop.id, source, command_text, command_name, "ok", response[0])
            return CommandResult(response, shop.id, command_name, "ok")
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Command failed: %s", exc)
            response = [self.formatter.format_error("Loi xu ly lenh", str(exc))]
            self.command_logs.save(shop.id, source, command_text, command_name, "error", response[0])
            return CommandResult(response, shop.id, command_name, "error")

    def _handle_order_now(self, shop_id: int) -> list[str]:
        shop = self.shops.get_by_id(shop_id)
        if shop is None:
            return ["Shop khong ton tai."]
        credential = self.credentials.get_active(shop.id)
        if credential is None:
            return ["Shop chua co credential Ozon."]
        client = OzonClient(
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
        orders = client.get_awaiting_packaging_orders(lookback_days=30, limit=10)
        return self.formatter.format_lines("Don hang", orders, self.formatter.format_order)

    def _resolve_shop(self, shop_code: str | None):
        if shop_code:
            return self.shops.get_by_code(shop_code)
        shops = self.shops.list_active()
        return shops[0] if len(shops) == 1 else None

    def _parse_command(self, command_text: str) -> tuple[str, str | None]:
        parts = (command_text or "").strip().split()
        if not parts:
            return "/help", None
        command_name = parts[0].lower()
        shop_code = self._normalize_shop_code(parts[1]) if len(parts) >= 2 else None
        return command_name, shop_code

    def _stats(self, shop_id: int) -> dict[str, int]:
        orders = self.order_states.list_recent(shop_id, 100)
        returns = self.return_states.list_recent(shop_id, 100)
        return {
            "awaiting_packaging": sum(1 for row in orders if row["last_status"] == "awaiting_packaging"),
            "cancelled": sum(1 for row in orders if row["last_status"] == "cancelled"),
            "returns": len(returns),
            "notifications": self.notification_logs.count_for_shop(shop_id),
        }

    @staticmethod
    def _ensure_messages(messages: list[str], command_name: str) -> list[str]:
        cleaned = [message for message in messages if isinstance(message, str) and message.strip()]
        if cleaned:
            return cleaned
        return [f"{command_name}\n\nKhong co du lieu."]

    @staticmethod
    def _normalize_shop_code(raw_value: str) -> str | None:
        value = (raw_value or "").strip()
        if not value:
            return None
        value = value.strip("[]<>(){}\"'`")
        value = value.rstrip(".,;:")
        return value or None
