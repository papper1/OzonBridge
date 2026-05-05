import json
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: str | Path) -> None:
    """Create the parent directory for a file path if needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)


def save_json(data: Any, path: str | Path) -> str:
    """Save Python data to a JSON file using UTF-8."""
    file_path = Path(path)
    try:
        ensure_parent_dir(file_path)
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(file_path)
    except OSError as exc:
        raise IOError(f"Failed to save JSON to {file_path}: {exc}") from exc


def load_json(path: str | Path):
    """Load JSON data from a UTF-8 file."""
    file_path = Path(path)
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"JSON file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in file {file_path}: {exc}") from exc
    except OSError as exc:
        raise IOError(f"Failed to read JSON file {file_path}: {exc}") from exc


def save_text(text: str, path: str | Path) -> str:
    """Save text content to a UTF-8 file."""
    file_path = Path(path)
    try:
        ensure_parent_dir(file_path)
        file_path.write_text(str(text), encoding="utf-8")
        return str(file_path)
    except OSError as exc:
        raise IOError(f"Failed to save text to {file_path}: {exc}") from exc


def load_text(path: str | Path) -> str:
    """Load text content from a UTF-8 file."""
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Text file not found: {file_path}") from exc
    except OSError as exc:
        raise IOError(f"Failed to read text file {file_path}: {exc}") from exc
