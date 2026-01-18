from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME: str = "auth-service"
    DATABASE_URL: str

    ENV: str = "dev"  # dev|prod

    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # forgot/reset password
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    ENV: str = "dev"

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.JWT_SECRET
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return self.JWT_ALG

settings = Settings()
