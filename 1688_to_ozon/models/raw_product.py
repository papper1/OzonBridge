from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RawProduct:
    product_url: str = ""
    url: str = ""
    title: str = ""
    price: str = ""
    images: list[str] = field(default_factory=list)
    description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    options: list[dict[str, Any]] = field(default_factory=list)
    variants: list[dict[str, Any]] = field(default_factory=list)
    sales: str = ""
    supplier: str = ""
    shop_name: str = ""
    sku: dict[str, Any] = field(default_factory=dict)
    source: str = "1688"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RawProduct":
        if not isinstance(data, dict):
            return cls()

        return cls(
            product_url=str(data.get("product_url", "") or ""),
            url=str(data.get("url", "") or ""),
            title=str(data.get("title", "") or ""),
            price=str(data.get("price", "") or ""),
            images=list(data.get("images", []) or []),
            description=str(data.get("description", "") or ""),
            attributes=dict(data.get("attributes", {}) or {}),
            options=list(data.get("options", []) or []),
            variants=list(data.get("variants", []) or []),
            sales=str(data.get("sales", "") or ""),
            supplier=str(data.get("supplier", "") or ""),
            shop_name=str(data.get("shop_name", "") or ""),
            sku=dict(data.get("sku", {}) or {}),
            source=str(data.get("source", "1688") or "1688"),
        )
