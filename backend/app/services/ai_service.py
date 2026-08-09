import os
import re
from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal

import openai
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
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60.0,
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
17. При сравнении периодов анализируй каждый период отдельно.
18. Не смешивай финансовые показатели одного периода с другим.
19. Если сравниваются два периода, явно указывай показатели каждого периода.
20. Изменение показателя рассчитывай только на основании предоставленных данных.
21. Отсутствие транзакций за период означает только отсутствие зарегистрированных финансовых операций.
22. Не утверждай, что бизнес не работал, не было продаж или компания была неактивна, если это прямо не подтверждается данными.
23. Не делай причинно-следственных выводов, которые нельзя подтвердить предоставленными финансовыми данными.
24. Если за период нет транзакций, используй формулировку:
"За этот период зарегистрированных финансовых операций не найдено."
"""


MONTHS = {
    "январь": 1,
    "января": 1,
    "февраль": 2,
    "февраля": 2,
    "март": 3,
    "марта": 3,
    "апрель": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июль": 7,
    "июля": 7,
    "август": 8,
    "августа": 8,
    "сентябрь": 9,
    "сентября": 9,
    "октябрь": 10,
    "октября": 10,
    "ноябрь": 11,
    "ноября": 11,
    "декабрь": 12,
    "декабря": 12,
}


def get_month_number(month_name: str) -> int | None:
    return MONTHS.get(month_name.lower())


def create_day_range(
    year: int,
    month: int,
    day: int,
):
    start = datetime(
        year,
        month,
        day,
        0,
        0,
        0,
    )

    end = datetime(
        year,
        month,
        day,
        23,
        59,
        59,
    )

    return start, end


def parse_date_range(message: str):
    """
    Определяет один финансовый период из сообщения пользователя.

    Поддерживаются:

    - сегодня
    - вчера
    - за август
    - за 9 августа
    - с 1 по 8 августа
    - с 1 августа по 8 августа
    - с 1 августа по 8 сентября
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
            microsecond=0,
        )

        end = now.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

        return start, end

    # Вчера
    if "вчера" in text:
        yesterday = now - timedelta(days=1)

        start = yesterday.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end = yesterday.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

        return start, end

    # Последний месяц
    if "последний месяц" in text:
        end = now
        start = end - timedelta(days=30)

        return start, end

    # С 1 по 8 августа
    range_match = re.search(
        r"с\s+"
        r"(\d{1,2})"
        r"(?:\s+([а-яё]+))?"
        r"\s+по\s+"
        r"(\d{1,2})"
        r"\s+([а-яё]+)"
        r"(?:\s+(\d{4}))?",
        text,
    )

    if range_match:
        start_day = int(range_match.group(1))
        start_month_name = range_match.group(2)

        end_day = int(range_match.group(3))
        end_month_name = range_match.group(4)
        year_text = range_match.group(5)

        end_month = get_month_number(end_month_name)

        if end_month:
            if start_month_name:
                start_month = get_month_number(
                    start_month_name
                )
            else:
                start_month = end_month

            if start_month:
                year = (
                    int(year_text)
                    if year_text
                    else now.year
                )

                start = datetime(
                    year,
                    start_month,
                    start_day,
                    0,
                    0,
                    0,
                )

                end = datetime(
                    year,
                    end_month,
                    end_day,
                    23,
                    59,
                    59,
                )

                return start, end

    # За 9 августа / от 9 августа
    single_day_match = re.search(
        r"(?:за|от)\s+"
        r"(\d{1,2})\s+"
        r"([а-яё]+)"
        r"(?:\s+(\d{4}))?",
        text,
    )

    if single_day_match:
        day = int(single_day_match.group(1))
        month_name = single_day_match.group(2)
        year_text = single_day_match.group(3)

        month = get_month_number(month_name)

        if month:
            year = (
                int(year_text)
                if year_text
                else now.year
            )

            return create_day_range(
                year,
                month,
                day,
            )

    # За август 2026
    month_match = re.search(
        r"за\s+"
        r"(январь|января|февраль|февраля|март|марта|"
        r"апрель|апреля|май|мая|июнь|июня|июль|июля|"
        r"август|августа|сентябрь|сентября|октябрь|октября|"
        r"ноябрь|ноября|декабрь|декабря)"
        r"(?:\s+(\d{4}))?",
        text,
    )

    if month_match:
        month_name = month_match.group(1)
        year_text = month_match.group(2)

        month = get_month_number(month_name)

        if month:
            year = (
                int(year_text)
                if year_text
                else now.year
            )

            last_day = monthrange(
                year,
                month,
            )[1]

            start = datetime(
                year,
                month,
                1,
                0,
                0,
                0,
            )

            end = datetime(
                year,
                month,
                last_day,
                23,
                59,
                59,
            )

            return start, end

    return None, None


def parse_comparison_periods(message: str):
    """
    Определяет два финансовых периода из запроса на сравнение.

    Например:

    "Сравни прибыль с 1 по 8 августа и за 9 августа"
    """

    text = message.lower().strip()

    comparison_words = (
        "сравни",
        "сравнить",
        "сопоставь",
        "сопоставить",
    )

    if not any(
        text.startswith(word)
        for word in comparison_words
    ):
        return None

    comparison_match = re.search(
        r"\s+и\s+",
        text,
    )

    if not comparison_match:
        return None

    left_part = text[
        :comparison_match.start()
    ]

    right_part = text[
        comparison_match.end():
    ]

    first_start, first_end = parse_date_range(
        left_part
    )

    second_start, second_end = parse_date_range(
        right_part
    )

    if (
        first_start is None
        or first_end is None
        or second_start is None
        or second_end is None
    ):
        return None

    return [
        (
            first_start,
            first_end,
        ),
        (
            second_start,
            second_end,
        ),
    ]


def calculate_financials(
    db: Session,
    company_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    """
    Получает транзакции и рассчитывает
    финансовые показатели.
    """

    query = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id
        )
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
        Decimal("0"),
    )

    total_expense = sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.type == "expense"
        ),
        Decimal("0"),
    )

    profit = (
        total_income
        - total_expense
    )

    if total_income > 0:
        profit_margin = (
            profit
            / total_income
        ) * Decimal("100")
    else:
        profit_margin = Decimal("0")

    expenses_by_category = {}

    for transaction in transactions:
        if transaction.type != "expense":
            continue

        category = transaction.category

        if category not in expenses_by_category:
            expenses_by_category[category] = (
                Decimal("0")
            )

        expenses_by_category[category] += (
            transaction.amount
        )

    expenses_by_category = dict(
        sorted(
            expenses_by_category.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    return {
        "transactions": transactions,
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": profit,
        "profit_margin": profit_margin,
        "expenses_by_category": (
            expenses_by_category
        ),
    }


def format_period(
    start_date: datetime,
    end_date: datetime,
) -> str:

    return (
        f"{start_date.strftime('%d.%m.%Y %H:%M:%S')} "
        f"— "
        f"{end_date.strftime('%d.%m.%Y %H:%M:%S')}"
    )


def get_financial_context(
    db: Session,
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> str:

    company = (
        db.query(Company)
        .filter(
            Company.owner_id == user_id
        )
        .order_by(Company.id.asc())
        .first()
    )

    if not company:
        return (
            "У пользователя пока нет "
            "зарегистрированной компании."
        )

    financials = calculate_financials(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    transactions = financials["transactions"]
    total_income = financials["total_income"]
    total_expense = financials["total_expense"]
    profit = financials["profit"]
    profit_margin = financials["profit_margin"]
    expenses_by_category = (
        financials["expenses_by_category"]
    )

    if expenses_by_category:
        expenses_text = "\n".join(
            f"- {category}: {amount}"
            for category, amount
            in expenses_by_category.items()
        )
    else:
        expenses_text = (
            "Расходов за выбранный период нет."
        )

    if start_date and end_date:
        period_text = format_period(
            start_date,
            end_date,
        )
    else:
        period_text = (
            "за весь доступный период"
        )

    return f"""
ФИНАНСОВЫЙ КОНТЕКСТ КОМПАНИИ

Компания: {company.name}
Валюта: {company.currency}

АНАЛИЗИРУЕМЫЙ ПЕРИОД:
{period_text}

Количество транзакций:
{len(transactions)}

Общий доход:
{total_income}

Общий расход:
{total_expense}

Прибыль:
{profit}

Маржа прибыли:
{profit_margin.quantize(Decimal("0.01"))}%

РАСХОДЫ ПО КАТЕГОРИЯМ:

{expenses_text}

Используй эти цифры как фактические данные компании.

Если количество транзакций равно 0,
сообщи пользователю:

"За этот период зарегистрированных
финансовых операций не найдено."

Не утверждай, что бизнес не работал,
если это не подтверждается данными.

Не придумывай другие финансовые показатели.
"""


def get_comparison_context(
    db: Session,
    user_id: int,
    periods,
) -> str:
    """
    Формирует финансовый контекст
    для двух сравниваемых периодов.
    """

    company = (
        db.query(Company)
        .filter(
            Company.owner_id == user_id
        )
        .order_by(Company.id.asc())
        .first()
    )

    if not company:
        return (
            "У пользователя пока нет "
            "зарегистрированной компании."
        )

    period_1_start, period_1_end = periods[0]
    period_2_start, period_2_end = periods[1]

    financials_1 = calculate_financials(
        db=db,
        company_id=company.id,
        start_date=period_1_start,
        end_date=period_1_end,
    )

    financials_2 = calculate_financials(
        db=db,
        company_id=company.id,
        start_date=period_2_start,
        end_date=period_2_end,
    )

    def format_financial_period(
        number: int,
        start_date: datetime,
        end_date: datetime,
        financials: dict,
    ) -> str:

        expenses_by_category = (
            financials["expenses_by_category"]
        )

        if expenses_by_category:
            expenses_text = "\n".join(
                f"- {category}: {amount}"
                for category, amount
                in expenses_by_category.items()
            )
        else:
            expenses_text = (
                "Расходов нет."
            )

        if len(financials["transactions"]) == 0:
            transaction_note = (
                "За этот период зарегистрированных "
                "финансовых операций не найдено."
            )
        else:
            transaction_note = (
                "Финансовые операции за период найдены."
            )

        return f"""
ПЕРИОД {number}

Период:
{format_period(
    start_date,
    end_date,
)}

Количество транзакций:
{len(financials["transactions"])}

Общий доход:
{financials["total_income"]}

Общий расход:
{financials["total_expense"]}

Прибыль:
{financials["profit"]}

Маржа прибыли:
{financials["profit_margin"].quantize(Decimal("0.01"))}%

Расходы по категориям:

{expenses_text}

Комментарий по данным:

{transaction_note}
"""

    return f"""
ФИНАНСОВЫЙ КОНТЕКСТ ДЛЯ СРАВНЕНИЯ

Компания: {company.name}
Валюта: {company.currency}

СРАВНИВАЕМЫЕ ПЕРИОДЫ:

{format_financial_period(
    1,
    period_1_start,
    period_1_end,
    financials_1,
)}

{format_financial_period(
    2,
    period_2_start,
    period_2_end,
    financials_2,
)}

ВАЖНЫЕ ПРАВИЛА:

1. Каждый период анализируй отдельно.
2. Не смешивай транзакции разных периодов.
3. Используй только предоставленные цифры.
4. Если в периоде нет транзакций,
   сообщи только об отсутствии
   зарегистрированных финансовых операций.
5. Не утверждай, что бизнес не работал,
   если это не подтверждается данными.
6. Не утверждай, что не было продаж,
   если это не подтверждается данными.
7. Не утверждай, что компания была неактивна,
   если это не подтверждается данными.
8. При сравнении можешь показать
   абсолютную разницу между показателями.
9. Не придумывай отсутствующие показатели.
"""


def ask_ai(
    db: Session,
    user_id: int,
    message: str,
) -> str:

    # Сохраняем сообщение пользователя
    add_message(
        db=db,
        user_id=user_id,
        role="user",
        content=message,
    )

    # Получаем историю пользователя
    history = get_history(
        db=db,
        user_id=user_id,
    )

    # Проверяем сравнение двух периодов
    comparison_periods = (
        parse_comparison_periods(message)
    )

    if comparison_periods:

        financial_context = (
            get_comparison_context(
                db=db,
                user_id=user_id,
                periods=comparison_periods,
            )
        )

    else:

        # Обычный запрос с одним периодом
        start_date, end_date = (
            parse_date_range(message)
        )

        financial_context = (
            get_financial_context(
                db=db,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": financial_context,
        },
    ]

    messages.extend(history)

    try:

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
        )

        reply = (
            response.choices[0]
            .message.content
        )

    except openai.APITimeoutError:

        reply = (
            "Сервис финансового анализа временно "
            "не ответил вовремя. "
            "Ваш запрос не потерян. "
            "Попробуйте отправить его ещё раз."
        )

    except openai.RateLimitError:

        reply = (
            "Сервис финансового анализа сейчас "
            "перегружен. "
            "Попробуйте повторить запрос "
            "немного позже."
        )

    except openai.AuthenticationError:

        reply = (
            "Не удалось выполнить финансовый анализ: "
            "проверьте настройки OpenAI API."
        )

    except openai.APIConnectionError:

        reply = (
            "Не удалось установить соединение "
            "с сервисом финансового анализа. "
            "Проверьте подключение и попробуйте ещё раз."
        )

    except openai.APIStatusError:

        reply = (
            "Сервис финансового анализа временно "
            "недоступен. "
            "Попробуйте повторить запрос позже."
        )

    except openai.APIError:

        reply = (
            "Произошла ошибка при выполнении "
            "финансового анализа. "
            "Попробуйте повторить запрос позже."
        )

    # Сохраняем ответ AI
    add_message(
        db=db,
        user_id=user_id,
        role="assistant",
        content=reply,
    )

    return reply