from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from db import Base, SessionLocal, engine
from errors import validation_error_handler
from routes.auth import router as auth_router
from routes.categories import router as categories_router
from routes.expenses import router as expenses_router
from routes.income import router as income_router
from routes.transactions import router as transactions_router
from services_categories import seed_default_categories
from routes.budgets import router as budgets_router
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

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(income_router)
app.include_router(expenses_router)
app.include_router(transactions_router)
app.include_router(budgets_router)

@app.get("/")
def root():
    return {"message": "PennyWise API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
