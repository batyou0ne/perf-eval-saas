"""Admin self-service: deactivating and reactivating users."""

from app.models import UserRole
from tests.factories import make_user

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


async def test_company_admin_can_unassign_a_users_manager(client, as_user, company_admin, employee):
    as_user(company_admin)

    response = await client.post(f"{USERS}/{employee.id}/manager", json={"manager_id": None})

    assert response.status_code == 200
    assert response.json()["manager_id"] is None
