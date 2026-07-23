import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class EvaluationSummary(TimestampMixin, Base):
    __tablename__ = "evaluation_summaries"
    __table_args__ = (UniqueConstraint("cycle_id", "subject_id", name="uq_summary_cycle_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_cycles.id"))
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[dict] = mapped_column(JSONB)

    cycle: Mapped["EvaluationCycle"] = relationship()
    subject: Mapped["User"] = relationship()
