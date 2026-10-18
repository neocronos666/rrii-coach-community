#!/usr/bin/env bash
set -euo pipefail

CHECK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 0 ]] || { printf 'Uso: %s (sin argumentos).\n' "$0" >&2; exit 1; }
command -v docker >/dev/null || { printf 'Falta Docker Engine.\n' >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { printf 'Falta Docker Compose moderno.\n' >&2; exit 1; }
docker info >/dev/null 2>&1 || { printf 'Docker no está disponible; revisar daemon y permisos.\n' >&2; exit 1; }

export RRII_CHECK_RUN_ID="$(date -u +%Y%m%d%H%M%S)-$$"
CHECK_PROJECT="rrii-community-check-$RRII_CHECK_RUN_ID"
CHECK_REPORTS="$CHECK_ROOT/reports/checks/$RRII_CHECK_RUN_ID"
mkdir -p "$CHECK_REPORTS/backend" "$CHECK_REPORTS/frontend"
CHECK_COMPOSE=(docker compose --project-directory "$CHECK_ROOT" --env-file /dev/null
  --project-name "$CHECK_PROJECT" --file "$CHECK_ROOT/compose.check.yaml")

check_compose() { "${CHECK_COMPOSE[@]}" "$@"; }

cleanup() {
  local result=$?
  trap - EXIT
  set +e
  check_compose logs --no-color >"$CHECK_REPORTS/containers.log" 2>&1
  check_compose cp backend:/tmp/check-reports/. "$CHECK_REPORTS/backend" >/dev/null 2>&1
  check_compose cp frontend:/tmp/check-reports/. "$CHECK_REPORTS/frontend" >/dev/null 2>&1
  check_compose cp frontend:/app/test-results/. "$CHECK_REPORTS/frontend/screenshots" >/dev/null 2>&1
  if ! check_compose down --remove-orphans; then
    printf 'No se pudo retirar el proyecto %s; revisar Docker.\n' "$CHECK_PROJECT" >&2
    result=1
  fi
  printf '%s\n' "$result" >"$CHECK_REPORTS/exit-code.txt"
  printf '\nResultado: %s. Informes: %s\n' "$result" "$CHECK_REPORTS"
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

check_compose config --quiet
printf 'Construyendo herramientas aisladas (%s)...\n' "$CHECK_PROJECT"
check_compose build backend frontend
check_compose up --detach --wait --wait-timeout 180 db db_e2e backend frontend
check_compose exec -T backend mkdir -p /tmp/check-reports
check_compose exec -T frontend mkdir -p /tmp/check-reports

printf '\nAlembic: instalación vacía, reversión y reaplicación...\n'
check_compose exec -T backend uv run --frozen alembic upgrade head
check_compose exec -T backend uv run --frozen alembic downgrade base
check_compose exec -T backend uv run --frozen alembic upgrade head
check_compose exec -T backend uv run --frozen alembic check

printf '\nBackend: lint, formato, tipos y suite completa PostgreSQL...\n'
check_compose exec -T backend uv run --frozen ruff check .
check_compose exec -T backend uv run --frozen ruff format --check .
check_compose exec -T backend uv run --frozen mypy app tests
check_compose exec -T backend uv run --frozen pytest -q --junitxml=/tmp/check-reports/backend.xml
check_compose exec -T backend python -c 'import xml.etree.ElementTree as E; r=E.parse("/tmp/check-reports/backend.xml"); cases=r.findall(".//testcase"); assert cases and not r.findall(".//skipped"), "Suite vacía o con pruebas omitidas"'
check_compose exec -T backend uv run --frozen alembic current
check_compose exec -T backend uv run --frozen alembic check
check_compose exec -T backend uv run --frozen python -c 'import json,sys; from app.main import app; assert json.load(sys.stdin)==app.openapi(), "OpenAPI versionado difiere del backend"' <"$CHECK_ROOT/frontend/openapi.json"

printf '\nFrontend: unitarias, lint/typecheck y build...\n'
check_compose exec -T frontend pnpm exec vitest run --reporter=default --reporter=junit --outputFile=/tmp/check-reports/frontend.xml
check_compose exec -T frontend node -e 'const s=require("node:fs").readFileSync("/tmp/check-reports/frontend.xml","utf8"); if (!/<testcase[\s>]/.test(s) || /<skipped[\s/>]/.test(s)) throw Error("Suite vacía o con pruebas omitidas")'
check_compose exec -T frontend pnpm lint
check_compose exec -T frontend pnpm build

printf '\nE2E: API y PostgreSQL separados de integración; Chromium y navegación táctil...\n'
check_compose run --rm --no-deps api uv run --frozen alembic upgrade head
check_compose up --detach --wait --wait-timeout 180 api
check_compose exec -T frontend pnpm exec playwright test --reporter=list,json --fail-on-flaky-tests --output=/tmp/check-reports/browser
check_compose exec -T frontend node -e 'const r=require("/tmp/check-reports/e2e.json"); if (!r.stats.expected || r.stats.skipped || r.stats.unexpected || r.stats.flaky) throw Error("E2E incompleto o inestable"); console.log(JSON.stringify(r.stats))'
printf '\nTodas las verificaciones automatizadas aprobaron. No reemplazan la prueba humana.\n'
