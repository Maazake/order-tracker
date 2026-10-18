from app.schemas import StepStatus


def start_step(client, step_id, employee_id):
    return client.post(f"/steps/{step_id}/start", json={"employee_id": employee_id})


def complete_step(client, step_id, note=None):
    return client.post(f"/steps/{step_id}/complete", json={"note": note})


def test_start_step(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    response = start_step(operator_client, step_id, employee["id"])
    data = response.json()

    assert response.status_code == 200
    assert data["started_at"] is not None
    assert data["status"] == StepStatus.IN_PROGRESS
    assert data["assigned_employee_id"] == employee["id"]


def test_start_step_unknown_employee_returns_404(operator_client, order):
    step_id = order["steps"][0]["id"]
    response = start_step(operator_client, step_id, employee_id=999)

    assert response.status_code == 404


def test_start_step_unknown_step_returns_404(operator_client, employee):
    response = start_step(operator_client, step_id=999, employee_id=employee["id"])

    assert response.status_code == 404


def test_start_second_step_before_first_returns_409(operator_client, order, employee):
    step_id = order["steps"][1]["id"]
    response = start_step(operator_client, step_id, employee["id"])

    assert response.status_code == 409


def test_start_same_step_twice_returns_409(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    assert start_step(operator_client, step_id, employee["id"]).status_code == 200

    response = start_step(operator_client, step_id, employee["id"])

    assert response.status_code == 409


def test_complete_without_start_returns_409(operator_client, order):
    step_id = order["steps"][0]["id"]
    response = complete_step(operator_client, step_id)

    assert response.status_code == 409


def test_complete_no_existing_step_returns_404(operator_client):
    response = complete_step(operator_client, step_id=999)

    assert response.status_code == 404


def test_complete_step(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    assert start_step(operator_client, step_id, employee["id"]).status_code == 200

    response = complete_step(operator_client, step_id)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == StepStatus.DONE
    assert data["completed_at"] is not None


def test_start_and_complete(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    assert start_step(operator_client, step_id, employee["id"]).status_code == 200

    response = complete_step(operator_client, step_id)
    data = response.json()

    assert data["status"] == StepStatus.DONE

    step_id = order["steps"][1]["id"]
    response = start_step(operator_client, step_id, employee["id"])
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == StepStatus.IN_PROGRESS


def test_complete_with_note(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    assert start_step(operator_client, step_id, employee["id"]).status_code == 200

    response = complete_step(operator_client, step_id, note="I was there")

    data = response.json()

    assert response.status_code == 200
    assert data["note"] == "I was there"
