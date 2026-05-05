"""Compatibility helpers for exposing mapped fields as name/value pairs."""

from __future__ import annotations

from typing import Any


def map_attributes_to_ozon(specs: dict[str, Any]) -> list[dict[str, str]]:
    """Convert a flat dict into Ozon-style attribute objects."""
    if not isinstance(specs, dict):
        return []

    mapped_attributes: list[dict[str, str]] = []
    for name, value in specs.items():
        text = str(value or "").strip()
        if not text or name in {"category", "template_name"}:
            continue
        mapped_attributes.append({"name": str(name), "value": text})
    return mapped_attributes
