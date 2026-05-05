import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT,
                    json_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS normalized_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT,
                    title TEXT,
                    category TEXT,
                    json_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def save_raw_product(self, product: dict) -> None:
        payload = dict(product or {})
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO raw_products (url, title, json_data)
                VALUES (?, ?, ?)
                """,
                (
                    str(payload.get("url", "") or ""),
                    str(payload.get("title", "") or ""),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            connection.commit()

    def save_normalized_product(self, product: dict) -> None:
        payload = dict(product or {})
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO normalized_products (source_url, title, category, json_data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(payload.get("source_url", "") or ""),
                    str(payload.get("title", "") or ""),
                    str(payload.get("category", "") or ""),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            connection.commit()

    def list_raw_products(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, url, title, json_data, created_at
                FROM raw_products
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_normalized_products(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, source_url, title, category, json_data, created_at
                FROM normalized_products
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
