from pydantic import BaseModel


class TaskStatusCounts(BaseModel):
    todo: int
    in_progress: int
    done: int
    cancelled: int


class CycleCompletionRate(BaseModel):
    cycle_name: str
    # None, not 0: a cycle where nobody has a manager owes no manager evaluations at all,
    # and reporting that as "0% complete" would read as work outstanding rather than
    # work that never existed.
    self_pct: int | None
    manager_pct: int | None


class AnalyticsOverview(BaseModel):
    task_status_counts: TaskStatusCounts
    cycle_completion_rates: list[CycleCompletionRate]
