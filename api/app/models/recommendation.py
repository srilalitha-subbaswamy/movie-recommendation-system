"""Recommendation ORM model for precomputed results."""

from datetime import datetime

from sqlalchemy import Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRecommendation(Base):
    """Precomputed user recommendations."""

    __tablename__ = "user_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    recommendations: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, server_default="als")
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserRecommendation(user_id={self.user_id}, model={self.model_version})>"
