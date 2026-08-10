import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.crud.user import list_active_users_by_company, list_users_by_company
from app.models.user import User, UserRole
from app.schemas.auth import UserRead
from app.schemas.pagination import Page
from app.schemas.user import AssignManagerRequest, UserOption
from app.services import user_service

router = APIRouter()


# Declared before the parameterised /users/... routes so the literal path wins.
@router.get("/users/options", response_model=list[UserOption])
async def list_user_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> list[UserOption]:
    """Every active colleague, unpaginated — this feeds the manager picker, which needs
    the full set to stay correct (you can't pick someone who isn't on the current page)."""
    return await list_active_users_by_company(db, current_user.company_id)


@router.get("/users", response_model=Page[UserRead])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> Page[UserRead]:
    users, total = await list_users_by_company(
        db, current_user.company_id, offset=(page - 1) * page_size, limit=page_size
    )
    return Page(
        items=[UserRead.model_validate(u) for u in users], total=total, page=page, page_size=page_size
    )


@router.post("/users/{user_id}/manager", response_model=UserRead)
async def assign_manager(
    user_id: uuid.UUID,
    body: AssignManagerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> UserRead:
    return await user_service.assign_manager(db, current_user, user_id, body.manager_id)


@router.post("/users/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> UserRead:
    return await user_service.deactivate_user(db, current_user, user_id)


@router.post("/users/{user_id}/reactivate", response_model=UserRead)
async def reactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> UserRead:
    return await user_service.reactivate_user(db, current_user, user_id)
