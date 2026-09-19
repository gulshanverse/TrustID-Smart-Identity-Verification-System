import ast
from pathlib import Path
from typing import cast

from app.core.config import Settings

MIGRATIONS_ENV = Path(__file__).parents[1] / "migrations" / "env.py"
MIGRATIONS_DIR = Path(__file__).parents[1] / "migrations" / "versions"


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


def _literal_assignment(tree: ast.Module, name: str) -> str | tuple[str, ...] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        if not isinstance(target, ast.Name) or target.id != name or node.value is None:
            continue
        value = ast.literal_eval(node.value)
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
            return cast(tuple[str, ...], value)
    raise AssertionError(f"Migration does not define literal {name}: {name}")


def test_alembic_revision_graph_is_valid_and_connected() -> None:
    revisions: dict[str, Path] = {}
    parents: dict[str, tuple[str, ...]] = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _literal_assignment(tree, "revision")
        down_revision = _literal_assignment(tree, "down_revision")
        assert isinstance(revision, str)
        assert len(revision) <= 32, f"{path.name} revision exceeds PostgreSQL alembic_version limit"
        assert revision not in revisions, f"duplicate Alembic revision: {revision}"
        revisions[revision] = path
        if down_revision is None:
            parents[revision] = ()
        elif isinstance(down_revision, str):
            parents[revision] = (down_revision,)
        else:
            parents[revision] = down_revision
        for parent in parents[revision]:
            assert len(parent) <= 32, f"{path.name} down_revision exceeds 32 characters"

    assert revisions, "no Alembic migrations discovered"
    for revision, parent_ids in parents.items():
        for parent in parent_ids:
            assert parent in revisions, f"{revision} references missing down_revision {parent}"

    referenced = {parent for parent_ids in parents.values() for parent in parent_ids}
    heads = set(revisions) - referenced
    assert len(heads) == 1, f"expected one Alembic head, found {sorted(heads)}"

    current = next(iter(heads))
    visited: set[str] = set()
    while current:
        assert current not in visited, f"cycle detected at {current}"
        visited.add(current)
        parent_ids = parents[current]
        assert len(parent_ids) <= 1, "migration graph contains a branch"
        current = parent_ids[0] if parent_ids else ""
    assert visited == set(revisions), f"disconnected migrations: {sorted(set(revisions) - visited)}"
    assert next(iter(heads)) == "015_analysis_processing_time"
