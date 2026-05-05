from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from config import RAW_DATA_DIR, RESOURCE_ROOT

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - depends on local environment
    load_dotenv = None


ENV_FILE = RESOURCE_ROOT / ".env"
ZYTE_API_URL = "https://api.zyte.com/v1/extract"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_BAN_RETRIES = 3
DEFAULT_BAN_RETRY_DELAY_SECONDS = 2.0

if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_FILE)


class MissingZyteAPIKeyError(RuntimeError):
    """Raised when ZYTE_API_KEY is not configured."""


class ZyteClient:
    """Thin wrapper around Zyte extract API with safe debug output support."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        ban_retries: int = DEFAULT_BAN_RETRIES,
        ban_retry_delay_seconds: float = DEFAULT_BAN_RETRY_DELAY_SECONDS,
    ) -> None:
        self._reload_env()
        self.api_key = (api_key or os.getenv("ZYTE_API_KEY", "")).strip()
        self.timeout = timeout
        self.ban_retries = max(int(ban_retries), 0)
        self.ban_retry_delay_seconds = max(float(ban_retry_delay_seconds), 0.0)

    def _reload_env(self) -> None:
        if load_dotenv is not None:
            load_dotenv(dotenv_path=ENV_FILE, override=True)

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise MissingZyteAPIKeyError(
                "Missing Zyte API key. Please set ZYTE_API_KEY in the .env file."
            )
        return self.api_key

    def extract(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error_message = ""
        total_attempts = self.ban_retries + 1

        for attempt in range(1, total_attempts + 1):
            response = requests.post(
                ZYTE_API_URL,
                auth=(self._require_api_key(), ""),
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code < 400:
                return response.json()

            response_text = response.text[:1000]
            is_retryable_ban = self._is_retryable_ban_response(response)
            last_error_message = f"Zyte API error {response.status_code}: {response_text}"

            if is_retryable_ban and attempt < total_attempts:
                delay_seconds = self.ban_retry_delay_seconds * attempt
                time.sleep(delay_seconds)
                continue

            if is_retryable_ban:
                raise RuntimeError(
                    f"{last_error_message}. Retried {total_attempts} times because Zyte reported a temporary ban response."
                )

            raise RuntimeError(last_error_message)

        raise RuntimeError(last_error_message or "Zyte API request failed without a response.")

    def _is_retryable_ban_response(self, response: requests.Response) -> bool:
        if response.status_code != 520:
            return False

        try:
            payload = response.json()
        except ValueError:
            return False

        error_type = str(payload.get("type") or "").strip().lower()
        return error_type == "/download/temporary-error"

    def extract_product(self, url: str, browser_html: bool = True) -> dict[str, Any]:
        payload = {
            "url": url,
            "browserHtml": bool(browser_html),
            "product": True,
        }
        return self.extract(payload)

    def save_debug_response(self, source: str, url: str, data: dict[str, Any], suffix: str = "") -> Path:
        debug_dir = RAW_DATA_DIR / "zyte"
        debug_dir.mkdir(parents=True, exist_ok=True)
        stem = self._build_debug_stem(source=source, url=url, suffix=suffix)
        output_path = debug_dir / f"{stem}.json"
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def _build_debug_stem(self, source: str, url: str, suffix: str = "") -> str:
        safe_source = "".join(char if char.isalnum() else "_" for char in str(source or "").lower()).strip("_") or "source"
        safe_url = "".join(char if char.isalnum() else "_" for char in str(url or "").lower()).strip("_")
        short_url = "_".join(part for part in safe_url.split("_") if part)[:60].strip("_") or "product"
        safe_suffix = "".join(char if char.isalnum() else "_" for char in suffix).strip("_")
        if safe_suffix:
            return f"raw_{safe_source}_{short_url}_{safe_suffix}"
        return f"raw_{safe_source}_{short_url}"
