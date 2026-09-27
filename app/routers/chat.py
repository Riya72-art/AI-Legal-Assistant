"""Accepts live-chat pings from the floating widget.

The frontend already shows an on-page auto-reply. This endpoint exists so
those POSTs are not 404s. Messages are not stored — guest-first, no history.
"""
from pydantic import BaseModel, Field
from fastapi import APIRouter

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    received: bool = True
    saved: bool = False


@router.post("/message", response_model=ChatMessageResponse)
async def receive_chat_message(_req: ChatMessageRequest) -> ChatMessageResponse:
    return ChatMessageResponse()
