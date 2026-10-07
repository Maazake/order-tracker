from datetime import date

from app.database import Base
from app.schemas import ProcessStage
from sqlalchemy import Date, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class OrderDB(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    element_name: Mapped[str] = mapped_column(String, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_completion_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ProcessStage] = mapped_column(
        Enum(ProcessStage), default=ProcessStage.CUTTING, nullable=False
    )
