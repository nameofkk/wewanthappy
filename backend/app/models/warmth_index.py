from sqlalchemy import Float, SmallInteger, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.app.core.database import Base


class WarmthIndex(Base):
    __tablename__ = "warmth_index"

    time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    country_code: Mapped[str] = mapped_column(String(4), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    warmth_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    event_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    accel_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    spread_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    percentile_30d: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
