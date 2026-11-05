from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from validation import clean_text

GoalAmount = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False),
]

ContributionAmount = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False),
]


class SavingsGoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    target_amount: GoalAmount
    current_amount: Annotated[
        Decimal,
        Field(
            default=Decimal("0.00"),
            ge=0,
            max_digits=12,
            decimal_places=2,
            allow_inf_nan=False,
        ),
    ] = Decimal("0.00")
    target_date: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return clean_text(value, field="Goal name", max_length=100)


class SavingsGoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    target_amount: GoalAmount | None = None
    current_amount: Annotated[
        Decimal,
        Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False),
    ] | None = None
    target_date: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return clean_text(value, field="Goal name", max_length=100)


class SavingsContribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: ContributionAmount


class SavingsGoalResponse(BaseModel):
    id: str
    name: str
    target_amount: float
    current_amount: float
    target_date: date | None
    progress_percent: float
    status: str
    created_at: str