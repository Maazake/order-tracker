from datetime import UTC, date, datetime

from app.models import OrderDB, OrderStepDB
from app.schemas import StepStatus
from app.services import build_order_facts

NOW = datetime(2026, 12, 12, 9, 0, 0, 0, tzinfo=UTC)


def make_order():
    return OrderDB(
        element_name="VALVE", count=10, planned_completion_date=date(2026, 12, 15)
    )


def test_not_started_order():
    new_order = make_order()
    new_order.steps = [
        OrderStepDB(step_name="cutting", step_order=1, status=StepStatus.PENDING),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.PENDING),
    ]

    facts = build_order_facts(new_order, now=NOW)

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

    facts = build_order_facts(new_order, now=NOW)
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

    facts = build_order_facts(new_order, now=NOW)

    assert facts["completed_steps"] == 1
    assert facts["days_overdue"] == 2
    assert facts["is_finished"] is False


def test_order_is_finished():
    new_order = make_order()
    new_order.steps = [
        OrderStepDB(step_name="cutting", step_order=1, status=StepStatus.DONE),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.DONE),
    ]

    facts = build_order_facts(new_order, now=NOW)

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
            step_order=3,
            status=StepStatus.IN_PROGRESS,
            note="cut too short and I have problems",
        ),
        OrderStepDB(step_name="turning", step_order=2, status=StepStatus.PENDING),
    ]

    facts = build_order_facts(new_order, now=NOW)

    assert len(facts["notes"]) == 2
    assert facts["notes"][0] == "cutting: had problems but everythings allright"
