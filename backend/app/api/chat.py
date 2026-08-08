from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.ai_service import ask_ai


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reply = ask_ai(
        db=db,
        user_id=current_user.id,
        message=request.message
    )

    return {
        "reply": reply,
        "user_id": current_user.id
    }