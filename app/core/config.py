# app/core/config.py
import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = os.getenv("ENV_FILE", ".env")


class Settings(BaseSettings):
    APP_NAME: str = "auth-service"

    # dev|prod
    ENV: str = "dev"
    LOCAL_PROD: bool = False  # prod แต่รัน local http

    # ---- Security headers flags ----
    SECURE_HEADERS: bool = True
    ENABLE_HSTS: bool = False  # เปิดเฉพาะ prod https จริง

    # ---- Docs ----
    DOCS_ENABLED: bool = False
    DOCS_KEY: Optional[str] = None

    # ---- CORS / hosts ----
    ALLOWED_ORIGINS: str = ""  # comma-separated
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_STRICT_IN_PROD: bool = True
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    # ---- cookies ----
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"  # lax|strict|none
    COOKIE_DOMAIN: str = ""

    # ---- Database ----
    DATABASE_URL: str

    # ---- JWT ----
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"  # ให้ใช้ชื่อนี้เป็นหลัก

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # ---- Rate limit ----
    RATE_LIMIT_ENABLED: bool = True

    # ---- SMTP (prod only) ----
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    FRONTEND_RESET_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in ("dev", "prod"):
            raise ValueError("ENV must be 'dev' or 'prod'")
        return v

    # รองรับ env เก่า JWT_ALG -> map ไป JWT_ALGORITHM
    @field_validator("JWT_ALGORITHM", mode="before")
    @classmethod
    def compat_jwt_alg(cls, v):
        return v or os.getenv("JWT_ALG") or "HS256"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [x.strip() for x in (self.ALLOWED_ORIGINS or "").split(",") if x.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in (self.ALLOWED_HOSTS or "").split(",") if h.strip()]


settings = Settings()

# ---- prod hardening (prod จริง) ----
if settings.ENV == "prod" and not settings.LOCAL_PROD:
    settings = settings.model_copy(update={
        "COOKIE_SECURE": True,
        "SECURE_HEADERS": True,
        "CORS_STRICT_IN_PROD": True,
        "RATE_LIMIT_ENABLED": True,
        # ENABLE_HSTS ให้เปิดเองเฉพาะ https จริง
        # "ENABLE_HSTS": True,
    })

    # ถ้าเปิด docs ใน prod ต้องมี key
    if settings.DOCS_ENABLED and not settings.DOCS_KEY:
        raise RuntimeError("DOCS_ENABLED=true in prod but DOCS_KEY is missing")
