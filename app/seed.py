"""Load demo data: employees, users and orders at different production stages.

Tables must already exist (run `alembic upgrade head` first).
Orders are created through the service layer, so every order has all 7 steps
and every step history follows the same rules as the API.
The script is idempotent: running it again does not duplicate anything.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.config import settings
from app.database import SessionLocal
from app.models import EmployeeDB, OrderDB, UserDB
from app.schemas import Order, ProcessStage, UserRole
from app.security import hash_password

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo1234"

STEP_DURATION = timedelta(hours=3)
BREAK_BETWEEN_STEPS = timedelta(hours=1)

EMPLOYEES = [
    ("Jan Kowalski", "Lathe Operator"),
    ("Adam Nowak", "Milling Operator"),
    ("Marta Zielinska", "Finishing Operator"),
    ("Ewa Wisniewska", "Quality Inspector"),
    ("Piotr Lewandowski", "Logistics"),
]

STAGE_ROLES = {
    ProcessStage.CUTTING: "Lathe Operator",
    ProcessStage.TURNING: "Lathe Operator",
    ProcessStage.MILLING: "Milling Operator",
    ProcessStage.POLISHING: "Finishing Operator",
    ProcessStage.WASHING: "Finishing Operator",
    ProcessStage.QUALITY_CONTROL: "Quality Inspector",
    ProcessStage.PACKING: "Logistics",
}


@dataclass
class OrderScenario:
    element_name: str
    count: int
    planned_in_days: int
    started_days_ago: float = 0
    done_steps: int = 0
    in_progress: bool = False
    notes: dict[ProcessStage, str] = field(default_factory=dict)


SCENARIOS = [
    OrderScenario("SHAFT", count=20, planned_in_days=21),
    OrderScenario("FLANGE", count=50, planned_in_days=30),
    OrderScenario(
        "DRILL",
        count=15,
        planned_in_days=10,
        started_days_ago=1,
        done_steps=2,
        in_progress=True,
        notes={
            ProcessStage.CUTTING: "Material cut with 2 mm allowance.",
            ProcessStage.TURNING: "Rough turning done, diameter left +0.3 mm.",
        },
    ),
    OrderScenario(
        "GEAR",
        count=8,
        planned_in_days=3,
        started_days_ago=2,
        done_steps=4,
        in_progress=True,
        notes={
            ProcessStage.MILLING: "Teeth milled with module 2 cutter, tool changed.",
            ProcessStage.POLISHING: "Burrs on tooth edges removed manually.",
        },
    ),
    OrderScenario(
        "BUSHING",
        count=100,
        planned_in_days=1,
        started_days_ago=2,
        done_steps=5,
        in_progress=True,
        notes={
            ProcessStage.TURNING: "Inner diameter 25H7 checked with plug gauge.",
            ProcessStage.WASHING: "Washed in ultrasonic bath, 10 min.",
        },
    ),
    OrderScenario(
        "VALVE BODY",
        count=12,
        planned_in_days=-2,
        started_days_ago=6,
        done_steps=7,
        notes={
            ProcessStage.MILLING: "Sealing face milled, flatness 0.02 mm.",
            ProcessStage.QUALITY_CONTROL: (
                "2 pcs rejected: thread M12 out of tolerance, reworked and accepted."
            ),
            ProcessStage.PACKING: "Packed in VCI foil, 2 boxes.",
        },
    ),
    OrderScenario(
        "PIN",
        count=200,
        planned_in_days=-3,
        started_days_ago=8,
        done_steps=2,
        notes={
            ProcessStage.TURNING: "Waiting for new milling fixture, step on hold.",
        },
    ),
]


def seed_users(db: Session) -> None:
    admin_exists = db.scalar(select(UserDB).where(UserDB.role == UserRole.ADMIN))
    if not admin_exists:
        db.add(
            UserDB(
                username=settings.admin_username,
                hashed_password=hash_password(
                    settings.admin_password.get_secret_value()
                ),
                role=UserRole.ADMIN,
            )
        )
        print(f"Created admin '{settings.admin_username}'.")

    demo_exists = db.scalar(select(UserDB).where(UserDB.username == DEMO_USERNAME))
    if not demo_exists:
        db.add(
            UserDB(
                username=DEMO_USERNAME,
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.OPERATOR,
            )
        )
        print(f"Created demo operator '{DEMO_USERNAME}'.")


def seed_employees(db: Session) -> dict[str, EmployeeDB]:
    employees = [EmployeeDB(name=name, role=role) for name, role in EMPLOYEES]
    db.add_all(employees)
    db.flush()
    print(f"Created {len(employees)} employees.")
    return {employee.role: employee for employee in employees}


def seed_order(
    db: Session,
    scenario: OrderScenario,
    employees_by_role: dict[str, EmployeeDB],
    now: datetime,
) -> None:
    order = services.create_order(
        db,
        Order(
            element_name=scenario.element_name,
            count=scenario.count,
            planned_completion_date=(
                now + timedelta(days=scenario.planned_in_days)
            ).date(),
        ),
    )

    moment = now - timedelta(days=scenario.started_days_ago)
    for step in order.steps[: scenario.done_steps]:
        stage = ProcessStage(step.step_name)
        employee = employees_by_role[STAGE_ROLES[stage]]

        services.start_step(db, step.id, employee.id, now=moment)
        moment += STEP_DURATION
        services.complete_step(db, step.id, note=scenario.notes.get(stage), now=moment)
        moment += BREAK_BETWEEN_STEPS

    if scenario.in_progress:
        step = order.steps[scenario.done_steps]
        employee = employees_by_role[STAGE_ROLES[ProcessStage(step.step_name)]]
        services.start_step(db, step.id, employee.id, now=moment)

    if moment > now:
        raise ValueError(
            f"Scenario {scenario.element_name} ends in the future, "
            "increase started_days_ago."
        )


def seed_database() -> None:
    now = datetime.now(UTC)

    with SessionLocal.begin() as db:
        seed_users(db)

        if db.scalar(select(OrderDB).limit(1)) is not None:
            print("Orders already exist, skipping employees and orders.")
            return

        employees_by_role = seed_employees(db)
        for scenario in SCENARIOS:
            seed_order(db, scenario, employees_by_role, now)
        print(f"Created {len(SCENARIOS)} orders.")

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()
