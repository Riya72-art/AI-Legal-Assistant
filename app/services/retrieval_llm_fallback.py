"""
LLM-based semantic fallback for retrieval.py

Add this alongside the existing keyword/phrase retrieval, to run only
when the top keyword-matched score comes in under CONFIDENCE_FLOOR.
Rather than standing up a separate embeddings pipeline, this reuses the
LLM call you're already making (see test_groq.py) to classify free-text
stories against the KB by meaning, not exact wording.

Design:
- Keyword retrieval stays the primary, fast, free path for anything it's
  already confident about — this fallback only runs on the harder cases.
- The LLM is given ONLY entry ids + titles + one-line summaries, and is
  never asked to write freeform answers here — so it can only point at
  an existing KB entry (or say "none fit"), it can't hallucinate content
  that isn't in your knowledge base. That constraint is what keeps this
  safe to use for something that governs what the LLM later gets
  grounded in.
- Confidence from the LLM is a self-reported float; treat it with the
  same skepticism your CONFIDENCE_FLOOR already applies to keyword
  scores. This is a heuristic upgrade, not a guarantee.
"""
import json
import logging
from typing import Awaitable, Callable, Optional

from app.services.retrieval import ScoredEntry, retrieve  # your existing module
from app.services.data_store import get_ask_knowledge_base

logger = logging.getLogger(__name__)

# Wire this up to whatever your actual Groq/Anthropic client call looks
# like. It must be an async function that takes a prompt string and
# returns the raw text completion — this mirrors _llm_rephrase's own
# httpx.AsyncClient calls in ask_service.py, since that's already async
# throughout and a sync call here would just return an unawaited
# coroutine rather than actual text.
LLMComplete = Callable[[str], Awaitable[str]]

_CLASSIFY_PROMPT_TEMPLATE = """You are matching a person's free-text description of a legal/safety situation to the single best-fitting entry in a fixed list below. Only choose from this list — never invent an entry.

Entries:
{entries_block}

Person's message:
\"\"\"{message}\"\"\"

Respond with ONLY a JSON object, no other text, no markdown fences:
{{"best_match_id": "<id from the list above, or null if nothing genuinely fits>", "confidence": <float 0.0-1.0>, "reason": "<one short sentence>"}}
"""


def _build_entries_block(kb_entries: list[dict]) -> str:
    lines = []
    for e in kb_entries:
        # title + a truncated slice of content as a cheap one-line summary,
        # so the prompt stays small even as the KB grows
        summary = e.get("content", "")[:160].rsplit(" ", 1)[0]
        lines.append(f'- id="{e["id"]}" title="{e.get("title", "")}" summary="{summary}..."')
    return "\n".join(lines)


def _parse_llm_json(raw: str) -> Optional[dict]:
    """LLMs sometimes wrap JSON in prose or code fences despite instructions —
    strip that defensively rather than trusting the prompt alone."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("LLM fallback classifier returned non-JSON: %r", raw[:200])
        return None


async def llm_fallback_classify(
    message: str,
    llm_complete: LLMComplete,
    kb_entries: Optional[list[dict]] = None,
) -> Optional[ScoredEntry]:
    """Ask the LLM to pick the best-matching KB entry by meaning rather
    than shared words. Returns None if the LLM found nothing confident,
    or if its response couldn't be parsed/validated — callers should
    treat None exactly like "no match" from the keyword path."""
    kb_entries = kb_entries if kb_entries is not None else get_ask_knowledge_base()["entries"]
    entries_by_id = {e["id"]: e for e in kb_entries}

    prompt = _CLASSIFY_PROMPT_TEMPLATE.format(
        entries_block=_build_entries_block(kb_entries),
        message=message.replace('"""', "'"),  # defuse accidental prompt-breaking triple-quotes
    )

    try:
        raw = await llm_complete(prompt)
    except Exception:
        logger.exception("LLM fallback classify call failed")
        return None

    parsed = _parse_llm_json(raw)
    if not parsed:
        return None

    match_id = parsed.get("best_match_id")
    confidence = parsed.get("confidence", 0.0)

    if not match_id or match_id not in entries_by_id:
        return None
    if not isinstance(confidence, (int, float)):
        return None

    # scaled *2.0 so this lines up with your existing `score / 2.0`
    # normalization in ask.py's top_confidence calculation — keeps both
    # paths on the same 0-1 scale downstream without touching ask.py.
    return ScoredEntry(entry=entries_by_id[match_id], score=float(confidence) * 2.0)


async def retrieve_with_fallback(
    message: str,
    topic: Optional[str],
    llm_complete: LLMComplete,
    top_k: int = 3,
    confidence_floor: float = 0.35,
) -> list[ScoredEntry]:
    """Drop-in replacement for retrieval.retrieve() that adds the LLM
    fallback only when the keyword path isn't confident. Keyword path
    stays first — fast, free, deterministic — and only escalates to a
    paid LLM call on the harder, free-form cases. `retrieve()` itself
    stays synchronous (it's pure in-memory scoring, no I/O), only the
    fallback branch needs to be awaited."""
    keyword_results = retrieve(message, topic, top_k=top_k)

    top_confidence = min(keyword_results[0].score / 2.0, 1.0) if keyword_results else 0.0
    if top_confidence >= confidence_floor:
        return keyword_results

    fallback = await llm_fallback_classify(message, llm_complete)
    if fallback is None:
        # nothing better found — surface the honest low-confidence
        # keyword result as before, rather than forcing a match
        return keyword_results

    # Fallback entry goes first; keep any keyword hits behind it in case
    # your prompt/UI wants to show "you might also mean" secondary results
    others = [r for r in keyword_results if r.entry["id"] != fallback.entry["id"]]
    return [fallback, *others][:top_k]