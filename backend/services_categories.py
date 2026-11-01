from sqlalchemy import select
from sqlalchemy.orm import Session

from models.category import Category

DEFAULT_CATEGORIES = {
    "expense": [
        "Food", "Transport", "Shopping", "Utilities",
        "Entertainment", "Healthcare", "Other",
    ],
    "income": ["Salary", "Freelance", "Other"],
}


def seed_default_categories(db: Session) -> None:
    """Insert built-in categories that do not exist yet (safe to run repeatedly)."""
    existing = {
        (c.name, c.type)
        for c in db.scalars(select(Category).where(Category.user_id.is_(None)))
    }
    for tx_type, names in DEFAULT_CATEGORIES.items():
        for name in names:
            if (name, tx_type) not in existing:
                db.add(Category(name=name, type=tx_type, user_id=None))
    db.commit()


def get_visible_category(db: Session, category_id: str, user_id: str) -> Category | None:
    """A category is visible if it is a default one or owned by the user."""
    category = db.get(Category, category_id)
    if category is None:
        return None
    if category.user_id is not None and category.user_id != user_id:
        return None
    return category
