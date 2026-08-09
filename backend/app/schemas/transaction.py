from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    type: str = Field(
        min_length=1,
        max_length=20
    )

    amount: Decimal = Field(
        gt=0,
        decimal_places=2
    )

    category: str = Field(
        min_length=1,
        max_length=100
    )

    description: str | None = None

    transaction_date: datetime

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        value = value.lower()

        if value not in {"income", "expense"}:
            raise ValueError(
                "type must be either 'income' or 'expense'"
            )

        return value