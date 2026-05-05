"""Shared text normalization helpers for field-level translation."""

from __future__ import annotations

import re


def normalize_spaces(value: str) -> str:
    """Collapse repeated whitespace and trim edges."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_text(value: str) -> str:
    """Basic safe text normalization before field-specific translation."""
    text = normalize_spaces(value)
    return text.strip(" ,:;|-")


def normalize_unit_value(value: str) -> str:
    """Normalize common capacity/unit strings into compact internal form."""
    text = normalize_text(value)
    if not text:
        return ""

    text = re.sub(r"(\d)\s+(GB|TB|KG|G|CM|MM|INCH|IN)\b", r"\1\2", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)\s*[xX]\s*(\d)", r"\1 x \2", text)
    return text
