"""Central config. Secrets only from .env, never hardcoded.

SECRET_KEY is mandatory and must be long: on a default/placeholder or short key
the backend refuses to start (fail-fast), so a weak key never reaches production.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known weak placeholders that must never be accepted as a real secret.
_WEAK_SECRETS = {
    "change-me-in-prod-min-32-chars",
    "dev-only-change-me",
    "change-me",
    "secret",
    "changeme",
}
_MIN_SECRET_LEN = 32


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-only-change-me"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./yolguard.db"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = ""  # override AI model chain; empty = default fallback chain
    # MongoDB (document store for AI/CV results, processing history). Empty = disabled,
    # SQL remains fully functional as the source of truth.
    MONGODB_URI: str = ""
    MONGODB_DB: str = "yolguard"
    # Local file storage dir for photos/video/audio (metadata in SQL + Mongo).
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOADS_PER_INCIDENT: int = 30
    # Explicit allow-list of browser origins (comma-separated in .env). Never "*".
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_must_be_strong(cls, v: str) -> str:
        if v.strip().lower() in _WEAK_SECRETS or len(v) < _MIN_SECRET_LEN:
            raise ValueError(
                "SECRET_KEY is missing, default, or too short "
                f"(need >= {_MIN_SECRET_LEN} chars, not a placeholder). "
                "Set a strong SECRET_KEY in backend/.env, e.g.: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
