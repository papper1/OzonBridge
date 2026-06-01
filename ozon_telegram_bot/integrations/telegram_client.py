from __future__ import annotations

import logging
import time
from typing import Any

import requests


class TelegramApiError(RuntimeError):
    pass


class TelegramBotClient:
    def __init__(self, timeout_seconds: int, logger: logging.Logger) -> None:
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self.session = requests.Session()

    def send_message(self, bot_token: str, chat_id: str, text: str) -> None:
        self._call(
            bot_token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )

    def get_updates(self, bot_token: str, offset: int | None = None, timeout: int = 20) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        data = self._call(bot_token, "getUpdates", payload)
        result = data.get("result")
        return result if isinstance(result, list) else []

    def _call(self, bot_token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{bot_token}/{method}"
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self.session.post(url, json=payload, timeout=self.timeout_seconds + 5)
                if response.status_code >= 400:
                    raise TelegramApiError(
                        f"Telegram HTTP {response.status_code}: {response.text[:300]}"
                    )
                data = response.json()
                if not data.get("ok"):
                    raise TelegramApiError(f"Telegram API error: {data}")
                return data
            except (requests.RequestException, ValueError, TelegramApiError) as exc:
                last_error = exc
                self.logger.warning("Telegram %s failed on attempt %s: %s", method, attempt, exc)
                if attempt < 3:
                    time.sleep(attempt)
        raise TelegramApiError(f"Telegram request failed: {last_error}")

