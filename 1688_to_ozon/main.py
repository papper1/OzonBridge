import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from config import (
    CLEAN_DATA_DIR,
    DEFAULT_TIMEOUT,
    EXPORT_DIR,
    HEADLESS,
    RAW_DATA_DIR,
    SEARCH_MAX_LINKS,
    SEARCH_SCROLL_ROUNDS,
    SESSION_FILE,
    ensure_directories,
)
from crawler import product as product_crawler
from crawler import search as search_crawler
from crawler.session import create_context_with_session
from services.zyte_source_service import crawl_source_product as crawl_zyte_source_product
from mapper import product_mapper
from normalizer.build_variants import build_product_variants
from normalizer.normalize_attributes import normalize_product as normalize_raw_product
from ozon import export_xlsx
from storage import file_store
from translator.ai_hashtag_service import generate_hashtags
from translator.ai_translator import translate_product_fields
from utils import logger as logger_module


def get_logger() -> logging.Logger:
    """Return a project logger with a safe fallback."""
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("1688_to_ozon")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("1688_to_ozon")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = get_logger()
SOURCE_1688 = "1688"
SOURCE_SHEIN = "shein"
SOURCE_ETSY = "etsy"
SOURCE_EBAY = "ebay"
SOURCE_MODE_KEYWORD = "keyword"
SOURCE_MODE_PRODUCT_URL = "product_url"
SOURCE_MODE_SHOP_URL = "shop_url"


def is_shein_url(value: str) -> bool:
    """Return True when the input points to a SHEIN product/domain."""
    lowered = str(value or "").strip().lower()
    return "shein.com/" in lowered or "shein.com.vn/" in lowered


def is_etsy_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return "etsy.com/listing/" in lowered


def is_ebay_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return "ebay.com/itm/" in lowered


def is_zyte_source(source: str) -> bool:
    return str(source or "").strip().lower() in {SOURCE_SHEIN, SOURCE_ETSY, SOURCE_EBAY}


def resolve_callable(module: Any, candidate_names: tuple[str, ...]) -> Callable[..., Any]:
    """Find the first callable that exists in a module."""
    for name in candidate_names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    raise NotImplementedError(
        f"Missing implementation in module '{module.__name__}'. "
        f"Expected one of: {', '.join(candidate_names)}"
    )


def save_json_with_fallback(data: Any, output_path: Path) -> Path:
    """Save JSON using storage.file_store if available, otherwise write directly."""
    for fn_name in ("save_json", "write_json", "dump_json", "save_data"):
        fn = getattr(file_store, fn_name, None)
        if not callable(fn):
            continue

        try:
            result = fn(data, output_path)
        except TypeError:
            try:
                result = fn(output_path, data)
            except TypeError:
                continue

        return Path(result) if result else output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def export_ozon_with_fallback(products: list[dict[str, Any]], output_path: Path) -> Path:
    """Export mapped products to Excel using ozon.export_xlsx if available."""
    for fn_name in ("export_products", "export_to_xlsx", "export_xlsx", "save_xlsx"):
        fn = getattr(export_xlsx, fn_name, None)
        if not callable(fn):
            continue

        try:
            result = fn(products, output_path)
        except TypeError:
            try:
                result = fn(output_path, products)
            except TypeError:
                continue

        return Path(result) if result else output_path

    raise NotImplementedError(
        "No Excel export function found in ozon.export_xlsx. "
        "Expected one of: export_products, export_to_xlsx, export_xlsx, save_xlsx"
    )


def create_browser_page(source: str = SOURCE_1688) -> tuple[Any, Browser, BrowserContext, Page]:
    """Start the source-specific browser workflow and return browser objects."""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=HEADLESS)
    context = create_context_with_session(browser, str(SESSION_FILE))
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    return playwright, browser, context, page


def detect_source(source_value: str, source: str = "") -> str:
    """Resolve the marketplace source from explicit input or the URL."""
    normalized_source = str(source or "").strip().lower()
    if normalized_source and normalized_source in {SOURCE_1688, SOURCE_SHEIN, SOURCE_ETSY, SOURCE_EBAY}:
        return normalized_source

    lowered = str(source_value or "").strip().lower()
    if is_shein_url(lowered):
        return SOURCE_SHEIN
    if is_etsy_url(lowered):
        return SOURCE_ETSY
    if is_ebay_url(lowered):
        return SOURCE_EBAY
    return SOURCE_1688


def detect_input_mode(source_value: str) -> str:
    """Infer whether the user provided a keyword, product URL, or shop URL."""
    text = str(source_value or "").strip()
    if not text:
        return SOURCE_MODE_KEYWORD

    lowered = text.lower()
    if lowered.startswith(("http://", "https://")):
        if is_shein_url(lowered) or is_etsy_url(lowered) or is_ebay_url(lowered):
            return SOURCE_MODE_PRODUCT_URL
        if "detail.1688.com/offer/" in lowered:
            return SOURCE_MODE_PRODUCT_URL
        if "1688.com" in lowered:
            return SOURCE_MODE_SHOP_URL
    return SOURCE_MODE_KEYWORD


def normalize_source_value(source_value: str, source_mode: str) -> str:
    """Normalize source input based on the selected crawl mode."""
    text = str(source_value or "").strip()
    if source_mode == SOURCE_MODE_PRODUCT_URL:
        normalize_fn = getattr(product_crawler, "normalize_product_url", None)
        if callable(normalize_fn):
            return normalize_fn(text)
        fallback_fn = getattr(search_crawler, "normalize_product_url", None)
        return fallback_fn(text) if callable(fallback_fn) else text
    if source_mode == SOURCE_MODE_SHOP_URL:
        normalize_fn = getattr(search_crawler, "normalize_listing_url", None)
        return normalize_fn(text) if callable(normalize_fn) else text
    return text


def build_export_stem(source_value: str, source_mode: str) -> str:
    """Build a stable export filename stem from the crawl source."""
    text = normalize_source_value(source_value, source_mode)
    if source_mode == SOURCE_MODE_PRODUCT_URL:
        if is_shein_url(text):
            parts = [part for part in re.split(r"[^a-z0-9]+", text.lower()) if part]
            return "_".join(parts[-4:])[:60].strip("_") or "shein"
        if is_etsy_url(text):
            match = re.search(r"/listing/(\d+)", text)
            return f"etsy_{match.group(1)}" if match else "etsy"
        if is_ebay_url(text):
            match = re.search(r"/itm/(?:[^/]+/)?(\d+)", text)
            return f"ebay_{match.group(1)}" if match else "ebay"
        match = re.search(r"/(\d+)\.html", text)
        return f"product_{match.group(1)}" if match else "product"
    if source_mode == SOURCE_MODE_SHOP_URL:
        parts = re.findall(r"[a-z0-9]+", text.lower())
        if not parts:
            return "shop"
        return "_".join(parts[-4:])[:60].strip("_") or "shop"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug[:60] or "keyword"


def fetch_product_links(page: Page, keyword: str, max_links: int) -> list[str]:
    """Fetch product links from 1688 search results."""
    search_fn = resolve_callable(
        search_crawler,
        (
            "search_products",
            "get_product_links",
            "fetch_product_links",
            "search",
        ),
    )

    try:
        links = search_fn(
            page=page,
            keyword=keyword,
            max_links=max_links,
            scroll_rounds=SEARCH_SCROLL_ROUNDS,
        )
    except TypeError:
        links = search_fn(page, keyword, max_links)

    if not isinstance(links, list):
        raise ValueError("Search crawler must return a list of product links.")

    return links[:max_links]


def fetch_shop_product_links(page: Page, shop_url: str, max_links: int) -> list[str]:
    """Fetch product links from a 1688 shop/listing page."""
    shop_fn = resolve_callable(
        search_crawler,
        (
            "get_shop_product_links",
            "fetch_shop_product_links",
            "crawl_shop_product_links",
        ),
    )

    try:
        links = shop_fn(page=page, shop_url=shop_url, max_links=max_links)
    except TypeError:
        links = shop_fn(page, shop_url, max_links)

    if not isinstance(links, list):
        raise ValueError("Shop crawler must return a list of product links.")

    return links[:max_links]


def crawl_product_detail(
    page: Page,
    product_link: str,
    source: str = SOURCE_1688,
    crawl_hint: str = "",
) -> dict[str, Any]:
    """Crawl one product detail page from the selected marketplace."""
    normalized_source = str(source or SOURCE_1688).strip().lower()
    if is_zyte_source(normalized_source):
        return crawl_zyte_source_product(product_link, normalized_source)

    crawl_fn = resolve_callable(
        product_crawler,
        (
            "crawl_product",
            "get_product_detail",
            "fetch_product",
            "parse_product",
        ),
    )

    try:
        raw_product = crawl_fn(page=page, product_url=product_link)
    except TypeError:
        try:
            raw_product = crawl_fn(page=page, url=product_link)
        except TypeError:
            raw_product = crawl_fn(page, product_link)

    if not isinstance(raw_product, dict):
        raise ValueError("Product crawler must return a dict.")

    return raw_product


def normalize_product(raw_product: dict[str, Any]) -> dict[str, Any]:
    """Normalize attributes and build variants for one raw product."""
    normalized = normalize_raw_product(raw_product)
    normalized_with_variants = build_product_variants(
        normalized,
        price=str(raw_product.get("price", "") or ""),
    )

    if not isinstance(normalized_with_variants, dict):
        raise ValueError("Normalizer must return a dict.")

    return normalized_with_variants


def map_to_ozon_product(normalized_product: dict[str, Any]) -> dict[str, Any]:
    """Map normalized product to Ozon format."""
    map_fn = resolve_callable(
        product_mapper,
        (
            "map_product",
            "map_to_ozon_product",
            "build_ozon_product",
            "transform_product",
        ),
    )

    mapped_product = map_fn(normalized_product)
    if not isinstance(mapped_product, dict):
        raise ValueError("Product mapper must return a dict.")

    return mapped_product


def process_single_product(
    page: Page,
    product_link: str,
    index: int,
    source: str = SOURCE_1688,
    crawl_hint: str = "",
) -> dict[str, Any] | None:
    """Process one product end-to-end without breaking the full pipeline on errors."""
    try:
        LOGGER.info("Step 4/8 - Crawling product %s: %s", index, product_link)
        raw_product = crawl_product_detail(page, product_link, source=source, crawl_hint=crawl_hint)

        raw_path = RAW_DATA_DIR / f"product_{index:03d}.json"
        save_json_with_fallback(raw_product, raw_path)
        LOGGER.info("Step 5/8 - Saved raw product %s to %s", index, raw_path)

        normalized_product = normalize_product(raw_product)
        normalized_product = translate_product_fields(normalized_product)
        normalized_product = generate_hashtags(normalized_product)
        clean_path = CLEAN_DATA_DIR / f"product_{index:03d}.json"
        save_json_with_fallback(normalized_product, clean_path)
        LOGGER.info("Step 6/8 - Normalized, translated, and generated hashtags for product %s", index)

        ozon_product = map_to_ozon_product(normalized_product)
        LOGGER.info("Step 7/8 - Mapped product %s to Ozon format", index)
        return ozon_product
    except Exception as exc:
        LOGGER.exception("Product %s failed and will be skipped: %s", index, exc)
        return None


def resolve_product_links(page: Page, source_value: str, source_mode: str, max_links: int) -> list[str]:
    """Resolve one or more product links from any supported crawl source."""
    normalized_value = normalize_source_value(source_value, source_mode)
    if source_mode == SOURCE_MODE_PRODUCT_URL:
        return [normalized_value] if normalized_value else []
    if source_mode == SOURCE_MODE_SHOP_URL:
        return fetch_shop_product_links(page=page, shop_url=normalized_value, max_links=max_links)
    return fetch_product_links(page=page, keyword=normalized_value, max_links=max_links)


def run_pipeline(
    keyword: str,
    max_links: int = 5,
    source_mode: str = SOURCE_MODE_KEYWORD,
    source: str = "",
    crawl_hint: str = "",
) -> Path | None:
    """Run the full crawl-to-export pipeline for a supported marketplace source."""
    source = detect_source(keyword, source)
    source_mode = str(source_mode or SOURCE_MODE_KEYWORD).strip() or SOURCE_MODE_KEYWORD
    keyword = normalize_source_value(keyword, source_mode)
    if is_zyte_source(source):
        source_mode = SOURCE_MODE_PRODUCT_URL
        max_links = 1
        validators = {
            SOURCE_SHEIN: is_shein_url,
            SOURCE_ETSY: is_etsy_url,
            SOURCE_EBAY: is_ebay_url,
        }
        if not validators[source](keyword):
            raise ValueError(f"{source.upper()} crawl currently supports only one product URL at a time.")
    else:
        max_links = min(max_links, SEARCH_MAX_LINKS)
    ensure_directories()
    LOGGER.info("Step 1/8 - Ensured data directories exist for source='%s'", source)

    playwright = None
    browser = None
    context = None
    page = None

    try:
        if is_zyte_source(source):
            raw_product = crawl_product_detail(
                page=None,  # type: ignore[arg-type]
                product_link=keyword,
                source=source,
                crawl_hint=crawl_hint,
            )
            raw_path = RAW_DATA_DIR / "product_001.json"
            save_json_with_fallback(raw_product, raw_path)
            source_raw_path = RAW_DATA_DIR / f"{source}_{build_export_stem(keyword, source_mode)}.json"
            save_json_with_fallback(raw_product, source_raw_path)
            LOGGER.info("Step 2/8 - Saved raw %s product to %s", source, raw_path)
            if raw_product.get("status") == "blocked":
                raise RuntimeError(raw_product.get("message") or f"{source.upper()} product is blocked by challenge page.")

            normalized_product = normalize_product(raw_product)
            normalized_product = translate_product_fields(normalized_product)
            normalized_product = generate_hashtags(normalized_product)
            clean_path = CLEAN_DATA_DIR / "product_001.json"
            save_json_with_fallback(normalized_product, clean_path)
            source_clean_path = CLEAN_DATA_DIR / f"clean_{source}_{build_export_stem(keyword, source_mode)}.json"
            save_json_with_fallback(normalized_product, source_clean_path)
            LOGGER.info("Step 3/8 - Normalized, translated, and generated hashtags for %s product", source)

            ozon_product = map_to_ozon_product(normalized_product)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = EXPORT_DIR / f"ozon_{build_export_stem(keyword, source_mode)}_{timestamp}.xlsx"
            export_ozon_with_fallback([ozon_product], output_path)
            LOGGER.info("Step 4/8 - Exported %s product to %s", source, output_path)
            return output_path

        playwright, browser, context, page = create_browser_page(source=source)
        LOGGER.info("Step 2/8 - Initialized Playwright browser/context/page")

        product_links = resolve_product_links(page=page, source_value=keyword, source_mode=source_mode, max_links=max_links)
        source_label = {
            SOURCE_MODE_PRODUCT_URL: "product URL",
            SOURCE_MODE_SHOP_URL: "shop URL",
        }.get(source_mode, "keyword")
        LOGGER.info(
            "Step 3/8 - Collected %s product links from source='%s' using %s '%s'",
            len(product_links),
            source,
            source_label,
            keyword,
        )

        ozon_products: list[dict[str, Any]] = []
        for index, product_link in enumerate(product_links, start=1):
            mapped_product = process_single_product(
                page=page,
                product_link=product_link,
                index=index,
                source=source,
                crawl_hint=crawl_hint,
            )
            if mapped_product is not None:
                ozon_products.append(mapped_product)

        if not ozon_products:
            LOGGER.warning("No products were processed successfully. Skipping Excel export.")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EXPORT_DIR / f"ozon_{build_export_stem(keyword, source_mode)}_{timestamp}.xlsx"
        export_ozon_with_fallback(ozon_products, output_path)
        LOGGER.info("Step 8/8 - Exported %s products to %s", len(ozon_products), output_path)
        return output_path
    finally:
        if page is not None:
            page.close()
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()


def main() -> None:
    """Run a local demo pipeline."""
    keyword = "laptop"
    LOGGER.info("Starting pipeline with keyword='%s'", keyword)
    output_path = run_pipeline(keyword=keyword, max_links=5, source_mode=SOURCE_MODE_KEYWORD, source=SOURCE_1688)

    if output_path is not None:
        LOGGER.info("Pipeline finished successfully. Excel file: %s", output_path)
    else:
        LOGGER.warning("Pipeline finished without export output.")


if __name__ == "__main__":
    main()
