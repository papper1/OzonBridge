"""Map canonical product fields to Ozon Excel columns using template config."""

from __future__ import annotations

from typing import Any

from mapper.template_option_mapper import is_template_option_field, map_field_value
from translator import translate_field


def _resolve_field_config(config: Any) -> tuple[str, str]:
    """Support both legacy string config and extended object config."""
    if isinstance(config, str):
        return config, ""

    if isinstance(config, dict):
        canonical_field = str(config.get("field") or "").strip()
        translate_rule = str(config.get("translate") or "").strip().lower()
        return canonical_field, translate_rule

    return "", ""


def map_fields(product: dict[str, Any], field_map: dict[str, Any]) -> dict[str, Any]:
    """Build one Excel row from a canonical product and config field map."""
    if not isinstance(product, dict):
        return {}

    mapped_row: dict[str, Any] = {}
    for output_column, config in (field_map or {}).items():
        canonical_field, translate_rule = _resolve_field_config(config)
        raw_value = product.get(canonical_field, "") if canonical_field else ""
        if is_template_option_field(str(output_column)):
            final_value = map_field_value(str(output_column), raw_value, product=product)
        elif translate_rule == "title" and product.get("translated_title"):
            final_value = product.get("translated_title", "")
        elif translate_rule == "description" and product.get("translated_description"):
            final_value = product.get("translated_description", "")
        else:
            final_value = translate_field(translate_rule, raw_value) if translate_rule else raw_value
        mapped_row[output_column] = final_value
    return mapped_row
