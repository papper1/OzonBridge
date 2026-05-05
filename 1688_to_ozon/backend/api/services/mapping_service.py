from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mapper.product_mapper import map_product_to_ozon  # noqa: E402


def map_products_to_ozon(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [map_product_to_ozon(product) for product in products]

