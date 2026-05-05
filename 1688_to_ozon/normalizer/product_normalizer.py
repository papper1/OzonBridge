"""Convert raw 1688 product payloads into a canonical internal product model."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from models.normalized_product import CANONICAL_FIELDS, NormalizedProduct
from normalizer.attribute_aliases import ALIAS_LOOKUP, normalize_alias_key
from normalizer.clean_text import clean_text
from normalizer.value_cleaner import clean_canonical_value


DIRECT_ATTRIBUTE_KEY_MAP: dict[str, str] = {
    "phong cách": "style",
    "kiểu cổ áo": "collar",
    "dài tay áo": "sleeve_type",
    "kiểu tay áo": "sleeve_type",
    "vạt áo": "fastener_type",
    "thích hợp cho mùa": "season",
    "hoa văn": "drawing",
    "chi tiết kiểu dáng": "decorative_elements",
    "kịch bản áp dụng": "purpose",
    "thành phần vải chính": "material",
    "tên vải": "material",
    "chất liệu": "material",
    "màu sắc": "color",
    "kích cỡ": "size",
    "có mũ liền không": "model_features",
    "có lót trong không": "lining_material",
    "dày mỏng": "model_features",
    "kiểu dáng": "cut",
    "phong cách túi quần áo": "decorative_elements",
    "trọng lượng": "weight",
}


def normalize_attribute_key(key: str) -> str:
    """Resolve a raw key to a canonical field when possible."""
    normalized_key = normalize_alias_key(key)
    if normalized_key in CANONICAL_FIELDS:
        return normalized_key
    return DIRECT_ATTRIBUTE_KEY_MAP.get(normalized_key, ALIAS_LOOKUP.get(normalized_key, ""))


def _extract_attributes(raw_product: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_product, dict):
        return {}
    attributes = raw_product.get("attributes")
    return dict(attributes or {}) if isinstance(attributes, dict) else {}


def normalize_product(raw_product: dict[str, Any]) -> dict[str, Any]:
    """Build a canonical product dict from raw 1688 data."""
    raw_product = dict(raw_product or {})
    raw_attributes = _extract_attributes(raw_product)

    normalized = NormalizedProduct(
        source_url=clean_text(raw_product.get("source_url") or raw_product.get("url") or ""),
        product_name=clean_text(raw_product.get("title") or raw_product.get("product_name") or ""),
        title=clean_text(raw_product.get("title") or ""),
        supplier=clean_text(raw_product.get("supplier") or ""),
        images=list(raw_product.get("images", []) or []),
        variants=list(raw_product.get("variants", []) or []),
        raw_attributes=raw_attributes,
    )

    for raw_key, raw_value in raw_attributes.items():
        canonical_key = normalize_attribute_key(str(raw_key))
        if not canonical_key:
            continue

        cleaned_value = clean_canonical_value(canonical_key, raw_value)
        if cleaned_value:
            setattr(normalized, canonical_key, cleaned_value)

    if not normalized.product_name:
        normalized.product_name = clean_text(raw_product.get("title") or "")

    normalized_dict = asdict(normalized)
    sku_data = raw_product.get("sku")
    if isinstance(sku_data, dict) and sku_data:
        normalized_dict["sku"] = dict(sku_data)
    return normalized_dict
