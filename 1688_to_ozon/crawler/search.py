import logging
import time
from urllib.parse import quote, urlsplit, urlunsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import DEFAULT_TIMEOUT, SEARCH_MAX_LINKS, SEARCH_SCROLL_ROUNDS
from crawler.session import is_verification_page, wait_for_manual_verification
from utils import logger as logger_module


def _get_logger() -> logging.Logger:
    """Return project logger with a safe fallback."""
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("crawler.search")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("crawler.search")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = _get_logger()

SEARCH_URL_TIMEOUT = max(DEFAULT_TIMEOUT, 60000)
SEARCH_URL_ATTEMPTS = 3
SEARCH_SNAPSHOT_ATTEMPTS = 3
SEARCH_REFERER = "https://www.1688.com/"
SEARCH_HOMEPAGE_URL = "https://www.1688.com/"
SEARCH_HOMEPAGE_TIMEOUT = min(SEARCH_URL_TIMEOUT, 20000)
SHOP_PAGE_LIMIT = 20


def normalize_product_url(url: str) -> str:
    """Keep only the canonical 1688 product URL without query string or fragment."""
    if not url:
        return ""

    parts = urlsplit(url.strip())
    normalized = urlunsplit((parts.scheme or "https", parts.netloc, parts.path, "", ""))
    if normalized.endswith("/"):
        normalized = normalized.rstrip("/")
    return normalized


def normalize_listing_url(url: str) -> str:
    """Normalize a non-product listing URL while keeping query params."""
    if not url:
        return ""

    parts = urlsplit(url.strip())
    normalized = urlunsplit((parts.scheme or "https", parts.netloc, parts.path, parts.query, ""))
    if normalized.endswith("/") and not parts.query:
        normalized = normalized.rstrip("/")
    return normalized


def is_product_detail_url(url: str) -> bool:
    """Return True when the URL points to a 1688 product detail page."""
    return "detail.1688.com/offer/" in normalize_product_url(url)


def _warmup_1688_homepage(page) -> None:
    """Warm up cookies and anti-bot checks by touching the 1688 homepage first."""
    try:
        LOGGER.info("Warming up 1688 homepage before opening search results")
        page.goto(
            SEARCH_HOMEPAGE_URL,
            wait_until="commit",
            timeout=SEARCH_HOMEPAGE_TIMEOUT,
            referer=SEARCH_REFERER,
        )
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(1200)
    except Exception as exc:
        LOGGER.warning("Homepage warmup did not complete cleanly: %s", exc)


def open_search_page(page, search_url: str, keyword: str) -> None:
    """Open a 1688 search page with a couple of fallback attempts."""
    wait_strategies = ("domcontentloaded", "load", "commit")
    candidate_urls = (
        search_url,
        search_url.replace("https://s.1688.com", "https://s.1688.com"),
        search_url.replace("/selloffer/offer_search.htm", "/selloffer/offer_search.htm#"),
    )
    last_error: Exception | None = None
    _warmup_1688_homepage(page)

    attempt = 0
    for candidate_url in candidate_urls:
        for wait_until in wait_strategies[:SEARCH_URL_ATTEMPTS]:
            attempt += 1
            try:
                LOGGER.info(
                    "Opening 1688 search page (attempt %s, wait_until=%s): %s",
                    attempt,
                    wait_until,
                    candidate_url,
                )
                page.goto(
                    candidate_url,
                    wait_until=wait_until,
                    timeout=SEARCH_URL_TIMEOUT,
                    referer=SEARCH_REFERER,
                )
                for load_state in ("domcontentloaded", "load"):
                    try:
                        page.wait_for_load_state(load_state, timeout=5000)
                    except PlaywrightTimeoutError:
                        continue
                if is_verification_page(page):
                    wait_for_manual_verification(page, reason=f"search keyword='{keyword}'")
                page.wait_for_timeout(1500)
                return
            except PlaywrightTimeoutError as exc:
                last_error = exc
                if is_verification_page(page):
                    wait_for_manual_verification(page, reason=f"search keyword='{keyword}' after timeout")
                    return
                LOGGER.warning(
                    "Search page load timed out for keyword='%s' on attempt %s (%s)",
                    keyword,
                    attempt,
                    wait_until,
                )
            except PlaywrightError as exc:
                last_error = exc
                if is_verification_page(page):
                    wait_for_manual_verification(page, reason=f"search keyword='{keyword}' after navigation error")
                    return
                LOGGER.warning(
                    "Search page failed for keyword='%s' on attempt %s (%s): %s",
                    keyword,
                    attempt,
                    wait_until,
                    exc,
                )
            page.wait_for_timeout(1200)

    raise RuntimeError(
        f"Khong mo duoc trang tim kiem 1688 cho keyword='{keyword}' sau nhieu lan thu. "
        "Hay kiem tra lai mang, session dang nhap, hoac thu chay lai sau."
    ) from last_error


def _snapshot_anchor_hrefs(page) -> list[str]:
    """Collect current anchor hrefs while tolerating transient 1688 navigations."""
    last_error: Exception | None = None

    for attempt in range(1, SEARCH_SNAPSHOT_ATTEMPTS + 1):
        try:
            if is_verification_page(page):
                wait_for_manual_verification(page, reason="collecting search result links")
            return page.locator("a").evaluate_all("(elements) => elements.map((el) => el.href || '')")
        except PlaywrightError as exc:
            last_error = exc
            if "Execution context was destroyed" not in str(exc):
                raise

            LOGGER.warning(
                "Search page navigated while collecting links (attempt %s/%s). Retrying...",
                attempt,
                SEARCH_SNAPSHOT_ATTEMPTS,
            )
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(800)

    if last_error is not None:
        raise last_error
    return []


def _snapshot_anchor_payloads(page) -> list[dict[str, str]]:
    """Collect href/text pairs while tolerating transient 1688 navigations."""
    last_error: Exception | None = None

    for attempt in range(1, SEARCH_SNAPSHOT_ATTEMPTS + 1):
        try:
            if is_verification_page(page):
                wait_for_manual_verification(page, reason="collecting listing anchors")
            payloads = page.locator("a").evaluate_all(
                """
                (elements) => elements.map((el) => ({
                  href: el.href || "",
                  text: (el.innerText || el.textContent || "").trim(),
                }))
                """
            )
            return [item for item in payloads if isinstance(item, dict)]
        except PlaywrightError as exc:
            last_error = exc
            if "Execution context was destroyed" not in str(exc):
                raise

            LOGGER.warning(
                "Listing page navigated while collecting anchors (attempt %s/%s). Retrying...",
                attempt,
                SEARCH_SNAPSHOT_ATTEMPTS,
            )
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(800)

    if last_error is not None:
        raise last_error
    return []


def _extract_product_links_from_hrefs(hrefs: list[str], max_links: int) -> list[str]:
    """Extract canonical product URLs from a list of raw hrefs."""
    unique_links: list[str] = []
    seen_links: set[str] = set()

    for href in hrefs:
        normalized_url = normalize_product_url(href)
        if not is_product_detail_url(normalized_url):
            continue
        if normalized_url in seen_links:
            continue
        seen_links.add(normalized_url)
        unique_links.append(normalized_url)
        if len(unique_links) >= max_links:
            break

    return unique_links[:max_links]


def _collect_product_links_from_payloads(
    payloads: list[dict[str, str]],
    unique_links: list[str],
    seen_links: set[str],
    max_links: int,
) -> None:
    """Merge product URLs from anchor payloads into the running result set."""
    for payload in payloads:
        href = payload.get("href", "")
        normalized_url = normalize_product_url(href)
        if not is_product_detail_url(normalized_url):
            continue
        if normalized_url in seen_links:
            continue
        seen_links.add(normalized_url)
        unique_links.append(normalized_url)
        if len(unique_links) >= max_links:
            return


def _collect_pagination_urls(
    payloads: list[dict[str, str]],
    current_url: str,
    pending_pages: list[str],
    queued_pages: set[str],
) -> None:
    """Queue likely shop pagination URLs discovered on the current listing page."""
    current_parts = urlsplit(current_url)
    current_host = current_parts.netloc.lower()

    for payload in payloads:
        href = normalize_listing_url(payload.get("href", ""))
        if not href:
            continue
        href_parts = urlsplit(href)
        href_host = href_parts.netloc.lower()
        if not href_host or href_host != current_host:
            continue
        if is_product_detail_url(href):
            continue

        text = str(payload.get("text", "") or "").strip().lower()
        path = href_parts.path.lower()
        query = href_parts.query.lower()
        looks_like_pagination = text.isdigit() or text in {"next", ">", ">>", "下一页", "下页"}
        if not looks_like_pagination and not any(token in f"{path}?{query}" for token in ("page=", "pagenum=", "offerlist", "search")):
            continue
        if href in queued_pages:
            continue
        queued_pages.add(href)
        pending_pages.append(href)


def _safe_get_scroll_height(page) -> int:
    """Read a stable page height even when body/html is temporarily unavailable."""
    try:
        height = page.evaluate(
            """
            () => {
              const body = document.body;
              const doc = document.documentElement;
              const candidates = [
                body ? body.scrollHeight : 0,
                body ? body.offsetHeight : 0,
                doc ? doc.scrollHeight : 0,
                doc ? doc.offsetHeight : 0,
                doc ? doc.clientHeight : 0,
              ].filter((value) => Number.isFinite(value) && value > 0);
              return candidates.length ? Math.max(...candidates) : 0;
            }
            """
        )
        return int(height or 0)
    except PlaywrightError as exc:
        LOGGER.warning("Could not read search page scroll height yet: %s", exc)
        return 0


def get_product_links(page, keyword: str, max_links: int = 50) -> list[str]:
    """Search 1688 by keyword and collect unique product detail links."""
    keyword = keyword.strip()
    if not keyword:
        LOGGER.warning("Keyword is empty, no product links collected.")
        return []

    max_links = min(max_links, SEARCH_MAX_LINKS)
    encoded_keyword = quote(keyword, safe="")
    search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_keyword}"

    LOGGER.info("Searching 1688 with keyword='%s'", keyword)
    open_search_page(page, search_url, keyword)

    unique_links: list[str] = []
    seen_links: set[str] = set()
    previous_height = 0

    for scroll_round in range(SEARCH_SCROLL_ROUNDS):
        if is_verification_page(page):
            wait_for_manual_verification(page, reason=f"scroll round {scroll_round + 1}")
        payloads = _snapshot_anchor_payloads(page)
        _collect_product_links_from_payloads(payloads, unique_links, seen_links, max_links)
        if len(unique_links) >= max_links:
            LOGGER.info("Collected %s product links from 1688", len(unique_links))
            return unique_links[:max_links]

        current_height = _safe_get_scroll_height(page)
        scroll_amount = current_height if current_height > 0 else 1200
        page.mouse.wheel(0, scroll_amount)
        page.wait_for_timeout(1200)
        time.sleep(0.3)

        LOGGER.info(
            "Scroll round %s/%s, collected %s links",
            scroll_round + 1,
            SEARCH_SCROLL_ROUNDS,
            len(unique_links),
        )

        if current_height == previous_height:
            break
        previous_height = current_height

    LOGGER.info("Collected %s product links from 1688", len(unique_links))
    return unique_links[:max_links]


def get_shop_product_links(page, shop_url: str, max_links: int = 50) -> list[str]:
    """Open a 1688 shop/listing URL and collect product detail links across listing pages."""
    shop_url = normalize_listing_url(shop_url)
    if not shop_url:
        LOGGER.warning("Shop URL is empty, no product links collected.")
        return []

    max_links = min(max_links, SEARCH_MAX_LINKS)
    LOGGER.info("Collecting product links from shop URL='%s'", shop_url)

    unique_links: list[str] = []
    seen_links: set[str] = set()
    pending_pages: list[str] = [shop_url]
    queued_pages: set[str] = {shop_url}
    visited_pages: set[str] = set()

    while pending_pages and len(visited_pages) < SHOP_PAGE_LIMIT and len(unique_links) < max_links:
        current_url = pending_pages.pop(0)
        if current_url in visited_pages:
            continue
        visited_pages.add(current_url)
        open_search_page(page, current_url, f"shop:{current_url}")

        previous_height = 0
        for scroll_round in range(SEARCH_SCROLL_ROUNDS):
            if is_verification_page(page):
                wait_for_manual_verification(page, reason=f"shop scroll round {scroll_round + 1}")
            payloads = _snapshot_anchor_payloads(page)
            _collect_product_links_from_payloads(payloads, unique_links, seen_links, max_links)
            _collect_pagination_urls(payloads, current_url, pending_pages, queued_pages)
            if len(unique_links) >= max_links:
                LOGGER.info("Collected %s product links from shop URL", len(unique_links))
                return unique_links[:max_links]

            current_height = _safe_get_scroll_height(page)
            scroll_amount = current_height if current_height > 0 else 1200
            page.mouse.wheel(0, scroll_amount)
            page.wait_for_timeout(1200)
            time.sleep(0.3)

            LOGGER.info(
                "Shop page %s, scroll round %s/%s, collected %s links",
                len(visited_pages),
                scroll_round + 1,
                SEARCH_SCROLL_ROUNDS,
                len(unique_links),
            )

            if current_height == previous_height:
                break
            previous_height = current_height

    LOGGER.info("Collected %s product links from shop URL", len(unique_links))
    return unique_links[:max_links]
