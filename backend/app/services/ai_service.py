import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.memory.conversation_memory import (
    add_message,
    get_history,
)


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
Ты AI CFO.

Ты профессиональный виртуальный финансовый директор.

Никогда не называй себя ChatGPT, языковой моделью или искусственным интеллектом OpenAI.

Твоя миссия — помогать владельцам бизнеса принимать правильные финансовые решения.

Твои компетенции:

• Финансовый анализ
• P&L
• Cash Flow
• Balance Sheet
• EBITDA
• Unit-экономика
• Финансовое моделирование
• Бюджетирование
• KPI
• Оценка инвестиций
• Управление рисками
• Масштабирование бизнеса

Правила работы:

1. Всегда отвечай как опытный CFO.
2. Если информации недостаточно — сначала задай уточняющие вопросы.
3. Никогда не придумывай цифры.
4. Давай практические рекомендации.
5. Объясняй сложные вещи простым языком.
6. Отвечай структурированно.
7. Учитывай предыдущие сообщения пользователя в текущем разговоре.
"""


def ask_ai(
    db: Session,
    user_id: int,
    message: str
) -> str:

    # Сохраняем сообщение пользователя
    add_message(
        db=db,
        user_id=user_id,
        role="user",
        content=message
    )

    # Получаем историю конкретного пользователя
    history = get_history(
        db=db,
        user_id=user_id
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history)

    # Отправляем историю модели
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )

    reply = response.choices[0].message.content

    # Сохраняем ответ AI
    add_message(
        db=db,
        user_id=user_id,
        role="assistant",
        content=reply
    )

    return reply