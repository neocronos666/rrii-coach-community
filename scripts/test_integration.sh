#!/bin/sh
set -eu

compose="docker compose"
test_url="postgresql+psycopg://rrii_coach_test:test_only@db_test:5432/rrii_coach_test"

cleanup() {
  $compose exec -T -e DATABASE_URL="$test_url" backend \
    uv run alembic downgrade base >/dev/null 2>&1 || true
  $compose --profile test stop db_test >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "Iniciando PostgreSQL aislado para pruebas de integración..."
$compose --profile test up -d --wait db_test
$compose exec -T -e DATABASE_URL="$test_url" backend uv run alembic upgrade head
$compose exec -T -e DATABASE_URL="$test_url" backend \
  uv run pytest -m integration
