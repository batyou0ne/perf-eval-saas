import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.evaluation import list_open_manager_evaluations_for_evaluator
from app.crud.task import list_open_tasks_for_assignee
from app.crud.user import get_user_by_id, list_direct_reports
from app.models.task import TaskStatus
from app.models.user import User, UserRole


async def _get_target_in_company(db: AsyncSession, actor: User, target_user_id: uuid.UUID) -> User:
    target = await get_user_by_id(db, target_user_id)
    if target is None or target.company_id != actor.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return target


async def assign_manager(
    db: AsyncSession, actor: User, target_user_id: uuid.UUID, manager_id: uuid.UUID | None
) -> User:
    target = await _get_target_in_company(db, actor, target_user_id)

    if manager_id is None:
        target.manager_id = None
        await db.commit()
        await db.refresh(target)
        return target

    if manager_id == target_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user cannot be their own manager")

    manager = await get_user_by_id(db, manager_id)
    if manager is None or manager.company_id != actor.company_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Manager must belong to the same company")
    # A deactivated user can't log in, so any manager evaluation assigned to them
    # would be impossible to complete (see activate_cycle, which skips them too).
    if not manager.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Manager must be an active user")

    target.manager_id = manager_id
    await db.commit()
    await db.refresh(target)
    return target


async def _hand_over_management(db: AsyncSession, target: User) -> None:
    """Move a departing manager's reports and unfinished reviews up to their own manager.

    Without this, the reports keep pointing at someone who can no longer log in — so future
    cycles silently generate no manager evaluation for them — and any review already assigned
    to the departing manager could never be submitted.
    """
    reports = await list_direct_reports(db, target.id)
    open_evaluations = await list_open_manager_evaluations_for_evaluator(db, target.id)
    if not reports and not open_evaluations:
        return

    if target.manager_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This user still manages people and has no manager of their own to hand that over to. "
            "Give them a manager, or reassign their reports, before deactivating.",
        )

    skip_level = await get_user_by_id(db, target.manager_id)
    if skip_level is None or not skip_level.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This user's own manager is inactive, so there's nobody to hand their reports to. "
            "Reassign the reports before deactivating.",
        )
    # A reporting loop would otherwise make someone their own manager or their own reviewer.
    if skip_level.manager_id == target.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This user and their manager report to each other — fix the reporting loop first.",
        )

    for report in reports:
        report.manager_id = skip_level.id
    for evaluation in open_evaluations:
        evaluation.evaluator_id = skip_level.id


async def _return_tasks_to_pool(db: AsyncSession, target: User) -> None:
    """Drop a departing user's in-flight tasks back into the shared pool.

    Unlike a manager review, a task isn't owed by anyone specific — whoever's free
    can pick it up next, so there's no handover target to find and no error case.
    Done/cancelled tasks are left alone: they're history, and Phase 2 reads them for
    evaluation evidence.
    """
    for task in await list_open_tasks_for_assignee(db, target.id):
        task.assignee_id = None
        task.status = TaskStatus.TODO
        task.claimed_at = None


async def deactivate_user(db: AsyncSession, actor: User, target_user_id: uuid.UUID) -> User:
    target = await _get_target_in_company(db, actor, target_user_id)

    if target.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")
    # HR manages the rank-and-file but not the company's admins.
    if actor.role == UserRole.HR and target.role == UserRole.COMPANY_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "HR cannot deactivate a company admin")

    # Reassigns in the same transaction as the deactivation, so we never leave reports
    # or reviews pointing at a user who can't log in.
    await _hand_over_management(db, target)
    await _return_tasks_to_pool(db, target)

    target.is_active = False
    await db.commit()
    await db.refresh(target)
    return target


async def reactivate_user(db: AsyncSession, actor: User, target_user_id: uuid.UUID) -> User:
    target = await _get_target_in_company(db, actor, target_user_id)

    # Mirrors deactivate_user: without this, HR could undo a company admin's
    # deactivation of a peer admin — a boundary HR can't cross in the other direction.
    if actor.role == UserRole.HR and target.role == UserRole.COMPANY_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "HR cannot reactivate a company admin")

    target.is_active = True
    await db.commit()
    await db.refresh(target)
    return target
