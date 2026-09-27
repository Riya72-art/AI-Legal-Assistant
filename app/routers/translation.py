from fastapi import APIRouter, HTTPException

from app.models.schemas import TranslateRequest, TranslateResponse
from app.services.translation import translate_texts


router = APIRouter(prefix="/api/translate", tags=["translation"])


@router.post("", response_model=TranslateResponse)
async def translate_website(req: TranslateRequest) -> TranslateResponse:
    try:
        return TranslateResponse(translations=await translate_texts(req.texts, req.language))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Website translation is unavailable right now.") from exc