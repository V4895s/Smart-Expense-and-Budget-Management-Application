from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from validation import clean_text

TransactionType = Literal["income", "expense"]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: TransactionType

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return clean_text(value, field="Category name", max_length=50)


class CategoryResponse(BaseModel):
    id: str
    name: str
    type: TransactionType
    is_default: bool
