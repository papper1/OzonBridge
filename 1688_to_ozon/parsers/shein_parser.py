from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .zyte_common import (
    clean_text,
    collect_images,
    extract_description,
    extract_price_bundle,
    extract_requested_url,
    get_additional_properties,
    get_breadcrumbs,
    get_brand_name,
    normalize_url,
    parse_structured_variants,
    to_float,
    unique_keep_order,
)

VALID_SIZES = {
    "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL",
    "0XL", "1XL", "2XL", "3XL", "4XL", "5XL",
    "ONE SIZE", "ONESIZE",
}


def is_shein_challenge_response(zyte_data: dict[str, Any]) -> bool:
    url = clean_text(zyte_data.get("url")).lower()
    html = str(zyte_data.get("browserHtml") or "")
    return (
        "risk/challenge" in url
        or "page_risk_crawler_block" in html
        or "captcha_type=" in url
        or "GB_RISK_CHALLEGE_LANG" in html
    )


def _extract_meta_content(html: str, property_name: str) -> str:
    pattern = rf'<meta[^>]+property="{re.escape(property_name)}"[^>]+content="([^"]+)"'
    match = re.search(pattern, html, flags=re.I)
    return clean_text(match.group(1)) if match else ""


def _extract_name_from_html(html: str) -> str:
    title = _extract_meta_content(html, "og:title")
    if not title:
        match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
        title = clean_text(match.group(1)) if match else ""
    return clean_text(title.replace("| SHEIN", ""))


def _extract_images_from_html(html: str) -> list[str]:
    images: list[str] = []
    og_image = normalize_url(_extract_meta_content(html, "og:image"))
    if og_image:
        images.append(og_image)
    pattern = re.compile(
        r'https?:\\?/\\?/img\.ltwebstatic\.com[^"\']+?\.(?:jpg|jpeg|png|webp)',
        flags=re.I,
    )
    for match in pattern.findall(html):
        url = normalize_url(match.replace("\\/", "/"))
        if url:
            images.append(url)
    return unique_keep_order(images)


def _extract_sizes_from_html(soup: BeautifulSoup) -> list[str]:
    size_blocks = soup.select(
        "[class*=product-intro] [class*=size], "
        "[class*=product-intro] [aria-label*=Size], "
        "[class*=product-intro] [aria-label*=Kích]"
    )
    sizes: list[str] = []
    for block in size_blocks:
        for element in block.select("button, span, li, div"):
            text = clean_text(element.get("aria-label") or element.get_text(" ", strip=True))
            if not text or len(text) > 12:
                continue
            normalized = text.upper().replace(" ", "")
            for size in VALID_SIZES:
                if normalized == size.upper().replace(" ", ""):
                    sizes.append(size)
    return unique_keep_order(sizes)


def _extract_sizes_from_embedded_data(html: str) -> list[str]:
    sizes: list[str] = []
    base_sort = re.search(r'"base_size_sort"\s*:\s*\{([^{}]{1,500})\}', html, flags=re.S)
    if base_sort:
        for size in re.findall(r'"([A-Z0-9 ]{1,10})"\s*:\s*\d+', base_sort.group(1)):
            normalized = size.upper().replace(" ", "")
            if any(normalized == valid.upper().replace(" ", "") for valid in VALID_SIZES):
                sizes.append(size.strip())
    return unique_keep_order(sizes)


def _extract_color_from_html(soup: BeautifulSoup) -> str:
    color_blocks = soup.select(
        "[class*=product-intro] [class*=color], "
        "[class*=product-intro] [aria-label*=Color], "
        "[class*=product-intro] [aria-label*=Màu]"
    )
    for block in color_blocks:
        text = clean_text(block.get("aria-label") or block.get_text(" ", strip=True))
        for pattern in (
            r"Màu sắc\s*[:：]\s*([A-Za-zÀ-ỹ0-9\s-]+)",
            r"Màu\s*[:：]\s*([A-Za-zÀ-ỹ0-9\s-]+)",
            r"Color\s*[:：]\s*([A-Za-zÀ-ỹ0-9\s-]+)",
        ):
            match = re.search(pattern, text, flags=re.I)
            if match:
                return clean_text(match.group(1))
    return ""


def _extract_color_from_embedded_data(html: str) -> str:
    match = re.search(
        r'"attr_name_en":"Color".{0,250}?"attr_value":"([^"]+)"',
        html,
        flags=re.I | re.S,
    )
    return clean_text(match.group(1)) if match else ""


def _extract_material_data(html: str, soup: BeautifulSoup) -> dict[str, str]:
    material = ""
    composition = ""
    care = ""

    embedded_match = re.search(
        r'"materialExposed"\s*:\s*\{.*?"materialInfoList"\s*:\s*\[(.*?)\]\s*\}',
        html,
        flags=re.I | re.S,
    )
    if embedded_match:
        for key, value in re.findall(
            r'"attrName":"([^"]+)","attrValue":"([^"]*)"',
            embedded_match.group(1),
            flags=re.S,
        ):
            key_text = clean_text(key).lower()
            value_text = clean_text(value)
            if not value_text:
                continue
            if "%" in value_text and not composition:
                composition = value_text
            elif ("composition" in key_text or "thành phần" in key_text) and not composition:
                composition = value_text
            elif not material:
                material = value_text

    product_area = soup.select_one("[class*=product-intro]") or soup
    all_text = clean_text(product_area.get_text(" ", strip=True))
    if not material:
        match = re.search(
            r"Chất liệu\s*[:：]?\s*([^:：]{2,80}?)(?:Thành phần|Hướng dẫn|Bảo quản|Chi tiết|$)",
            all_text,
            flags=re.I,
        )
        material = clean_text(match.group(1)) if match else ""
    if not composition:
        match = re.search(
            r"Thành phần\s*[:：]?\s*([^:：]{2,100}?)(?:Chất liệu|Hướng dẫn|Bảo quản|Chi tiết|$)",
            all_text,
            flags=re.I,
        )
        composition = clean_text(match.group(1)) if match else ""
    match = re.search(
        r"(?:Hướng dẫn chăm sóc|Bảo quản|Care Instructions)\s*[:：]?\s*([^:：]{4,120}?)(?:Chất liệu|Thành phần|Chi tiết|$)",
        all_text,
        flags=re.I,
    )
    care = clean_text(match.group(1)) if match else ""
    return {
        "material": material,
        "composition": composition,
        "care": care,
    }


def _extract_price_from_html(soup: BeautifulSoup) -> dict[str, Any]:
    price_element = soup.select_one("#productMainPriceId, .productPrice__main, [class*=productPrice__main]")
    if not price_element:
        return {"price": None, "price_text": "", "currency": ""}
    raw = clean_text(price_element.get("aria-label") or price_element.get_text(" ", strip=True))
    raw = clean_text(raw.replace("Giá", ""))
    return {
        "price": to_float(raw),
        "price_text": raw,
        "currency": "VND" if "₫" in raw else "",
    }


def _extract_sku_options_from_html(html: str) -> list[dict[str, Any]]:
    size_names = _extract_sizes_from_embedded_data(html)
    matches = list(
        re.finditer(
            r'"sku_code":"([^"]+)","stock":"([^"]*)".{0,1200}?"salePrice":\{"amount":"[^"]*","amountWithSymbol":"([^"]+)"',
            html,
            flags=re.I | re.S,
        )
    )
    options: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        options.append(
            {
                "sku_code": clean_text(match.group(1)),
                "size": size_names[index] if index < len(size_names) else "",
                "color": "",
                "stock": clean_text(match.group(2)),
                "price_text": clean_text(match.group(3)),
                "price": to_float(match.group(3)),
            }
        )
    return options


def parse_shein_product(zyte_data: dict[str, Any], url: str) -> dict[str, Any]:
    if is_shein_challenge_response(zyte_data):
        blocked_url = clean_text(zyte_data.get("url")) or url
        return {
            "source": "shein",
            "status": "blocked",
            "blocked_reason": "shein_risk_challenge",
            "requested_url": extract_requested_url(blocked_url) or url,
            "blocked_url": blocked_url,
            "message": "Zyte was redirected to a SHEIN challenge or captcha page instead of the real product page.",
        }

    product = zyte_data.get("product") if isinstance(zyte_data.get("product"), dict) else {}
    html = str(zyte_data.get("browserHtml") or "")
    soup = BeautifulSoup(html, "html.parser") if html else BeautifulSoup("", "html.parser")
    html_price = _extract_price_from_html(soup)
    api_price = extract_price_bundle(product)
    price = api_price["price"] if api_price["price"] is not None else html_price["price"]
    price_text = api_price["price_text"] or html_price["price_text"]
    currency = api_price["currency"] or html_price["currency"]
    material_data = _extract_material_data(html, soup)
    breadcrumbs = get_breadcrumbs(product)
    images = collect_images(product) or _extract_images_from_html(html)
    variants = parse_structured_variants(product) or _extract_sku_options_from_html(html)
    additional = get_additional_properties(product)
    color = clean_text(product.get("color")) or _extract_color_from_html(soup) or _extract_color_from_embedded_data(html)
    sizes = [clean_text(item.get("size")) for item in variants if clean_text(item.get("size"))]
    if not sizes:
        sizes = _extract_sizes_from_html(soup) or _extract_sizes_from_embedded_data(html)

    attributes = dict(additional)
    attributes.update(
        {
            "brand": get_brand_name(product),
            "color": color,
            "sizes": unique_keep_order([size for size in sizes if size]),
            "material": material_data["material"],
            "composition": material_data["composition"],
            "care": material_data["care"],
        }
    )

    return {
        "source": "shein",
        "status": "ok",
        "product_url": clean_text(product.get("url")) or clean_text(zyte_data.get("url")) or url,
        "canonical_url": clean_text(product.get("canonicalUrl")),
        "title": clean_text(product.get("name")) or _extract_name_from_html(html),
        "product_id": clean_text(product.get("sku")),
        "sku": clean_text(product.get("sku")) or clean_text((variants or [{}])[0].get("sku_code")),
        "brand": get_brand_name(product),
        "price": price,
        "price_text": price_text,
        "currency": currency,
        "availability": clean_text(product.get("availability")),
        "category_path": breadcrumbs,
        "category": breadcrumbs[-2] if len(breadcrumbs) >= 2 else (breadcrumbs[-1] if breadcrumbs else ""),
        "images": images,
        "main_image": images[0] if images else "",
        "description": extract_description(product, html=html),
        "attributes": {key: value for key, value in attributes.items() if value not in ("", [], {}, None)},
        "variants": variants,
        "raw": {
            "zyte_url": clean_text(zyte_data.get("url")),
            "status_code": zyte_data.get("statusCode"),
        },
    }
