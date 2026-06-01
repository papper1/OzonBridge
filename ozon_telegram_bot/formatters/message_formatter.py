from __future__ import annotations

from datetime import datetime
from typing import Any


class MessageFormatter:
    STATUS_LABELS = {
        "awaiting_registration": "Cho xac nhan",
        "awaiting_packaging": "Cho dong goi",
        "awaiting_deliver": "Cho ban giao van chuyen",
        "awaiting_delivery": "Cho ban giao van chuyen",
        "delivering": "Dang giao",
        "delivered": "Da giao",
        "cancelled": "Da huy",
        "arbitration": "Tranh chap",
        "unredeemed": "Khach khong nhan",
    }

    def format_help(self) -> str:
        return (
            "/status [shop_code] - Tong quan theo DB\n"
            "/order [shop_code] - Don awaiting_packaging tu DB\n"
            "/refund [shop_code] - Return/refund tu DB\n"
            "/cancel [shop_code] - Cancellation tu DB\n"
            "/order_now <shop_code> - Goi realtime Ozon\n"
            "/help - Danh sach lenh"
        )

    def format_status(self, shop_name: str, stats: dict[str, int]) -> str:
        return (
            f"Trang thai bot cho {shop_name}\n\n"
            f"Don cho dong goi: {stats.get('awaiting_packaging', 0)}\n"
            f"Don huy: {stats.get('cancelled', 0)}\n"
            f"Returns/Refunds: {stats.get('returns', 0)}\n"
            f"Thong bao da gui: {stats.get('notifications', 0)}"
        )

    def format_order(self, order: dict[str, Any]) -> str:
        return (
            "Don hang\n\n"
            f"Shop: {order.get('shop_name') or 'N/A'}\n"
            f"Posting: {order.get('posting_number') or 'N/A'}\n"
            f"Trang thai: {self._status(order.get('status'))}\n"
            f"San pham: {order.get('product_name') or 'N/A'}\n"
            f"So luong: {order.get('quantity') or 'N/A'}\n"
            f"Gia: {self._money(order.get('price'))} {order.get('currency') or 'N/A'}\n"
            f"Tao luc: {self._dt(order.get('created_or_in_process_at'))}\n"
            f"Giao luc: {self._dt(order.get('shipment_date'))}"
        )

    def format_return(self, item: dict[str, Any]) -> str:
        return (
            "Return/Refund\n\n"
            f"Shop: {item.get('shop_name') or 'N/A'}\n"
            f"Return: {item.get('return_number') or 'N/A'}\n"
            f"Loai: {item.get('return_type') or 'N/A'}\n"
            f"Posting: {item.get('posting_number') or 'N/A'}\n"
            f"Trang thai: {item.get('status') or 'N/A'}\n"
            f"Ly do: {item.get('reason') or 'N/A'}\n"
            f"Tao luc: {self._dt(item.get('created_date'))}\n"
            f"Cap nhat luc: {self._dt(item.get('changed_date'))}"
        )

    def format_cancelled_order(self, order: dict[str, Any], reason: str | None) -> str:
        return (
            "Yeu cau huy don\n\n"
            f"Shop: {order.get('shop_name') or 'N/A'}\n"
            f"Posting: {order.get('posting_number') or 'N/A'}\n"
            f"Trang thai: {self._status(order.get('status'))}\n"
            f"Ly do: {reason or 'N/A'}"
        )

    def format_lines(self, title: str, items: list[dict[str, Any]], renderer) -> list[str]:
        if not items:
            return [f"{title}\n\nKhong co du lieu."]
        return [renderer(item) for item in items]

    def format_error(self, title: str, detail: str) -> str:
        return f"{title}\n\n{detail[:3000]}"

    @staticmethod
    def _money(value: Any) -> str:
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "N/A"

    def _status(self, value: Any) -> str:
        if value is None:
            return "N/A"
        text = str(value).strip()
        return self.STATUS_LABELS.get(text, text or "N/A")

    @staticmethod
    def _dt(value: Any) -> str:
        if not value:
            return "N/A"
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return value
        return str(value)
