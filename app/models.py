from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.schemas import StepStatus, UserRole


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(default=UserRole.OPERATOR, nullable=False)


class EmployeeDB(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str]

    steps: Mapped[list[OrderStepDB]] = relationship(back_populates="assigned_employee")


class OrderDB(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    element_name: Mapped[str]
    count: Mapped[int]
    planned_completion_date: Mapped[date]

    steps: Mapped[list[OrderStepDB]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStepDB.step_order",
    )


class OrderStepDB(Base):
    __tablename__ = "order_steps"
    __table_args__ = (
        UniqueConstraint("order_id", "step_order", name="uq_order_steps_order_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    step_name: Mapped[str]
    step_order: Mapped[int]
    status: Mapped[str] = mapped_column(default=StepStatus.PENDING)
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

    order: Mapped[OrderDB] = relationship(back_populates="steps")
    assigned_employee: Mapped[EmployeeDB | None] = relationship(back_populates="steps")
