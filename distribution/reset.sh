#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# == 0 ]] || fail 'Uso: ./reset.sh'
prepare
printf 'ATENCIÓN: se eliminarán TODOS los datos y archivos de %s.\n' "$RRII_PROJECT"
printf 'Para confirmar escribí ELIMINAR %s: ' "$RRII_PROJECT"
answer=''
if ! IFS= read -r answer || [[ "$answer" != "ELIMINAR $RRII_PROJECT" ]]; then
  printf 'Cancelado. No se borraron datos.\n'
  exit 1
fi
compose down --volumes --remove-orphans
rm -f -- "$RRII_ROOT/.attempted-version"
printf 'Datos eliminados. Configuración conservada. Ejecutá ./start.sh para empezar de nuevo.\n'
