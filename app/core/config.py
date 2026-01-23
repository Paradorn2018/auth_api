from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    APP_NAME: str = "auth-service"
    DATABASE_URL: str = Field(..., description="SQLAlchemy database url")

    ENV: str = "dev"  # dev|prod

    # ✅ ห้ามมี default ในโค้ด (กันเผลอขึ้น prod ด้วยค่าเดาๆ)
    JWT_SECRET: str = Field(..., min_length=32)
    JWT_ALG: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
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

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters (use a long random secret)")
        if v.lower() in {"change-me", "colorful", "secret", "password", "123456"}:
            raise ValueError("JWT_SECRET looks like a placeholder/weak secret")
        return v

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.JWT_SECRET

    @property
    def JWT_ALGORITHM(self) -> str:
        return self.JWT_ALG


settings = Settings()
