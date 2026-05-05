from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html_lib.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def to_float(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None

    text = re.sub(r"^[^\d-]+", "", text)
    text = text.replace("₫", "").replace("VND", "").replace("$", "").replace("US", "").strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    text = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_url(url: str | None) -> str:
    text = clean_text(url)
    if not text:
        return ""
    if text.startswith("//"):
        text = f"https:{text}"
    return text.split("?")[0]


def unique_keep_order(items: list[Any]) -> list[Any]:
    results: list[Any] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, dict) else str(item)
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results


def get_nested(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def extract_requested_url(url: str | None) -> str:
    text = clean_text(url)
    if not text:
        return ""
    parsed = urlparse(text)
    redirected = parse_qs(parsed.query).get("redirection")
    if redirected:
        return clean_text(unquote(redirected[0]))
    return text


def get_brand_name(product: dict[str, Any]) -> str:
    brand = product.get("brand")
    if isinstance(brand, dict):
        return clean_text(brand.get("name"))
    return clean_text(brand)


def get_breadcrumbs(product: dict[str, Any]) -> list[str]:
    breadcrumbs: list[str] = []
    for item in product.get("breadcrumbs") or []:
        if isinstance(item, dict):
            value = clean_text(item.get("name"))
            if value:
                breadcrumbs.append(value)
    return unique_keep_order(breadcrumbs)


def get_additional_properties(product: dict[str, Any]) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    for item in product.get("additionalProperties") or []:
        if not isinstance(item, dict):
            continue
        key = clean_text(item.get("name"))
        value = clean_text(item.get("value"))
        if key and value:
            attributes[key] = value
    return attributes


def collect_images(product: dict[str, Any]) -> list[str]:
    images: list[str] = []
    main_image = product.get("mainImage")
    if isinstance(main_image, dict):
        main_url = normalize_url(main_image.get("url"))
        if main_url:
            images.append(main_url)
    elif main_image:
        main_url = normalize_url(str(main_image))
        if main_url:
            images.append(main_url)

    for item in product.get("images") or []:
        if isinstance(item, dict):
            url = normalize_url(item.get("url"))
        else:
            url = normalize_url(str(item))
        if url:
            images.append(url)
    return [item for item in unique_keep_order(images) if item]


def extract_description(product: dict[str, Any], html: str = "") -> str:
    for key in ("description", "summary", "text", "shortDescription"):
        value = clean_text(product.get(key))
        if value:
            return value
    match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, flags=re.I)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_price_bundle(product: dict[str, Any]) -> dict[str, Any]:
    raw_price = (
        product.get("price")
        or get_nested(product, "offers", "price")
        or get_nested(product, "offers", "lowPrice")
        or get_nested(product, "aggregateOffer", "lowPrice")
    )
    amount = to_float(raw_price)
    return {
        "price": amount,
        "price_text": clean_text(raw_price) or (str(amount) if amount is not None else ""),
        "currency": clean_text(product.get("currency") or get_nested(product, "offers", "priceCurrency")),
    }


def parse_structured_variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    raw_variants = product.get("variants") or []
    for index, item in enumerate(raw_variants, start=1):
        if not isinstance(item, dict):
            continue
        variant = {
            "sku_code": clean_text(item.get("sku") or item.get("skuCode") or item.get("id")) or f"variant-{index}",
            "color": clean_text(item.get("color")),
            "size": clean_text(item.get("size")),
            "stock": clean_text(item.get("stock") or item.get("availability")),
            "price_text": clean_text(item.get("price") or item.get("salePrice") or item.get("amountWithSymbol")),
            "price": to_float(item.get("price") or item.get("salePrice") or item.get("amountWithSymbol")),
        }
        if any(variant.values()):
            variants.append(variant)
    return unique_keep_order(variants)
