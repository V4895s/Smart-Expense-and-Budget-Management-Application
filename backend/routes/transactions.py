"""Combined transactions list with search and filter (SEA-F-013)."""

import datetime as dt
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from db import get_db
from models.category import Category
from models.transaction import Transaction
from models.user import User
from routes.transaction_router import to_response
from schemas.transaction import TransactionResponse
from security import get_current_user
from validation import clean_text

router = APIRouter(prefix="/transactions", tags=["Transactions"])

MAX_PAGE_SIZE = 500


def _like_pattern(term: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@router.get("", response_model=list[TransactionResponse])
def list_all_transactions(
    q: str | None = Query(None, max_length=100, description="Matches description or category name"),
    type: Literal["income", "expense"] | None = Query(None),
    category_id: str | None = Query(None, max_length=36),
    category: str | None = Query(None, max_length=100, description="Exact category name"),
    date_from: dt.date | None = Query(None),
    date_to: dt.date | None = Query(None),
    min_amount: Decimal | None = Query(None, ge=0, max_digits=12, decimal_places=2),
    max_amount: Decimal | None = Query(None, ge=0, max_digits=12, decimal_places=2),
    limit: int | None = Query(None, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Income + expense list for the logged-in user, newest first.

    Every filter is optional; with none given the full list is returned.
    Always scoped to the authenticated user (SEA-SR-003); all values are bound
    parameters, never string-built SQL (SEA-SR-004).
    """
    if date_from and date_to and date_from > date_to:
        raise _bad_request("date_from must not be after date_to.")
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise _bad_request("min_amount must not be greater than max_amount.")

    stmt = (
        select(Transaction, Category.name)
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == current_user.id)
    )

    if q is not None:
        try:
            term = clean_text(q, field="Search", max_length=100, allow_empty=True)
        except ValueError as exc:
            raise _bad_request(str(exc)) from None
        if term:
            pattern = _like_pattern(term)
            stmt = stmt.where(
                or_(
                    Transaction.description.ilike(pattern, escape="\\"),
                    Category.name.ilike(pattern, escape="\\"),
                )
            )
    if type:
        stmt = stmt.where(Transaction.type == type)
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if category:
        stmt = stmt.where(func.lower(Category.name) == category.strip().lower())
    if date_from:
        stmt = stmt.where(Transaction.transaction_date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.transaction_date <= date_to)
    if min_amount is not None:
        stmt = stmt.where(Transaction.amount >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(Transaction.amount <= max_amount)

    stmt = stmt.order_by(
        Transaction.transaction_date.desc(),
        Transaction.created_at.desc(),
        Transaction.id,
    )
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    elif offset:
        stmt = stmt.offset(offset)

    rows = db.execute(stmt).all()
    return [to_response(tx, name) for tx, name in rows]
