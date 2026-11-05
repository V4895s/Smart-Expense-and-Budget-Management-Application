"""Budget alert generation and notification persistence."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.budget import Budget
from models.category import Category
from models.notification import Notification

from services.budget_service import get_budget_spending


# Product decision: approaching the limit at 80%, exceeded at 100%.
BUDGET_ALERT_THRESHOLDS = (
    Decimal("0.80"),
    Decimal("1.00"),
)


def evaluate_budget_alerts(
    db: Session,
    *,
    user_id: str,
    category_id: str | None = None,
) -> int:
    """
    Create one in-app alert per budget, period and threshold.

    Call this inside the transaction that creates/updates an expense or budget.
    Notification rows therefore commit or roll back with the triggering change.
    """

    query = select(Budget).where(
        Budget.user_id == user_id
    )

    if category_id is not None:
        query = query.where(
            Budget.category_id == category_id
        )

    budgets = db.scalars(query).all()

    created = 0

    for budget in budgets:

        start, end, spent = get_budget_spending(
            db,
            budget,
        )

        if spent <= 0 or budget.amount <= 0:
            continue

        category = db.get(
            Category,
            budget.category_id,
        )

        category_name = (
            category.name
            if category
            else budget.name
        )

        ratio = spent / Decimal(str(budget.amount))

        for threshold in BUDGET_ALERT_THRESHOLDS:

            if ratio < threshold:
                continue

            percent = int(threshold * 100)

            # One alert per budget, period and threshold.
            dedupe_key = (
                f"budget:{budget.id}:"
                f"{start.isoformat()}:"
                f"{end.isoformat()}:"
                f"{percent}"
            )

            existing = db.scalar(
                select(Notification.id).where(
                    Notification.dedupe_key == dedupe_key
                )
            )

            if existing:
                continue

            if threshold == Decimal("0.80"):

                title = (
                    f"{category_name} budget almost used"
                )

                message = (
                    f"You've used {ratio * 100:.0f}% of your "
                    f"{budget.period} {category_name} budget "
                    f"({spent:.2f} of {budget.amount:.2f})."
                )

                level = "warning"

            else:

                title = (
                    f"{category_name} budget limit reached"
                )

                message = (
                    f"You've used {ratio * 100:.0f}% of your "
                    f"{budget.period} {category_name} budget "
                    f"({spent:.2f} of {budget.amount:.2f})."
                )

                level = "danger"

            try:
                # A savepoint prevents a concurrent duplicate alert from
                # rolling back the expense or budget update itself.
                with db.begin_nested():

                    db.add(
                        Notification(
                            user_id=user_id,
                            budget_id=budget.id,
                            dedupe_key=dedupe_key,
                            title=title,
                            message=message,
                            level=level,
                        )
                    )

                    db.flush()

                created += 1

            except IntegrityError:
                # Another request may have inserted the same alert.
                continue

    return created