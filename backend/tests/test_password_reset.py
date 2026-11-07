import logging
import hashlib
import re
from datetime import datetime, timedelta, timezone

import pytest

import routes.auth as auth
from models.password_reset_token import PasswordResetToken
from security import verify_password


@pytest.fixture()
def reset_setup(session_factory, monkeypatch, caplog):
    monkeypatch.setattr(auth, "SessionLocal", session_factory)
    monkeypatch.setattr(auth, "PASSWORD_RESET_CONSOLE", True)
    monkeypatch.setattr(
        auth, "FRONTEND_URL", "http://localhost:3000"
    )

    caplog.set_level(logging.INFO, logger="routes.auth")


def extract_token(caplog):
    match = re.search(r"[?&]token=([A-Za-z0-9_-]+)", caplog.text)
    assert match is not None, "Reset token was not logged."
    return match.group(1)


def request_reset(client, email):
    return client.post(
        "/auth/password-reset/request",
        json={"email": email},
    )


def confirm_reset(client, token, password="NewPassword123"):
    return client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "password": password,
            "confirm_password": password,
        },
    )


def test_reset_request_returns_same_message_for_known_and_unknown_email(
    client, reset_setup
):
    known_response = request_reset(client, "alice@example.com")
    unknown_response = request_reset(client, "unknown@example.com")

    assert known_response.status_code == 200
    assert unknown_response.status_code == 200
    assert known_response.json() == unknown_response.json()


def test_reset_request_stores_only_token_hash(
    client, session_factory, reset_setup, caplog
):
    response = request_reset(client, "alice@example.com")

    assert response.status_code == 200

    raw_token = extract_token(caplog)
    expected_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with session_factory() as session:
        stored_token = session.query(PasswordResetToken).filter_by(
            token_hash=expected_hash
        ).first()

        assert stored_token is not None
        assert stored_token.token_hash != raw_token
        assert stored_token.used_at is None

        remaining_seconds = (
            stored_token.expires_at.replace(tzinfo=timezone.utc)
            - datetime.now(timezone.utc)
        ).total_seconds()

        assert 0 < remaining_seconds <= 15 * 60


def test_password_reset_successfully_changes_password(
    client, session_factory, reset_setup, caplog
):
    request_response = request_reset(
        client, "alice@example.com"
    )
    assert request_response.status_code == 200

    raw_token = extract_token(caplog)

    response = confirm_reset(
        client, raw_token, "UpdatedPassword123"
    )

    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()

    from models.user import User

    with session_factory() as session:
        user = session.query(User).filter_by(
            email="alice@example.com"
        ).first()

        assert user is not None
        assert verify_password(
            "UpdatedPassword123", user.password_hash
        )


def test_used_token_cannot_be_reused(
    client, reset_setup, caplog
):
    request_reset(client, "alice@example.com")
    raw_token = extract_token(caplog)

    first_response = confirm_reset(client, raw_token)
    second_response = confirm_reset(client, raw_token)

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_invalid_token_is_rejected(client, reset_setup):
    response = confirm_reset(
        client, "this-is-not-a-valid-reset-token"
    )

    assert response.status_code == 400


def test_expired_token_is_rejected(
    client, session_factory, reset_setup
):
    from models.user import User

    raw_token = "expired-test-token"
    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with session_factory() as session:
        user = session.query(User).filter_by(
            email="alice@example.com"
        ).first()

        expired_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc)
            - timedelta(minutes=1),
        )

        session.add(expired_token)
        session.commit()

    response = confirm_reset(client, raw_token)

    assert response.status_code == 400


def test_password_mismatch_is_rejected(
    client, reset_setup, caplog
):
    request_reset(client, "alice@example.com")
    raw_token = extract_token(caplog)

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": raw_token,
            "password": "NewPassword123",
            "confirm_password": "DifferentPassword123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match."


def test_new_reset_request_invalidates_previous_token(
    client, reset_setup, caplog
):
    request_reset(client, "alice@example.com")
    first_token = extract_token(caplog)

    caplog.clear()

    request_reset(client, "alice@example.com")
    second_token = extract_token(caplog)

    assert first_token != second_token

    old_response = confirm_reset(client, first_token)
    new_response = confirm_reset(client, second_token)

    assert old_response.status_code == 400
    assert new_response.status_code == 200


def test_reset_request_does_not_log_link_when_console_disabled(
    client, reset_setup, monkeypatch, caplog
):
    monkeypatch.setattr(auth, "PASSWORD_RESET_CONSOLE", False)

    response = request_reset(client, "alice@example.com")

    assert response.status_code == 200
    assert "Development password reset link" not in caplog.text
