"""Placeholder client for future external translation API integration."""

from __future__ import annotations

from dataclasses import dataclass

from translator.text_formatter import normalize_text


@dataclass(slots=True)
class TranslationRequest:
    """Simple request payload for future translator backends."""

    text: str
    source_lang: str = "en"
    target_lang: str = "ru"
    field_name: str = ""


@dataclass(slots=True)
class TranslationResult:
    """Normalized response payload shared by translator backends."""

    text: str
    translated: bool = False
    provider: str = "placeholder"


class TranslationApiClient:
    """Placeholder API client that keeps the current text unchanged."""

    provider_name = "placeholder"

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """Return normalized text until a real translation provider is added."""
        # TODO: replace this placeholder with a real provider implementation
        # such as OpenAI or Google Translate when API credentials/workflow exist.
        return TranslationResult(
            text=normalize_text(request.text),
            translated=False,
            provider=self.provider_name,
        )


DEFAULT_TRANSLATION_CLIENT = TranslationApiClient()


def translate_text(
    text: str,
    *,
    field_name: str = "",
    source_lang: str = "en",
    target_lang: str = "ru",
    client: TranslationApiClient | None = None,
) -> str:
    """Convenience wrapper for future API-backed translation calls."""
    request = TranslationRequest(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        field_name=field_name,
    )
    active_client = client or DEFAULT_TRANSLATION_CLIENT
    return active_client.translate(request).text
