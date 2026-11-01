import pytest


def payload(category_id, **overrides):
    data = {"amount": "45000.50", "category_id": category_id, "date": "2026-10-25", "description": "Monthly salary"}
    data.update(overrides)
    return data


def test_create_read_update_delete_income(client, cat):
    salary = cat(client, "Salary", "income")
    freelance = cat(client, "Freelance", "income")

    created = client.post("/income", json=payload(salary))
    assert created.status_code == 201
    body = created.json()
    assert body["type"] == "income" and body["amount"] == 45000.5 and body["category_name"] == "Salary"

    tx_id = body["id"]
    assert client.get(f"/income/{tx_id}").json()["description"] == "Monthly salary"
    assert [t["id"] for t in client.get("/income").json()] == [tx_id]

    updated = client.put(f"/income/{tx_id}", json={"amount": "50000", "category_id": freelance})
    assert updated.status_code == 200
    assert updated.json()["amount"] == 50000 and updated.json()["category_name"] == "Freelance"
    assert updated.json()["description"] == "Monthly salary"  # untouched field preserved

    assert client.delete(f"/income/{tx_id}").status_code == 204
    assert client.get(f"/income/{tx_id}").status_code == 404
    assert client.get("/income").json() == []


def test_requires_income_category(client, cat):
    resp = client.post("/income", json=payload(cat(client, "Food", "expense")))
    assert resp.status_code == 400


def test_unknown_category_404(client):
    assert client.post("/income", json=payload("does-not-exist")).status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "abc"},
        {"amount": "12.345"},
        {"amount": "9999999999999"},
        {"amount": "NaN"},
        {"amount": "Infinity"},
        {"date": "not-a-date"},
        {"date": "1999-01-01"},
        {"date": "2099-01-01"},
        {"description": "x" * 201},
        {"description": "bad\x00text"},
        {"type": "expense"},  # unexpected field
    ],
)
def test_invalid_input_rejected(client, cat, overrides):
    resp = client.post("/income", json=payload(cat(client, "Salary", "income"), **overrides))
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_missing_fields_rejected(client):
    assert client.post("/income", json={}).status_code == 400


def test_empty_update_rejected(client, cat):
    tx = client.post("/income", json=payload(cat(client, "Salary", "income"))).json()
    assert client.put(f"/income/{tx['id']}", json={}).status_code == 400
    assert client.put(f"/income/{tx['id']}", json={"amount": None}).status_code == 400


def test_sql_injection_text_stored_literally(client, cat):
    evil = "'; DROP TABLE transactions; --"
    resp = client.post("/income", json=payload(cat(client, "Salary", "income"), description=evil))
    assert resp.status_code == 201 and resp.json()["description"] == evil
    assert len(client.get("/income").json()) == 1


def test_users_cannot_access_each_others_income(make_client, cat):
    alice = make_client("alice")
    tx = alice.post("/income", json=payload(cat(alice, "Salary", "income"))).json()

    bob = make_client("bob")
    assert bob.get("/income").json() == []
    assert bob.get(f"/income/{tx['id']}").status_code == 404
    assert bob.put(f"/income/{tx['id']}", json={"amount": "1"}).status_code == 404
    assert bob.delete(f"/income/{tx['id']}").status_code == 404

    alice = make_client("alice")
    assert alice.get(f"/income/{tx['id']}").status_code == 200


def test_cannot_use_another_users_custom_category(make_client, cat):
    alice = make_client("alice")
    private = alice.post("/categories", json={"name": "Side gig", "type": "income"}).json()["id"]
    bob = make_client("bob")
    assert bob.post("/income", json=payload(private)).status_code == 404


def test_endpoints_require_auth(make_client):
    from security import get_current_user
    import main

    anon = make_client("alice")
    main.app.dependency_overrides.pop(get_current_user)  # keep test DB, drop fake login
    assert anon.get("/income").status_code == 401
    assert anon.post("/income", json={}).status_code == 401
