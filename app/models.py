from datetime import date, datetime

from app.database import Base
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EmployeeDB(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    role: Mapped[str]

    steps: Mapped[list["OrderStepDB"]] = relationship(
        back_populates="assigned_employee"
    )


class OrderDB(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    element_name: Mapped[str]
    count: Mapped[int]
    planned_completion_date: Mapped[date]

    steps: Mapped[list["OrderStepDB"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderStepDB(Base):
    __tablename__ = "order_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    step_name: Mapped[str]
    step_order: Mapped[int]
    status: Mapped[str] = mapped_column(default="PENDING")
    note: Mapped[str | None] = mapped_column(default=None)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    assigned_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), default=None
    )

    order: Mapped["OrderDB"] = relationship(back_populates="steps")
    assigned_employee: Mapped["EmployeeDB | None"] = relationship(
        back_populates="steps"
    )
