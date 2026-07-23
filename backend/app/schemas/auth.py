import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    company_id: uuid.UUID | None
    manager_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
