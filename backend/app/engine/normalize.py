"""Normalization: mask variable tokens so templates stay stable.

"connection pool exhausted for db-7 after 1423ms" and
"connection pool exhausted for db-3 after  88ms" both normalise to
"connection pool exhausted for db-<NUM> after <DUR>", which is what lets the
template miner collapse them into one cluster.

Masking is a fixed, ordered sequence of regex passes; specific patterns
(UUID, IP, email, URL, duration) run before the generic number pass so they are
not shredded into pieces.
"""

from __future__ import annotations

import re

# Order matters: earlier rules win over later ones.
_MASKS: list[tuple[re.Pattern, str]] = [
    # UUID
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    # ISO-ish timestamp embedded mid-message
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"
                r"(?:Z|[+-]\d{2}:?\d{2})?\b"), "<TS>"),
    # email
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL>"),
    # url
    (re.compile(r"\bhttps?://[^\s\"']+"), "<URL>"),
    # ip address with optional port
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<IP>"),
    # duration: 1423ms, 4.5s, 2m, 300us, 1.2h
    (re.compile(r"\b\d+(?:\.\d+)?\s?(?:ns|us|ms|s|m|h)\b"), "<DUR>"),
    # size: 12MB, 4.5GiB, 900kb
    (re.compile(r"\b\d+(?:\.\d+)?\s?(?:[kKmMgGtT]i?[bB])\b"), "<SIZE>"),
    # hex id: 0xdeadbeef or long bare hex runs
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r"\b[0-9a-fA-F]{12,}\b"), "<HEX>"),
    # filesystem path
    (re.compile(r"(?:/[\w.\-]+){2,}/?"), "<PATH>"),
    # quoted string
    (re.compile(r"\"[^\"]*\"|'[^']*'"), "<STR>"),
    # percentage
    (re.compile(r"\b\d+(?:\.\d+)?%"), "<PCT>"),
    # bare numbers (ints, floats, signed) - last, so it doesn't eat the above
    (re.compile(r"(?<![\w<])[+-]?\d+(?:\.\d+)?(?![\w>])"), "<NUM>"),
]

_WS = re.compile(r"\s+")


def normalize_message(message: str) -> str:
    """Return the message with all variable tokens masked to sentinels."""
    text = message
    for pattern, repl in _MASKS:
        text = pattern.sub(repl, text)
    return _WS.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    """Split a (already normalised) string into template tokens."""
    return text.split()


def masked_tokens(message: str) -> list[str]:
    """Convenience: normalise then tokenize."""
    return tokenize(normalize_message(message))
