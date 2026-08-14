import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.pagination import Page
from app.schemas.task import TaskAssign, TaskCreate, TaskRead, TaskUpdate
from app.services import task_service

router = APIRouter()


@router.post("/tasks", response_model=TaskRead)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return await task_service.create_task(db, current_user, body)


@router.get("/tasks", response_model=Page[TaskRead])
async def list_tasks(
    scope: str = Query(default="all", pattern="^(all|pool|mine)$"),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    open_only: bool = Query(default=False, description="Only todo/in_progress tasks"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[TaskRead]:
    return await task_service.list_company_tasks(
        db, current_user, scope, task_status, page, page_size, open_only=open_only
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return await task_service.get_task(db, current_user, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return await task_service.update_task(db, current_user, task_id, body)


@router.post("/tasks/{task_id}/claim", response_model=TaskRead)
async def claim_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return await task_service.claim_task(db, current_user, task_id)


@router.post("/tasks/{task_id}/release", response_model=TaskRead)
async def release_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return await task_service.release_task(db, current_user, task_id)


@router.post("/tasks/{task_id}/assign", response_model=TaskRead)
async def assign_task(
    task_id: uuid.UUID,
    body: TaskAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return await task_service.assign_task(db, current_user, task_id, body.assignee_id)
