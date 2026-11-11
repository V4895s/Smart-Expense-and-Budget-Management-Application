"""Schedule logic for recurring transactions (SEA-F-016)."""

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.recurring_transaction import RecurringTransaction
from models.transaction import Transaction
from services.notification_service import evaluate_budget_alerts

MAX_CATCH_UP = 366  # safety cap: occurrences created per rule per call


def next_occurrence(current: date, frequency: str, anchor_day: int) -> date:
    """Next run date after `current`. Monthly/yearly clamp to month end (31 Jan -> 28 Feb)."""
    if frequency == "daily":
        return current + timedelta(days=1)
    if frequency == "weekly":
        return current + timedelta(weeks=1)

    months = 1 if frequency == "monthly" else 12
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor_day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def run_due_rules(db: Session, user_id: str, today: date | None = None) -> int:
    """Create a real transaction for every occurrence that is due (including missed ones).

    Does not commit; the caller commits. Returns how many transactions were created.
    """
    today = today or date.today()
    rules = db.scalars(
        select(RecurringTransaction)
        .where(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.next_run_date <= today,
        )
        .with_for_update()
    ).all()

    created = 0
    expense_categories: set[str] = set()

    for rule in rules:
        runs = 0
        while (
            rule.next_run_date <= today
            and (rule.end_date is None or rule.next_run_date <= rule.end_date)
            and runs < MAX_CATCH_UP
        ):
            db.add(
                Transaction(
                    user_id=rule.user_id,
                    type=rule.type,
                    amount=rule.amount,
                    category_id=rule.category_id,
                    description=rule.description,
                    transaction_date=rule.next_run_date,
                )
            )
            created += 1
            runs += 1
            if rule.type == "expense":
                expense_categories.add(rule.category_id)
            rule.next_run_date = next_occurrence(
                rule.next_run_date, rule.frequency, rule.start_date.day
            )

        if rule.end_date is not None and rule.next_run_date > rule.end_date:
            rule.is_active = False

    db.flush()
    for category_id in expense_categories:
        evaluate_budget_alerts(db, user_id=user_id, category_id=category_id)

    return created
