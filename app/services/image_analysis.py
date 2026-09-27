"""Gemini-backed vision, non-persistent image analysis for uploaded evidence."""
import asyncio
import base64
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# "gemini-flash-latest" always points at Google's current GA Flash model,
# so this doesn't need to be hand-updated every time a model is retired.
GEMINI_VISION_MODEL = os.environ.get("GEMINI_VISION_MODEL", "gemini-flash-latest")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _strip_markdown(text: str) -> str:
    """Safety net: remove Markdown syntax in case the model uses it despite
    being told not to. The frontend renders this as plain text, so headers,
    bold markers, and asterisk bullets would otherwise show up literally."""
    text = re.sub(r"^#{1,6}\s*(.+)$", r"\1:", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"^\s*[\*\-]\s+", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def analyze_image(image: bytes, media_type: str, language: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured on the backend.")

    prompt = (
        "You are assisting a legal-support tool. Describe only what is visibly present in this image. "
        "Transcribe readable text exactly when possible, identify dates, names, links, usernames, "
        "or threats that may help the user preserve evidence, and clearly label anything uncertain. "
        "If the positioning of people in the image could reasonably suggest a physical "
        "confrontation, restraint, defensiveness, or one person reacting to another (for "
        "example, a hand raised toward someone, or someone flinching or shielding themselves), "
        "say so as part of what's visible \u2014 using hedged language like 'the positioning could "
        "suggest...' or 'appears consistent with...' rather than either a firm claim or silence. "
        "Noting an uncertain-but-visible dynamic is more useful here than omitting it because "
        "you aren't fully sure. "
        "Do NOT identify who any specific real person is, guess their relationship, decide who is at "
        "fault, state or imply criminal or legal conclusions, or invent details that aren't visible. "
        "Write in plain, natural sentences and short paragraphs, the way you would explain it to someone "
        "out loud. Do NOT use Markdown formatting of any kind \u2014 no '#' headings, no '**bold**', no "
        "asterisk or dash bullet lists. If you need to list several things, write them as a normal "
        "sentence or on separate lines with plain text only. "
        f"Reply in {language}. Keep the response concise and practical."
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": media_type,
                            "data": base64.b64encode(image).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 800,
        },
    }

    url = f"{GEMINI_BASE_URL}/{GEMINI_VISION_MODEL}:generateContent"

    max_attempts = 3
    last_error: httpx.HTTPStatusError | None = None
    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(max_attempts):
            try:
                response = await client.post(
                    url,
                    params={"key": GEMINI_API_KEY},
                    json=payload,
                )
                response.raise_for_status()
                last_error = None
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                is_overloaded = exc.response.status_code == 503
                if is_overloaded and attempt < max_attempts - 1:
                    logger.warning(
                        "Gemini vision overloaded (attempt %s/%s), retrying...",
                        attempt + 1, max_attempts,
                    )
                    await asyncio.sleep(2 * (attempt + 1))  # 2s, then 4s
                    continue
                logger.error("Gemini vision HTTP %s: %s", exc.response.status_code, exc.response.text)
                if is_overloaded:
                    raise RuntimeError(
                        "Gemini's image analysis service is experiencing high demand right now. "
                        "Please try uploading the image again in a moment."
                    ) from exc
                raise RuntimeError(
                    f"Gemini vision request failed ({exc.response.status_code}): {exc.response.text[:300]}"
                ) from exc
            except httpx.TimeoutException as exc:
                logger.error("Gemini vision request timed out")
                raise RuntimeError("Gemini vision request timed out after 45s.") from exc

        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        feedback = data.get("promptFeedback", {})
        logger.warning("Gemini vision returned no candidates: %s", data)
        if feedback.get("blockReason"):
            raise ValueError(f"Image analysis was blocked ({feedback['blockReason']}).")
        raise ValueError("Gemini vision returned no analysis.")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason == "SAFETY":
        logger.warning("Gemini vision response blocked by safety filters: %s", candidate)
        raise ValueError(
            "This image couldn't be analyzed automatically \u2014 that's usually because the "
            "service restricts processing intimate or graphic images directly, not because "
            "anything is wrong with your evidence. You don't need an automated description "
            "for it to be valid: you can describe what it shows in your own words in the chat, "
            "or use the platform's own reporting tool (most have a specific non-consensual "
            "image reporting flow) and a police or Cyber Crime Helpline (1930) report directly."
        )

    parts = (candidate.get("content", {}) or {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        logger.warning("Gemini vision returned empty text. Full response: %s", data)
        raise ValueError("Gemini vision returned no image analysis.")
    return _strip_markdown(text)