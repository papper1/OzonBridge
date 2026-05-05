"""Normalize template option fields so exports only use allowed values."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from mapper.template_loader import resolve_template_dir
from translator.openai_client import (
    MissingOpenAIAPIKeyError,
    extract_response_text,
    get_openai_client,
)


UNKNOWN_VALUE = "UNKNOWN"
MULTI_VALUE_SEPARATOR = ";"
_SPLIT_PATTERN = re.compile(r"[;,/|+\n]|(?:\s+and\s+)|(?:\s+vÃ \s+)|(?:\s+va\s+)|(?:\s+åŠ\s+)|(?:\s+å’Œ\s+)")
_NON_ALNUM_PATTERN = re.compile(r"[^\w\s%+-]+", flags=re.UNICODE)


def normalize_text(value: Any) -> str:
    """Normalize free-form input for alias matching."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("_", " ")
    text = _NON_ALNUM_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@lru_cache(maxsize=1)
def load_template_mapping() -> dict[str, dict[str, Any]]:
    """Load the editable field mapping config from JSON."""
    mapping_path = resolve_template_dir() / "template_mapping.json"
    with mapping_path.open("r", encoding="utf-8") as file:
        raw_mapping = json.load(file)
    return raw_mapping if isinstance(raw_mapping, dict) else {}


def _normalize_allowed_values(values: list[Any]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _normalize_aliases(aliases: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for alias, mapped in aliases.items():
        normalized_alias = normalize_text(alias)
        normalized_mapped = str(mapped or "").strip()
        if normalized_alias and normalized_mapped:
            normalized[normalized_alias] = normalized_mapped
    return normalized


def _split_multi_value(raw_value: Any) -> list[str]:
    text = str(raw_value or "").strip()
    if not text:
        return []
    return [part.strip() for part in _SPLIT_PATTERN.split(text) if part.strip()]


def _contains_alias_match(normalized_value: str, aliases: dict[str, str], allowed_lookup: dict[str, str]) -> str:
    for alias, mapped in aliases.items():
        if alias and alias in normalized_value and mapped in allowed_lookup.values():
            return mapped
    return ""


def _match_allowed_exact(normalized_value: str, allowed_lookup: dict[str, str]) -> str:
    return allowed_lookup.get(normalized_value, "")


def _rule_match_single(raw_value: Any, allowed: list[str], aliases: dict[str, str]) -> str:
    allowed_lookup = {normalize_text(option): option for option in allowed}
    normalized_value = normalize_text(raw_value)
    if not normalized_value:
        return ""
    return (
        _match_allowed_exact(normalized_value, allowed_lookup)
        or aliases.get(normalized_value, "")
        or _contains_alias_match(normalized_value, aliases, allowed_lookup)
        or _contains_alias_match(normalized_value, allowed_lookup, allowed_lookup)
    )


def _rule_match_multi(raw_value: Any, allowed: list[str], aliases: dict[str, str], max_variants: int) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    candidates = _split_multi_value(raw_value) or [str(raw_value or "")]
    for candidate in candidates:
        matched = _rule_match_single(candidate, allowed, aliases)
        if not matched or matched in seen:
            continue
        seen.add(matched)
        values.append(matched)
        if len(values) >= max_variants:
            break
    return values


def _build_ai_prompt(field_name: str, raw_value: Any, allowed: list[str], field_type: str, max_variants: int) -> str:
    allowed_lines = "\n".join(f"- {value}" for value in allowed)
    return (
        f"Field: {field_name}\n"
        f"Type: {field_type}\n"
        f"Raw value: {raw_value}\n"
        f"Allowed values:\n{allowed_lines}\n"
        f"Max variants: {max_variants}\n\n"
        "Select only from the allowed values above. "
        "Do not invent new text. "
        "For single fields return exactly one allowed value or an empty string. "
        f"For multi fields return up to {max_variants} allowed values separated by ';'."
    )


def _ai_select_allowed_values(
    field_name: str,
    raw_value: Any,
    allowed: list[str],
    field_type: str,
    max_variants: int,
) -> list[str]:
    if not allowed or not str(raw_value or "").strip():
        return []
    try:
        client = get_openai_client()
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You map ecommerce attribute values to a fixed allowed list. "
                                "Return only values from the allowed list, separated by ';' when multiple. "
                                "Return empty text when nothing fits."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": _build_ai_prompt(field_name, raw_value, allowed, field_type, max_variants)}],
                },
            ],
        )
        text = extract_response_text(response)
    except (MissingOpenAIAPIKeyError, RuntimeError, Exception):
        return []

    values = _split_multi_value(text) if field_type == "multi" else [text]
    allowed_lookup = {normalize_text(option): option for option in allowed}
    selected: list[str] = []
    for value in values:
        matched = _match_allowed_exact(normalize_text(value), allowed_lookup)
        if matched and matched not in selected:
            selected.append(matched)
        if len(selected) >= max_variants:
            break
    return selected


def _map_text_field(field_name: str, raw_value: Any, product: dict[str, Any], field_config: dict[str, Any]) -> str:
    text = str(raw_value or "").strip()
    has_default = "default" in field_config
    default_value = str(field_config.get("default") or "") if has_default else UNKNOWN_VALUE
    if field_name == "Material composition":
        material_value = map_field_value("Material", raw_value or product.get("material") or "", product=product)
        if material_value and material_value != UNKNOWN_VALUE:
            return material_value
    if field_config.get("strict"):
        normalized = normalize_text(text)
        has_non_ascii = any(ord(char) > 127 for char in text)
        if not normalized or has_non_ascii:
            return default_value
    return text or default_value


def map_field_value(field_name: str, raw_value: Any, *, product: dict[str, Any] | None = None) -> str:
    """Map one template field to allowed values with AI as a constrained fallback."""
    product = product or {}
    field_config = load_template_mapping().get(field_name)
    if not isinstance(field_config, dict):
        return str(raw_value or "").strip()

    field_type = str(field_config.get("type") or "single").strip().lower()
    allowed = _normalize_allowed_values(list(field_config.get("allowed", []) or []))
    aliases = _normalize_aliases(dict(field_config.get("aliases", {}) or {}))
    default_value = str(field_config.get("default") or "").strip()
    max_variants = max(1, int(field_config.get("max_variants") or 3))

    if field_type == "text":
        return _map_text_field(field_name, raw_value, product, field_config)

    if field_type == "multi":
        matched_values = _rule_match_multi(raw_value, allowed, aliases, max_variants)
        if not matched_values:
            matched_values = _ai_select_allowed_values(field_name, raw_value, allowed, field_type, max_variants)
        if matched_values:
            return MULTI_VALUE_SEPARATOR.join(matched_values[:max_variants])
        return default_value or UNKNOWN_VALUE

    matched_value = _rule_match_single(raw_value, allowed, aliases)
    if not matched_value:
        ai_values = _ai_select_allowed_values(field_name, raw_value, allowed, field_type, 1)
        matched_value = ai_values[0] if ai_values else ""
    return matched_value or default_value or UNKNOWN_VALUE


def is_template_option_field(field_name: str) -> bool:
    """Return whether the output column is handled by the template option mapper."""
    return field_name in load_template_mapping()
