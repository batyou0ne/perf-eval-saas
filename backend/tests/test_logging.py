"""An unhandled exception must become a clean 500, not crash the app or leak a traceback."""

import app.services.evaluation_service as evaluation_service


async def test_unhandled_exception_returns_500_and_app_stays_up(client, as_user, employee, monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("something went wrong")

    monkeypatch.setattr(evaluation_service, "list_my_evaluations", _boom)
    as_user(employee)

    response = await client.get("/api/v1/evaluations/me")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}

    # The app must still serve the next request normally.
    healthy = await client.get("/api/v1/health")
    assert healthy.status_code == 200
