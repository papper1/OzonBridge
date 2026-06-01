from __future__ import annotations

from db.session import Database


class CommandLogRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(
        self,
        shop_id: int | None,
        source: str,
        command_text: str,
        command_type: str,
        status: str,
        response_summary: str,
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO command_log (
                    shop_id, source, command_text, command_type, status, response_summary
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (shop_id, source, command_text, command_type, status, response_summary[:2000]),
            )
            conn.commit()
