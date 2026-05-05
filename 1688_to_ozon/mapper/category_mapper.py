import re
from typing import Any


CATEGORY_MAP = {
    "laptop": {
        "ozon_category_name": "Laptop",
        "category_id": 999999,
    },
    "hoodie": {
        "ozon_category_name": "Hoodie",
        "category_id": 999998,
    },
    "unknown": {
        "ozon_category_name": "unknown",
        "category_id": None,
    },
}

LAPTOP_KEYWORDS = {
    "laptop",
    "notebook",
    "ultrabook",
    "macbook",
    "thinkpad",
    "ideapad",
    "vivobook",
    "gaming laptop",
}

LAPTOP_SPEC_HINTS = {
    "cpu",
    "processor",
    "ram",
    "storage",
    "screen_size",
    "resolution",
    "gpu",
    "operating system",
    "battery",
}

HOODIE_KEYWORDS = {
    "hoodie",
    "hooded sweatshirt",
    "pullover hoodie",
    "zip hoodie",
    "sweatshirt",
}


def _normalize_text(value: Any) -> str:
    """Convert any value into normalized searchable text."""
    if value is None:
        return ""

    if isinstance(value, dict):
        value = " ".join(
            f"{_normalize_text(key)} {_normalize_text(item)}"
            for key, item in value.items()
        )
    elif isinstance(value, (list, tuple, set)):
        value = " ".join(_normalize_text(item) for item in value)

    text = str(value).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _collect_search_blob(product: dict) -> str:
    """Collect searchable text from title, attributes and specs."""
    title = _normalize_text(product.get("title"))
    attributes = _normalize_text(product.get("attributes"))
    specs = _normalize_text(product.get("specs"))
    return " ".join(part for part in (title, attributes, specs) if part).strip()


def infer_internal_category(product: dict) -> str:
    """Infer internal category from product title, attributes and specs."""
    if not isinstance(product, dict):
        return "unknown"

    search_blob = _collect_search_blob(product)
    specs = product.get("specs") if isinstance(product.get("specs"), dict) else {}
    attributes = product.get("attributes") if isinstance(product.get("attributes"), dict) else {}

    if any(keyword in search_blob for keyword in LAPTOP_KEYWORDS):
        return "laptop"

    combined_keys = {
        _normalize_text(key)
        for key in list(specs.keys()) + list(attributes.keys())
    }
    if any(hint in combined_keys for hint in LAPTOP_SPEC_HINTS):
        return "laptop"

    if any(keyword in search_blob for keyword in HOODIE_KEYWORDS):
        return "hoodie"

    return "unknown"


def map_category_to_ozon(internal_category: str) -> dict:
    """Map internal category to Ozon category information."""
    normalized_category = _normalize_text(internal_category)
    return CATEGORY_MAP.get(normalized_category, CATEGORY_MAP["unknown"])
