"""OpenAI Responses API helpers for product translation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - depends on local environment
    OpenAI = Any  # type: ignore[misc,assignment]

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - depends on local environment
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_FILE)

class MissingOpenAIAPIKeyError(RuntimeError):
    """Raised when OPENAI_API_KEY is not configured."""


def _reload_env() -> None:
    if load_dotenv is not None:
        load_dotenv(dotenv_path=ENV_FILE, override=True)


def get_openai_model() -> str:
    _reload_env()
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


def get_openai_api_key() -> str:
    """Read the OpenAI API key from the environment."""
    _reload_env()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise MissingOpenAIAPIKeyError(
            "Missing OpenAI API key. Please set OPENAI_API_KEY in your environment or in the .env file."
        )
    return api_key


def get_openai_client() -> OpenAI:
    """Build an authenticated OpenAI client."""
    if OpenAI is Any:
        raise RuntimeError(
            "OpenAI Python SDK is not installed. Please install dependencies from requirements.txt."
        )
    return OpenAI(api_key=get_openai_api_key())


def extract_response_text(response: Any) -> str:
    """Extract text output from a Responses API payload."""
    output_text = getattr(response, "output_text", "")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunk for chunk in chunks if chunk).strip()
