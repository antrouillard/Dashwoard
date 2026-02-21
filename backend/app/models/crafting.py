from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CraftingOrder(Base):
    __tablename__ = "crafting_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client: Mapped[str] = mapped_column(String(100), nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
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

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    character: Mapped["Character"] = relationship("Character")  # noqa: F821
