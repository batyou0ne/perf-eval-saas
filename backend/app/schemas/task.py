import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date | None = None
    # Absent or null means the task goes into the shared pool.
    assignee_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    status: TaskStatus | None = None


class TaskAssign(BaseModel):
    assignee_id: uuid.UUID


class TaskEvidence(BaseModel):
    """A finished task as it appears on an evaluation form — just enough to cite as evidence."""

    id: uuid.UUID
    title: str
    completed_at: datetime


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    created_by_id: uuid.UUID
    created_by_name: str
    assignee_id: uuid.UUID | None
    assignee_name: str | None
    status: TaskStatus
    due_date: date | None
    claimed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
