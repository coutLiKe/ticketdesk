from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, read from environment variables (and a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TicketDesk"
    # "production" turns on safety checks (see check_production_secret below).
    environment: str = "development"
    # Browser origins allowed to call the API from another domain, comma-separated,
    # e.g. "https://ticketdesk.pages.dev". Empty means no cross-origin access (local dev
    # doesn't need it because the Vite dev server proxies /api).
    cors_origins: str = ""
    # Default points at the Postgres container's published port, so running tools
    # (alembic, pytest) on your Mac works. Inside Compose, DATABASE_URL overrides it.
    database_url: str = "postgresql+psycopg://ticketdesk:ticketdesk@localhost:5432/ticketdesk"

    # Signs JWTs. Anyone who knows it can forge a login, so any real deployment MUST set
    # its own long random value (e.g. `openssl rand -hex 32`). This default is dev-only.
    secret_key: str = "dev-only-secret-change-me-this-is-not-for-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # bcrypt work factor: each +1 doubles hashing time. 12 is a sensible production value;
    # tests lower it so creating users stays fast.
    bcrypt_rounds: int = 12

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Hosts like Neon hand out `postgresql://...` URLs. SQLAlchemy needs to be told
        which driver to use, so rewrite the scheme to `postgresql+psycopg://`."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def check_production_secret(self) -> "Settings":
        """Refuse to start in production with the publicly known development secret,
        because anyone could then forge login tokens."""
        if self.environment == "production" and self.secret_key.startswith("dev-only"):
            raise ValueError(
                "SECRET_KEY must be set to a private value when ENVIRONMENT=production"
            )
        return self


settings = Settings()
