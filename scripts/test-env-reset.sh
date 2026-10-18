#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/test-env-common.sh"
[[ $# == 0 ]] || test_env_error "Uso: $0 (sin argumentos)."
test_env_init
printf 'DESTRUCTIVO: elimina toda la base y los assets de %s.\n' "$TEST_ENV_PROJECT"
printf 'No afecta los volúmenes del Compose de desarrollo.\n'
printf 'Escribí ELIMINAR %s para confirmar: ' "$TEST_ENV_PROJECT"
answer=""
if ! IFS= read -r answer || [[ "$answer" != "ELIMINAR $TEST_ENV_PROJECT" ]]; then
  printf '\nCancelado. No se eliminaron datos.\n' >&2
  exit 1
fi
test_env_compose down --volumes --remove-orphans
printf 'Base y assets de prueba eliminados. El próximo up será una instalación nueva.\n'
