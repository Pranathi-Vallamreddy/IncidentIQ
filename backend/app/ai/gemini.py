"""Thin optional Gemini client (google-genai SDK).

Isolated so the rest of the app never imports the SDK directly. If the key or the
package is missing, or the API call fails, `generate_json` returns None and the
caller falls back to the deterministic explainer. Failures are logged at WARNING
so the reason is visible in server logs instead of being silently swallowed.
"""

from __future__ import annotations

import json
import logging

from ..config import settings

logger = logging.getLogger("incidentiq.ai")


def available() -> bool:
    return bool(settings.gemini_api_key)


def generate_json(prompt: str) -> dict | None:
    """Return parsed JSON from Gemini, or None on any failure (logged)."""
    if not available():
        return None
    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        text = (resp.text or "").strip()
        if not text:
            logger.warning(
                "Gemini (%s) returned an empty response; using deterministic fallback",
                settings.gemini_model,
            )
            return None
        return json.loads(text)
    except Exception as e:  # noqa: BLE001 - degrade gracefully, but log why
        logger.warning(
            "Gemini call failed (%s: %s); using deterministic fallback",
            type(e).__name__, e,
        )
        return None
