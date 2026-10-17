from app.schemas import StepStatus


def test_start_step(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["started_at"] is not None
    assert data["status"] == StepStatus.IN_PROGRESS
    assert data["assigned_employee_id"] == employee["id"]


def test_start_step_unknown_employee_returns_404(operator_client, order):
    step_id = order["steps"][0]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": 999}
    )

    assert response.status_code == 404


def test_start_step_unknown_step_returns_404(operator_client, employee):
    step_id = 999
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 404


def test_start_second_step_before_first_returns_409(operator_client, order, employee):
    step_id = order["steps"][1]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 409


def test_start_same_step_twice_returns_409(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 200
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )
    assert response.status_code == 409


def test_complete_without_start_returns_409(
    operator_client,
    order,
):
    step_id = order["steps"][0]["id"]
    response = operator_client.post(f"/steps/{step_id}/complete", json={})

    assert response.status_code == 409


def test_complete_no_existing_step_returns_404(
    operator_client,
):
    step_id = 999
    response = operator_client.post(f"/steps/{step_id}/complete", json={})

    assert response.status_code == 404


def test_complete_step(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == StepStatus.IN_PROGRESS
    assert data["completed_at"] is None

    response = operator_client.post(f"/steps/{step_id}/complete", json={})
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == StepStatus.DONE
    assert data["completed_at"] is not None


def test_start_and_complete(operator_client, order, employee):
    step_id = order["steps"][0]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )

    assert response.status_code == 200

    response = operator_client.post(f"/steps/{step_id}/complete", json={})
    data = response.json()

    assert data["status"] == StepStatus.DONE

    step_id = order["steps"][1]["id"]
    response = operator_client.post(
        f"/steps/{step_id}/start", json={"employee_id": employee["id"]}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == StepStatus.IN_PROGRESS
