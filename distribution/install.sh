#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
offline=false
case "${1:-}" in
  '') [[ $# == 0 ]] || fail 'Uso: ./install.sh [--offline]' ;;
  --offline) [[ $# == 1 ]] || fail 'Uso: ./install.sh [--offline]'; offline=true ;;
  --demo) fail 'Los datos demo están en preparación. Esta instalación crea una base vacía.' ;;
  *) fail 'Uso: ./install.sh [--offline]' ;;
esac
platform_check
lock_installation
create_config
read_config
trap operation_error ERR
check_port
if [[ "$offline" == false ]]; then
  printf 'Descargando RRII-Coach %s…\n' "$RRII_VERSION"
  compose pull
else
  printf 'Modo local: se usarán imágenes ya presentes. No se compila ni descarga.\n'
fi
start_services
