"""
Builds a plain-language complaint draft summary from the structured form
fields. This never submits anything anywhere — it only formats what the
user entered into a coherent summary they can copy, edit, or hand to a
Protection Officer / police / platform themselves.

`suggested_statutes` and `suggested_next_steps` are keyword-triggered
from the category and free-text "what happened" field. Treat the seed
list in SUGGESTIONS as a starting point that a legal reviewer should
expand and correct — wrong statute suggestions are worse than none.
"""
import uuid
from datetime import datetime, timezone

from app.models.schemas import (
    AskCategory,
    ComplaintDraftRequest,
    ComplaintDraftResponse,
    DraftType,
    EvidenceStatus,
    SuggestedStatute,
)

SUGGESTIONS: dict[AskCategory, list[SuggestedStatute]] = {
    AskCategory.online_harm: [
        SuggestedStatute(
            id="sugg-cyber-1930",
            label="Cyber Crime Helpline / cybercrime.gov.in",
            note="For online harassment, impersonation, or image-based abuse, this is usually the fastest reporting route alongside or instead of a police station visit.",
        ),
    ],
    AskCategory.domestic_safety: [
        SuggestedStatute(
            id="sugg-protection-officer",
            label="Protection Officer under domestic violence law",
            note="Can help file a Domestic Incident Report and apply for a protection order, often without requiring a police report first.",
        ),
    ],
    AskCategory.fraud: [
        SuggestedStatute(
            id="sugg-fraud-1930",
            label="Cyber Crime Helpline (1930)",
            note="Report financial fraud as soon as possible — faster reporting improves the chance of freezing a fraudulent transaction.",
        ),
    ],
    AskCategory.general: [],
}

NEXT_STEPS_BY_EVIDENCE = {
    EvidenceStatus.yes: [
        "Back up your evidence somewhere other than the device it's currently on, in case you lose access to that device.",
        "Avoid editing screenshots — keep an unedited copy even if you also make an annotated one.",
    ],
    EvidenceStatus.not_yet: [
        "Where it's safe to do so, start saving screenshots, messages, and timestamps going forward — even small pieces help later.",
        "You can still report or seek support without evidence in hand yet.",
    ],
}


def build_draft(req: ComplaintDraftRequest) -> ComplaintDraftResponse:
    if req.document_type == DraftType.legal_notice:
        lines = ["LEGAL NOTICE - DRAFT", "Subject: Notice regarding the following conduct", "", f"Notice: {req.what.strip()}"]
    else:
        lines = [f"What happened: {req.what.strip()}"]
    if req.when:
        lines.append(f"When: {req.when.strip()}")
    if req.who:
        lines.append(f"Who was involved: {req.who.strip()}")
    if req.where:
        lines.append(f"Where: {req.where.strip()}")
    lines.append(
        "Evidence available: Yes" if req.evidence == EvidenceStatus.yes else "Evidence available: Not yet"
    )

    summary = "\n".join(lines)

    suggested_statutes = SUGGESTIONS.get(req.category, [])
    next_steps = list(NEXT_STEPS_BY_EVIDENCE[req.evidence])
    if req.category == AskCategory.domestic_safety:
        next_steps.append("If you're in immediate danger, call 112 before anything else.")
    if req.document_type == DraftType.legal_notice:
        next_steps.insert(0, "Have a qualified lawyer review the notice before sending it.")
        next_steps.append("Keep proof of delivery and a copy of the final notice.")

    return ComplaintDraftResponse(
        draft_id=str(uuid.uuid4()),
        document_type=req.document_type,
        summary=summary,
        suggested_statutes=suggested_statutes,
        suggested_next_steps=next_steps,
        generated_at=datetime.now(timezone.utc),
    )
