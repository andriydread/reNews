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

    # AI config (claude CLI, subscription auth on the host)
    CLAUDE_BIN: str = "claude"
    AI_MODEL: str = "haiku"
    AI_BATCH_SIZE: int = 10
    AI_TIMEOUT_SECONDS: int = 300

    # Worker config (cadence lives in deploy/renews-worker.timer)
    USER_AGENT: str = "reNews-Reader/2.0 (+https://github.com/reNews)"
    MAX_CONTENT_LENGTH: int = 15000  # Limit text sent to AI to save tokens


settings = Settings()
