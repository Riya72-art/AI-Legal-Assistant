"""
Retrieval over the curated knowledge base for "Ask Nyaya".

This is deliberately simple (keyword/overlap scoring) rather than an
embedding-based semantic search, so the service has zero external
dependencies and zero cost with no LLM configured at all. If quality
becomes a problem, the natural upgrade is to swap `score_entry` for a
call to an embeddings API and compare cosine similarity — the rest of
the pipeline (top-k selection, grounding the LLM only in matched
entries) doesn't need to change.
"""
import re
from dataclasses import dataclass

from app.services.data_store import get_ask_knowledge_base

_WORD_RE = re.compile(r"[a-zA-Z']+")

# Small hand-picked suffix list — folds common inflections ("controlling"
# -> "control", "isolated" -> "isolate", "messages" -> "message") without
# pulling in a full stemming library. It's a heuristic, not a real
# linguistic stemmer, but it's applied identically to the query and the
# knowledge base, so it stays internally consistent. If this ever needs
# to get sharper, swap it for nltk's PorterStemmer/SnowballStemmer.
_SUFFIXES = ("'s", "ies", "ing", "edly", "ed", "es", "ly", "s")


def _stem(word: str) -> str:
    w = word.lower()
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def _tokenize(text: str) -> set[str]:
    return {_stem(w) for w in _WORD_RE.findall(text) if len(w) > 2}


@dataclass
class ScoredEntry:
    entry: dict
    score: float


def _keyword_phrase_hits(query_tokens: set[str], keywords: list[str]) -> int:
    """Count matched *keyword phrases*, requiring every significant word in
    a multi-word phrase to be present — not just one word from it.

    This is the core fix: the old version flattened phrases like "won't
    stop messaging" into a bag of words {won't, stop, messaging} and
    counted a match if the message contained the single common word
    "stop" for any reason at all (e.g. "...convinced her to stop seeing
    them..."), which is how a domestic-abuse message ended up scoring as
    cyberstalking. Requiring the whole phrase's tokens to be present stops
    a single generic word from triggering an unrelated topic.
    """
    hits = 0
    for phrase in keywords:
        phrase_tokens = _tokenize(phrase)
        if not phrase_tokens:
            continue
        if phrase_tokens.issubset(query_tokens):
            hits += 1
    return hits


def _score_entry(query_tokens: set[str], entry: dict) -> float:
    content_tokens = _tokenize(" ".join([entry.get("title", ""), entry.get("content", "")]))
    overlap_score = 0.0
    if content_tokens and query_tokens:
        overlap = query_tokens & content_tokens
        overlap_score = len(overlap) / len(query_tokens)

    keyword_hits = _keyword_phrase_hits(query_tokens, entry.get("keywords", []))
    return overlap_score + 0.9 * keyword_hits


def retrieve(message: str, topic: str | None, top_k: int = 3) -> list[ScoredEntry]:
    """Return up to top_k knowledge-base entries relevant to the message,
    highest score first. An empty list means no confident match."""
    kb = get_ask_knowledge_base()["entries"]
    query_tokens = _tokenize(message)

    def score_all(candidates, require_positive=True):
        out = []
        for entry in candidates:
            score = _score_entry(query_tokens, entry)
            if score > 0 or not require_positive:
                out.append(ScoredEntry(entry=entry, score=score))
        out.sort(key=lambda s: s.score, reverse=True)
        return out

    # A topic chip is an explicit signal from the user — trust it over
    # ambiguous keyword overlap. If they picked "Domestic cruelty", never
    # let a cyberstalking entry outrank it just because of shared common
    # words; only look inside that topic. `require_positive=False` here
    # means: even if the message has weak textual overlap with that
    # topic's entry, still surface it — the topic choice itself is
    # evidence enough. (Confidence scoring downstream still reflects how
    # weak that overlap was, so the reply stays honest about it.)
    if topic:
        in_topic = [e for e in kb if e.get("topic", "").lower() == topic.lower()]
        if in_topic:
            return score_all(in_topic, require_positive=False)[:top_k]

    return score_all(kb)[:top_k]