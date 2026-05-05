import json
import logging
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import DEFAULT_TIMEOUT, PRODUCT_PAGE_STABILIZE_MS, PRODUCT_PAGE_TIMEOUT
from crawler.session import is_verification_page, wait_for_manual_verification
from utils import logger as logger_module


def _get_logger() -> logging.Logger:
    """Return project logger with a safe fallback."""
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("crawler.product")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("crawler.product")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = _get_logger()

PRODUCT_READY_SELECTORS = (
    "h1",
    ".title-text",
    ".d-title",
    ".od-pc-offer-title",
    ".price",
    ".od-pc-offer-price",
    "[data-testid='product-title']",
)

NOISY_ATTRIBUTE_TEXT = (
    "inventory",
    "stock",
    "logistics",
    "shipping",
    "delivery",
    "cart",
    "buy now",
    "add to",
    "chat",
    "contact",
    "service",
    "coupon",
    "promotion",
    "discount",
    "quantity",
    "moq",
    "piece",
    "pcs",
)

IMAGE_NOISE_HINTS = (
    "icon",
    "logo",
    "avatar",
    "sprite",
    "lazyload",
    "placeholder",
    "thumb",
)

ETSY_IMAGE_HOST_HINTS = (
    "etsystatic.com",
    "etsy.com/images",
    "i.etsystatic.com",
)


def clean_text(text: str) -> str:
    """Normalize extracted text."""
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" :-|")


def _safe_get(data: Any, *path: Any) -> Any:
    """Read nested dict/list values safely."""
    current = data
    for key in path:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def _iter_nested_objects(data: Any) -> Any:
    """Yield nested dict/list nodes depth-first without revisiting objects."""
    stack = [data]
    seen: set[int] = set()

    while stack:
        current = stack.pop()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        yield current

        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _find_first_nested_key(data: Any, target_key: str) -> Any:
    """Find the first value stored under the given key anywhere in nested data."""
    for current in _iter_nested_objects(data):
        if isinstance(current, dict) and target_key in current:
            value = current.get(target_key)
            if value not in (None, "", [], {}, ()):
                return value
    return None


def _extract_sku_image_list_from_dom(page) -> list[dict[str, str]]:
    """Extract color-option images directly from DOM when JS bootstrap data omits them."""
    try:
        items = page.evaluate(
            """
            () => {
              const collectImage = (root) => {
                if (!root || !(root instanceof Element)) return "";

                const imageNode = root.matches("img") ? root : root.querySelector("img");
                if (imageNode) {
                  const imageValue =
                    imageNode.currentSrc ||
                    imageNode.getAttribute("src") ||
                    imageNode.getAttribute("data-src") ||
                    imageNode.getAttribute("data-lazy-src") ||
                    imageNode.getAttribute("data-img") ||
                    "";
                  if (imageValue) {
                    return imageValue;
                  }
                }

                const nodes = [root, ...root.querySelectorAll("*")];
                for (const node of nodes) {
                  const style = window.getComputedStyle(node);
                  const background = style ? style.backgroundImage || "" : "";
                  const match = background.match(/url\\((['"]?)(.*?)\\1\\)/i);
                  if (match && match[2]) {
                    return match[2];
                  }

                  for (const attributeName of [
                    "data-img",
                    "data-image",
                    "data-image-url",
                    "data-img-url",
                    "data-src",
                    "data-lazy-src",
                    "image",
                    "img",
                  ]) {
                    const value = node.getAttribute(attributeName) || "";
                    if (value) {
                      return value;
                    }
                  }
                }
                return "";
              };

              const roots = Array.from(
                document.querySelectorAll(
                  [
                    "[class*='sku']",
                    "[class*='Sku']",
                    "[class*='prop']",
                    "[class*='Prop']",
                    "[data-spm-anchor-id*='skuSelection']",
                  ].join(",")
                )
              );

              const seen = new Set();
              const results = [];

              const pushCandidate = (label, root) => {
                const cleanLabel = (label || "").trim();
                if (!cleanLabel || seen.has(cleanLabel)) {
                  return;
                }
                const imageUrl = collectImage(root);
                if (!imageUrl) {
                  return;
                }
                seen.add(cleanLabel);
                results.push({
                  value: cleanLabel,
                  skuImageUrl: imageUrl,
                });
              };

              for (const root of roots) {
                const labelNodes = root.querySelectorAll(".label-name, [class*='label'], [class*='name'], span, div");
                for (const labelNode of labelNodes) {
                  const label = (labelNode.textContent || "").trim();
                  if (!label) {
                    continue;
                  }
                  const optionRoot = labelNode.closest("li, label, button, .sku-item, .prop-item, .value-item, .tag-item") || labelNode.parentElement || root;
                  pushCandidate(label, optionRoot);
                }
              }

              return results;
            }
            """
        )
        return list(items or []) if isinstance(items, list) else []
    except Exception:
        return []


def _looks_like_product_image(url: str) -> bool:
    """Filter out obvious non-product images."""
    if not url:
        return False

    lowered = url.lower()
    if not lowered.startswith(("http://", "https://", "//")):
        return False
    if "cbu01.alicdn.com/img/ibank/" not in lowered:
        return False
    if any(hint in lowered for hint in IMAGE_NOISE_HINTS):
        return False
    return any(ext in lowered for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif"))


def _normalize_image_url(url: str) -> str:
    """Normalize image URLs and remove query strings."""
    if not url:
        return ""
    if url.startswith("//"):
        url = f"https:{url}"

    parts = urlsplit(url.strip())
    normalized = urlunsplit((parts.scheme or "https", parts.netloc, parts.path, "", ""))
    return normalized


def normalize_product_url(url: str) -> str:
    """Keep only the canonical product URL without query string or fragment."""
    if not url:
        return ""

    parts = urlsplit(url.strip())
    normalized = urlunsplit((parts.scheme or "https", parts.netloc, parts.path, "", ""))
    return normalized.rstrip("/") if normalized.endswith("/") else normalized


def is_1688_product_url(url: str) -> bool:
    """Return True when the URL points to a 1688 product detail page."""
    return "detail.1688.com/offer/" in normalize_product_url(url).lower()


def is_etsy_product_url(url: str) -> bool:
    """Return True when the URL points to an Etsy listing page."""
    normalized = normalize_product_url(url).lower()
    return "etsy.com/listing/" in normalized


def _is_valid_attribute_pair(key: str, value: str) -> bool:
    """Filter noisy key-value pairs from unrelated blocks."""
    if not key or not value:
        return False
    if len(key) > 60 or len(value) > 200:
        return False

    lowered = f"{key} {value}".lower()
    if any(noise in lowered for noise in NOISY_ATTRIBUTE_TEXT):
        return False
    if re.search(r"\b(click|view|select|choose|login|register)\b", lowered):
        return False
    return True


def _collect_init_data(page) -> dict[str, Any] | None:
    """Collect candidate JS bootstrap data from common global variables."""
    try:
        raw_data = page.evaluate(
            """
            () => {
              const candidates = [
                window.__INIT_DATA__,
                window.__PRELOADED_STATE__,
                window.__GLOBAL_DATA__,
                window.__APP_DATA__,
                window.__NUXT__,
                window.__NEXT_DATA__,
                window.__DATA__,
              ];

              const merged = {};
              const collected = [];

              for (const item of candidates) {
                if (!item || typeof item !== "object") {
                  continue;
                }
                collected.push(item);
                for (const [key, value] of Object.entries(item)) {
                  if (!(key in merged)) {
                    merged[key] = value;
                  }
                }
              }

              if (!collected.length) {
                return null;
              }

              merged.__candidate_dicts__ = collected;
              return merged;
            }
            """
        )
        return raw_data if isinstance(raw_data, dict) else None
    except Exception:
        return None


def _collect_json_ld_objects(page) -> list[dict[str, Any]]:
    """Collect JSON-LD objects embedded in the page."""
    try:
        scripts = page.locator("script[type='application/ld+json']").evaluate_all(
            "(elements) => elements.map((el) => el.textContent || '')"
        )
    except Exception:
        return []

    objects: list[dict[str, Any]] = []
    for raw_text in scripts or []:
        text = str(raw_text or "").strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            graph_items = item.get("@graph")
            if isinstance(graph_items, list):
                for graph_item in graph_items:
                    if isinstance(graph_item, dict):
                        objects.append(graph_item)
            else:
                objects.append(item)
    return objects


def _find_first_json_ld_product(json_ld_objects: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the first Product-like JSON-LD object."""
    for item in json_ld_objects:
        type_value = str(item.get("@type") or "").lower()
        if type_value == "product" or "product" in type_value:
            return item
    return {}


def _looks_like_etsy_product_image(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    if not lowered.startswith(("http://", "https://", "//")):
        return False
    if not any(host_hint in lowered for host_hint in ETSY_IMAGE_HOST_HINTS):
        return False
    return any(ext in lowered for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif"))


def extract_title(page) -> str:
    """Extract product title from JS data or HTML."""
    try:
        title = page.evaluate(
            """
            () => {
              const selectorCandidates = [
                "h1[data-spm-anchor-id*='productTitle']",
                "h1:not([title])",
                "h1",
                ".title-text",
                ".d-title",
                ".od-pc-offer-title",
                "[data-testid='product-title']",
              ];

              for (const selector of selectorCandidates) {
                const element = document.querySelector(selector);
                if (!element) {
                  continue;
                }
                if (element.matches("h1[title]") && selector === "h1") {
                  continue;
                }
                const text = (
                  element.innerText ||
                  element.textContent ||
                  ""
                ).trim();
                if (text) {
                  return text;
                }
              }

              const globals = [
                window.__INIT_DATA__,
                window.__PRELOADED_STATE__,
                window.__GLOBAL_DATA__,
                window.__APP_DATA__,
              ];
              const keys = ["title", "subject", "name", "productTitle"];

              const visit = (node) => {
                if (!node || typeof node !== "object") return "";
                if (Array.isArray(node)) {
                  for (const item of node) {
                    const found = visit(item);
                    if (found) return found;
                  }
                  return "";
                }

                for (const key of keys) {
                  const value = node[key];
                  if (typeof value === "string" && value.trim()) return value;
                }

                for (const value of Object.values(node)) {
                  const found = visit(value);
                  if (found) return found;
                }
                return "";
              };

              for (const item of globals) {
                const found = visit(item);
                if (found) return found;
              }

              return document.title || "";
            }
            """
        )
        return clean_text(title)
    except Exception:
        return ""


def extract_price(page) -> str:
    """Extract product price from JS data or HTML."""
    try:
        price = page.evaluate(
            """
            () => {
              const globals = [
                window.__INIT_DATA__,
                window.__PRELOADED_STATE__,
                window.__GLOBAL_DATA__,
                window.__APP_DATA__,
              ];
              const keys = ["price", "priceDisplay", "showPrice", "priceStr", "displayPrice"];

              const visit = (node) => {
                if (!node || typeof node !== "object") return "";
                if (Array.isArray(node)) {
                  for (const item of node) {
                    const found = visit(item);
                    if (found) return found;
                  }
                  return "";
                }

                for (const key of keys) {
                  const value = node[key];
                  if (typeof value === "string" && value.trim()) return value;
                  if (typeof value === "number") return String(value);
                }

                for (const value of Object.values(node)) {
                  const found = visit(value);
                  if (found) return found;
                }
                return "";
              };

              for (const item of globals) {
                const found = visit(item);
                if (found) return found;
              }

              const selectors = [
                ".price",
                ".price-now",
                ".od-pc-offer-price",
                "[class*='price']",
                "[data-testid='price']"
              ];
              for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element && element.textContent) return element.textContent;
              }
              return "";
            }
            """
        )
        return clean_text(price)
    except Exception:
        return ""


def extract_images(page, init_data: dict[str, Any] | None = None) -> list[str]:
    """Extract likely product images from JS data or HTML."""
    images: list[str] = []
    seen: set[str] = set()

    def add_image(candidate: Any) -> None:
        if not isinstance(candidate, str):
            return
        normalized = _normalize_image_url(candidate)
        if not _looks_like_product_image(normalized):
            return
        if normalized in seen:
            return
        seen.add(normalized)
        images.append(normalized)

    try:
        detail_images = page.evaluate(
            """
            () => {
              const selectors = [
                "img[usemap][loading='lazy']",
                "div img[usemap]",
                "div img[loading='lazy']",
              ];

              const results = [];
              for (const selector of selectors) {
                const nodes = document.querySelectorAll(selector);
                for (const node of nodes) {
                  const src =
                    node.currentSrc ||
                    node.getAttribute("src") ||
                    node.getAttribute("data-src") ||
                    node.getAttribute("data-lazy-src") ||
                    "";
                  if (!src) {
                    continue;
                  }

                  const lowered = src.toLowerCase();
                  if (!lowered.includes("cbu01.alicdn.com/img/ibank/")) {
                    continue;
                  }

                  results.push(src);
                }
                if (results.length) {
                  break;
                }
              }
              return results;
            }
            """
        )
        for item in detail_images:
            add_image(item)
        if images:
            return images
    except Exception:
        pass

    try:
        gallery_images = page.locator("img.ant-image-img.preview-img").evaluate_all(
            """
            (elements) => elements.map((img) =>
              img.currentSrc ||
              img.src ||
              img.getAttribute('src') ||
              img.getAttribute('data-src') ||
              img.getAttribute('data-lazy-src') ||
              ''
            )
            """
        )
        for item in gallery_images:
            add_image(item)
        if images:
            return images
    except Exception:
        pass

    try:
        gallery_images = page.evaluate(
            """
            () => {
              const selectors = [
                "img.ant-image-img.preview-img.active-preview-img",
                "img.ant-image-img.preview-img",
                ".ant-image img.preview-img",
                ".preview-img",
              ];

              const results = [];
              for (const selector of selectors) {
                const nodes = document.querySelectorAll(selector);
                for (const node of nodes) {
                  const value =
                    node.currentSrc ||
                    node.getAttribute("src") ||
                    node.getAttribute("data-src") ||
                    node.getAttribute("data-lazy-src") ||
                    "";
                  if (value) {
                    results.push(value);
                  }
                }
                if (results.length) {
                  break;
                }
              }
              return results;
            }
            """
        )
        for item in gallery_images:
            add_image(item)
        if images:
            return images
    except Exception:
        pass

    try:
        if init_data:
            possible_lists = [
                _safe_get(init_data, "images"),
                _safe_get(init_data, "productImage", "images"),
                _safe_get(init_data, "data", "images"),
                _safe_get(init_data, "offerImgList"),
                _safe_get(init_data, "skuModel", "skuImageList"),
                _safe_get(init_data, "skuCore", "sku2info"),
            ]

            for item in possible_lists:
                if isinstance(item, list):
                    for entry in item:
                        if isinstance(entry, str):
                            add_image(entry)
                        elif isinstance(entry, dict):
                            for key in ("url", "imageUrl", "imgUrl", "fullPathImageURI", "originalImageURI"):
                                add_image(entry.get(key))
                elif isinstance(item, dict):
                    for value in item.values():
                        if isinstance(value, dict):
                            for key in ("skuImageUrl", "imageUrl", "imgUrl"):
                                add_image(value.get(key))
        if images:
            return images
    except Exception:
        pass

    try:
        html_images = page.locator("img").evaluate_all(
            """
            (elements) => elements.map((img) =>
              img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || ''
            )
            """
        )
        for item in html_images:
            add_image(item)
    except Exception:
        pass

    return images


def extract_attributes(page) -> dict[str, str]:
    """Extract product attributes while avoiding unrelated tables and noisy text."""
    attributes: dict[str, str] = {}

    try:
        pairs = page.evaluate(
            """
            () => {
              const results = [];
              const blocks = Array.from(document.querySelectorAll("table, ul, dl, .attributes, .specs, .detail-attrs"));

              for (const block of blocks) {
                const rows = block.querySelectorAll("tr");
                if (rows.length) {
                  for (const row of rows) {
                    const cells = row.querySelectorAll("th, td");
                    if (cells.length >= 2) {
                      for (let i = 0; i < cells.length - 1; i += 2) {
                        const key = (cells[i].textContent || "").trim();
                        const value = (cells[i + 1].textContent || "").trim();
                        if (key && value) {
                          results.push([key, value]);
                        }
                      }
                    }
                  }
                }

                const items = block.querySelectorAll("li");
                for (const item of items) {
                  const text = (item.textContent || "").trim();
                  const parts = text.split(/[:：]/).map((part) => part.trim()).filter(Boolean);
                  if (parts.length === 2) {
                    results.push([parts[0], parts[1]]);
                  }
                }

                const terms = block.querySelectorAll("dt");
                const descriptions = block.querySelectorAll("dd");
                if (terms.length && terms.length === descriptions.length) {
                  for (let i = 0; i < terms.length; i += 1) {
                    results.push([
                      (terms[i].textContent || "").trim(),
                      (descriptions[i].textContent || "").trim(),
                    ]);
                  }
                }
              }

              const fieldNames = Array.from(document.querySelectorAll(".field-name, .attr-name, .prop-name"));
              for (const nameNode of fieldNames) {
                const key = (nameNode.textContent || "").trim();
                if (!key) {
                  continue;
                }

                const container = nameNode.closest("li, div, td, tr") || nameNode.parentElement;
                if (!container) {
                  continue;
                }

                const valueNode = container.querySelector(".field-value, .attr-value, .prop-value");
                const value = valueNode ? (valueNode.textContent || "").trim() : "";
                if (value) {
                  results.push([key, value]);
                }
              }

              const fieldValues = Array.from(document.querySelectorAll(".field-value"));
              for (const valueNode of fieldValues) {
                const container = valueNode.closest("li, div, td, tr") || valueNode.parentElement;
                if (!container) {
                  continue;
                }

                let keyNode = container.querySelector(".field-name, .attr-name, .prop-name");
                if (!keyNode) {
                  const siblingCandidates = [
                    valueNode.previousElementSibling,
                    container.previousElementSibling,
                    container.parentElement ? container.parentElement.previousElementSibling : null,
                  ];
                  for (const candidate of siblingCandidates) {
                    if (!candidate) {
                      continue;
                    }
                    if (candidate.matches && candidate.matches(".field-name, .attr-name, .prop-name")) {
                      keyNode = candidate;
                      break;
                    }
                    const nestedKey = candidate.querySelector ? candidate.querySelector(".field-name, .attr-name, .prop-name") : null;
                    if (nestedKey) {
                      keyNode = nestedKey;
                      break;
                    }
                  }
                }
                const key = keyNode ? (keyNode.textContent || "").trim() : "";
                const value = (valueNode.textContent || "").trim();
                if (key && value) {
                  results.push([key, value]);
                }
              }

              return results;
            }
            """
        )

        if isinstance(pairs, list):
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2:
                    continue
                key = clean_text(pair[0])
                value = clean_text(pair[1])
                if _is_valid_attribute_pair(key, value):
                    attributes[key] = value
    except Exception:
        return {}

    return attributes


def extract_sales(page, init_data: dict[str, Any] | None = None) -> str:
    """Extract sales text."""
    try:
        if init_data:
            for path in (
                ("sales",),
                ("tradeModel", "saleCount"),
                ("data", "sales"),
                ("saleCount",),
            ):
                value = _safe_get(init_data, *path)
                if value:
                    return clean_text(str(value))
    except Exception:
        pass

    try:
        text = page.evaluate(
            """
            () => {
              const selectors = [".sale-count", ".sales", "[class*='sale']", "[class*='deal']"];
              for (const selector of selectors) {
                const nodes = document.querySelectorAll(selector);
                for (const node of nodes) {
                  const text = (node.textContent || "").trim();
                  if (text) return text;
                }
              }
              return "";
            }
            """
        )
        return clean_text(text)
    except Exception:
        return ""


def extract_supplier(page, init_data: dict[str, Any] | None = None) -> str:
    """Extract supplier name."""
    try:
        text = page.evaluate(
            """
            () => {
              const preferred = document.querySelector("h1[title]");
              if (preferred) {
                const explicitTitle = (preferred.getAttribute("title") || "").trim();
                if (explicitTitle) return explicitTitle;
                const fallbackText = (preferred.innerText || preferred.textContent || "").trim();
                if (fallbackText) return fallbackText;
              }
              return "";
            }
            """
        )
        cleaned = clean_text(text)
        if cleaned:
            return cleaned
    except Exception:
        pass

    try:
        if init_data:
            for path in (
                ("supplier", "name"),
                ("companyName",),
                ("seller", "companyName"),
                ("storeInfo", "storeName"),
                ("company", "name"),
            ):
                value = _safe_get(init_data, *path)
                if value:
                    return clean_text(str(value))
    except Exception:
        pass

    try:
        text = page.evaluate(
            """
            () => {
              const selectors = [
                ".company-name",
                ".supplier-name",
                ".shop-name",
                "[class*='company']",
                "[class*='supplier']"
              ];
              for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element && element.textContent) return element.textContent;
              }
              return "";
            }
            """
        )
        return clean_text(text)
    except Exception:
        return ""


def extract_sku(page, init_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract SKU-related data from JS or HTML."""
    payload: dict[str, Any] = {}

    try:
        if init_data:
            for key in ("sku", "skuModel", "skuCore", "productSKU"):
                value = _safe_get(init_data, key)
                if value in (None, "", [], {}, ()):
                    value = _find_first_nested_key(init_data, key)
                if isinstance(value, dict) and value:
                    payload[key] = value
    except Exception:
        pass

    try:
        option_labels = page.evaluate(
            """
            () => {
              const results = [];
              const seen = new Set();
              const nodes = document.querySelectorAll(".label-name, [class*='sku'] .label-name, [data-spm-anchor-id*='skuSelection'] .label-name");

              for (const node of nodes) {
                const text = (node.textContent || "").trim();
                if (!text || seen.has(text)) {
                  continue;
                }
                seen.add(text);
                results.push(text);
              }

              return results;
            }
            """
        )
        sku_text = page.evaluate(
            """
            () => {
              const selectors = [".sku", ".sku-list", "[class*='sku']"];
              for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element && element.textContent) return element.textContent;
              }
              return "";
            }
            """
        )
        cleaned = clean_text(sku_text)
        if isinstance(option_labels, list):
            cleaned_labels = [clean_text(str(item)) for item in option_labels if clean_text(str(item))]
            if cleaned_labels:
                payload["option_labels"] = cleaned_labels
        if cleaned:
            payload["raw_text"] = cleaned
        if "skuImageList" not in payload:
            dom_image_list = [
                {
                    "value": clean_text(str(item.get("value", ""))),
                    "skuImageUrl": _normalize_image_url(str(item.get("skuImageUrl", ""))),
                }
                for item in _extract_sku_image_list_from_dom(page)
                if isinstance(item, dict)
            ]
            dom_image_list = [item for item in dom_image_list if item["value"] and _looks_like_product_image(item["skuImageUrl"])]
            if dom_image_list:
                payload["skuImageList"] = dom_image_list
        return payload
    except Exception:
        return payload


def open_1688_product_page(page, url: str) -> None:
    """Open a 1688 product page and wait for visible product content."""
    wait_strategies = ("domcontentloaded", "load", "commit")
    last_error: Exception | None = None

    for attempt, wait_until in enumerate(wait_strategies, start=1):
        try:
            LOGGER.info(
                "Opening product page (attempt %s/%s, wait_until=%s): %s",
                attempt,
                len(wait_strategies),
                wait_until,
                url,
            )
            page.goto(url, wait_until=wait_until, timeout=PRODUCT_PAGE_TIMEOUT)
            if is_verification_page(page):
                wait_for_manual_verification(page, reason=f"opening product page {url}")
            break
        except PlaywrightTimeoutError as exc:
            last_error = exc
            LOGGER.warning(
                "Product page load timed out on attempt %s/%s: %s",
                attempt,
                len(wait_strategies),
                url,
            )
    else:
        raise RuntimeError(
            f"Khong mo duoc trang san pham sau {len(wait_strategies)} lan thu: {url}"
        ) from last_error

    try:
        page.wait_for_load_state("domcontentloaded", timeout=DEFAULT_TIMEOUT)
    except PlaywrightTimeoutError:
        LOGGER.debug("domcontentloaded state did not complete within default timeout for %s", url)

    if is_verification_page(page):
        wait_for_manual_verification(page, reason=f"waiting product content for {url}")

    for selector in PRODUCT_READY_SELECTORS:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=4000)
            LOGGER.info("Product content became visible with selector '%s'", selector)
            break
        except PlaywrightTimeoutError:
            continue
    else:
        LOGGER.warning("No product content selector became visible in time for %s", url)

    page.wait_for_timeout(PRODUCT_PAGE_STABILIZE_MS)


def open_etsy_product_page(page, url: str) -> None:
    """Open an Etsy product page and wait for the buy box to stabilize."""
    wait_strategies = ("domcontentloaded", "load", "commit")
    last_error: Exception | None = None

    for attempt, wait_until in enumerate(wait_strategies, start=1):
        try:
            LOGGER.info(
                "Opening Etsy product page (attempt %s/%s, wait_until=%s): %s",
                attempt,
                len(wait_strategies),
                wait_until,
                url,
            )
            page.goto(url, wait_until=wait_until, timeout=PRODUCT_PAGE_TIMEOUT)
            break
        except PlaywrightTimeoutError as exc:
            last_error = exc
            LOGGER.warning(
                "Etsy product page load timed out on attempt %s/%s: %s",
                attempt,
                len(wait_strategies),
                url,
            )
    else:
        raise RuntimeError(
            f"Khong mo duoc trang san pham Etsy sau {len(wait_strategies)} lan thu: {url}"
        ) from last_error

    try:
        page.wait_for_load_state("domcontentloaded", timeout=DEFAULT_TIMEOUT)
    except PlaywrightTimeoutError:
        LOGGER.debug("Etsy domcontentloaded state did not complete within default timeout for %s", url)

    for selector in (
        "h1",
        "[data-buy-box-listing-title='true']",
        "[data-selector='listing-page-image-carousel']",
        "meta[property='og:title']",
    ):
        try:
            page.locator(selector).first.wait_for(state="attached", timeout=4000)
            break
        except PlaywrightTimeoutError:
            continue

    page.wait_for_timeout(2500)


def extract_etsy_title(page, product_data: dict[str, Any] | None = None) -> str:
    """Extract Etsy listing title from DOM or structured data."""
    if isinstance(product_data, dict):
        for key in ("name", "title"):
            value = product_data.get(key)
            if isinstance(value, str) and clean_text(value):
                return clean_text(value)

    try:
        title = page.evaluate(
            """
            () => {
              const selectors = [
                "[data-buy-box-listing-title='true']",
                "h1[data-listing-title]",
                "h1",
                "meta[property='og:title']",
              ];
              for (const selector of selectors) {
                const node = document.querySelector(selector);
                if (!node) continue;
                const value =
                  node.getAttribute?.("content") ||
                  node.innerText ||
                  node.textContent ||
                  "";
                if (value && value.trim()) return value.trim();
              }
              return document.title || "";
            }
            """
        )
        return clean_text(title)
    except Exception:
        return ""


def extract_etsy_price(page, product_data: dict[str, Any] | None = None) -> str:
    """Extract Etsy listing price from structured data or the buy box."""
    offers = product_data.get("offers") if isinstance(product_data, dict) else None
    if isinstance(offers, dict):
        value = offers.get("price")
        if value not in (None, ""):
            return clean_text(str(value))
    if isinstance(offers, list):
        for offer in offers:
            if isinstance(offer, dict) and offer.get("price") not in (None, ""):
                return clean_text(str(offer.get("price")))

    try:
        price = page.evaluate(
            """
            () => {
              const selectors = [
                "[data-buy-box-region='price'] p",
                "[data-buy-box-region='price']",
                "[data-selector='price-only']",
                "[data-selector='listing-page-price']",
                "p[class*='wt-text-title']",
                "meta[property='product:price:amount']",
              ];
              for (const selector of selectors) {
                const node = document.querySelector(selector);
                if (!node) continue;
                const value =
                  node.getAttribute?.("content") ||
                  node.innerText ||
                  node.textContent ||
                  "";
                if (value && value.trim()) return value.trim();
              }
              return "";
            }
            """
        )
        return clean_text(price)
    except Exception:
        return ""


def extract_etsy_images(page, product_data: dict[str, Any] | None = None) -> list[str]:
    """Extract Etsy product images from structured data and DOM."""
    images: list[str] = []
    seen: set[str] = set()

    def add_image(candidate: Any) -> None:
        if not isinstance(candidate, str):
            return
        normalized = _normalize_image_url(candidate)
        if not _looks_like_etsy_product_image(normalized):
            return
        if normalized in seen:
            return
        seen.add(normalized)
        images.append(normalized)

    if isinstance(product_data, dict):
        image_value = product_data.get("image")
        if isinstance(image_value, list):
            for item in image_value:
                add_image(item)
        else:
            add_image(image_value)

    try:
        image_candidates = page.evaluate(
            """
            () => {
              const values = [];
              const push = (value) => {
                if (value) values.push(value);
              };

              const ogImage = document.querySelector("meta[property='og:image']");
              if (ogImage) {
                push(ogImage.getAttribute("content") || "");
              }

              const selectors = [
                "[data-selector='listing-page-image-carousel'] img",
                "[data-carousel-panel] img",
                "ul img[src*='etsystatic.com']",
                "img[src*='etsystatic.com']",
              ];

              for (const selector of selectors) {
                for (const node of document.querySelectorAll(selector)) {
                  push(
                    node.currentSrc ||
                    node.getAttribute("src") ||
                    node.getAttribute("data-src") ||
                    ""
                  );
                }
              }

              return values;
            }
            """
        )
        for item in image_candidates or []:
            add_image(item)
    except Exception:
        pass

    return images


def extract_etsy_attributes(page, product_data: dict[str, Any] | None = None) -> dict[str, str]:
    """Extract Etsy item details into the same raw attributes shape used by normalizers."""
    attributes: dict[str, str] = {}

    if isinstance(product_data, dict):
        brand = _safe_get(product_data, "brand", "name")
        if isinstance(brand, str) and clean_text(brand):
            attributes["brand"] = clean_text(brand)
        elif isinstance(product_data.get("brand"), str) and clean_text(str(product_data.get("brand"))):
            attributes["brand"] = clean_text(str(product_data.get("brand")))

        color = product_data.get("color")
        if isinstance(color, str) and clean_text(color):
            attributes["color"] = clean_text(color)

        material = product_data.get("material")
        if isinstance(material, list):
            values = [clean_text(str(item)) for item in material if clean_text(str(item))]
            if values:
                attributes["material"] = ", ".join(values)
        elif isinstance(material, str) and clean_text(material):
            attributes["material"] = clean_text(material)

        size = product_data.get("size")
        if isinstance(size, str) and clean_text(size):
            attributes["size"] = clean_text(size)

    try:
        pairs = page.evaluate(
            """
            () => {
              const results = [];
              const push = (key, value) => {
                const cleanKey = (key || "").trim();
                const cleanValue = (value || "").trim();
                if (cleanKey && cleanValue) {
                  results.push([cleanKey, cleanValue]);
                }
              };

              for (const row of document.querySelectorAll("dl div, dl")) {
                const terms = row.querySelectorAll("dt");
                const descriptions = row.querySelectorAll("dd");
                if (terms.length && terms.length === descriptions.length) {
                  for (let i = 0; i < terms.length; i += 1) {
                    push(terms[i].textContent, descriptions[i].textContent);
                  }
                }
              }

              for (const item of document.querySelectorAll("li, p")) {
                const text = (item.textContent || "").trim();
                const parts = text.split(/[:：]/).map((part) => part.trim()).filter(Boolean);
                if (parts.length === 2) {
                  push(parts[0], parts[1]);
                }
              }

              for (const select of document.querySelectorAll("select")) {
                const id = select.getAttribute("id") || "";
                let label = select.getAttribute("aria-label") || "";
                if (!label && id) {
                  const labelNode = document.querySelector(`label[for="${id}"]`);
                  label = labelNode ? (labelNode.textContent || "") : "";
                }
                if (!label) continue;

                const values = [];
                for (const option of select.querySelectorAll("option")) {
                  const optionText = (option.textContent || "").trim();
                  if (!optionText) continue;
                  if (/select|choose|optional/i.test(optionText)) continue;
                  values.push(optionText);
                }
                if (values.length) {
                  push(label, values.join(", "));
                }
              }

              return results;
            }
            """
        )
        for pair in pairs or []:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            key = clean_text(pair[0])
            value = clean_text(pair[1])
            if key and value and key not in attributes:
                attributes[key] = value
    except Exception:
        pass

    return attributes


def extract_etsy_supplier(page, product_data: dict[str, Any] | None = None) -> str:
    """Extract Etsy shop or seller name."""
    if isinstance(product_data, dict):
        for path in (
            ("brand", "name"),
            ("seller", "name"),
            ("manufacturer", "name"),
        ):
            value = _safe_get(product_data, *path)
            if isinstance(value, str) and clean_text(value):
                return clean_text(value)

    try:
        supplier = page.evaluate(
            """
            () => {
              const selectors = [
                "[data-shop-name]",
                "a[href*='/shop/']",
                "[data-selector='shop-name']",
              ];
              for (const selector of selectors) {
                const node = document.querySelector(selector);
                if (!node) continue;
                const value = node.innerText || node.textContent || "";
                if (value && value.trim()) return value.trim();
              }
              return "";
            }
            """
        )
        return clean_text(supplier)
    except Exception:
        return ""


def extract_etsy_sales(page, product_data: dict[str, Any] | None = None) -> str:
    """Extract lightweight social-proof text such as ratings or review counts."""
    if isinstance(product_data, dict):
        rating_count = _safe_get(product_data, "aggregateRating", "ratingCount")
        rating_value = _safe_get(product_data, "aggregateRating", "ratingValue")
        if rating_count not in (None, ""):
            return clean_text(f"rating {rating_value or ''} ({rating_count})")

    try:
        text = page.evaluate(
            """
            () => {
              const selectors = [
                "[data-buy-box-region='review']",
                "[data-review-count]",
                "a[href*='#reviews']",
              ];
              for (const selector of selectors) {
                const node = document.querySelector(selector);
                if (!node) continue;
                const value = node.innerText || node.textContent || "";
                if (value && value.trim()) return value.trim();
              }
              return "";
            }
            """
        )
        return clean_text(text)
    except Exception:
        return ""


def crawl_1688_product(page, url: str) -> dict[str, Any]:
    """Crawl one 1688 product detail page and return raw product data."""
    LOGGER.info("Crawling product: %s", url)
    open_1688_product_page(page, url)

    init_data = _collect_init_data(page)

    product = {
        "url": url,
        "title": "",
        "price": "",
        "images": [],
        "attributes": {},
        "sales": "",
        "supplier": "",
        "sku": {},
        "source": "1688",
    }

    try:
        product["title"] = extract_title(page)
    except Exception:
        product["title"] = ""

    try:
        product["price"] = extract_price(page)
    except Exception:
        product["price"] = ""

    try:
        product["images"] = extract_images(page, init_data=init_data)
    except Exception:
        product["images"] = []

    try:
        product["attributes"] = extract_attributes(page)
    except Exception:
        product["attributes"] = {}

    try:
        product["sales"] = extract_sales(page, init_data=init_data)
    except Exception:
        product["sales"] = ""

    try:
        product["supplier"] = extract_supplier(page, init_data=init_data)
    except Exception:
        product["supplier"] = ""

    try:
        product["sku"] = extract_sku(page, init_data=init_data)
    except Exception:
        product["sku"] = {}

    LOGGER.info(
        "Product crawled: title='%s', images=%s, attributes=%s",
        product["title"],
        len(product["images"]),
        len(product["attributes"]),
    )
    return product


def crawl_etsy_product(page, url: str) -> dict[str, Any]:
    """Crawl one Etsy listing page and return raw product data."""
    LOGGER.info("Crawling Etsy product: %s", url)
    open_etsy_product_page(page, url)

    json_ld_objects = _collect_json_ld_objects(page)
    product_data = _find_first_json_ld_product(json_ld_objects)

    product = {
        "url": normalize_product_url(url),
        "title": extract_etsy_title(page, product_data=product_data),
        "price": extract_etsy_price(page, product_data=product_data),
        "images": extract_etsy_images(page, product_data=product_data),
        "attributes": extract_etsy_attributes(page, product_data=product_data),
        "sales": extract_etsy_sales(page, product_data=product_data),
        "supplier": extract_etsy_supplier(page, product_data=product_data),
        "sku": {},
        "source": "etsy",
    }

    LOGGER.info(
        "Etsy product crawled: title='%s', images=%s, attributes=%s",
        product["title"],
        len(product["images"]),
        len(product["attributes"]),
    )
    return product


def open_product_page(page, url: str) -> None:
    """Compatibility wrapper that opens a 1688 product page."""
    open_1688_product_page(page, url)


def crawl_product(page, url: str) -> dict[str, Any]:
    """Crawl one 1688 product detail page."""
    return crawl_1688_product(page, url)
