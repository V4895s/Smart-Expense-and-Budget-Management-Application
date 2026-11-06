
import routes.auth as auth
import main

from fastapi.testclient import TestClient


def test_update_profile_success(client, session_factory, monkeypatch):
    monkeypatch.setattr(auth, "SessionLocal", session_factory)

    response = client.put(
        "/auth/me",
        json={
            "full_name": "  Alice Updated  ",
            "email": "ALICE.NEW@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Alice Updated"
    assert response.json()["email"] == "alice.new@example.com"

    from models.user import User

    with session_factory() as session:
        user = session.query(User).filter_by(
            email="alice.new@example.com"
        ).first()

        assert user is not None
        assert user.full_name == "Alice Updated"


def test_update_profile_rejects_duplicate_email(
    client, session_factory, monkeypatch
):
    monkeypatch.setattr(auth, "SessionLocal", session_factory)

    response = client.put(
        "/auth/me",
        json={
            "full_name": "Alice",
            "email": "bob@example.com",
        },
    )

    assert response.status_code == 409


def test_update_profile_rejects_invalid_input(client):
    response = client.put(
        "/auth/me",
        json={
            "full_name": "A",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 400


def test_update_profile_requires_authentication():
    with TestClient(main.app) as unauthenticated_client:
        response = unauthenticated_client.put(
            "/auth/me",
            json={
                "full_name": "Alice Updated",
                "email": "alice@example.com",
            },
        )

    assert response.status_code == 401
