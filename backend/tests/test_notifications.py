from datetime import date


def test_budget_alerts_at_80_and_100_percent_without_duplicates(
    client,
    cat,
):
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

    first = client.post(
        "/expenses",
        json={
            "amount": "850",
            "category_id": food,
            "date": date.today().isoformat(),
            "description": "Groceries",
        },
    )

    assert first.status_code == 201

    alerts = client.get(
        "/notifications?unread_only=true"
    ).json()

    assert len(alerts) == 1
    assert alerts[0]["level"] == "warning"
    assert "85%" in alerts[0]["message"]

    second = client.post(
        "/expenses",
        json={
            "amount": "250",
            "category_id": food,
            "date": date.today().isoformat(),
            "description": "More groceries",
        },
    )

    assert second.status_code == 201

    alerts = client.get(
        "/notifications?unread_only=true"
    ).json()

    assert len(alerts) == 2

    assert {
        alert["level"]
        for alert in alerts
    } == {
        "warning",
        "danger",
    }

    # Additional expenses in the same period must not
    # create duplicate alerts.

    third = client.post(
        "/expenses",
        json={
            "amount": "100",
            "category_id": food,
            "date": date.today().isoformat(),
            "description": "Snacks",
        },
    )

    assert third.status_code == 201

    assert len(
        client.get("/notifications").json()
    ) == 2


def test_mark_notification_read_and_user_isolation(
    make_client,
    cat,
):
    alice = make_client("alice")

    food = cat(alice, "Food", "expense")

    budget = alice.post(
        "/budgets",
        json={
            "name": "Food budget",
            "category_id": food,
            "amount": "100",
            "period": "monthly",
        },
    )

    assert budget.status_code == 201

    expense = alice.post(
        "/expenses",
        json={
            "amount": "90",
            "category_id": food,
            "date": date.today().isoformat(),
            "description": "Groceries",
        },
    )

    assert expense.status_code == 201

    alert = alice.get("/notifications").json()[0]

    bob = make_client("bob")

    assert bob.get("/notifications").json() == []

    assert bob.patch(
        f"/notifications/{alert['id']}/read"
    ).status_code == 404

    # Restore Alice's dependency override for this test.
    alice = make_client("alice")

    marked = alice.patch(
        f"/notifications/{alert['id']}/read"
    )

    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    assert alice.get(
        "/notifications?unread_only=true"
    ).json() == []