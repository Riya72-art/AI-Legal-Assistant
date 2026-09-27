from fastapi import APIRouter

from app.models.schemas import HealingResourcesResponse
from app.services.data_store import get_healing_resources

router = APIRouter(prefix="/api/healing", tags=["healing"])


@router.get("/resources", response_model=HealingResourcesResponse)
async def get_resources() -> HealingResourcesResponse:
    return HealingResourcesResponse(**get_healing_resources())
