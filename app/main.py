from typing import Annotated

from app.database import Base, engine, get_db
from app.models import OrderDB
from app.schemas import PROCESS_STEPS, Order, OrderResponse
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

DbSession = Annotated[Session, Depends(get_db)]
Base.metadata.create_all(bind=engine)

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

    return new_order


@app.patch("/orders/{order_id}/next-step", response_model=OrderResponse)
def update_order(order_id: int, db: DbSession):
    order = find_order_or_404(order_id, db)
    current_index = PROCESS_STEPS.index(order.status)
    if current_index + 1 < len(PROCESS_STEPS):
        order.status = PROCESS_STEPS[current_index + 1]
        db.commit()
        db.refresh(order)
        return order

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Order is already done.",
    )


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: DbSession):
    order = find_order_or_404(order_id, db)
    db.delete(order)
    db.commit()
