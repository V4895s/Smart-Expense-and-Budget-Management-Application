import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import db
import main
from db import Base, get_db
from security import get_current_user


def _make_user(session, email, name):
    from models.user import User

    user = User(full_name=name, email=email, password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import models  # noqa: F401  (registers all models)

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def users(session_factory):
    with session_factory() as session:
        alice = _make_user(session, "alice@example.com", "Alice")
        bob = _make_user(session, "bob@example.com", "Bob")
        return {"alice": alice.id, "bob": bob.id}


@pytest.fixture()
def make_client(session_factory, users):
    """Return a function that builds a TestClient authenticated as a given user."""
    from models.user import User

    def _make(name="alice"):
        def override_db():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        def override_user():
            with session_factory() as session:
                return session.get(User, users[name])

        main.app.dependency_overrides[get_db] = override_db
        main.app.dependency_overrides[get_current_user] = override_user
        return TestClient(main.app)

    yield _make
    main.app.dependency_overrides.clear()


@pytest.fixture()
def client(make_client):
    return make_client("alice")


@pytest.fixture()
def cat():
    """Look up a default category id by (name, type)."""

    def _cat(client, name, tx_type):
        for c in client.get("/categories").json():
            if c["name"] == name and c["type"] == tx_type:
                return c["id"]
        raise AssertionError(f"category {name}/{tx_type} not found")

    return _cat


@pytest.fixture(autouse=True)
def _seed(session_factory):
    from services_categories import seed_default_categories

    with session_factory() as session:
        seed_default_categories(session)
