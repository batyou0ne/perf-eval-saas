import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import get_user_by_id
from app.models.user import User, UserRole


async def _get_target_in_company(db: AsyncSession, actor: User, target_user_id: uuid.UUID) -> User:
    target = await get_user_by_id(db, target_user_id)
    if target is None or target.company_id != actor.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return target


async def assign_manager(db: AsyncSession, actor: User, target_user_id: uuid.UUID, manager_id: uuid.UUID) -> User:
    target = await _get_target_in_company(db, actor, target_user_id)

    if manager_id == target_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user cannot be their own manager")

    manager = await get_user_by_id(db, manager_id)
    if manager is None or manager.company_id != actor.company_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Manager must belong to the same company")

    target.manager_id = manager_id
    await db.commit()
    await db.refresh(target)
    return target


async def deactivate_user(db: AsyncSession, actor: User, target_user_id: uuid.UUID) -> User:
    target = await _get_target_in_company(db, actor, target_user_id)

    if target.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")
    # HR manages the rank-and-file but not the company's admins.
    if actor.role == UserRole.HR and target.role == UserRole.COMPANY_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "HR cannot deactivate a company admin")

    target.is_active = False
    await db.commit()
    await db.refresh(target)
    return target


async def reactivate_user(db: AsyncSession, actor: User, target_user_id: uuid.UUID) -> User:
    target = await _get_target_in_company(db, actor, target_user_id)

    target.is_active = True
    await db.commit()
    await db.refresh(target)
    return target
