from datetime import UTC, datetime
from typing import Annotated

from app.database import get_db
from app.models import EmployeeDB, OrderDB, OrderStepDB
from app.schemas import (
    Employee,
    EmployeeResponse,
    Order,
    OrderResponse,
    OrderStepResponse,
    ProcessStage,
    StepComplete,
    StepStart,
    StepStatus,
)
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

DbSession = Annotated[Session, Depends(get_db)]


app = FastAPI()


@app.get("/orders", response_model=list[OrderResponse])
def get_all_orders(db: DbSession):
    return db.scalars(select(OrderDB)).all()


def find_order_or_404(order_id: int, db: Session):
    order = db.get(OrderDB, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID {order_id} does not exist",
        )
    return order


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_single_order(order_id: int, db: DbSession):
    order = find_order_or_404(order_id, db)
    return order


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_new_order(order_data: Order, db: DbSession):

    new_order = OrderDB(**order_data.model_dump())
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

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
    db.commit()
    db.refresh(new_order)

    return new_order


def find_step_or_404(step_id: int, db: Session):
    step = db.get(OrderStepDB, step_id)

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step ID  {step_id} not found",
        )
    return step


@app.post("/steps/{step_id}/start", response_model=OrderStepResponse)
def start_step(step_id: int, db: DbSession, data: StepStart):
    step = find_step_or_404(step_id, db)
    employee = db.get(EmployeeDB, data.employee_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee ID {data.employee_id} not found",
        )

    if step.status != StepStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step is already {step.status}",
        )

    if step.step_order > 1:
        previous = db.scalar(
            select(OrderStepDB).where(
                OrderStepDB.order_id == step.order_id,
                OrderStepDB.step_order == step.step_order - 1,
            )
        )
        if previous is None or previous.status != StepStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Previous step is not done yet",
            )

    step.status = StepStatus.IN_PROGRESS
    step.assigned_employee_id = employee.id
    step.started_at = datetime.now(UTC)
    db.commit()
    db.refresh(step)
    return step


@app.post("/steps/{step_id}/complete", response_model=OrderStepResponse)
def complete_step(step_id: int, data: StepComplete, db: DbSession):
    step = find_step_or_404(step_id, db)

    if step.status != StepStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step ID {step_id} is not in progress",
        )

    step.status = StepStatus.COMPLETED
    step.completed_at = datetime.now(UTC)
    if data.note is not None:
        step.note = data.note
    db.commit()
    db.refresh(step)
    return step


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: DbSession):
    order = find_order_or_404(order_id, db)
    db.delete(order)
    db.commit()


@app.get("/employees", response_model=list[EmployeeResponse])
def get_all_employees(db: DbSession):
    return db.scalars(select(EmployeeDB)).all()


@app.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_new_employee(employee_data: Employee, db: DbSession):

    new_employee = EmployeeDB(**employee_data.model_dump())
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee
