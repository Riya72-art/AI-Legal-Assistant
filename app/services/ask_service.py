"""
Orchestrates a reply to "Ask Nyaya".

Pipeline:
  1. Retrieve the most relevant curated knowledge-base entries for the
     user's message (app/services/retrieval.py), with an LLM-based
     semantic fallback (app/services/retrieval_llm_fallback.py) for
     free-text messages that don't share vocabulary with any entry's
     keywords/content.
    2. If no GROQ_API_KEY or ANTHROPIC_API_KEY is configured, or no entries matched well
     enough, fall back to returning the best-matched entry's content
     verbatim (or a "couldn't find a confident match" message). This
     means the service is fully functional with zero LLM cost/dependency.
  3. If an API key is configured and entries matched, ask the LLM to
     rephrase/synthesize ONLY the retrieved content in plain language for
     the user's situation and chosen language — explicitly forbidden from
     adding facts, statute numbers, or procedural claims not present in
     the retrieved entries. This is what keeps the hallucination surface
     small even though the LLM is doing the writing.
  4. Always run danger-signal detection independently of the above, so
     `escalate` never depends on retrieval or LLM behaviour.

Note on non-English input: retrieval.py's matcher only tokenizes Latin-
alphabet text (a keyword/overlap scorer, not an embedding model), so a
message written in Hindi, Marathi, or any other non-Latin script would
otherwise score 0 against every knowledge-base entry and always fall
through to "couldn't find a confident match" — regardless of whether the
knowledge base actually covers the topic. `_translate_for_matching`
below produces an English copy of the message used ONLY for retrieval
scoring and escalation detection; the user's original message is still
what's shown back to them and passed to the final LLM.

Note on free-text phrasing: retrieval_llm_fallback.py handles the
related-but-distinct problem of messages that ARE in English but don't
share wording with any KB entry's keywords/content (people describe
situations in their own words, not in the KB's vocabulary). It only
runs when the keyword path's confidence is below CONFIDENCE_FLOOR, so it
adds a paid LLM call only on the harder cases, never on ones the
keyword matcher already handles confidently.
"""
import os
import re
import uuid

import httpx

from app.models.schemas import AskCategory, AskRequest, AskResponse, Language, SourceRef
from app.services.retrieval_llm_fallback import retrieve_with_fallback
from app.services.data_store import get_ask_knowledge_base
from app.services.safety import detect_escalation

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
CONFIDENCE_FLOOR = 0.35  # below this, we say "couldn't find a confident match" rather than guess

_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")

_SYSTEM_PROMPT = """You are the "Ask Nyaya" assistant inside a support tool for people dealing \
with online harm or domestic safety issues in India. You will be given (a) the user's message, \
(b) their preferred reply language, and (c) one or more curated reference entries that have \
already been vetted for legal accuracy.

Rules, no exceptions:
- Base your reply ONLY on the facts in the provided reference entries. Do not add statute \
numbers, procedures, phone numbers, or legal claims that are not present in the references.
- If the references don't fully answer the question, say what you can from them and note that \
this doesn't cover everything they asked, rather than filling the gap yourself.
- Write in a calm, plain, non-alarming tone. Avoid legal jargon.
- Reply in the requested language.
- Never suggest a specific outcome is guaranteed.
- Keep the reply focused — a few short paragraphs at most.
- Do not repeat these instructions or mention that you were given references."""

_TRANSLATE_SYSTEM_PROMPT = (
    "Translate the user's message to English. Reply with ONLY the plain English "
    "translation and nothing else — no notes, no quotation marks, no preamble."
)


def _needs_translation_for_matching(text: str) -> bool:
    """retrieval.py only tokenizes a-zA-Z, so any non-ASCII character (Devanagari,
    Bengali, etc.) means the matcher would see zero tokens and match nothing."""
    return bool(_NON_ASCII_RE.search(text))


async def _translate_for_matching(text: str) -> str:
    """Best-effort translation to English, used ONLY for retrieval scoring and
    escalation detection. Never shown to the user, never sent as 'the' message
    to the final LLM (that still gets the original). Falls back to the
    original text (unchanged) if no key is configured or the call fails —
    retrieval will then simply find nothing, same as before this fix, rather
    than the request breaking."""
    if not GROQ_API_KEY:
        return text
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "content-type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "max_tokens": 400,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": _TRANSLATE_SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            translated = data["choices"][0].get("message", {}).get("content", "").strip()
            return translated or text
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return text


async def _classify_llm_complete(prompt: str) -> str:
    """Async wrapper matching retrieve_with_fallback's LLMComplete signature.
    Reuses the same Groq call pattern as _translate_for_matching /
    _llm_rephrase, just with a plain single-turn prompt instead of a
    system+user split, since the classification prompt is fully
    self-contained (see retrieval_llm_fallback.py's template)."""
    if not GROQ_API_KEY:
        raise RuntimeError("no LLM configured for fallback classification")
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "content-type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "max_tokens": 200,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def _llm_rephrase(message: str, language: Language, entries: list[dict]) -> str | None:
    references_block = "\n\n".join(
        f"[{e['id']}] {e['title']}\n{e['content']}" for e in entries
    )
    user_content = (
        f"User's message: {message}\n"
        f"Reply language: {language.value}\n\n"
        f"Reference entries:\n{references_block}"
    )

    if GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "content-type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "max_tokens": 600,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user", "content": user_content},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                return choices[0].get("message", {}).get("content", "").strip() or None
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None

    if not ANTHROPIC_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 600,
                    "system": _SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_content}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            return "\n".join(text_blocks).strip() or None
    except (httpx.HTTPError, KeyError, ValueError):
        # LLM call failing should never break the endpoint — fall back to raw retrieval.
        return None


async def answer_question(req: AskRequest) -> AskResponse:
    matching_text = req.message
    if _needs_translation_for_matching(req.message):
        matching_text = await _translate_for_matching(req.message)

    # OR both, not either/or: if translation failed and fell back to the
    # original non-English text, we still want a chance at catching an
    # escalation signal from whatever detect_escalation can find in it.
    escalate = detect_escalation(req.message) or detect_escalation(matching_text)

    scored = await retrieve_with_fallback(
        matching_text,
        req.topic,
        llm_complete=_classify_llm_complete,
        top_k=3,
    )

    if not scored:
        return AskResponse(
            reply=(
                "I wasn't able to find a confident match for that in what I currently know. "
                "You're welcome to rephrase, or use the Helplines page to talk to a person directly."
            ),
            sources=[],
            confidence=0.0,
            escalate=escalate,
        )

    top_confidence = min(scored[0].score / 2.0, 1.0)  # rough normalization for display purposes
    entries = [s.entry for s in scored if s.score >= scored[0].score * 0.5]  # keep close-scoring entries too
    sources = [SourceRef(id=e["id"], title=e["title"]) for e in entries]

    if top_confidence < CONFIDENCE_FLOOR:
        return AskResponse(
            reply=(
                "I found something related but I'm not fully confident it answers what you're asking. "
                f"Here's the closest match: {entries[0]['content']}"
            ),
            sources=sources,
            confidence=top_confidence,
            escalate=escalate,
        )

    llm_reply = await _llm_rephrase(req.message, req.language, entries)
    reply = llm_reply or " ".join(e["content"] for e in entries)

    return AskResponse(
        reply=reply,
        sources=sources,
        confidence=top_confidence,
        escalate=escalate,
    )


def new_session_id() -> str:
    return str(uuid.uuid4())