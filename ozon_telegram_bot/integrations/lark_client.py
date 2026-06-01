from __future__ import annotations

import logging
import time

import requests


class LarkApiError(RuntimeError):
    pass


class LarkWebhookClient:
    def __init__(self, timeout_seconds: int, logger: logging.Logger) -> None:
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self.session = requests.Session()

    def send_message(self, webhook_url: str, text: str) -> None:
        payload = {"msg_type": "text", "content": {"text": text}}
        self._post(webhook_url, payload)

    def _post(self, webhook_url: str, payload: dict) -> None:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self.session.post(
                    webhook_url,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                if response.status_code >= 400:
                    raise LarkApiError(
                        f"Lark webhook HTTP {response.status_code}: {response.text[:300]}"
                    )
                data = response.json()
                if data.get("code") not in (None, 0):
                    raise LarkApiError(f"Lark webhook API error: {data}")
                return
            except (requests.RequestException, ValueError, LarkApiError) as exc:
                last_error = exc
                self.logger.warning("Lark send failed on attempt %s: %s", attempt, exc)
                if attempt < 3:
                    time.sleep(attempt)
        raise LarkApiError(f"Lark webhook request failed: {last_error}")

