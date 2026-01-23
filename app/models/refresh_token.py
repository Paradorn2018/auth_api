from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base



class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # ใช้แยก session/device (เช่น uuid string)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # เก็บ hash ของ refresh token (ห้ามเก็บ token จริง)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # optional telemetry
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")
