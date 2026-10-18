#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/test-env-common.sh"
[[ $# == 0 ]] || test_env_error "Uso: $0 (sin argumentos)."
test_env_init

startup_failed() {
  printf '\nNo se pudo completar el arranque. Los datos se conservan.\n' >&2
  test_env_compose ps >&2 || true
  printf 'Diagnóstico: revisar el error anterior; para detener, scripts/test-env-down.sh.\n' >&2
}
trap startup_failed ERR

printf 'Preparando el entorno local %s...\n' "$TEST_ENV_PROJECT"
test_env_compose build backend frontend
test_env_compose up --detach --wait --wait-timeout 180 db
# No esperar readiness del backend antes de instalar el esquema.
# Detener la API propia antes de actualizar una base existente.
test_env_compose stop frontend backend
test_env_compose run --rm --no-deps backend uv run --frozen alembic upgrade head
test_env_compose up --detach --wait --wait-timeout 240 backend frontend
trap - ERR

printf '\nEntorno listo:\n'
printf '  Aplicación: http://localhost:%s\n' "${RRII_TEST_FRONTEND_PORT:-13000}"
printf '  API: http://localhost:%s/api/v1\n' "${RRII_TEST_BACKEND_PORT:-18000}"
printf '  OpenAPI: http://localhost:%s/docs\n' "${RRII_TEST_BACKEND_PORT:-18000}"
printf '  Readiness: http://localhost:%s/ready\n' "${RRII_TEST_BACKEND_PORT:-18000}"
printf 'Detener y conservar datos: scripts/test-env-down.sh\n'
