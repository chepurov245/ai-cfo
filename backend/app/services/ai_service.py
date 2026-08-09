import os
from decimal import Decimal

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.memory.conversation_memory import (
    add_message,
    get_history,
)
from app.models.company import Company
from app.models.transaction import Transaction


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
8. Если предоставлены финансовые данные компании, используй их как источник фактических данных.
9. Не придумывай финансовые показатели, которых нет в предоставленных данных.
"""


def get_financial_context(
    db: Session,
    user_id: int
) -> str:

    company = (
        db.query(Company)
        .filter(Company.owner_id == user_id)
        .order_by(Company.id.asc())
        .first()
    )

    if not company:
        return "У пользователя пока нет зарегистрированной компании."

    transactions = (
        db.query(Transaction)
        .filter(Transaction.company_id == company.id)
        .all()
    )

    total_income = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "income"
        ),
        Decimal("0")
    )

    total_expense = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
        ),
        Decimal("0")
    )

    profit = total_income - total_expense

    return f"""
ФИНАНСОВЫЙ КОНТЕКСТ КОМПАНИИ

Компания: {company.name}
Валюта: {company.currency}

Количество транзакций: {len(transactions)}
Общий доход: {total_income}
Общий расход: {total_expense}
Прибыль: {profit}

Используй эти цифры как фактические данные компании.
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

    # Получаем актуальные финансовые данные
    financial_context = get_financial_context(
        db=db,
        user_id=user_id
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "system",
            "content": financial_context
        }
    ]

    messages.extend(history)

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