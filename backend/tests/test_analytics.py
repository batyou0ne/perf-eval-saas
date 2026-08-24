"""GET /analytics/overview: the company-wide figures behind the HR dashboard charts."""

from app.models import TaskStatus, UserRole
from tests.factories import find_evaluation, make_task, make_user, submit_evaluation

OVERVIEW = "/api/v1/analytics/overview"
CYCLES = "/api/v1/cycles"


async def _activate(client, as_user, company_admin, cycle):
    as_user(company_admin)
    assert (await client.post(f"{CYCLES}/{cycle.id}/activate")).status_code == 200


async def test_company_admin_gets_the_full_shape(client, as_user, company_admin):
    as_user(company_admin)
    response = await client.get(OVERVIEW)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"task_status_counts", "cycle_completion_rates"}
    # All four statuses are present even with no tasks at all, so the chart never has
    # to guess at a missing slice.
    assert body["task_status_counts"] == {"todo": 0, "in_progress": 0, "done": 0, "cancelled": 0}
    assert body["cycle_completion_rates"] == []


async def test_hr_can_view_the_overview(client, as_user, hr_user):
    as_user(hr_user)
    assert (await client.get(OVERVIEW)).status_code == 200


async def test_employee_cannot_view_the_overview(client, as_user, employee):
    as_user(employee)
    assert (await client.get(OVERVIEW)).status_code == 403


async def test_manager_cannot_view_the_overview(client, as_user, manager):
    as_user(manager)
    assert (await client.get(OVERVIEW)).status_code == 403


async def test_super_admin_cannot_view_the_overview(client, as_user, super_admin):
    as_user(super_admin)
    assert (await client.get(OVERVIEW)).status_code == 403


async def test_task_status_counts_match_the_task_list(client, as_user, db_session, company, company_admin, employee):
    for status, count in ((TaskStatus.TODO, 2), (TaskStatus.IN_PROGRESS, 1), (TaskStatus.DONE, 3), (TaskStatus.CANCELLED, 1)):
        for i in range(count):
            await make_task(
                db_session,
                company_id=company.id,
                assignee_id=employee.id,
                created_by_id=company_admin.id,
                title=f"{status.value} task {i}",
                status=status,
            )

    as_user(company_admin)
    counts = (await client.get(OVERVIEW)).json()["task_status_counts"]

    assert counts == {"todo": 2, "in_progress": 1, "done": 3, "cancelled": 1}
    # The same seven tasks the paginated list reports, split four ways.
    listing = (await client.get("/api/v1/tasks", params={"scope": "all", "page_size": 100})).json()
    assert sum(counts.values()) == listing["total"] == 7


async def test_counts_exclude_another_companys_tasks(
    client, as_user, db_session, company, other_company, company_admin, other_company_admin, employee
):
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=company_admin.id,
        status=TaskStatus.DONE,
    )
    other_employee = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=other_company.id)
    await make_task(
        db_session,
        company_id=other_company.id,
        assignee_id=other_employee.id,
        created_by_id=other_company_admin.id,
        status=TaskStatus.DONE,
    )

    as_user(company_admin)
    assert (await client.get(OVERVIEW)).json()["task_status_counts"]["done"] == 1


async def test_completion_rates_reflect_submitted_evaluations(
    client, as_user, company_admin, manager, employee, cycle
):
    await _activate(client, as_user, company_admin, cycle)

    # Three subjects owe a self-evaluation; only the employee has a manager, so there
    # is exactly one manager evaluation to submit.
    as_user(employee)
    self_eval = await find_evaluation(client, cycle_id=cycle.id, subject_id=employee.id, eval_type="self")
    assert (await submit_evaluation(client, self_eval["id"])).status_code == 200

    as_user(manager)
    manager_eval = await find_evaluation(client, cycle_id=cycle.id, subject_id=employee.id, eval_type="manager")
    assert (await submit_evaluation(client, manager_eval["id"])).status_code == 200

    as_user(company_admin)
    rates = (await client.get(OVERVIEW)).json()["cycle_completion_rates"]

    assert rates == [{"cycle_name": cycle.name, "self_pct": 33, "manager_pct": 100}]


async def test_manager_pct_is_null_when_no_manager_evaluations_exist(
    client, as_user, db_session, company, company_admin, cycle
):
    """A company where nobody reports to anyone owes no manager evaluations.

    That has to read as "not applicable", not as 0% — otherwise the chart shows work
    outstanding that was never assigned.
    """
    await _activate(client, as_user, company_admin, cycle)

    as_user(company_admin)
    rates = (await client.get(OVERVIEW)).json()["cycle_completion_rates"]

    assert len(rates) == 1
    assert rates[0]["manager_pct"] is None
    assert rates[0]["self_pct"] == 0


async def test_cycles_with_no_evaluations_are_omitted(client, as_user, company_admin, cycle):
    """A draft cycle has never generated evaluations, so it has no rate to plot."""
    as_user(company_admin)
    assert (await client.get(OVERVIEW)).json()["cycle_completion_rates"] == []


async def test_completion_rates_exclude_another_companys_cycles(
    client, as_user, company_admin, other_company_admin, cycle
):
    await _activate(client, as_user, company_admin, cycle)

    as_user(other_company_admin)
    assert (await client.get(OVERVIEW)).json()["cycle_completion_rates"] == []
