from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models.category import Category
from models.transaction import Transaction
from models.user import User
from routes.transaction_router import to_response
from schemas.transaction import TransactionResponse
from security import get_current_user

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionResponse])
def list_all_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Combined income + expense list for the logged-in user, newest first."""
    rows = db.execute(
        select(Transaction, Category.name)
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
    ).all()
    return [to_response(tx, name) for tx, name in rows]
