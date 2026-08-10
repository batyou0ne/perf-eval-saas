"""Admin self-service: deactivating and reactivating users."""

import uuid

from sqlalchemy import select

from app.models import Evaluation, EvaluationType, UserRole
from tests.factories import find_evaluation, make_user, submit_evaluation

USERS = "/api/v1/users"


async def test_company_admin_can_deactivate_an_employee(client, as_user, company_admin, employee):
    as_user(company_admin)

    response = await client.post(f"{USERS}/{employee.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_company_admin_can_reactivate_an_employee(client, as_user, db_session, company_admin, employee):
    as_user(company_admin)
    await client.post(f"{USERS}/{employee.id}/deactivate")

    response = await client.post(f"{USERS}/{employee.id}/reactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True


async def test_hr_can_deactivate_an_employee(client, as_user, hr_user, employee):
    as_user(hr_user)
    assert (await client.post(f"{USERS}/{employee.id}/deactivate")).status_code == 200


async def test_hr_cannot_deactivate_a_company_admin(client, as_user, hr_user, company_admin):
    as_user(hr_user)

    response = await client.post(f"{USERS}/{company_admin.id}/deactivate")

    assert response.status_code == 403


async def test_company_admin_can_deactivate_another_company_admin(client, as_user, db_session, company, company_admin):
    other_admin = await make_user(db_session, role=UserRole.COMPANY_ADMIN, company_id=company.id)
    as_user(company_admin)

    response = await client.post(f"{USERS}/{other_admin.id}/deactivate")

    assert response.status_code == 200


async def test_employee_cannot_deactivate_anyone(client, as_user, employee, manager):
    as_user(employee)
    assert (await client.post(f"{USERS}/{manager.id}/deactivate")).status_code == 403


async def test_manager_cannot_deactivate_anyone(client, as_user, manager, employee):
    as_user(manager)
    assert (await client.post(f"{USERS}/{employee.id}/deactivate")).status_code == 403


async def test_cannot_deactivate_a_user_in_another_company(client, as_user, other_company_admin, employee):
    as_user(other_company_admin)
    assert (await client.post(f"{USERS}/{employee.id}/deactivate")).status_code == 404


async def test_cannot_deactivate_own_account(client, as_user, company_admin):
    as_user(company_admin)
    assert (await client.post(f"{USERS}/{company_admin.id}/deactivate")).status_code == 400


async def test_deactivating_an_already_inactive_user_is_idempotent(client, as_user, db_session, company, company_admin):
    inactive = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, is_active=False)
    as_user(company_admin)

    response = await client.post(f"{USERS}/{inactive.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_a_deactivated_users_token_is_rejected_on_the_next_request(client, as_user, company_admin, employee):
    as_user(company_admin)
    await client.post(f"{USERS}/{employee.id}/deactivate")

    as_user(employee)
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_hr_cannot_reactivate_a_company_admin(client, as_user, db_session, company, hr_user):
    """Mirrors the deactivate rule — otherwise HR could undo an admin's decision about a peer admin."""
    inactive_admin = await make_user(
        db_session, role=UserRole.COMPANY_ADMIN, company_id=company.id, is_active=False
    )
    as_user(hr_user)

    response = await client.post(f"{USERS}/{inactive_admin.id}/reactivate")

    assert response.status_code == 403


async def test_cannot_reactivate_a_user_in_another_company(client, as_user, other_company_admin, employee):
    as_user(other_company_admin)
    assert (await client.post(f"{USERS}/{employee.id}/reactivate")).status_code == 404


async def test_company_admin_can_unassign_a_users_manager(client, as_user, company_admin, employee):
    as_user(company_admin)

    response = await client.post(f"{USERS}/{employee.id}/manager", json={"manager_id": None})

    assert response.status_code == 200
    assert response.json()["manager_id"] is None


async def test_cannot_assign_an_inactive_user_as_manager(client, as_user, db_session, company, company_admin, employee):
    """A deactivated manager can't log in, so their evaluation could never be completed."""
    inactive_manager = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, is_active=False)
    as_user(company_admin)

    response = await client.post(f"{USERS}/{employee.id}/manager", json={"manager_id": str(inactive_manager.id)})

    assert response.status_code == 400


# --- handover on deactivation -------------------------------------------------


async def test_deactivating_a_manager_hands_their_reports_to_the_skip_level(
    client, as_user, db_session, company, company_admin
):
    skip_level = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id)
    departing = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, manager_id=skip_level.id)
    report = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, manager_id=departing.id)
    as_user(company_admin)

    response = await client.post(f"{USERS}/{departing.id}/deactivate")

    assert response.status_code == 200
    await db_session.refresh(report)
    assert report.manager_id == skip_level.id


async def test_deactivating_a_manager_reassigns_their_unfinished_reviews(
    client, as_user, db_session, company, company_admin, cycle
):
    """The departing manager can't log in anymore, so the review has to move or it's stuck forever."""
    skip_level = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id)
    departing = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, manager_id=skip_level.id)
    report = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, manager_id=departing.id)
    as_user(company_admin)
    await client.post(f"/api/v1/cycles/{cycle.id}/activate")

    await client.post(f"{USERS}/{departing.id}/deactivate")

    manager_eval = (
        await db_session.execute(
            select(Evaluation).where(
                Evaluation.cycle_id == cycle.id,
                Evaluation.subject_id == report.id,
                Evaluation.type == EvaluationType.MANAGER,
            )
        )
    ).scalar_one()
    assert manager_eval.evaluator_id == skip_level.id


async def test_deactivation_leaves_already_submitted_reviews_alone(
    client, as_user, db_session, company, company_admin, cycle
):
    skip_level = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id)
    departing = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, manager_id=skip_level.id)
    report = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, manager_id=departing.id)
    as_user(company_admin)
    await client.post(f"/api/v1/cycles/{cycle.id}/activate")

    as_user(departing)
    manager_eval = await find_evaluation(client, cycle_id=cycle.id, subject_id=report.id, eval_type="manager")
    assert (await submit_evaluation(client, manager_eval["id"])).status_code == 200

    as_user(company_admin)
    assert (await client.post(f"{USERS}/{departing.id}/deactivate")).status_code == 200

    stored = (
        await db_session.execute(select(Evaluation).where(Evaluation.id == uuid.UUID(manager_eval["id"])))
    ).scalar_one()
    assert stored.evaluator_id == departing.id


async def test_cannot_deactivate_a_manager_with_no_one_to_hand_their_reports_to(
    client, as_user, company_admin, manager, employee
):
    """`manager` has a report but no manager of their own, so there's no skip-level."""
    as_user(company_admin)

    response = await client.post(f"{USERS}/{manager.id}/deactivate")

    assert response.status_code == 400


async def test_cannot_deactivate_a_manager_whose_own_manager_is_inactive(
    client, as_user, db_session, company, company_admin
):
    inactive_skip = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, is_active=False)
    departing = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, manager_id=inactive_skip.id)
    await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, manager_id=departing.id)
    as_user(company_admin)

    response = await client.post(f"{USERS}/{departing.id}/deactivate")

    assert response.status_code == 400


async def test_cannot_deactivate_into_a_reporting_loop(client, as_user, db_session, company, company_admin):
    """Two users managing each other would otherwise end up as their own manager."""
    departing = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id)
    looped = await make_user(db_session, role=UserRole.MANAGER, company_id=company.id, manager_id=departing.id)
    departing.manager_id = looped.id
    await db_session.flush()
    as_user(company_admin)

    response = await client.post(f"{USERS}/{departing.id}/deactivate")

    assert response.status_code == 400


async def test_an_employee_with_no_reports_can_still_be_deactivated_without_a_manager(
    client, as_user, db_session, company, company_admin
):
    """Regression guard: the handover rules must not block ordinary offboarding."""
    loner = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(company_admin)

    assert (await client.post(f"{USERS}/{loner.id}/deactivate")).status_code == 200
