from __future__ import annotations

from typing import Any

from crawlers.ebay_zyte_crawler import EbayZyteCrawler
from crawlers.etsy_zyte_crawler import EtsyZyteCrawler
from crawlers.shein_zyte_crawler import SheinZyteCrawler


def crawl_source_product(url: str, source: str) -> dict[str, Any]:
    normalized_source = str(source or "").strip().lower()
    if normalized_source == "shein":
        return SheinZyteCrawler().crawl_product(url)
    if normalized_source == "etsy":
        return EtsyZyteCrawler().crawl_product(url)
    if normalized_source == "ebay":
        return EbayZyteCrawler().crawl_product(url)
    raise ValueError(f"Unsupported Zyte source: {source}")
