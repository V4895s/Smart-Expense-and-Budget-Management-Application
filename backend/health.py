"""Health check used by uptime monitoring (SEA-NF-002)."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

import db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def check_database() -> bool:
    if db.SessionLocal is None:
        return False
    try:
        with db.SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # any failure means "not healthy"
        logger.error("Health check database failure: %s", type(exc).__name__)
        return False


@router.get("/health")
def health_check():
    if check_database():
        return {"status": "healthy", "database": "up"}
    return JSONResponse(
        status_code=503,
        content={
            "status": "unhealthy",
            "database": "down",
            "code": "SERVICE_UNAVAILABLE",
            "message": "The service is temporarily unavailable.",
        },
    )
