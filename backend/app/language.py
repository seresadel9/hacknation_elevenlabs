"""Deterministic text heuristics used when no language model is configured (the labelled demo fallback).

Small, transparent rules beat an opaque guess: every classification here can be explained to the expert.
"""

from __future__ import annotations

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“€])")

UNCERTAINTY_CUES = (
    "not sure",
    "i think",
    "maybe",
    "probably",
    "honestly",
    "don't know",
    "do not know",
    "i guess",
    "not certain",
    "unsure",
    "might be",
    "no idea",
    "depends, i",
    "i believe",
)

_CUES: dict[str, tuple[str, ...]] = {
    "never": ("never", "don't ", "do not ", "must not", "mustn't", "under no", "no case"),
    "escalation": (
        "escalat",
        "controller",
        "ask finance",
        "check with",
        "ask someone",
        "second signature",
        "send it back",
        "goes to",
        "go to the",
        "call-back",
        "calls the supplier",
        "ask ",
    ),
    "threshold": (
        "€",
        "%",
        " per item",
        " net",
        " gross",
        "above",
        "over ",
        "under ",
        "below",
        "up to",
        "more than",
        "less than",
        "whichever",
    ),
    "exception": (
        "except",
        "unless",
        "every december",
        "only ",
        "not only",
        "special",
        "behave differently",
        "year-end",
        "re-sends",
        "always",
    ),
    "why": (
        "because",
        "since ",
        "so that",
        "that is the",
        "that's the",
        "reason",
        "goes on the balance",
        "allows",
        "is expected",
        "red flag",
    ),
    "change_condition": ("if ", "only release", "after ", "until", "would make", "otherwise", "above that"),
}

_PRONOUNS = [
    (r"\bI'm\b", "you're"),
    (r"\bI'd\b", "you'd"),
    (r"\bI've\b", "you've"),
    (r"\bI'll\b", "you'll"),
    (r"\bI\b", "you"),
    (r"\bmy\b", "your"),
    (r"\bMy\b", "Your"),
    (r"\bme\b", "you"),
    (r"\bmyself\b", "yourself"),
]


def split_sentences(text: str) -> list[str]:
    text = " ".join(text.strip().split())
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def is_uncertain(sentence: str) -> bool:
    s = sentence.lower().strip()
    if s.startswith(("if ", "when ", "whenever ")):
        return False  # a conditional rule ("If I'm unsure…, I ask Finance") is guidance, not a hedge
    return any(cue in s for cue in UNCERTAINTY_CUES)


def detect_gap_types(text: str) -> set[str]:
    """Which knowledge gaps does a statement plausibly cover?"""
    s = " " + text.lower() + " "
    found = {gap for gap, cues in _CUES.items() if any(c in s for c in cues)}
    # A threshold is only "answered" when an explicit amount AND a scope are given — "over five thousand"
    # still leaves per-item vs per-invoice and net vs gross open.
    if "threshold" in found:
        has_amount = bool(re.search(r"(€\s?\d|\d[\d.,]*\s?(€|%|eur))", s))
        has_scope = any(k in s for k in (" per item", " per invoice", " net", " gross", " total", "whichever"))
        if not (has_amount and has_scope):
            found.discard("threshold")
    return found


def classify_sentence(sentence: str) -> str:
    """Map a debrief sentence to a skill-card field."""
    if is_uncertain(sentence):
        return "uncertain"
    gaps = detect_gap_types(sentence)
    s = sentence.lower()
    if "never" in gaps or s.startswith(("don't", "do not", "never")):
        return "never"
    if (
        "threshold" in gaps
        or re.search(r"€\s?\d|\d\s?%", s)
        or any(k in s for k in ("per item", "net of", "gross of", "whichever is higher"))
    ):
        return "threshold"
    if "escalation" in gaps:
        return "escalation"
    if "exception" in gaps:
        return "exception"
    if "why" in gaps:
        return "why"
    return "how"


def to_apprentice_voice(sentence: str) -> str:
    """Restate an expert's first-person sentence as the apprentice would repeat it back."""
    out = sentence.strip()
    for pattern, repl in _PRONOUNS:
        out = re.sub(pattern, repl, out)
    out = re.sub(r"^Honestly,?\s*", "", out)
    if out and out[0].islower():
        out = out[0].upper() + out[1:]
    return out


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z€][a-zA-Z0-9€,.%-]+", text.lower())
    stop = {
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "what",
        "when",
        "should",
        "would",
        "have",
        "from",
        "into",
        "your",
        "about",
        "does",
        "there",
        "they",
        "then",
        "than",
        "which",
        "it's",
        "is",
        "are",
        "was",
        "how",
        "why",
        "can",
        "you",
        "do",
        "i",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "it",
        "be",
        "or",
        "if",
        "at",
        "as",
    }
    return {w.strip(".,") for w in words if w.strip(".,") not in stop and len(w.strip(".,")) > 2}


def fmt_clock(t_s: float) -> str:
    t = max(0, int(round(t_s)))
    return f"{t // 60:02d}:{t % 60:02d}"
