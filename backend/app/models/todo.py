from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

TODO_STATUSES = ("a_faire", "en_cours", "termine")


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    priority: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(20), default="a_faire")  # a_faire | en_cours | termine

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    character: Mapped["Character"] = relationship("Character", back_populates="todos")  # noqa: F821
