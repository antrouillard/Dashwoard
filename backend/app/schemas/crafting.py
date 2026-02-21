from datetime import datetime

from pydantic import BaseModel, ConfigDict

ORDER_STATUSES = ["a_faire", "en_cours", "termine"]


# ── Référence minimale au personnage embarquée dans les réponses ──────────────

class CharacterRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    realm: str | None = None


# ── CraftingOrder ─────────────────────────────────────────────────────────────

class CraftingOrderBase(BaseModel):
    item_name: str
    item_id: int | None = None      # item_id Blizzard/Wowhead (pour le tooltip)
    recipe_id: int | None = None    # recipe_id Blizzard (pour récupérer réactifs)
    client: str
    profession: str
    status: str = "a_faire"
    profit_gold: int = 0  # en gold (pas copper)


class CraftingOrderCreate(CraftingOrderBase):
    character_id: int


class CraftingOrderUpdate(BaseModel):
    item_name: str | None = None
    client: str | None = None
    profession: str | None = None
    status: str | None = None
    profit_gold: int | None = None


class CraftingOrderOut(CraftingOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    character: CharacterRef | None = None
    created_at: datetime
    updated_at: datetime


# ── Recipe (lecture seule — données Blizzard statiques) ───────────────────────

class RecipeOut(BaseModel):
    recipe_id: int
    name: str
    category: str = ""


class RecipeDetailOut(BaseModel):
    recipe_id: int
    recipe_name: str | None = None
    item_id: int | None = None
    item_name: str | None = None
    reagents: list[dict] = []


# ── CraftingGoal ──────────────────────────────────────────────────────────────

# ── CraftingGoal ──────────────────────────────────────────────────────────────

class CraftingGoalBase(BaseModel):
    title: str
    detail: str | None = None
    progress_pct: int = 0   # 0-100
    profession: str
    item_id: int | None = None      # item_id Blizzard/Wowhead
    recipe_id: int | None = None


class CraftingGoalCreate(CraftingGoalBase):
    character_id: int


class CraftingGoalUpdate(BaseModel):
    title: str | None = None
    detail: str | None = None
    profession: str | None = None


class CraftingGoalOut(CraftingGoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    character: CharacterRef | None = None
    created_at: datetime
    updated_at: datetime


# ── CraftingGoalReagent (quantités posssédées par réactif) ────────────────

class GoalReagentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    goal_id: int
    item_id: int
    have_qty: int


class GoalReagentPatch(BaseModel):
    have_qty: int
