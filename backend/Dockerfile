# syntax=docker/dockerfile:1.7
FROM python:3.14.7-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.11.29
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY --chown=app:app . .
RUN mkdir -p /data/assets && chown -R app:app /app /data/assets

USER app

FROM base AS development
RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.14.7-slim-bookworm AS release
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:${PATH}"
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /data/assets && chown app:app /data/assets
WORKDIR /app
COPY --from=base /app/.venv /app/.venv
COPY --from=base --chown=app:app /app/app ./app
COPY --from=base --chown=app:app /app/alembic ./alembic
COPY --from=base --chown=app:app /app/alembic.ini ./alembic.ini
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
