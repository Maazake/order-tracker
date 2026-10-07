from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel, Field, PositiveInt


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

class Order(BaseModel):
    element_name: str = "DRILL"
    count: PositiveInt 
    planned_completion_date: date = Field(default_factory=default_completion_date)
    status: ProcessStage = ProcessStage.CUTTING


class OrderResponse(Order):
    id: int
