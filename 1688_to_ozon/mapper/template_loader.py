"""Load Ozon Excel template configs from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import TEMPLATES_DIR


def resolve_template_dir() -> Path:
    """Locate the template directory in source and packaged builds."""
    module_path = Path(__file__).resolve()
    candidates = (
        TEMPLATES_DIR,
        module_path.parent.parent / "templates",
        module_path.parent.parent / "1688_to_ozon" / "templates",
        module_path.parents[2] / "1688_to_ozon" / "templates",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_template(template_name: str) -> dict[str, Any]:
    """Load one template config by name, with generic fallback."""
    template_dir = resolve_template_dir()
    normalized_name = str(template_name or "generic").strip().lower() or "generic"
    template_path = template_dir / f"{normalized_name}.json"
    if not template_path.exists():
        template_path = template_dir / "generic.json"

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)
