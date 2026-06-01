from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Shop:
    id: int
    code: str
    name: str
    timezone: str
    poll_interval_seconds: int
    next_poll_at: datetime | None
    is_active: bool


@dataclass(slots=True)
class ShopCredential:
    shop_id: int
    provider: str
    client_id: str
    api_key: str
    extra_jsonb: dict[str, Any]
    is_active: bool


@dataclass(slots=True)
class ShopChannel:
    id: int
    shop_id: int
    channel_type: str
    channel_name: str
    target: str
    secret: str | None
    is_active: bool


@dataclass(slots=True)
class PollJob:
    id: int
    shop_id: int
    job_type: str
    status: str
    retry_count: int
    max_retry: int
    next_run_at: datetime
    locked_at: datetime | None
    locked_by: str | None
    last_error: str | None

