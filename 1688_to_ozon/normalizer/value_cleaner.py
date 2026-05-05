"""Helpers for cleaning values during normalization."""

from __future__ import annotations

import re
from typing import Any

from normalizer.clean_text import (
    clean_text,
    extract_numeric_dimension_values,
    normalize_dimension,
    normalize_storage_text,
    normalize_weight,
)


DIMENSION_FIELDS = {"screen_size"}
STORAGE_FIELDS = {"ram", "storage"}


def clean_canonical_value(field_name: str, value: Any) -> str:
    """Normalize raw values into a consistent canonical text format."""
    text = clean_text(str(value or ""))
    if not text:
        return ""

    if field_name in STORAGE_FIELDS:
        return normalize_storage_text(text)
    if field_name == "size":
        if re.search(r"\d+\s*(?:x|\*)\s*\d+", text, flags=re.IGNORECASE):
            numeric_dimensions = extract_numeric_dimension_values(text)
            return numeric_dimensions or text
        size_match = re.search(r"\b(XXXL|XXL|XL|XS|S|M|L)\b", text.upper())
        if size_match:
            return size_match.group(1)
        numeric_dimensions = extract_numeric_dimension_values(text)
        return numeric_dimensions or text
    if field_name == "screen_size":
        numbers = extract_numeric_dimension_values(text)
        return numbers.split()[0] if numbers else ""
    if field_name in DIMENSION_FIELDS:
        return normalize_dimension(text)
    if field_name == "weight":
        return normalize_weight(text)
    return text
