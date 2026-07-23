import uuid

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Response(TimestampMixin, Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("evaluation_id", "question_id", name="uq_response_evaluation_question"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluations.id"))
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"))
    rating_value: Mapped[int | None] = mapped_column(Integer())
    text_value: Mapped[str | None] = mapped_column(Text())

    evaluation: Mapped["Evaluation"] = relationship(back_populates="responses")
    question: Mapped["Question"] = relationship()
