import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskStatus

_LOAD_OPTIONS = (selectinload(Task.created_by), selectinload(Task.assignee))


async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id).options(*_LOAD_OPTIONS))
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    scope: str,
    user_id: uuid.UUID,
    status: TaskStatus | None,
    open_only: bool = False,
    offset: int,
    limit: int,
) -> tuple[list[Task], int]:
    query = select(Task).where(Task.company_id == company_id)
    if scope == "pool":
        query = query.where(Task.assignee_id.is_(None))
    elif scope == "mine":
        query = query.where(Task.assignee_id == user_id)
    if status is not None:
        query = query.where(Task.status == status)
    # A dashboard widget's shape: "still in flight", regardless of the single-status filter above.
    if open_only:
        query = query.where(Task.status.in_((TaskStatus.TODO, TaskStatus.IN_PROGRESS)))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    result = await db.execute(
        query.options(*_LOAD_OPTIONS).order_by(Task.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def claim_task(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Atomically claim a pool task. Returns False if it was already taken by then.

    The WHERE clause is the whole point: it lets the database, not the app, decide
    who wins when two people claim the same task at once.
    """
    result = await db.execute(
        update(Task)
        .where(Task.id == task_id, Task.assignee_id.is_(None))
        .values(assignee_id=user_id, claimed_at=datetime.now(timezone.utc))
    )
    return result.rowcount > 0


async def list_open_tasks_for_assignee(db: AsyncSession, assignee_id: uuid.UUID) -> list[Task]:
    """Tasks still in flight for this user — what a deactivation has to release back to the pool."""
    result = await db.execute(
        select(Task).where(
            Task.assignee_id == assignee_id,
            Task.status.in_((TaskStatus.TODO, TaskStatus.IN_PROGRESS)),
        )
    )
    return list(result.scalars().all())


async def count_tasks_by_status(db: AsyncSession, company_id: uuid.UUID) -> dict[TaskStatus, int]:
    """How the company's tasks are split across the four statuses.

    Aggregated in the database rather than by paging the task list and counting in
    Python: the dashboard only needs four numbers, and a company with thousands of
    tasks shouldn't have to ship them all to produce them. Statuses with no rows are
    absent from the result — the caller fills the gaps, since a missing key and a
    zero mean the same thing here.
    """
    result = await db.execute(
        select(Task.status, func.count())
        .where(Task.company_id == company_id)
        .group_by(Task.status)
    )
    return {status: count for status, count in result.all()}


async def list_completed_tasks_for_subject_in_range(
    db: AsyncSession, company_id: uuid.UUID, subject_id: uuid.UUID, start_date: date, end_date: date
) -> list[Task]:
    """A person's finished work within a review cycle's window — the evidence an
    evaluation form and the AI summary draw on instead of relying on memory alone."""
    result = await db.execute(
        select(Task)
        .where(
            Task.company_id == company_id,
            Task.assignee_id == subject_id,
            Task.status == TaskStatus.DONE,
            Task.completed_at.is_not(None),
            func.date(Task.completed_at) >= start_date,
            func.date(Task.completed_at) <= end_date,
        )
        .order_by(Task.completed_at)
    )
    return list(result.scalars().all())
