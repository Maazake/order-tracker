import random
from datetime import date, timedelta

from app.database import SessionLocal
from app.models import OrderDB
from app.schemas import ProcessStage

ELEMENT_NAMES = [
    "DRILL",
    "END_MILL",
    "SHAFT",
    "FLANGE",
    "BUSHING",
    "GEAR",
    "HOUSING",
    "PIN",
    "PUNCH",
    "VALVE_BODY",
]


def seed_database(num_orders: int = 15):
    db = SessionLocal()
    try:
        orders_to_add = []
        stages = list(ProcessStage)

        for _ in range(num_orders):
            random_days = random.randint(1, 45)
            completion_date = date.today() + timedelta(days=random_days) # noqa: DTZ011

            order = OrderDB(
                element_name=random.choice(ELEMENT_NAMES),
                count=random.randint(5, 200),
                planned_completion_date=completion_date,
                status=random.choice(stages),
            )
            orders_to_add.append(order)

        db.add_all(orders_to_add)
        db.commit()
        print(f"✅ Sucessfully added {num_orders} orders!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error while seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
