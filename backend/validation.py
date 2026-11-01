"""Shared server-side input validation helpers (SEA-SR-004)."""

import re
from datetime import date, timedelta

# Control characters (except tab/newline handled separately) and NUL bytes
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MIN_TRANSACTION_DATE = date(2000, 1, 1)
MAX_FUTURE_DAYS = 365


def clean_text(value: str, *, field: str, max_length: int, allow_empty: bool = False) -> str:
    """Trim, collapse whitespace and reject control characters / over-long text."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")

    if _CONTROL_CHARS.search(value):
        raise ValueError(f"{field} contains invalid characters.")

    value = re.sub(r"\s+", " ", value).strip()

    if not value and not allow_empty:
        raise ValueError(f"{field} must not be empty.")

    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters.")

    return value


def check_transaction_date(value: date) -> date:
    if value < MIN_TRANSACTION_DATE:
        raise ValueError("Date must be on or after 2000-01-01.")
    if value > date.today() + timedelta(days=MAX_FUTURE_DAYS):
        raise ValueError("Date cannot be more than one year in the future.")
    return value
