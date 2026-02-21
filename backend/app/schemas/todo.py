from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TodoBase(BaseModel):
    title: str
    description: str | None = None
    priority: int = 1
    status: str = "a_faire"  # a_faire | en_cours | termine


class TodoCreate(TodoBase):
    character_id: int


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: int | None = None
    status: str | None = None


class TodoOut(TodoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    created_at: datetime
    updated_at: datetime
