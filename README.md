# Nyaya Desk — Backend

FastAPI backend for the Nyaya Desk frontend. Guest-first: no endpoint
requires authentication, and nothing is written to a database — this
scaffold is file/memory-backed throughout, matching the frontend's
"no history by default" promise.

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Docs at `http://localhost:8000/docs` once running.

Optional: set `GROQ_API_KEY` to use Groq for grounded response writing in
`/api/ask`. It defaults to `openai/gpt-oss-120b`; override that with
`GROQ_MODEL`. `ANTHROPIC_API_KEY` remains supported as a fallback provider.
Without either key, the endpoint returns the matched knowledge-base content
directly.

The header language selector supports all 22 scheduled Indian languages plus
English. It controls the Ask response language, voice-input locale, document
locale, and the translated core navigation labels.

If Groq is unavailable, Ask Nyaya falls back to the curated knowledge base,
and common Hindi/Marathi interface labels use local translations. A valid key
is required for full page translation and fully generated multilingual replies.

Optional: set `GEMINI_API_KEY` to enable image analysis from the Attach image
button. Images are held in memory for the request and are not saved. Set
`GEMINI_MODEL` to override the default `gemini-2.0-flash` model.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ask` | Free-text question → grounded reply |
| POST | `/api/ask/image` | Image upload → Gemini visual analysis |
| POST | `/api/translate` | Translate visible website copy through Groq |
| POST | `/api/complaint/draft` | Structured form → complaint or legal-notice draft (`document_type`) |
| GET | `/api/helplines?state=` | National + optional state helplines |
| GET | `/api/laws?topic=&q=&act=` | Search the BNS / BNSS / IT Act glossary by section, text, or topic |
| GET | `/api/rights?q=` | Search the plain-language rights glossary |
| GET | `/api/healing/resources` | Principles, counselling contacts, community resources |
| GET | `/api/safety/directory?state=` | State/UT legal-aid, shelter-referral, and crisis-referral listings |
| POST | `/api/safety/panic-clear?session_id=` | Wipe server-side state for Quick Exit |
| GET | `/api/health` | Liveness check |

Full request/response shapes are in `app/models/schemas.py` and are
enforced by FastAPI/Pydantic — `/docs` gives you an interactive spec.

## Ask Nyaya architecture

This was the main design decision, so it's worth spelling out. Three
options exist for powering free-text legal Q&A; this scaffold implements
the third:

1. **Pure FAQ/rules match** — safest, but brittle against messy phrasing.
2. **Pure LLM** — flexible, but risks hallucinated legal specifics
   (wrong statute, wrong procedure) — bad on a safety product.
3. **Retrieval-grounded (implemented here)** — `app/services/retrieval.py`
   scores the user's message against a curated knowledge base
   (`app/data/ask_knowledge_base.json`). The top matches are the *only*
   material an LLM is allowed to draw from (`app/services/ask_service.py`,
   system prompt explicitly forbids adding facts not in the retrieved
  entries). If no `GROQ_API_KEY` or `ANTHROPIC_API_KEY` is set, or nothing matched
   confidently, the service falls back to returning the matched entry's
   vetted text directly — never a guess.

Retrieval is currently keyword/overlap-based (zero dependencies, zero
cost). If quality needs improve, swap `_score_entry` in `retrieval.py`
for an embeddings-based similarity call — nothing else in the pipeline
needs to change.

**The knowledge base is the safety boundary.** Every file in `app/data/`
is marked `_note: SAMPLE DATA` and must be reviewed by an actual legal
aid professional before this goes anywhere near real users — wrong
helpline numbers or statute references on a product like this cause
real harm, not just bad UX.

## Danger-signal escalation

`app/services/safety.py` runs on every `/api/ask` call, independent of
retrieval/LLM success, and sets `escalate: true` in the response when the
message contains signals of immediate danger (e.g. "he's outside right
now"). The frontend should surface the emergency banner / 112 button
when this is true, in addition to the normal reply — never instead of it.
The phrase list is a starting point; have a crisis-response professional
review and expand it, biased toward false positives over false negatives.

## Not yet built (natural next steps)

- **Auth + opt-in persistence.** Currently nothing survives a request.
  If you add "sign in to save your own notes," gate all writes behind
  authentication and make saving explicit per-item, not a default.
- **Session store swap.** `app/services/session.py` is in-memory and a
  placeholder — replace with Redis + short TTL before any endpoint
  actually writes to it.
- **Rate limiting** on `/api/ask` (cost + abuse control) once an LLM key
  is wired in.
- **i18n for `/api/rights` and the knowledge base** — `term_hindi` exists
  in the schema but content is English-first; Marathi isn't represented
  yet despite being offered as a language option in the frontend.
- **CORS origin lock-down** — `app/main.py` currently allows `*` for
  local dev convenience only.
