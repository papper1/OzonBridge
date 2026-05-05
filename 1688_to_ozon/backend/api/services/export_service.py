from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import EXPORT_DIR, ensure_directories  # noqa: E402
from mapper.product_mapper import map_product_to_ozon  # noqa: E402
from ozon.export_xlsx import export_to_xlsx  # noqa: E402

from .runtime_store import runtime_store


def export_products(products: list[dict[str, Any]], file_name: str | None = None) -> dict[str, str]:
    ensure_directories()
    mapped_products = [
        product if isinstance(product.get("row_data"), dict) else map_product_to_ozon(product)
        for product in products
    ]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    resolved_name = file_name or f"crawldesk_export_{timestamp}.xlsx"
    export_path = EXPORT_DIR / resolved_name
    export_to_xlsx(mapped_products, str(export_path))
    file_id, registered_path = runtime_store.register_file(export_path)
    return {
        "file_id": file_id,
        "file_name": registered_path.name,
        "download_url": f"/download/{file_id}",
    }

