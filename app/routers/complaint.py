from fastapi import APIRouter

from app.models.schemas import ComplaintDraftRequest, ComplaintDraftResponse
from app.services.complaint_service import build_draft

router = APIRouter(prefix="/api/complaint", tags=["complaint"])


@router.post("/draft", response_model=ComplaintDraftResponse)
async def create_draft(req: ComplaintDraftRequest) -> ComplaintDraftResponse:
    """Builds a reviewable draft summary from the form fields. Nothing is
    submitted or persisted — the caller decides what to do with the draft_id
    (e.g. hold it client-side only, unless the user is signed in and opts
    to save it)."""
    return build_draft(req)
