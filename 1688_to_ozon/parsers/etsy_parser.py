from __future__ import annotations

from typing import Any

from .zyte_common import (
    clean_text,
    collect_images,
    extract_description,
    extract_price_bundle,
    get_additional_properties,
    get_breadcrumbs,
    get_brand_name,
    parse_structured_variants,
    unique_keep_order,
)


def _extract_etsy_attributes(product: dict[str, Any]) -> dict[str, Any]:
    attributes = get_additional_properties(product)
    colors: list[str] = []
    sizes: list[str] = []
    for variant in product.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        color = clean_text(variant.get("color"))
        size = clean_text(variant.get("size"))
        if color:
            colors.append(color)
        if size:
            sizes.append(size)
    if clean_text(product.get("color")):
        colors.append(clean_text(product.get("color")))
    if clean_text(product.get("material")):
        attributes["material"] = clean_text(product.get("material"))
    if colors:
        attributes["colors"] = unique_keep_order(colors)
        if "color" not in attributes:
            attributes["color"] = colors[0]
    if sizes:
        attributes["sizes"] = unique_keep_order(sizes)
        if "size" not in attributes:
            attributes["size"] = sizes[0]
    brand = get_brand_name(product)
    if brand:
        attributes["brand"] = brand
    return attributes


def parse_etsy_product(zyte_data: dict[str, Any], url: str) -> dict[str, Any]:
    product = zyte_data.get("product") if isinstance(zyte_data.get("product"), dict) else {}
    breadcrumbs = get_breadcrumbs(product)
    price = extract_price_bundle(product)
    images = collect_images(product)
    attributes = _extract_etsy_attributes(product)
    variants = parse_structured_variants(product)

    return {
        "source": "etsy",
        "status": "ok",
        "product_url": clean_text(product.get("url")) or clean_text(zyte_data.get("url")) or url,
        "canonical_url": clean_text(product.get("canonicalUrl")),
        "title": clean_text(product.get("name")) or clean_text(product.get("title")),
        "product_id": clean_text(product.get("sku") or product.get("productId")),
        "sku": clean_text(product.get("sku") or product.get("productId")),
        "brand": get_brand_name(product),
        "price": price["price"],
        "price_text": price["price_text"],
        "currency": price["currency"],
        "availability": clean_text(product.get("availability")),
        "category_path": breadcrumbs,
        "category": breadcrumbs[-1] if breadcrumbs else "",
        "images": images,
        "main_image": images[0] if images else "",
        "description": extract_description(product, html=str(zyte_data.get("browserHtml") or "")),
        "attributes": {key: value for key, value in attributes.items() if value not in ("", [], {}, None)},
        "variants": variants,
        "raw": {
            "zyte_url": clean_text(zyte_data.get("url")),
            "status_code": zyte_data.get("statusCode"),
        },
    }
