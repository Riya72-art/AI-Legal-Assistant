"""
Pydantic request/response models for the Nyaya Desk API.

Design note: nothing in these models requires a user identifier. Guest
sessions are the default (see app/services/session.py) — callers pass an
ephemeral session_id only if they want short-lived server-side state
(e.g. multi-turn "Ask Nyaya" context), and nothing is persisted to a
database unless the caller has authenticated and explicitly opted in.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    assamese = "Assamese"
    bengali = "Bengali"
    bodo = "Bodo"
    dogri = "Dogri"
    english = "English"
    gujarati = "Gujarati"
    hindi = "Hindi"
    kannada = "Kannada"
    kashmiri = "Kashmiri"
    konkani = "Konkani"
    maithili = "Maithili"
    malayalam = "Malayalam"
    manipuri = "Manipuri"
    marathi = "Marathi"
    nepali = "Nepali"
    odia = "Odia"
    punjabi = "Punjabi"
    sanskrit = "Sanskrit"
    santali = "Santali"
    sindhi = "Sindhi"
    tamil = "Tamil"
    telugu = "Telugu"
    urdu = "Urdu"


class AskCategory(str, Enum):
    online_harm = "Online harm & harassment"
    domestic_safety = "Domestic safety"
    fraud = "Fraud & identity theft"
    general = "General question"


# ---------------------------------------------------------------- Ask Nyaya

class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    topic: Optional[str] = Field(
        None, description="One of the quick-select topic chips, e.g. 'Cyberstalking'."
    )
    category: AskCategory = AskCategory.general
    language: Language = Language.english
    session_id: Optional[str] = Field(
        None, description="Optional ephemeral session id for multi-turn context. Omit for a single stateless question."
    )


class SourceRef(BaseModel):
    id: str
    title: str


class AskResponse(BaseModel):
    reply: str
    sources: list[SourceRef] = Field(
        default_factory=list,
        description="Curated knowledge-base entries the reply was grounded in. Empty list means no confident match was found.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalate: bool = Field(
        False,
        description="True if the message contains signals of immediate danger; frontend should surface the emergency banner.",
    )
    disclaimer: str = "This is general information, not legal advice."


class ImageAnalysisResponse(BaseModel):
    analysis: str
    filename: str
    disclaimer: str = "Image analysis is informational only, not legal advice. Do not rely on it alone for urgent safety or legal decisions."


class TranslateRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=160)
    language: Language


class TranslateResponse(BaseModel):
    translations: list[str]


# ---------------------------------------------------------------- Complaint draft

class EvidenceStatus(str, Enum):
    yes = "yes"
    not_yet = "not_yet"


class DraftType(str, Enum):
    complaint = "complaint"
    legal_notice = "legal_notice"


class ComplaintDraftRequest(BaseModel):
    what: str = Field(..., min_length=1, max_length=4000)
    when: Optional[str] = Field(None, max_length=200)
    who: Optional[str] = Field(None, max_length=200)
    where: Optional[str] = Field(None, max_length=200)
    evidence: EvidenceStatus = EvidenceStatus.not_yet
    category: AskCategory = AskCategory.general
    language: Language = Language.english
    document_type: DraftType = DraftType.complaint


class SuggestedStatute(BaseModel):
    id: str
    label: str
    note: str


class ComplaintDraftResponse(BaseModel):
    draft_id: str
    document_type: DraftType
    summary: str
    suggested_statutes: list[SuggestedStatute] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    generated_at: datetime
    note: str = "This is a draft summary for your own review. Nothing has been submitted anywhere."


# ---------------------------------------------------------------- Helplines

class Helpline(BaseModel):
    id: str
    name: str
    number: str
    description: str
    state: Optional[str] = Field(None, description="Null/omitted means national coverage.")
    hours: str = "24/7"
    kind: str = Field("emergency", description="'emergency' | 'specialist' | 'support'")


class HelplinesResponse(BaseModel):
    national: list[Helpline]
    state: list[Helpline] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- Rights glossary

class RightsTerm(BaseModel):
    id: str
    term: str
    term_hindi: Optional[str] = None
    description: str
    category: AskCategory = AskCategory.general


class RightsSearchResponse(BaseModel):
    results: list[RightsTerm]
    query: str


# ---------------------------------------------------------------- Healing & support

class HealingPrinciple(BaseModel):
    id: str
    title: str
    description: str


class SupportContact(BaseModel):
    id: str
    name: str
    number: str
    description: str
    hours: str = "By appointment"


class CommunityResource(BaseModel):
    id: str
    title: str
    description: str


class HealingResourcesResponse(BaseModel):
    principles: list[HealingPrinciple]
    counselling: list[SupportContact]
    community: list[CommunityResource]


# ---------------------------------------------------------------- Safety

class PanicClearResponse(BaseModel):
    cleared: bool
    message: str = "Any server-side session state has been discarded."
