from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.evaluation import count_submissions_per_cycle
from app.crud.task import count_tasks_by_status
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.analytics import AnalyticsOverview, CycleCompletionRate, TaskStatusCounts


def _pct(submitted: int, total: int) -> int | None:
    """None when there was nothing to submit — see CycleCompletionRate.self_pct."""
    if total == 0:
        return None
    return round(submitted / total * 100)


async def get_overview(db: AsyncSession, actor: User) -> AnalyticsOverview:
    # super_admin has no company_id, and the role guard on the endpoint already keeps
    # them out; this is the belt-and-braces check so a None can never widen the scope
    # of the company-filtered queries below.
    if actor.company_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available to platform admins")

    counts = await count_tasks_by_status(db, actor.company_id)
    cycles = await count_submissions_per_cycle(db, actor.company_id)

    return AnalyticsOverview(
        task_status_counts=TaskStatusCounts(
            todo=counts.get(TaskStatus.TODO, 0),
            in_progress=counts.get(TaskStatus.IN_PROGRESS, 0),
            done=counts.get(TaskStatus.DONE, 0),
            cancelled=counts.get(TaskStatus.CANCELLED, 0),
        ),
        cycle_completion_rates=[
            CycleCompletionRate(
                cycle_name=row.name,
                self_pct=_pct(row.self_submitted, row.self_total),
                manager_pct=_pct(row.manager_submitted, row.manager_total),
            )
            for row in cycles
        ],
    )
