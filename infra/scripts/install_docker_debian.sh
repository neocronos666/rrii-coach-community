#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /etc/os-release ]]; then
  echo "No se pudo identificar el sistema operativo." >&2
  exit 1
fi

# shellcheck source=/dev/null
source /etc/os-release

if [[ "${ID:-}" != "debian" ]]; then
  echo "Este script admite únicamente Debian. Sistema detectado: ${ID:-desconocido}." >&2
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
elif command -v sudo >/dev/null 2>&1; then
  SUDO=(sudo)
else
  echo "Se requieren privilegios de root o el comando sudo." >&2
  exit 1
fi

echo "Configurando el repositorio APT oficial de Docker para Debian ${VERSION_CODENAME}."

"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y ca-certificates curl
"${SUDO[@]}" install -m 0755 -d /etc/apt/keyrings
"${SUDO[@]}" curl -fsSL \
  "https://download.docker.com/linux/debian/gpg" \
  -o /etc/apt/keyrings/docker.asc
"${SUDO[@]}" chmod a+r /etc/apt/keyrings/docker.asc

ARCHITECTURE="$(dpkg --print-architecture)"
REPOSITORY="Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: ${ARCHITECTURE}
Signed-By: /etc/apt/keyrings/docker.asc"

printf '%s\n' "${REPOSITORY}" \
  | "${SUDO[@]}" tee /etc/apt/sources.list.d/docker.sources >/dev/null

"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

"${SUDO[@]}" systemctl enable --now docker

echo "Docker Engine y el plugin Compose quedaron instalados."

if [[ "${1:-}" == "--add-current-user" ]]; then
  TARGET_USER="${SUDO_USER:-${USER}}"
  "${SUDO[@]}" usermod -aG docker "${TARGET_USER}"
  echo "El usuario ${TARGET_USER} fue agregado al grupo docker."
  echo "Debe cerrar la sesión y abrir una nueva antes de usar Docker sin sudo."
else
  echo "No se modificaron grupos de usuarios."
  echo "Use --add-current-user solo si acepta otorgar acceso equivalente a root."
fi
