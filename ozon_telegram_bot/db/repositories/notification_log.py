from __future__ import annotations

from typing import Any

from core.utils import to_json
from db.session import Database


class NotificationLogRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def has(self, idempotency_key: str) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM notification_log WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
        return row is not None

    def save(
        self,
        shop_id: int,
        channel_type: str,
        event_type: str,
        entity_key: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO notification_log (
                    shop_id, channel_type, event_type, entity_key, idempotency_key, payload
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING
                """,
                (shop_id, channel_type, event_type, entity_key, idempotency_key, to_json(payload)),
            )
            conn.commit()

    def count_for_shop(self, shop_id: int) -> int:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM notification_log WHERE shop_id = %s",
                (shop_id,),
            ).fetchone()
        return int(row["total"]) if row else 0
