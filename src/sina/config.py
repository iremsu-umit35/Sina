"""Uygulama ayarlarını yönetecek modül."""

import os

from dotenv import load_dotenv

GEMINI_MODEL = "gemini-3.5-flash-lite"


def get_gemini_api_key() -> str:
    """Gemini API anahtarını environment variable'dan oku."""

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return api_key
