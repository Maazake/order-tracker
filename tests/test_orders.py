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

    for expected, s in enumerate(data["steps"], start =1):
        assert s["step_order"] == expected
        
    
