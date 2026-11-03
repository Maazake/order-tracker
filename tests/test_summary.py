from datetime import UTC, date, datetime

import pytest

from app import services
from app.config import settings
from app.exceptions import LlmUnavailableError
from app.models import OrderDB, OrderStepDB
from app.schemas import OrderDraft, StepStatus
from tests.fakes import (
    FailingClient,
    FakeBlock,
    FakeClient,
    FakeResponse,
    FakeUsage,
    TruncatedMessages,
)

NOW = datetime(2026, 12, 12, 9, 0, 0, 0, tzinfo=UTC)


def make_order():
    return OrderDB(
        element_name="VALVE", count=10, planned_completion_date=date(2026, 12, 15)
    )


def test_summarize_order_returns_text_from_model():
    new_order = make_order()
    fake_block = FakeBlock(type="text", text="fake summary")
    fake_usage = FakeUsage(100, 50)
    fake_response = FakeResponse(
        content=[fake_block],
        stop_reason="end_turn",
        usage=fake_usage,
        model="claude-haiku-10-10",
    )
    fake_client = FakeClient(fake_response)

    summary = services.summarize_order(new_order, fake_client)

    assert summary == "fake summary"


def test_summarize_order_with_empty_text():
    new_order = make_order()
    fake_block = FakeBlock(type="text", text="")
    fake_usage = FakeUsage(100, 50)
    fake_response = FakeResponse(
        content=[fake_block],
        stop_reason="end_turn",
        usage=fake_usage,
        model="claude-haiku-10-10",
    )
    fake_client = FakeClient(fake_response)

    with pytest.raises(LlmUnavailableError):
        services.summarize_order(new_order, fake_client)


def test_summarize_order_with_not_complete_response():
    new_order = make_order()
    fake_block = FakeBlock(type="text", text="Order 7 is overdue and  the")
    fake_usage = FakeUsage(100, 50)
    fake_response = FakeResponse(
        content=[fake_block],
        stop_reason="max_tokens",
        usage=fake_usage,
        model="claude-haiku-10-10",
    )
    fake_client = FakeClient(fake_response)

    with pytest.raises(LlmUnavailableError):
        services.summarize_order(new_order, fake_client)


def test_summarize_order_without_text_block():
    new_order = make_order()
    fake_block = FakeBlock(type="thinking", text="this is not a text block")
    fake_usage = FakeUsage(100, 50)
    fake_response = FakeResponse(
        content=[fake_block],
        stop_reason="max_tokens",
        usage=fake_usage,
        model="claude-haiku-10-10",
    )
    fake_client = FakeClient(fake_response)

    with pytest.raises(LlmUnavailableError):
        services.summarize_order(new_order, fake_client)


def test_extract_order_draft_returns_parsed_output():
    draft = OrderDraft(
        element_name="VALVE", count=50, planned_completion_date=date(2026, 11, 13)
    )
    fake_usage = FakeUsage(100, 50)
    fake_response = FakeResponse(
        content=[],
        stop_reason="end_turn",
        usage=fake_usage,
        model="claude-haiku-10-10",
        parsed_output=draft,
    )
    fake_client = FakeClient(fake_response)
    e_mail = "We need 50 pieces on the next friday"

    result = services.extract_order_draft(email_text=e_mail, client=fake_client)

    assert result == draft


def test_none_parsed_output_returns_llm_unavailable():
    fake_usage = FakeUsage(100, 50)
    fake_response = FakeResponse(
        content=[],
        stop_reason="end_turn",
        usage=fake_usage,
        model="claude-haiku-10-10",
        parsed_output=None,
    )
    fake_client = FakeClient(fake_response)
    e_mail = "We need 50 pieces on the next friday"

    with pytest.raises(LlmUnavailableError):
        services.extract_order_draft(e_mail, fake_client)


def test_summarize_order_api_error_raises_llm_unavailable():
    new_order = make_order()
    fake_client = FailingClient()

    with pytest.raises(LlmUnavailableError):
        services.summarize_order(new_order, fake_client)


def test_operator_gets_403_on_endpoint_from_text(operator_client, fake_llm):
    response = operator_client.post(
        "/orders/from-text", json={"text": "some e-mail here"}
    )

    assert response.status_code == 403
    assert fake_llm.messages.call_counts == 0


def test_extract_order_draft_truncated_json_raises_llm_unavailable():
    fake_client = FailingClient()
    fake_client.messages = TruncatedMessages()

    with pytest.raises(LlmUnavailableError):
        services.extract_order_draft("asdasd", fake_client)


def test_admin_get_200_and_summary(admin_client, order, fake_llm):
    response = admin_client.get(f"/orders/{order['id']}/summary")
    assert response.status_code == 200
    assert response.json()["summary"] == "fake summary"
    assert fake_llm.messages.call_counts == 1


def test_operator_client_get_200_on_summary(operator_client, order, fake_llm):
    response = operator_client.get(f"/orders/{order['id']}/summary")
    assert response.status_code == 200
    assert fake_llm.messages.call_counts == 1


def test_not_logged_in_user_asks_for_summary(client, order, fake_llm):
    response = client.get(f"/orders/{order['id']}/summary")
    assert response.status_code == 401
    assert fake_llm.messages.call_counts == 0


def test_summary_wrong_id_returns_404(admin_client, fake_llm):
    response = admin_client.get("/orders/999/summary")
    assert response.status_code == 404
    assert fake_llm.messages.call_counts == 0


def test_exceeding_llm_limits(operator_client, order, monkeypatch, fake_llm):
    monkeypatch.setattr(services, "SUMMARY_DAILY_LIMIT", 1)
    response = operator_client.get(f"/orders/{order['id']}/summary")
    assert response.status_code == 200
    assert fake_llm.messages.call_counts == 1

    response = operator_client.get(f"/orders/{order['id']}/summary")
    assert response.status_code == 429
    assert fake_llm.messages.call_counts == 1


def test_failing_client_returns_503(admin_client, order, failing_llm):
    response = admin_client.get(f"/orders/{order['id']}/summary")
    assert response.status_code == 503
    assert (
        response.json()["detail"] == "LLM is temporarily unavailable, try again later"
    )


def test_no_key_returns_503(monkeypatch, admin_client, order):
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    response = admin_client.get(f"/orders/{order['id']}/summary")

    assert response.status_code == 503


def test_not_started_order():
    new_order = make_order()
    new_order.steps = [
        OrderStepDB(step_name="cutting", step_order=1, status=StepStatus.PENDING),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.PENDING),
    ]

    facts = services.build_order_facts(new_order, now=NOW)

    assert facts["completed_steps"] == 0
    assert facts["total_steps"] == 2
    assert facts["current_step"] is None
    assert facts["days_overdue"] == 0


def test_one_step_in_progress_without_employee():
    new_order = make_order()

    new_order.steps = [
        OrderStepDB(step_name="cutting", step_order=1, status=StepStatus.DONE),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.IN_PROGRESS),
        OrderStepDB(step_name="milling", step_order=3, status=StepStatus.PENDING),
    ]

    facts = services.build_order_facts(new_order, now=NOW)
    assert facts["total_steps"] == 3
    assert facts["current_step"]["step_name"] == "turning"
    assert facts["current_step"]["employee"] is None
    assert facts["days_overdue"] == 0
    assert facts["completed_steps"] == 1


def test_delayed_order_not_finished():
    new_order = make_order()
    new_order.planned_completion_date = date(2026, 12, 10)
    new_order.steps = [
        OrderStepDB(step_name="cutting", step_order=1, status=StepStatus.DONE),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.PENDING),
    ]

    facts = services.build_order_facts(new_order, now=NOW)

    assert facts["completed_steps"] == 1
    assert facts["days_overdue"] == 2
    assert facts["is_finished"] is False


def test_order_is_finished():
    new_order = make_order()
    new_order.steps = [
        OrderStepDB(step_name="cutting", step_order=1, status=StepStatus.DONE),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.DONE),
    ]

    facts = services.build_order_facts(new_order, now=NOW)

    assert facts["completed_steps"] == facts["total_steps"]
    assert facts["days_overdue"] == 0
    assert facts["is_finished"] is True


def test_orders_with_notes():
    new_order = make_order()
    new_order.steps = [
        OrderStepDB(
            step_name="cutting",
            step_order=1,
            status=StepStatus.DONE,
            note="had problems but everythings allright",
        ),
        OrderStepDB(
            step_name="turning",
            step_order=2,
            status=StepStatus.IN_PROGRESS,
            note="cut too short and I have problems",
        ),
        OrderStepDB(step_name="milling", step_order=3, status=StepStatus.PENDING),
    ]

    facts = services.build_order_facts(new_order, now=NOW)

    assert len(facts["notes"]) == 2
    assert facts["notes"][0] == "cutting: had problems but everythings allright"
