import os
import re
from calendar import monthrange
from datetime import datetime, timedelta
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
10. Если финансовых данных недостаточно для полноценного вывода, прямо указывай на это.
11. При анализе прибыльности учитывай как абсолютную прибыль, так и маржинальность.
12. При анализе расходов учитывай распределение расходов по категориям.
13. Не называй категорию крупнейшей, если это не подтверждается предоставленными данными.
14. Если данных мало, указывай, что вывод является предварительным.
15. Если финансовый контекст содержит период, анализируй только данные этого периода.
16. Никогда не смешивай данные разных периодов.
"""


MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def parse_date_range(message: str):
    """
    Определяет финансовый период из сообщения пользователя.

    Поддерживаются основные сценарии:

    - сегодня
    - вчера
    - за август
    - за 9 августа
    - с 1 по 8 августа
    - с 1 августа по 8 августа
    - за последний месяц
    """

    text = message.lower().strip()

    now = datetime.now()

    # Сегодня
    if "сегодня" in text:
        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end = now.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        )

        return start, end

    # Вчера
    if "вчера" in text:
        yesterday = now - timedelta(days=1)

        start = yesterday.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end = yesterday.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        )

        return start, end

    # Последний месяц
    if "последний месяц" in text:
        end = now

        start = end - timedelta(days=30)

        return start, end

    # С 1 по 8 августа
    range_match = re.search(
        r"с\s+(\d{1,2})\s+([а-яё]+)"
        r"(?:\s+\d{4})?"
        r"\s+по\s+(\d{1,2})\s+([а-яё]+)"
        r"(?:\s+\d{4})?",
        text
    )

    if range_match:
        start_day = int(range_match.group(1))
        start_month_name = range_match.group(2)

        end_day = int(range_match.group(3))
        end_month_name = range_match.group(4)

        start_month = MONTHS.get(start_month_name)
        end_month = MONTHS.get(end_month_name)

        if start_month and end_month:
            year = now.year

            start = datetime(
                year,
                start_month,
                start_day,
                0,
                0,
                0
            )

            end = datetime(
                year,
                end_month,
                end_day,
                23,
                59,
                59
            )

            return start, end

    # За 9 августа
    single_day_match = re.search(
        r"(?:за|от)\s+(\d{1,2})\s+([а-яё]+)",
        text
    )

    if single_day_match:
        day = int(single_day_match.group(1))
        month_name = single_day_match.group(2)

        month = MONTHS.get(month_name)

        if month:
            year = now.year

            start = datetime(
                year,
                month,
                day,
                0,
                0,
                0
            )

            end = datetime(
                year,
                month,
                day,
                23,
                59,
                59
            )

            return start, end

    # За август
    month_match = re.search(
        r"за\s+"
        r"(январь|февраль|март|апрель|май|июнь|июль|август|"
        r"сентябрь|октябрь|ноябрь|декабрь)"
        r"(?:\s+(\d{4}))?",
        text
    )

    if month_match:
        month_name = month_match.group(1)
        year_text = month_match.group(2)

        month = MONTHS.get(
            f"{month_name}а"
            if month_name in ["январь", "февраль", "апрель", "май", "июнь",
                              "июль", "август", "сентябрь", "октябрь",
                              "ноябрь", "декабрь"]
            else month_name
        )

        # Отдельно обрабатываем "март", который уже совпадает с ключом.
        if month_name == "март":
            month = 3

        if month_name == "май":
            month = 5

        if month:
            year = int(year_text) if year_text else now.year

            last_day = monthrange(year, month)[1]

            start = datetime(
                year,
                month,
                1,
                0,
                0,
                0
            )

            end = datetime(
                year,
                month,
                last_day,
                23,
                59,
                59
            )

            return start, end

    return None, None


def get_financial_context(
    db: Session,
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> str:

    company = (
        db.query(Company)
        .filter(Company.owner_id == user_id)
        .order_by(Company.id.asc())
        .first()
    )

    if not company:
        return "У пользователя пока нет зарегистрированной компании."

    query = (
        db.query(Transaction)
        .filter(Transaction.company_id == company.id)
    )

    if start_date:
        query = query.filter(
            Transaction.transaction_date >= start_date
        )

    if end_date:
        query = query.filter(
            Transaction.transaction_date <= end_date
        )

    transactions = query.all()

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

    if total_income > 0:
        profit_margin = (
            profit / total_income
        ) * Decimal("100")
    else:
        profit_margin = Decimal("0")

    expenses_by_category = {}

    for transaction in transactions:
        if transaction.type != "expense":
            continue

        category = transaction.category

        if category not in expenses_by_category:
            expenses_by_category[category] = Decimal("0")

        expenses_by_category[category] += transaction.amount

    expenses_by_category = dict(
        sorted(
            expenses_by_category.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    if expenses_by_category:
        expenses_text = "\n".join(
            f"- {category}: {amount}"
            for category, amount in expenses_by_category.items()
        )
    else:
        expenses_text = "Расходов за выбранный период нет."

    if start_date and end_date:
        period_text = (
            f"с {start_date.strftime('%d.%m.%Y %H:%M:%S')} "
            f"по {end_date.strftime('%d.%m.%Y %H:%M:%S')}"
        )
    else:
        period_text = "за весь доступный период"

    return f"""
ФИНАНСОВЫЙ КОНТЕКСТ КОМПАНИИ

Компания: {company.name}
Валюта: {company.currency}

АНАЛИЗИРУЕМЫЙ ПЕРИОД:
{period_text}

Количество транзакций: {len(transactions)}

Общий доход: {total_income}
Общий расход: {total_expense}
Прибыль: {profit}
Маржа прибыли: {profit_margin.quantize(Decimal("0.01"))}%

РАСХОДЫ ПО КАТЕГОРИЯМ:

{expenses_text}

Используй эти цифры как фактические данные компании.

Если количество транзакций равно 0, сообщи пользователю,
что за выбранный период финансовых операций не найдено.

Не придумывай другие финансовые показатели.
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

    # Определяем финансовый период из вопроса
    start_date, end_date = parse_date_range(message)

    # Получаем историю конкретного пользователя
    history = get_history(
        db=db,
        user_id=user_id
    )

    # Получаем актуальные финансовые данные
    financial_context = get_financial_context(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
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