from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from services.rate_limit import SimpleRateLimiter


class OzonApiError(RuntimeError):
    pass


class OzonClient:
    def __init__(
        self,
        client_id: str,
        api_key: str,
        base_url: str,
        shop_name: str,
        timeout_seconds: int,
        retry_attempts: int,
        retry_backoff_seconds: float,
        rate_limiter: SimpleRateLimiter,
        logger: logging.Logger,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.shop_name = shop_name
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self.rate_limiter = rate_limiter
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Client-Id": client_id,
                "Api-Key": api_key,
                "Content-Type": "application/json",
            }
        )

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                self.rate_limiter.acquire()
                response = self.session.post(url, json=payload, timeout=self.timeout_seconds)
                if response.status_code in (401, 403):
                    raise OzonApiError(f"Ozon auth failed for {path}: HTTP {response.status_code}")
                if response.status_code >= 400:
                    raise OzonApiError(
                        f"Ozon HTTP {response.status_code} for {path}: {response.text[:500]}"
                    )
                data = response.json()
                if not isinstance(data, dict):
                    raise OzonApiError(f"Ozon returned unexpected payload for {path}")
                if data.get("error"):
                    raise OzonApiError(f"Ozon API error for {path}: {data}")
                return data
            except (requests.RequestException, ValueError, OzonApiError) as exc:
                last_error = exc
                self.logger.warning("Ozon request failed %s attempt %s: %s", path, attempt, exc)
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))
        raise OzonApiError(f"Ozon request failed for {path}: {last_error}")

    def collect_recent_orders(self, lookback_days: int) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        date_from = now - timedelta(days=lookback_days)
        collected: dict[str, dict[str, Any]] = {}
        for fetcher in (self.get_fbs_postings, self.get_unfulfilled_postings):
            offset = 0
            while True:
                response = fetcher(date_from, now, limit=100, offset=offset)
                result = response.get("result") or {}
                postings = result.get("postings") or result.get("result") or []
                if not isinstance(postings, list) or not postings:
                    break
                for item in postings:
                    if not isinstance(item, dict):
                        continue
                    posting_number = str(item.get("posting_number") or "").strip()
                    if not posting_number:
                        continue
                    collected[posting_number] = self.normalize_order_item(self.enrich_order(item))
                if len(postings) < 100:
                    break
                offset += 100
        return list(collected.values())

    def get_awaiting_packaging_orders(self, lookback_days: int, limit: int = 20) -> list[dict[str, Any]]:
        orders = [
            item
            for item in self.collect_recent_orders(lookback_days)
            if str(item.get("status") or "").strip() == "awaiting_packaging"
        ]
        return orders[:limit]

    def get_recent_returns(self, limit: int = 20) -> list[dict[str, Any]]:
        search_limit = max(limit * 5, 100)
        collected: list[dict[str, Any]] = []
        seen: set[str] = set()
        last_id: int | str | None = None
        while len(collected) < search_limit:
            response = self.post(
                "/v1/returns/list",
                {"filter": {"return_schema": "FBS"}, "limit": min(100, search_limit), "last_id": last_id},
            )
            result = response.get("result") or response
            returns = result.get("returns") or result.get("items") or result.get("results") or []
            if not isinstance(returns, list) or not returns:
                break
            for item in returns:
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_fbs_return_item(item)
                key = str(normalized.get("return_number") or "").strip()
                if not key or key in seen:
                    continue
                seen.add(key)
                collected.append(normalized)
                if len(collected) >= search_limit:
                    break
            next_last_id = result.get("last_id")
            if next_last_id in (None, "", 0, "0") or not result.get("has_next"):
                break
            last_id = next_last_id
        for item in self.get_rfbs_returns(limit=search_limit):
            key = str(item.get("return_number") or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            collected.append(item)
            if len(collected) >= search_limit:
                break
        return self._sort_returns_by_created_desc(collected)[:limit]

    def get_rfbs_returns(self, limit: int = 20) -> list[dict[str, Any]]:
        returns: list[dict[str, Any]] = []
        last_id = 0
        while len(returns) < limit:
            data = self.post(
                "/v2/returns/rfbs/list",
                {"filter": {}, "limit": min(max(limit, 20), 100), "last_id": last_id},
            )
            raw_result = data.get("result") or data
            items = raw_result.get("returns") if isinstance(raw_result, dict) else raw_result
            has_next = bool(raw_result.get("has_next")) if isinstance(raw_result, dict) else False
            next_last_id = raw_result.get("last_id") if isinstance(raw_result, dict) else None
            if not isinstance(items, list) or not items:
                break
            for item in items:
                if not isinstance(item, dict):
                    continue
                returns.append(self._normalize_rfbs_return_item(item))
                if len(returns) >= limit:
                    break
            if not has_next or next_last_id in (None, "", 0, "0"):
                break
            last_id = int(next_last_id)
        return self._sort_returns_by_created_desc(returns)[:limit]

    def get_rfbs_cancellations(self, limit: int = 20) -> list[dict[str, Any]]:
        items = [item for item in self.get_rfbs_returns(limit=max(limit * 2, 20))
                 if str(item.get("return_type") or "").strip().lower() == "cancellation"]
        return items[:limit]

    def get_cancel_reason(self, posting_number: str) -> str | None:
        requests_by_path = (
            ("/v2/posting/fbs/cancel-reason/list", {"posting_number": posting_number}),
            (
                "/v1/posting/fbs/cancel-reason",
                {"related_posting_numbers": [posting_number]},
            ),
        )
        for path, payload in requests_by_path:
            try:
                data = self.post(path, payload)
            except OzonApiError:
                continue
            reason = self._extract_cancel_reason(data.get("result"))
            if reason:
                return reason
        return None

    def get_order_detail(self, posting_number: str) -> dict[str, Any]:
        data = self.post("/v3/posting/fbs/get", {"posting_number": posting_number})
        result = data.get("result")
        if not isinstance(result, dict):
            raise OzonApiError(f"Order detail invalid for {posting_number}")
        return result

    def get_fbs_postings(
        self, date_from: datetime, date_to: datetime, limit: int, offset: int
    ) -> dict[str, Any]:
        payload = {
            "dir": "ASC",
            "filter": {"since": self._ts(date_from), "to": self._ts(date_to)},
            "limit": limit,
            "offset": offset,
            "with": {"financial_data": True},
        }
        return self.post("/v3/posting/fbs/list", payload)

    def get_unfulfilled_postings(
        self, date_from: datetime, date_to: datetime, limit: int, offset: int
    ) -> dict[str, Any]:
        payload = {
            "dir": "ASC",
            "filter": {"cutoff_from": self._ts(date_from), "cutoff_to": self._ts(date_to)},
            "limit": limit,
            "offset": offset,
            "with": {"financial_data": True},
        }
        return self.post("/v3/posting/fbs/unfulfilled/list", payload)

    def enrich_order(self, order: dict[str, Any]) -> dict[str, Any]:
        posting_number = str(order.get("posting_number") or "").strip()
        if not posting_number or order.get("products"):
            return order
        try:
            detail = self.get_order_detail(posting_number)
        except OzonApiError as exc:
            self.logger.warning("Order detail fetch failed for %s: %s", posting_number, exc)
            return order
        merged = dict(order)
        merged.update(detail)
        return merged

    def normalize_order_item(self, order: dict[str, Any]) -> dict[str, Any]:
        products = order.get("products") or []
        first_product = products[0] if isinstance(products, list) and products else {}
        financial_data = order.get("financial_data") or {}
        financial_products = financial_data.get("products") or []
        first_financial = financial_products[0] if isinstance(financial_products, list) and financial_products else {}
        return {
            "shop_name": self.shop_name,
            "posting_number": self._txt(order.get("posting_number"), "N/A"),
            "status": self._txt(order.get("status"), "N/A"),
            "substatus": self._txt(order.get("substatus"), ""),
            "created_or_in_process_at": self._txt(order.get("in_process_at") or order.get("created_at"), "N/A"),
            "shipment_date": self._txt(order.get("shipment_date") or order.get("shipping_date"), "N/A"),
            "product_name": self._txt(first_product.get("name") or first_product.get("offer_name"), "N/A"),
            "offer_id": self._txt(first_product.get("offer_id") or first_product.get("article_code"), "N/A"),
            "quantity": self._int(first_product.get("quantity")) or 1,
            "price": self._money(first_financial) or self._money(first_product),
            "currency": self._txt(first_financial.get("currency_code") or first_product.get("currency_code"), "N/A"),
            "warehouse_name": self._txt((order.get("warehouse") or {}).get("name") or order.get("warehouse_name"), "N/A"),
            "delivery_service": self._txt((order.get("delivery_method") or {}).get("name") or order.get("provider"), "N/A"),
            "cancel_reason": self._txt(order.get("cancel_reason"), ""),
        }

    def _normalize_fbs_return_item(self, item: dict[str, Any]) -> dict[str, Any]:
        status = item.get("status")
        return {
            "shop_name": self.shop_name,
            "return_number": self._txt(item.get("return_number") or item.get("id") or item.get("return_id"), "N/A"),
            "return_type": self._txt(item.get("return_type"), "Refund"),
            "posting_number": self._txt(item.get("posting_number") or (item.get("posting") or {}).get("posting_number"), "N/A"),
            "status": self._txt((status.get("name") if isinstance(status, dict) else status), "N/A"),
            "reason": self._txt(item.get("return_reason_name") or item.get("reason"), "N/A"),
            "product_name": self._txt((item.get("product") or {}).get("name"), "N/A"),
            "price": self._money(item.get("money") or {}) or self._money(item.get("product") or {}),
            "currency": self._txt(((item.get("money") or {}).get("currency_code")), "N/A"),
            "created_date": self._txt(item.get("created_at") or item.get("created_date"), "N/A"),
            "changed_date": self._txt(item.get("updated_at") or item.get("changed_date"), "N/A"),
        }

    def _normalize_rfbs_return_item(self, item: dict[str, Any]) -> dict[str, Any]:
        status = item.get("state") or item.get("status")
        detail = item
        return {
            "shop_name": self.shop_name,
            "return_number": self._txt(detail.get("return_number") or item.get("return_number") or item.get("return_id"), "N/A"),
            "return_type": self._txt(detail.get("return_type") or item.get("return_type"), "Refund"),
            "posting_number": self._txt(detail.get("posting_number") or item.get("posting_number"), "N/A"),
            "status": self._txt((status.get("state_name") if isinstance(status, dict) else status), "N/A"),
            "reason": self._txt(detail.get("return_reason_name") or item.get("return_reason_name"), "N/A"),
            "product_name": self._txt((detail.get("product") or {}).get("name") or detail.get("product_name"), "N/A"),
            "price": self._money(detail.get("money") or {}) or self._money(detail.get("product") or {}),
            "currency": self._txt((detail.get("money") or {}).get("currency") or (detail.get("money") or {}).get("currency_code"), "N/A"),
            "created_date": self._txt(detail.get("created_at") or detail.get("created_date"), "N/A"),
            "changed_date": self._txt(detail.get("updated_at") or detail.get("changed_date"), "N/A"),
        }

    @staticmethod
    def _sort_returns_by_created_desc(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(item: dict[str, Any]) -> tuple[int, str]:
            created = str(item.get("created_date") or "").strip()
            return (1 if created else 0, created)

        return sorted(items, key=sort_key, reverse=True)

    @staticmethod
    def _extract_cancel_reason(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for key in ("cancel_reason", "reason", "name", "description"):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    return item.strip()
            nested = value.get("reasons")
            if isinstance(nested, list):
                for item in nested:
                    extracted = OzonClient._extract_cancel_reason(item)
                    if extracted:
                        return extracted
        if isinstance(value, list):
            for item in value:
                extracted = OzonClient._extract_cancel_reason(item)
                if extracted:
                    return extracted
        return None

    @staticmethod
    def _ts(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _txt(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _money(value: Any) -> float | None:
        if not isinstance(value, dict):
            return None
        for key in ("price", "client_price", "total_price", "amount", "value"):
            item = value.get(key)
            if item in (None, ""):
                continue
            try:
                return float(item)
            except (TypeError, ValueError):
                continue
        return None
