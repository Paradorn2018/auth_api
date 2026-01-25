import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List

ENV_FILE = os.getenv("ENV_FILE", ".env")  # default เผื่อรัน local

class Settings(BaseSettings):
    APP_NAME: str = "auth-service"
    DATABASE_URL: str = Field(...)

    ENV: str = "dev"  # dev|prod

    JWT_SECRET: str = Field(..., min_length=32)

    JWT_ALGORITHM: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    JWT_ALG: str = Field(default="HS256", validation_alias="JWT_ALG")

    def __init__(self, **values):
        super().__init__(**values)
        if getattr(self, "JWT_ALGORITHM", None) and not getattr(self, "JWT_ALG", None):
            object.__setattr__(self, "JWT_ALG", self.JWT_ALGORITHM)
        if getattr(self, "JWT_ALG", None) and not getattr(self, "JWT_ALGORITHM", None):
            object.__setattr__(self, "JWT_ALGORITHM", self.JWT_ALG)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # เพิ่ม flags ที่จะคุม behavior dev/prod
    RATE_LIMIT_ENABLED: bool = True
    DOCS_ENABLED: bool = False          # prod ปิด
    SECURE_HEADERS: bool = True        # prod เปิด
    ALLOWED_ORIGINS: str = ""
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    COOKIE_SECURE: bool = False      # prod จะ override เป็น true
    COOKIE_SAMESITE: str = "lax"     # "lax" ดีสำหรับ auth ทั่วไป
    COOKIE_DOMAIN: str = ""          # optional

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    FRONTEND_RESET_URL: str | None = None

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

    @property
    def ALLOWED_ORIGINS_LIST(self):
        return [x.strip() for x in self.ALLOWED_ORIGINS.split(",") if x.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

settings = Settings()
