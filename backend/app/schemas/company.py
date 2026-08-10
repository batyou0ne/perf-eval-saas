import uuid
from datetime import datetime

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str


class CompanyRead(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyOption(BaseModel):
    """Just enough to render a picker — kept slim because this list isn't paginated."""

    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}
