from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import EmployeeDB, OrderDB, OrderStepDB
from app.schemas import Order, ProcessStage, StepStatus


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
            raise ConflictError("Previus step is not done yet")

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
        raise ConflictError(f"Stop is already {step.status}")

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
