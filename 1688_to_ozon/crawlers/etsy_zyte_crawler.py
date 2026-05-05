from __future__ import annotations

from typing import Any

from adapters.source_to_ozon_input_adapter import convert_source_product_to_existing_ozon_input
from parsers.etsy_parser import parse_etsy_product
from services.zyte_client import ZyteClient


class EtsyZyteCrawler:
    """Fetch and normalize Etsy products through Zyte."""

    def __init__(self, client: ZyteClient | None = None) -> None:
        self.client = client or ZyteClient()

    def crawl_product(self, url: str) -> dict[str, Any]:
        zyte_data = self.client.extract_product(url)
        self.client.save_debug_response("etsy", url, zyte_data)
        parsed = parse_etsy_product(zyte_data, url)
        return convert_source_product_to_existing_ozon_input(parsed, "etsy")
