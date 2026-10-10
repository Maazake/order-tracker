from datetime import UTC, datetime, timedelta

from app.database import Base, SessionLocal, engine
from app.models import EmployeeDB, OrderDB, OrderStepDB
from app.schemas import ProcessStage, StepStatus


def seed_database() -> None:
    print("Clearing database and recreating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("Creating sample employees...")
        emp1 = EmployeeDB(name="Jan Kowalski", role="Lathe Operator")
        emp2 = EmployeeDB(name="Adam Nowak", role="Milling Operator")
        emp3 = EmployeeDB(name="Ewa Wisniewska", role="Quality Inspector")

        db.add_all([emp1, emp2, emp3])
        db.commit()
        db.refresh(emp1)
        db.refresh(emp2)
        db.refresh(emp3)

        print("Creating Order 1 (DRILL) with steps...")
        order1 = OrderDB(
            element_name="DRILL",
            count=15,
            planned_completion_date=datetime.now(UTC) + timedelta(days=14),
        )
        db.add(order1)
        db.commit()
        db.refresh(order1)

        steps_order1 = [
            OrderStepDB(
                order_id=order1.id,
                step_name=ProcessStage.CUTTING.value,
                step_order=1,
                status=StepStatus.COMPLETED,
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
            planned_completion_date=datetime.now(UTC) + timedelta(days=7),
        )
        db.add(order2)
        db.commit()
        db.refresh(order2)

        steps_order2 = [
            OrderStepDB(
                order_id=order2.id,
                step_name=ProcessStage.CUTTING.value,
                step_order=1,
                status=StepStatus.COMPLETED,
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

        db.commit()
        print("Database seeded successfully.")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
