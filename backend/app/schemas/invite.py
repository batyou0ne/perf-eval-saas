import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class InviteCreate(BaseModel):
    email: str
    role: UserRole
    company_id: uuid.UUID | None = None  # required for super_admin, ignored for company_admin


class InviteCreateResponse(BaseModel):
    email: str
    role: UserRole
    invite_link: str
    expires_at: datetime


class InvitePreview(BaseModel):
    email: str
    role: UserRole
    company_name: str
    expires_at: datetime
    accepted_at: datetime | None


class InviteAccept(BaseModel):
    full_name: str
    password: str
