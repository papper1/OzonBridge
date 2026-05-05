from typing import Any

from normalizer.clean_text import clean_text


TRANSLATION_MAP = {
    "vi": {
        "品牌": "thương hiệu",
        "型号": "mẫu",
        "屏幕尺寸": "kích thước màn hình",
        "分辨率": "độ phân giải",
        "操作系统": "hệ điều hành",
        "处理器": "bộ xử lý",
        "内存": "ram",
        "硬盘容量": "dung lượng lưu trữ",
        "显卡": "card đồ họa",
        "重量": "trọng lượng",
        "颜色": "màu sắc",
    },
    "en": {
        "品牌": "brand",
        "型号": "model",
        "屏幕尺寸": "screen size",
        "分辨率": "resolution",
        "操作系统": "operating system",
        "处理器": "processor",
        "内存": "ram",
        "硬盘容量": "storage",
        "显卡": "graphics card",
        "重量": "weight",
        "颜色": "color",
    },
}


def translate_text(text: str, target_lang: str = "vi") -> str:
    """Translate common known labels using an internal dictionary."""
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    language_map = TRANSLATION_MAP.get(target_lang, TRANSLATION_MAP["vi"])
    return language_map.get(cleaned, text)


def batch_translate_dict_keys(data: dict, target_lang: str = "vi") -> dict:
    """Translate dict keys with the internal dictionary and preserve values."""
    if not isinstance(data, dict):
        return {}

    translated: dict[str, Any] = {}
    for key, value in data.items():
        translated_key = translate_text(str(key), target_lang=target_lang)
        translated[translated_key] = value
    return translated
