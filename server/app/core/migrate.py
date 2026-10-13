from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.core.database import Base, engine
from app.models import alert, metric_log, metric_rollup, refresh_token, server, user  # noqa: F401

SERVER_DIR = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "0001"


def alembic_config() -> Config:
    config = Config(str(SERVER_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(SERVER_DIR / "migrations"))
    return config


def adopt_unversioned_database(config: Config) -> None:
    existing = set(sa.inspect(engine).get_table_names())
    if "alembic_version" in existing or not existing & set(Base.metadata.tables):
        return

    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                table.create(connection)
                continue
            present = {c["name"] for c in sa.inspect(connection).get_columns(table.name)}
            for column in table.columns:
                if column.name not in present:
                    operations.add_column(table.name, sa.Column(column.name, column.type, nullable=True))
                    if column.default is not None and column.default.is_scalar:
                        connection.execute(sa.update(table).values({column.name: column.default.arg}))

    command.stamp(config, BASELINE_REVISION)


def run_migrations() -> None:
    config = alembic_config()
    adopt_unversioned_database(config)
    command.upgrade(config, "head")