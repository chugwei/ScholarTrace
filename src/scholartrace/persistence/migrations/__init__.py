"""Programmatic Alembic entry points."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from scholartrace.persistence.database import create_sqlite_engine

INITIAL_REVISION = "0001"
LATEST_REVISION = "0006"


def _configuration(database_path: Path) -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    engine = create_sqlite_engine(database_path)
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    engine.dispose()
    return config


def upgrade_database(database_path: Path, revision: str = "head") -> None:
    """Upgrade a SQLite database to the requested schema revision."""

    command.upgrade(_configuration(database_path), revision)


def downgrade_database(database_path: Path, revision: str = "base") -> None:
    """Downgrade a SQLite database to the requested schema revision."""

    command.downgrade(_configuration(database_path), revision)


def current_revision(database_path: Path) -> str | None:
    """Return the currently applied Alembic revision."""

    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
