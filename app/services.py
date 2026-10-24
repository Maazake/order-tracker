import json
from datetime import UTC, datetime

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import ConflictError, NotFoundError
from app.models import EmployeeDB, OrderDB, OrderStepDB
from app.schemas import Order, ProcessStage, StepStatus

SUMMARY_SYSTEM_PROMPT = """You summarize production orders for a production manager.
You will receive order data as JSON inside <order> tags.
Write exactly 2 sentences in English.
Use only facts from the data. Do not guess or add information.
If the order is finished, say so first.
If the order is overdue, mention it first.
If the order is not finished and no step is in progress, mention it first.
Write in plain language. Do not mention field names, JSON or null values."""


def summarize_order(order: OrderDB, client: anthropic.Anthropic) -> str:
    facts = build_order_facts(order)
    order_json = json.dumps(facts, ensure_ascii=False, indent=2)
    content = f"<order>\n{order_json}\n</order>"

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        system=SUMMARY_SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": content}],
    )

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise RuntimeError(f"Reason for no text: {response.stop_reason}")

    return text


def start_step(
    db: Session, step_id: int, employee_id: int, now: datetime | None = None
) -> OrderStepDB:
    step = db.get(OrderStepDB, step_id)
    if step is None:
        raise NotFoundError(f"Step ID {step_id} not found")

    employee = db.get(EmployeeDB, employee_id)
    if employee is None:
        raise NotFoundError(f"Employee ID {employee_id} not found")

    if step.status != StepStatus.PENDING:
        raise ConflictError(f"Step is already {step.status}")

    if step.step_order > 1:
        previous = db.scalar(
            select(OrderStepDB).where(
                OrderStepDB.order_id == step.order_id,
                OrderStepDB.step_order == step.step_order - 1,
            )
        )
        if previous is None or previous.status != StepStatus.DONE:
            raise ConflictError("Previous step is not done yet")

    step.status = StepStatus.IN_PROGRESS
    step.assigned_employee_id = employee_id
    step.started_at = now or datetime.now(UTC)
    db.flush()
    return step


def complete_step(
    db: Session,
    step_id: int,
    note: str | None = None,
    now: datetime | None = None,
) -> OrderStepDB:
    step = db.get(OrderStepDB, step_id)
    if step is None:
        raise NotFoundError(f"Step ID {step_id} not found")

    if step.status != StepStatus.IN_PROGRESS:
        raise ConflictError(f"Step is already {step.status}")

    if note is not None:
        step.note = note

    step.status = StepStatus.DONE
    step.completed_at = now or datetime.now(UTC)
    db.flush()
    return step


def create_order(db: Session, order_data: Order) -> OrderDB:
    new_order = OrderDB(**order_data.model_dump())
    db.add(new_order)
    db.flush()

    steps_to_create = []

    for step_number, stage in enumerate(ProcessStage, start=1):
        step = OrderStepDB(
            order_id=new_order.id,
            step_name=stage.value,
            step_order=step_number,
            status=StepStatus.PENDING,
        )
        steps_to_create.append(step)

    db.add_all(steps_to_create)
    db.flush()
    return new_order


def build_order_facts(order: OrderDB, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)

    done = [s for s in order.steps if s.status == StepStatus.DONE]
    current_step = next(
        (c for c in order.steps if c.status == StepStatus.IN_PROGRESS), None
    )
    current = None

    if current_step is not None:
        employee = current_step.assigned_employee
        current = {
            "step_name": current_step.step_name,
            "employee": employee.name if employee is not None else None,
        }

    is_finished = len(done) == len(order.steps)
    days_late = (now.date() - order.planned_completion_date).days

    days_overdue = 0
    if days_late > 0 and not is_finished:
        days_overdue = days_late

    notes = [f"{n.step_name}: {n.note}" for n in order.steps if n.note is not None]

    return {
        "element_name": order.element_name,
        "count": order.count,
        "completed_steps": len(done),
        "total_steps": len(order.steps),
        "current_step": current,
        "planned_completion_date": order.planned_completion_date.isoformat(),
        "days_overdue": days_overdue,
        "notes": notes,
        "is_finished": is_finished,
    }
