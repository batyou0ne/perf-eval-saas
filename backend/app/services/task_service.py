import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.task import claim_task as claim_task_row
from app.crud.task import get_task_by_id, list_tasks
from app.crud.user import get_user_by_id, list_direct_reports
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.pagination import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

_MANAGER_ROLES = (UserRole.COMPANY_ADMIN, UserRole.HR)


def _require_company_scope(actor: User) -> None:
    # super_admin has no company_id — tasks are a per-company concern they sit outside of.
    if actor.company_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available to platform admins")


def _to_read(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        created_by_id=task.created_by_id,
        created_by_name=task.created_by.full_name,
        assignee_id=task.assignee_id,
        assignee_name=task.assignee.full_name if task.assignee else None,
        status=task.status,
        due_date=task.due_date,
        claimed_at=task.claimed_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
    )


async def _get_owned_task(db: AsyncSession, task_id: uuid.UUID, actor: User) -> Task:
    task = await get_task_by_id(db, task_id)
    if task is None or task.company_id != actor.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


async def _validate_assignee(db: AsyncSession, actor: User, assignee_id: uuid.UUID) -> User:
    """A caller may only hand work to themselves, a direct report (if manager), or —
    if HR/company admin — anyone active in the company."""
    if assignee_id == actor.id:
        return actor

    assignee = await get_user_by_id(db, assignee_id)
    if assignee is None or assignee.company_id != actor.company_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee must belong to the same company")
    if not assignee.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee must be an active user")

    if actor.role in _MANAGER_ROLES:
        return assignee

    if actor.role == UserRole.MANAGER:
        reports = await list_direct_reports(db, actor.id)
        if assignee_id not in {r.id for r in reports}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only assign tasks to your direct reports")
        return assignee

    raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only assign tasks to yourself")


def _can_manage(actor: User, task: Task) -> bool:
    """Whether `actor` can edit fields or change status on this (already-known-in-company) task."""
    if actor.role in _MANAGER_ROLES:
        return True
    if task.assignee_id == actor.id:
        return True
    # A creator can still edit their own submission while it's sitting unclaimed in the pool.
    if task.created_by_id == actor.id and task.assignee_id is None:
        return True
    return False


async def _can_manage_via_reports(db: AsyncSession, actor: User, task: Task) -> bool:
    if _can_manage(actor, task):
        return True
    if actor.role == UserRole.MANAGER and task.assignee_id is not None:
        reports = await list_direct_reports(db, actor.id)
        return task.assignee_id in {r.id for r in reports}
    return False


async def create_task(db: AsyncSession, actor: User, data: TaskCreate) -> TaskRead:
    _require_company_scope(actor)

    if data.assignee_id is not None:
        await _validate_assignee(db, actor, data.assignee_id)

    task = Task(
        company_id=actor.company_id,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
        created_by_id=actor.id,
        assignee_id=data.assignee_id,
        claimed_at=datetime.now(timezone.utc) if data.assignee_id is not None else None,
    )
    db.add(task)
    await db.commit()
    return _to_read(await get_task_by_id(db, task.id))


async def list_company_tasks(
    db: AsyncSession,
    actor: User,
    scope: str,
    status_filter: TaskStatus | None,
    page: int,
    page_size: int,
    open_only: bool = False,
) -> Page[TaskRead]:
    _require_company_scope(actor)

    tasks, total = await list_tasks(
        db,
        actor.company_id,
        scope=scope,
        user_id=actor.id,
        status=status_filter,
        open_only=open_only,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return Page(items=[_to_read(t) for t in tasks], total=total, page=page, page_size=page_size)


async def get_task(db: AsyncSession, actor: User, task_id: uuid.UUID) -> TaskRead:
    _require_company_scope(actor)
    task = await _get_owned_task(db, task_id, actor)
    return _to_read(task)


async def update_task(db: AsyncSession, actor: User, task_id: uuid.UUID, data: TaskUpdate) -> TaskRead:
    _require_company_scope(actor)
    task = await _get_owned_task(db, task_id, actor)

    if not await _can_manage_via_reports(db, actor, task):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to update this task")

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.due_date is not None:
        task.due_date = data.due_date

    if data.status is not None:
        _apply_status_change(task, data.status)

    await db.commit()
    return _to_read(await get_task_by_id(db, task.id))


def _apply_status_change(task: Task, new_status: TaskStatus) -> None:
    if new_status == TaskStatus.DONE and task.assignee_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An unclaimed task can't be marked done")

    if new_status == TaskStatus.DONE:
        task.completed_at = datetime.now(timezone.utc)
    elif task.status == TaskStatus.DONE:
        # Reopening a completed task — it's no longer complete, so the timestamp
        # that Phase 2's evaluation-window filter reads has to be cleared with it.
        task.completed_at = None

    task.status = new_status


async def claim_task(db: AsyncSession, actor: User, task_id: uuid.UUID) -> TaskRead:
    _require_company_scope(actor)
    task = await _get_owned_task(db, task_id, actor)

    if task.assignee_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This task has already been claimed")

    claimed = await claim_task_row(db, task_id, actor.id)
    if not claimed:
        # Someone else's claim landed between our read and our write.
        raise HTTPException(status.HTTP_409_CONFLICT, "This task was just claimed by someone else")

    await db.commit()
    return _to_read(await get_task_by_id(db, task_id))


async def release_task(db: AsyncSession, actor: User, task_id: uuid.UUID) -> TaskRead:
    _require_company_scope(actor)
    task = await _get_owned_task(db, task_id, actor)

    if task.assignee_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This task is already in the pool")
    if task.status not in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only an in-flight task can be released back to the pool")
    if not await _can_manage_via_reports(db, actor, task):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to release this task")

    task.assignee_id = None
    task.status = TaskStatus.TODO
    task.claimed_at = None

    await db.commit()
    return _to_read(await get_task_by_id(db, task_id))


async def assign_task(db: AsyncSession, actor: User, task_id: uuid.UUID, assignee_id: uuid.UUID) -> TaskRead:
    _require_company_scope(actor)
    task = await _get_owned_task(db, task_id, actor)

    if actor.role == UserRole.EMPLOYEE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Employees cannot assign tasks")

    if actor.role == UserRole.MANAGER and task.assignee_id is not None:
        # Reassigning someone else's task — only allowed if the current holder is a
        # direct report; otherwise a manager could pull work off an unrelated team.
        reports = await list_direct_reports(db, actor.id)
        if task.assignee_id not in {r.id for r in reports}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to reassign this task")

    await _validate_assignee(db, actor, assignee_id)

    task.assignee_id = assignee_id
    task.claimed_at = datetime.now(timezone.utc)
    if task.status == TaskStatus.DONE:
        task.completed_at = None
        task.status = TaskStatus.TODO

    await db.commit()
    return _to_read(await get_task_by_id(db, task_id))
