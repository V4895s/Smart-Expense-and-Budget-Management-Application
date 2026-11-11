import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from routes.recurring import router as recurring_router

from contextlib import asynccontextmanager

from db import Base, SessionLocal, engine
from errors import (
    database_error_handler,
    http_exception_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from health import router as health_router
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from routes.auth import router as auth_router
from routes.categories import router as categories_router
from routes.expenses import router as expenses_router
from routes.income import router as income_router
from routes.transactions import router as transactions_router
from services.category_service import seed_default_categories
from routes.budgets import router as budgets_router
from routes.savings_goals import router as savings_goals_router
from routes.notifications import router as notifications_router
@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create any missing tables and seed built-in categories (idempotent).
    if engine is not None and SessionLocal is not None:
        import models  # noqa: F401  (registers all models)

        Base.metadata.create_all(engine)
        with SessionLocal() as session:
            seed_default_categories(session)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="PennyWise API",
    description="Backend API for Smart Expense and Budget Management",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://smart-expense-and-budget-management.vercel.app",
        "https://smart-expense-and-budget-management-application-bawc0yu3r.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

perf_logger = logging.getLogger("performance")
SLOW_REQUEST_SECONDS = 5.0  # SEA-NF-001: 90% of requests must finish within 5 s


@app.middleware("http")
async def response_time_middleware(request: Request, call_next):
    """Measure every request; expose X-Process-Time and warn on slow ones (SEA-NF-001)."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    if elapsed > SLOW_REQUEST_SECONDS:
        perf_logger.warning("SLOW %s %s %.2fs", request.method, request.url.path, elapsed)
    else:
        perf_logger.info("%s %s %d %.3fs", request.method, request.url.path, response.status_code, elapsed)
    return response


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(income_router)
app.include_router(expenses_router)
app.include_router(transactions_router)
app.include_router(budgets_router)
app.include_router(savings_goals_router)
app.include_router(notifications_router)
app.include_router(recurring_router)


@app.get("/")
def root():
    return {"message": "PennyWise API is running"}
