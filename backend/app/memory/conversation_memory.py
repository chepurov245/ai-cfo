from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


def add_message(
    db: Session,
    user_id: int,
    role: str,
    content: str
):
    message = ChatMessage(
        user_id=user_id,
        role=role,
        content=content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_history(
    db: Session,
    user_id: int
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return [
        {
            "role": message.role,
            "content": message.content
        }
        for message in messages
    ]


def clear_history(
    db: Session,
    user_id: int
):
    (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .delete()
    )

    db.commit()