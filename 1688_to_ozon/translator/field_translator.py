"""Field-aware translation rules for preparing Russian Ozon export values."""

from __future__ import annotations

import re
from typing import Callable

from translator.api_client import translate_text as translate_text_via_api
from translator.ru_dictionary import BRAND_MAP, COLOR_MAP, MATERIAL_MAP, UNIT_MAP
from translator.text_formatter import normalize_text, normalize_unit_value


RUSSIAN_SIZE_MAP: dict[str, str] = {
    "XXS": "40",
    "XS": "42",
    "S": "44",
    "M": "46",
    "L": "48",
    "XL": "50",
    "XXL": "52",
    "3XL": "54",
    "XXXL": "54",
    "4XL": "56",
    "XXXXL": "56",
}


def _title_case_word(value: str) -> str:
    text = normalize_text(value)
    return text[:1].upper() + text[1:].lower() if text else ""


def _map_with_fallback(value: str, mapping: dict[str, str], fallback: Callable[[str], str] | None = None) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    mapped = mapping.get(text.lower())
    if mapped:
        return mapped
    if fallback is not None:
        return fallback(text)
    return text


def _translate_units(value: str) -> str:
    text = normalize_unit_value(value)
    if not text:
        return ""

    def replace_unit(match: re.Match[str]) -> str:
        number = match.group(1)
        unit = match.group(2).lower()
        return f"{number} {UNIT_MAP.get(unit, unit)}"

    return re.sub(r"(\d+(?:\.\d+)?)\s*(gb|tb|kg|g|cm|mm|inch|in)\b", replace_unit, text, flags=re.IGNORECASE)


def translate_brand(value: str) -> str:
    """Keep brand names intact, with light normalization for known brands."""
    return _map_with_fallback(value, BRAND_MAP, fallback=_title_case_word)


def translate_color(value: str) -> str:
    """Translate common color values using a fixed dictionary."""
    return _map_with_fallback(value, COLOR_MAP)


def translate_material(value: str) -> str:
    """Translate common materials; keep the original text if unknown."""
    return _map_with_fallback(value, MATERIAL_MAP)


def translate_storage(value: str) -> str:
    """Normalize storage units into Russian abbreviations."""
    return _translate_units(value)


def translate_ram(value: str) -> str:
    """Normalize RAM units into Russian abbreviations."""
    return _translate_units(value)


def translate_weight(value: str) -> str:
    """Normalize weight units into Russian abbreviations."""
    return _translate_units(value)


def translate_size(value: str) -> str:
    """Keep size values stable, only normalize formatting."""
    return normalize_unit_value(value)


def convert_international_size_to_russian(value: object) -> dict[str, str | bool]:
    """Convert international clothing size to Russian size with safe structured output."""
    normalized_input = normalize_unit_value("" if value is None else str(value)).upper()
    normalized_input = {
        "XXXL": "3XL",
        "XXXXL": "4XL",
    }.get(normalized_input, normalized_input)
    russian_size = RUSSIAN_SIZE_MAP.get(normalized_input, "")
    return {
        "input": "" if value is None else str(value),
        "normalized_input": normalized_input,
        "russian_size": russian_size,
        "valid": bool(russian_size),
    }


def translate_title(value: str) -> str:
    """Placeholder for future generic title translation API integration."""
    text = normalize_text(value)
    # TODO: switch the placeholder client in translator.api_client to a real provider.
    return translate_text_via_api(text, field_name="title")


def translate_description(value: str) -> str:
    """Placeholder for future generic description translation API integration."""
    text = normalize_text(value)
    # TODO: switch the placeholder client in translator.api_client to a real provider.
    return translate_text_via_api(text, field_name="description")


FIELD_TRANSLATORS: dict[str, Callable[[str], str]] = {
    "brand": translate_brand,
    "color": translate_color,
    "material": translate_material,
    "storage": translate_storage,
    "ram": translate_ram,
    "weight": translate_weight,
    "size": translate_size,
    "title": translate_title,
    "description": translate_description,
}


def translate_field(field_name: str, value: str) -> str:
    """Translate one field value with the correct field-specific rule."""
    normalized_value = normalize_text(value)
    if not normalized_value:
        return ""

    translator = FIELD_TRANSLATORS.get(str(field_name or "").strip().lower())
    if translator is None:
        return normalized_value
    return translator(normalized_value)
