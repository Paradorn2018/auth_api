import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token, create_refresh_token, decode_token

from app.crud.user import get_user_by_email, create_user, get_user
from app.crud.refresh_token import (
    create_refresh_token as save_refresh,
    get_by_hash,
    revoke,
    revoke_all_for_user,
)
from app.crud.password_reset_token import (
    create_reset_token,
    get_by_hash as get_reset_by_hash,
    mark_used,
)

from app.schemas.auth import (
    RegisterRequest, LoginRequest, RefreshRequest,
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.schemas.token import TokenPair
from app.schemas.user import UserOut, ProfileUpdateRequest
from app.core.limiter import limiter
from app.core.cookies import set_refresh_cookie, clear_refresh_cookie
from typing import Optional
from app.core.email import send_reset_email



router = APIRouter(prefix="/auth", tags=["Authentication"])


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/verify")
def verify_token(current_user=Depends(get_current_user)):
    return {"active": True, "user_id": current_user.id, "email": current_user.email}


@router.get("/view-profile", response_model=UserOut, summary="Get my profile", 
            description="Return the current user's profile using the access token (Bearer).")
def me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserOut)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = create_user(db, str(payload.email), hash_password(payload.password))
    return user


@router.post("/login")
@limiter.limit("5/minute")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,   # ✅ เพิ่ม
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_id = payload.device_id or secrets.token_hex(16)
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None

    access = create_access_token(str(user.id))
    refresh, exp = create_refresh_token(str(user.id))

    save_refresh(db, user.id, session_id, _sha256(refresh), exp, user_agent=ua, ip=ip)
    db.commit()

    # ✅ ใส่ refresh token ลง cookie
    set_refresh_cookie(response, refresh)

    if settings.ENV == "prod":
        return TokenPair(access_token=access)   # refresh_token จะเป็น None
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh-access-token", response_model=TokenPair)
def refresh(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = None,
    refresh_token_cookie: Optional[str] = Cookie(default=None, alias="refresh_token"),
    db: Session = Depends(get_db),
):
    
    rt_raw = (payload.refresh_token if payload and payload.refresh_token else None) or refresh_token_cookie
    if not rt_raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    try:
        data = decode_token(rt_raw)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_hash = _sha256(rt_raw)
    rt = get_by_hash(db, token_hash)
    if not rt or rt.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token revoked/unknown")

    revoke(db, rt)

    user = get_user(db, rt.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found/inactive")

    access = create_access_token(str(user.id))
    new_refresh, exp = create_refresh_token(str(user.id))

    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None

    save_refresh(db, user.id, rt.session_id, _sha256(new_refresh), exp, user_agent=ua, ip=ip)
    db.commit()

    # ✅ rotate แล้ว set cookie ใหม่
    set_refresh_cookie(response, new_refresh)

    if settings.ENV == "prod":
        return TokenPair(access_token=access)
    return TokenPair(access_token=access, refresh_token=new_refresh)




@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token"),
    db: Session = Depends(get_db),
):
    
    # ✅ เอาจาก body ก่อน ถ้าไม่มีค่อยจาก cookie
    rt_raw = refresh_token_cookie or (payload.refresh_token if payload else None)
    if rt_raw:
        token_hash = _sha256(rt_raw)
        rt = get_by_hash(db, token_hash)
        if rt and rt.revoked_at is None:
            revoke(db, rt)
        db.commit()

    clear_refresh_cookie(response)
    return {"status": "ok"}


@router.post("/logout-all")
def logout_all(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = revoke_all_for_user(db, current_user.id)
    return {"status": "ok", "revoked": n}


@router.patch("/edit-profile", response_model=UserOut)
def edit_profile(payload: ProfileUpdateRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # update allowed fields
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone is not None:
        current_user.phone = payload.phone

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid old password")

    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)

    # security: revoke all sessions after password change
    revoke_all_for_user(db, current_user.id)
    db.commit()
    return {"status": "ok"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    # ไม่บอกว่ามี user หรือไม่ (กัน enumeration)
    if not user:
        return {"status": "ok"}

    raw_token = secrets.token_urlsafe(32)
    token_hash = _sha256(raw_token)

    expires_at = _now_utc() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    create_reset_token(db, user.id, token_hash, expires_at)

    # DEV MODE: คืน token ให้ทดสอบ (PROD ควรส่ง email อย่างเดียว)
    if settings.ENV == "dev":
        return {"status": "ok", "reset_token": raw_token}

    send_reset_email(user.email, raw_token)
    return {"status": "ok"}


@router.post("/reset-password")
@limiter.limit("5/minutes")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = _sha256(payload.token)
    row = get_reset_by_hash(db, token_hash)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    if row.used_at is not None:
        raise HTTPException(status_code=401, detail="Token already used")
    if row.expires_at.replace(tzinfo=timezone.utc) < _now_utc():
        raise HTTPException(status_code=401, detail="Token expired")

    user = get_user(db, row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()

    mark_used(db, row)

    # security: revoke all sessions after reset
    revoke_all_for_user(db, user.id)
    return {"status": "ok"}
