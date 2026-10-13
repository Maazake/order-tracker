import pytest

from app.schemas import ProcessStage


def test_orders_require_login(client):
    response = client.get("/orders")

    assert response.status_code == 401

def test_get_orders_empty(operator_client):
    response = operator_client.get("/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_create_order_creates_all_steps(admin_client):
    element = {"element_name": "DRILL", "count": 15}
    response = admin_client.post("/orders", json=element)
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


def test_get_order_by_id(operator_client, order):
    response = operator_client.get(f"/orders/{order['id']}")
    data = response.json()

    assert response.status_code == 200

    steps = []
    for step in data["steps"]:
        steps.append(step["step_order"])

    assert data["element_name"] == order["element_name"]
    assert data["id"] == order["id"]
    assert steps == list(range(1, 8))


def test_get_order_by_wrong_id_returns_404(operator_client):
    response = operator_client.get("/orders/999")

    assert response.status_code == 404


def test_delete_order(admin_client, operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    response = admin_client.delete(f"/orders/{order['id']}")

    assert response.status_code == 204

    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 404

    response = operator_client.get(f"/orders/{order['id']}")

    assert response.status_code == 404


def test_get_orders_with_params(admin_client, operator_client):
    element = {"element_name": "DRILL", "count": 15}
    for _ in range(3):
        admin_client.post("/orders", json=element)

    response = operator_client.get("/orders?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = operator_client.get("/orders?offset=2")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == 3

    response = operator_client.get("/orders?offset=999")
    assert response.status_code == 200
    assert response.json() == []


def test_get_order_by_status(admin_client, operator_client, employee, order):
    step_id = order["steps"][0]["id"]
    additional_order = {"element_name": "SHAFT", "count": 44}
    response = admin_client.post("/orders", json=additional_order)

    assert response.status_code == 201

    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 200

    response = operator_client.get("/orders?status=in_progress")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == order["id"]

@pytest.mark.parametrize("desc", [False, True])
def test_sort_orders_by_count(admin_client, operator_client, desc):
    counts_in = [10, 30, 20]

    for count in counts_in:
        response = admin_client.post(
            "/orders", json={"element_name": "DRILL", "count": count}
        )
        assert response.status_code == 201

    response = operator_client.get("/orders", params={"sort": "count", "desc": desc})
    data = response.json()
    expected = sorted(counts_in, reverse=desc)

    assert response.status_code == 200

    counts = []
    for order in data:
        counts.append(order["count"])

    assert counts == expected


@pytest.mark.parametrize(
    "url",
    [
        "/orders?limit=-5",
        "/orders?limit=0",
        "/orders?limit=101",
        "/orders?status=xyz",
        "/orders?sort=xyz",
    ],
)
def test_invalid_params_return_422(operator_client, url):
    response = operator_client.get(url)

    assert response.status_code == 422
