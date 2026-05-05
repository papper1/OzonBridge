"""Small manual test for the AI translator."""

from __future__ import annotations

import json
import os

from translator.ai_translator import translate_product_fields, translate_text_zh_to_ru


def main() -> None:
    sample_title = "夏季新款男士宽松短袖T恤潮流百搭圆领上衣"
    sample_product = {
        "title": sample_title,
        "description": "纯棉面料，透气舒适，适合夏季日常穿着",
        "attributes": {
            "颜色": "黑色",
            "尺码": "XL",
            "材质": "纯棉",
        },
    }

    print("=== Single Text ===")
    print("AI enabled:", os.getenv("ENABLE_AI_TRANSLATION", "1"))
    print("ZH:", sample_title)
    print("RU:", translate_text_zh_to_ru(sample_title, content_type="title"))
    print()

    print("=== Product Fields ===")
    translated_product = translate_product_fields(sample_product)
    print(json.dumps(translated_product, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
