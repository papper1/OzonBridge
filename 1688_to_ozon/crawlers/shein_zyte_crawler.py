from __future__ import annotations

from typing import Any
from uuid import uuid4

from adapters.source_to_ozon_input_adapter import convert_source_product_to_existing_ozon_input
from parsers.shein_parser import parse_shein_product
from services.zyte_client import ZyteClient


class SheinZyteCrawler:
    """Fetch and normalize SHEIN products through Zyte."""

    def __init__(self, client: ZyteClient | None = None) -> None:
        self.client = client or ZyteClient()

    def crawl_product(self, url: str) -> dict[str, Any]:
        session_id = str(uuid4())
        warmup = self.client.extract(
            {
                "url": url,
                "browserHtml": True,
                "responseCookies": True,
                "session": {"id": session_id},
                "requestHeaders": {"referer": self._build_referer(url)},
            }
        )
        cookies = warmup.get("responseCookies") if isinstance(warmup, dict) else []
        payload: dict[str, Any] = {
            "url": url,
            "browserHtml": True,
            "product": True,
            "responseCookies": True,
            "session": {"id": session_id},
            "requestHeaders": {"referer": self._build_referer(url)},
        }
        if cookies:
            payload["requestCookies"] = cookies
        zyte_data = self.client.extract(payload)
        self.client.save_debug_response("shein", url, zyte_data)
        parsed = parse_shein_product(zyte_data, url)
        return convert_source_product_to_existing_ozon_input(parsed, "shein")

    def _build_referer(self, url: str) -> str:
        parts = url.split("/", 3)
        if len(parts) >= 3:
            return f"{parts[0]}//{parts[2]}/"
        return "https://www.shein.com.vn/"
