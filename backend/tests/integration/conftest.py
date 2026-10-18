from collections.abc import Iterator

import pytest
from sqlalchemy import update

from app.db import models as registered_models  # noqa: F401
from app.db.base import Base
from app.db.engine import engine
from app.modules.assets.models import UNCATEGORIZED_ID, Asset, AssetCategory
from app.modules.options.configuration_models import ProductOption


def clear_test_database() -> None:
    """Limpia sólo datos de la base exclusiva de integración, sin tocar el esquema."""
    if engine.url.database != "rrii_coach_test":
        raise RuntimeError("La integración requiere la base aislada rrii_coach_test")
    with engine.begin() as connection:
        # Romper el enlace circular antes de borrar revisiones en esta base aislada.
        connection.execute(update(Asset).values(current_revision_id=None))
        connection.execute(update(ProductOption).values(context_definition_id=None))
        for table in reversed(Base.metadata.sorted_tables):
            statement = table.delete()
            if table is AssetCategory.__table__:
                # Dato del sistema sembrado por Alembic, no creado por los tests.
                statement = statement.where(table.c.id != UNCATEGORIZED_ID)
            connection.execute(statement)


@pytest.fixture(scope="session", autouse=True)
def isolated_integration_session() -> Iterator[None]:
    # Las fixtures históricas limpian sólo su dominio; pueden dejar referencias
    # desde producción que impiden repetir la suite sobre el mismo esquema.
    clear_test_database()
    yield
    clear_test_database()
