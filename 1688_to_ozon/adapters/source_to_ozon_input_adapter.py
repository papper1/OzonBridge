from __future__ import annotations

import re
from typing import Any

SIZE_TOKENS = (
    "XXS",
    "XS",
    "S",
    "M",
    "L",
    "XL",
    "XXL",
    "2XL",
    "XXXL",
    "3XL",
    "XXXXL",
    "4XL",
    "5XL",
    "ONE SIZE",
    "ONESIZE",
)

COLOR_ALIASES = {
    "WHITE": "White",
    "BLACK": "Black",
    "GREY": "Grey",
    "GRAY": "Grey",
    "RED": "Red",
    "BURGUNDY": "Burgundy",
    "NAVY": "Navy Blue",
    "NAVY BLUE": "Navy Blue",
    "BLUE": "Blue",
    "BRIGHT BLUE": "Blue",
    "BABY BLUE": "Baby Blue",
    "GREEN": "Green",
    "PINK": "Pink",
    "BABY PINK": "Baby Pink",
    "PURPLE": "Purple",
    "STONE": "Stone",
    "BROWN": "Brown",
    "MOCHA": "Mocha Brown",
    "MOCHA BROWN": "Mocha Brown",
    "KHAKI": "Khaki",
    "BEIGE": "Beige",
    "ORANGE": "Orange",
    "YELLOW": "Yellow",
    "SILVER": "Silver",
    "GOLD": "Gold",
}


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _strip_price_noise(value: Any) -> str:
    text = _to_text(value)
    if not text:
        return ""
    text = re.sub(r"\(\s*[$€£₫]?\s*\d+(?:\.\d+)?\s*\)", "", text)
    text = re.sub(r"[$€£₫]\s*\d+(?:\.\d+)?", "", text)
    return re.sub(r"\s+", " ", text).strip(" -_/|,")


def _extract_size_token(text: str) -> str:
    normalized = _strip_price_noise(text).upper()
    for token in sorted(SIZE_TOKENS, key=len, reverse=True):
        pattern = rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])"
        if re.search(pattern, normalized):
            return token
    return ""


def _extract_color_token(text: str) -> tuple[str, str]:
    normalized = _strip_price_noise(text).upper()
    normalized = re.sub(r"\bHOODIE\b", "", normalized)
    normalized = re.sub(r"\bSWEATSHIRT\b", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for alias in sorted(COLOR_ALIASES, key=len, reverse=True):
        pattern = rf"(?<![A-Z]){re.escape(alias)}(?![A-Z])"
        if re.search(pattern, normalized):
            return COLOR_ALIASES[alias], alias.title()
    return "", ""


def _normalize_variant_fields(variant: dict[str, Any]) -> dict[str, str]:
    size = _to_text(variant.get("size"))
    color = _to_text(variant.get("color"))
    color_name = _to_text(variant.get("color_name") or variant.get("color"))

    combined_candidates = [
        size,
        color,
        color_name,
        _to_text(variant.get("name")),
        _to_text(variant.get("label")),
        _to_text(variant.get("value")),
    ]

    extracted_size = "" if _extract_size_token(size) and _extract_color_token(size)[0] else size
    extracted_color = "" if _extract_size_token(color) and _extract_color_token(color)[0] else color
    extracted_color_name = "" if _extract_size_token(color_name) and _extract_color_token(color_name)[0] else color_name

    for candidate in combined_candidates:
        if not extracted_size:
            extracted_size = _extract_size_token(candidate)
        if not extracted_color:
            extracted_color, detected_color_name = _extract_color_token(candidate)
            if detected_color_name and not extracted_color_name:
                extracted_color_name = detected_color_name
        elif not extracted_color_name:
            _, detected_color_name = _extract_color_token(candidate)
            if detected_color_name:
                extracted_color_name = detected_color_name

    return {
        "size": extracted_size,
        "color": extracted_color,
        "color_name": extracted_color_name or extracted_color,
    }


def _build_attributes(product: dict[str, Any]) -> dict[str, Any]:
    attributes = dict(product.get("attributes") or {})
    field_map = {
        "brand": product.get("brand"),
        "model": product.get("product_id") or product.get("sku"),
        "color": attributes.get("color") or product.get("color"),
        "size": attributes.get("size"),
        "material": attributes.get("material"),
        "weight": attributes.get("weight"),
        "season": attributes.get("season"),
        "style": attributes.get("style"),
        "purpose": attributes.get("purpose"),
        "fastener_type": attributes.get("fastener_type"),
        "drawing": attributes.get("drawing"),
        "decorative_elements": attributes.get("decorative_elements"),
        "sleeve_type": attributes.get("sleeve_type"),
        "collar": attributes.get("collar"),
        "lining_material": attributes.get("lining_material"),
        "height_type": attributes.get("height_type"),
        "cut": attributes.get("cut"),
        "composition": attributes.get("composition"),
        "care": attributes.get("care"),
    }
    for key, value in field_map.items():
        if value not in ("", [], {}, None):
            attributes[key] = value

    colors = attributes.get("colors")
    if isinstance(colors, list) and colors and "color" not in attributes:
        attributes["color"] = _to_text(colors[0])
    sizes = attributes.get("sizes")
    if isinstance(sizes, list) and sizes and "size" not in attributes:
        attributes["size"] = _to_text(sizes[0])
    return attributes


def _normalize_variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for index, variant in enumerate(product.get("variants") or [], start=1):
        if not isinstance(variant, dict):
            continue
        normalized_fields = _normalize_variant_fields(variant)
        variants.append(
            {
                "sku": _to_text(variant.get("sku") or variant.get("sku_code") or variant.get("id") or f"variant-{index}"),
                "color": normalized_fields["color"],
                "color_name": normalized_fields["color_name"],
                "size": normalized_fields["size"],
                "ram": _to_text(variant.get("ram")),
                "storage": _to_text(variant.get("storage")),
                "price": _to_text(variant.get("price_text") or variant.get("price") or product.get("price_text") or product.get("price")),
                "stock": _to_text(variant.get("stock")),
                "image_url": _to_text(variant.get("image_url")),
            }
        )
    return variants


def convert_source_product_to_existing_ozon_input(product: dict[str, Any], source: str) -> dict[str, Any]:
    normalized_source = _to_text(source).lower()
    attributes = _build_attributes(product)
    variants = _normalize_variants(product)
    if variants:
        if not attributes.get("color"):
            attributes["color"] = _to_text(next((item.get("color") for item in variants if _to_text(item.get("color"))), ""))
        if not attributes.get("size"):
            attributes["size"] = _to_text(next((item.get("size") for item in variants if _to_text(item.get("size"))), ""))
    supplier = _to_text(product.get("brand") or attributes.get("brand") or product.get("seller"))
    raw_payload = {
        "source": normalized_source,
        "url": _to_text(product.get("product_url") or product.get("canonical_url")),
        "source_url": _to_text(product.get("product_url") or product.get("canonical_url")),
        "product_url": _to_text(product.get("product_url") or product.get("canonical_url")),
        "title": _to_text(product.get("title") or product.get("name")),
        "price": _to_text(product.get("price_text") or product.get("price")),
        "images": list(product.get("images", []) or []),
        "description": _to_text(product.get("description")),
        "attributes": attributes,
        "sales": _to_text(product.get("sales")),
        "supplier": supplier,
        "shop_name": supplier,
        "variants": variants,
        "options": list(product.get("options", []) or []),
        "sku": {
            "raw_text": _to_text(product.get("sku")),
            "product_id": _to_text(product.get("product_id")),
            "source": normalized_source,
            "availability": _to_text(product.get("availability")),
            "currency": _to_text(product.get("currency")),
            "category": _to_text(product.get("category")),
            "category_path": list(product.get("category_path", []) or []),
            "main_image": _to_text(product.get("main_image")),
            "canonical_url": _to_text(product.get("canonical_url")),
        },
    }
    if product.get("status") == "blocked":
        raw_payload["status"] = "blocked"
        raw_payload["blocked_reason"] = _to_text(product.get("blocked_reason"))
        raw_payload["message"] = _to_text(product.get("message"))
    return raw_payload
