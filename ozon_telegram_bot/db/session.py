from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg import connect
from psycopg.rows import dict_row


class Database:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @contextmanager
    def connection(self) -> Iterator:
        with connect(self.dsn, row_factory=dict_row) as conn:
            yield conn

