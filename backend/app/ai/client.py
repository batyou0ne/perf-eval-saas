from functools import lru_cache

from google import genai

from app.core.config import get_settings


@lru_cache
def get_gemini_client() -> genai.Client:
    """Built on first use, not at import.

    genai.Client raises when no API key is configured. Constructing it at module
    scope made the whole API un-importable without a key — the AI summary is one
    feature, so a missing key should break only that, not every endpoint.
    """
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)
