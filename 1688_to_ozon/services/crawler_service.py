from __future__ import annotations

from crawlers.crawler_1688 import Crawler1688
from crawlers.crawler_shein import CrawlerShein
from models.product_model import ProductModel


def crawl_product(url: str, source: str) -> ProductModel:
    normalized_source = str(source or "").strip().lower()
    if normalized_source == "1688":
        return Crawler1688().crawl_product(url)
    if normalized_source == "shein":
        return CrawlerShein().crawl_product(url)
    raise ValueError(f"Unsupported crawler source: {source}")
