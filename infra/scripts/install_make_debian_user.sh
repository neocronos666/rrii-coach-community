#!/usr/bin/env bash
set -euo pipefail

if command -v make >/dev/null 2>&1; then
  echo "GNU Make ya está instalado."
  exit 0
fi

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

(
  cd "$work_dir"
  apt-get download make
  package_file="$(find . -maxdepth 1 -name 'make_*.deb' -print -quit)"
  dpkg-deb --extract "$package_file" extracted
  mkdir -p "$HOME/.local/bin"
  install -m 0755 extracted/usr/bin/make "$HOME/.local/bin/make"
)

echo "GNU Make se instaló en $HOME/.local/bin/make."
echo "Agregar temporalmente la ruta con:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
