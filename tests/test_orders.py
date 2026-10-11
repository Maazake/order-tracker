from app.schemas import ProcessStage


def test_get_orders_empty(client):
    response = client.get("/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_create_order_creates_all_steps(client):
    element = {"element_name": "DRILL", "count": 15}
    response = client.post("/orders", json=element)
    data = response.json()

    assert response.status_code == 201
    assert data["id"] is not None
    assert data["element_name"] == element["element_name"]
    assert data["count"] == element["count"]
    assert len(data["steps"]) == len(ProcessStage)

    for step in data["steps"]:
        assert step["status"] == "pending"

    for expected, s in enumerate(data["steps"], start=1):
        assert s["step_order"] == expected


def test_get_order_by_id(client, order):
    response = client.get(f"/orders/{order['id']}")
    data = response.json()

    assert response.status_code == 200

    steps = []
    for step in data["steps"]:
        steps.append(step["step_order"])

    assert data["element_name"] == order["element_name"]
    assert data["id"] == order["id"]
    assert steps == list(range(1, 8))


def test_get_order_by_wrong_id_returns_404(client):
    response = client.get("/orders/999")

    assert response.status_code == 404


def test_delete_order(client, order, employee):
    step_id = order["steps"][0]["id"]
    response = client.delete(f"/orders/{order['id']}")

    assert response.status_code == 204

    response = client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 404

    response = client.get(f"/orders/{order['id']}")

    assert response.status_code == 404
