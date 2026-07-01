"""Thin optional Gemini client.

Isolated so the rest of the app never imports the SDK directly. If the key or the
package is missing, `available()` is False and callers fall back to the
deterministic explainer.
"""

from __future__ import annotations

import json

from ..config import settings

_MODEL = "gemini-1.5-flash"


def available() -> bool:
    return bool(settings.gemini_api_key)


def generate_json(prompt: str) -> dict | None:
    """Return parsed JSON from Gemini, or None on any failure."""
    if not available():
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(_MODEL)
        resp = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        text = (resp.text or "").strip()
        if not text:
            return None
        return json.loads(text)
    except Exception:
        # Any SDK/network/parse error degrades gracefully to deterministic mode.
        return None
