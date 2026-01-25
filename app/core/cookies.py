from fastapi import Response
from app.core.config import settings

def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,     # ตอนนี้คุณตั้ง false แล้วใน local
        samesite=settings.COOKIE_SAMESITE, # lax
        path="/",                          # ✅ กว้างสุด
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/",
    )
