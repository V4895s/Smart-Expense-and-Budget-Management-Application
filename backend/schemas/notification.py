from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    budget_id: str | None
    title: str
    message: str
    level: Literal["warning", "danger"]
    created_at: datetime
    read_at: datetime | None