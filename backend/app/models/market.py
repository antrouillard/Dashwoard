from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AhSnapshot(Base):
    """Historique des prix de l'Auction House."""

    __tablename__ = "ah_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price_copper: Mapped[int] = mapped_column(BigInteger, nullable=False)  # buyout en copper
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    connected_realm_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
