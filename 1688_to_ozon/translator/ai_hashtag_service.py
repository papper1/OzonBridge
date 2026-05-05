"""AI-assisted hashtag generation for crawled products."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from translator.openai_client import (
    MissingOpenAIAPIKeyError,
    extract_response_text,
    get_openai_client,
    get_openai_model,
)


LOGGER = logging.getLogger("translator.ai_hashtag_service")
MIN_HASHTAGS = 8
MAX_HASHTAGS = 15
_WHITESPACE_PATTERN = re.compile(r"\s+")
_NON_TAG_CHAR_PATTERN = re.compile(r"[^a-z0-9#]+")
_HASHTAG_PATTERN = re.compile(r"#?[a-z0-9][a-z0-9_-]*", flags=re.IGNORECASE)
MAX_HASHTAG_LENGTH = 24
_WORD_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "without",
    "new",
    "fashion",
    "high",
    "quality",
    "product",
    "products",
    "clothing",
    "clothes",
    "wear",
    "daily",
    "casual",
}
_CATEGORY_HINTS = (
    "hoodie",
    "sweatshirt",
    "jacket",
    "coat",
    "tshirt",
    "shirt",
    "dress",
    "pants",
    "trousers",
    "jeans",
    "shoes",
    "sneakers",
    "boots",
    "laptop",
)
_STYLE_HINTS = {
    "streetwear": "streetwear",
    "casual": "casualstyle",
    "sport": "sportswear",
    "sports": "sportswear",
    "oversized": "oversized",
    "vintage": "vintagefashion",
    "minimalist": "minimalstyle",
}
_SEASON_HINTS = {
    "summer": "summerwear",
    "winter": "winterwear",
    "autumn": "autumnwear",
    "spring": "springwear",
}
_MATERIAL_HINTS = {
    "cotton": "cotton",
    "polyester": "polyester",
    "fleece": "fleece",
    "wool": "wool",
    "denim": "denim",
}
_AUDIENCE_HINTS = {
    "men": "menswear",
    "male": "menswear",
    "man": "menswear",
    "women": "womenswear",
    "female": "womenswear",
    "woman": "womenswear",
    "unisex": "unisexfashion",
    "kids": "kidsfashion",
    "children": "kidsfashion",
}
_COLOR_HINTS = {
    "black": "black",
    "white": "white",
    "grey": "grey",
    "gray": "grey",
    "blue": "blue",
    "red": "red",
    "green": "green",
    "pink": "pink",
    "brown": "brown",
    "beige": "beige",
}


def _normalize_text(value: Any) -> str:
    return _WHITESPACE_PATTERN.sub(" ", str(value or "")).strip()


def _slugify_hashtag(value: Any) -> str:
    text = _normalize_text(value).lower()
    if not text:
        return ""
    text = text.replace("_", "")
    text = text.replace("-", "")
    text = _NON_TAG_CHAR_PATTERN.sub("", text)
    text = text.lstrip("#")
    if not text or len(text) > MAX_HASHTAG_LENGTH:
        return ""
    return f"#{text}" if text else ""


def _dedupe_hashtags(values: list[Any], *, limit: int = MAX_HASHTAGS) -> list[str]:
    hashtags: list[str] = []
    seen: set[str] = set()
    for value in values:
        hashtag = _slugify_hashtag(value)
        if not hashtag or hashtag in seen:
            continue
        seen.add(hashtag)
        hashtags.append(hashtag)
        if len(hashtags) >= limit:
            break
    return hashtags


def _strip_code_fences(text: str) -> str:
    cleaned = _normalize_text(text)
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _serialize_attributes(attributes: Any) -> dict[str, Any]:
    if not isinstance(attributes, dict):
        return {}
    return {str(key): value for key, value in attributes.items()}


def _build_prompt_payload(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": _normalize_text(product.get("translated_title") or product.get("title") or product.get("product_name")),
        "description": _normalize_text(product.get("translated_description") or product.get("description")),
        "attributes": _serialize_attributes(
            product.get("translated_attributes")
            or product.get("attributes")
            or product.get("raw_attributes")
            or {}
        ),
        "category": _normalize_text(product.get("category")),
        "color": _normalize_text(product.get("color")),
        "material": _normalize_text(product.get("material")),
        "gender": _normalize_text(product.get("gender") or product.get("gender_export")),
        "season": _normalize_text(product.get("season")),
        "style": _normalize_text(product.get("style")),
    }


def _build_ai_prompt(product: dict[str, Any]) -> str:
    payload = json.dumps(_build_prompt_payload(product), ensure_ascii=False)
    return (
        "Generate 8-15 relevant product hashtags for this product. "
        "Return only a JSON array of strings. "
        "Use lowercase hashtags, no duplicates, no explanation. "
        "Prefer product type, audience, style, material, season, and use case. "
        f"Product data: {payload}"
    )


def _extract_attribute_terms(attributes: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key, value in attributes.items():
        key_text = _normalize_text(key)
        value_text = _normalize_text(value)
        if key_text:
            terms.append(key_text)
        if isinstance(value, list):
            terms.extend(_normalize_text(item) for item in value if _normalize_text(item))
            continue
        if isinstance(value, dict):
            terms.extend(_normalize_text(item) for item in value.values() if _normalize_text(item))
            continue
        if value_text:
            terms.append(value_text)
    return terms


def _extract_words(value: Any) -> list[str]:
    text = _normalize_text(value).lower()
    return [word for word in _WORD_PATTERN.findall(text) if word and word not in _STOPWORDS]


def _pick_category(product: dict[str, Any]) -> str:
    for value in (
        product.get("category"),
        product.get("translated_title"),
        product.get("title"),
        product.get("product_name"),
    ):
        words = _extract_words(value)
        for hint in _CATEGORY_HINTS:
            if hint in words:
                return hint
    return _extract_words(product.get("category") or "product")[:1][0] if _extract_words(product.get("category") or "product") else "product"


def _pick_audience(product: dict[str, Any], words: list[str]) -> str:
    for value in (product.get("gender"), product.get("gender_export")):
        value_words = _extract_words(value)
        for word in value_words:
            if word in _AUDIENCE_HINTS:
                return _AUDIENCE_HINTS[word]
    for word in words:
        if word in _AUDIENCE_HINTS:
            return _AUDIENCE_HINTS[word]
    return ""


def _pick_style(words: list[str]) -> str:
    for word in words:
        if word in _STYLE_HINTS:
            return _STYLE_HINTS[word]
    return ""


def _pick_material(product: dict[str, Any], words: list[str]) -> str:
    for value in (product.get("material"),):
        for word in _extract_words(value):
            if word in _MATERIAL_HINTS:
                return _MATERIAL_HINTS[word]
    for word in words:
        if word in _MATERIAL_HINTS:
            return _MATERIAL_HINTS[word]
    return ""


def _pick_season(product: dict[str, Any], words: list[str]) -> str:
    for value in (product.get("season"),):
        for word in _extract_words(value):
            if word in _SEASON_HINTS:
                return _SEASON_HINTS[word]
    for word in words:
        if word in _SEASON_HINTS:
            return _SEASON_HINTS[word]
    return ""


def _pick_color(product: dict[str, Any], words: list[str]) -> str:
    for value in (product.get("color"),):
        for word in _extract_words(value):
            if word in _COLOR_HINTS:
                return _COLOR_HINTS[word]
    for word in words:
        if word in _COLOR_HINTS:
            return _COLOR_HINTS[word]
    return ""


def _build_semantic_fallback_hashtags(product: dict[str, Any]) -> list[str]:
    attributes = _serialize_attributes(
        product.get("translated_attributes")
        or product.get("attributes")
        or product.get("raw_attributes")
        or {}
    )
    source_words: list[str] = []
    for value in (
        product.get("translated_title"),
        product.get("title"),
        product.get("product_name"),
        product.get("translated_description"),
        product.get("description"),
        product.get("style"),
        product.get("season"),
        product.get("material"),
        product.get("gender"),
        product.get("color"),
    ):
        source_words.extend(_extract_words(value))
    for term in _extract_attribute_terms(attributes):
        source_words.extend(_extract_words(term))

    category = _pick_category(product)
    audience = _pick_audience(product, source_words)
    style = _pick_style(source_words)
    material = _pick_material(product, source_words)
    season = _pick_season(product, source_words)
    color = _pick_color(product, source_words)

    candidates: list[str] = []
    candidates.append(category)
    if audience:
        candidates.append(audience)
    if style:
        candidates.append(style)
    if season:
        candidates.append(season)
    if material:
        candidates.append(f"{material}{category}")
    if color:
        candidates.append(f"{color}{category}")
    if audience and category != "product":
        if audience == "menswear":
            candidates.append(f"mens{category}")
        elif audience == "womenswear":
            candidates.append(f"womens{category}")
        elif audience == "kidsfashion":
            candidates.append(f"kids{category}")
    for word in source_words:
        if word in {"oversized", "zipper", "hooded", "hood", "streetwear", "sports", "sport", "fleece", "cotton"}:
            if word == "oversized":
                candidates.append(f"oversized{category}")
            elif word in {"sports", "sport"}:
                candidates.append("sportswear")
            elif word == "hood" and category != "hoodie":
                candidates.append("hoodedstyle")
            elif word == "hooded":
                candidates.append("hoodedstyle")
            else:
                candidates.append(word if word in {"streetwear", "zipper"} else f"{word}{category}" if category != "product" else word)
    if category == "hoodie":
        candidates.extend(["casualwear", "streetwear", "cozywear"])

    return _dedupe_hashtags(candidates, limit=MAX_HASHTAGS)


def _fallback_hashtags(product: dict[str, Any]) -> list[str]:
    hashtags = _build_semantic_fallback_hashtags(product)
    if len(hashtags) >= MIN_HASHTAGS:
        return hashtags

    attributes = _serialize_attributes(
        product.get("translated_attributes")
        or product.get("attributes")
        or product.get("raw_attributes")
        or {}
    )
    seed_terms = [product.get("category"), product.get("color"), product.get("material"), product.get("gender"), product.get("season"), product.get("style")]
    seed_terms.extend(_extract_attribute_terms(attributes))
    hashtags.extend(_dedupe_hashtags(seed_terms, limit=MAX_HASHTAGS))
    return _dedupe_hashtags(hashtags, limit=MAX_HASHTAGS)


def _extract_hashtags_from_text(text: str) -> list[str]:
    matches = _HASHTAG_PATTERN.findall(text or "")
    return _dedupe_hashtags(matches, limit=MAX_HASHTAGS)


def _parse_ai_hashtag_response(text: str) -> list[str]:
    cleaned = _strip_code_fences(text)
    if not cleaned:
        return []

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, list):
        return _dedupe_hashtags(parsed, limit=MAX_HASHTAGS)

    if isinstance(parsed, dict):
        for key in ("hashtags", "tags", "data", "items"):
            value = parsed.get(key)
            if isinstance(value, list):
                return _dedupe_hashtags(value, limit=MAX_HASHTAGS)
            if isinstance(value, str):
                extracted = _extract_hashtags_from_text(value)
                if extracted:
                    return extracted

    extracted = _extract_hashtags_from_text(cleaned)
    if extracted:
        return extracted

    # Last fallback: accept comma/semicolon/newline-separated plain words.
    plain_values = [part.strip() for part in re.split(r"[,\n;|]+", cleaned) if part.strip()]
    return _dedupe_hashtags(plain_values, limit=MAX_HASHTAGS)


def _generate_hashtags_with_ai(product: dict[str, Any]) -> list[str]:
    client = get_openai_client()
    response = client.responses.create(
        model=get_openai_model(),
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You generate ecommerce hashtags for product listings. "
                            "Return only a JSON array of 8 to 15 lowercase hashtag strings. "
                            "No prose. No duplicate hashtags."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": _build_ai_prompt(product)}],
            },
        ],
    )
    text = extract_response_text(response)
    hashtags = _parse_ai_hashtag_response(text)
    if hashtags:
        LOGGER.info("AI hashtag generation succeeded with %s hashtags", len(hashtags))
    else:
        LOGGER.warning("AI hashtag generation returned no usable hashtags. Raw response: %s", text[:300])
    return hashtags


def generate_hashtags(product: dict[str, Any]) -> dict[str, Any]:
    """Return the product payload with a new `hashtags` field."""
    product = dict(product or {})
    hashtags: list[str] = []

    try:
        hashtags = _generate_hashtags_with_ai(product)
        if len(hashtags) < MIN_HASHTAGS:
            raise ValueError("AI returned too few hashtags")
    except MissingOpenAIAPIKeyError as exc:
        LOGGER.warning("AI hashtag generation skipped: %s", exc)
    except Exception as exc:
        LOGGER.warning("AI hashtag generation failed, using fallback hashtags: %s", exc)

    if not hashtags:
        hashtags = _fallback_hashtags(product)
        LOGGER.info("Using fallback hashtags count=%s", len(hashtags))

    product["hashtags"] = hashtags[:MAX_HASHTAGS]
    return product
