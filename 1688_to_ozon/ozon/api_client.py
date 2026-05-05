import logging

import requests

from utils import logger as logger_module


DEFAULT_API_TIMEOUT = 30

ENDPOINTS = {
    "create_product": "/v1/product/import",
    "update_product": "/v1/product/update",
    "get_product_info": "/v2/product/info",
}


def _get_logger() -> logging.Logger:
    """Return project logger with a safe fallback."""
    for factory_name in ("get_logger", "setup_logger", "build_logger", "create_logger"):
        factory = getattr(logger_module, factory_name, None)
        if callable(factory):
            try:
                return factory("ozon.api_client")
            except TypeError:
                try:
                    return factory()
                except TypeError:
                    continue

    logger = logging.getLogger("ozon.api_client")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logger.setLevel(logging.INFO)
    return logger


class OzonClient:
    def __init__(self, base_url: str, client_id: str, api_key: str, timeout: int = DEFAULT_API_TIMEOUT):
        self.base_url = str(base_url or "").rstrip("/")
        self.client_id = str(client_id or "").strip()
        self.api_key = str(api_key or "").strip()
        self.timeout = timeout
        self.logger = _get_logger()

        if not self.api_key:
            raise ValueError("Missing Ozon API key. Please provide a non-empty api_key.")
        if not self.client_id:
            raise ValueError("Missing Ozon client_id. Please provide a non-empty client_id.")
        if not self.base_url:
            raise ValueError("Missing Ozon base_url. Please provide a non-empty base_url.")

    def _headers(self) -> dict[str, str]:
        return {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = self._build_url(endpoint)

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            if not response.text.strip():
                return {"ok": True, "status_code": response.status_code}
            return response.json()
        except requests.RequestException as exc:
            self.logger.exception("Ozon API request failed for %s: %s", url, exc)
            return {
                "ok": False,
                "error": str(exc),
                "endpoint": endpoint,
            }
        except ValueError as exc:
            self.logger.exception("Failed to decode JSON response from %s: %s", url, exc)
            return {
                "ok": False,
                "error": "invalid_json_response",
                "endpoint": endpoint,
            }

    def create_product(self, payload: dict) -> dict:
        endpoint = ENDPOINTS["create_product"]
        return self._post(endpoint, payload)

    def update_product(self, payload: dict) -> dict:
        endpoint = ENDPOINTS["update_product"]
        return self._post(endpoint, payload)

    def get_product_info(self, product_id: str) -> dict:
        endpoint = ENDPOINTS["get_product_info"]
        payload = {"product_id": product_id}
        return self._post(endpoint, payload)
