import re
from typing import Any

from classifier.template_detector import detect_template
from normalizer.clean_text import clean_text, normalize_storage_text


INVALID_OPTION_HINTS = {
    "barebone",
    "khÃ´ng ram",
    "khong ram",
    "no ram",
    "khÃ´ng á»• cá»©ng",
    "khong o cung",
    "no ssd",
    "no storage",
    "without disk",
}

COLOR_SPLIT_PATTERN = r"[,;/|]+"
SIZE_SPLIT_PATTERN = r"[,;|]+"

COLOR_REPLACEMENTS = (
    ("xám không gian", "Space Grey"),
    ("xam khong gian", "Space Grey"),
    ("space grey", "Space Grey"),
    ("space gray", "Space Grey"),
    ("xám", "Grey"),
    ("xam", "Grey"),
    ("grey", "Grey"),
    ("gray", "Grey"),
    ("bạc", "Silver"),
    ("bac", "Silver"),
    ("silver", "Silver"),
    ("đen", "Black"),
    ("den", "Black"),
    ("black", "Black"),
    ("trắng", "White"),
    ("trang", "White"),
    ("white", "White"),
    ("xanh dương", "Blue"),
    ("xanh duong", "Blue"),
    ("xanh lam", "Blue"),
    ("blue", "Blue"),
    ("xanh lá", "Green"),
    ("xanh la", "Green"),
    ("green", "Green"),
    ("vàng", "Gold"),
    ("vang", "Gold"),
    ("gold", "Gold"),
    ("đỏ", "Red"),
    ("do", "Red"),
    ("red", "Red"),
    ("hồng", "Pink"),
    ("hong", "Pink"),
    ("pink", "Pink"),
    ("tím", "Purple"),
    ("tim", "Purple"),
    ("purple", "Purple"),
    ("cam", "Orange"),
    ("orange", "Orange"),
    ("nâu", "Brown"),
    ("nau", "Brown"),
    ("brown", "Brown"),
)

BASIC_COLOR_BY_HINT = (
    ("space grey", "Grey"),
    ("space gray", "Grey"),
    ("grey", "Grey"),
    ("gray", "Grey"),
    ("silver", "Silver"),
    ("black", "Black"),
    ("white", "White"),
    ("blue", "Blue"),
    ("green", "Green"),
    ("gold", "Gold"),
    ("red", "Red"),
    ("pink", "Pink"),
    ("purple", "Purple"),
    ("orange", "Orange"),
    ("brown", "Brown"),
)

IMAGE_URL_KEYS = (
    "skuImageUrl",
    "imageUrl",
    "imgUrl",
    "url",
    "fullPathImageURI",
    "originalImageURI",
)


def _pick_value(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for the given keys."""
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}, ()):
            return value
    return None


def _slugify(text: str) -> str:
    """Build a simple SKU-friendly slug."""
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _is_invalid_option(text: str) -> bool:
    """Detect options that should be skipped or marked."""
    lowered = clean_text(text).lower()
    return any(hint in lowered for hint in INVALID_OPTION_HINTS)


def _normalize_capacity(value: str) -> str:
    """Normalize RAM or storage capacity text."""
    normalized = normalize_storage_text(value.upper().replace("G", "GB").replace("T", "TB"))
    normalized = re.sub(r"(\d+)\s*GBB\b", r"\1GB", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"(\d+)\s*TBB\b", r"\1TB", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _looks_like_memory_value(text: str) -> bool:
    cleaned = clean_text(str(text or ""))
    if not cleaned:
        return False
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*(TB|GB|G|MB|M)\b", cleaned, flags=re.IGNORECASE)
    return len(matches) >= 1


def _looks_like_color_label(text: str) -> bool:
    cleaned = clean_text(str(text or ""))
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if _looks_like_combined_memory_text(cleaned):
        return False
    if any(token in lowered for token in ("¥", "库存", "kho", "chiếc", "memory", "ram", "ssd", "gb", "tb")):
        return False
    return True


def _translate_color_label(text: str) -> str:
    translated = clean_text(str(text or ""))
    if not translated:
        return ""

    for source, target in COLOR_REPLACEMENTS:
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated, flags=re.IGNORECASE)

    translated = re.sub(r"\s{2,}", " ", translated).strip()
    return translated


def _normalize_size_option(text: str) -> str:
    option = clean_text(str(text or ""))
    if not option:
        return ""
    if re.search(r"\d+\s*[x*]\s*\d+", option, flags=re.IGNORECASE):
        return ""

    primary = option.split("/")[0].strip()
    if not primary:
        return ""
    if not re.search(r"[A-Za-z]", primary):
        return ""

    normalized = primary.upper().replace("SIZE", "").strip()
    normalized = re.sub(r"[^A-Z0-9+\- ]", "", normalized).strip()
    return normalized


def _extract_basic_color(value: str) -> str:
    lowered = clean_text(str(value or "")).lower()
    for hint, basic_color in BASIC_COLOR_BY_HINT:
        if hint in lowered:
            return basic_color
    return ""


def _normalize_color_option(text: str) -> dict[str, str]:
    original = clean_text(str(text or ""))
    if not original or not _looks_like_color_label(original):
        return {}

    color_name = _translate_color_label(original)
    basic_color = _extract_basic_color(color_name) or _extract_basic_color(original)
    if not basic_color:
        return {}

    return {
        "color": basic_color,
        "color_name": color_name,
    }


def _extract_variant_image_map(product_data: dict[str, Any]) -> dict[str, str]:
    """Build a best-effort color/image map from 1688 SKU image payloads."""
    sku_data = product_data.get("sku")
    if not isinstance(sku_data, dict):
        return {}

    image_entries: list[dict[str, Any]] = []
    for key in ("skuImageList", "sku_image_list", "images"):
        value = sku_data.get(key)
        if isinstance(value, list):
            image_entries.extend(item for item in value if isinstance(item, dict))

    nested_model = sku_data.get("skuModel")
    if isinstance(nested_model, dict):
        nested_images = nested_model.get("skuImageList")
        if isinstance(nested_images, list):
            image_entries.extend(item for item in nested_images if isinstance(item, dict))

    image_map: dict[str, str] = {}
    for entry in image_entries:
        image_url = ""
        for key in IMAGE_URL_KEYS:
            candidate = clean_text(str(entry.get(key, "")))
            if candidate:
                image_url = candidate
                break
        if not image_url:
            continue

        for candidate in (
            entry.get("value"),
            entry.get("name"),
            entry.get("skuAttr"),
            entry.get("skuName"),
            entry.get("text"),
            entry.get("attributeValue"),
            entry.get("color"),
        ):
            option = _normalize_color_option(str(candidate or ""))
            if not option:
                continue
            for map_key in (option.get("color_name", "").lower(), option.get("color", "").lower()):
                if map_key and map_key not in image_map:
                    image_map[map_key] = image_url

    return image_map


def parse_memory_options(text: str) -> list[dict]:
    """Parse combined RAM + storage options into structured dicts."""
    if not text:
        return []

    options: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for raw_option in re.split(r"[,;/|]+", text):
        option = clean_text(raw_option)
        if not option or _is_invalid_option(option):
            continue

        explicit_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(TB|GB|G|MB|M)\b", option, flags=re.IGNORECASE)
        compact_match = re.search(
            r"^\s*(\d+(?:\.\d+)?)\s*(?:GB|G)?\s*\+\s*(\d+(?:\.\d+)?)\s*(TB|GB|G|MB|M)\b",
            option,
            flags=re.IGNORECASE,
        )
        no_storage_match = re.search(
            r"^\s*(\d+(?:\.\d+)?)\s*(?:GB|G)?\s*\+\s*0(?:\.0+)?\s*$",
            option,
            flags=re.IGNORECASE,
        )

        ram_value = ""
        storage_value = ""

        if compact_match:
            ram_value = _normalize_capacity(f"{compact_match.group(1)}GB")
            storage_amount = compact_match.group(2)
            storage_unit = compact_match.group(3)
            if storage_amount not in {"0", "0.0"}:
                storage_value = _normalize_capacity(f"{storage_amount}{storage_unit}")
        elif no_storage_match:
            ram_value = _normalize_capacity(f"{no_storage_match.group(1)}GB")
            storage_value = ""
        elif len(explicit_matches) >= 2:
            ram_value = _normalize_capacity(f"{explicit_matches[0][0]}{explicit_matches[0][1]}")
            storage_value = _normalize_capacity(f"{explicit_matches[1][0]}{explicit_matches[1][1]}")
        else:
            continue

        if not ram_value:
            continue
        key = (ram_value, storage_value)
        if key in seen:
            continue

        seen.add(key)
        options.append(
            {
                "ram": ram_value,
                "storage": storage_value,
            }
        )

    return options


def _looks_like_combined_memory_text(text: str) -> bool:
    """Return True when a field contains RAM+storage option text instead of a single value."""
    cleaned = clean_text(str(text or ""))
    if not cleaned:
        return False

    parsed = parse_memory_options(cleaned)
    if len(parsed) >= 2:
        return True

    return len(parsed) == 1 and bool(re.search(r"[,+/|;]", cleaned))


def extract_primary_memory_option(text: str) -> dict[str, str]:
    """Pick the first valid RAM + storage combination from a raw options string."""
    options = parse_memory_options(text)
    selected = select_primary_variant(options)
    if not selected:
        return {"ram": "", "storage": ""}
    return {
        "ram": clean_text(str(selected.get("ram", ""))),
        "storage": clean_text(str(selected.get("storage", ""))),
    }


def _capacity_to_gb(value: str) -> float:
    """Convert capacity text like 16GB or 1TB into a comparable GB number."""
    text = clean_text(str(value or "")).upper()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB|MB)", text)
    if not match:
        return float("inf")

    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "TB":
        return amount * 1024
    if unit == "MB":
        return amount / 1024
    return amount


def select_primary_variant(variants: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose a stable base variant, preferring the smallest storage then RAM."""
    valid_variants: list[dict[str, Any]] = []
    for variant in variants or []:
        if not isinstance(variant, dict):
            continue
        if variant.get("note") == "invalid_option":
            continue
        valid_variants.append(variant)

    if not valid_variants:
        return {}

    return min(
        valid_variants,
        key=lambda variant: (
            _capacity_to_gb(str(variant.get("storage", ""))),
            _capacity_to_gb(str(variant.get("ram", ""))),
            clean_text(str(variant.get("sku", ""))),
        ),
    )


def parse_color_options(text: str) -> list[dict[str, str]]:
    """Parse color options into unique basic-color/display-name pairs."""
    if not text:
        return []

    colors: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw_option in re.split(COLOR_SPLIT_PATTERN, text):
        option = _normalize_color_option(raw_option)
        color = option.get("color", "")
        color_name = option.get("color_name", "")
        if not color or not color_name or _is_invalid_option(color_name):
            continue

        normalized = color_name.lower()
        if normalized in seen:
            continue

        seen.add(normalized)
        colors.append(option)

    return colors


def parse_size_options(text: str) -> list[str]:
    """Parse clothing size text into normalized labels."""
    if not text:
        return []

    sizes: list[str] = []
    seen: set[str] = set()

    for raw_option in re.split(SIZE_SPLIT_PATTERN, text):
        size = _normalize_size_option(raw_option)
        if not size or size in seen:
            continue
        seen.add(size)
        sizes.append(size)

    return sizes


def _extract_memory_text(attributes: dict[str, Any]) -> str:
    """Find likely text containing memory/storage combinations."""
    candidate_keys = (
        "memory_options",
        "memory",
        "ram_storage",
        "config",
        "configuration",
        "版本",
        "内存",
        "硬盘容量",
        "套餐",
        "dung lượng bộ nhớ",
        "dung luong bo nho",
        "dung lÆ°á»£ng bá»™ nhá»›",
    )
    for key, value in attributes.items():
        key_text = clean_text(str(key)).lower()
        if key_text in candidate_keys:
            return clean_text(str(value))

    for key, value in attributes.items():
        key_text = clean_text(str(key)).lower()
        value_text = clean_text(str(value))
        if any(
            token in key_text
            for token in (
                "ram",
                "memory",
                "内存",
                "bộ nhớ",
                "bo nho",
            )
        ):
            return value_text
        if (
            any(token in key_text for token in ("storage", "ssd", "硬盘", "dung lượng", "dung luong"))
            and len(re.findall(r"(\d+(?:\.\d+)?)\s*(TB|GB|G|MB|M)\b", value_text, flags=re.IGNORECASE)) >= 2
        ):
            return value_text
    return ""


def _extract_color_text(attributes: dict[str, Any]) -> str:
    """Find likely text containing colors."""
    candidate_keys = (
        "color",
        "colors",
        "mÃ u",
        "mau",
        "颜色",
        "color options",
        "màu sắc",
        "mau sac",
        "mÃ u sáº¯c",
    )
    for key, value in attributes.items():
        key_text = clean_text(str(key)).lower()
        value_text = clean_text(str(value))
        if any(token in value_text.lower() for token in ("gb", "tb", "bộ nhớ", "bo nho", "dung lượng", "dung luong")):
            continue
        if key_text in candidate_keys or "color" in key_text or "颜色" in key_text or "màu" in key_text or "mÃ u" in key_text:
            return value_text
    return ""


def _extract_color_labels(product_data: dict[str, Any], raw_attributes: dict[str, Any]) -> list[str]:
    """Collect color labels from SKU labels and raw attribute keys."""
    labels: list[str] = []
    seen: set[str] = set()

    sku_data = product_data.get("sku")
    if isinstance(sku_data, dict):
        option_labels = sku_data.get("option_labels")
        if isinstance(option_labels, list):
            for option in option_labels:
                label = clean_text(str(option))
                normalized = label.lower()
                if not label or normalized in seen or not _looks_like_color_label(label):
                    continue
                seen.add(normalized)
                labels.append(label)

    for key, value in raw_attributes.items():
        key_text = clean_text(str(key))
        value_text = clean_text(str(value))
        normalized_key = key_text.lower()
        if not key_text or normalized_key in seen:
            continue
        if not _looks_like_color_label(key_text):
            continue
        if _looks_like_memory_value(value_text):
            seen.add(normalized_key)
            labels.append(key_text)

    if labels:
        return labels

    fallback_text = _extract_color_text(raw_attributes)
    return [fallback_text] if fallback_text else []


def _extract_size_text(attributes: dict[str, Any]) -> str:
    """Find likely text containing size options."""
    candidate_keys = (
        "size",
        "sizes",
        "size option",
        "kích cỡ",
        "kich co",
        "尺码",
    )
    for key, value in attributes.items():
        key_text = clean_text(str(key)).lower()
        value_text = clean_text(str(value))
        if key_text in candidate_keys or "size" in key_text or "kích cỡ" in key_text or "尺码" in key_text:
            return value_text
    return ""


def _build_sku(model: str, color: str, ram: str, storage: str, index: int) -> str:
    """Generate a simple SKU from model and variant fields."""
    parts = [_slugify(part) for part in (model, color, ram, storage) if clean_text(part)]
    return "-".join(parts) if parts else f"variant-{index}"


def build_variants(attributes: dict, price: str = "") -> list[dict]:
    """Build variants by combining color and memory/storage options."""
    if not isinstance(attributes, dict):
        return []

    product_data = attributes
    raw_attributes = product_data.get("raw_attributes") if isinstance(product_data.get("raw_attributes"), dict) else product_data
    model = clean_text(str(_pick_value(product_data, "model") or _pick_value(raw_attributes, "model") or ""))
    template_name = detect_template(product_data if isinstance(product_data, dict) else {})

    memory_text = _extract_memory_text(raw_attributes)
    color_text = _extract_color_text(raw_attributes)
    size_text = _extract_size_text(raw_attributes)
    variant_image_map = _extract_variant_image_map(product_data)

    memory_options = [] if template_name in {"hoodie", "clothing", "shoes"} else parse_memory_options(memory_text)
    color_options: list[dict[str, str]] = []
    size_options = parse_size_options(size_text)
    for label in _extract_color_labels(product_data, raw_attributes):
        parsed_options = parse_color_options(label) if re.search(COLOR_SPLIT_PATTERN, label) else [_normalize_color_option(label)]
        for option in parsed_options:
            if option and option not in color_options:
                color_options.append(option)
    if not color_options:
        color_options = parse_color_options(color_text)

    if not memory_options and any(product_data.get(key) for key in ("ram", "storage")):
        memory_options = [
            {
                "ram": clean_text(str(product_data.get("ram", ""))),
                "storage": clean_text(str(product_data.get("storage", ""))),
            }
        ]

    if not color_options:
        fallback_color = clean_text(str(_pick_value(product_data, "color") or ""))
        fallback_option = _normalize_color_option(fallback_color)
        color_options = [fallback_option] if fallback_option else []
    if not size_options:
        fallback_size = _normalize_size_option(str(_pick_value(product_data, "size") or ""))
        size_options = [fallback_size] if fallback_size else []

    if not memory_options:
        memory_options = [{"ram": "", "storage": ""}]
    if not color_options:
        color_options = [{"color": "", "color_name": ""}]
    if not size_options:
        size_options = [""]

    variants: list[dict] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for color_option in color_options:
        for size in size_options:
            for memory in memory_options:
                color = clean_text(color_option.get("color", ""))
                color_name = clean_text(color_option.get("color_name", ""))
                ram = clean_text(memory.get("ram", ""))
                storage = clean_text(memory.get("storage", ""))
                normalized_size = clean_text(size)
                dedupe_key = (color.lower(), color_name.lower(), normalized_size.lower(), ram.lower(), storage.lower())
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                invalid = any(_is_invalid_option(part) for part in (color_name, normalized_size, ram, storage) if part)
                variant = {
                    "sku": _build_sku(model, " ".join(part for part in (color_name or color, normalized_size) if part), ram, storage, len(variants) + 1),
                    "color": color,
                    "color_name": color_name or color,
                    "size": normalized_size,
                    "ram": ram,
                    "storage": storage,
                    "price": clean_text(price),
                }
                image_url = variant_image_map.get(color_name.lower()) or variant_image_map.get(color.lower())
                if image_url:
                    variant["image_url"] = image_url
                if invalid:
                    variant["note"] = "invalid_option"
                variants.append(variant)

    return variants


def build_product_variants(attributes: dict, price: str = "") -> dict:
    """Compatibility helper for pipeline usage."""
    if not isinstance(attributes, dict):
        return {"variants": []}

    product = dict(attributes)
    template_name = detect_template(product)
    if not product.get("variants"):
        product["variants"] = build_variants(attributes, price=price or clean_text(str(product.get("price", ""))))

    variants = product.get("variants") if isinstance(product.get("variants"), list) else []
    selected_variant = select_primary_variant(variants)
    if selected_variant:
        current_ram = clean_text(str(product.get("ram", "")))
        current_storage = clean_text(str(product.get("storage", "")))
        current_color = clean_text(str(product.get("color", "")))
        current_color_name = clean_text(str(product.get("color_name", "")))
        current_size = clean_text(str(product.get("size", "")))

        if template_name not in {"hoodie", "clothing", "shoes"} and (not current_ram or _looks_like_combined_memory_text(current_ram)):
            product["ram"] = clean_text(str(selected_variant.get("ram", "")))
        if template_name not in {"hoodie", "clothing", "shoes"} and (not current_storage or _looks_like_combined_memory_text(current_storage)):
            product["storage"] = clean_text(str(selected_variant.get("storage", "")))
        if not current_color or _looks_like_combined_memory_text(current_color):
            product["color"] = clean_text(str(selected_variant.get("color", "")))
        if not current_color_name or _looks_like_combined_memory_text(current_color_name):
            product["color_name"] = clean_text(str(selected_variant.get("color_name", selected_variant.get("color", ""))))
        if not current_size or bool(re.search(SIZE_SPLIT_PATTERN, current_size)):
            product["size"] = clean_text(str(selected_variant.get("size", "")))

    return product
