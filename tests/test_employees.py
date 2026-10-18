def test_get_employees_empty_list_when_none(admin_client):
    response = admin_client.get("/employees")

    assert response.status_code == 200
    assert response.json() == []


def test_get_employees_when_there_is_one(admin_client, employee):
    response = admin_client.get("/employees")
    data = response.json()

    assert response.status_code == 200
    assert data[0]["name"] == employee["name"]


def test_create_employee(admin_client):
    element = {"name": "Patrick Star", "role": "CNC Operator"}
    response = admin_client.post("/employees", json=element)
    data = response.json()

    assert response.status_code == 201
    assert data["name"] == element["name"]
    assert data["role"] == element["role"]
    assert "id" in data


def test_get_all_users_with_admin(admin_client):
    response_admin = admin_client.get("/users")
    assert response_admin.status_code == 200
