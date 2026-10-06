from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


def default_completion_date() -> date:
    return date.today() + timedelta(days=30)  # noqa: DTZ011


fake_db = []
orders_ids = 0


class Order(BaseModel):
    element_name: str = "DRILL HSS"
    planned_completion_date: date = Field(default_factory=default_completion_date)
    status: str = "cięcie"


app = FastAPI()


class OrderResponse(Order):
    id: int


@app.get("/orders")
def get_all_orders():
    return fake_db


@app.get("orders/{order_id}", response_model=OrderResponse)
def get_single_order(order_id: int):
    for order in fake_db:
        if order.id == order_id:
            return order
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Zlecenie o ID {order_id} nie istnieje",
    )


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_new_order(order_data: Order):
    global orders_ids
    orders_ids += 1

    new_order = OrderResponse(id=orders_ids, **order_data.model_dump())
    fake_db.append(new_order)

    return new_order
