def test_get_employees_empty_list_when_none(client):
    response = client.get("/employees")

    assert response.status_code == 200
    assert response.json() == []


def test_get_employees_when_there_is_one(client, employee):
    response = client.get("/employees")
    data = response.json()

    assert response.status_code == 200
    assert data[0]["name"] == employee["name"]


def test_create_employee(client):
    element = {"name": "Patrick Star", "role": "CNC Operator"}
    response = client.post("/employees", json=element)
    data = response.json()

    assert response.status_code == 201
    assert data["name"] == element["name"]
    assert data["role"] == element["role"]
    assert "id" in data