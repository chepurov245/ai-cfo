from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.services.ai_service import ask_ai

router = APIRouter(tags=["Chat"])


@router.post("/chat")
def chat(request: ChatRequest):
    reply = ask_ai(request.message)

    return {
        "reply": reply
    }