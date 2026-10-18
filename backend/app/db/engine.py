import logging

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.database_echo,
)


def dispose_database_engine() -> None:
    """Libera las conexiones del pool durante un cierre controlado."""

    logger.info("Cerrando el pool de conexiones de PostgreSQL")
    engine.dispose()
