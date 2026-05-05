from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any
from urllib.parse import quote_plus, urlsplit, urlunsplit

from playwright.async_api import BrowserContext, Page, Playwright, TimeoutError as PlaywrightTimeoutError

from config import DEFAULT_TIMEOUT, BROWSER_VIEWPORT_CHOICES
from models.product_model import ProductModel, ProductVariant
from utils import logger as logger_module

from .base_crawler import BaseCrawler
from .shein_session import (
    is_shein_verification_page,
    launch_shein_persistent_context_async,
    wait_for_manual_verification_async,
)


SHEIN_HOME_URL = "https://www.shein.com.vn"
SHEIN_ACCOUNT_URL = "https://www.shein.com.vn/user/auth/login?redirection=%2Fuser%2Forders%2Flist%3Ffrom%3DnavTop"
SHEIN_READY_SELECTORS = (
    "h1",
    "[data-testid='product-intro-title']",
    ".product-intro__head-name",
)


def get_logger() -> logging.Logger:
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("crawlers.crawler_shein")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("crawlers.crawler_shein")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = get_logger()


def _normalize_text(text: Any) -> str:
    value = re.sub(r"\s+", " ", str(text or "").replace("\xa0", " "))
    return value.strip(" :-|")


def _normalize_image_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme or "https", parts.netloc, parts.path, "", ""))


def _normalize_product_url(url: str) -> str:
    parts = urlsplit(str(url or "").strip())
    return urlunsplit((parts.scheme or "https", parts.netloc, parts.path, parts.query, ""))


def _choose_viewport() -> dict[str, int]:
    viewport = random.choice(BROWSER_VIEWPORT_CHOICES or ({"width": 1366, "height": 768},))
    return {"width": int(viewport["width"]), "height": int(viewport["height"])}


async def _random_delay(min_seconds: float = 2.0, max_seconds: float = 6.0) -> None:
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))


async def open_homepage(page: Page) -> None:
    LOGGER.info("SHEIN: open homepage")
    await page.goto(SHEIN_HOME_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    if await is_shein_verification_page(page):
        await wait_for_manual_verification_async(page, "opening SHEIN homepage")
    await _random_delay(3.0, 5.0)


async def simulate_user_behavior(page: Page) -> None:
    LOGGER.info("SHEIN: simulate user scroll")
    for _ in range(random.randint(2, 4)):
        await page.mouse.move(random.randint(80, 900), random.randint(120, 700), steps=random.randint(8, 20))
        await page.mouse.wheel(0, random.randint(180, 650))
        await _random_delay(1.0, 2.5)


def _build_search_url(product_url: str) -> str:
    parts = [part for part in re.split(r"[^a-z0-9]+", product_url.lower()) if part]
    keywords = [part for part in parts if not part.isdigit() and part not in {"https", "www", "shein", "com", "vn", "html", "p"}]
    query = " ".join(keywords[:4]).strip() or "hoodie"
    return f"https://www.shein.com.vn/pdsearch/{quote_plus(query)}/"


async def warm_up_logged_in_session(page: Page, product_url: str) -> None:
    LOGGER.info("SHEIN: warm up logged-in session")
    await page.goto(SHEIN_ACCOUNT_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    if await is_shein_verification_page(page):
        await wait_for_manual_verification_async(page, "opening SHEIN account page")
        await page.reload(wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    await _random_delay(2.0, 4.0)

    search_url = _build_search_url(product_url)
    LOGGER.info("SHEIN: warm up search page")
    await page.goto(search_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    if await is_shein_verification_page(page):
        await wait_for_manual_verification_async(page, f"opening SHEIN search page {search_url}")
        await page.reload(wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    await simulate_user_behavior(page)


async def open_product(page: Page, product_url: str) -> None:
    LOGGER.info("SHEIN: open product")
    await page.goto(_normalize_product_url(product_url), wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    if await is_shein_verification_page(page):
        await wait_for_manual_verification_async(page, f"opening product page {product_url}")
        await page.reload(wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
    await _random_delay(5.0, 8.0)
    for selector in SHEIN_READY_SELECTORS:
        try:
            await page.locator(selector).first.wait_for(state="attached", timeout=5000)
            return
        except PlaywrightTimeoutError:
            continue

    if await is_shein_verification_page(page):
        await wait_for_manual_verification_async(page, f"waiting for product content {product_url}")
        await page.reload(wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
        for selector in SHEIN_READY_SELECTORS:
            try:
                await page.locator(selector).first.wait_for(state="attached", timeout=5000)
                return
            except PlaywrightTimeoutError:
                continue

    raise RuntimeError(f"SHEIN product page did not become ready: {product_url}")


async def extract_title(page: Page) -> str:
    try:
        return _normalize_text(
            await page.evaluate(
                """
                () => {
                  const selectors = ["[data-testid='product-intro-title']", ".product-intro__head-name", "h1"];
                  for (const selector of selectors) {
                    const node = document.querySelector(selector);
                    if (node && (node.innerText || node.textContent)) {
                      return (node.innerText || node.textContent || "").trim();
                    }
                  }
                  return document.title || "";
                }
                """
            )
        )
    except Exception:
        return ""


async def extract_price(page: Page) -> str:
    try:
        return _normalize_text(
            await page.evaluate(
                """
                () => {
                  const selectors = [
                    "[data-testid='finalPrice']",
                    ".product-intro__head-mainprice",
                    ".from",
                    "[class*='price']"
                  ];
                  for (const selector of selectors) {
                    const node = document.querySelector(selector);
                    if (node && (node.innerText || node.textContent)) {
                      return (node.innerText || node.textContent || "").trim();
                    }
                  }
                  return "";
                }
                """
            )
        )
    except Exception:
        return ""


async def extract_images(page: Page) -> list[str]:
    try:
        images = await page.evaluate(
            """
            () => {
              const values = [];
              for (const node of document.querySelectorAll("img")) {
                const value = node.currentSrc || node.getAttribute("src") || node.getAttribute("data-src") || "";
                if (value) values.push(value);
              }
              return values;
            }
            """
        )
    except Exception:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in images or []:
        value = _normalize_image_url(str(item or ""))
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


async def extract_description(page: Page) -> str:
    try:
        return _normalize_text(
            await page.evaluate(
                """
                () => {
                  const selectors = [
                    "[data-testid='product-detail-desc']",
                    ".product-intro__description",
                    "[class*='description']"
                  ];
                  for (const selector of selectors) {
                    const node = document.querySelector(selector);
                    if (node && (node.innerText || node.textContent)) {
                      return (node.innerText || node.textContent || "").trim();
                    }
                  }
                  return "";
                }
                """
            )
        )
    except Exception:
        return ""


async def extract_variants(page: Page) -> list[ProductVariant]:
    try:
        variant_payload = await page.evaluate(
            """
            () => {
              const groups = [];
              const addGroup = (name, values) => {
                if (name && values && values.length) groups.push({ name, values });
              };

              for (const container of document.querySelectorAll("[class*='size'], [class*='color'], [class*='attr']")) {
                const text = (container.textContent || "").trim();
                if (!text) continue;
              }

              const sizeValues = [];
              const colorValues = [];
              for (const button of document.querySelectorAll("button, div, span")) {
                const text = (button.textContent || "").trim();
                if (!text || text.length > 40) continue;
                const lowered = text.toLowerCase();
                if (/^(xxs|xs|s|m|l|xl|xxl|xxxl|\\d{2,3})$/.test(lowered)) {
                  sizeValues.push(text);
                }
                if (/(black|white|blue|red|pink|green|grey|gray|brown|beige|khaki)/.test(lowered)) {
                  colorValues.push(text);
                }
              }
              addGroup("size", [...new Set(sizeValues)]);
              addGroup("color", [...new Set(colorValues)]);
              return groups;
            }
            """
        )
    except Exception:
        return []

    sizes: list[str] = []
    colors: list[str] = []
    for group in variant_payload or []:
        if not isinstance(group, dict):
            continue
        name = str(group.get("name") or "").lower()
        values = [_normalize_text(item) for item in group.get("values", []) if _normalize_text(item)]
        if name == "size":
            sizes = values
        elif name == "color":
            colors = values

    if not sizes and not colors:
        return []
    if not sizes:
        sizes = [""]
    if not colors:
        colors = [""]

    variants: list[ProductVariant] = []
    for size in sizes:
        for color in colors:
            variants.append(ProductVariant(size=size, color=color))
    return variants


async def extract_product_data(page: Page, product_url: str) -> ProductModel:
    LOGGER.info("SHEIN: extract data")
    title = await extract_title(page)
    price = await extract_price(page)
    images = await extract_images(page)
    description = await extract_description(page)
    variants = await extract_variants(page)
    return ProductModel(
        source="shein",
        product_url=_normalize_product_url(product_url),
        title=title,
        price=price,
        images=images,
        description=description,
        variants=variants,
    )


class CrawlerShein(BaseCrawler):
    """Async Playwright crawler for one SHEIN product."""

    async def _crawl_product_async(self, url: str) -> ProductModel:
        playwright: Playwright | None = None
        context: BrowserContext | None = None
        page: Page | None = None
        try:
            LOGGER.info("SHEIN: launch browser")
            playwright, context, page = await launch_shein_persistent_context_async()

            await open_homepage(page)
            await simulate_user_behavior(page)
            await warm_up_logged_in_session(page, url)
            await open_product(page, url)
            return await extract_product_data(page, url)
        except Exception:
            LOGGER.exception("SHEIN crawl failed for URL: %s", url)
            raise
        finally:
            if context is not None:
                await context.close()
            if playwright is not None:
                await playwright.stop()

    def crawl_product(self, url: str) -> ProductModel:
        return asyncio.run(self._crawl_product_async(url))
