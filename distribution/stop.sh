#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# == 0 ]] || fail 'Uso: ./stop.sh'
prepare
compose down --remove-orphans
printf 'RRII-Coach detenido. Sus procesos ya no ocupan RAM; datos y configuración conservados.\n'
