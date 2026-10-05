"""Deterministic customer message quality checks, preserving original text."""
from __future__ import annotations
import re

JUNK_PATTERNS = (re.compile(r"\b(?:ivr|transcript)\b.*\b(?:failed|error|unavailable|technical issue)\b", re.I),
                 re.compile(r"^(?:[\[<])?\s*(?:no input|silence|unintelligible|call disconnected|ivr error)\b", re.I))

def classify_message(message: str | None, channel: str | None = None) -> tuple[str, str]:
    text = (message or "").strip()
    if not text:
        return "degraded", "empty_message"
    for pattern in JUNK_PATTERNS:
        if pattern.search(text):
            return "degraded", "known_ivr_or_transcript_marker"
    if len(text) < 3 or not re.search(r"[A-Za-z0-9]", text):
        return "degraded", "insufficient_text"
    if len(text) >= 12 and len(set(text.casefold().replace(" ", ""))) <= 2:
        return "degraded", "repetitive_text"
    return "usable", ""
