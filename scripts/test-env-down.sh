#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/test-env-common.sh"
[[ $# == 0 ]] || test_env_error "Uso: $0 (sin argumentos)."
test_env_init
test_env_compose down --remove-orphans
printf 'Entorno detenido y contenedores eliminados. Base y assets conservados.\n'
