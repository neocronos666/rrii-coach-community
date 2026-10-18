import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.db.engine import dispose_database_engine

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Iniciando RRII-Coach Community")
    yield
    dispose_database_engine()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de infraestructura inicial de RRII-Coach Community.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Accept", "Content-Type"],
)

app.include_router(health_router)
app.include_router(api_v1_router, prefix="/api/v1")
