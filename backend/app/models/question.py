import enum
import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class QuestionType(str, enum.Enum):
    RATING = "rating"
    TEXT = "text"


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_cycles.id"))
    text: Mapped[str] = mapped_column(Text())
    type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType, name="question_type", values_callable=lambda s: [x.value for x in s])
    )
    order: Mapped[int] = mapped_column(Integer(), default=0)

    cycle: Mapped["EvaluationCycle"] = relationship(back_populates="questions")
