from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(10), default="eu")
    realm: Mapped[str] = mapped_column(String(100), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Blizzard OAuth tokens (stockés chiffrés en prod, plain pour le dev)
    blizzard_battletag: Mapped[str | None] = mapped_column(String(200), nullable=True)
    blizzard_access_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    blizzard_refresh_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    blizzard_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    characters: Mapped[list["Character"]] = relationship(  # noqa: F821
        "Character", back_populates="account", cascade="all, delete-orphan"
    )
