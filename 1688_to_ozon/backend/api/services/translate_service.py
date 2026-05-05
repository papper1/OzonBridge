from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from translator.ai_translator import translate_product_fields  # noqa: E402


def translate_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    translated_items: list[dict[str, Any]] = []
    for product in products:
        translated_items.append(translate_product_fields(product))
    return translated_items

