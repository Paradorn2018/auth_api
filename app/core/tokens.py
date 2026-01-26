import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def create_access_token(subject: str) -> str:
    now = _now_utc()
    payload = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(subject: str):
    now = _now_utc()
    exp_dt = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
        "exp": int(exp_dt.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, exp_dt

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError("Invalid token") from e



