"""SEA-F-013 search and filter (TC-Search-01)."""

import pytest


@pytest.fixture()
def seeded(client, cat):
    food, transport = cat(client, "Food", "expense"), cat(client, "Transport", "expense")
    salary = cat(client, "Salary", "income")
    rows = [
        ("/expenses", food, "100", "2026-10-01", "Grocery shopping"),
        ("/expenses", food, "250.50", "2026-10-10", "Dinner out"),
        ("/expenses", transport, "60", "2026-10-15", "Bus pass"),
        ("/income", salary, "5000", "2026-10-05", "October salary"),
    ]
    for path, category, amount, day, text in rows:
        resp = client.post(path, json={"amount": amount, "category_id": category, "date": day, "description": text})
        assert resp.status_code == 201
    return {"food": food, "transport": transport, "salary": salary}


def names(resp):
    assert resp.status_code == 200
    return [t["description"] for t in resp.json()]


def test_no_filters_returns_everything_newest_first(client, seeded):
    assert names(client.get("/transactions")) == ["Bus pass", "Dinner out", "October salary", "Grocery shopping"]


def test_search_matches_description_and_category_case_insensitive(client, seeded):
    assert names(client.get("/transactions", params={"q": "GROCERY"})) == ["Grocery shopping"]
    assert sorted(names(client.get("/transactions", params={"q": "food"}))) == ["Dinner out", "Grocery shopping"]


def test_filter_by_type(client, seeded):
    assert names(client.get("/transactions", params={"type": "income"})) == ["October salary"]
    assert len(names(client.get("/transactions", params={"type": "expense"}))) == 3


def test_filter_by_category_id_and_name(client, seeded):
    assert names(client.get("/transactions", params={"category_id": seeded["transport"]})) == ["Bus pass"]
    assert len(names(client.get("/transactions", params={"category": "food"}))) == 2


def test_filter_by_date_range(client, seeded):
    resp = client.get("/transactions", params={"date_from": "2026-10-05", "date_to": "2026-10-10"})
    assert names(resp) == ["Dinner out", "October salary"]


def test_filter_by_amount_range(client, seeded):
    resp = client.get("/transactions", params={"min_amount": "60", "max_amount": "250.50"})
    assert names(resp) == ["Bus pass", "Dinner out", "Grocery shopping"]


def test_filters_combine(client, seeded):
    resp = client.get("/transactions", params={"q": "food", "min_amount": "200", "type": "expense"})
    assert names(resp) == ["Dinner out"]


def test_pagination(client, seeded):
    assert names(client.get("/transactions", params={"limit": 2})) == ["Bus pass", "Dinner out"]
    assert names(client.get("/transactions", params={"limit": 2, "offset": 2})) == ["October salary", "Grocery shopping"]


def test_no_match_returns_empty_list(client, seeded):
    assert client.get("/transactions", params={"q": "nothing-like-this"}).json() == []


@pytest.mark.parametrize(
    "params",
    [
        {"date_from": "2026-10-10", "date_to": "2026-10-01"},
        {"min_amount": "10", "max_amount": "5"},
        {"min_amount": "-1"},
        {"type": "transfer"},
        {"limit": 0},
        {"limit": 100000},
        {"offset": -1},
        {"q": "x" * 101},
        {"date_from": "not-a-date"},
    ],
)
def test_invalid_filters_are_rejected(client, seeded, params):
    assert client.get("/transactions", params=params).status_code == 400


def test_wildcards_are_matched_literally(client, seeded):
    assert client.get("/transactions", params={"q": "%"}).json() == []
    assert client.get("/transactions", params={"q": "_"}).json() == []


def test_sql_injection_text_is_harmless(client, seeded):
    resp = client.get("/transactions", params={"q": "' OR 1=1; DROP TABLE transactions;--"})
    assert resp.status_code == 200 and resp.json() == []
    assert len(client.get("/transactions").json()) == 4


def test_search_never_returns_other_users_data(make_client, seeded):
    bob = make_client("bob")
    assert bob.get("/transactions", params={"q": "grocery"}).json() == []
    assert bob.get("/transactions").json() == []
