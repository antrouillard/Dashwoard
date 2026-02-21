import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from app.schemas.todo import TodoOut
from app.schemas.profession import ProfessionOut


class CharacterBase(BaseModel):
    name: str
    realm: str
    region: str = "eu"
    class_name: str | None = None
    spec: str | None = None
    role: str | None = None
    level: int = 80
    faction: str | None = None


class CharacterCreate(CharacterBase):
    account_id: int


class CharacterUpdate(BaseModel):
    class_name: str | None = None
    spec: str | None = None
    role: str | None = None
    ilvl: int | None = None
    mythic_score: float | None = None


class CharacterOut(CharacterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    guild_id: int | None = None
    ilvl: int
    ilvl_equipped: int
    mythic_score: float
    gold: int
    time_played_seconds: int
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Raider.io
    raiderio_score: float = 0.0
    raiderio_rank_world: int | None = None
    raiderio_rank_region: int | None = None
    raiderio_rank_realm: int | None = None
    raiderio_best_runs: list[dict] = []
    raiderio_last_sync_at: datetime | None = None

    todos: list[TodoOut] = []
    professions: list[ProfessionOut] = []

    @model_validator(mode="before")
    @classmethod
    def parse_raiderio_runs(cls, data):
        """Parse raiderio_best_runs depuis JSON string ou None avant validation."""
        if hasattr(data, "__dict__"):
            raw = getattr(data, "raiderio_best_runs", None)
            if raw is None:
                object.__setattr__(data, "raiderio_best_runs", [])
            elif isinstance(raw, str):
                try:
                    object.__setattr__(data, "raiderio_best_runs", json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    object.__setattr__(data, "raiderio_best_runs", [])
        return data

    @computed_field
    @property
    def gold_display(self) -> str:
        g = self.gold // 10000
        s = (self.gold % 10000) // 100
        c = self.gold % 100
        return f"{g}g {s}s {c}c"

    @computed_field
    @property
    def time_played_display(self) -> str:
        h = self.time_played_seconds // 3600
        m = (self.time_played_seconds % 3600) // 60
        return f"{h}h {m}m"
