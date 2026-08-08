from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3
    )