from app.database.session import Base, engine

from app.models.user import User
from app.models.chat_message import ChatMessage


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")