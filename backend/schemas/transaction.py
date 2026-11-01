import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

from validation import check_transaction_date, clean_text

Amount = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False),
]
MoneyOut = Annotated[Decimal, PlainSerializer(float, return_type=float)]


class _TransactionFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("category_id", check_fields=False)
    @classmethod
    def validate_category_id(cls, value):
        if value is None:
            return value
        return clean_text(value, field="Category", max_length=36)

    @field_validator("description", check_fields=False)
    @classmethod
    def validate_description(cls, value):
        if value is None:
            return value
        return clean_text(value, field="Description", max_length=200, allow_empty=True)

    @field_validator("date", check_fields=False)
    @classmethod
    def validate_date(cls, value):
        if value is None:
            return value
        return check_transaction_date(value)


class TransactionCreate(_TransactionFields):
    amount: Amount
    category_id: str
    date: dt.date
    description: str = ""


class TransactionUpdate(_TransactionFields):
    amount: Amount | None = None
    category_id: str | None = None
    date: dt.date | None = None
    description: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        if any(
            name in self.model_fields_set and getattr(self, name) is None
            for name in ("amount", "category_id", "date")
        ):
            raise ValueError("amount, category_id and date cannot be null.")
        return self


class TransactionResponse(BaseModel):
    id: str
    type: Literal["income", "expense"]
    amount: MoneyOut
    category_id: str
    category_name: str
    date: dt.date
    description: str
