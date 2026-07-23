import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.crud.user import list_users_by_company
from app.models.user import User, UserRole
from app.schemas.auth import UserRead
from app.schemas.user import AssignManagerRequest
from app.services import user_service

router = APIRouter()


@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> list[UserRead]:
    return await list_users_by_company(db, current_user.company_id)


@router.post("/users/{user_id}/manager", response_model=UserRead)
async def assign_manager(
    user_id: uuid.UUID,
    body: AssignManagerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> UserRead:
    return await user_service.assign_manager(db, current_user, user_id, body.manager_id)
