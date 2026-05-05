from __future__ import annotations

from abc import ABC, abstractmethod

from models.product_model import ProductModel


class BaseCrawler(ABC):
    """Common crawler interface for product-detail sources."""

    @abstractmethod
    def crawl_product(self, url: str) -> ProductModel:
        """Crawl one product URL and return the normalized source product model."""
        raise NotImplementedError
