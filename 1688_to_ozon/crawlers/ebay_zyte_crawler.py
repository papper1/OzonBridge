from __future__ import annotations

from typing import Any

from adapters.source_to_ozon_input_adapter import convert_source_product_to_existing_ozon_input
from parsers.ebay_parser import parse_ebay_product
from services.zyte_client import ZyteClient


class EbayZyteCrawler:
    """Fetch and normalize eBay products through Zyte."""

    def __init__(self, client: ZyteClient | None = None) -> None:
        self.client = client or ZyteClient()

    def crawl_product(self, url: str) -> dict[str, Any]:
        zyte_data = self.client.extract_product(url)
        self.client.save_debug_response("ebay", url, zyte_data)
        parsed = parse_ebay_product(zyte_data, url)
        return convert_source_product_to_existing_ozon_input(parsed, "ebay")
