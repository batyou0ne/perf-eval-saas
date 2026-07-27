"""Invite-only registration: who may invite whom, and what an invite grants."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Invite, UserRole
from tests.factories import make_user

INVITES = "/api/v1/invites"


def _token_from(response) -> str:
    return response.json()["invite_link"].rstrip("/").rsplit("/", 1)[-1]


async def test_company_admin_can_invite_an_employee(client, as_user, company_admin):
    as_user(company_admin)

    response = await client.post(INVITES, json={"email": "new@example.com", "role": "employee"})

    assert response.status_code == 200
    assert response.json()["role"] == "employee"


@pytest.mark.parametrize("role", ["company_admin", "manager", "hr", "employee"])
async def test_company_admin_may_invite_any_role_below_super_admin(client, as_user, company_admin, role):
    as_user(company_admin)

    response = await client.post(INVITES, json={"email": f"{role}@example.com", "role": role})

    assert response.status_code == 200


async def test_company_admin_cannot_invite_a_super_admin(client, as_user, company_admin):
    as_user(company_admin)

    response = await client.post(INVITES, json={"email": "sneaky@example.com", "role": "super_admin"})

    assert response.status_code == 403


async def test_company_admin_invite_ignores_a_supplied_company_id(
    client, as_user, company_admin, company, other_company
):
    """A company_id in the body must be ignored, not honoured — this is the tenant boundary."""
    as_user(company_admin)

    response = await client.post(
        INVITES,
        json={"email": "crosstenant2@example.com", "role": "employee", "company_id": str(other_company.id)},
    )
    assert response.status_code == 200

    preview = await client.get(f"{INVITES}/{_token_from(response)}")
    assert preview.json()["company_name"] == company.name


async def test_employee_cannot_invite(client, as_user, employee):
    as_user(employee)
    assert (await client.post(INVITES, json={"email": "x@example.com", "role": "employee"})).status_code == 403


async def test_manager_cannot_invite(client, as_user, manager):
    as_user(manager)
    assert (await client.post(INVITES, json={"email": "x@example.com", "role": "employee"})).status_code == 403


async def test_super_admin_must_supply_a_company_id(client, as_user, super_admin):
    as_user(super_admin)

    response = await client.post(INVITES, json={"email": "admin@newco.example", "role": "company_admin"})

    assert response.status_code == 400


async def test_super_admin_can_only_invite_company_admins(client, as_user, super_admin, company):
    """Invite.company_id is required, so a company-less super_admin can't be invited this way."""
    as_user(super_admin)

    ok = await client.post(
        INVITES, json={"email": "ca@newco.example", "role": "company_admin", "company_id": str(company.id)}
    )
    assert ok.status_code == 200

    rejected = await client.post(
        INVITES, json={"email": "sa@newco.example", "role": "super_admin", "company_id": str(company.id)}
    )
    assert rejected.status_code == 403


async def test_cannot_invite_an_existing_user(client, as_user, company_admin, employee):
    as_user(company_admin)

    response = await client.post(INVITES, json={"email": employee.email, "role": "employee"})

    assert response.status_code == 400


async def test_invite_preview_is_public(client, as_user, company_admin, company):
    as_user(company_admin)
    created = await client.post(INVITES, json={"email": "preview@example.com", "role": "hr"})
    token = _token_from(created)

    client.headers.pop("Authorization", None)
    preview = await client.get(f"{INVITES}/{token}")

    assert preview.status_code == 200
    body = preview.json()
    assert body["company_name"] == company.name
    assert body["role"] == "hr"
    assert body["accepted_at"] is None


async def test_invite_preview_unknown_token_is_404(client):
    assert (await client.get(f"{INVITES}/does-not-exist")).status_code == 404


async def test_accepting_an_invite_creates_a_user_with_the_invited_role_and_company(
    client, as_user, company_admin, company
):
    as_user(company_admin)
    created = await client.post(INVITES, json={"email": "joiner@example.com", "role": "hr"})
    token = _token_from(created)

    client.headers.pop("Authorization", None)
    accepted = await client.post(
        f"{INVITES}/{token}/accept", json={"full_name": "Jo Joiner", "password": "joinerpass123"}
    )
    assert accepted.status_code == 200

    client.headers["Authorization"] = f"Bearer {accepted.json()['access_token']}"
    me = (await client.get("/api/v1/auth/me")).json()
    assert me["email"] == "joiner@example.com"
    assert me["role"] == "hr"
    assert me["company_id"] == str(company.id)


async def test_an_invite_cannot_be_accepted_twice(client, as_user, company_admin):
    as_user(company_admin)
    created = await client.post(INVITES, json={"email": "once@example.com", "role": "employee"})
    token = _token_from(created)
    client.headers.pop("Authorization", None)

    first = await client.post(f"{INVITES}/{token}/accept", json={"full_name": "First", "password": "firstpass123"})
    assert first.status_code == 200

    second = await client.post(f"{INVITES}/{token}/accept", json={"full_name": "Second", "password": "secondpass123"})
    assert second.status_code == 400


async def test_an_expired_invite_cannot_be_accepted(client, db_session, company, company_admin):
    expired = Invite(
        email="expired@example.com",
        company_id=company.id,
        role=UserRole.EMPLOYEE,
        token="expired-token-value",
        invited_by_id=company_admin.id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(expired)
    await db_session.flush()

    response = await client.post(
        f"{INVITES}/expired-token-value/accept", json={"full_name": "Too Late", "password": "toolatepass123"}
    )

    assert response.status_code == 400


async def test_hr_cannot_invite(client, as_user, db_session, company):
    """HR is deliberately not in the inviter allow-list — only company_admin and super_admin are."""
    hr = await make_user(db_session, role=UserRole.HR, company_id=company.id)
    as_user(hr)

    response = await client.post(INVITES, json={"email": "hrinvite@example.com", "role": "employee"})

    assert response.status_code == 403
