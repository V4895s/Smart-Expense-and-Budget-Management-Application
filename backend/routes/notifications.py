import logging

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db

from models.notification import Notification
from models.user import User

from schemas.notification import NotificationResponse

from security import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


def get_own_notification(
    db: Session,
    notification_id: str,
    user_id: str,
):

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return notification


@router.get(
    "",
    response_model=list[NotificationResponse],
)
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    query = select(Notification).where(
        Notification.user_id == current_user.id
    )

    if unread_only:
        query = query.where(
            Notification.read_at.is_(None)
        )

    try:
        rows = db.scalars(
            query
            .order_by(Notification.created_at.desc())
            .limit(100)
        ).all()

        return rows

    except SQLAlchemyError:

        logger.exception(
            "Could not list notifications"
        )

        raise HTTPException(
            status_code=503,
            detail="Could not load notifications. Please try again.",
        ) from None


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    notification = get_own_notification(
        db,
        notification_id,
        current_user.id,
    )

    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(notification)

        return notification

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "Could not mark notification as read"
        )

        raise HTTPException(
            status_code=503,
            detail="Could not update notification. Please try again.",
        ) from None