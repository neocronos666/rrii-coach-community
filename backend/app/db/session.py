from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import engine

SessionFactory = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db_session() -> Iterator[Session]:
    """Entrega una sesión por petición y la cierra sin confirmar implícitamente."""

    with SessionFactory() as session:
        yield session
