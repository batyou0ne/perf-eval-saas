import uuid

from pydantic import BaseModel


class AssignManagerRequest(BaseModel):
    manager_id: uuid.UUID | None


class UserOption(BaseModel):
    """Just enough to render a picker — kept slim because this list isn't paginated."""

    id: uuid.UUID
    full_name: str

    model_config = {"from_attributes": True}
