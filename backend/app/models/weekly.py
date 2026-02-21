from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class WeeklyActivity(Base):
    __tablename__ = "weekly_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)   # vault_guild, catalyst, world_boss...
    detail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="a_faire")
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    character: Mapped["Character"] = relationship("Character", back_populates="weekly_activities")  # noqa: F821
