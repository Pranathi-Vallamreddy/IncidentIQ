"""Explanation orchestration: try Gemini, always fall back to deterministic.

The engine's structured output is the only input. Gemini is asked purely to
phrase it; if it is unavailable or returns anything malformed, the deterministic
explainer produces an identically-shaped result so the UI never breaks.
"""

from __future__ import annotations

from . import gemini
from .explainer import ExplainInput, build_prompt, explain_deterministic

_REQUIRED_KEYS = ("summary", "root_cause", "suggested_fixes")


def generate_explanation(inp: ExplainInput, use_ai: bool = True) -> tuple[str, dict]:
    """Return (source, explanation_dict). source is 'gemini' or 'deterministic'."""
    if use_ai and gemini.available():
        result = gemini.generate_json(build_prompt(inp))
        if _valid(result):
            fixes = result["suggested_fixes"]
            if isinstance(fixes, str):
                fixes = [fixes]
            return "gemini", {
                "summary": str(result["summary"]),
                "root_cause": str(result["root_cause"]),
                "suggested_fixes": [str(f) for f in fixes][:5],
            }
    return "deterministic", explain_deterministic(inp)


def _valid(result: dict | None) -> bool:
    return bool(result) and all(k in result for k in _REQUIRED_KEYS)
