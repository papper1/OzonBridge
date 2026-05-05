"""AI-based Chinese to Russian translation helpers."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from translator.openai_client import (
    MissingOpenAIAPIKeyError,
    extract_response_text,
    get_openai_client,
    get_openai_model,
)


LOGGER = logging.getLogger("translator.ai_translator")

BASE_TRANSLATION_PROMPT = (
    "You translate 1688 product data from Chinese into Russian for Ozon ecommerce listings. "
    "Write concise, natural Russian for ecommerce. "
    "Preserve brand names, model codes, numbers, sizes, measurements, and units exactly. "
    "Do not add information. Do not guess. "
    "Remove Chinese-style wording and keep only the meaning present in the source. "
    "Return only the translation."
)

TITLE_TRANSLATION_PROMPT = (
    "You translate Chinese product titles into Russian for Ozon. "
    "Make the title clean, concise, and natural for a marketplace listing. "
    "Keep only useful product facts from the source. "
    "Remove spammy filler such as new arrival, trendy, versatile, hot sale, high quality, fashionable, elegant, luxury, and repeated adjectives. "
    "Preserve brand names, model names, article codes, sizes, gender, season, material, dimensions, and units exactly if present. "
    "Do not invent specifications. Do not add brand or features that are not in the source. "
    "Output one clean Russian product title only."
)

DESCRIPTION_TRANSLATION_PROMPT = (
    "You translate Chinese product descriptions into Russian for Ozon. "
    "Write concise, natural ecommerce Russian. "
    "Keep factual details only, without Chinese marketing style. "
    "Do not add information. Return only the translated description."
)

ATTRIBUTE_TRANSLATION_PROMPT = (
    "You translate Chinese product attribute labels and values into Russian for Ozon. "
    "Keep the translation short and factual. "
    "Preserve brands, model codes, numbers, sizes, dimensions, and units exactly. "
    "Return only the translated text."
)


def is_ai_translation_enabled() -> bool:
    """Return whether AI translation is enabled."""
    raw_value = str(os.getenv("ENABLE_AI_TRANSLATION", "1") or "").strip().lower()
    return raw_value not in {"0", "false", "no", "off"}


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _clean_ozon_title(text: str) -> str:
    """Apply light cleanup so titles fit marketplace style better."""
    cleaned = _normalize_whitespace(text)
    cleaned = re.sub(r"\s*[,;|/]+\s*", ", ", cleaned)
    cleaned = re.sub(r"(,\s*){2,}", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ,.-")


def _translate_text_with_openai(text: str, *, system_prompt: str, task_label: str) -> str:
    """Translate a single text string via the OpenAI Responses API."""
    client = get_openai_client()
    response = client.responses.create(
        model=get_openai_model(),
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"{task_label}\n\nSource text:\n{text}",
                    }
                ],
            },
        ],
    )
    translated_text = extract_response_text(response)
    return _normalize_whitespace(translated_text or text)


def translate_text_zh_to_ru(text: str, *, content_type: str = "generic") -> str:
    """Translate Chinese product text into Russian, with safe fallback."""
    normalized_text = _normalize_whitespace(text)
    if not normalized_text:
        return ""
    if not is_ai_translation_enabled():
        return normalized_text

    prompt_map = {
        "title": TITLE_TRANSLATION_PROMPT,
        "description": DESCRIPTION_TRANSLATION_PROMPT,
        "attribute": ATTRIBUTE_TRANSLATION_PROMPT,
        "generic": BASE_TRANSLATION_PROMPT,
    }
    task_map = {
        "title": "Translate this Chinese product title into a clean Russian Ozon title.",
        "description": "Translate this Chinese product description into concise Russian.",
        "attribute": "Translate this Chinese product attribute text into Russian.",
        "generic": "Translate this Chinese product text into Russian.",
    }

    try:
        translated = _translate_text_with_openai(
            normalized_text,
            system_prompt=prompt_map.get(content_type, BASE_TRANSLATION_PROMPT),
            task_label=task_map.get(content_type, task_map["generic"]),
        )
        if content_type == "title":
            return _clean_ozon_title(translated)
        return translated
    except MissingOpenAIAPIKeyError as exc:
        LOGGER.warning("AI translation skipped: %s", exc)
    except Exception as exc:
        LOGGER.warning("AI translation failed, using original text: %s", exc)
    return normalized_text


def _translate_attribute_value(value: Any) -> Any:
    if isinstance(value, str):
        return translate_text_zh_to_ru(value, content_type="attribute")
    if isinstance(value, dict):
        return {
            translate_text_zh_to_ru(str(key), content_type="attribute"): _translate_attribute_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_translate_attribute_value(item) for item in value]
    return value


def _serialize_attributes(attributes: Any) -> dict[str, Any]:
    if not isinstance(attributes, dict):
        return {}
    return {str(key): value for key, value in attributes.items()}


def translate_product_fields(product: dict[str, Any]) -> dict[str, Any]:
    """Translate key product fields and return extra translated fields."""
    product = dict(product or {})
    title = str(product.get("title") or product.get("product_name") or "").strip()
    description = str(product.get("description") or "").strip()
    attributes = _serialize_attributes(
        product.get("attributes")
        or product.get("raw_attributes")
        or {}
    )
    if not is_ai_translation_enabled():
        translated_product = dict(product)
        translated_product.update(
            {
                "translated_title": title,
                "translated_description": description,
                "translated_attributes": attributes,
            }
        )
        return translated_product

    translated_attributes = _translate_attribute_value(attributes) if attributes else {}

    translated_product = dict(product)
    translated_product.update(
        {
            "translated_title": translate_text_zh_to_ru(title, content_type="title") if title else "",
            "translated_description": translate_text_zh_to_ru(description, content_type="description")
            if description
            else "",
            "translated_attributes": translated_attributes,
        }
    )
    return translated_product


def build_translation_preview(product: dict[str, Any]) -> str:
    """Format a small JSON preview for logs/debugging when needed."""
    preview = {
        "translated_title": product.get("translated_title", ""),
        "translated_description": product.get("translated_description", ""),
        "translated_attributes": product.get("translated_attributes", {}),
    }
    return json.dumps(preview, ensure_ascii=False)
