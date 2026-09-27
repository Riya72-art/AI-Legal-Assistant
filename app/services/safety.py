"""
Very deliberately conservative danger-signal detection.

This is NOT a classifier that decides whether to help — Ask Nyaya always
answers. It only decides whether to also set `escalate=True` so the
frontend can surface the emergency banner / 112 call button alongside
the normal reply. Because a false negative here (missing real danger) is
much worse than a false positive (showing the banner when it wasn't
needed), the phrase list below is intentionally broad. Tune it with
input from an actual DV/crisis-response professional, not just engineers.
"""
import re

_DANGER_PATTERNS = [
    r"\bhe(\'s| is)? (here|outside|coming)\b",
    r"\bright now\b",
    r"\bcan\'?t breathe\b",
    r"\btrying to (kill|hurt) me\b",
    r"\bhas a (knife|gun|weapon)\b",
    r"\blocked me (in|out)\b",
    r"\bkids? (are|is) (alone|with him|in danger)\b",
    r"\bi\'?m scared he\'?ll kill\b",
    r"\bemergency\b",
    r"\bbleeding\b",
    r"\bhurt myself\b",
    r"\bkill myself\b",
    r"\bsuicid",
]

_compiled = [re.compile(p, re.IGNORECASE) for p in _DANGER_PATTERNS]


def detect_escalation(message: str) -> bool:
    return any(p.search(message) for p in _compiled)
