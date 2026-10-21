#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
offline=false
if [[ "${1:-}" == --offline ]]; then offline=true; shift; fi
[[ $# -le 1 ]] || fail 'Uso: ./update.sh [--offline] [versión]'
prepare
[[ -f "$RRII_ROOT/.installed-version" ]] || fail 'Primero instalá RRII-Coach.'
previous="$RRII_VERSION"
next="${1:-$(cat "$RRII_ROOT/VERSION")}"
valid_version "$next" || fail 'Indicá una versión explícita, por ejemplo 0.1.0-rc2; no latest.'
[[ "$next" != "$previous" ]] || { printf 'Ya está instalada la versión %s.\n' "$previous"; exit 0; }
printf 'Actualizar %s → %s. No hay rollback automático del esquema.\n' "$previous" "$next"
printf '¿Continuar? Escribí ACTUALIZAR: '
answer=''
IFS= read -r answer || fail 'Actualización cancelada.'
[[ "$answer" == ACTUALIZAR ]] || fail 'Actualización cancelada.'
RRII_VERSION="$next"
export RRII_VERSION
if [[ "$offline" == false ]]; then compose pull; fi
check_port
compose up -d --pull never --wait --wait-timeout 180 db
compose stop frontend backend
backup="$RRII_ROOT/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$backup"
chmod 700 "$RRII_ROOT/backups" "$backup"
printf '%s\n' "$previous" >"$backup/previous-version"
printf '%s\n' "$next" >"$backup/attempted-version"
printf 'Guardando respaldo antes de migrar…\n'
compose exec -T db pg_dump -U rrii_coach -d rrii_coach -Fc >"$backup/database.dump"
# Respaldar assets con la imagen instalada, antes de migrar a la nueva.
RRII_VERSION="$previous" compose run --rm --no-deps --pull never --entrypoint tar backend -C /data/assets -czf - . >"$backup/assets.tar.gz"
printf '%s\n' "$previous" >"$RRII_ROOT/.previous-version"
printf '%s\n' "$next" >"$RRII_ROOT/.attempted-version"
start_services
printf 'Actualización completada: %s → %s. Respaldo privado: %s\n' "$previous" "$next" "$backup"
