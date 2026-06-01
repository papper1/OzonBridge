from __future__ import annotations

from core.models import ShopChannel
from db.session import Database


class ShopChannelsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_active(self, shop_id: int) -> list[ShopChannel]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, shop_id, channel_type, channel_name, target, secret, is_active
                FROM shop_channels
                WHERE shop_id = %s AND is_active = TRUE
                ORDER BY id
                """,
                (shop_id,),
            ).fetchall()
        return [ShopChannel(**row) for row in rows]

    def list_active_by_type(
        self,
        channel_type: str,
        shop_id: int | None = None,
    ) -> list[ShopChannel]:
        with self.database.connection() as conn:
            if shop_id is None:
                rows = conn.execute(
                    """
                    SELECT id, shop_id, channel_type, channel_name, target, secret, is_active
                    FROM shop_channels
                    WHERE channel_type = %s AND is_active = TRUE
                    ORDER BY shop_id, id
                    """,
                    (channel_type,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, shop_id, channel_type, channel_name, target, secret, is_active
                    FROM shop_channels
                    WHERE shop_id = %s AND channel_type = %s AND is_active = TRUE
                    ORDER BY id
                    """,
                    (shop_id, channel_type),
                ).fetchall()
        return [ShopChannel(**row) for row in rows]

    def upsert_channel(
        self,
        shop_id: int,
        channel_type: str,
        channel_name: str,
        target: str,
        secret: str | None,
    ) -> None:
        with self.database.connection() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM shop_channels
                WHERE shop_id = %s AND channel_type = %s AND target = %s
                LIMIT 1
                """,
                (shop_id, channel_type, target),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE shop_channels
                    SET channel_name = %s,
                        secret = %s,
                        is_active = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (channel_name, secret, existing["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO shop_channels (
                        shop_id, channel_type, channel_name, target, secret, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    """,
                    (shop_id, channel_type, channel_name, target, secret),
                )
            conn.commit()
