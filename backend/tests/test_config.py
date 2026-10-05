import pytest
from pydantic import ValidationError

from app.config import Settings


def make(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)  # ignore any local .env file


@pytest.mark.parametrize("scheme", ["postgresql://", "postgres://"])
def test_plain_postgres_urls_are_rewritten_for_the_psycopg_driver(scheme):
    settings = make(database_url=f"{scheme}user:pw@host.example/db?sslmode=require")

    assert settings.database_url == "postgresql+psycopg://user:pw@host.example/db?sslmode=require"


def test_urls_that_already_name_a_driver_are_left_alone():
    url = "postgresql+psycopg://user:pw@host/db"

    assert make(database_url=url).database_url == url


def test_production_refuses_the_public_development_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(environment="production")


def test_production_accepts_a_private_secret():
    assert make(environment="production", secret_key="x" * 40).environment == "production"


def test_development_allows_the_default_secret():
    assert make().environment == "development"
