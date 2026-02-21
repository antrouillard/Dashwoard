import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class SkillNode(BaseModel):
    name: str
    level: str
    detail: str | None = None


class ProfessionBase(BaseModel):
    name: str
    kp_current: int = 0
    kp_max: int = 0
    bonus: str | None = None


class ProfessionCreate(ProfessionBase):
    character_id: int


class ProfessionUpdate(BaseModel):
    kp_current: int | None = None
    kp_max: int | None = None
    bonus: str | None = None
    skill_tree: list[SkillNode] | None = None


class ProfessionOut(ProfessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    skill_tree: list[SkillNode] = []
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_skill_tree(cls, data):
        """skill_tree est stocké en JSON string en base, ou None."""
        if hasattr(data, "__dict__"):
            raw = getattr(data, "skill_tree", None)
            if raw is None:
                object.__setattr__(data, "skill_tree", [])
            elif isinstance(raw, str):
                try:
                    object.__setattr__(data, "skill_tree", json.loads(raw))
                except (json.JSONDecodeError, AttributeError):
                    object.__setattr__(data, "skill_tree", [])
        return data
