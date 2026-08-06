import uuid

from pydantic import BaseModel


class AssignManagerRequest(BaseModel):
    manager_id: uuid.UUID | None
