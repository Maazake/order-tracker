import pytest


def test_login_returns_working_token(client):
    client.post("/auth/register", json={"username": "John", "password": "Smithson"})

    login = client.post(
        "/auth/login", data={"username": "John", "password": "Smithson"}
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "John"


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={"username": "John", "password": "Smithson"})

    login = client.post("/auth/login", data={"username": "John", "password": "wrong"})
    assert login.status_code == 401


def test_register_response_model(client):
    response = client.post(
        "/auth/register", json={"username": "John", "password": "Smithson"}
    )
    data = response.json()

    assert response.status_code == 201
    assert "hashed_password" not in data

    re_register = client.post(
        "/auth/register", json={"username": "John", "password": "Smithson"}
    )
    assert re_register.status_code == 409

    register_admin = client.post(
        "/auth/register",
        json={"username": "Tom", "password": "JerryMouse", "role": "admin"},
    )
    assert register_admin.status_code == 201
    assert register_admin.json()["role"] == "operator"


def test_register_empty_strings(client):
    response = client.post("/auth/register", json={"username": "", "password": "123"})
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("POST", "/orders"),
        ("POST", "/employees"),
        ("GET", "/employees"),
        ("GET", "/users"),
    ],
)
def test_operators_gets_403_on_admin_endpoints(operator_client, method, url):
    response = operator_client.request(method, url)

    assert response.status_code == 403
