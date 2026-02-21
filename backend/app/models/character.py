from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Identité
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    realm: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(10), default="eu")
    class_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    spec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Heal / Tank / DPS
    level: Mapped[int] = mapped_column(Integer, default=80)
    race: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    faction: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Alliance / Horde

    # Stats de jeu
    ilvl: Mapped[int] = mapped_column(Integer, default=0)
    ilvl_equipped: Mapped[int] = mapped_column(Integer, default=0)
    mythic_score: Mapped[float] = mapped_column(Float, default=0.0)
    gold: Mapped[int] = mapped_column(Integer, default=0)       # en copper (Blizzard renvoie copper)
    time_played_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Raider.io
    raiderio_score: Mapped[float] = mapped_column(Float, default=0.0)
    raiderio_rank_world: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raiderio_rank_region: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raiderio_rank_realm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raiderio_best_runs: Mapped[str | None] = mapped_column(String(5000), nullable=True)  # JSON
    raiderio_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # FK
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    guild_id: Mapped[int | None] = mapped_column(ForeignKey("guilds.id"), nullable=True)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    account: Mapped["Account"] = relationship("Account", back_populates="characters")  # noqa: F821
    guild: Mapped["Guild | None"] = relationship("Guild", back_populates="characters")  # noqa: F821
    todos: Mapped[list["Todo"]] = relationship(  # noqa: F821
        "Todo", back_populates="character", cascade="all, delete-orphan"
    )
    professions: Mapped[list["Profession"]] = relationship(  # noqa: F821
        "Profession", back_populates="character", cascade="all, delete-orphan"
    )
    weekly_activities: Mapped[list["WeeklyActivity"]] = relationship(  # noqa: F821
        "WeeklyActivity", back_populates="character", cascade="all, delete-orphan"
    )
