#!/usr/bin/env bash
# Funciones compartidas; ejecutar los scripts up/down/reset, no este archivo.
set -euo pipefail

TEST_ENV_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ENV_PROJECT="rrii-community-test"

test_env_error() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

test_env_init() {
  command -v docker >/dev/null || test_env_error "Falta Docker Engine."
  if [[ -n "${RRII_TEST_COMPOSE_BIN:-}" ]]; then
    TEST_ENV_COMPOSE=("$RRII_TEST_COMPOSE_BIN")
  else
    TEST_ENV_COMPOSE=(docker compose)
  fi
  local version
  version="$("${TEST_ENV_COMPOSE[@]}" version --short 2>/dev/null)" ||
    test_env_error "Se requiere Docker Compose >= 2.20; docker-compose v1 no es compatible."
  version="${version#v}"
  [[ "$version" =~ ^([0-9]+)\.([0-9]+) ]] ||
    test_env_error "No se pudo identificar la versión de Compose."
  if (( BASH_REMATCH[1] < 2 || (BASH_REMATCH[1] == 2 && BASH_REMATCH[2] < 20) )); then
    test_env_error "Se requiere Docker Compose >= 2.20."
  fi
  docker info >/dev/null 2>&1 ||
    test_env_error "Docker no está disponible. Revisá el daemon y los permisos del socket."
  local port
  for port in "${RRII_TEST_BACKEND_PORT:-18000}" "${RRII_TEST_FRONTEND_PORT:-13000}"; do
    [[ "$port" =~ ^[1-9][0-9]{0,4}$ ]] && (( 10#$port <= 65535 )) ||
      test_env_error "Puerto inválido: $port. Usá un entero entre 1 y 65535."
  done
  [[ "${RRII_TEST_BACKEND_PORT:-18000}" != "${RRII_TEST_FRONTEND_PORT:-13000}" ]] ||
    test_env_error "Backend y frontend requieren puertos diferentes."
  TEST_ENV_COMPOSE+=(--project-directory "$TEST_ENV_ROOT" --env-file /dev/null
    --project-name "$TEST_ENV_PROJECT" --file "$TEST_ENV_ROOT/compose.test-env.yaml")
  test_env_compose config --quiet
}

test_env_compose() {
  "${TEST_ENV_COMPOSE[@]}" "$@"
}
