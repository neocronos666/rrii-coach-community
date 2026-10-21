#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# == 0 ]] || fail 'Uso: ./start.sh'
prepare
if [[ -f "$RRII_ROOT/.attempted-version" ]]; then
  [[ "$(cat "$RRII_ROOT/.attempted-version")" == "$RRII_VERSION" ]] || fail 'Actualización incompleta: revisá status.sh y repetí update.sh con la versión intentada.'
fi
# Si ya está iniciado, comprobar salud sin detenerlo ni duplicar servicios.
if [[ "$(compose ps --status running --services | sort | tr '\n' ' ')" == 'backend db frontend ' ]]; then
  check_port
  compose up -d --pull never --wait --wait-timeout 240
  printf 'RRII-Coach ya está iniciado: http://localhost:%s\n' "$RRII_PORT"
else
  start_services
fi
