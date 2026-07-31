from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str
    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    invite_expire_days: int = 7
    password_reset_expire_minutes: int = 60

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5174"

    @model_validator(mode="after")
    def check_frontend_url_set_in_production(self) -> "Settings":
        if self.environment == "production" and self.frontend_url == "http://localhost:5174":
            raise ValueError(
                "FRONTEND_URL is unset (defaulting to localhost) while ENVIRONMENT=production. "
                "Set FRONTEND_URL to the deployed frontend URL — invite and password-reset "
                "links are built from it."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
