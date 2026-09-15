from pathlib import Path

from app.core.config import Settings

MIGRATIONS_ENV = Path(__file__).parents[1] / "migrations" / "env.py"


def test_alembic_environment_uses_application_database_setting() -> None:
    source = MIGRATIONS_ENV.read_text(encoding="utf-8")

    assert "from app.core.config import get_settings" in source
    assert "database_url = get_settings().database_url" in source
    assert 'config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))' in source


def test_database_url_can_be_overridden_by_environment(monkeypatch) -> None:
    production_url = "postgresql+psycopg://demo:demo@db.example.test:5432/trustid"
    monkeypatch.setenv("DATABASE_URL", production_url)

    settings = Settings()

    assert settings.database_url == production_url
    assert "localhost" not in settings.database_url
