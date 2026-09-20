"""Gemini servisiyle kurulacak entegrasyondan sorumlu modül."""

from google import genai

from sina.config import GEMINI_MODEL, get_gemini_api_key


def _create_client() -> genai.Client:
    return genai.Client(api_key=get_gemini_api_key())


def generate_with_ai(prompt: str) -> str:
    """Hazır promptu Gemini'a gönderip üretilen metni döndür."""

    client = _create_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    if response.text is None or not response.text.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return response.text
