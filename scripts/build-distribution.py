#!/usr/bin/env python3
"""Construir un paquete cerrado para testers; nunca publica imágenes."""

import argparse
import gzip
import hashlib
import io
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "install.sh",
    "start.sh",
    "stop.sh",
    "reset.sh",
    "update.sh",
    "status.sh",
    "common.sh",
    "compose.yaml",
    ".env.example",
    "VERSION",
    "README-INSTALL.txt",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", default=(ROOT / "distribution/VERSION").read_text().strip()
    )
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--build-images", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9][a-zA-Z0-9.-]*)?", args.version
    ):
        parser.error("La versión debe ser explícita; latest no es válido.")
    if (ROOT / "LICENSE").is_symlink():
        parser.error("LICENSE no puede ser un enlace simbólico.")
    if not (ROOT / "LICENSE").read_text().strip():
        parser.error("LICENSE no puede estar vacío.")
    for name in FILES:
        path = ROOT / "distribution" / name
        if path.is_symlink() or not path.is_file():
            parser.error("Archivo de distribución inválido: " + name)
    if args.build_images:
        # El modo offline del paquete también necesita la imagen de la base.
        compose_text = (ROOT / "distribution/compose.yaml").read_text()
        postgres = re.search(r"image: (postgres:[^\s]+)", compose_text)
        if postgres is None:
            parser.error("No se encontró la imagen versionada de PostgreSQL.")
        subprocess.run(["docker", "pull", postgres.group(1)], check=True)
        for component in ("backend", "frontend"):
            subprocess.run(
                [
                    "docker",
                    "build",
                    "--target",
                    "release",
                    "-t",
                    f"ghcr.io/neocronos666/rrii-coach-community-{component}:{args.version}",
                    str(ROOT / component),
                ],
                check=True,
            )
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as archive:
        for name in (*FILES, "LICENSE"):
            path = ROOT / ("LICENSE" if name == "LICENSE" else "distribution/" + name)
            data = (
                (args.version + "\n").encode()
                if name == "VERSION"
                else path.read_bytes()
            )
            info = tarfile.TarInfo("rrii-coach-community/" + name)
            info.size = len(data)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"rrii-coach-community-{args.version}-linux-amd64.tar.gz"
    with (
        target.open("wb") as output,
        gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as zipped,
    ):
        zipped.write(payload.getvalue())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n"
    )
    print(target)
    print("Paquete generado. No se publicó ninguna imagen, tag ni Release.")


if __name__ == "__main__":
    main()
