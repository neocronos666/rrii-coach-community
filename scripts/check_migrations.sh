#!/bin/sh
set -eu

compose="docker compose"
test_url="postgresql+psycopg://rrii_coach_test:test_only@db_test:5432/rrii_coach_test"

cleanup() {
  $compose --profile test stop db_test >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "Verificando upgrade, downgrade y reaplicación en PostgreSQL aislado..."
$compose --profile test up -d --wait db_test
$compose exec -T -e DATABASE_URL="$test_url" backend uv run alembic upgrade head
$compose exec -T -e DATABASE_URL="$test_url" backend uv run alembic downgrade base
$compose exec -T -e DATABASE_URL="$test_url" backend uv run alembic upgrade head
$compose exec -T -e DATABASE_URL="$test_url" backend uv run alembic check
