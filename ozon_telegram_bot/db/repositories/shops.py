from __future__ import annotations

from datetime import timedelta

from core.models import Shop
from core.utils import utcnow
from db.session import Database


class ShopsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_active(self) -> list[Shop]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, code, name, timezone, poll_interval_seconds, next_poll_at, is_active
                FROM shops
                WHERE is_active = TRUE
                ORDER BY id
                """
            ).fetchall()
        return [Shop(**row) for row in rows]

    def list_due(self) -> list[Shop]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, code, name, timezone, poll_interval_seconds, next_poll_at, is_active
                FROM shops
                WHERE is_active = TRUE
                  AND (next_poll_at IS NULL OR next_poll_at <= NOW())
                ORDER BY COALESCE(next_poll_at, NOW()), id
                """
            ).fetchall()
        return [Shop(**row) for row in rows]

    def get_by_code(self, shop_code: str) -> Shop | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT id, code, name, timezone, poll_interval_seconds, next_poll_at, is_active
                FROM shops
                WHERE code = %s
                """,
                (shop_code,),
            ).fetchone()
        return Shop(**row) if row else None

    def get_by_id(self, shop_id: int) -> Shop | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT id, code, name, timezone, poll_interval_seconds, next_poll_at, is_active
                FROM shops
                WHERE id = %s
                """,
                (shop_id,),
            ).fetchone()
        return Shop(**row) if row else None

    def upsert_seed_shop(
        self,
        code: str,
        name: str,
        timezone: str,
        poll_interval_seconds: int,
    ) -> int:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO shops (code, name, timezone, poll_interval_seconds, next_poll_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    timezone = EXCLUDED.timezone,
                    poll_interval_seconds = EXCLUDED.poll_interval_seconds,
                    is_active = TRUE,
                    updated_at = NOW()
                RETURNING id
                """,
                (code, name, timezone, poll_interval_seconds),
            ).fetchone()
            conn.commit()
        return int(row["id"])

    def schedule_next_poll(self, shop_id: int, interval_seconds: int) -> None:
        next_poll_at = utcnow() + timedelta(seconds=interval_seconds)
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE shops
                SET next_poll_at = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (next_poll_at, shop_id),
            )
            conn.commit()
