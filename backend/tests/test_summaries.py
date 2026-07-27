"""AI evaluation summaries.

Gemini is always mocked here — GEMINI_API_KEY is blank in the test environment, so
an unmocked call fails loudly rather than silently costing money or flaking on a
network hiccup.
"""

from unittest.mock import AsyncMock

import pytest

from app.ai.evaluation_summary import EvaluationSummaryContent
from tests.factories import find_evaluation, make_user, submit_evaluation
from app.models import UserRole

CYCLES = "/api/v1/cycles"

FAKE_SUMMARY = EvaluationSummaryContent(
    synthesis="Consistent performer with strong delivery.",
    strengths=["Ships reliably"],
    growth_areas=["Public speaking"],
    alignment_notes="Self and manager agree on strengths; manager rated slightly higher.",
)


def summary_url(cycle_id, subject_id) -> str:
    return f"{CYCLES}/{cycle_id}/subjects/{subject_id}/summary"


@pytest.fixture
def mock_gemini(monkeypatch) -> AsyncMock:
    """Patch where it's used, not where it's defined — the service imported the name."""
    mock = AsyncMock(return_value=FAKE_SUMMARY)
    monkeypatch.setattr("app.services.evaluation_summary_service.generate_evaluation_summary", mock)
    return mock


@pytest.fixture
async def active_cycle(client, as_user, company_admin, manager, employee, cycle):
    as_user(company_admin)
    await client.post(f"{CYCLES}/{cycle.id}/activate")
    return cycle


@pytest.fixture
async def both_submitted(client, as_user, employee, manager, active_cycle):
    """Employee's self-evaluation and their manager's evaluation, both submitted."""
    as_user(employee)
    self_eval = await find_evaluation(client, cycle_id=active_cycle.id, subject_id=employee.id, eval_type="self")
    await submit_evaluation(client, self_eval["id"])

    as_user(manager)
    manager_eval = await find_evaluation(client, cycle_id=active_cycle.id, subject_id=employee.id, eval_type="manager")
    await submit_evaluation(client, manager_eval["id"])

    return active_cycle


async def test_company_admin_cannot_generate_before_anything_is_submitted(
    client, as_user, company_admin, employee, active_cycle, mock_gemini
):
    """403 rather than 400, on purpose.

    An admin may only see *submitted* evaluations, so with nothing submitted there is
    nothing they're allowed to look at and authorization fails before the readiness
    check. The 400 "must be submitted first" path is reachable once at least one
    evaluation is visible to them — covered by the next test.
    """
    as_user(company_admin)

    response = await client.post(summary_url(active_cycle.id, employee.id))

    assert response.status_code == 403
    mock_gemini.assert_not_awaited()


async def test_evaluator_generating_before_submission_gets_a_readiness_error(
    client, as_user, manager, employee, active_cycle, mock_gemini
):
    """The manager can always see their own evaluation, so they reach the 400 instead."""
    as_user(manager)

    response = await client.post(summary_url(active_cycle.id, employee.id))

    assert response.status_code == 400
    mock_gemini.assert_not_awaited()


async def test_generating_with_only_the_self_evaluation_submitted_is_rejected(
    client, as_user, company_admin, employee, active_cycle, mock_gemini
):
    as_user(employee)
    self_eval = await find_evaluation(client, cycle_id=active_cycle.id, subject_id=employee.id, eval_type="self")
    await submit_evaluation(client, self_eval["id"])

    as_user(company_admin)
    response = await client.post(summary_url(active_cycle.id, employee.id))

    assert response.status_code == 400
    mock_gemini.assert_not_awaited()


async def test_generating_after_both_are_submitted_returns_the_summary(
    client, as_user, company_admin, employee, both_submitted, mock_gemini
):
    as_user(company_admin)

    response = await client.post(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 200
    body = response.json()
    assert body["synthesis"] == FAKE_SUMMARY.synthesis
    assert body["strengths"] == FAKE_SUMMARY.strengths
    assert body["alignment_notes"] == FAKE_SUMMARY.alignment_notes
    mock_gemini.assert_awaited_once()


async def test_the_summary_is_generated_once_and_then_reused(
    client, as_user, company_admin, employee, both_submitted, mock_gemini
):
    """A second POST must return the stored row rather than paying for another call."""
    as_user(company_admin)

    first = await client.post(summary_url(both_submitted.id, employee.id))
    second = await client.post(summary_url(both_submitted.id, employee.id))

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    mock_gemini.assert_awaited_once()


async def test_get_returns_404_before_a_summary_exists(
    client, as_user, company_admin, employee, both_submitted, mock_gemini
):
    as_user(company_admin)

    response = await client.get(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 404


async def test_get_returns_the_summary_once_generated(
    client, as_user, company_admin, employee, both_submitted, mock_gemini
):
    as_user(company_admin)
    await client.post(summary_url(both_submitted.id, employee.id))

    response = await client.get(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 200
    assert response.json()["synthesis"] == FAKE_SUMMARY.synthesis


async def test_the_subject_can_read_their_own_summary(
    client, as_user, company_admin, employee, both_submitted, mock_gemini
):
    as_user(company_admin)
    await client.post(summary_url(both_submitted.id, employee.id))

    as_user(employee)
    response = await client.get(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 200


async def test_an_unrelated_colleague_cannot_read_a_summary(
    client, as_user, db_session, company, company_admin, employee, both_submitted, mock_gemini
):
    as_user(company_admin)
    await client.post(summary_url(both_submitted.id, employee.id))

    bystander = await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id)
    as_user(bystander)
    response = await client.get(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 403


async def test_another_companys_admin_cannot_generate_a_summary(
    client, as_user, other_company_admin, employee, both_submitted, mock_gemini
):
    as_user(other_company_admin)

    response = await client.post(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 403
    mock_gemini.assert_not_awaited()


async def test_upstream_ai_failure_surfaces_as_502(
    client, as_user, company_admin, employee, both_submitted, monkeypatch
):
    from google.genai.errors import ClientError

    failing = AsyncMock(side_effect=ClientError(429, {"error": {"message": "quota"}}))
    monkeypatch.setattr("app.services.evaluation_summary_service.generate_evaluation_summary", failing)
    as_user(company_admin)

    response = await client.post(summary_url(both_submitted.id, employee.id))

    assert response.status_code == 502
    assert "quota" in response.json()["detail"].lower()
