from dataclasses import asdict, dataclass, field
from typing import Any


CANONICAL_FIELDS = (
    "product_name",
    "brand",
    "model",
    "color",
    "size",
    "material",
    "style",
    "season",
    "fastener_type",
    "drawing",
    "model_features",
    "cut",
    "decorative_elements",
    "height_type",
    "sleeve_type",
    "collar",
    "purpose",
    "height",
    "lining_material",
    "ram",
    "storage",
    "cpu",
    "screen_size",
    "weight",
)


def _default_specs() -> dict[str, str]:
    """Keep legacy `specs` payload for compatibility with the old pipeline."""
    return {
        "ram": "",
        "storage": "",
        "cpu": "",
        "screen_size": "",
        "weight": "",
        "color": "",
        "size": "",
        "material": "",
    }


@dataclass
class NormalizedProduct:
    """Canonical internal product model shared across all templates."""

    source_url: str = ""
    title: str = ""
    product_name: str = ""
    brand: str = ""
    model: str = ""
    color: str = ""
    size: str = ""
    material: str = ""
    style: str = ""
    season: str = ""
    fastener_type: str = ""
    drawing: str = ""
    model_features: str = ""
    cut: str = ""
    decorative_elements: str = ""
    height_type: str = ""
    sleeve_type: str = ""
    collar: str = ""
    purpose: str = ""
    height: str = ""
    lining_material: str = ""
    ram: str = ""
    storage: str = ""
    cpu: str = ""
    screen_size: str = ""
    weight: str = ""
    category: str = ""
    specs: dict[str, Any] = field(default_factory=_default_specs)
    variants: list[dict[str, Any]] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    supplier: str = ""
    raw_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["specs"] = self.build_legacy_specs()
        return payload

    def build_legacy_specs(self) -> dict[str, Any]:
        """Expose canonical values under the older nested `specs` layout."""
        specs = _default_specs()
        specs.update(dict(self.specs or {}))
        for field_name in specs:
            value = getattr(self, field_name, "")
            if value not in (None, "", [], {}, ()):
                specs[field_name] = value
        return specs

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizedProduct":
        if not isinstance(data, dict):
            return cls()

        specs = _default_specs()
        specs.update(dict(data.get("specs", {}) or {}))

        canonical_values = {}
        for field_name in CANONICAL_FIELDS:
            direct_value = data.get(field_name)
            if direct_value in (None, ""):
                direct_value = specs.get(field_name, "")
            canonical_values[field_name] = str(direct_value or "")

        return cls(
            source_url=str(data.get("source_url", "") or ""),
            title=str(data.get("title", "") or ""),
            category=str(data.get("category", "") or ""),
            specs=specs,
            variants=list(data.get("variants", []) or []),
            images=list(data.get("images", []) or []),
            supplier=str(data.get("supplier", "") or ""),
            raw_attributes=dict(data.get("raw_attributes", {}) or {}),
            **canonical_values,
        )
