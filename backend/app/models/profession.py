from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Profession(Base):
    __tablename__ = "professions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kp_current: Mapped[int] = mapped_column(Integer, default=0)
    kp_max: Mapped[int] = mapped_column(Integer, default=0)
    skill_tree: Mapped[str | None] = mapped_column(String(5000), nullable=True)  # JSON string
    bonus: Mapped[str | None] = mapped_column(String(200), nullable=True)

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    character: Mapped["Character"] = relationship("Character", back_populates="professions")  # noqa: F821
