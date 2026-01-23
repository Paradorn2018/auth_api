from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.refresh_token import RefreshToken


def create_refresh_token(
    db: Session,
    user_id: int,
    session_id: str,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip: str | None = None,
) -> RefreshToken:
    rt = RefreshToken(
        user_id=user_id,
        session_id=session_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()


def revoke(db: Session, rt: RefreshToken) -> None:
    now = datetime.now(timezone.utc)
    rt.revoked_at = now
    rt.last_used_at = now
    db.commit()



def revoke_all_for_user(db: Session, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    q = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    count = q.count()
    q.update({"revoked_at": now, "last_used_at": now}, synchronize_session=False)
    db.commit()
    return count

