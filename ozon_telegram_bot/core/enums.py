from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    pass


class JobType(StrEnum):
    SYNC_ORDERS = "sync_orders"
    SYNC_RETURNS = "sync_returns"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ChannelType(StrEnum):
    LARK = "lark"
    TELEGRAM = "telegram"
