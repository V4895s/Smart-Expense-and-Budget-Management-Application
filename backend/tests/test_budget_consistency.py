from datetime import date


def test_budget_spending_stays_consistent_after_expense_crud(client, cat):
    food = cat(client, "Food", "expense")

    budget = client.post(
        "/budgets",
        json={
            "name": "Food budget",
            "category_id": food,
            "amount": "1000",
            "period": "monthly",
        },
    )

    assert budget.status_code == 201
    budget_id = budget.json()["id"]

    expense = client.post(
        "/expenses",
        json={
            "amount": "200",
            "category_id": food,
            "date": date.today().isoformat(),
            "description": "Groceries",
        },
    )

    assert expense.status_code == 201
    expense_id = expense.json()["id"]

    current = client.get(f"/budgets/{budget_id}").json()
    assert current["spent"] == 200
    assert current["remaining"] == 800

    updated = client.put(
        f"/expenses/{expense_id}",
        json={"amount": "350"},
    )

    assert updated.status_code == 200

    current = client.get(f"/budgets/{budget_id}").json()
    assert current["spent"] == 350
    assert current["remaining"] == 650

    deleted = client.delete(f"/expenses/{expense_id}")

    assert deleted.status_code == 204

    current = client.get(f"/budgets/{budget_id}").json()
    assert current["spent"] == 0
    assert current["remaining"] == 1000


def test_income_does_not_change_expense_budget_spending(client, cat):
    food = cat(client, "Food", "expense")
    salary = cat(client, "Salary", "income")

    budget = client.post(
        "/budgets",
        json={
            "name": "Food budget",
            "category_id": food,
            "amount": "1000",
            "period": "monthly",
        },
    ).json()

    response = client.post(
        "/income",
        json={
            "amount": "5000",
            "category_id": salary,
            "date": date.today().isoformat(),
            "description": "Salary",
        },
    )

    assert response.status_code == 201

    current = client.get(f"/budgets/{budget['id']}").json()
    assert current["spent"] == 0
    assert current["remaining"] == 1000


def test_budget_spending_tracks_transaction_category_and_date_changes(
    client, cat
):
    food = cat(client, "Food", "expense")
    transport = cat(client, "Transport", "expense")

    food_budget = client.post(
        "/budgets",
        json={
            "name": "Food",
            "category_id": food,
            "amount": "1000",
            "period": "monthly",
        },
    ).json()

    transport_budget = client.post(
        "/budgets",
        json={
            "name": "Transport",
            "category_id": transport,
            "amount": "1000",
            "period": "monthly",
        },
    ).json()

    tx = client.post(
        "/expenses",
        json={
            "amount": "125",
            "category_id": food,
            "date": date.today().isoformat(),
            "description": "Test",
        },
    ).json()

    moved = client.put(
        f"/expenses/{tx['id']}",
        json={"category_id": transport},
    )

    assert moved.status_code == 200
    assert client.get(f"/budgets/{food_budget['id']}").json()["spent"] == 0
    assert (
        client.get(f"/budgets/{transport_budget['id']}").json()["spent"]
        == 125
    )

    dated = client.put(
        f"/expenses/{tx['id']}",
        json={"date": "2000-01-01"},
    )

    assert dated.status_code == 200
    assert (
        client.get(f"/budgets/{transport_budget['id']}").json()["spent"]
        == 0
    )