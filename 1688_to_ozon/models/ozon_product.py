from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class OzonProduct:
    """Template-driven Ozon payload used by export and upload stages."""

    name: str = ""
    category: str = ""
    category_id: int | None = None
    template_name: str = ""
    row_data: dict[str, Any] = field(default_factory=dict)
    attributes: list[dict[str, Any]] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    variants: list[dict[str, Any]] = field(default_factory=list)
    supplier: str = ""
    source_url: str = ""
    missing_required_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OzonProduct":
        if not isinstance(data, dict):
            return cls()

        category_id = data.get("category_id")
        if category_id is not None:
            try:
                category_id = int(category_id)
            except (TypeError, ValueError):
                category_id = None

        return cls(
            name=str(data.get("name", "") or ""),
            category=str(data.get("category", "") or ""),
            category_id=category_id,
            template_name=str(data.get("template_name", "") or ""),
            row_data=dict(data.get("row_data", {}) or {}),
            attributes=list(data.get("attributes", []) or []),
            images=list(data.get("images", []) or []),
            variants=list(data.get("variants", []) or []),
            supplier=str(data.get("supplier", "") or ""),
            source_url=str(data.get("source_url", "") or ""),
            missing_required_fields=list(data.get("missing_required_fields", []) or []),
        )
