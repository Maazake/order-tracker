def test_login_returns_working_token(client):
    client.post("/auth/register", json={"username": "John", "password": "Smith"})

    login = client.post("/auth/login", data={"username": "John", "password": "Smith"})
    assert login.status_code == 200

    token = login.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "John"


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={"username": "John", "password": "Smith"})

    login = client.post("/auth/login", data={"username": "John", "password": "wrong"})
    assert login.status_code == 401

    
