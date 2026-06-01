from __future__ import annotations

from typing import Any

from core.utils import from_json, to_json
from db.session import Database


class OrderStateRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, shop_id: int, posting_number: str) -> dict[str, Any] | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT id, shop_id, posting_number, raw_payload::text AS raw_payload, last_status,
                       last_notified_status, updated_at
                FROM order_state
                WHERE shop_id = %s AND posting_number = %s
                """,
                (shop_id, posting_number),
            ).fetchone()
        if not row:
            return None
        row["raw_payload"] = from_json(row["raw_payload"], {})
        return row

    def upsert(
        self,
        shop_id: int,
        posting_number: str,
        raw_payload: dict[str, Any],
        last_status: str,
        last_notified_status: str | None,
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO order_state (
                    shop_id, posting_number, raw_payload, last_status, last_notified_status, updated_at
                )
                VALUES (%s, %s, %s::jsonb, %s, %s, NOW())
                ON CONFLICT (shop_id, posting_number) DO UPDATE SET
                    raw_payload = EXCLUDED.raw_payload,
                    last_status = EXCLUDED.last_status,
                    last_notified_status = EXCLUDED.last_notified_status,
                    updated_at = NOW()
                """,
                (shop_id, posting_number, to_json(raw_payload), last_status, last_notified_status),
            )
            conn.commit()

    def list_recent(self, shop_id: int, limit: int = 10) -> list[dict[str, Any]]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT posting_number, raw_payload::text AS raw_payload, last_status, updated_at
                FROM order_state
                WHERE shop_id = %s
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (shop_id, limit),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            row["raw_payload"] = from_json(row["raw_payload"], {})
            result.append(row)
        return result

    def list_by_status(self, shop_id: int, status: str, limit: int = 10) -> list[dict[str, Any]]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT posting_number, raw_payload::text AS raw_payload, last_status, updated_at
                FROM order_state
                WHERE shop_id = %s AND last_status = %s
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (shop_id, status, limit),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            row["raw_payload"] = from_json(row["raw_payload"], {})
            result.append(row)
        return result
