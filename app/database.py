from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlmodel import create_engine

DATABASE_URL = "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/order_tracker"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
