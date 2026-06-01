from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

from db.repositories.shop_channels import ShopChannelsRepository
from integrations.lark_client import LarkWebhookClient
from integrations.telegram_client import TelegramBotClient

if TYPE_CHECKING:
    from services.command_router import CommandRouter

HEALTH_PATHS = {"/health", "/lark/health"}
COMMAND_PATH = "/lark/command"
SUPPORTED_COMMANDS = ("/order", "/refund", "/help", "/status", "/cancel", "/order_now")


class CommandServer:
    def __init__(
        self,
        host: str | None,
        port: int | None,
        telegram_bot_token: str | None,
        allowed_chat_ids: tuple[str, ...],
        router: CommandRouter,
        shop_channels: ShopChannelsRepository,
        lark_client: LarkWebhookClient,
        telegram_client: TelegramBotClient,
        logger: logging.Logger,
    ) -> None:
        self.host = host
        self.port = port
        self.telegram_bot_token = telegram_bot_token
        self.allowed_chat_ids = set(allowed_chat_ids)
        self.router = router
        self.shop_channels = shop_channels
        self.lark_client = lark_client
        self.telegram_client = telegram_client
        self.logger = logger
        self.server = (
            ThreadingHTTPServer((host, port), self._build_handler())
            if host and port
            else None
        )
        self.stop_event = threading.Event()
        self.telegram_offset: int | None = None

    def serve_lark_forever(self) -> None:
        if self.server is None:
            return
        self.logger.info("Lark command server listening on %s:%s", self.host, self.port)
        self.server.serve_forever()

    def poll_telegram_forever(self) -> None:
        if not self.telegram_bot_token:
            return
        self.logger.info("Telegram command polling started")
        while not self.stop_event.is_set():
            updates = self.telegram_client.get_updates(
                self.telegram_bot_token,
                offset=self.telegram_offset,
                timeout=20,
            )
            for update in updates:
                self.telegram_offset = int(update.get("update_id", 0)) + 1
                self._handle_telegram_update(update)

    def shutdown(self) -> None:
        self.stop_event.set()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

    def _handle_telegram_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = str(message.get("text") or "").strip()
        if not text:
            return
        if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
            self.logger.warning("Ignored telegram command from chat_id=%s", chat_id)
            return
        result = self.router.handle("telegram", text)
        for response in result.messages:
            self.telegram_client.send_message(self.telegram_bot_token or "", chat_id, response)

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path not in HEALTH_PATHS:
                    self._write_json(404, {"error": "not found"})
                    return
                self._write_json(200, {"status": "ok", "service": "lark-command-server"})

            def do_POST(self) -> None:  # noqa: N802
                if self.path != COMMAND_PATH:
                    self._write_json(404, {"error": "not found"})
                    return
                raw_length = self.headers.get("Content-Length", "0")
                try:
                    content_length = int(raw_length)
                except ValueError:
                    content_length = 0
                body = self.rfile.read(content_length)
                body_text = body.decode("utf-8", errors="replace")
                parent.logger.info("Lark callback path=%s body=%s", self.path, body_text[:4000])
                try:
                    payload = json.loads(body_text or "{}")
                except json.JSONDecodeError:
                    parent.logger.warning("Lark callback invalid json")
                    self._write_json(400, {"error": "invalid json"})
                    return
                if "challenge" in payload:
                    parent.logger.info("Lark callback challenge received")
                    self._write_json(200, {"challenge": payload["challenge"]})
                    return
                text = parent._extract_text(payload)
                parent.logger.info("Lark callback extracted_text=%r", text)
                command = parent._extract_command(text)
                if not command:
                    parent.logger.info("Lark callback no supported command found")
                    self._write_json(200, {"ok": True})
                    return
                parent.logger.info("Lark callback command=%s", command)
                result = parent.router.handle("lark", command)
                parent._reply_to_lark(result.shop_id, result.messages)
                self._write_json(200, {"ok": True, "messages": result.messages})

            def log_message(self, format: str, *args: object) -> None:
                parent.logger.debug("command server: " + format, *args)

            def _write_json(self, status: int, payload: dict[str, object]) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler

    @staticmethod
    def _extract_text(payload: dict[str, object]) -> str:
        event = payload.get("event")
        if not isinstance(event, dict):
            return ""
        message = event.get("message")
        if isinstance(message, dict):
            content_raw = message.get("content")
            if isinstance(content_raw, str):
                try:
                    content = json.loads(content_raw)
                except json.JSONDecodeError:
                    content = {}
                text = content.get("text")
                if isinstance(text, str):
                    return text.strip()
        direct_text = event.get("text")
        return direct_text.strip() if isinstance(direct_text, str) else ""

    @staticmethod
    def _extract_command(text: str) -> str | None:
        lowered = text.lower()
        for command in SUPPORTED_COMMANDS:
            if command in lowered:
                return lowered[lowered.index(command):].strip()
        return None

    def _reply_to_lark(self, shop_id: int | None, messages: list[str]) -> None:
        channels = self.shop_channels.list_active_by_type("lark", shop_id=shop_id)
        if not channels:
            channels = self.shop_channels.list_active_by_type("lark")
        if not channels:
            self.logger.warning("No active Lark channel found to reply to command")
            return
        channel = channels[0]
        for message in messages:
            self.lark_client.send_message(channel.target, message)
