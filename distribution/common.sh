#!/usr/bin/env bash
# Funciones del paquete; no ejecutar directamente ni cargar .env como código.
set -Eeuo pipefail
umask 077
RRII_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
valid_version() { [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9][a-zA-Z0-9.-]*)?$ ]]; }
platform_check() {
  [[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || fail 'Esta candidata admite únicamente Linux de 64 bits (amd64).'
  command -v flock >/dev/null || fail 'Falta flock (paquete util-linux).'
  command -v ss >/dev/null || fail 'Falta ss (paquete iproute2); consultar README-INSTALL.txt.'
  if ! command -v docker >/dev/null; then
    printf 'RRII-Coach necesita Docker para ejecutar sus servicios. No se modificó el sistema.\n' >&2
    # /etc/os-release es configuración del sistema, nunca contenido del paquete.
    local ID=unknown
    # shellcheck source=/dev/null
    [[ ! -r /etc/os-release ]] || source /etc/os-release
    case "$ID" in
      debian) printf 'Debian: https://docs.docker.com/engine/install/debian/\n' >&2 ;;
      ubuntu|linuxmint) printf 'Ubuntu/Mint: https://docs.docker.com/engine/install/ubuntu/\nMint requiere revisar la base Ubuntu; ver README-INSTALL.txt.\n' >&2 ;;
      *) printf 'Sistema detectado: %s. Esta candidata se orienta a Debian, Ubuntu y Mint.\n' "$ID" >&2 ;;
    esac
    fail 'Instalá Docker Engine y su plugin Compose con ayuda de un administrador, y repetí install.sh.'
  fi
  local compose_version
  compose_version="$(docker compose version --short 2>/dev/null)" || fail 'Falta Docker Compose moderno (plugin >= 2.20).'
  compose_version="${compose_version#v}"
  [[ "$compose_version" =~ ^([0-9]+)\.([0-9]+) ]] || fail 'No se pudo verificar Docker Compose.'
  (( BASH_REMATCH[1] > 2 || (BASH_REMATCH[1] == 2 && BASH_REMATCH[2] >= 20) )) || fail 'Se necesita Compose >= 2.20.'
  docker info >/dev/null 2>&1 || fail 'Docker no responde o no tenés permisos. Pedí revisar el servicio y el acceso; no cambies permisos del socket.'
  local endpoint="${DOCKER_HOST:-}"
  [[ -n "$endpoint" ]] || endpoint="$(docker context inspect --format '{{.Endpoints.docker.Host}}')"
  [[ "$endpoint" == unix://* ]] || fail 'Usá un Docker local con socket Unix; este paquete no administra servidores remotos.'
}
lock_installation() {
  exec 9>"$RRII_ROOT/.operation.lock"
  flock -n 9 || fail 'Ya hay otra operación de RRII-Coach en esta carpeta.'
}
create_config() {
  [[ ! -L "$RRII_ROOT/.env" ]] || fail '.env no puede ser un enlace simbólico.'
  [[ ! -e "$RRII_ROOT/.env" ]] || return 0
  local suffix password
  suffix="$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')"
  password="$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  sed -e "s/RRII_PROJECT=GENERATED/RRII_PROJECT=rrii-community-$suffix/" \
      -e "s/RRII_DB_PASSWORD=GENERATED/RRII_DB_PASSWORD=$password/" \
      "$RRII_ROOT/.env.example" >"$RRII_ROOT/.env"
  chmod 600 "$RRII_ROOT/.env"
}
read_config() {
  [[ -f "$RRII_ROOT/.env" && ! -L "$RRII_ROOT/.env" ]] || fail 'Primero ejecutá ./install.sh.'
  chmod 600 "$RRII_ROOT/.env"
  local key value
  RRII_PROJECT='' RRII_PORT='' RRII_DB_PASSWORD='' RRII_IMAGE_PREFIX=''
  while IFS='=' read -r key value || [[ -n "$key" ]]; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    case "$key" in
      RRII_PROJECT) RRII_PROJECT="$value" ;;
      RRII_PORT) RRII_PORT="$value" ;;
      RRII_DB_PASSWORD) RRII_DB_PASSWORD="$value" ;;
      RRII_IMAGE_PREFIX) RRII_IMAGE_PREFIX="$value" ;;
      *) fail 'La configuración contiene una variable desconocida; revisar .env.' ;;
    esac
  done <"$RRII_ROOT/.env"
  [[ "$RRII_PROJECT" =~ ^rrii-community-[a-f0-9]{12}$ ]] || fail 'Nombre de instalación inválido.'
  if [[ ! "$RRII_PORT" =~ ^[1-9][0-9]{0,4}$ ]] || (( 10#$RRII_PORT > 65535 )); then
    fail 'RRII_PORT debe ser un puerto entre 1 y 65535.'
  fi
  [[ "$RRII_DB_PASSWORD" =~ ^[a-f0-9]{64}$ ]] || fail 'Contraseña local inválida; no cambiarla después de crear datos.'
  [[ "$RRII_IMAGE_PREFIX" =~ ^[a-z0-9][a-z0-9./_-]+$ ]] || fail 'Prefijo de imágenes inválido.'
  RRII_VERSION="$(cat "$RRII_ROOT/VERSION")"
  [[ ! -f "$RRII_ROOT/.installed-version" ]] || RRII_VERSION="$(cat "$RRII_ROOT/.installed-version")"
  valid_version "$RRII_VERSION" || fail 'Versión inválida.'
  export RRII_PROJECT RRII_PORT RRII_DB_PASSWORD RRII_IMAGE_PREFIX RRII_VERSION
  COMPOSE=(docker compose --project-directory "$RRII_ROOT" --env-file "$RRII_ROOT/.env" -p "$RRII_PROJECT" -f "$RRII_ROOT/compose.yaml")
  compose config --quiet
}
compose() { "${COMPOSE[@]}" "$@"; }
check_port() {
  local own
  own="$(compose ps --status running -q frontend)"
  if [[ -n "$own" ]]; then
    local actual
    actual="$(docker inspect --format '{{(index (index .NetworkSettings.Ports "3000/tcp") 0).HostPort}}' "$own")"
    [[ "$actual" != "$RRII_PORT" ]] || return 0
  fi
  [[ -z "$(ss -H -ltn "sport = :$RRII_PORT")" ]] || fail "El puerto $RRII_PORT está ocupado. Cambiá RRII_PORT en .env por uno libre y repetí."
}
operation_error() {
  local result=$?
  trap - ERR
  printf '\nNo se completó la operación. Se conservaron configuración y datos.\n' >&2
  printf 'Revisá el mensaje anterior. Diagnóstico: ./status.sh\n' >&2
  exit "$result"
}
prepare() {
  platform_check
  lock_installation
  read_config
  trap operation_error ERR
}
start_services() {
  if [[ -f "$RRII_ROOT/.attempted-version" ]]; then
    [[ "$(cat "$RRII_ROOT/.attempted-version")" == "$RRII_VERSION" ]] ||
      fail 'Hay una actualización incompleta. Consultá status.sh y repetí update.sh con la versión intentada; no se hará downgrade automático.'
  fi
  check_port
  compose up -d --pull never --wait --wait-timeout 180 db
  compose stop frontend backend
  printf 'Preparando datos de RRII-Coach…\n'
  compose run --rm --no-deps --pull never backend alembic upgrade head
  compose up -d --pull never --wait --wait-timeout 240 backend frontend
  printf '%s\n' "$RRII_VERSION" >"$RRII_ROOT/.installed-version.new"
  mv -- "$RRII_ROOT/.installed-version.new" "$RRII_ROOT/.installed-version"
  printf '\nRRII-Coach %s listo: http://localhost:%s\n' "$RRII_VERSION" "$RRII_PORT"
  printf 'Para terminar y liberar memoria: ./stop.sh\n'
}
