import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_requires_psycopg_3() -> None:
    with pytest.raises(ValidationError, match="psycopg 3"):
        Settings(database_url="sqlite:///temporary.db")


def test_sql_logging_is_disabled_by_default() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:password@db/example")

    assert settings.database_echo is False
