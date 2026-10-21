#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# == 0 ]] || fail 'Uso: ./status.sh'
prepare
printf 'Instalación %s, versión %s, URL http://localhost:%s\n' "$RRII_PROJECT" "$RRII_VERSION" "$RRII_PORT"
if [[ -f "$RRII_ROOT/.attempted-version" ]]; then
  printf 'Última versión intentada: %s\n' "$(cat "$RRII_ROOT/.attempted-version")"
fi
compose ps -a
compose logs --no-color --tail 60
