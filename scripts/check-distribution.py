#!/usr/bin/env python3
"""Probar el artefacto real fuera del checkout, con datos/volúmenes propios."""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    before = set(subprocess.check_output(["docker", "ps", "-q"], text=True).split())
    with tempfile.TemporaryDirectory(prefix="rrii-distribution-test-") as temp:
        temp_root = Path(temp)
        root = temp_root / "rrii-coach-community"
        with tarfile.open(artifact) as archive:
            members = archive.getmembers()
            assert len(members) == 12
            assert all(
                m.isfile() and m.name.startswith("rrii-coach-community/")
                for m in members
            )
            assert all(".." not in Path(m.name).parts for m in members)
            assert not any(m.name.endswith("/.env") for m in members)
            archive.extractall(temp_root, filter="data")

        def run(command: list[str], data: str | None = None, ok: bool = True) -> str:
            result = subprocess.run(
                command,
                cwd=root,
                text=True,
                input=data,
                capture_output=True,
                check=False,
            )
            if ok and result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            if not ok:
                assert result.returncode != 0, command
            return result.stdout + result.stderr

        no_docker = temp_root / "without-docker"
        no_docker.mkdir()
        for name in ("bash", "uname", "dirname", "flock", "ss"):
            executable = shutil.which(name)
            assert executable is not None
            (no_docker / name).symlink_to(executable)
        missing = subprocess.run(
            [str(root / "install.sh")],
            cwd=root,
            env={**os.environ, "PATH": str(no_docker)},
            text=True,
            capture_output=True,
            check=False,
        )
        assert missing.returncode != 0 and "Docker" in missing.stderr
        assert not (root / ".env").exists()
        run(["bash", "-c", 'source "$1/common.sh"; create_config', "_", str(root)])
        config_file = root / ".env"
        assert config_file.stat().st_mode & 0o777 == 0o600
        with socket.socket() as held:
            held.bind(("127.0.0.1", 0))
            held.listen()
            port = held.getsockname()[1]
            config_file.write_text(
                config_file.read_text().replace("RRII_PORT=18080", f"RRII_PORT={port}")
            )
            assert "ocupado" in run(["./install.sh", "--offline"], ok=False)
        config = dict(
            line.split("=", 1)
            for line in config_file.read_text().splitlines()
            if line and not line.startswith("#")
        )
        project = config["RRII_PROJECT"]
        assert project.startswith("rrii-community-") and len(project) == 27
        assert len(config["RRII_DB_PASSWORD"]) == 64
        env = {
            **os.environ,
            **config,
            "RRII_VERSION": (root / "VERSION").read_text().strip(),
        }
        dc = [
            "docker",
            "compose",
            "--env-file",
            str(config_file),
            "-p",
            project,
            "-f",
            str(root / "compose.yaml"),
        ]

        def compose(*command: str) -> str:
            result = subprocess.run(
                dc + list(command), env=env, text=True, capture_output=True, check=False
            )
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout

        base = f"http://localhost:{port}"

        def request(path: str, body: dict | None = None):
            req = urllib.request.Request(
                base + path,
                data=None if body is None else json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                data = response.read()
                return (
                    json.loads(data)
                    if "application/json" in response.headers.get("Content-Type", "")
                    else data
                )

        try:
            # Rechazar configuración como código, sin ejecutarla.
            original = config_file.read_text()
            config_file.write_text(
                original.replace(f"RRII_PORT={port}", "RRII_PORT=$(touch INJECTION)")
            )
            run(["./start.sh"], ok=False)
            assert not (root / "INJECTION").exists()
            config_file.write_text(original)
            print("A/E: instalación limpia y conflicto de puerto…", flush=True)
            run(["./install.sh", "--offline"])
            assert request("/")
            settings = request("/api/v1/settings")
            assert settings
            states = compose("ps", "--format", "{{.Service}} {{.Health}}")
            assert all(
                name + " healthy" in states for name in ("db", "backend", "frontend")
            ), states
            machine = request(
                "/api/v1/machines",
                {
                    "name": "Persistencia paquete",
                    "machine_type": "other",
                    "currency": "ARS",
                    "purchase_price": "123.4567",
                },
            )
            # Archivo real persistente escrito con el UID de la aplicación.
            compose(
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                "from pathlib import Path; import os; assert os.geteuid()==10001; Path('/data/assets/packaging.txt').write_text('archivo de prueba')",
            )
            config_hash = hashlib.sha256(config_file.read_bytes()).hexdigest()
            run(["./start.sh"])
            assert len(compose("ps", "-q").split()) == 3
            print("B: stop/start conserva registro y archivo…", flush=True)
            run(["./stop.sh"])
            assert not compose("ps", "-a", "-q").strip()
            assert len(compose("config", "--volumes").split()) == 2
            run(["./start.sh"])
            assert (
                request("/api/v1/machines/" + machine["id"])["purchase_price"]
                == "123.4567"
            )
            compose(
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                "from pathlib import Path; assert Path('/data/assets/packaging.txt').read_text()=='archivo de prueba'",
            )
            print(
                "D: actualizar desde esquema 0037 en una copia sintética…", flush=True
            )
            compose("stop", "frontend", "backend")
            compose(
                "run",
                "--rm",
                "--no-deps",
                "--pull",
                "never",
                "backend",
                "alembic",
                "downgrade",
                "20260929_0037",
            )
            installed = (root / ".installed-version").read_text().strip()
            candidate = "0.1.0-rc999"
            for component in ("backend", "frontend"):
                run(
                    [
                        "docker",
                        "tag",
                        f"{config['RRII_IMAGE_PREFIX']}-{component}:{installed}",
                        f"{config['RRII_IMAGE_PREFIX']}-{component}:{candidate}",
                    ]
                )
            run(["./update.sh", "--offline", candidate], data="ACTUALIZAR\n")
            env["RRII_VERSION"] = candidate
            assert (root / ".installed-version").read_text().strip() == candidate
            assert (
                request("/api/v1/machines/" + machine["id"])["purchase_price"]
                == "123.4567"
            )
            compose(
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                "from pathlib import Path; assert Path('/data/assets/packaging.txt').read_text()=='archivo de prueba'",
            )
            backups = list((root / "backups").iterdir())
            assert len(backups) == 1
            assert (backups[0] / "database.dump").stat().st_size > 0
            with tarfile.open(backups[0] / "assets.tar.gz") as saved:
                entry = saved.extractfile("./packaging.txt")
                assert entry is not None
                assert entry.read() == b"archivo de prueba"
            # Comprobar restauración real del dump sin tocar la base activa.
            compose(
                "exec", "-T", "db", "createdb", "-U", "rrii_coach", "packaging_restore"
            )
            with (backups[0] / "database.dump").open("rb") as dump:
                restored = subprocess.run(
                    dc
                    + [
                        "exec",
                        "-T",
                        "db",
                        "pg_restore",
                        "--exit-on-error",
                        "-U",
                        "rrii_coach",
                        "-d",
                        "packaging_restore",
                    ],
                    env=env,
                    stdin=dump,
                    capture_output=True,
                    check=False,
                )
            assert restored.returncode == 0, restored.stderr
            assert "20260929_0037" in compose(
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "rrii_coach",
                "-d",
                "packaging_restore",
                "-Atc",
                "SELECT version_num FROM alembic_version",
            )
            print("C: cancelación del reset y reset confirmado…", flush=True)
            (root / ".attempted-version").write_text("0.1.0-rc1000\n")
            run(["./start.sh"], ok=False)
            run(["./reset.sh"], data="NO\n", ok=False)
            assert request("/api/v1/machines/" + machine["id"])
            run(["./reset.sh"], data=f"ELIMINAR {project}\n")
            run(["./start.sh"])
            assert request("/api/v1/machines") == []
            compose(
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                "from pathlib import Path; assert not Path('/data/assets/packaging.txt').exists()",
            )
            assert hashlib.sha256(config_file.read_bytes()).hexdigest() == config_hash
            print(
                "OK A/B/C/D/E. D valida esquema histórico y backups; no existe aún una release binaria anterior distinta.",
                flush=True,
            )
        finally:
            # Únicamente volúmenes nuevos creados por este test.
            run(["./reset.sh"], data=f"ELIMINAR {project}\n")
            after = set(
                subprocess.check_output(["docker", "ps", "-q"], text=True).split()
            )
            assert before <= after, "Se detuvo un contenedor ajeno al test"


if __name__ == "__main__":
    main()
