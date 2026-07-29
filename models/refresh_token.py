"""Server-side refresh tokens for JWT session lifecycle (Security Wave 0)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index
from database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_family_id", "family_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    jti = Column(String(64), unique=True, nullable=False)
    family_id = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_jti = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)


class AccessTokenDenylist(Base):
    """Optional short-lived denylist for access-token jti after logout/password change."""

    __tablename__ = "access_token_denylist"
    __table_args__ = (Index("ix_access_token_denylist_expires_at", "expires_at"),)

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    reason = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
