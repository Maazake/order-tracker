from datetime import timedelta

import jwt
import pytest

from app.security import ALGORITHM, create_access_token


@pytest.mark.parametrize("url", ["/orders", "/orders/1"])
def test_orders_require_login(client, url):
    response = client.get(url)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "garbage",
        create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=-1)),
        jwt.encode(
            {"sub": "1"}, "wrong-key-wrong-key-wrong-key-32b", algorithm=ALGORITHM
        ),
        create_access_token({"role": "admin"}),
        create_access_token({"sub": "999"}),
    ],
)
def test_invalid_token_returns_401(client, token):
    response = client.get("/orders", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_no_enough_permissions(order, operator_client):
    response = operator_client.delete(f"/orders/{order['id']}")

    assert response.status_code == 403
