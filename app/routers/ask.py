from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import AskRequest, AskResponse, ImageAnalysisResponse
from app.services.ask_service import answer_question
from app.services.image_analysis import analyze_image

router = APIRouter(prefix="/api/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Answer a free-text question. Stateless unless session_id is provided
    (session-based context is not yet implemented in this scaffold — see
    app/services/ask_service.py for where to add it)."""
    return await answer_question(req)


@router.post("/image", response_model=ImageAnalysisResponse)
async def analyze_uploaded_image(
    image: UploadFile = File(...),
    language: str = Form("English"),
) -> ImageAnalysisResponse:
    """Analyze one image in memory through Gemini; never save the upload."""
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, WEBP, or GIF image.")

    contents = await image.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")

    try:
        analysis = await analyze_image(contents, image.content_type, language)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Gemini could not analyze this image right now.") from exc

    return ImageAnalysisResponse(analysis=analysis, filename=image.filename or "uploaded image")
