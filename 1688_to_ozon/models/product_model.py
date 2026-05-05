from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProductVariant:
    size: str = ""
    color: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductModel:
    source: str = ""
    product_url: str = ""
    title: str = ""
    price: str = ""
    images: list[str] = field(default_factory=list)
    description: str = ""
    variants: list[ProductVariant] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["variants"] = [variant.to_dict() for variant in self.variants]
        return payload
