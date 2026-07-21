import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin
from app.models.user import UserRole


class Invite(TimestampMixin, Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda roles: [r.value for r in roles])
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship()
    invited_by: Mapped["User"] = relationship()
