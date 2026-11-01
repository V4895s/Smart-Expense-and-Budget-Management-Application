import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db
from models.category import Category
from models.user import User
from schemas.category import CategoryCreate, CategoryResponse, TransactionType
from security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["Categories"])


def to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        type=category.type,
        is_default=category.user_id is None,
    )


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    type: TransactionType | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Category).where(
        or_(Category.user_id.is_(None), Category.user_id == current_user.id)
    )
    if type is not None:
        query = query.where(Category.type == type)

    categories = db.scalars(query.order_by(Category.name)).all()
    return [to_response(c) for c in categories]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duplicate = db.scalar(
        select(Category).where(
            Category.type == payload.type,
            func.lower(Category.name) == payload.name.lower(),
            or_(Category.user_id.is_(None), Category.user_id == current_user.id),
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        )

    category = Category(name=payload.name, type=payload.type, user_id=current_user.id)
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        ) from None
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error creating category: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save the category. Please try again later.",
        ) from None

    return to_response(category)
