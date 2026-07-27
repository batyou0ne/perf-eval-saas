"""Guards the fixture harness itself — DB isolation, auth wiring, app boot."""

from app.models import UserRole


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["api"] == "ok"


async def test_authenticated_me(client, as_user, company_admin):
    as_user(company_admin)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(company_admin.id)
    assert body["role"] == UserRole.COMPANY_ADMIN.value


async def test_isolation_first(db_session, company):
    from app.models import Company
    from sqlalchemy import select

    result = await db_session.execute(select(Company))
    assert len(list(result.scalars().all())) == 1


async def test_isolation_second(db_session, company):
    """If the previous test's data leaked, this sees 2 companies instead of 1."""
    from app.models import Company
    from sqlalchemy import select

    result = await db_session.execute(select(Company))
    assert len(list(result.scalars().all())) == 1
