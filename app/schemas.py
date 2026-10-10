from datetime import date, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


def default_completion_date() -> date:
    return date.today() + timedelta(days=30)  # noqa: DTZ011


class ProcessStage(StrEnum):
    CUTTING = "cutting"
    TURNING = "turning"
    MILLING = "milling"
    POLISHING = "polishing"
    WASHING = "washing"
    QUALITY_CONTROL = "quality_control"
    PACKING = "packing"


PROCESS_STEPS = list(ProcessStage)


class StepStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "done"


STEP_STATUS = list(StepStatus)


class Order(BaseModel):
    element_name: str = "DRILL"
    count: PositiveInt
    planned_completion_date: date = Field(default_factory=default_completion_date)


class Employee(BaseModel):
    name: str
    role: str


class EmployeeResponse(Employee):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OrderStep(BaseModel):
    id: int
    order_id: int
    step_name: str
    step_order: int
    status: str
    note: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_employee_id: int | None = None


class OrderStepResponse(OrderStep):
    assigned_employee: EmployeeResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(Order):
    id: int
    steps: list[OrderStepResponse] = []

    model_config = ConfigDict(from_attributes=True)

class StepStart(BaseModel):
    employee_id: int
    started_at: datetime

class StepComplete(BaseModel):
    note: str | None = None


    
