
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

engine = None
SessionLocal = None

if DATABASE_URL:
    _engine_kwargs = {"pool_pre_ping": True}
    if DATABASE_URL.startswith("postgresql"):
        # Fail fast instead of hanging when the database is unreachable (SEA-NF-002).
        _engine_kwargs.update(
            pool_recycle=300,
            pool_timeout=10,
            connect_args={"connect_timeout": 10},
        )
    engine = create_engine(DATABASE_URL, **_engine_kwargs)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )


class Base(DeclarativeBase):
    pass


def get_db():
    if SessionLocal is None:
        raise RuntimeError(
            "Database is not configured. Check backend/.env."
        )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
