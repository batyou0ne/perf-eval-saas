"""The shared task pool: creation, assignment, claiming, and the invariants around status."""

from app.models import UserRole
from tests.factories import make_user

TASKS = "/api/v1/tasks"


async def _create(client, **overrides):
    body = {"title": "Fix the API route mismatch", **overrides}
    return await client.post(TASKS, json=body)


# --- creation and assignment --------------------------------------------------


async def test_employee_can_drop_a_task_into_the_pool(client, as_user, employee):
    as_user(employee)

    response = await _create(client)

    assert response.status_code == 200
    body = response.json()
    assert body["assignee_id"] is None
    assert body["status"] == "todo"
    assert body["created_by_id"] == str(employee.id)


async def test_employee_cannot_assign_a_task_to_someone_else(client, as_user, employee, manager):
    as_user(employee)

    response = await _create(client, assignee_id=str(manager.id))

    assert response.status_code == 403


async def test_manager_can_assign_a_task_to_a_direct_report(client, as_user, manager, employee):
    as_user(manager)

    response = await _create(client, assignee_id=str(employee.id))

    assert response.status_code == 200
    body = response.json()
    assert body["assignee_id"] == str(employee.id)
    assert body["claimed_at"] is not None


async def test_manager_cannot_assign_a_task_to_a_non_report(client, as_user, db_session, company, manager):
    stranger = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(manager)

    response = await _create(client, assignee_id=str(stranger.id))

    assert response.status_code == 403


async def test_hr_can_assign_a_task_to_anyone_in_the_company(client, as_user, hr_user, employee):
    as_user(hr_user)

    response = await _create(client, assignee_id=str(employee.id))

    assert response.status_code == 200
    assert response.json()["assignee_id"] == str(employee.id)


# --- claiming --------------------------------------------------------------


async def test_claiming_a_pool_task_assigns_it_to_the_claimer(client, as_user, employee):
    as_user(employee)
    task_id = (await _create(client)).json()["id"]

    response = await client.post(f"{TASKS}/{task_id}/claim")

    assert response.status_code == 200
    body = response.json()
    assert body["assignee_id"] == str(employee.id)
    assert body["claimed_at"] is not None


async def test_claiming_an_already_claimed_task_conflicts(client, as_user, db_session, company, employee):
    as_user(employee)
    task_id = (await _create(client)).json()["id"]
    first = await client.post(f"{TASKS}/{task_id}/claim")
    assert first.status_code == 200

    other = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(other)
    second = await client.post(f"{TASKS}/{task_id}/claim")

    assert second.status_code == 409


async def test_releasing_a_claimed_task_returns_it_to_the_pool(client, as_user, employee):
    as_user(employee)
    task_id = (await _create(client)).json()["id"]
    await client.post(f"{TASKS}/{task_id}/claim")

    response = await client.post(f"{TASKS}/{task_id}/release")

    assert response.status_code == 200
    body = response.json()
    assert body["assignee_id"] is None
    assert body["status"] == "todo"
    assert body["claimed_at"] is None


async def test_unrelated_user_cannot_release_someone_elses_task(
    client, as_user, db_session, company, manager, employee
):
    as_user(manager)
    task_id = (await _create(client, assignee_id=str(employee.id))).json()["id"]

    stranger = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(stranger)
    response = await client.post(f"{TASKS}/{task_id}/release")

    assert response.status_code == 403


# --- status invariants -------------------------------------------------------


async def test_unclaimed_task_cannot_be_marked_done(client, as_user, employee):
    as_user(employee)
    task_id = (await _create(client)).json()["id"]

    response = await client.patch(f"{TASKS}/{task_id}", json={"status": "done"})

    assert response.status_code == 400


async def test_reopening_a_done_task_clears_completed_at(client, as_user, employee):
    as_user(employee)
    task_id = (await _create(client)).json()["id"]
    await client.post(f"{TASKS}/{task_id}/claim")
    done = await client.patch(f"{TASKS}/{task_id}", json={"status": "done"})
    assert done.json()["completed_at"] is not None

    reopened = await client.patch(f"{TASKS}/{task_id}", json={"status": "in_progress"})

    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None


async def test_unrelated_employee_cannot_change_task_status(client, as_user, db_session, company, manager, employee):
    as_user(manager)
    task_id = (await _create(client, assignee_id=str(employee.id))).json()["id"]

    stranger = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(stranger)
    response = await client.patch(f"{TASKS}/{task_id}", json={"status": "in_progress"})

    assert response.status_code == 403


# --- boundaries --------------------------------------------------------------


async def test_task_in_another_company_is_not_found(client, as_user, other_company_admin, company_admin):
    as_user(other_company_admin)
    task_id = (await _create(client)).json()["id"]

    as_user(company_admin)
    response = await client.get(f"{TASKS}/{task_id}")

    assert response.status_code == 404


async def test_super_admin_cannot_use_task_endpoints(client, as_user, super_admin):
    as_user(super_admin)

    response = await _create(client)

    assert response.status_code == 403


async def test_pool_scope_only_returns_unassigned_tasks(client, as_user, manager, employee):
    as_user(manager)
    await _create(client, title="Unassigned one")
    await _create(client, title="Assigned one", assignee_id=str(employee.id))

    response = await client.get(TASKS, params={"scope": "pool"})

    assert response.status_code == 200
    body = response.json()
    assert all(item["assignee_id"] is None for item in body["items"])
    assert any(item["title"] == "Unassigned one" for item in body["items"])
    assert not any(item["title"] == "Assigned one" for item in body["items"])


async def test_task_list_uses_the_pagination_envelope(client, as_user, employee):
    as_user(employee)
    await _create(client)

    response = await client.get(TASKS)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert body["total"] >= 1


# --- deactivation integration -------------------------------------------------


async def test_deactivating_a_user_returns_their_open_tasks_to_the_pool(
    client, as_user, company_admin, manager, employee
):
    as_user(manager)
    task_id = (await _create(client, assignee_id=str(employee.id))).json()["id"]

    as_user(company_admin)
    deactivate = await client.post(f"/api/v1/users/{employee.id}/deactivate")
    assert deactivate.status_code == 200

    task = (await client.get(f"{TASKS}/{task_id}")).json()
    assert task["assignee_id"] is None
    assert task["status"] == "todo"
    assert task["claimed_at"] is None


async def test_deactivating_a_user_leaves_their_completed_tasks_alone(
    client, as_user, company_admin, manager, employee
):
    as_user(manager)
    task_id = (await _create(client, assignee_id=str(employee.id))).json()["id"]

    as_user(employee)
    await client.patch(f"{TASKS}/{task_id}", json={"status": "done"})

    as_user(company_admin)
    await client.post(f"/api/v1/users/{employee.id}/deactivate")

    task = (await client.get(f"{TASKS}/{task_id}")).json()
    assert task["assignee_id"] == str(employee.id)
    assert task["status"] == "done"
