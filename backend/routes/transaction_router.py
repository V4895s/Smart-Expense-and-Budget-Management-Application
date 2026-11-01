"""Router factory shared by /income (SEA-F-005) and /expenses (SEA-F-006)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db
from models.category import Category
from models.transaction import Transaction
from models.user import User
from schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from security import get_current_user
from services_categories import get_visible_category

logger = logging.getLogger(__name__)


def to_response(tx: Transaction, category_name: str) -> TransactionResponse:
    return TransactionResponse(
        id=tx.id,
        type=tx.type,
        amount=tx.amount,
        category_id=tx.category_id,
        category_name=category_name,
        date=tx.transaction_date,
        description=tx.description,
    )


def _db_unavailable(action: str, exc: SQLAlchemyError) -> HTTPException:
    logger.error("Database error while %s: %s", action, type(exc).__name__)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The request could not be completed. Please try again later.",
    )


def _valid_category(db: Session, category_id: str, user_id: str, tx_type: str) -> Category:
    category = get_visible_category(db, category_id, user_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )
    if category.type != tx_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category.name}' cannot be used for {tx_type} transactions.",
        )
    return category


def _get_own(db: Session, tx_id: str, user_id: str, tx_type: str) -> Transaction:
    # Always scoped to the logged-in user and type: other users' records look like 404 (SEA-SR-003).
    tx = db.scalar(
        select(Transaction).where(
            Transaction.id == tx_id,
            Transaction.user_id == user_id,
            Transaction.type == tx_type,
        )
    )
    if tx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found."
        )
    return tx


def build_transaction_router(tx_type: str, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
    def create(
        payload: TransactionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        category = _valid_category(db, payload.category_id, current_user.id, tx_type)
        tx = Transaction(
            user_id=current_user.id,
            type=tx_type,
            amount=payload.amount,
            category_id=category.id,
            description=payload.description,
            transaction_date=payload.date,
        )
        try:
            db.add(tx)
            db.commit()
            db.refresh(tx)
        except SQLAlchemyError as exc:
            db.rollback()
            raise _db_unavailable("creating transaction", exc) from None
        return to_response(tx, category.name)

    @router.get("", response_model=list[TransactionResponse])
    def list_all(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        rows = db.execute(
            select(Transaction, Category.name)
            .join(Category, Category.id == Transaction.category_id)
            .where(Transaction.user_id == current_user.id, Transaction.type == tx_type)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        ).all()
        return [to_response(tx, name) for tx, name in rows]

    @router.get("/{tx_id}", response_model=TransactionResponse)
    def get_one(
        tx_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        tx = _get_own(db, tx_id, current_user.id, tx_type)
        return to_response(tx, db.get(Category, tx.category_id).name)

    @router.put("/{tx_id}", response_model=TransactionResponse)
    def update(
        tx_id: str,
        payload: TransactionUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        tx = _get_own(db, tx_id, current_user.id, tx_type)
        fields = payload.model_fields_set

        if "category_id" in fields:
            category = _valid_category(db, payload.category_id, current_user.id, tx_type)
            tx.category_id = category.id
        if "amount" in fields:
            tx.amount = payload.amount
        if "date" in fields:
            tx.transaction_date = payload.date
        if "description" in fields:
            tx.description = payload.description

        try:
            db.commit()
            db.refresh(tx)
        except SQLAlchemyError as exc:
            db.rollback()
            raise _db_unavailable("updating transaction", exc) from None
        return to_response(tx, db.get(Category, tx.category_id).name)

    @router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(
        tx_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        tx = _get_own(db, tx_id, current_user.id, tx_type)
        try:
            db.delete(tx)
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise _db_unavailable("deleting transaction", exc) from None

    return router
