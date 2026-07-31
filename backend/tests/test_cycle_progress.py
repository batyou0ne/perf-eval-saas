"""GET /cycles/{id}/progress: who has submitted their self and manager evaluations."""

from tests.factories import find_evaluation, submit_evaluation

CYCLES = "/api/v1/cycles"


async def _activate(client, as_user, company_admin, cycle):
    as_user(company_admin)
    response = await client.post(f"{CYCLES}/{cycle.id}/activate")
    assert response.status_code == 200


async def test_progress_before_any_submissions(client, as_user, company_admin, manager, employee, cycle):
    await _activate(client, as_user, company_admin, cycle)

    as_user(company_admin)
    body = (await client.get(f"{CYCLES}/{cycle.id}/progress")).json()

    assert body["self_total"] == 3
    assert body["self_submitted"] == 0
    # Only the employee has a manager, so that's the only manager evaluation.
    assert body["manager_total"] == 1
    assert body["manager_submitted"] == 0

    by_id = {s["subject_id"]: s for s in body["subjects"]}
    assert set(by_id) == {str(company_admin.id), str(manager.id), str(employee.id)}
    assert by_id[str(employee.id)]["manager_status"] == "not_started"
    assert by_id[str(company_admin.id)]["manager_status"] is None
    assert by_id[str(manager.id)]["manager_status"] is None


async def test_progress_reflects_submitted_evaluations(client, as_user, company_admin, manager, employee, cycle):
    await _activate(client, as_user, company_admin, cycle)

    as_user(employee)
    self_eval = await find_evaluation(client, cycle_id=cycle.id, subject_id=employee.id, eval_type="self")
    assert (await submit_evaluation(client, self_eval["id"])).status_code == 200

    as_user(manager)
    manager_eval = await find_evaluation(client, cycle_id=cycle.id, subject_id=employee.id, eval_type="manager")
    assert (await submit_evaluation(client, manager_eval["id"])).status_code == 200

    as_user(company_admin)
    body = (await client.get(f"{CYCLES}/{cycle.id}/progress")).json()

    assert body["self_submitted"] == 1
    assert body["manager_submitted"] == 1

    by_id = {s["subject_id"]: s for s in body["subjects"]}
    assert by_id[str(employee.id)]["self_status"] == "submitted"
    assert by_id[str(employee.id)]["manager_status"] == "submitted"
    assert by_id[str(manager.id)]["self_status"] == "not_started"


async def test_hr_can_view_progress(client, as_user, hr_user, company_admin, cycle):
    await _activate(client, as_user, company_admin, cycle)

    as_user(hr_user)
    assert (await client.get(f"{CYCLES}/{cycle.id}/progress")).status_code == 200


async def test_employee_cannot_view_progress(client, as_user, company_admin, employee, cycle):
    await _activate(client, as_user, company_admin, cycle)

    as_user(employee)
    assert (await client.get(f"{CYCLES}/{cycle.id}/progress")).status_code == 403


async def test_manager_cannot_view_progress(client, as_user, company_admin, manager, cycle):
    await _activate(client, as_user, company_admin, cycle)

    as_user(manager)
    assert (await client.get(f"{CYCLES}/{cycle.id}/progress")).status_code == 403


async def test_cannot_view_another_companys_progress(client, as_user, company_admin, other_company_admin, cycle):
    await _activate(client, as_user, company_admin, cycle)

    as_user(other_company_admin)
    assert (await client.get(f"{CYCLES}/{cycle.id}/progress")).status_code == 404
