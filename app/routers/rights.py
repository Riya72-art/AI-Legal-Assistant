from fastapi import APIRouter, Query

from app.models.schemas import RightsSearchResponse, RightsTerm
from app.services.data_store import get_rights_glossary

router = APIRouter(prefix="/api/rights", tags=["rights"])


@router.get("", response_model=RightsSearchResponse)
async def search_rights(q: str = Query("", description="Free-text search over term names and descriptions.")) -> RightsSearchResponse:
    data = get_rights_glossary()
    terms = [RightsTerm(**t) for t in data["terms"]]

    if not q.strip():
        return RightsSearchResponse(results=terms, query=q)

    needle = q.strip().lower()
    matches = [
        t for t in terms
        if needle in t.term.lower() or needle in t.description.lower() or (t.term_hindi and needle in t.term_hindi)
    ]
    return RightsSearchResponse(results=matches, query=q)
