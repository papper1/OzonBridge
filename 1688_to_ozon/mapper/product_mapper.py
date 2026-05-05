"""Build final Ozon product payloads from canonical products and template config."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import re
from typing import Any

from classifier.template_detector import detect_template
from mapper.attribute_mapper import map_attributes_to_ozon
from mapper.field_mapper import map_fields
from mapper.template_loader import load_template
from models.normalized_product import NormalizedProduct
from models.ozon_product import OzonProduct
from normalizer.build_variants import select_primary_variant
from translator.ai_hashtag_service import generate_hashtags
from translator.field_translator import convert_international_size_to_russian
from validators.required_field_validator import find_missing_required_fields


DIMENSION_KEY_HINTS = (
    "kích",
    "kich",
    "size",
    "dimension",
    "package",
    "product size",
    "尺寸",
)
FIXED_TEMPLATE_PRICES = {
    "hoodie": "249",
}
DEFAULT_PACKAGE_FALLBACK = {
    "weight_package_g": "600",
    "package_width_mm": "350",
    "package_height_mm": "80",
    "package_length_mm": "400",
}
RUSSIAN_SIZE_BY_SIZE = {
    "XXS": "40",
    "XS": "42",
    "S": "44",
    "M": "46",
    "L": "48",
    "XL": "50",
    "XXL": "52",
    "2XL": "52",
    "3XL": "54",
    "4XL": "56",
}
DEFAULT_RUSSIAN_SIZE = "46"


def _to_dict(product: Any) -> dict[str, Any]:
    if is_dataclass(product):
        return asdict(product)
    if isinstance(product, dict):
        return dict(product)
    return {}


def build_ozon_name(product: Any) -> str:
    """Build a concise export name from canonical product fields."""
    product_dict = _to_dict(product)
    translated_title = str(product_dict.get("translated_title") or "").strip()
    if translated_title:
        return translated_title

    parts: list[str] = []
    for field_name in ("brand", "model", "product_name", "cpu", "ram", "storage", "color", "size"):
        value = str(product_dict.get(field_name) or "").strip()
        if value and value not in parts:
            parts.append(value)

    if parts:
        return " ".join(parts[:5])
    return (
        str(product_dict.get("product_name") or product_dict.get("title") or "Product").strip()
        or "Product"
    )


def build_ozon_variants(product: Any) -> list[dict]:
    """Pass variants through with minimal cleanup for compatibility."""
    product_dict = _to_dict(product)
    variants = product_dict.get("variants")
    return list(variants or []) if isinstance(variants, list) else []


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _extract_first_numeric(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", "."))
    return match.group(1) if match else ""


def _resolve_export_price(product: dict[str, Any], selected_variant: dict[str, Any]) -> str:
    template_name = detect_template(product)
    fixed_price = FIXED_TEMPLATE_PRICES.get(template_name)
    if fixed_price:
        return fixed_price
    return _extract_first_numeric(_first_non_empty(selected_variant.get("price"), product.get("price")))


def _extract_last_url_token(source_url: str) -> str:
    match = re.search(r"/(\d+)\.html", str(source_url or ""))
    return match.group(1) if match else ""


def _split_numeric_dimensions(value: Any) -> tuple[str, str, str]:
    numbers = re.findall(r"(\d+(?:[.,]\d+)?)", str(value or ""))
    if len(numbers) < 3:
        return "", "", ""
    normalized = [number.replace(",", ".") for number in numbers[:3]]
    return normalized[0], normalized[1], normalized[2]


def _extract_dimensions_mm(raw_attributes: dict[str, Any]) -> tuple[str, str, str]:
    if not isinstance(raw_attributes, dict):
        return "", "", ""

    for key, value in raw_attributes.items():
        key_text = str(key or "").lower()
        if not any(token in key_text for token in DIMENSION_KEY_HINTS):
            continue

        width, height, length = _split_numeric_dimensions(value)
        if all((width, height, length)):
            return width, height, length
    return "", "", ""


def _extract_weight_kg(value: Any) -> str:
    return _extract_first_numeric(value)


def _extract_weight_g(value: Any) -> str:
    raw_text = str(value or "").lower()
    numbers = re.findall(r"(\d+(?:\.\d+)?)", str(value or "").replace(",", "."))
    if not numbers:
        return ""

    number = max(float(item) for item in numbers)
    if "kg" in raw_text or "кг" in raw_text:
        return str(int(number * 1000))
    if re.search(r"\bg\b", raw_text) or "г" in raw_text:
        return str(int(number))
    if number < 10:
        return str(int(number * 1000))
    return str(int(number))


def _with_default_package_value(value: Any, fallback_key: str) -> str:
    text = str(value or "").strip()
    return text or DEFAULT_PACKAGE_FALLBACK[fallback_key]


def _extract_storage_capacity_gb(value: Any) -> str:
    text = str(value or "").upper()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)", text)
    if not match:
        return ""

    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "TB":
        amount *= 1024
    return str(int(amount)) if amount.is_integer() else str(amount)


def _format_ram_value(value: Any) -> str:
    text = str(value or "").strip().upper()
    match = re.search(r"(\d+(?:\.\d+)?)\s*GB\b", text)
    if not match:
        return str(value or "").strip()
    amount = match.group(1)
    amount = str(int(float(amount))) if float(amount).is_integer() else amount
    return f"{amount} GB"


def _sanitize_color_value(value: Any) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    if any(token in lowered for token in ("gb", "tb", "bộ nhớ", "bo nho", "dung lượng", "dung luong")):
        return ""
    return lowered


def _format_hashtags(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _resolve_variant_image_urls(images: list[str], selected_variant: dict[str, Any]) -> tuple[str, str]:
    variant_main_image = str(selected_variant.get("image_url") or "").strip()
    if not variant_main_image:
        return (images[0] if images else "", "\n".join(images[1:]) if len(images) > 1 else "")

    additional_images = [url for url in images if str(url).strip() and str(url).strip() != variant_main_image]
    return variant_main_image, "\n".join(additional_images)


def _normalize_size_key(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    return text.replace("SIZE", "").replace(" ", "")


def _resolve_russian_size(value: Any) -> str:
    normalized_size = _normalize_size_key(value)
    converted = str(convert_international_size_to_russian(value).get("russian_size") or "").strip()
    return converted or RUSSIAN_SIZE_BY_SIZE.get(normalized_size, DEFAULT_RUSSIAN_SIZE)


def _infer_laptop_type(product: dict[str, Any]) -> str:
    blob = " ".join(
        str(part or "")
        for part in (
            product.get("title"),
            product.get("product_name"),
            product.get("cpu"),
            product.get("raw_attributes"),
        )
    ).lower()
    if any(hint in blob for hint in ("gaming", "gamming", "game", "gamer", "rtx", "gtx", "geforce", "radeon rx")):
        return "Gaming laptop"
    return "Laptop"


def _infer_gender(product: dict[str, Any]) -> str:
    blob = " ".join(
        str(part or "")
        for part in (
            product.get("title"),
            product.get("product_name"),
            product.get("raw_attributes"),
            product.get("gender"),
        )
    ).lower()
    if any(token in blob for token in ("women", "woman", "female", "girl", "ladies")):
        return "Female"
    if any(token in blob for token in ("men", "man", "male", "boy", "gentlemen")):
        return "Male"
    if "unisex" in blob:
        return "Male"
    return "Male"


def _infer_type_export(product: dict[str, Any]) -> str:
    template_name = detect_template(product)
    blob = " ".join(
        str(part or "")
        for part in (
            product.get("title"),
            product.get("product_name"),
            product.get("model"),
            product.get("raw_attributes"),
        )
    ).lower()

    if template_name == "laptop":
        return _infer_laptop_type(product)
    if template_name == "hoodie":
        return "Hoodie"
    if template_name == "clothing":
        if any(token in blob for token in ("t-shirt", "t shirt", "tee", "tee-shirt")):
            return "T-Shirt"
        return "T-Shirt"
    if template_name == "shoes":
        return "Shoes"
    return ""


def build_export_context(product: dict[str, Any]) -> dict[str, Any]:
    """Build derived export fields needed by real Ozon workbook templates."""
    context = dict(product)
    images = list(product.get("images", []) or [])
    raw_attributes = dict(product.get("raw_attributes", {}) or {})

    package_width_mm, package_height_mm, package_length_mm = _split_numeric_dimensions(product.get("size"))
    if not all((package_width_mm, package_height_mm, package_length_mm)):
        package_width_mm, package_height_mm, package_length_mm = _extract_dimensions_mm(raw_attributes)

    variants = build_ozon_variants(product)
    selected_variant = select_primary_variant(variants)
    main_image_url, additional_image_urls = _resolve_variant_image_urls(images, selected_variant)
    export_price = _resolve_export_price(product, selected_variant)
    export_ram = _format_ram_value(_first_non_empty(selected_variant.get("ram"), product.get("ram")))
    export_storage = _first_non_empty(selected_variant.get("storage"), product.get("storage"))
    export_color = _sanitize_color_value(_first_non_empty(selected_variant.get("color"), product.get("color")))
    export_size = _first_non_empty(selected_variant.get("size"), product.get("size"))
    russian_size_export = _resolve_russian_size(export_size)
    russian_size_info = convert_international_size_to_russian(export_size)
    export_color_name = _first_non_empty(
        selected_variant.get("color_name"),
        product.get("color_name"),
        export_color,
    )
    export_height = _first_non_empty(product.get("height"))

    context.update(
        {
            "ozon_product_name": build_ozon_name(product),
            "article_code": _first_non_empty(
                product.get("article_code"),
                _extract_last_url_token(product.get("source_url", "")),
                selected_variant.get("sku"),
            ),
            "price_cny": export_price,
            "merge_on_one_pdp": "",
            "main_image_url": main_image_url,
            "additional_image_urls": additional_image_urls,
            "package_weight_g": _with_default_package_value(_extract_weight_g(product.get("weight")), "weight_package_g"),
            "package_width_mm": _with_default_package_value(package_width_mm, "package_width_mm"),
            "package_height_mm": _with_default_package_value(package_height_mm, "package_height_mm"),
            "package_length_mm": _with_default_package_value(package_length_mm, "package_length_mm"),
            "weight_kg_numeric": _extract_weight_kg(product.get("weight")),
            "storage_capacity_gb": _extract_storage_capacity_gb(export_storage),
            "ram_export": export_ram,
            "storage_export": export_storage,
            "size": export_size,
            "russian_size_export": russian_size_export,
            "size_conversion": russian_size_info,
            "color_export": export_color,
            "color_name_export": export_color_name,
            "hashtags_export": _format_hashtags(product.get("hashtags")),
            "type_export": _infer_type_export(product),
            "gender_export": _first_non_empty(product.get("gender"), _infer_gender(product)) or "Male",
            "height": export_height,
            "country_of_manufacture": _first_non_empty(
                product.get("country_of_manufacture"),
                raw_attributes.get("Country of manufacture"),
                raw_attributes.get("country_of_manufacture"),
                raw_attributes.get("Xuất xứ"),
                raw_attributes.get("xuat xu"),
                raw_attributes.get("Made in"),
                raw_attributes.get("made in"),
            ),
        }
    )
    return context


def map_product_to_ozon(product: Any) -> dict:
    """Map a canonical product to a template-driven Ozon payload."""
    original_dict = _to_dict(product)
    if not original_dict.get("hashtags"):
        original_dict = generate_hashtags(original_dict)
    canonical_dict = NormalizedProduct.from_dict(original_dict).to_dict()
    for passthrough_field in (
        "price",
        "title",
        "product_name",
        "description",
        "hashtags",
        "source_url",
        "supplier",
        "translated_title",
        "translated_description",
        "translated_attributes",
    ):
        passthrough_value = original_dict.get(passthrough_field)
        if passthrough_value not in (None, "", [], {}, ()):
            canonical_dict[passthrough_field] = passthrough_value
    export_context = build_export_context(canonical_dict)
    template_name = detect_template(canonical_dict)
    template = load_template(template_name)
    row_data = map_fields(export_context, dict(template.get("field_map", {}) or {}))
    missing_required_fields = find_missing_required_fields(
        export_context,
        list(template.get("required_fields", []) or []),
    )

    ozon_product = OzonProduct(
        name=build_ozon_name(canonical_dict),
        category=template_name,
        category_id=None,
        template_name=str(template.get("template_name", template_name)),
        row_data=row_data,
        attributes=map_attributes_to_ozon(row_data),
        images=list(canonical_dict.get("images", []) or []),
        variants=build_ozon_variants(canonical_dict),
        supplier=str(canonical_dict.get("supplier", "") or ""),
        source_url=str(canonical_dict.get("source_url", "") or ""),
        missing_required_fields=missing_required_fields,
    )
    return ozon_product.to_dict()


def map_product(product: Any) -> dict:
    """Compatibility wrapper for older pipeline code."""
    return map_product_to_ozon(product)
