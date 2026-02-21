from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    realm: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(10), default="eu")
    faction: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Raid progress stocké en JSON (ex: {"Normal":{"done":9,"total":9}, ...})
    raid_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    raid_progress: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # JSON string
    member_count: Mapped[int] = mapped_column(Integer, default=0)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    characters: Mapped[list["Character"]] = relationship(  # noqa: F821
        "Character", back_populates="guild"
    )
