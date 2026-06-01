from __future__ import annotations

import logging
import unittest

from integrations.ozon_client import OzonClient
from services.rate_limit import SimpleRateLimiter


class FakeOzonClient(OzonClient):
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        super().__init__(
            client_id="1",
            api_key="test",
            base_url="https://api-seller.ozon.ru",
            shop_name="Shop A",
            timeout_seconds=5,
            retry_attempts=1,
            retry_backoff_seconds=0,
            rate_limiter=SimpleRateLimiter(100),
            logger=logging.getLogger("test_ozon_client"),
        )
        self.responses = {path: list(items) for path, items in responses.items()}

    def post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        items = self.responses.get(path, [])
        if not items:
            return {"returns": [], "has_next": False}
        return items.pop(0)


class OzonClientTests(unittest.TestCase):
    def test_get_recent_returns_prioritizes_newest_rfbs_items(self) -> None:
        old_page = {
            "returns": [
                {
                    "return_id": idx,
                    "posting_number": f"POST-{idx}",
                    "created_at": f"2026-01-{idx:02d}T00:00:00Z",
                    "state": {"state_name": "Old"},
                    "product": {"name": "Old item"},
                }
                for idx in range(1, 21)
            ],
            "has_next": True,
            "last_id": 20,
        }
        new_page = {
            "returns": [
                {
                    "return_id": idx,
                    "return_number": f"RET-{idx}",
                    "posting_number": f"POST-{idx}",
                    "created_at": f"2026-05-{idx - 20:02d}T00:00:00Z",
                    "state": {"state_name": "New"},
                    "product": {"name": "New item"},
                }
                for idx in range(21, 26)
            ],
            "has_next": False,
            "last_id": 25,
        }
        client = FakeOzonClient(
            {
                "/v1/returns/list": [{"returns": [], "has_next": False}],
                "/v2/returns/rfbs/list": [old_page, new_page],
            }
        )

        items = client.get_recent_returns(limit=5)

        self.assertEqual([item["return_number"] for item in items], ["RET-25", "RET-24", "RET-23", "RET-22", "RET-21"])


if __name__ == "__main__":
    unittest.main()
