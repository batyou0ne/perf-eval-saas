from google import genai

from app.core.config import get_settings

settings = get_settings()

gemini_client = genai.Client(api_key=settings.gemini_api_key)
