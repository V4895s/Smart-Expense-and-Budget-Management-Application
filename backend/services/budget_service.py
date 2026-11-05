import calendar

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.budget import Budget
from models.transaction import Transaction


def get_period_dates(
    period: str,
    today: date | None = None,
) -> tuple[date, date]:

    today = today or date.today()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]

    return start, today.replace(day=last_day)


def get_spending(
    db: Session,
    *,
    user_id: str,
    category_id: str,
    start: date,
    end: date,
) -> Decimal:

    result = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
    )

    return Decimal(str(result or 0))


def get_budget_spending(
    db: Session,
    budget: Budget,
) -> tuple[date, date, Decimal]:

    start, end = get_period_dates(budget.period)

    spent = get_spending(
        db,
        user_id=budget.user_id,
        category_id=budget.category_id,
        start=start,
        end=end,
    )

    return start, end, spent