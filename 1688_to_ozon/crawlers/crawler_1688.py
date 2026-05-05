from __future__ import annotations

import logging

from crawler.product import crawl_1688_product
from crawler.session import create_context_with_session
from config import DEFAULT_TIMEOUT, HEADLESS, SESSION_FILE
from models.product_model import ProductModel, ProductVariant
from playwright.sync_api import sync_playwright
from utils import logger as logger_module

from .base_crawler import BaseCrawler


def get_logger() -> logging.Logger:
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("crawlers.crawler_1688")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("crawlers.crawler_1688")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = get_logger()


def _build_variants_from_1688_payload(payload: dict) -> list[ProductVariant]:
    variants: list[ProductVariant] = []
    sku_payload = payload.get("sku") if isinstance(payload.get("sku"), dict) else {}
    option_labels = sku_payload.get("option_labels") if isinstance(sku_payload.get("option_labels"), list) else []
    for option_label in option_labels:
        text = str(option_label or "").strip()
        if not text:
            continue
        variants.append(ProductVariant(size="", color=text))
    return variants


class Crawler1688(BaseCrawler):
    """Thin wrapper around the legacy 1688 Playwright crawler."""

    def crawl_product(self, url: str) -> ProductModel:
        LOGGER.info("1688 crawler: opening product URL %s", url)
        playwright = browser = context = page = None
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=HEADLESS)
            context = create_context_with_session(browser, str(SESSION_FILE))
            page = context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT)
            payload = crawl_1688_product(page, url)
            LOGGER.info("1688 crawler: extracted title and media for %s", url)
            return ProductModel(
                source="1688",
                product_url=str(payload.get("url") or url),
                title=str(payload.get("title") or ""),
                price=str(payload.get("price") or ""),
                images=list(payload.get("images", []) or []),
                description="",
                variants=_build_variants_from_1688_payload(payload),
            )
        except Exception:
            LOGGER.exception("1688 crawl failed for URL: %s", url)
            raise
        finally:
            if page is not None:
                page.close()
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()
            if playwright is not None:
                playwright.stop()
