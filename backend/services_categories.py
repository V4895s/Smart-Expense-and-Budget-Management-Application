"""Backward-compatible imports for the category application service.

New code should import from services.category_service.
"""

from services.category_service import (
    get_visible_category,
    seed_default_categories,
)

__all__ = [
    "get_visible_category",
    "seed_default_categories",
]