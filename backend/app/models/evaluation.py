import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class EvaluationType(str, enum.Enum):
    SELF = "self"
    MANAGER = "manager"


class EvaluationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"


class Evaluation(TimestampMixin, Base):
    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("cycle_id", "subject_id", "type", name="uq_evaluation_cycle_subject_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_cycles.id"))
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    evaluator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[EvaluationType] = mapped_column(
        SAEnum(EvaluationType, name="evaluation_type", values_callable=lambda s: [x.value for x in s])
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        SAEnum(EvaluationStatus, name="evaluation_status", values_callable=lambda s: [x.value for x in s]),
        default=EvaluationStatus.NOT_STARTED,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cycle: Mapped["EvaluationCycle"] = relationship(back_populates="evaluations")
    subject: Mapped["User"] = relationship(foreign_keys=[subject_id])
    evaluator: Mapped["User"] = relationship(foreign_keys=[evaluator_id])
    responses: Mapped[list["Response"]] = relationship(back_populates="evaluation", cascade="all, delete-orphan")
