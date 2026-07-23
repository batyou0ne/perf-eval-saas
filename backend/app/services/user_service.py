import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import get_user_by_id
from app.models.user import User


async def assign_manager(db: AsyncSession, actor: User, target_user_id: uuid.UUID, manager_id: uuid.UUID) -> User:
    target = await get_user_by_id(db, target_user_id)
    if target is None or target.company_id != actor.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if manager_id == target_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user cannot be their own manager")

    manager = await get_user_by_id(db, manager_id)
    if manager is None or manager.company_id != actor.company_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Manager must belong to the same company")

    target.manager_id = manager_id
    await db.commit()
    await db.refresh(target)
    return target
