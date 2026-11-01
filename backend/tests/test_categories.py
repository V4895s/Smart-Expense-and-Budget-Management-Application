import pytest

from services_categories import seed_default_categories


@pytest.fixture(autouse=True)
def seeded(session_factory):
    with session_factory() as session:
        seed_default_categories(session)
        seed_default_categories(session)  # idempotent


def test_defaults_listed_once_and_filterable(client):
    all_cats = client.get("/categories").json()
    names = [(c["name"], c["type"]) for c in all_cats]
    assert len(names) == len(set(names))
    assert all(c["is_default"] for c in all_cats)

    income = client.get("/categories", params={"type": "income"}).json()
    assert income and all(c["type"] == "income" for c in income)


def test_create_custom_category(client):
    resp = client.post("/categories", json={"name": "  Pets ", "type": "expense"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Pets" and body["is_default"] is False


def test_duplicate_is_rejected_case_insensitive(client):
    assert client.post("/categories", json={"name": "food", "type": "expense"}).status_code == 409
    client.post("/categories", json={"name": "Pets", "type": "expense"})
    assert client.post("/categories", json={"name": "PETS", "type": "expense"}).status_code == 409


def test_same_name_allowed_for_other_type(client):
    assert client.post("/categories", json={"name": "Gifts", "type": "expense"}).status_code == 201
    assert client.post("/categories", json={"name": "Gifts", "type": "income"}).status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "type": "expense"},
        {"name": "x" * 51, "type": "expense"},
        {"name": "Bad\x00", "type": "expense"},
        {"name": "Ok", "type": "transfer"},
        {"name": "Ok"},
        {"name": "Ok", "type": "expense", "user_id": "someone-else"},
    ],
)
def test_invalid_payloads_rejected(client, payload):
    resp = client.post("/categories", json=payload)
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_custom_categories_are_private(make_client):
    make_client("alice").post("/categories", json={"name": "Secret", "type": "expense"})
    bob_names = [c["name"] for c in make_client("bob").get("/categories").json()]
    assert "Secret" not in bob_names
