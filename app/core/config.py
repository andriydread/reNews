from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "reNews"
    ENVIRONMENT: str = "development"

    # Database Setup
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Admin Dashboard Security
    JWT_SECRET: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ADMIN_USER: str
    ADMIN_PASS: str

    # AI API key and model
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview"

    # Worker config
    USER_AGENT: str = "reNews-Reader/2.0 (+https://github.com/reNews)"
    MAX_CONTENT_LENGTH: int = 15000  # Limit text sent to AI to save tokens
    WORKER_INTERVAL_MINUTES: int = 30


settings = Settings()
