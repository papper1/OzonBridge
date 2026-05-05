import re
from datetime import datetime
from typing import Any


def safe_get(data: dict, *keys, default=None):
    """Safely read a nested value from dictionaries."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def chunk_list(items: list, size: int) -> list[list]:
    """Split a list into smaller chunks."""
    if size <= 0:
        return [items[:]] if items else []
    return [items[index:index + size] for index in range(0, len(items), size)]


def unique_list(items: list) -> list:
    """Return a list with duplicate items removed while keeping order."""
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def slugify(text: str) -> str:
    """Convert text to a simple slug for filenames or SKU parts."""
    value = str(text or "").strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9-]", "", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-")


def now_str() -> str:
    """Return the current timestamp as a compact string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
