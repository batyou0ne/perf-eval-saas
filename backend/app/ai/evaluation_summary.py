from google.genai import types
from pydantic import BaseModel

from app.ai.client import get_gemini_client
from app.core.config import get_settings

settings = get_settings()


class EvaluationSummaryContent(BaseModel):
    synthesis: str
    strengths: list[str]
    growth_areas: list[str]
    alignment_notes: str


_SYSTEM_PROMPT = """You are an assistant that synthesizes employee performance review data for HR and \
management use. You will be given a self-evaluation and a manager's evaluation of the same employee, \
for the same review cycle.

Produce a synthesis that is:
- Grounded strictly in the content provided. Do not invent specific examples, projects, or incidents \
that are not mentioned in the source text or the completed-tasks list.
- Professional and constructive in tone.
- Specific about where the self-evaluation and manager evaluation agree or disagree, since that \
comparison is the most useful thing you can add beyond either review alone.
- Where relevant, ground a point in one of the completed tasks by name rather than speaking only \
in generalities — that's the most concrete evidence available for this period.

If the provided text is too brief or vague to support a confident, specific observation, say so \
plainly rather than filling the gap with a generic or invented detail."""


def _format_qa(qa: list[tuple[str, str]]) -> str:
    return "\n".join(f"{i}. Q: {q}\n   A: {a}" for i, (q, a) in enumerate(qa, start=1))


def _format_tasks(titles: list[str]) -> str:
    return "\n".join(f"- {t}" for t in titles) if titles else "None recorded for this period."


async def generate_evaluation_summary(
    *,
    subject_name: str,
    subject_role: str,
    cycle_name: str,
    self_qa: list[tuple[str, str]],
    manager_name: str,
    manager_qa: list[tuple[str, str]],
    completed_task_titles: list[str],
) -> EvaluationSummaryContent:
    user_prompt = f"""Review cycle: {cycle_name}
Employee: {subject_name} ({subject_role})
Manager: {manager_name}

Self-evaluation responses:
{_format_qa(self_qa)}

Manager's evaluation responses:
{_format_qa(manager_qa)}

Tasks {subject_name} completed during this period:
{_format_tasks(completed_task_titles)}"""

    response = await get_gemini_client().aio.models.generate_content(
        model=settings.gemini_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=EvaluationSummaryContent,
        ),
    )
    return response.parsed
