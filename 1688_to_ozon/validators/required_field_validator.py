"""Validation helpers for template-required canonical fields."""

from __future__ import annotations

from typing import Any


def find_missing_required_fields(product: dict[str, Any], required_fields: list[str]) -> list[str]:
    """Return required canonical fields that are empty."""
    if not isinstance(product, dict):
        return list(required_fields or [])

    missing_fields: list[str] = []
    for field_name in required_fields or []:
        if not str(product.get(field_name) or "").strip():
            missing_fields.append(field_name)
    return missing_fields


def validate_required_fields(product: dict[str, Any], required_fields: list[str]) -> dict[str, Any]:
    """Return a simple validation payload for downstream mapping/export."""
    missing_fields = find_missing_required_fields(product, required_fields)
    return {
        "is_valid": not missing_fields,
        "missing_fields": missing_fields,
    }
