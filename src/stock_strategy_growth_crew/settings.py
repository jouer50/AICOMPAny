from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Robot Company API"
    app_env: str = "development"
    app_port: int = 8000
    database_url: str = Field(
        default="sqlite:///./robot_company.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    stock_strategy_growth_crew_home: str | None = Field(
        default=None,
        alias="STOCK_STRATEGY_GROWTH_CREW_HOME",
    )


settings = Settings()

