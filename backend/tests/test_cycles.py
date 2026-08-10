"""Review cycles: who can manage them, and the evaluation fan-out on activation."""

from sqlalchemy import select

from app.models import Evaluation, EvaluationType, Question, UserRole
from tests.factories import make_user

CYCLES = "/api/v1/cycles"

NEW_CYCLE = {
    "name": "Q2 2026 Review",
    "start_date": "2026-04-01",
    "end_date": "2026-06-30",
    "questions": [
        {"text": "Rate overall performance", "type": "rating", "order": 0},
        {"text": "What could improve?", "type": "text", "order": 1},
    ],
}

UPDATED_CYCLE = {
    "name": "Q2 2026 Review (revised)",
    "start_date": "2026-04-15",
    "end_date": "2026-07-15",
    "questions": [
        {"text": "Rate teamwork", "type": "rating", "order": 0},
    ],
}


async def test_company_admin_can_create_a_cycle_with_questions(client, as_user, company_admin):
    as_user(company_admin)

    response = await client.post(CYCLES, json=NEW_CYCLE)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert [q["text"] for q in body["questions"]] == [q["text"] for q in NEW_CYCLE["questions"]]


async def test_hr_can_create_a_cycle(client, as_user, hr_user):
    as_user(hr_user)
    assert (await client.post(CYCLES, json=NEW_CYCLE)).status_code == 200


async def test_employee_cannot_create_a_cycle(client, as_user, employee):
    as_user(employee)
    assert (await client.post(CYCLES, json=NEW_CYCLE)).status_code == 403


async def test_manager_cannot_create_a_cycle(client, as_user, manager):
    as_user(manager)
    assert (await client.post(CYCLES, json=NEW_CYCLE)).status_code == 403


async def test_cycle_list_is_scoped_to_the_callers_company(
    client, as_user, company_admin, other_company_admin, cycle
):
    as_user(company_admin)
    assert [c["id"] for c in (await client.get(CYCLES)).json()] == [str(cycle.id)]

    as_user(other_company_admin)
    assert (await client.get(CYCLES)).json() == []


async def test_cannot_read_another_companys_cycle(client, as_user, other_company_admin, cycle):
    as_user(other_company_admin)
    assert (await client.get(f"{CYCLES}/{cycle.id}")).status_code == 404


async def test_activation_generates_self_and_manager_evaluations(
    client, as_user, db_session, company_admin, manager, employee, cycle
):
    as_user(company_admin)

    response = await client.post(f"{CYCLES}/{cycle.id}/activate")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    evaluations = (await db_session.execute(select(Evaluation).where(Evaluation.cycle_id == cycle.id))).scalars().all()

    self_evals = {e.subject_id for e in evaluations if e.type == EvaluationType.SELF}
    manager_evals = {(e.subject_id, e.evaluator_id) for e in evaluations if e.type == EvaluationType.MANAGER}

    # Everyone in the company self-evaluates...
    assert self_evals == {company_admin.id, manager.id, employee.id}
    # ...but only the employee has a manager, so that's the only manager evaluation.
    assert manager_evals == {(employee.id, manager.id)}


async def test_activation_does_not_review_a_manager_even_if_they_have_a_manager_id(
    client, as_user, db_session, company, company_admin, manager, cycle
):
    """Only employees get reviewed — a non-employee with manager_id set still shouldn't get a manager-eval."""
    reviewed_manager = await make_user(
        db_session, role=UserRole.MANAGER, company_id=company.id, manager_id=manager.id
    )
    as_user(company_admin)

    await client.post(f"{CYCLES}/{cycle.id}/activate")

    evaluations = (await db_session.execute(select(Evaluation).where(Evaluation.cycle_id == cycle.id))).scalars().all()
    manager_evals = {e.subject_id for e in evaluations if e.type == EvaluationType.MANAGER}

    assert reviewed_manager.id not in manager_evals


async def test_activation_skips_inactive_users(client, as_user, db_session, company, company_admin, cycle):
    await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, is_active=False)
    as_user(company_admin)

    await client.post(f"{CYCLES}/{cycle.id}/activate")

    evaluations = (await db_session.execute(select(Evaluation).where(Evaluation.cycle_id == cycle.id))).scalars().all()
    assert {e.subject_id for e in evaluations} == {company_admin.id}


async def test_a_cycle_cannot_be_activated_twice(client, as_user, company_admin, cycle):
    as_user(company_admin)

    assert (await client.post(f"{CYCLES}/{cycle.id}/activate")).status_code == 200
    assert (await client.post(f"{CYCLES}/{cycle.id}/activate")).status_code == 400


async def test_employee_cannot_activate_a_cycle(client, as_user, employee, cycle):
    as_user(employee)
    assert (await client.post(f"{CYCLES}/{cycle.id}/activate")).status_code == 403


async def test_cannot_activate_another_companys_cycle(client, as_user, other_company_admin, cycle):
    as_user(other_company_admin)
    assert (await client.post(f"{CYCLES}/{cycle.id}/activate")).status_code == 404


async def test_company_admin_can_edit_a_draft_cycle(client, as_user, company_admin, cycle):
    as_user(company_admin)

    response = await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == UPDATED_CYCLE["name"]
    assert body["start_date"] == UPDATED_CYCLE["start_date"]
    assert body["end_date"] == UPDATED_CYCLE["end_date"]
    assert [q["text"] for q in body["questions"]] == ["Rate teamwork"]


async def test_hr_can_edit_a_draft_cycle(client, as_user, hr_user, cycle):
    as_user(hr_user)
    assert (await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)).status_code == 200


async def test_employee_cannot_edit_a_cycle(client, as_user, employee, cycle):
    as_user(employee)
    assert (await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)).status_code == 403


async def test_manager_cannot_edit_a_cycle(client, as_user, manager, cycle):
    as_user(manager)
    assert (await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)).status_code == 403


async def test_cannot_edit_another_companys_cycle(client, as_user, other_company_admin, cycle):
    as_user(other_company_admin)
    assert (await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)).status_code == 404


async def test_cannot_edit_an_active_cycle(client, as_user, company_admin, cycle):
    as_user(company_admin)
    await client.post(f"{CYCLES}/{cycle.id}/activate")

    response = await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)

    assert response.status_code == 400


async def test_editing_a_cycle_fully_replaces_its_questions(client, as_user, db_session, company_admin, cycle):
    original_ids = {
        str(q.id)
        for q in (await db_session.execute(select(Question).where(Question.cycle_id == cycle.id))).scalars().all()
    }
    as_user(company_admin)

    response = await client.patch(f"{CYCLES}/{cycle.id}", json=UPDATED_CYCLE)

    body = response.json()
    new_ids = {q["id"] for q in body["questions"]}
    assert len(body["questions"]) == 1
    assert new_ids.isdisjoint(original_ids)


async def test_cannot_create_a_cycle_without_questions(client, as_user, company_admin):
    """A question-less cycle would produce evaluations that are complete on arrival."""
    as_user(company_admin)

    response = await client.post(CYCLES, json={**NEW_CYCLE, "questions": []})

    assert response.status_code == 422


async def test_cannot_edit_a_cycle_down_to_zero_questions(client, as_user, company_admin, cycle):
    as_user(company_admin)

    response = await client.patch(f"{CYCLES}/{cycle.id}", json={**UPDATED_CYCLE, "questions": []})

    assert response.status_code == 422


async def test_activation_skips_the_manager_evaluation_when_the_manager_is_inactive(
    client, as_user, db_session, company, company_admin, cycle
):
    """An inactive manager can't log in, so the evaluation would be unsubmittable forever."""
    inactive_manager = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, is_active=False)
    reportee = await make_user(
        db_session, role=UserRole.EMPLOYEE, company_id=company.id, manager_id=inactive_manager.id
    )
    as_user(company_admin)

    await client.post(f"{CYCLES}/{cycle.id}/activate")

    evaluations = (await db_session.execute(select(Evaluation).where(Evaluation.cycle_id == cycle.id))).scalars().all()
    assert reportee.id in {e.subject_id for e in evaluations if e.type == EvaluationType.SELF}
    assert reportee.id not in {e.subject_id for e in evaluations if e.type == EvaluationType.MANAGER}


async def test_company_admin_can_close_an_active_cycle(client, as_user, company_admin, cycle):
    as_user(company_admin)
    await client.post(f"{CYCLES}/{cycle.id}/activate")

    response = await client.post(f"{CYCLES}/{cycle.id}/close")

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


async def test_cannot_close_a_draft_cycle(client, as_user, company_admin, cycle):
    as_user(company_admin)
    assert (await client.post(f"{CYCLES}/{cycle.id}/close")).status_code == 400


async def test_a_cycle_cannot_be_closed_twice(client, as_user, company_admin, cycle):
    as_user(company_admin)
    await client.post(f"{CYCLES}/{cycle.id}/activate")

    assert (await client.post(f"{CYCLES}/{cycle.id}/close")).status_code == 200
    assert (await client.post(f"{CYCLES}/{cycle.id}/close")).status_code == 400


async def test_employee_cannot_close_a_cycle(client, as_user, employee, cycle):
    as_user(employee)
    assert (await client.post(f"{CYCLES}/{cycle.id}/close")).status_code == 403


async def test_cannot_close_another_companys_cycle(client, as_user, other_company_admin, cycle):
    as_user(other_company_admin)
    assert (await client.post(f"{CYCLES}/{cycle.id}/close")).status_code == 404
