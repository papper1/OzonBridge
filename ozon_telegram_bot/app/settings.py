from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass(slots=True)
class Settings:
    database_url: str
    log_file_path: str
    request_timeout_seconds: int
    scheduler_sleep_seconds: int
    worker_sleep_seconds: int
    default_poll_interval_seconds: int
    default_max_retry: int
    ozon_base_url: str
    ozon_rate_limit_per_second: float
    ozon_retry_attempts: int
    ozon_retry_backoff_seconds: float
    lark_command_host: str | None
    lark_command_port: int | None
    telegram_command_bot_token: str | None
    telegram_allowed_chat_ids: tuple[str, ...]
    seed_shop_code: str | None
    seed_shop_name: str | None
    seed_shop_timezone: str
    seed_ozon_client_id: str | None
    seed_ozon_api_key: str | None
    seed_lark_webhook_url: str | None
    seed_telegram_chat_id: str | None
    seed_telegram_bot_token: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise ConfigError("Missing required environment variable: DATABASE_URL")

        log_file_path = os.getenv("LOG_FILE_PATH", "logs/bot.log").strip() or "logs/bot.log"
        request_timeout_seconds = _positive_int("REQUEST_TIMEOUT_SECONDS", "20")
        scheduler_sleep_seconds = _positive_int("SCHEDULER_SLEEP_SECONDS", "5")
        worker_sleep_seconds = _positive_int("WORKER_SLEEP_SECONDS", "3")
        default_poll_interval_seconds = _positive_int("DEFAULT_POLL_INTERVAL_SECONDS", "180")
        default_max_retry = _positive_int("DEFAULT_MAX_RETRY", "3")
        ozon_retry_attempts = _positive_int("OZON_RETRY_ATTEMPTS", "3")
        ozon_rate_limit_per_second = _positive_float("OZON_RATE_LIMIT_PER_SECOND", "2")
        ozon_retry_backoff_seconds = _positive_float("OZON_RETRY_BACKOFF_SECONDS", "1")
        ozon_base_url = (
            os.getenv("OZON_BASE_URL", "https://api-seller.ozon.ru").strip()
            or "https://api-seller.ozon.ru"
        )
        lark_command_host = os.getenv("LARK_COMMAND_HOST", "").strip() or None
        lark_command_port = _optional_positive_int(os.getenv("LARK_COMMAND_PORT", "").strip())
        telegram_command_bot_token = (
            os.getenv("TELEGRAM_COMMAND_BOT_TOKEN", "").strip() or None
        )
        telegram_allowed_chat_ids = _parse_list(
            os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
        )
        seed_shop_timezone = os.getenv("SEED_SHOP_TIMEZONE", "Asia/Saigon").strip() or "Asia/Saigon"
        _validate_timezone(seed_shop_timezone)

        return cls(
            database_url=database_url,
            log_file_path=log_file_path,
            request_timeout_seconds=request_timeout_seconds,
            scheduler_sleep_seconds=scheduler_sleep_seconds,
            worker_sleep_seconds=worker_sleep_seconds,
            default_poll_interval_seconds=default_poll_interval_seconds,
            default_max_retry=default_max_retry,
            ozon_base_url=ozon_base_url,
            ozon_rate_limit_per_second=ozon_rate_limit_per_second,
            ozon_retry_attempts=ozon_retry_attempts,
            ozon_retry_backoff_seconds=ozon_retry_backoff_seconds,
            lark_command_host=lark_command_host,
            lark_command_port=lark_command_port,
            telegram_command_bot_token=telegram_command_bot_token,
            telegram_allowed_chat_ids=telegram_allowed_chat_ids,
            seed_shop_code=os.getenv("SEED_SHOP_CODE", "").strip() or None,
            seed_shop_name=os.getenv("SEED_SHOP_NAME", "").strip() or None,
            seed_shop_timezone=seed_shop_timezone,
            seed_ozon_client_id=os.getenv("SEED_OZON_CLIENT_ID", "").strip() or None,
            seed_ozon_api_key=os.getenv("SEED_OZON_API_KEY", "").strip() or None,
            seed_lark_webhook_url=os.getenv("SEED_LARK_WEBHOOK_URL", "").strip() or None,
            seed_telegram_chat_id=os.getenv("SEED_TELEGRAM_CHAT_ID", "").strip() or None,
            seed_telegram_bot_token=os.getenv("SEED_TELEGRAM_BOT_TOKEN", "").strip() or None,
        )


def _positive_int(name: str, default: str) -> int:
    raw_value = os.getenv(name, default).strip() or default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be greater than 0")
    return value


def _optional_positive_int(raw_value: str) -> int | None:
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError("LARK_COMMAND_PORT must be an integer") from exc
    if value <= 0:
        raise ConfigError("LARK_COMMAND_PORT must be greater than 0")
    return value


def _positive_float(name: str, default: str) -> float:
    raw_value = os.getenv(name, default).strip() or default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be greater than 0")
    return value


def _parse_list(raw_value: str) -> tuple[str, ...]:
    if not raw_value:
        return ()
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


def _validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(
            f"TIMEZONE {value!r} is not available. Install tzdata or use a valid IANA timezone."
        ) from exc
