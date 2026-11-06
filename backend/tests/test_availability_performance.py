"""SEA-NF-002 availability and SEA-NF-001 response-time instrumentation."""

import db
import main
from fastapi.testclient import TestClient


def test_health_ok_when_database_reachable(client, session_factory, monkeypatch):
    monkeypatch.setattr(db, "SessionLocal", session_factory)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "database": "up"}


def test_health_503_when_database_unreachable(client, monkeypatch):
    def broken():
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "SessionLocal", broken)
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy" and body["code"] == "SERVICE_UNAVAILABLE"


def test_health_503_when_database_not_configured(client, monkeypatch):
    monkeypatch.setattr(db, "SessionLocal", None)
    assert client.get("/health").status_code == 503


def test_response_time_header_present(client):
    resp = client.get("/")
    assert float(resp.headers["X-Process-Time"]) >= 0


def test_http_errors_use_code_message_envelope(client):
    resp = client.get("/transactions/does-not-exist")
    assert resp.status_code in (404, 405)
    body = resp.json()
    assert body["code"] == f"HTTP_{resp.status_code}" and body["message"] == body["detail"]


def test_database_errors_become_503_envelope(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    def explode(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))

    monkeypatch.setattr(Session, "execute", explode)
    resp = client.get("/transactions")
    assert resp.status_code == 503
    assert resp.json()["code"] == "SERVICE_UNAVAILABLE"
    assert "connection refused" not in resp.text
    assert resp.headers["Retry-After"] == "10"


def test_unexpected_errors_become_500_envelope(make_client, cat, monkeypatch):
    client = make_client("alice")
    client.post(
        "/expenses",
        json={"amount": "10", "category_id": cat(client, "Food", "expense"), "date": "2026-10-01", "description": "x"},
    )
    from routes import transactions as tx_routes

    def explode(*args, **kwargs):
        raise ValueError("secret internal detail")

    monkeypatch.setattr(tx_routes, "to_response", explode)
    resp = TestClient(main.app, raise_server_exceptions=False).get("/transactions")
    assert resp.status_code == 500
    assert resp.json()["code"] == "INTERNAL_ERROR"
    assert "secret internal detail" not in resp.text
