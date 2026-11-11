"""Recurring income and expenses (SEA-F-016)."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db
from models.category import Category
from models.recurring_transaction import RecurringTransaction
from models.user import User
from routes.transaction_router import _db_unavailable, _valid_category
from schemas.recurring import RecurringCreate, RecurringResponse, RecurringUpdate
from security import get_current_user
from services.recurring_service import next_occurrence, run_due_rules

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recurring", tags=["Recurring"])


def to_response(rule: RecurringTransaction, category_name: str) -> RecurringResponse:
    return RecurringResponse(
        id=rule.id,
        type=rule.type,
        amount=rule.amount,
        category_id=rule.category_id,
        category_name=category_name,
        description=rule.description,
        frequency=rule.frequency,
        start_date=rule.start_date,
        end_date=rule.end_date,
        next_run_date=rule.next_run_date,
        is_active=rule.is_active,
    )


def _get_own(db: Session, rule_id: str, user_id: str) -> RecurringTransaction:
    # Scoped to the logged-in user: other users' rules look like 404 (SEA-SR-003).
    rule = db.scalar(
        select(RecurringTransaction).where(
            RecurringTransaction.id == rule_id,
            RecurringTransaction.user_id == user_id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Recurring transaction not found.")
    return rule


@router.post("", response_model=RecurringResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RecurringCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = _valid_category(db, payload.category_id, current_user.id, payload.type)
    rule = RecurringTransaction(
        user_id=current_user.id,
        type=payload.type,
        amount=payload.amount,
        category_id=category.id,
        description=payload.description,
        frequency=payload.frequency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        next_run_date=payload.start_date,
    )
    try:
        db.add(rule)
        db.flush()
        run_due_rules(db, current_user.id)  # a rule starting today/in the past posts at once
        db.commit()
        db.refresh(rule)
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_unavailable("creating recurring transaction", exc) from None
    return to_response(rule, category.name)


@router.get("", response_model=list[RecurringResponse])
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(RecurringTransaction, Category.name)
        .join(Category, Category.id == RecurringTransaction.category_id)
        .where(RecurringTransaction.user_id == current_user.id)
        .order_by(RecurringTransaction.is_active.desc(), RecurringTransaction.next_run_date)
    ).all()
    return [to_response(rule, name) for rule, name in rows]


@router.post("/process")
def process_due(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create any transactions that are due. The frontend calls this when the page opens."""
    try:
        created = run_due_rules(db, current_user.id)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_unavailable("processing recurring transactions", exc) from None
    return {"created": created}


@router.put("/{rule_id}", response_model=RecurringResponse)
def update_rule(
    rule_id: str,
    payload: RecurringUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause or resume a rule. Resuming skips occurrences missed while it was paused."""
    rule = _get_own(db, rule_id, current_user.id)
    if payload.is_active and not rule.is_active:
        today = date.today()
        while rule.next_run_date < today:
            rule.next_run_date = next_occurrence(
                rule.next_run_date, rule.frequency, rule.start_date.day
            )
    rule.is_active = payload.is_active
    try:
        db.commit()
        db.refresh(rule)
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_unavailable("updating recurring transaction", exc) from None
    return to_response(rule, db.get(Category, rule.category_id).name)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes the rule only; transactions it already created are kept."""
    rule = _get_own(db, rule_id, current_user.id)
    try:
        db.delete(rule)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise _db_unavailable("deleting recurring transaction", exc) from None
