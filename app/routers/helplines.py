from fastapi import APIRouter, Query

from app.models.schemas import Helpline, HelplinesResponse
from app.services.data_store import get_helplines

router = APIRouter(prefix="/api/helplines", tags=["helplines"])

REGIONS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]


@router.get("", response_model=HelplinesResponse)
async def list_helplines(state: str | None = Query(None, description="e.g. 'Maharashtra'. Omit for national only.")) -> HelplinesResponse:
    data = get_helplines()
    national = [Helpline(**h) for h in data["national"]]
    state_matches = (
        [Helpline(**h) for h in data["state"] if h["state"].lower() == state.lower()]
        if state
        else []
    )
    if state and not state_matches and state.strip().lower() in {region.lower() for region in REGIONS}:
        state_matches = [Helpline(
            id=f"referral-{state.strip().lower().replace(' ', '-')}",
            name=f"Women Helpline referral ({state.strip()})",
            number="181",
            description=f"Call for a current local women's support, shelter, and legal-aid referral in {state.strip()}.",
            state=state.strip(),
            hours="24/7 referral",
            kind="specialist",
        )]
    return HelplinesResponse(national=national, state=state_matches, regions=REGIONS)
