"""Company management is super-admin-only, and listing must not leak across tenants."""

COMPANIES = "/api/v1/companies"


async def test_super_admin_can_create_a_company(client, as_user, super_admin):
    as_user(super_admin)

    response = await client.post(COMPANIES, json={"name": "Initech LLC"})

    assert response.status_code == 200
    assert response.json()["name"] == "Initech LLC"


async def test_super_admin_can_list_companies(client, as_user, super_admin, company, other_company):
    as_user(super_admin)

    response = await client.get(COMPANIES)

    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert {company.name, other_company.name} <= names


async def test_company_admin_cannot_create_a_company(client, as_user, company_admin):
    as_user(company_admin)
    assert (await client.post(COMPANIES, json={"name": "Nope Inc"})).status_code == 403


async def test_company_admin_cannot_list_companies(client, as_user, company_admin):
    as_user(company_admin)
    assert (await client.get(COMPANIES)).status_code == 403


async def test_employee_cannot_create_a_company(client, as_user, employee):
    as_user(employee)
    assert (await client.post(COMPANIES, json={"name": "Nope Inc"})).status_code == 403


async def test_unauthenticated_cannot_list_companies(client):
    assert (await client.get(COMPANIES)).status_code == 401
