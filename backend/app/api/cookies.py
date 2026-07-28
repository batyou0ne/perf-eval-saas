from fastapi import Response

from app.core.config import get_settings

settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, refresh_token: str, remember_me: bool = False) -> None:
    is_production = settings.environment != "development"
    cookie_kwargs = {
        "key": REFRESH_COOKIE_NAME,
        "value": refresh_token,
        "httponly": True,
        "secure": is_production,
        # Frontend and backend are deployed on different origins, so the browser
        # treats them as cross-site — SameSite=Lax would drop the cookie on fetch()
        # calls. Lax is kept for local dev where both run on http://localhost.
        "samesite": "none" if is_production else "lax",
        "path": REFRESH_COOKIE_PATH,
    }
    if remember_me:
        cookie_kwargs["max_age"] = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(**cookie_kwargs)


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
