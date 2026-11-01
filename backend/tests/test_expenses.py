import pytest


def payload(category_id, **overrides):
    data = {"amount": "1850", "category_id": category_id, "date": "2026-10-24", "description": "Grocery shopping"}
    data.update(overrides)
    return data


def test_expense_crud(client, cat):
    food = cat(client, "Food", "expense")
    transport = cat(client, "Transport", "expense")

    created = client.post("/expenses", json=payload(food))
    assert created.status_code == 201
    tx = created.json()
    assert tx["type"] == "expense" and tx["amount"] == 1850 and tx["category_name"] == "Food"

    assert client.get(f"/expenses/{tx['id']}").status_code == 200
    updated = client.put(f"/expenses/{tx['id']}", json={"description": "Bus pass", "category_id": transport, "amount": "650.75"})
    assert updated.status_code == 200
    assert updated.json()["category_name"] == "Transport" and updated.json()["amount"] == 650.75

    assert client.delete(f"/expenses/{tx['id']}").status_code == 204
    assert client.get("/expenses").json() == []


def test_requires_expense_category(client, cat):
    assert client.post("/expenses", json=payload(cat(client, "Salary", "income"))).status_code == 400


def test_cannot_move_expense_to_income_category(client, cat):
    tx = client.post("/expenses", json=payload(cat(client, "Food", "expense"))).json()
    resp = client.put(f"/expenses/{tx['id']}", json={"category_id": cat(client, "Salary", "income")})
    assert resp.status_code == 400


@pytest.mark.parametrize("overrides", [{"amount": "0"}, {"amount": "-1"}, {"amount": "x"}, {"date": "31-12-2026"}, {"description": "y" * 201}])
def test_invalid_expense_input(client, cat, overrides):
    resp = client.post("/expenses", json=payload(cat(client, "Food", "expense"), **overrides))
    assert resp.status_code == 400


def test_income_and_expense_endpoints_are_separate(client, cat):
    exp = client.post("/expenses", json=payload(cat(client, "Food", "expense"))).json()
    inc = client.post("/income", json=payload(cat(client, "Salary", "income"), amount="100")).json()
    assert client.get(f"/income/{exp['id']}").status_code == 404
    assert client.get(f"/expenses/{inc['id']}").status_code == 404


def test_combined_transaction_list_is_per_user(make_client, cat):
    alice = make_client("alice")
    alice.post("/expenses", json=payload(cat(alice, "Food", "expense")))
    alice.post("/income", json=payload(cat(alice, "Salary", "income"), amount="500"))
    assert {t["type"] for t in alice.get("/transactions").json()} == {"income", "expense"}
    assert make_client("bob").get("/transactions").json() == []


def test_cross_user_expense_access_denied(make_client, cat):
    alice = make_client("alice")
    tx = alice.post("/expenses", json=payload(cat(alice, "Food", "expense"))).json()
    bob = make_client("bob")
    assert bob.get(f"/expenses/{tx['id']}").status_code == 404
    assert bob.put(f"/expenses/{tx['id']}", json={"amount": "1"}).status_code == 404
    assert bob.delete(f"/expenses/{tx['id']}").status_code == 404
    assert make_client("alice").get(f"/expenses/{tx['id']}").status_code == 200
