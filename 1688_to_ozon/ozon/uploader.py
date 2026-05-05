import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config import EXPORT_DIR, OZON_API_KEY, OZON_API_URL, OZON_CLIENT_ID
from ozon.api_client import OzonClient
from ozon.export_xlsx import export_to_xlsx
from utils import logger as logger_module


def _get_logger() -> logging.Logger:
    """Return project logger with a safe fallback."""
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("ozon.uploader")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("ozon.uploader")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


LOGGER = _get_logger()


def _build_export_path() -> Path:
    """Create a timestamped export path for Excel mode."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return EXPORT_DIR / f"ozon_upload_{timestamp}.xlsx"


def _is_success_response(response: Any) -> bool:
    """Best-effort success detection for API responses."""
    if isinstance(response, dict):
        if response.get("ok") is False:
            return False
        if response.get("error"):
            return False
    return True


def upload_products(products: list[dict], mode: str = "excel"):
    """Upload Ozon product data by Excel export or API calls."""
    normalized_mode = str(mode or "excel").strip().lower()
    valid_products = [product for product in products if isinstance(product, dict)]

    if normalized_mode == "excel":
        output_path = _build_export_path()
        file_path = export_to_xlsx(valid_products, str(output_path))
        LOGGER.info("Excel export completed: %s products -> %s", len(valid_products), file_path)
        return file_path

    if normalized_mode != "api":
        raise ValueError("Unsupported upload mode. Use 'excel' or 'api'.")

    client = OzonClient(
        base_url=OZON_API_URL,
        client_id=OZON_CLIENT_ID,
        api_key=OZON_API_KEY,
    )

    responses: list[dict] = []
    success_count = 0
    failed_count = 0

    for index, product in enumerate(valid_products, start=1):
        try:
            response = client.create_product(product)
            if _is_success_response(response):
                success_count += 1
            else:
                failed_count += 1

            responses.append(
                {
                    "index": index,
                    "name": product.get("name", ""),
                    "success": _is_success_response(response),
                    "response": response,
                }
            )
        except Exception as exc:
            failed_count += 1
            LOGGER.exception("Failed to upload product %s: %s", index, exc)
            responses.append(
                {
                    "index": index,
                    "name": product.get("name", ""),
                    "success": False,
                    "response": {"error": str(exc)},
                }
            )

    LOGGER.info(
        "API upload finished: success=%s, failed=%s, total=%s",
        success_count,
        failed_count,
        len(valid_products),
    )
    return responses
