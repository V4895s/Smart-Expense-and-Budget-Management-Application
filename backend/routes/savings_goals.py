import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db
from models.savings_goal import SavingsGoal
from models.user import User
from schemas.savings_goal import (
    SavingsContribution,
    SavingsGoalCreate,
    SavingsGoalResponse,
    SavingsGoalUpdate,
)
from security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/savings-goals", tags=["Savings Goals"])


def to_response(goal: SavingsGoal) -> SavingsGoalResponse:
    target = Decimal(str(goal.target_amount))
    current = Decimal(str(goal.current_amount))
    progress = min(100.0, float((current / target) * 100)) if target > 0 else 0.0

    return SavingsGoalResponse(
        id=goal.id,
        name=goal.name,
        target_amount=float(target),
        current_amount=float(current),
        target_date=goal.target_date,
        progress_percent=round(progress, 2),
        status="completed" if current >= target else "active",
        created_at=goal.created_at.isoformat(),
    )


def get_own_goal(db: Session, goal_id: str, user_id: str) -> SavingsGoal:
    goal = db.scalar(
        select(SavingsGoal).where(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == user_id,
        )
    )

    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found.")

    return goal


def db_error(action: str, exc: SQLAlchemyError) -> HTTPException:
    logger.error("Database error while %s: %s", action, type(exc).__name__)

    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The request could not be completed. Please try again later.",
    )


@router.post(
    "",
    response_model=SavingsGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_goal(
    payload: SavingsGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.current_amount > payload.target_amount:
        raise HTTPException(
            status_code=400,
            detail="Saved amount cannot exceed the target amount.",
        )

    goal = SavingsGoal(
        user_id=current_user.id,
        name=payload.name,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        target_date=payload.target_date,
    )

    try:
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return to_response(goal)
    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("creating savings goal", exc) from None


@router.get("", response_model=list[SavingsGoalResponse])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        goals = db.scalars(
            select(SavingsGoal)
            .where(SavingsGoal.user_id == current_user.id)
            .order_by(SavingsGoal.created_at.desc())
        ).all()

        return [to_response(goal) for goal in goals]
    except SQLAlchemyError as exc:
        raise db_error("listing savings goals", exc) from None


@router.get("/{goal_id}", response_model=SavingsGoalResponse)
def get_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return to_response(get_own_goal(db, goal_id, current_user.id))


@router.put("/{goal_id}", response_model=SavingsGoalResponse)
def update_goal(
    goal_id: str,
    payload: SavingsGoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = get_own_goal(db, goal_id, current_user.id)
    fields = payload.model_fields_set

    if not fields:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update.",
        )

    for field in fields:
        value = getattr(payload, field)

        if value is None and field != "target_date":
            raise HTTPException(
                status_code=400,
                detail=f"{field} cannot be null.",
            )

        setattr(goal, field, value)

    if goal.current_amount > goal.target_amount:
        raise HTTPException(
            status_code=400,
            detail="Saved amount cannot exceed the target amount.",
        )

    try:
        db.commit()
        db.refresh(goal)
        return to_response(goal)
    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("updating savings goal", exc) from None


@router.post(
    "/{goal_id}/contributions",
    response_model=SavingsGoalResponse,
)
def add_contribution(
    goal_id: str,
    payload: SavingsContribution,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the row on PostgreSQL so simultaneous contributions cannot
    # overwrite one another.
    goal = db.scalar(
        select(SavingsGoal)
        .where(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == current_user.id,
        )
        .with_for_update()
    )

    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found.")

    if goal.current_amount + payload.amount > goal.target_amount:
        raise HTTPException(
            status_code=400,
            detail="Contribution exceeds the remaining amount for this goal.",
        )

    try:
        goal.current_amount += payload.amount
        db.commit()
        db.refresh(goal)
        return to_response(goal)
    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("adding savings contribution", exc) from None


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = get_own_goal(db, goal_id, current_user.id)

    try:
        db.delete(goal)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise db_error("deleting savings goal", exc) from None