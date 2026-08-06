"""Auth flow: login, token refresh with rotation, logout revocation, password reset."""

import pytest

from app.models import UserRole
from tests.factories import TEST_PASSWORD, make_user

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
RESET_REQUEST = "/api/v1/auth/password-reset/request"
RESET_CONFIRM = "/api/v1/auth/password-reset/confirm"


def _set_cookie_header(response) -> str:
    return "; ".join(response.headers.get_list("set-cookie"))


async def test_login_success_returns_token_and_sets_refresh_cookie(client, company_admin):
    response = await client.post(LOGIN, json={"email": company_admin.email, "password": TEST_PASSWORD})

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert "refresh_token=" in _set_cookie_header(response)


async def test_login_wrong_password_is_401(client, company_admin):
    response = await client.post(LOGIN, json={"email": company_admin.email, "password": "wrong-password"})
    assert response.status_code == 401


async def test_login_unknown_email_is_401(client, company_admin):
    response = await client.post(LOGIN, json={"email": "nobody@example.com", "password": TEST_PASSWORD})
    assert response.status_code == 401


async def test_login_inactive_user_is_403(client, db_session, company):
    inactive = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, is_active=False)

    response = await client.post(LOGIN, json={"email": inactive.email, "password": TEST_PASSWORD})
    assert response.status_code == 403


async def test_refresh_cookie_is_httponly(client, company_admin):
    response = await client.post(LOGIN, json={"email": company_admin.email, "password": TEST_PASSWORD})
    assert "httponly" in _set_cookie_header(response).lower()


@pytest.mark.parametrize(
    ("remember_me", "expect_max_age"),
    [(True, True), (False, False)],
)
async def test_remember_me_controls_cookie_persistence(client, company_admin, remember_me, expect_max_age):
    """Unchecked must produce a session cookie (no Max-Age) that dies with the browser."""
    response = await client.post(
        LOGIN, json={"email": company_admin.email, "password": TEST_PASSWORD, "remember_me": remember_me}
    )

    assert ("max-age" in _set_cookie_header(response).lower()) is expect_max_age


async def test_me_without_token_is_401(client):
    response = await client.get(ME)
    assert response.status_code == 401


async def test_me_returns_current_user(client, as_user, employee):
    as_user(employee)

    response = await client.get(ME)

    assert response.status_code == 200
    assert response.json()["id"] == str(employee.id)


async def test_refresh_rotates_token_and_rejects_the_old_one(client, company_admin):
    await client.post(LOGIN, json={"email": company_admin.email, "password": TEST_PASSWORD})
    original_cookie = client.cookies.get("refresh_token")

    rotated = await client.post(REFRESH)
    assert rotated.status_code == 200
    assert client.cookies.get("refresh_token") != original_cookie

    # Replaying the pre-rotation token must fail even though it hasn't expired.
    client.cookies.set("refresh_token", original_cookie)
    replay = await client.post(REFRESH)
    assert replay.status_code == 401


async def test_refresh_without_cookie_is_401(client):
    response = await client.post(REFRESH)
    assert response.status_code == 401


async def test_logout_revokes_the_refresh_token(client, company_admin):
    await client.post(LOGIN, json={"email": company_admin.email, "password": TEST_PASSWORD})

    assert (await client.post(LOGOUT)).status_code == 204
    assert (await client.post(REFRESH)).status_code == 401


async def test_login_is_rate_limited_after_five_attempts_per_minute(client, company_admin):
    for _ in range(5):
        response = await client.post(LOGIN, json={"email": company_admin.email, "password": "wrong-password"})
        assert response.status_code == 401

    sixth = await client.post(LOGIN, json={"email": company_admin.email, "password": "wrong-password"})
    assert sixth.status_code == 429


async def test_password_reset_request_is_rate_limited_after_three_attempts_per_minute(client, company_admin):
    for _ in range(3):
        response = await client.post(RESET_REQUEST, json={"email": company_admin.email})
        assert response.status_code == 204

    fourth = await client.post(RESET_REQUEST, json={"email": company_admin.email})
    assert fourth.status_code == 429


async def test_password_reset_does_not_reveal_whether_email_exists(client, company_admin):
    known = await client.post(RESET_REQUEST, json={"email": company_admin.email})
    unknown = await client.post(RESET_REQUEST, json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 204
    assert known.content == unknown.content


async def test_password_reset_changes_password_and_token_is_single_use(client, db_session, company_admin, monkeypatch):
    captured: list[str] = []

    # The reset link is only printed to the console (no email provider yet), so
    # intercept the token at the source rather than scraping stdout.
    import app.services.auth_service as auth_service

    real_generate = auth_service.generate_secure_token

    def _capture() -> str:
        token = real_generate()
        captured.append(token)
        return token

    monkeypatch.setattr(auth_service, "generate_secure_token", _capture)

    await client.post(RESET_REQUEST, json={"email": company_admin.email})
    assert captured, "no reset token was generated"
    token = captured[0]

    confirmed = await client.post(RESET_CONFIRM, json={"token": token, "new_password": "brand-new-password"})
    assert confirmed.status_code == 200

    old = await client.post(LOGIN, json={"email": company_admin.email, "password": TEST_PASSWORD})
    assert old.status_code == 401
    new = await client.post(LOGIN, json={"email": company_admin.email, "password": "brand-new-password"})
    assert new.status_code == 200

    reused = await client.post(RESET_CONFIRM, json={"token": token, "new_password": "another-password"})
    assert reused.status_code == 400


async def test_password_reset_with_invalid_token_is_400(client):
    response = await client.post(RESET_CONFIRM, json={"token": "not-a-real-token", "new_password": "whatever123"})
    assert response.status_code == 400
