from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.engine import engine
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="rrii-coach-backend")


def get_database_revisions() -> tuple[set[str], set[str]]:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(backend_root / "alembic.ini")
    alembic_config.set_main_option(
        "script_location",
        str(backend_root / "alembic"),
    )
    expected_revisions = set(ScriptDirectory.from_config(alembic_config).get_heads())

    with engine.connect() as connection:
        current_revisions = set(
            MigrationContext.configure(connection).get_current_heads()
        )

    return current_revisions, expected_revisions


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def readiness(response: Response) -> ReadinessResponse:
    try:
        current_revisions, expected_revisions = get_database_revisions()
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            database="unavailable",
            schema_status="unknown",
        )

    if current_revisions != expected_revisions:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            database="ok",
            schema_status="outdated",
        )

    return ReadinessResponse(
        status="ready",
        database="ok",
        schema_status="current",
    )
