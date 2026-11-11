import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from schemas.transaction import Amount, MoneyOut
from validation import check_transaction_date, clean_text

Frequency = Literal["daily", "weekly", "monthly", "yearly"]


class RecurringCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["income", "expense"]
    amount: Amount
    category_id: str
    description: str = ""
    frequency: Frequency
    start_date: dt.date
    end_date: dt.date | None = None

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, value):
        return clean_text(value, field="Category", max_length=36)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        return clean_text(value, field="Description", max_length=200, allow_empty=True)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates(cls, value):
        return None if value is None else check_transaction_date(value)

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date.")
        return self


class RecurringUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class RecurringResponse(BaseModel):
    id: str
    type: Literal["income", "expense"]
    amount: MoneyOut
    category_id: str
    category_name: str
    description: str
    frequency: Frequency
    start_date: dt.date
    end_date: dt.date | None
    next_run_date: dt.date
    is_active: bool
