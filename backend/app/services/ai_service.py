import os
import re
from calendar import monthrange
from datetime import datetime, timedelta

import openai
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.memory.conversation_memory import (
    add_message,
    get_history,
)
from app.models.company import Company
from app.services.financial_service import (
    calculate_cash_flow,
    calculate_expenses_by_category,
    calculate_kpi,
    calculate_revenue_by_category,
    calculate_summary,
    get_transactions,
)


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

25. При вопросах о Cash Flow используй показатели:
    - cash inflow;
    - cash outflow;
    - net cash flow.

26. При вопросах о KPI используй только рассчитанные финансовые показатели.

27. При вопросах о расходах используй распределение расходов по категориям.

28. При вопросах о доходах используй распределение доходов по категориям.

29. Не называй показатель прогнозом, если он рассчитан только по фактическим транзакциям.

30. Не называй прибыль чистой прибылью, EBITDA или денежным остатком,
    если соответствующий показатель отдельно не рассчитан.

31. Если пользователь спрашивает о среднем размере транзакции,
    используй фактическое количество транзакций и суммы,
    предоставленные в финансовом контексте.

32. Если пользователь спрашивает о нескольких финансовых показателях,
    используй только соответствующие показатели из финансового контекста.

33. Если финансовый контекст содержит данные за конкретный период,
    не используй транзакции за другие периоды.

34. Если финансовый контекст содержит два периода,
    всегда разделяй показатели этих периодов.

35. Не делай вывод о причинах изменения финансовых показателей,
    если причина не подтверждается данными.

36. Не утверждай, что показатель является "хорошим", "плохим",
    "высоким" или "низким" без достаточного контекста для такого вывода.
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


def get_month_number(
    month_name: str,
) -> int | None:
    return MONTHS.get(
        month_name.lower()
    )


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


def parse_date_range(
    message: str,
):
    """
    Определяет один финансовый период
    из сообщения пользователя.

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
        yesterday = (
            now - timedelta(days=1)
        )

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
        start_day = int(
            range_match.group(1)
        )

        start_month_name = (
            range_match.group(2)
        )

        end_day = int(
            range_match.group(3)
        )

        end_month_name = (
            range_match.group(4)
        )

        year_text = (
            range_match.group(5)
        )

        end_month = get_month_number(
            end_month_name
        )

        if end_month:

            if start_month_name:
                start_month = (
                    get_month_number(
                        start_month_name
                    )
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
        day = int(
            single_day_match.group(1)
        )

        month_name = (
            single_day_match.group(2)
        )

        year_text = (
            single_day_match.group(3)
        )

        month = get_month_number(
            month_name
        )

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
        r"(январь|января|февраль|февраля|"
        r"март|марта|апрель|апреля|май|мая|"
        r"июнь|июня|июль|июля|август|августа|"
        r"сентябрь|сентября|октябрь|октября|"
        r"ноябрь|ноября|декабрь|декабря)"
        r"(?:\s+(\d{4}))?",
        text,
    )

    if month_match:
        month_name = (
            month_match.group(1)
        )

        year_text = (
            month_match.group(2)
        )

        month = get_month_number(
            month_name
        )

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


def parse_comparison_periods(
    message: str,
):
    """
    Определяет два финансовых периода
    из запроса на сравнение.

    Например:

    "Сравни прибыль с 1 по 8 августа
    и за 9 августа"
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

    first_start, first_end = (
        parse_date_range(left_part)
    )

    second_start, second_end = (
        parse_date_range(right_part)
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

    transactions = get_transactions(
        db=db,
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
    )

    summary = calculate_summary(
        transactions
    )

    cash_flow = calculate_cash_flow(
        transactions
    )

    expenses = (
        calculate_expenses_by_category(
            transactions
        )
    )

    revenue = (
        calculate_revenue_by_category(
            transactions
        )
    )

    kpi = calculate_kpi(
        transactions
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

    if expenses:
        expenses_text = "\n".join(
            f"- {category}: {amount}"
            for category, amount
            in expenses.items()
        )
    else:
        expenses_text = (
            "Расходов за выбранный период нет."
        )

    if revenue:
        revenue_text = "\n".join(
            f"- {category}: {amount}"
            for category, amount
            in revenue.items()
        )
    else:
        revenue_text = (
            "Доходов за выбранный период нет."
        )

    if len(transactions) == 0:
        transaction_note = (
            "За этот период зарегистрированных "
            "финансовых операций не найдено."
        )
    else:
        transaction_note = (
            "Финансовые операции за период найдены."
        )

    return f"""
ФИНАНСОВЫЙ КОНТЕКСТ КОМПАНИИ

Компания:
{company.name}

Валюта:
{company.currency}

АНАЛИЗИРУЕМЫЙ ПЕРИОД:
{period_text}

ТРАНЗАКЦИИ

Количество транзакций:
{summary["transaction_count"]}

Количество доходных транзакций:
{kpi["income_transaction_count"]}

Количество расходных транзакций:
{kpi["expense_transaction_count"]}

ПРИБЫЛЬНОСТЬ

Общий доход:
{summary["total_income"]}

Общий расход:
{summary["total_expense"]}

Прибыль:
{summary["profit"]}

Маржа прибыли:
{summary["profit_margin"]}%

CASH FLOW

Денежный приток:
{cash_flow["cash_inflow"]}

Денежный отток:
{cash_flow["cash_outflow"]}

Чистый денежный поток:
{cash_flow["net_cash_flow"]}

РАСХОДЫ ПО КАТЕГОРИЯМ

{expenses_text}

ДОХОДЫ ПО КАТЕГОРИЯМ

{revenue_text}

KPI

Средний доход на транзакцию:
{kpi["average_income_transaction"]}

Средний расход на транзакцию:
{kpi["average_expense_transaction"]}

Средний размер транзакции:
{kpi["average_transaction"]}

ИНФОРМАЦИЯ О ДАННЫХ

{transaction_note}

Используй эти показатели как фактические
данные компании.

Не придумывай другие финансовые показатели.

Не смешивай данные с другими периодами.

Не утверждай, что бизнес не работал,
если за период нет транзакций.

Отсутствие транзакций означает только
отсутствие зарегистрированных финансовых операций.
"""


def get_comparison_context(
    db: Session,
    user_id: int,
    periods,
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

    period_1_start, period_1_end = periods[0]
    period_2_start, period_2_end = periods[1]

    transactions_1 = get_transactions(
        db=db,
        company_id=company.id,
        start_date=period_1_start,
        end_date=period_1_end,
    )

    transactions_2 = get_transactions(
        db=db,
        company_id=company.id,
        start_date=period_2_start,
        end_date=period_2_end,
    )

    financials_1 = calculate_summary(
        transactions_1
    )

    financials_2 = calculate_summary(
        transactions_2
    )

    cash_flow_1 = calculate_cash_flow(
        transactions_1
    )

    cash_flow_2 = calculate_cash_flow(
        transactions_2
    )

    expenses_1 = (
        calculate_expenses_by_category(
            transactions_1
        )
    )

    expenses_2 = (
        calculate_expenses_by_category(
            transactions_2
        )
    )

    revenue_1 = (
        calculate_revenue_by_category(
            transactions_1
        )
    )

    revenue_2 = (
        calculate_revenue_by_category(
            transactions_2
        )
    )

    kpi_1 = calculate_kpi(
        transactions_1
    )

    kpi_2 = calculate_kpi(
        transactions_2
    )

    def format_categories(
        categories,
        empty_text,
    ):
        if not categories:
            return empty_text

        return "\n".join(
            f"- {category}: {amount}"
            for category, amount
            in categories.items()
        )

    def format_financial_period(
        number: int,
        start_date: datetime,
        end_date: datetime,
        summary: dict,
        cash_flow: dict,
        expenses: dict,
        revenue: dict,
        kpi: dict,
        transaction_count: int,
    ) -> str:

        if transaction_count == 0:
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
{transaction_count}

Доход:
{summary["total_income"]}

Расход:
{summary["total_expense"]}

Прибыль:
{summary["profit"]}

Маржа прибыли:
{summary["profit_margin"]}%

Cash Flow:

Денежный приток:
{cash_flow["cash_inflow"]}

Денежный отток:
{cash_flow["cash_outflow"]}

Чистый денежный поток:
{cash_flow["net_cash_flow"]}

Расходы по категориям:

{format_categories(
    expenses,
    "Расходов нет.",
)}

Доходы по категориям:

{format_categories(
    revenue,
    "Доходов нет.",
)}

KPI:

Средний доход на транзакцию:
{kpi["average_income_transaction"]}

Средний расход на транзакцию:
{kpi["average_expense_transaction"]}

Средний размер транзакции:
{kpi["average_transaction"]}

Комментарий:

{transaction_note}
"""

    return f"""
ФИНАНСОВЫЙ КОНТЕКСТ ДЛЯ СРАВНЕНИЯ

Компания:
{company.name}

Валюта:
{company.currency}

{format_financial_period(
    1,
    period_1_start,
    period_1_end,
    financials_1,
    cash_flow_1,
    expenses_1,
    revenue_1,
    kpi_1,
    len(transactions_1),
)}

{format_financial_period(
    2,
    period_2_start,
    period_2_end,
    financials_2,
    cash_flow_2,
    expenses_2,
    revenue_2,
    kpi_2,
    len(transactions_2),
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

9. Можешь сравнивать:
   - доход;
   - расход;
   - прибыль;
   - маржу;
   - Cash Flow;
   - категории расходов;
   - категории доходов;
   - KPI.

10. Не придумывай отсутствующие показатели.

11. Не делай вывод о причинах изменения
    показателей без подтверждающих данных.
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

    # Определяем сравнение периодов
    comparison_periods = (
        parse_comparison_periods(
            message
        )
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

        # Определяем обычный период
        start_date, end_date = (
            parse_date_range(
                message
            )
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

        response = (
            client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
            )
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