"""Detect which Ozon template should be used for a canonical product."""

from __future__ import annotations

from typing import Any


def _has_any_value(product: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return any(str(product.get(field) or "").strip() for field in fields)


def _looks_like_hoodie(product: dict[str, Any]) -> bool:
    blob = " ".join(
        str(part or "")
        for part in (
            product.get("title"),
            product.get("product_name"),
            product.get("model"),
            product.get("style"),
            product.get("model_features"),
            product.get("lining_material"),
            product.get("raw_attributes"),
        )
    ).lower()
    return any(
        token in blob
        for token in (
            "hoodie",
            "hooded",
            "hooded sweatshirt",
            "pullover hoodie",
            "zip hoodie",
            "hood",
            "áo hoodie",
            "áo nỉ có mũ",
            "áo khoác nỉ có mũ",
            "liền mũ",
            "có mũ liền",
            "mũ trùm",
            "có mũ trùm",
            "hood zip",
        )
    )


def detect_template(product: dict[str, Any]) -> str:
    """Choose the most suitable template from canonical product data."""
    if not isinstance(product, dict):
        return "generic"

    if _looks_like_hoodie(product):
        return "hoodie"

    if _has_any_value(product, ("ram", "storage", "cpu", "screen_size")):
        return "laptop"

    if _has_any_value(product, ("size", "material")):
        if _looks_like_hoodie(product):
            return "hoodie"
        color = str(product.get("color") or "").strip()
        return "shoes" if size_like_shoes(product.get("size")) and color else "clothing"

    return "generic"


def size_like_shoes(value: Any) -> bool:
    """Small heuristic for numeric shoe sizes."""
    text = str(value or "").strip()
    if not text:
        return False
    return text.replace(".", "", 1).isdigit()
