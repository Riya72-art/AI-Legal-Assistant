from fastapi import APIRouter, Query
from app.models.schemas import PanicClearResponse
from app.services.session import clear_session

router = APIRouter(prefix="/api/safety", tags=["safety"])

REGIONS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]


@router.get("/directory")
async def safety_directory(state: str = Query(..., min_length=1)) -> dict:
    region = next((item for item in REGIONS if item.lower() == state.strip().lower()), None)
    if not region:
        return {"state": state, "results": []}
    return {
        "state": region,
        "results": [
            {"type": "legal", "name": f"District Legal Services Authority ({region})", "loc": f"Free legal-aid service directory for districts in {region}", "num": f"{region} legal-aid directory", "beds": "Free legal aid"},
            {"type": "shelter", "name": f"One Stop Centre directory ({region})", "loc": f"State shelter and support-centre directory for {region}", "num": f"{region} shelter directory", "beds": "Call to check"},
            {"type": "crisis", "name": f"State crisis-support directory ({region})", "loc": f"State and local crisis contacts for {region}; national emergency support remains on Helplines", "num": f"{region} crisis directory", "beds": "Live referral"}
        ]
    }


@router.post("/checkin-request")
async def checkin_request() -> dict:
    """Quiet acknowledgement for the disguised distress poll.
    Nothing is stored. The frontend only needs a 2xx so the request is not
    a 404 in the network log.
    """
    return {"acknowledged": True}
@router.post("/panic-clear", response_model=PanicClearResponse)
async def panic_clear(session_id: str | None = Query(None)) -> PanicClearResponse:
    """Wipes any server-side session state for the given session_id.
    Note: the frontend's "Quick exit" button should navigate away
    immediately regardless of whether this call succeeds — never make
    the redirect wait on a network round trip. Fire this request and
    move on."""
    if session_id:
        clear_session(session_id)
    return PanicClearResponse(cleared=True)