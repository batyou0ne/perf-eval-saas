import uuid
from datetime import datetime

from pydantic import BaseModel


class EvaluationSummaryRead(BaseModel):
    id: uuid.UUID
    cycle_id: uuid.UUID
    subject_id: uuid.UUID
    synthesis: str
    strengths: list[str]
    growth_areas: list[str]
    alignment_notes: str
    created_at: datetime
