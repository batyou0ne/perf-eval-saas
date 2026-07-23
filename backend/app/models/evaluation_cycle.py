import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class CycleStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class EvaluationCycle(TimestampMixin, Base):
    __tablename__ = "evaluation_cycles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date())
    end_date: Mapped[date] = mapped_column(Date())
    status: Mapped[CycleStatus] = mapped_column(
        SAEnum(CycleStatus, name="cycle_status", values_callable=lambda s: [x.value for x in s]),
        default=CycleStatus.DRAFT,
    )

    company: Mapped["Company"] = relationship()
    questions: Mapped[list["Question"]] = relationship(
        back_populates="cycle", order_by="Question.order", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="cycle", cascade="all, delete-orphan")
