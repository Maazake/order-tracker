def test_get_employees_empty_list_when_none(client):
    response = client.get("/employees")

    assert response.status_code == 200
    assert response.json() == []


def test_get_employees_when_there_is_one(client, employee):
    element = {"name": "John Smith", "role": "Lathe Operator"}
    response = client.post("/employees", json=element)
    data = response.json()

    assert response.status_code == 201
