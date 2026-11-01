import logging
import calendar

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db
from models.category import Category
from models.budget import Budget
from models.transaction import Transaction
from models.user import User
from schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
)
from security import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/budgets", tags=["Budgets"])


def get_period_dates(period: str):
    today = date.today()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)

    else:
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)

    return start, end


def get_spending(
    db: Session,
    budget: Budget,
    start: date,
    end: date,
) -> Decimal:
    result = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == budget.user_id,
            Transaction.category_id == budget.category_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
    )

    return Decimal(str(result or 0))


def to_response(db: Session, budget: Budget) -> BudgetResponse:
    start, end = get_period_dates(budget.period)

    spent = get_spending(db, budget, start, end)
    remaining = budget.amount - spent

    category = db.get(Category, budget.category_id)

    return BudgetResponse(
        id=budget.id,
        name=budget.name,
        category_id=budget.category_id,
        category_name=category.name if category else "Unknown",
        amount=float(budget.amount),
        period=budget.period,
        spent=float(spent),
        remaining=float(remaining),
        period_start=start.isoformat(),
        period_end=end.isoformat(),
    )


def get_own_budget(
    db: Session,
    budget_id: str,
    user_id: str,
) -> Budget:
    budget = db.scalar(
        select(Budget).where(
            Budget.id == budget_id,
            Budget.user_id == user_id,
        )
    )

    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )

    return budget


def db_error(action: str, exc: SQLAlchemyError):
    logger.error(
        "Database error while %s: %s",
        action,
        type(exc).__name__,
    )

    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The request could not be completed. Please try again later.",
    )


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = get_valid_category(db, payload.category_id, current_user.id)
    budget = Budget(
        user_id=current_user.id,
        category_id=category.id,
        name=payload.name,
        amount=payload.amount,
        period=payload.period,
    )

    try:
        db.add(budget)
        db.commit()
        db.refresh(budget)

        return to_response(db, budget)

    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("creating budget", exc) from None

def get_valid_category(
    db: Session,
    category_id: str,
    user_id: str,
) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.type == "expense",
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
        )
    )

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Expense category not found.",
        )

    return category

@router.get(
    "",
    response_model=list[BudgetResponse],
)
def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        budgets = db.scalars(
            select(Budget)
            .where(Budget.user_id == current_user.id)
            .order_by(Budget.created_at.desc())
        ).all()

        return [
            to_response(db, budget)
            for budget in budgets
        ]

    except SQLAlchemyError as exc:
        raise db_error("listing budgets", exc) from None


@router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
)
def get_budget(
    budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = get_own_budget(db, budget_id, current_user.id)
    return to_response(db, budget)


@router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
)
def update_budget(
    budget_id: str,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = get_own_budget(db, budget_id, current_user.id)

    fields = payload.model_fields_set

    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update.",
        )

    for field in fields:
        value = getattr(payload, field)
    
        if value is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null.",
            )
    
        if field == "category_id":
            category = get_valid_category(db, value, current_user.id)
            value = category.id
    
        setattr(budget, field, value)

    try:
        db.commit()
        db.refresh(budget)

        return to_response(db, budget)

    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("updating budget", exc) from None


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_budget(
    budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = get_own_budget(db, budget_id, current_user.id)

    try:
        db.delete(budget)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("deleting budget", exc) from None