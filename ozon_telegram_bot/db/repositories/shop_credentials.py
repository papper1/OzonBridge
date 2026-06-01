from __future__ import annotations

from core.models import ShopCredential
from core.utils import to_json
from db.session import Database


class ShopCredentialsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_active(self, shop_id: int, provider: str = "ozon") -> ShopCredential | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT shop_id, provider, client_id, api_key, extra_jsonb, is_active
                FROM shop_credentials
                WHERE shop_id = %s AND provider = %s AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 1
                """,
                (shop_id, provider),
            ).fetchone()
        return ShopCredential(**row) if row else None

    def upsert_seed_credential(
        self,
        shop_id: int,
        client_id: str,
        api_key: str,
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO shop_credentials (
                    shop_id, provider, client_id, api_key, extra_jsonb, is_active
                )
                VALUES (%s, 'ozon', %s, %s, %s::jsonb, TRUE)
                ON CONFLICT DO NOTHING
                """,
                (shop_id, client_id, api_key, to_json({})),
            )
            conn.execute(
                """
                UPDATE shop_credentials
                SET client_id = %s,
                    api_key = %s,
                    is_active = TRUE,
                    updated_at = NOW()
                WHERE shop_id = %s AND provider = 'ozon'
                """,
                (client_id, api_key, shop_id),
            )
            conn.commit()
