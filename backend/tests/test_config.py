from app.core.config import get_settings


def test_required_configuration_is_loaded() -> None:
    settings = get_settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.asset_storage_path.is_absolute()
    assert settings.cors_origins == ["http://localhost:3000"]
