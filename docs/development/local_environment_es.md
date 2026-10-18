# Entorno local de desarrollo

Para probar la aplicación en una PC, iniciar y detener todos sus procesos sin
perder datos, usar el [entorno de prueba humana](human_test_environment_es.md).
El flujo siguiente corresponde al Compose de desarrollo histórico.

## Requisitos

- VM Debian vigente.
- Docker Engine.
- Plugin Docker Compose.
- GNU Make para los comandos abreviados de desarrollo.

No se requieren Python, Node.js, pnpm, uv ni PostgreSQL instalados en la VM.

Si GNU Make no está instalado y no se dispone de acceso administrativo, puede
instalarse desde el paquete oficial de Debian en el directorio del usuario:

```bash
./infra/scripts/install_make_debian_user.sh
export PATH="$HOME/.local/bin:$PATH"
```

El script no modifica Python ni los paquetes del sistema.

## Instalar Docker en Debian

El script usa el repositorio APT oficial y es idempotente:

```bash
sudo ./infra/scripts/install_docker_debian.sh
```

Para agregar de forma explícita el usuario invocante al grupo `docker`:

```bash
sudo ./infra/scripts/install_docker_debian.sh --add-current-user
```

Pertenecer al grupo `docker` concede privilegios equivalentes a root. Después
de agregar el usuario se debe cerrar la sesión y abrir una nueva.

## Primer arranque

```bash
cp .env.example .env
```

Editar `POSTGRES_PASSWORD` antes de continuar. Luego:

```bash
docker compose up --build
```

Servicios:

- frontend: <http://localhost:3000>
- backend: <http://localhost:8000>
- documentación OpenAPI: <http://localhost:8000/docs>
- salud: <http://localhost:8000/health>
- salud v1: <http://localhost:8000/api/v1/health>
- readiness: <http://localhost:8000/ready>

## Comandos

```bash
make up
make down
make build
make logs
make ps
make backend-shell
make frontend-shell
make db-shell
make migrate
make db-upgrade
make db-current
make db-history
make db-check
make test-integration
make test
make lint
make typecheck
make format
make openapi
make clean
```

`make clean` conserva datos. `make destroy` elimina contenedores y volúmenes
solo después de escribir `ELIMINAR`.

## Migraciones

La primera migración crea únicamente `system_settings`, una tabla técnica no
comercial para comprobar la infraestructura. Los comandos, confirmaciones y la
base PostgreSQL aislada se documentan en
[`database_es.md`](database_es.md).

Las migraciones son explícitas. Antes de esperar que el backend quede ready en
una base nueva o desactualizada, ejecutar:

```bash
make db-upgrade
docker compose up -d
```

`/health` informa liveness del proceso; `/ready` devuelve error mientras
PostgreSQL no esté disponible o `alembic_version` no coincida con el head.

## OpenAPI y tipos

Con los servicios iniciados:

```bash
make openapi
```

El comando exporta `frontend/openapi.json` desde FastAPI y genera
`frontend/app/types/api.generated.ts`. No se deben mantener manualmente tipos
duplicados. La escritura final la realiza el usuario del host para evitar
conflictos de UID con los bind mounts.

## Pruebas y calidad

```bash
make test
make lint
make typecheck
make format
```

Para el cierre completo con PostgreSQL, frontend compilado y Chromium, usar un
entorno independiente de los datos de desarrollo:

```bash
./scripts/check-local.sh
```

La imagen de testing instala Chromium y sus bibliotecas durante la construcción;
el usuario de ejecución no necesita permisos administrativos. Ver
[calidad y resultados](quality_es.md). Este comando no es la prueba humana.

## Comprobar persistencia

1. Crear un dato de prueba en PostgreSQL o un archivo en `/data/assets`.
2. Ejecutar `make down`.
3. Ejecutar `make up`.
4. Confirmar que el dato o archivo continúa.

No usar `make destroy` para esta prueba.

## Problemas frecuentes

### Docker responde “permission denied”

Abrir una nueva sesión después de agregar el usuario al grupo `docker`, o
ejecutar Docker con el mecanismo administrativo elegido para la VM.

### Un puerto está ocupado

Modificar `BACKEND_PORT` o `FRONTEND_PORT` en `.env`. Los valores afectan al
host; los puertos internos permanecen en 8000 y 3000.

### El frontend no alcanza al backend

Verificar `NUXT_PUBLIC_API_BASE_URL` y `BACKEND_CORS_ORIGINS`. La URL pública
debe ser alcanzable desde el navegador, no solo desde la red de Compose.
Por defecto CORS admite el origen `http://localhost:3000` y los métodos GET,
POST, PUT y PATCH utilizados por la API. Los orígenes adicionales deben
declararse explícitamente, separados por comas.

### Restaurar desde cero

Respaldar primero cualquier dato necesario y luego ejecutar:

```bash
make destroy
docker compose up --build
```

La operación elimina definitivamente la base y los assets almacenados en los
volúmenes.
