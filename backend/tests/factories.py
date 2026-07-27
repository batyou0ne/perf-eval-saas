"""Shared test data helpers.

Kept out of conftest.py on purpose: importing conftest from a test module loads it
a second time under a different module name, re-running its import-time environment
setup. Test modules import from here instead.
"""

import uuid

from app.core.security import hash_password
from app.models import User, UserRole

TEST_PASSWORD = "testpassword123"


async def make_user(
    session,
    *,
    role: UserRole,
    company_id=None,
    manager_id=None,
    email: str | None = None,
    full_name: str | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        email=email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password(TEST_PASSWORD),
        full_name=full_name or role.value.replace("_", " ").title(),
        role=role,
        company_id=company_id,
        manager_id=manager_id,
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def find_evaluation(client, *, cycle_id, subject_id, eval_type: str) -> dict | None:
    """Locate one of the current user's evaluations from /evaluations/me."""
    listing = (await client.get("/api/v1/evaluations/me")).json()
    return next(
        (
            e
            for e in listing
            if e["cycle_id"] == str(cycle_id) and e["subject_id"] == str(subject_id) and e["type"] == eval_type
        ),
        None,
    )


def build_responses(detail: dict, *, rating: int = 4, text: str = "Solid work this quarter.") -> dict:
    """Turn an evaluation detail payload into a valid submit body."""
    return {
        "responses": [
            {"question_id": q["id"], "rating_value": rating}
            if q["type"] == "rating"
            else {"question_id": q["id"], "text_value": text}
            for q in detail["questions"]
        ]
    }


async def submit_evaluation(client, evaluation_id, *, rating: int = 4, text: str = "Solid work this quarter."):
    """Answer every question on an evaluation and submit it, as the current user.

    Reads the questions back through the API, so the caller must be allowed to view
    the evaluation — use build_responses() directly when testing an unauthorised actor.
    """
    detail = (await client.get(f"/api/v1/evaluations/{evaluation_id}")).json()
    body = build_responses(detail, rating=rating, text=text)
    return await client.post(f"/api/v1/evaluations/{evaluation_id}/submit", json=body)
