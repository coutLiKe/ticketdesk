from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, read from environment variables (and a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TicketDesk"
    # Default points at the Postgres container's published port, so running tools
    # (alembic, pytest) on your Mac works. Inside Compose, DATABASE_URL overrides it.
    database_url: str = "postgresql+psycopg://ticketdesk:ticketdesk@localhost:5432/ticketdesk"


settings = Settings()
