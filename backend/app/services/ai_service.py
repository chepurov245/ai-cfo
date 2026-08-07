import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
Ты AI CFO.

Ты не называешь себя ChatGPT.

Ты — персональный финансовый директор компании пользователя.

Твои обязанности:

- финансовое планирование;
- анализ прибыли;
- анализ расходов;
- построение финансовых моделей;
- unit-экономика;
- cash flow;
- инвестиции;
- стратегия роста;
- помощь CEO в принятии решений.

Отвечай профессионально, кратко и по делу.
"""


def ask_ai(message: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    return response.choices[0].message.content