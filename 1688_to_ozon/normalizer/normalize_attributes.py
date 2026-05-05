"""Compatibility layer around the new canonical product normalizer."""

from __future__ import annotations

from typing import Any

from classifier.template_detector import detect_template
from models.normalized_product import NormalizedProduct
from normalizer.clean_text import clean_text
from normalizer.product_normalizer import (
    normalize_attribute_key,
    normalize_product as normalize_canonical_product,
)


def extract_brand(attributes: dict) -> str:
    """Extract brand from raw attributes using canonical aliases."""
    if not isinstance(attributes, dict):
        return ""

    for raw_key, raw_value in attributes.items():
        if normalize_attribute_key(str(raw_key)) == "brand":
            return clean_text(str(raw_value))
    return ""


def extract_model(attributes: dict) -> str:
    """Extract model from raw attributes using canonical aliases."""
    if not isinstance(attributes, dict):
        return ""

    for raw_key, raw_value in attributes.items():
        if normalize_attribute_key(str(raw_key)) == "model":
            return clean_text(str(raw_value))
    return ""


def _extract_attributes_input(data: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    """Accept either a raw product dict or an attributes-only dict."""
    if not isinstance(data, dict):
        return {}, {}

    if "attributes" in data and isinstance(data.get("attributes"), dict):
        return dict(data.get("attributes") or {}), data
    return dict(data), {}


def normalize_attributes(attributes: dict) -> dict:
    """Return canonical fields plus the legacy `specs` payload."""
    raw_attributes, raw_product = _extract_attributes_input(attributes)
    canonical_source = raw_product if raw_product else {"attributes": raw_attributes}
    normalized = NormalizedProduct.from_dict(normalize_canonical_product(canonical_source))

    if not normalized.category:
        normalized.category = detect_template(normalized.to_dict())

    payload = normalized.to_dict()
    payload["supplier"] = clean_text(str((raw_product or {}).get("supplier", payload.get("supplier", ""))))
    payload["raw_attributes"] = raw_attributes
    return payload


def normalize_product(data: dict) -> dict:
    """Compatibility wrapper for pipeline usage with a raw product dict."""
    normalized = normalize_attributes(data)
    if not isinstance(data, dict):
        return normalized

    normalized.update(
        {
            "source": clean_text(str(data.get("source") or "")),
            "source_url": clean_text(str(data.get("source_url") or data.get("url") or "")),
            "product_url": clean_text(str(data.get("product_url") or data.get("source_url") or data.get("url") or "")),
            "title": clean_text(str(data.get("title", ""))),
            "product_name": clean_text(str(data.get("title") or normalized.get("product_name", ""))),
            "price": clean_text(str(data.get("price", ""))),
            "description": clean_text(str(data.get("description", ""))),
            "images": list(data.get("images", []) or []),
            "variants": list(data.get("variants", []) or []),
            "options": list(data.get("options", []) or []),
            "sku": dict(data.get("sku", {}) or {}),
            "shop_name": clean_text(str(data.get("shop_name") or data.get("supplier") or "")),
        }
    )
    return normalized
