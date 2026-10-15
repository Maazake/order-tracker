def test_no_token(client):
    response = client.get("/orders")

    assert response.status_code == 401


def test_garbage_token_returns_401(client):
    response = client.get("/orders", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401


def test_no_enough_permissions(order, operator_client):
    response = operator_client.delete(f"/orders/{order['id']}")

    assert response.status_code == 403
