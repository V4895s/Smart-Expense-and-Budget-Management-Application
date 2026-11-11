from datetime import date, timedelta

from services.recurring_service import next_occurrence


def test_next_occurrence_clamps_to_month_end():
    assert next_occurrence(date(2026, 1, 31), "monthly", 31) == date(2026, 2, 28)
    assert next_occurrence(date(2026, 2, 28), "monthly", 31) == date(2026, 3, 31)
    assert next_occurrence(date(2026, 12, 15), "monthly", 15) == date(2027, 1, 15)
    assert next_occurrence(date(2026, 3, 1), "weekly", 1) == date(2026, 3, 8)
    assert next_occurrence(date(2026, 3, 1), "daily", 1) == date(2026, 3, 2)
    assert next_occurrence(date(2028, 2, 29), "yearly", 29) == date(2029, 2, 28)


def _rule(category_id, **overrides):
    data = {
        "type": "expense",
        "amount": "499.00",
        "category_id": category_id,
        "description": "Netflix",
        "frequency": "monthly",
        "start_date": date.today().isoformat(),
    }
    data.update(overrides)
    return data


def test_rule_starting_today_creates_first_transaction_immediately(client, cat):
    food = cat(client, "Food", "expense")
    response = client.post("/recurring", json=_rule(food))
    assert response.status_code == 201
    assert response.json()["next_run_date"] > date.today().isoformat()

    expenses = client.get("/expenses").json()
    assert len(expenses) == 1 and expenses[0]["description"] == "Netflix"


def test_missed_periods_are_caught_up(client, cat):
    salary = cat(client, "Salary", "income")
    start = date.today() - timedelta(days=14)
    client.post(
        "/recurring",
        json=_rule(salary, type="income", frequency="weekly", start_date=start.isoformat()),
    )
    assert len(client.get("/income").json()) == 3  # start, +7, +14


def test_end_date_deactivates_rule(client, cat):
    salary = cat(client, "Salary", "income")
    start = date.today() - timedelta(days=14)
    end = start + timedelta(days=7)
    response = client.post(
        "/recurring",
        json=_rule(
            salary,
            type="income",
            frequency="weekly",
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        ),
    )
    assert response.json()["is_active"] is False
    assert len(client.get("/income").json()) == 2


def test_pause_resume_delete(client, cat):
    food = cat(client, "Food", "expense")
    rule_id = client.post("/recurring", json=_rule(food)).json()["id"]

    assert client.put(f"/recurring/{rule_id}", json={"is_active": False}).json()["is_active"] is False
    assert client.put(f"/recurring/{rule_id}", json={"is_active": True}).json()["is_active"] is True

    assert client.delete(f"/recurring/{rule_id}").status_code == 204
    assert client.get("/recurring").json() == []
    assert len(client.get("/expenses").json()) == 1  # generated transaction is kept


def test_validation_and_wrong_category_type(client, cat):
    food = cat(client, "Food", "expense")
    salary = cat(client, "Salary", "income")
    assert client.post("/recurring", json=_rule(salary)).status_code == 400  # income category on expense
    assert client.post("/recurring", json=_rule(food, frequency="hourly")).status_code == 400
    bad_end = (date.today() - timedelta(days=1)).isoformat()
    assert client.post("/recurring", json=_rule(food, end_date=bad_end)).status_code == 400


def test_rules_are_private_to_each_user(make_client, cat):
    alice = make_client("alice")
    rule_id = alice.post("/recurring", json=_rule(cat(alice, "Food", "expense"))).json()["id"]

    bob = make_client("bob")
    assert bob.get("/recurring").json() == []
    assert bob.put(f"/recurring/{rule_id}", json={"is_active": False}).status_code == 404
    assert bob.delete(f"/recurring/{rule_id}").status_code == 404
