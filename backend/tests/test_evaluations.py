"""Evaluation submission rules and the who-can-see-what matrix."""

from datetime import datetime, timezone

import pytest

from tests.factories import build_responses, find_evaluation, make_task, make_user, submit_evaluation
from app.models import TaskStatus, UserRole

CYCLES = "/api/v1/cycles"
EVALUATIONS = "/api/v1/evaluations"


@pytest.fixture
async def active_cycle(client, as_user, company_admin, manager, employee, cycle):
    """An activated cycle, so self/manager evaluations exist for the fixture users."""
    as_user(company_admin)
    await client.post(f"{CYCLES}/{cycle.id}/activate")
    return cycle


@pytest.fixture
async def employee_self_eval(client, as_user, employee, active_cycle):
    as_user(employee)
    return await find_evaluation(client, cycle_id=active_cycle.id, subject_id=employee.id, eval_type="self")


@pytest.fixture
async def manager_eval_of_employee(client, as_user, manager, employee, active_cycle):
    as_user(manager)
    return await find_evaluation(client, cycle_id=active_cycle.id, subject_id=employee.id, eval_type="manager")


async def test_my_evaluations_lists_own_self_and_reports(client, as_user, manager, employee, active_cycle):
    as_user(manager)

    listing = (await client.get(f"{EVALUATIONS}/me")).json()["items"]

    kinds = {(e["type"], e["subject_id"]) for e in listing}
    assert ("self", str(manager.id)) in kinds
    assert ("manager", str(employee.id)) in kinds
    assert all(e["evaluator_id"] == str(manager.id) for e in listing)


async def test_my_evaluations_reports_evaluator_for_records_where_user_is_subject(
    client, as_user, manager, employee, active_cycle
):
    """A manager-eval of the employee must carry the manager's evaluator_id, not the employee's own id."""
    as_user(employee)

    listing = (await client.get(f"{EVALUATIONS}/me")).json()["items"]

    manager_eval = next(e for e in listing if e["type"] == "manager" and e["subject_id"] == str(employee.id))
    assert manager_eval["evaluator_id"] == str(manager.id)
    assert manager_eval["evaluator_name"] == manager.full_name


# --- pagination ----------------------------------------------------------------


async def test_my_evaluations_is_paginated(client, as_user, manager, employee, active_cycle):
    """The manager has two evaluations (self + report on employee); page_size=1 should split them across pages."""
    as_user(manager)

    page_one = (await client.get(f"{EVALUATIONS}/me", params={"page": 1, "page_size": 1})).json()
    page_two = (await client.get(f"{EVALUATIONS}/me", params={"page": 2, "page_size": 1})).json()

    assert page_one["total"] == 2
    assert page_one["page"] == 1
    assert page_one["page_size"] == 1
    assert len(page_one["items"]) == 1

    assert page_two["page"] == 2
    assert len(page_two["items"]) == 1
    assert page_one["items"][0]["id"] != page_two["items"][0]["id"]


async def test_my_evaluations_page_past_the_end_is_empty(client, as_user, manager, active_cycle):
    as_user(manager)

    response = await client.get(f"{EVALUATIONS}/me", params={"page": 5, "page_size": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 2


async def test_my_evaluations_rejects_invalid_page_params(client, as_user, manager, active_cycle):
    as_user(manager)

    assert (await client.get(f"{EVALUATIONS}/me", params={"page": 0})).status_code == 422
    assert (await client.get(f"{EVALUATIONS}/me", params={"page_size": 0})).status_code == 422
    assert (await client.get(f"{EVALUATIONS}/me", params={"page_size": 101})).status_code == 422


async def test_submitting_stores_and_returns_the_responses(client, as_user, employee, employee_self_eval):
    """Regression guard: the submit response once came back with an empty responses list."""
    as_user(employee)

    response = await submit_evaluation(client, employee_self_eval["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert len(body["responses"]) == len(body["questions"])
    assert all(r["rating_value"] is not None or r["text_value"] for r in body["responses"])


async def test_cannot_submit_someone_elses_evaluation(client, as_user, employee, manager, employee_self_eval):
    # Build a valid body as the employee, who is allowed to read the questions...
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    body = build_responses(detail)

    # ...then try to submit it as the manager, who is not the assigned evaluator.
    as_user(manager)
    response = await client.post(f"{EVALUATIONS}/{employee_self_eval['id']}/submit", json=body)

    assert response.status_code == 403


async def test_cannot_submit_twice(client, as_user, employee, employee_self_eval):
    as_user(employee)

    assert (await submit_evaluation(client, employee_self_eval["id"])).status_code == 200
    assert (await submit_evaluation(client, employee_self_eval["id"])).status_code == 400


async def test_every_question_must_be_answered(client, as_user, employee, employee_self_eval):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    only_one = detail["questions"][:1]

    response = await client.post(
        f"{EVALUATIONS}/{employee_self_eval['id']}/submit",
        json={"responses": [{"question_id": only_one[0]["id"], "rating_value": 3}]},
    )

    assert response.status_code == 400


@pytest.mark.parametrize("bad_rating", [0, 6, -1])
async def test_ratings_outside_one_to_five_are_rejected(client, as_user, employee, employee_self_eval, bad_rating):
    as_user(employee)

    response = await submit_evaluation(client, employee_self_eval["id"], rating=bad_rating)

    assert response.status_code == 400


async def test_text_questions_require_a_non_empty_answer(client, as_user, employee, employee_self_eval):
    as_user(employee)

    response = await submit_evaluation(client, employee_self_eval["id"], text="")

    assert response.status_code == 400


# --- visibility matrix -------------------------------------------------------


async def test_evaluator_can_view_their_own_unsubmitted_evaluation(client, as_user, manager, manager_eval_of_employee):
    as_user(manager)

    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 200


async def test_subject_cannot_view_a_manager_evaluation_before_submission(
    client, as_user, employee, manager_eval_of_employee
):
    as_user(employee)

    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 403


async def test_subject_can_view_a_manager_evaluation_once_submitted(
    client, as_user, employee, manager, manager_eval_of_employee
):
    as_user(manager)
    assert (await submit_evaluation(client, manager_eval_of_employee["id"])).status_code == 200

    as_user(employee)
    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 200


async def test_company_admin_can_view_a_submitted_evaluation_in_their_company(
    client, as_user, company_admin, manager, manager_eval_of_employee
):
    as_user(manager)
    await submit_evaluation(client, manager_eval_of_employee["id"])

    as_user(company_admin)
    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 200


async def test_company_admin_cannot_view_an_unsubmitted_evaluation(
    client, as_user, company_admin, manager_eval_of_employee
):
    as_user(company_admin)

    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 403


async def test_another_companys_admin_cannot_view_a_submitted_evaluation(
    client, as_user, other_company_admin, manager, manager_eval_of_employee
):
    """The tenant boundary must hold even for a submitted evaluation."""
    as_user(manager)
    await submit_evaluation(client, manager_eval_of_employee["id"])

    as_user(other_company_admin)
    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 403


async def test_an_unrelated_colleague_cannot_view_an_evaluation(
    client, as_user, db_session, company, manager, manager_eval_of_employee
):
    as_user(manager)
    await submit_evaluation(client, manager_eval_of_employee["id"])

    bystander = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(bystander)
    response = await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")

    assert response.status_code == 403


# --- draft save ---------------------------------------------------------------


async def test_draft_save_accepts_a_partial_answer_and_moves_to_in_progress(
    client, as_user, employee, employee_self_eval
):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    only_one = detail["questions"][:1]

    response = await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": only_one[0]["id"], "rating_value": 3}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert len(body["responses"]) == 1


async def test_draft_saving_the_same_question_twice_does_not_duplicate_the_row(
    client, as_user, employee, employee_self_eval
):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    question_id = detail["questions"][0]["id"]

    await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": question_id, "rating_value": 2}]},
    )
    response = await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": question_id, "rating_value": 5}]},
    )

    assert response.status_code == 200
    body = response.json()
    matching = [r for r in body["responses"] if r["question_id"] == question_id]
    assert len(matching) == 1
    assert matching[0]["rating_value"] == 5


async def test_cannot_draft_save_a_submitted_evaluation(client, as_user, employee, employee_self_eval):
    as_user(employee)
    assert (await submit_evaluation(client, employee_self_eval["id"])).status_code == 200

    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    response = await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": detail["questions"][0]["id"], "rating_value": 4}]},
    )

    assert response.status_code == 400


async def test_only_the_assigned_evaluator_can_draft_save(client, as_user, employee, manager, employee_self_eval):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    question_id = detail["questions"][0]["id"]

    as_user(manager)
    response = await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": question_id, "rating_value": 4}]},
    )

    assert response.status_code == 403


async def test_draft_saving_then_submitting_keeps_one_response_per_question(
    client, as_user, employee, employee_self_eval
):
    """Draft-save and submit share the same upsert, so a drafted answer must be updated, not duplicated."""
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    rating_question = next(q for q in detail["questions"] if q["type"] == "rating")

    await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": rating_question["id"], "rating_value": 2}]},
    )
    response = await submit_evaluation(client, employee_self_eval["id"], rating=5)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert len(body["responses"]) == len(body["questions"])
    drafted = [r for r in body["responses"] if r["question_id"] == rating_question["id"]]
    assert len(drafted) == 1
    assert drafted[0]["rating_value"] == 5


@pytest.mark.parametrize("bad_rating", [0, 6, -1])
async def test_draft_save_rejects_a_rating_outside_one_to_five(client, as_user, employee, employee_self_eval, bad_rating):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    rating_question = next(q for q in detail["questions"] if q["type"] == "rating")

    response = await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": rating_question["id"], "rating_value": bad_rating}]},
    )

    assert response.status_code == 400


async def test_cannot_draft_save_into_a_closed_cycle(
    client, as_user, company_admin, employee, active_cycle, employee_self_eval
):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    question_id = detail["questions"][0]["id"]

    as_user(company_admin)
    assert (await client.post(f"{CYCLES}/{active_cycle.id}/close")).status_code == 200

    as_user(employee)
    response = await client.patch(
        f"{EVALUATIONS}/{employee_self_eval['id']}",
        json={"responses": [{"question_id": question_id, "rating_value": 4}]},
    )

    assert response.status_code == 400


async def test_cannot_submit_into_a_closed_cycle(
    client, as_user, company_admin, employee, active_cycle, employee_self_eval
):
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()
    body = build_responses(detail)

    as_user(company_admin)
    assert (await client.post(f"{CYCLES}/{active_cycle.id}/close")).status_code == 200

    as_user(employee)
    response = await client.post(f"{EVALUATIONS}/{employee_self_eval['id']}/submit", json=body)

    assert response.status_code == 400


# --- completed tasks as evidence ---------------------------------------------


async def test_evaluation_detail_includes_only_the_subjects_completed_tasks_in_the_cycle_window(
    client, as_user, db_session, company, employee, manager, active_cycle, employee_self_eval
):
    in_window = await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=employee.id,
        title="Shipped the onboarding flow",
        completed_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
    )
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=employee.id,
        title="Finished before the cycle started",
        completed_at=datetime(2025, 12, 20, tzinfo=timezone.utc),
    )
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=employee.id,
        title="Finished after the cycle ended",
        completed_at=datetime(2026, 4, 5, tzinfo=timezone.utc),
    )
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=manager.id,
        created_by_id=manager.id,
        title="Someone else's completed task",
        completed_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
    )
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=employee.id,
        title="Still in progress",
        status=TaskStatus.IN_PROGRESS,
        completed_at=None,
    )
    as_user(employee)

    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()

    titles = {t["title"] for t in detail["completed_tasks"]}
    assert titles == {"Shipped the onboarding flow"}
    assert detail["completed_tasks"][0]["id"] == str(in_window.id)


async def test_manager_sees_the_same_completed_tasks_when_evaluating(
    client, as_user, db_session, company, employee, manager, active_cycle, manager_eval_of_employee
):
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=employee.id,
        title="Migrated the auth service",
        completed_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    as_user(manager)

    detail = (await client.get(f"{EVALUATIONS}/{manager_eval_of_employee['id']}")).json()

    assert {t["title"] for t in detail["completed_tasks"]} == {"Migrated the auth service"}


async def test_submitting_returns_completed_tasks_in_the_response(
    client, as_user, db_session, company, employee, active_cycle, employee_self_eval
):
    await make_task(
        db_session,
        company_id=company.id,
        assignee_id=employee.id,
        created_by_id=employee.id,
        title="Wrote the onboarding doc",
        completed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    as_user(employee)
    detail = (await client.get(f"{EVALUATIONS}/{employee_self_eval['id']}")).json()

    response = await client.post(
        f"{EVALUATIONS}/{employee_self_eval['id']}/submit", json=build_responses(detail)
    )

    assert {t["title"] for t in response.json()["completed_tasks"]} == {"Wrote the onboarding doc"}


# --- dashboard-facing filters -------------------------------------------------


async def test_evaluation_summary_includes_the_cycles_end_date(client, as_user, manager, active_cycle):
    as_user(manager)

    listing = (await client.get(f"{EVALUATIONS}/me")).json()["items"]

    assert all(e["cycle_end_date"] == str(active_cycle.end_date) for e in listing)


async def test_pending_filter_returns_only_unsubmitted_work_owed_as_evaluator(
    client, as_user, manager, employee, active_cycle
):
    as_user(manager)

    pending = (await client.get(f"{EVALUATIONS}/me", params={"pending": "true"})).json()

    # The manager owes their own self-eval and the employee's manager-eval — both unsubmitted.
    assert pending["total"] == 2
    kinds = {(e["type"], e["subject_id"]) for e in pending["items"]}
    assert ("self", str(manager.id)) in kinds
    assert ("manager", str(employee.id)) in kinds


async def test_pending_filter_excludes_submitted_work(client, as_user, manager, employee_self_eval, employee):
    as_user(employee)
    await submit_evaluation(client, employee_self_eval["id"])

    pending = (await client.get(f"{EVALUATIONS}/me", params={"pending": "true"})).json()

    assert pending["total"] == 0


async def test_pending_filter_excludes_evaluations_where_user_is_only_the_subject(
    client, as_user, employee, manager_eval_of_employee
):
    """The employee is the subject of their manager-eval, not the evaluator — it's not their pending work."""
    as_user(employee)

    pending = (await client.get(f"{EVALUATIONS}/me", params={"pending": "true"})).json()

    assert all(e["id"] != manager_eval_of_employee["id"] for e in pending["items"])
