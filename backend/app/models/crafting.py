from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CraftingOrder(Base):
    __tablename__ = "crafting_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client: Mapped[str] = mapped_column(String(100), nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)    # Wowhead item ID
    recipe_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Blizzard recipe ID
    profession: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="a_faire")
    profit_gold: Mapped[int] = mapped_column(Integer, default=0)  # en gold

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    character: Mapped["Character"] = relationship("Character")  # noqa: F821


class CraftingGoal(Base):
    __tablename__ = "crafting_goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    profession: Mapped[str] = mapped_column(String(100), nullable=False)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recipe_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    character: Mapped["Character"] = relationship("Character")  # noqa: F821
    reagent_quantities: Mapped[list["CraftingGoalReagent"]] = relationship(
        "CraftingGoalReagent", back_populates="goal", cascade="all, delete-orphan"
    )


class CraftingGoalReagent(Base):
    """Quantités possédées pour chaque réactif d'un objectif de craft."""
    __tablename__ = "crafting_goal_reagents"
    __table_args__ = (UniqueConstraint("goal_id", "item_id", name="uq_goal_reagent"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("crafting_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    have_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    goal: Mapped["CraftingGoal"] = relationship("CraftingGoal", back_populates="reagent_quantities")


class CraftingRecipeCache(Base):
    """
    Cache persistant des détails de recette (réactifs).
    Permet de restaurer recipeDetails côté frontend sans re-scraper Wowhead après un restart.
    """
    __tablename__ = "crafting_recipe_cache"

    recipe_id: Mapped[int] = mapped_column(primary_key=True)   # = Blizzard recipe_id
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    recipe_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reagents_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    cached_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
