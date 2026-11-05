def goal_payload(**overrides):
    data = {
        "name": "Emergency fund",
        "target_amount": "10000",
        "current_amount": "2500",
        "target_date": "2027-06-30",
    }
    data.update(overrides)
    return data


def test_savings_goal_crud_and_contributions(client):
    created = client.post("/savings-goals", json=goal_payload())

    assert created.status_code == 201
    goal = created.json()
    assert goal["current_amount"] == 2500
    assert goal["progress_percent"] == 25
    assert goal["status"] == "active"

    contributed = client.post(
        f"/savings-goals/{goal['id']}/contributions",
        json={"amount": "2500"},
    )

    assert contributed.status_code == 200
    assert contributed.json()["current_amount"] == 5000
    assert contributed.json()["progress_percent"] == 50

    updated = client.put(
        f"/savings-goals/{goal['id']}",
        json={"name": "Rainy day fund"},
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Rainy day fund"

    assert client.delete(f"/savings-goals/{goal['id']}").status_code == 204
    assert client.get("/savings-goals").json() == []


def test_goal_cannot_receive_more_than_remaining(client):
    goal = client.post(
        "/savings-goals",
        json=goal_payload(current_amount="9000"),
    ).json()

    response = client.post(
        f"/savings-goals/{goal['id']}/contributions",
        json={"amount": "1001"},
    )

    assert response.status_code == 400

    unchanged = client.get(f"/savings-goals/{goal['id']}").json()
    assert unchanged["current_amount"] == 9000


def test_goal_rejects_invalid_amounts(client):
    assert (
        client.post(
            "/savings-goals",
            json=goal_payload(target_amount="0"),
        ).status_code
        == 400
    )

    assert (
        client.post(
            "/savings-goals",
            json=goal_payload(current_amount="11000"),
        ).status_code
        == 400
    )


def test_savings_goals_are_private(make_client):
    alice = make_client("alice")

    goal = alice.post(
        "/savings-goals",
        json=goal_payload(),
    ).json()

    bob = make_client("bob")

    assert bob.get("/savings-goals").json() == []

    assert bob.get(
        f"/savings-goals/{goal['id']}"
    ).status_code == 404

    assert bob.put(
        f"/savings-goals/{goal['id']}",
        json={"name": "Stolen"},
    ).status_code == 404

    assert bob.delete(
        f"/savings-goals/{goal['id']}"
    ).status_code == 404

    assert bob.post(
        f"/savings-goals/{goal['id']}/contributions",
        json={"amount": "10"},
    ).status_code == 404