from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from validation import clean_text

BudgetAmount = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False),
]


class BudgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    category_id: str
    amount: BudgetAmount
    period: Literal["weekly", "monthly"]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, field="Budget name", max_length=100)


class BudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    category_id: str | None = None
    amount: BudgetAmount | None = None
    period: Literal["weekly", "monthly"] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            return value
        return clean_text(value, field="Budget name", max_length=100)


class BudgetResponse(BaseModel):
    id: str
    name: str
    category_id: str
    category_name: str
    amount: float
    period: Literal["weekly", "monthly"]
    spent: float
    remaining: float
    period_start: str
    period_end: str