from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import EmployeeDB, OrderDB, OrderStepDB, UserDB
from app.schemas import (
    ProcessStage,
    StepStatus,
    UserRole,
)
from app.security import hash_password


def seed_database() -> None:
    print("Clearing database and recreating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal.begin() as db:
        print("Creating sample employees...")
        emp1 = EmployeeDB(name="Jan Kowalski", role="Lathe Operator")
        emp2 = EmployeeDB(name="Adam Nowak", role="Milling Operator")
        emp3 = EmployeeDB(name="Ewa Wisniewska", role="Quality Inspector")

        db.add_all([emp1, emp2, emp3])
        db.flush()

        print("Creating Order 1 (DRILL) with steps...")
        order1 = OrderDB(
            element_name="DRILL",
            count=15,
            planned_completion_date=(datetime.now(UTC) + timedelta(days=14)).date(),
        )
        db.add(order1)
        db.flush()

        steps_order1 = [
            OrderStepDB(
                order_id=order1.id,
                step_name=ProcessStage.CUTTING.value,
                step_order=1,
                status=StepStatus.DONE,
                note="Material cut with 2mm margin",
                assigned_employee_id=emp1.id,
            ),
            OrderStepDB(
                order_id=order1.id,
                step_name=ProcessStage.TURNING.value,
                step_order=2,
                status=StepStatus.IN_PROGRESS,
                note="Rough machining in progress",
                assigned_employee_id=emp1.id,
            ),
            OrderStepDB(
                order_id=order1.id,
                step_name=ProcessStage.QUALITY_CONTROL.value,
                step_order=3,
                status=StepStatus.PENDING,
                assigned_employee_id=emp3.id,
            ),
        ]
        db.add_all(steps_order1)

        print("Creating Order 2 (SHAFT) with steps...")
        order2 = OrderDB(
            element_name="SHAFT",
            count=5,
            planned_completion_date=(datetime.now(UTC) + timedelta(days=7)).date(),
        )
        db.add(order2)
        db.flush()

        steps_order2 = [
            OrderStepDB(
                order_id=order2.id,
                step_name=ProcessStage.CUTTING.value,
                step_order=1,
                status=StepStatus.DONE,
                assigned_employee_id=emp1.id,
            ),
            OrderStepDB(
                order_id=order2.id,
                step_name=ProcessStage.MILLING.value,
                step_order=2,
                status=StepStatus.IN_PROGRESS,
                assigned_employee_id=emp2.id,
            ),
            OrderStepDB(
                order_id=order2.id,
                step_name=ProcessStage.PACKING.value,
                step_order=3,
                status=StepStatus.PENDING,
                assigned_employee_id=None,
            ),
        ]
        db.add_all(steps_order2)

        create_admin(db)

    print("Database seeded successfully.")


def create_admin(db: Session) -> None:
    exists = db.scalar(select(UserDB).where(UserDB.role == "admin"))
    if exists:
        return
    db.add(
        UserDB(
            username="mazak",
            hashed_password=hash_password("123"),
            role=UserRole.ADMIN,
        )
    )


if __name__ == "__main__":
    seed_database()
