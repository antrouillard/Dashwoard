import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class RaidStage(BaseModel):
    label: str
    done: int
    total: int


class GuildBase(BaseModel):
    name: str
    realm: str
    region: str = "eu"
    faction: str | None = None


class GuildCreate(GuildBase):
    pass


class GuildUpdate(BaseModel):
    raid_name: str | None = None
    raid_progress: list[RaidStage] | None = None
    member_count: int | None = None


class GuildOut(GuildBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raid_name: str | None = None
    raid_progress: list[RaidStage] = []
    member_count: int
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_raid_progress(cls, data):
        if hasattr(data, "__dict__"):
            raw = getattr(data, "raid_progress", None)
            if isinstance(raw, str):
                try:
                    object.__setattr__(data, "raid_progress", json.loads(raw))
                except (json.JSONDecodeError, AttributeError):
                    pass
        return data
